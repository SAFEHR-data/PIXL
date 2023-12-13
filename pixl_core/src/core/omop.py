"""Processing of OMOP parquet files."""
import datetime
import pathlib
import shutil

import slugify

root_from_install = pathlib.Path(__file__).parents[3]


class OmopExtract:
    """Processing Omop extracts on the filesystem."""

    def __init__(self, root_dir: pathlib.Path = root_from_install) -> None:
        """Create instance of OMOP file helper."""
        self.export_dir = root_dir / "exports"

    @staticmethod
    def _get_slugs(
        project_name: str, extract_datetime: datetime.datetime
    ) -> tuple[str, str]:
        """Convert project name and datetime to slugs for writing to filesystem."""
        project_slug = slugify.slugify(project_name)
        extract_time_slug = slugify.slugify(extract_datetime.isoformat())
        return project_slug, extract_time_slug

    def copy_to_exports(
        self,
        omop_dir: pathlib.Path,
        project_name: str,
        extract_datetime: datetime.datetime,
    ) -> str:
        """
        Copy public omop directory as the latest extract for the project.

        Creates directories if they don't already exist.
        :param omop_dir: parent path for omop export, with a "public" subdirectory
        :param project_name: name of the project
        :param extract_datetime: datetime that the OMOP ES extract was run
        :raises FileNotFoundError: if there is no public subdirectory in `omop_dir`
        :returns str: the project slug, so this can be registered for export to the DSH
        """
        public_input = omop_dir / "public"
        if not public_input.exists():
            msg = f"Could not find public directory in input {omop_dir}"
            raise FileNotFoundError(msg)

        # Make directory for exports if they don't exist
        project_slug, extract_time_slug = self._get_slugs(
            project_name, extract_datetime
        )
        export_base = self.export_dir / project_slug
        public_output = OmopExtract._mkdir(
            export_base / "all_extracts" / "omop" / extract_time_slug / "public"
        )

        # Copy extract files, overwriting if it exists
        shutil.copytree(public_input, public_output, dirs_exist_ok=True)
        # Make the latest export dir if it doesn't exist
        latest_parent_dir = self._mkdir(export_base / "latest" / "omop")
        # Symlink this extract to the latest directory
        latest_public = latest_parent_dir / "public"
        if latest_public.exists():
            latest_public.unlink()

        latest_public.symlink_to(public_output, target_is_directory=True)
        return project_slug

    @staticmethod
    def _mkdir(directory: pathlib.Path) -> pathlib.Path:
        directory.mkdir(parents=True, exist_ok=True)
        return directory

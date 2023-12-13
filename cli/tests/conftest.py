"""CLI testing fixtures."""
import pathlib

import pytest
from core.omop import OmopExtract


@pytest.fixture()
def omop_files(tmp_path_factory: pytest.TempPathFactory) -> OmopExtract:
    """Create an OmopFiles instance using a temporary directory"""
    export_dir = tmp_path_factory.mktemp("repo_base")
    return OmopExtract(export_dir)


@pytest.fixture()
def resources() -> pathlib.Path:
    """Test resources directory path."""
    return pathlib.Path(__file__).parent / "resources"

from pathlib import Path

import pytest
import yaml
from core.config import PixlConfig
from pydantic import ValidationError

EXAMPLE_CONFIG = Path(__file__).parents[2] / "config-template" / "example-config.yaml"


def test_config():
    """Test whether config file is correctly parsed and validated."""
    config_data = yaml.safe_load(EXAMPLE_CONFIG.read_text())
    config = PixlConfig.parse_obj(config_data)

    assert config.project.name == "myproject"
    assert config.project.modalities == ["DX", "CR"]
    assert config.tag_operations.base_profile == Path(
        "orthanc/orthanc-anon/plugin/tag-operations.yaml"
    )
    assert config.destination.dicom == "ftps"
    assert config.destination.parquet == "ftps"


BASE_YAML_DATA = {
    "project": {"name": "myproject", "modalities": ["DX", "CR"]},
    "tag_operations": {
        "base_profile": "orthanc/orthanc-anon/plugin/tag-operations.yaml",
        "extension_profile": None,
    },
    "destination": {"dicom": "ftps", "parquet": "ftps"},
}


def test_valid_extension_profile():
    """Test that the config validation passes for valid extension profile."""
    config_data = BASE_YAML_DATA
    config_data["tag_operations"][
        "extension_profile"
    ] = "orthanc/orthanc-anon/plugin/tag-operations.yaml"

    config = PixlConfig.parse_obj(config_data)
    assert config.tag_operations.extension_profile.exists()


def test_parquet_dicom_fails():
    """
    Test that the config validation fails for non-valid values: 'dicomweb' not allowed for
    parquet destionation
    """
    config_data = BASE_YAML_DATA
    config_data["destination"]["parquet"] = "dicomweb"
    with pytest.raises(ValidationError):
        PixlConfig.parse_obj(config_data)


def test_invalid_destinations():
    """Test that the config validation fails for invalid destinations."""
    config_data = BASE_YAML_DATA
    config_data["destination"]["dicom"] = "nope"
    config_data["destination"]["parquet"] = "nope"
    with pytest.raises(ValidationError):
        PixlConfig.parse_obj(config_data)


def test_invalid_paths():
    """Test that the config validation fails for invalid tag-operation paths."""
    config_data_wrong_base = BASE_YAML_DATA
    config_data_wrong_base["tag_operations"]["base_profile"] = "/i/dont/exist.yaml"
    with pytest.raises(ValidationError):
        PixlConfig.parse_obj(config_data_wrong_base)

    config_data_wrong_extension = BASE_YAML_DATA
    config_data_wrong_extension["tag_operations"]["extension_profile"] = "/i/dont/exist.yaml"
    with pytest.raises(ValidationError):
        PixlConfig.parse_obj(config_data_wrong_extension)

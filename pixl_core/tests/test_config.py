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


def test_config_fails():
    """
    Test that the config validation fails for non-valid values:
        - 'dicomweb' not allowed for parquet destionation
        - Invalid destinations
        - Non-existing base_profile path
        - Non-exisiting extension_profile path
    """
    with pytest.raises(ValidationError):
        PixlConfig(
            project={"name": "myproject", "modalities": ["DX", "CR"]},
            tag_operations={
                "base_profile": "orthanc/orthanc-anon/plugin/tag-operations.yaml",
            },
            destination={"dicom": "ftps", "parquet": "dicomweb"},
        )
    with pytest.raises(ValidationError):
        PixlConfig(
            project={"name": "myproject", "modalities": ["DX", "CR"]},
            tag_operations={
                "base_profile": "orthanc/orthanc-anon/plugin/tag-operations.yaml",
            },
            destination={"dicom": "nope", "parquet": "nope"},
        )
    with pytest.raises(ValidationError):
        PixlConfig(
            project={"name": "myproject", "modalities": ["DX", "CR"]},
            tag_operations={"base_profile": "/i/dont/exist.yaml"},
            destination={"dicom": "ftps", "parquet": "ftps"},
        )
    with pytest.raises(ValidationError):
        PixlConfig(
            project={"name": "myproject", "modalities": ["DX", "CR"]},
            tag_operations={
                "base_profile": "orthanc/orthanc-anon/plugin/tag-operations.yaml",
                "extension_profile": "/i/dont/exist.yaml",
            },
            destination={"dicom": "ftps", "parquet": "ftps"},
        )

#  Copyright (c) University College London Hospitals NHS Foundation Trust
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.


from pathlib import Path

import pytest
from core.project_config import PixlConfig, _load_and_validate
from decouple import config
from pydantic import ValidationError

PROJECT_CONFIGS_DIR = Path(config("PROJECT_CONFIGS_DIR"))
TEST_CONFIG = PROJECT_CONFIGS_DIR / "test-extract-uclh-omop-cdm.yaml"


def test_config_from_file():
    """Test whether config file is correctly parsed and validated."""
    project_config = _load_and_validate(TEST_CONFIG)

    assert project_config.project.name == "test-extract-uclh-omop-cdm"
    assert project_config.project.modalities == ["DX", "CR"]
    assert project_config.tag_operation_files == [
        PROJECT_CONFIGS_DIR / "tag-operations" / "test-extract-uclh-omop-cdm.yaml"
    ]
    assert project_config.destination.dicom == "ftps"
    assert project_config.destination.parquet == "ftps"


@pytest.fixture()
def base_yaml_data():
    """Good data (excluding optional fields)"""
    return {
        "project": {"name": "myproject", "modalities": ["DX", "CR"]},
        "tag_operation_files": ["test-extract-uclh-omop-cdm.yaml"],
        "destination": {"dicom": "ftps", "parquet": "ftps"},
    }


def test_base_is_valid(base_yaml_data):
    """Before anything else, check that the unaltered baseline validates ok."""
    PixlConfig.model_validate(base_yaml_data)


def test_parquet_dicom_fails(base_yaml_data):
    """
    Test that the config validation fails for non-valid values: 'dicomweb' not allowed for
    parquet destionation
    """
    config_data = base_yaml_data
    config_data["destination"]["parquet"] = "dicomweb"
    with pytest.raises(ValidationError):
        PixlConfig.model_validate(config_data)


def test_invalid_destinations(base_yaml_data):
    """Test that the config validation fails for invalid destinations."""
    config_data = base_yaml_data
    config_data["destination"]["dicom"] = "nope"
    config_data["destination"]["parquet"] = "nope"
    with pytest.raises(ValidationError):
        PixlConfig.model_validate(config_data)


def test_too_many_paths(base_yaml_data):
    """Test that the config validation fails if there are >1 tag operation files"""
    config_data_extra_file = base_yaml_data
    tof = config_data_extra_file["tag_operation_files"]
    tof.append(tof[0])
    with pytest.raises(ValidationError, match="at most 1"):
        PixlConfig.model_validate(config_data_extra_file)


def test_invalid_paths(base_yaml_data):
    """Test that the config validation fails for invalid tag-operation paths."""
    config_data_wrong_base = base_yaml_data
    config_data_wrong_base["tag_operation_files"][0] = "/i/dont/exist.yaml"
    with pytest.raises(ValidationError):
        PixlConfig.model_validate(config_data_wrong_base)


@pytest.mark.parametrize(("yaml_file"), PROJECT_CONFIGS_DIR.glob("*.yaml"))
def test_all_real_configs(yaml_file):
    """Test that all production configs are valid"""
    _load_and_validate(yaml_file)

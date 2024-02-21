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
from core.project_config import PixlConfig, _load_project_config
from decouple import config
from pydantic import ValidationError

PROJECT_CONFIGS_DIR = Path(config("PROJECT_CONFIGS_DIR"))
TEST_CONFIG = PROJECT_CONFIGS_DIR / "test-extract-uclh-omop-cdm.yaml"


def test_config_from_file():
    """Test whether config file is correctly parsed and validated."""
    project_config = _load_project_config(TEST_CONFIG)

    assert project_config.project.name == "myproject"
    assert project_config.project.modalities == ["DX", "CR"]
    assert project_config.tag_operation_files == [
        PROJECT_CONFIGS_DIR / "tag-operations" / "test-extract-uclh-omop-cdm-tag-operations.yaml"
    ]
    assert project_config.destination.dicom == "ftps"
    assert project_config.destination.parquet == "ftps"


BASE_YAML_DATA = {
    "project": {"name": "myproject", "modalities": ["DX", "CR"]},
    "tag_operations": ["test-extract-uclh-omop-cdm-tag-operations.yaml"],
    "destination": {"dicom": "ftps", "parquet": "ftps"},
}


def test_parquet_dicom_fails():
    """
    Test that the config validation fails for non-valid values: 'dicomweb' not allowed for
    parquet destionation
    """
    config_data = BASE_YAML_DATA
    config_data["destination"]["parquet"] = "dicomweb"
    with pytest.raises(ValidationError):
        PixlConfig.model_validate(config_data)


def test_invalid_destinations():
    """Test that the config validation fails for invalid destinations."""
    config_data = BASE_YAML_DATA
    config_data["destination"]["dicom"] = "nope"
    config_data["destination"]["parquet"] = "nope"
    with pytest.raises(ValidationError):
        PixlConfig.model_validate(config_data)


def test_invalid_paths():
    """Test that the config validation fails for invalid tag-operation paths."""
    config_data_wrong_base = BASE_YAML_DATA
    config_data_wrong_base["tag_operations"][0] = "/i/dont/exist.yaml"
    with pytest.raises(ValidationError):
        PixlConfig.model_validate(config_data_wrong_base)

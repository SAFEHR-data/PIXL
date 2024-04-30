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
"""Check validity of radiology export"""

from pathlib import Path

import pytest
from conftest import RESOURCES_DIR


@pytest.mark.usefixtures("_setup_pixl_cli")
def test_public_parquet(host_export_root_dir: Path) -> None:
    """Tests whether the public parquet files have been exported to the right place"""
    expected_public_dir = (
        host_export_root_dir / "test-extract-uclh-omop-cdm" / "latest" / "omop" / "public"
    )
    expected_files = sorted([x.stem for x in (RESOURCES_DIR / "omop" / "public").glob("*.parquet")])

    assert expected_public_dir.exists()
    assert expected_files == sorted([x.stem for x in expected_public_dir.glob("*.parquet")])

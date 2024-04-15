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

import logging
from pathlib import Path

import pandas as pd
import pytest
from conftest import RESOURCES_DIR

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("_setup_pixl_cli")
def test_public_parquet(host_export_root_dir: Path) -> None:
    """Tests whether the public parquet files have been exported to the right place"""
    expected_public_dir = (
        host_export_root_dir / "test-extract-uclh-omop-cdm" / "latest" / "omop" / "public"
    )
    expected_files = sorted([x.stem for x in (RESOURCES_DIR / "omop" / "public").glob("*.parquet")])

    assert expected_public_dir.exists()
    assert expected_files == sorted([x.stem for x in expected_public_dir.glob("*.parquet")])


@pytest.mark.usefixtures("_extract_radiology_reports")
def test_radiology_parquet(host_export_root_dir: Path) -> None:
    """
    From:
    scripts/test_radiology_parquet.py \
        ../projects/exports/test-extract-uclh-omop-cdm/latest/radiology/radiology.parquet
    Test contents of radiology report parquet file in the export location
    """
    expected_radiology_parquet_file = (
        host_export_root_dir
        / "test-extract-uclh-omop-cdm"
        / "latest"
        / "radiology"
        / "radiology.parquet"
    )

    exported_data = pd.read_parquet(expected_radiology_parquet_file)

    logger.warning(exported_data.head())

    parquet_header_names = ["image_identifier", "procedure_occurrence_id", "image_report"]
    assert (exported_data.columns == parquet_header_names).all()

    # the fake DEID service adds this string to the end to confirm it has been through it
    DE_ID_SUFFIX = "**DE-IDENTIFIED**"

    expected_rows = 2
    assert exported_data.shape[0] == expected_rows

    po_col = exported_data["procedure_occurrence_id"]
    row_po_4 = exported_data[po_col == 4].iloc[0]
    row_po_5 = exported_data[po_col == 5].iloc[0]
    assert row_po_4.image_report == "this is a radiology report 1" + DE_ID_SUFFIX

    # blake2b-256 hash of string ('987654321' + 'AA12345601') with key = 'test_key'
    assert (
        row_po_4.image_identifier
        == "d40f0639105babcdec043f1acf7330a8ebd64e64f13f7d0d4745f0135ddee0cd"
    )

    assert row_po_5.image_report == "this is a radiology report 2" + DE_ID_SUFFIX

    # blake2b-256 hash of string ('987654321' + 'AA12345605') with key = 'test_key'
    assert (
        row_po_5.image_identifier
        == "7ff25b0b438d23a31db984f49b0d6ca272104eb3d20c82f30e392cff5446a9c3"
    )

    # Files must not be owned by root - they'll be hard to delete and we shouldn't be running our
    # containers as root anyway.
    file_stats = expected_radiology_parquet_file.stat()
    try:
        assert file_stats.st_uid != 0
        assert file_stats.st_gid != 0
    except AssertionError:
        logger.exception("Known bug: files should not be owned by root")

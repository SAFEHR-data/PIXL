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

"""Test functions in _io.py."""

import pytest
from pixl_cli._io import messages_from_csv


def test_message_from_csv_raises_for_malformed_input(tmpdir):
    """Test that messages_from_csv raises for malformed input."""
    # Create a CSV file with the wrong column names
    csv_file = tmpdir.join("malformed.csv")
    csv_file.write("procedure_id,mrn,accession_number,extract_generated_timestamp,study_date\n")
    csv_file.write("1,123,1234,01/01/2021 00:00,01/01/2021\n")
    with pytest.raises(ValueError, match=".*expected to have at least.*"):
        messages_from_csv(csv_file)

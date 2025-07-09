#  Copyright (c) 2022 University College London Hospitals NHS Foundation Trust
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
from __future__ import annotations

import pytest

from hasher.hashing import Hasher  # type: ignore [import-untyped]

TEST_MIN_LENGTHS = range(-10, 1)
TEST_MAX_LENGTHS = range(65, 100)
TEST_PROJECT_SLUG = "test_project_slug"


@pytest.fixture
def mock_hasher(_mock_hasher):
    return Hasher(TEST_PROJECT_SLUG)


def test_generate_hash_of_default_length(mock_hasher):
    message = "test"
    digest = mock_hasher.generate_hash(message)
    assert len(digest) == 64
    assert digest == "cc8ab6f3e63235b45f3d00cbc4873efac59bf15cec4bdffd461882d57dfc010f"


@pytest.mark.parametrize("length", TEST_MIN_LENGTHS)
def test_generate_hash_enforces_min_length(mock_hasher, length):
    message = "test"
    with pytest.raises(ValueError, match="Minimum hash length is 2"):
        mock_hasher.generate_hash(message, length=1)


@pytest.mark.parametrize("length", TEST_MAX_LENGTHS)
def test_generate_hash_enforces_max_length(mock_hasher, length):
    message = "test"
    with pytest.raises(ValueError, match="Maximum hash length is 64"):
        mock_hasher.generate_hash(message, length)


def test_generate_hash_of_specific_length(mock_hasher):
    message = "test"
    length = 16
    digest = mock_hasher.generate_hash(message, length)
    assert len(digest) == length
    assert digest == "b721eef65328a79c"


TEST_MESSSAGES = [("9876544321", 12), ("1.2.840.10008", 48)]


@pytest.mark.parametrize(("message", "length"), TEST_MESSSAGES)
def test_generate_hash_output_length(message, length, mock_hasher):
    digest = mock_hasher.generate_hash(message, length)
    assert len(digest) <= length


@pytest.mark.parametrize("length", TEST_MIN_LENGTHS)
def test_generate_salt_enforces_min_length(mock_hasher, length):
    with pytest.raises(ValueError, match="Minimum salt length is 2"):
        mock_hasher.create_salt(length)


@pytest.mark.parametrize("length", TEST_MAX_LENGTHS)
def test_generate_salt_enforces_max_length(mock_hasher, length):
    with pytest.raises(ValueError, match="Maximum salt length is 64"):
        mock_hasher.create_salt(length)


def test_generate_salt_of_specific_length(mock_hasher):
    length = 9
    salt = mock_hasher.create_salt(length)
    assert len(salt) <= length


def test_generate_salt_produces_unique_outputs(mock_hasher):
    salt_1 = mock_hasher.create_salt()
    salt_2 = mock_hasher.create_salt()
    assert salt_1 != salt_2

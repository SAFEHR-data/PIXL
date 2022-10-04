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

from hypothesis import example, given, strategies as st

from hasher.hashing import generate_hash


def test_generate_hash(dummy_key):
    msg = "test"
    digest = generate_hash(msg)
    assert digest == "270426312ab76c2f0df60b6cef3d14aab6bc17219f1a76e63edf88a8f705c17a"


@given(msg=st.text(min_size=0, max_size=1024))
@example(msg="9876544321")
@example(msg="1.2.840.10008")
def test_digest_max_length(msg):
    digest = generate_hash(msg)
    assert len(digest) <= 64

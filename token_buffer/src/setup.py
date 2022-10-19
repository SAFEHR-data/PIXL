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

from setuptools import find_packages, setup

exec(open("token_buffer/_version.py").read())

setup(
    name="token_buffer",
    version=__version__,  # noqa: F821
    description="Service to create and manage a token bucket",
    packages=find_packages(
        include=[
            "token_buffer*",
        ],
        exclude=[
            "*tests",
            "*.tests.*",
        ],
    ),
    python_requires=">=3.10",
)

#  Copyright (c) University College London Hospitals NHS Foundation Trust and Microsoft
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
# limitations under the License.
from setuptools import setup, find_packages

exec(open("pixl_ehr/_version.py").read())

setup(
    name="pixl_ehr",
    version=__version__,  # noqa: F821
    author="Tom Young",
    url="https://github.com/UCLH-DIF/PIXL",
    description="PIXL electronic health record extractor",
    packages=find_packages(
        exclude=["*tests", "*.tests.*"],
    ),
    package_data={
        "pixl_ehr": ["sql/*.sql"],
    },
    python_requires=">=3.10",
)

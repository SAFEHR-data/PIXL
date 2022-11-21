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
FROM osimis/orthanc:22.9.0-full-stable
SHELL ["/bin/bash", "-o", "pipefail", "-e", "-u", "-x", "-c"]

COPY ./orthanc/orthanc-anon/plugin/pixl.py /etc/orthanc/pixl.py
COPY ./orthanc/orthanc-anon/plugin/tag-operations.yaml /etc/orthanc/tag-operations.yaml

COPY ./pixl_dcmd/src/requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY ./pixl_dcmd/src ./pixl_dcmd
RUN pip3 install --no-cache-dir ./pixl_dcmd
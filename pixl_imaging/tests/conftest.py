"""Setup for tests."""
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

import os

os.environ["TEST"] = "true"
os.environ["LOGLEVEL"] = "DEBUG"
os.environ["RABBITMQ_PASSWORD"] = "guest"
os.environ["RABBITMQ_USERNAME"] = "guest"
os.environ["RABBITMQ_HOST"] = "queue"
os.environ["RABBITMQ_PORT"] = "5672"
os.environ["ORTHANC_RAW_URL"] = "http://localhost:8044"
os.environ["ORTHANC_RAW_USERNAME"] = "orthanc"
os.environ["ORTHANC_RAW_PASSWORD"] = "orthanc"
os.environ["ORTHANC_RAW_AE_TITLE"] = "PIXLRAW"
os.environ["ORTHANC_VNA_URL"] = "http://localhost:8043"
os.environ["ORTHANC_VNA_USERNAME"] = "orthanc"
os.environ["ORTHANC_VNA_PASSWORD"] = "orthanc"
os.environ["ORTHANC_VNA_AE_TITLE"] = "VNAQR"
os.environ["VNAQR_MODALITY"] = "UCVNAQR"
os.environ["PIXL_DICOM_TRANSFER_TIMEOUT"] = "30"
os.environ["SKIP_ALEMBIC"] = "true"
os.environ["PIXL_MAX_MESSAGES_IN_FLIGHT"] = "20"
os.environ["ORTHANC_AUTOROUTE_RAW_TO_ANON"] = "false"

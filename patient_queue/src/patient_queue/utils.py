#  Copyright (c) 2022 University College London Hospitals NHS Foundation Trust
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from enum import Enum


class AvailableTopics(Enum):
    """
    In Pulsar, topics are offered to consumers for subscription. This Enum provides an overview over all the topics
    that are available as part of Pixl. At the moment, it is envisaged that there will be two different topics, one
    for the image and one for the EHR demographics download.
    """
    DICOM = "dicom"
    EHR = "ehr"
    ORTHANC = "orthanc"

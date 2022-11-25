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
import requests

from json import JSONDecodeError
from abc import ABC, abstractmethod
from typing import Any
from pixl_pacs.utils import env_var
from requests.auth import HTTPBasicAuth


class Orthanc(ABC):
    def __init__(self, url: str, username: str, password: str):

        self._url = url.rstrip("/")
        self._username = username
        self._password = password

        self._auth = HTTPBasicAuth(username=username, password=password)

    @property
    def modalities(self) -> Any:
        """Accessible modalities from this Orthanc node"""
        return self._get("/modalities")

    @abstractmethod
    @property
    def modality(self) -> str:
        """The modality for this orthanc instance, as defined in dicom.json"""

    def query_remote(self, data: dict, modality: str) -> dict:
        """Query a particular modality, available from this node"""

        query_data = self._post(f"/modalities/{modality}/query", data=data)
        return self._get(f"/queries/{query_data['ID']}/answers")

    def _get(self, path: str) -> Any:
        return _decode(requests.get(f"{self._url}{path}", auth=self._auth))

    def _post(self, path: str, data: dict) -> Any:
        return _decode(requests.post(f"{self._url}{path}", json=data, auth=self._auth))


def _decode(response: requests.Response) -> Any:
    """Decode an Orthanc rest API reponse"""

    if response.status_code != 200:
        raise requests.HTTPError(f"Failed request. "
                                 f"Status code: {response.status_code}"
                                 f"Content: {response.content}")
    try:
        return response.json()
    except JSONDecodeError:
        raise requests.HTTPError(f"Failed to parse {response} as json")


class PIXLRawOrthanc(Orthanc):
    def __init__(self):
        super().__init__(
            url="http://orthanc-raw:8042",
            username=env_var("ORTHANC_RAW_USERNAME"),
            password=env_var("ORTHANC_RAW_PASSWORD")
        )

    @property
    def modality(self) -> str:
        return env_var("RAW_MODAILITY")

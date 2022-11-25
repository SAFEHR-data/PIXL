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
from abc import ABC, abstractmethod
from json import JSONDecodeError
import logging
from typing import Any, Optional

from pixl_pacs.utils import env_var
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger("uvicorn")


class Orthanc(ABC):
    def __init__(self, url: str, username: str, password: str):

        self._url = url.rstrip("/")
        self._username = username
        self._password = password

        self._auth = HTTPBasicAuth(username=username, password=password)

    @property
    @abstractmethod
    def aet(self) -> str:
        """Application entity title (AET) of this Orthanc instance"""

    @property
    def modalities(self) -> Any:
        """Accessible modalities from this Orthanc instance"""
        return self._get("/modalities")

    def query_local(self, data: dict) -> Any:
        return self._post("/tools/find", data=data)

    def query_remote(self, data: dict, modality: str) -> Optional[str]:
        """Query a particular modality, available from this node"""
        logger.debug(f"Running query on modality: {modality} with {data}")

        response = self._post(f"/modalities/{modality}/query", data=data)
        logger.debug(f"Query response: {response}")

        if len(self._get(f"/queries/{response['ID']}/answers")) > 0:
            return str(response["ID"])
        else:
            return None

    def retrieve_from_remote(self, query_id: str) -> Any:
        response = self._post(
            f"/queries/{query_id}/retrieve",
            data={"TargetAet": self.aet, "Synchronous": True},  # TODO: async
        )
        return response

    def _get(self, path: str) -> Any:
        return _deserialise(requests.get(f"{self._url}{path}", auth=self._auth))

    def _post(self, path: str, data: dict) -> Any:
        return _deserialise(
            requests.post(f"{self._url}{path}", json=data, auth=self._auth)
        )


def _deserialise(response: requests.Response) -> Any:
    """Decode an Orthanc rest API response"""

    if response.status_code != 200:
        raise requests.HTTPError(
            f"Failed request. "
            f"Status code: {response.status_code}"
            f"Content: {response.content.decode()}"
        )
    try:
        return dict(response.json())
    except (JSONDecodeError, ValueError):
        raise requests.HTTPError(f"Failed to parse {response} as json")


class PIXLRawOrthanc(Orthanc):
    def __init__(self) -> None:
        super().__init__(
            url="http://orthanc-raw:8042",
            username=env_var("ORTHANC_RAW_USERNAME"),
            password=env_var("ORTHANC_RAW_PASSWORD"),
        )

    @property
    def aet(self) -> str:
        return env_var("RAW_AE_TITLE")

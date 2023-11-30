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
import logging
from abc import ABC, abstractmethod
from json import JSONDecodeError
from typing import Any, Optional

import requests
from decouple import config
from requests.auth import HTTPBasicAuth

logger = logging.getLogger("uvicorn")


class Orthanc(ABC):
    def __init__(self, url: str, username: str, password: str) -> None:
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
        logger.debug("Running query on modality: %s with %s", modality, data)

        response = self._post(
            f"/modalities/{modality}/query",
            data=data,
            timeout=config("PIXL_QUERY_TIMEOUT", default=10, cast=float),
        )
        logger.debug("Query response: %s", response)

        if len(self._get(f"/queries/{response['ID']}/answers")) > 0:
            return str(response["ID"])

        return None

    def retrieve_from_remote(self, query_id: str) -> str:
        response = self._post(
            f"/queries/{query_id}/retrieve",
            data={"TargetAet": self.aet, "Synchronous": False},
        )
        return str(response["ID"])

    def job_state(self, job_id: str) -> str:
        # See: https://book.orthanc-server.com/users/advanced-rest.html#jobs-monitoring
        return str(self._get(f"/jobs/{job_id}")["State"])

    def _get(self, path: str) -> Any:
        return _deserialise(
            requests.get(f"{self._url}{path}", auth=self._auth, timeout=10)
            )

    def _post(self, path: str, data: dict, timeout: Optional[float] = None) -> Any:
        return _deserialise(
            requests.post(
                f"{self._url}{path}", json=data, auth=self._auth, timeout=timeout
            )
        )


def _deserialise(response: requests.Response) -> Any:
    """Decode an Orthanc rest API response"""
    success_code = 200
    if response.status_code != success_code:
        msg = (
            f"Failed request. "
            f"Status code: {response.status_code}"
            f"Content: {response.content.decode()}"
        )
        raise requests.HTTPError(
            msg
        )
    try:
        return response.json()
    except (JSONDecodeError, ValueError) as exc:
        msg = f"Failed to parse {response} as json"
        raise requests.HTTPError(msg) from exc


class PIXLRawOrthanc(Orthanc):
    def __init__(self) -> None:
        super().__init__(
            url="http://orthanc-raw:8042",
            username=config("ORTHANC_RAW_USERNAME"),
            password=config("ORTHANC_RAW_PASSWORD"),
        )

    @property
    def aet(self) -> str:
        return str(config("ORTHANC_RAW_AE_TITLE"))

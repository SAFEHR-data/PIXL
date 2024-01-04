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
"""Filter a cohort .csv file for those that are not present in Orthanc raw"""
from __future__ import annotations

import os
import sys
from json import JSONDecodeError
from typing import Any

import requests
from requests.auth import HTTPBasicAuth

os.environ["NO_PROXY"] = os.environ["no_proxy"] = "localhost"


class Study:
    def __init__(self, uid: str):
        self.uid = uid


class Orthanc:
    def __init__(
        self,
        url=f"http://localhost:{os.environ['ORTHANC_PORT']}",
        username=os.environ["ORTHANC_USERNAME"],
        password=os.environ["ORTHANC_PASSWORD"],
    ):
        self._url = url.rstrip("/")
        self._username = username
        self._password = password

        self._auth = HTTPBasicAuth(username=username, password=password)

    @property
    def studies(self) -> list[Study]:
        """Get all the studies in an Orthanc instance"""
        uids = self.query_local(
            {
                "Level": "Study",
                "Query": {},
            }
        )
        return [Study(uid) for uid in uids]

    def accession_number(self, study: Study) -> str:
        data = self._get(f"/studies/{study.uid}")
        return data["MainDicomTags"]["AccessionNumber"]

    def query_local(self, data: dict) -> Any:
        return self._post("/tools/find", data=data)

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
        return response.json()
    except (JSONDecodeError, ValueError):
        raise requests.HTTPError(f"Failed to parse {response} as json")


if __name__ == "__main__":
    filename = sys.argv[1]
    orthanc = Orthanc()

    present_accession_numbers = [orthanc.accession_number(s) for s in orthanc.studies]
    print(f"Found {len(present_accession_numbers)} total studies")

    with Path.open(filename) as file:
        with Path.open(f"{filename.rstrip('.csv')}_filtered.csv", "w") as new_file:
            for line in file:
                if any(a in line for a in present_accession_numbers):
                    continue

                print(line, file=new_file)

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
"""Delete a number of studies from an Orthanc instance"""
import argparse
from datetime import datetime
from json import JSONDecodeError
import os
from typing import Any, List, Optional

import requests
from requests.auth import HTTPBasicAuth

os.environ["NO_PROXY"] = os.environ["no_proxy"] = "localhost"


class Study:
    def __init__(self, uid: str):
        self.uid = uid
        self.received_time: Optional[datetime] = None


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
    def studies(self) -> List[Study]:
        """Get all the studies in an Orthanc instance"""
        uids = self.query_local(
            {
                "Level": "Study",
                "Query": {},
            }
        )
        return [Study(uid) for uid in uids]

    def received_time(self, study: Study) -> datetime:
        """Get the received time of this study"""
        r = requests.get(
            f"{self._url}/studies/{study.uid}/metadata/LastUpdate", auth=self._auth
        )
        time_string = r.content.decode()  # UTC e.g. 20230218T125518
        return datetime.strptime(time_string, "%Y%m%d" + "T" + "%H%M%S")

    def query_local(self, data: dict) -> Any:
        return self._post("/tools/find", data=data)

    def delete(self, study: Study) -> None:
        """Delete a study from Orthanc"""
        response = requests.delete(
            f"{self._url}/studies/{study.uid}",
            auth=self._auth
        )

        if response.status_code != 200:
            raise RuntimeError(f"Failed to delete: {study.uid}")

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


def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "number_to_delete", type=int, help="Number of the oldest studies to delete"
    )
    parser.add_argument(
        "--pause", action="store_true", help="Pause prior to deleting each study"
    )
    return parser.parse_args()


if __name__ == "__main__":

    args = parse_args()
    print(f"Deleting the oldest {args.number_to_delete} studies")

    orthanc = Orthanc()
    studies = orthanc.studies
    print(f"Found {len(studies)} total studies")

    for study in studies:
        study.received_time = orthanc.received_time(study)

    for i, study in enumerate(sorted(studies, key=lambda x: x.received_time)):
        if i == args.number_to_delete:
            break

        print(f"Deleting study received at {study.received_time}. uid: {study.uid}")

        if args.pause:
            _ = input("Press any key to continue")

        orthanc.delete(study)

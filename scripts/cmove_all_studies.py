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
"""C-Move all studies from Orthanc Raw to Anon"""
import argparse
from datetime import datetime, timedelta
from json import JSONDecodeError
import os
from typing import Any

import requests
from requests.auth import HTTPBasicAuth

os.environ["NO_PROXY"] = os.environ["no_proxy"] = "localhost"


class Orthanc:
    def __init__(
        self,
        url=f"http://localhost:{os.environ['ORTHANC_PORT']}",
        username=os.environ["ORTHANC_USERNAME"],
        password=os.environ["ORTHANC_PASSWORD"],
        anon_aet=os.environ["ORTHANC_ANON_AE_TITLE"],
    ):
        self._url = url.rstrip("/")
        self._username = username
        self._password = password
        self._anon_aet = anon_aet

        self._auth = HTTPBasicAuth(username=username, password=password)

    def cmove_to_anon(self, _query_id: str) -> None:
        data = {"TargetAet": self._anon_aet}
        print(self._post(f"/queries/{_query_id}/retrieve", data=data))

    def query_remote(self, data: dict) -> str:
        return self._post("/modalities/PIXL-Raw/query", data=data)["ID"]

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
        "start_date",
        help="Date from which to trigger C-Move from in the format: YYYY-MM-DD",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    orthanc = Orthanc()

    start_date = datetime.fromisoformat(args.start_date)
    now = datetime.now()

    for i in range((now - start_date).days):
        date = start_date + timedelta(days=i)

        query_id = orthanc.query_remote(
            data={"Level": "Study", "Query": {"StudyDate": date.strftime("%Y%m%d")}}
        )
        print(f"Driving C-Move for study {i} {query_id} on {date}")

        orthanc.cmove_to_anon(query_id)

        _ = input("Waiting... press any key to continue")

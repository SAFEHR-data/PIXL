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
"""Queries to orthanc (anon)"""

from __future__ import annotations

import json
from io import BytesIO

import requests
from decouple import config
from loguru import logger


def get_study_zip_archive(resourceId: str) -> BytesIO:
    # Download zip archive of the DICOM resource
    query = f"{ORTHANC_ANON_URL}/studies/{resourceId}/archive"
    fail_msg = "Could not download archive of resource '%s'"
    response_study = _query_orthanc_anon(resourceId, query, fail_msg)

    # get the zip content
    logger.debug("Downloaded data for resource {}", resourceId)
    return BytesIO(response_study.content)


def get_tags_by_study(study_id: str) -> tuple[str, str]:
    """
    Queries the Orthanc server at the study level, returning the
    Study Instance UID and UCLHPIXLProjectName DICOM tags.
    BEWARE: post-anonymisation, the Study Instance UID is NOT
    the Study Instance UID, it's the pseudo-anonymised ID generated randomly.
    """
    query = f"{ORTHANC_ANON_URL}/studies/{study_id}/shared-tags?simplify=true"
    fail_msg = "Could not query study for resource '%s'"

    response_study = _query_orthanc_anon(study_id, query, fail_msg)
    json_response = json.loads(response_study.content.decode())
    return json_response["StudyInstanceUID"], json_response["UCLHPIXLProjectName"]


def _query_orthanc_anon(resourceId: str, query: str, fail_msg: str) -> requests.Response:
    try:
        response = requests.get(
            query,
            auth=(config("ORTHANC_ANON_USERNAME"), config("ORTHANC_ANON_PASSWORD")),
            timeout=10,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException:
        logger.exception("Failed to query resource '{}', error: '{}'", resourceId, fail_msg)
        raise
    else:
        return response


ORTHANC_ANON_URL = "http://orthanc-anon:8042"

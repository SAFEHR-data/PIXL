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
from __future__ import annotations

import asyncio
import contextlib
from asyncio import sleep
from time import time
from typing import Any, Optional

import aiohttp
from core.exceptions import PixlDiscardError, PixlRequeueMessageError
from decouple import config
from loguru import logger


class Orthanc:
    def __init__(  # noqa: PLR0913
        self,
        url: str,
        username: str,
        password: str,
        http_timeout: int,
        dicom_timeout: int,
        aet: str,
    ) -> None:
        if not url:
            msg = "URL for orthanc is required"
            raise ValueError(msg)
        self._url = url.rstrip("/")
        self._aet = aet
        self._username = username
        self._password = password

        self._auth = aiohttp.BasicAuth(login=username, password=password)
        self.http_timeout = http_timeout
        self.dicom_timeout = dicom_timeout

    @property
    def aet(self) -> str:
        """Application entity title (AET) of this Orthanc instance"""
        return self._aet

    @property
    async def modalities(self) -> Any:
        """Accessible modalities from this Orthanc instance"""
        return await self._get("/modalities")

    async def query_local(self, data: dict) -> Any:
        """Query local Orthanc instance for resourceId."""
        logger.debug("Running query on local Orthanc with {}", data)
        return await self._post("/tools/find", data=data)

    async def query_local_study(self, study_id: str) -> Any:
        """Query local Orthanc instance for study."""
        return await self._get(f"/studies/{study_id}")

    async def query_local_series(self, series_id: str) -> Any:
        """Query local Orthanc instance for series."""
        return await self._get(f"/series/{series_id}")

    async def query_local_instance(self, instance_id: str) -> Any:
        """Query local Orthanc instance for instance."""
        return await self._get(f"/instances/{instance_id}")

    async def query_remote(self, data: dict, modality: str) -> Optional[str]:
        """Query a particular modality, available from this node"""
        logger.debug("Running query on modality: {} with {}", modality, data)

        response = await self._post(
            f"/modalities/{modality}/query",
            data=data,
        )
        logger.debug("Query response: {}", response)
        query_answers = await self.get_remote_query_answers(response["ID"])
        if len(query_answers) > 0:
            return str(response["ID"])

        return None

    async def get_remote_query_answers(self, query_id: str) -> Any:
        """Get the answers to a query"""
        return await self._get(f"/queries/{query_id}/answers")

    async def get_remote_query_answer_content(self, query_id: str, answer_id: str) -> Any:
        """Get the content of a query answer"""
        return await self._get(f"/queries/{query_id}/answers/{answer_id}/content")

    async def get_remote_query_answer_instances(self, query_id: str, answer_id: str) -> Any:
        """Get the instances of a query answer, using DICOM timeout as can take a while"""
        response = await self._post(
            f"/queries/{query_id}/answers/{answer_id}/query-instances",
            data={"Query": {}},
            timeout=self.dicom_timeout,
        )
        return response["ID"]

    async def modify_private_tags_by_study(
        self,
        *,
        study_id: str,
        private_creator: str,
        tag_replacement: dict,
    ) -> None:
        # According to the docs, you can't modify tags for an instance using the instance API
        # (the best you can do is download a modified version), so do it via the studies API.
        # KeepSource=false needed to stop it making a copy
        # https://orthanc.uclouvain.be/api/index.html#tag/Studies/paths/~1studies~1{id}~1modify/post
        response = await self._post(
            f"/studies/{study_id}/modify",
            {
                "PrivateCreator": private_creator,
                "Permissive": False,
                "Replace": tag_replacement,
                "Asynchronous": True,
                "Force": True,
                "Keep": ["StudyInstanceUID", "SeriesInstanceUID", "SOPInstanceUID"],
                "Timeout": self.dicom_timeout,
            },
        )
        logger.debug("Modify studies Job: {}", response)
        job_id = str(response["ID"])
        await self.wait_for_job_success_or_raise(job_id, "modify", timeout=self.dicom_timeout)

    async def retrieve_study_from_remote(self, query_id: str) -> str:
        response = await self._post(
            f"/queries/{query_id}/retrieve",
            data={"TargetAet": self.aet, "Synchronous": False, "Timeout": self.dicom_timeout},
        )
        return str(response["ID"])

    async def retrieve_instances_from_remote(
        self, modality: str, missing_instances: list[dict[str, str]]
    ) -> str:
        """Retieve missing instances from remote modality in a single c-move query."""
        response = await self._post(
            f"/modalities/{modality}/move",
            data={
                "Level": "Instance",
                "TargetAet": self.aet,
                "Synchronous": False,
                "Resources": missing_instances,
                "Timeout": self.dicom_timeout,
            },
        )
        return str(response["ID"])

    async def get_jobs(self) -> Any:
        """Get expanded details for all jobs."""
        return await self._get("/jobs?expand")

    async def wait_for_job_success_or_raise(self, job_id: str, job_type: str, timeout: int) -> None:
        """Wait for job to complete successfully, or raise exception if fails or exceeds timeout."""
        job_info = {"State": "Pending"}
        start_time = time()

        while job_info["State"] != "Success":
            if job_info["State"] == "Failure":
                msg = (
                    "Job failed: "
                    f"Error code={job_info['ErrorCode']} Cause={job_info['ErrorDescription']}"
                )
                raise PixlDiscardError(msg)
            if job_type == "modify":
                logger.debug("Modify job: {}", job_info)
            if (time() - start_time) > timeout:
                msg = f"Failed to finish {job_type} job {job_id} in {timeout} seconds"
                await sleep(10)
                raise PixlDiscardError(msg)
            await sleep(10)
            if job_info["State"] == "Pending":
                start_time = time()
            job_info = await self.job_state(job_id=job_id)

    async def job_state(self, job_id: str) -> Any:
        """Get job state from orthanc."""
        # See: https://book.orthanc-server.com/users/advanced-rest.html#jobs-monitoring
        return await self._get(f"/jobs/{job_id}")

    async def _get(self, path: str) -> Any:
        async with (
            aiohttp.ClientSession() as session,
            session.get(
                f"{self._url}{path}",
                auth=self._auth,
                timeout=self.http_timeout,
            ) as response,
        ):
            return await _deserialise(response)

    async def _post(self, path: str, data: dict, timeout: int | None = None) -> Any:
        # Optionally override default http timeout
        http_timeout = timeout or self.http_timeout
        async with (
            aiohttp.ClientSession() as session,
            session.post(
                f"{self._url}{path}", json=data, auth=self._auth, timeout=http_timeout
            ) as response,
        ):
            return await _deserialise(response)

    async def delete(self, path: str) -> None:
        async with (
            aiohttp.ClientSession() as session,
            session.delete(
                f"{self._url}{path}", auth=self._auth, timeout=self.http_timeout
            ) as response,
        ):
            await _deserialise(response)


async def _deserialise(response: aiohttp.ClientResponse) -> Any:
    """Decode an Orthanc rest API response"""
    response.raise_for_status()
    return await response.json()


class PIXLRawOrthanc(Orthanc):
    """Orthanc Raw connection."""

    def __init__(self) -> None:
        super().__init__(
            url=config("ORTHANC_RAW_URL"),
            username=config("ORTHANC_RAW_USERNAME"),
            password=config("ORTHANC_RAW_PASSWORD"),
            http_timeout=config("PIXL_QUERY_TIMEOUT", default=10, cast=int),
            dicom_timeout=config("PIXL_DICOM_TRANSFER_TIMEOUT", default=240, cast=int),
            aet=config("ORTHANC_RAW_AE_TITLE"),
        )

        self.autoroute_to_anon = config("ORTHANC_AUTOROUTE_RAW_TO_ANON", default=False, cast=bool)

    async def raise_if_pending_jobs(self) -> None:
        """
        Raise PixlRequeueMessageError if there are pending jobs on the server.

        Otherwise orthanc starts to get buggy when there are a whole load of pending jobs.
        PixlRequeueMessageError will cause the rabbitmq message to be requeued
        """
        jobs = await self.get_jobs()
        unfinished_jobs = [x for x in jobs if x["State"] not in ("Success", "Failure")]
        for job in unfinished_jobs:
            logger.trace(
                "{}, {}, {}, {}, {}",
                job["State"],
                job.get("CreationTime"),
                job.get("ID"),
                job.get("Type"),
                job.get("EffectiveRuntime"),
            )
        for job in jobs:
            if job["State"] == "Pending":
                msg = "Pending messages in orthanc raw"
                raise PixlRequeueMessageError(msg)

    async def send_study_to_anon(self, resource_id: str) -> Any:
        """Send study to orthanc anon."""
        response = await self._post(
            "/modalities/PIXL-Anon/store",
            data={
                "Resources": [resource_id],
                "Asynchronous": True,
                "Timeout": self.dicom_timeout,
            },
        )

        logger.debug("Successfully triggered c-store of study to anon modality: {}", resource_id)
        return str(response["ID"])


class PIXLAnonOrthanc(Orthanc):
    """Orthanc Anon connection."""

    def __init__(self) -> None:
        super().__init__(
            url=config("ORTHANC_ANON_URL"),
            username=config("ORTHANC_ANON_USERNAME"),
            password=config("ORTHANC_ANON_PASSWORD"),
            http_timeout=config("PIXL_QUERY_TIMEOUT", default=10, cast=int),
            dicom_timeout=config("PIXL_DICOM_TRANSFER_TIMEOUT", default=240, cast=int),
            aet=config("ORTHANC_ANON_AE_TITLE"),
        )

        self.autoroute_to_endpoint = config(
            "ORTHANC_AUTOROUTE_ANON_TO_ENDPOINT", default=False, cast=bool
        )

    async def notify_anon_to_retrieve_study(
        self, orthanc_raw: PIXLRawOrthanc, resource_id: str
    ) -> Any:
        """
        Notify Orthanc Anon of a study to retrieve from Orthanc Raw

        - Query Orthanc Raw for the study
        - Send the StudyInstanceUID and the query ID to Orthanc Anon
        """
        orthanc_raw_study_info = await orthanc_raw.query_local_study(study_id=resource_id)
        study_uid = orthanc_raw_study_info["MainDicomTags"]["StudyInstanceUID"]

        data = {
            "Level": "Study",
            "Query": {
                "StudyInstanceUID": study_uid,
            },
        }
        query_id = await self.query_remote(modality="PIXL-Raw", data=data)
        if query_id is None:
            logger.info(f"No unique study found in Orthanc Raw with StudyInstanceUID: {study_uid}.")
            return

        logger.info("Importing study {} from raw to anon", study_uid)

        # Don't wait for Orthanc Anon to finish processing the study.
        # We still need to await the function otherwise the task is not added to the event loop.
        # We could create the task with asyncio.create_task but a timeout error is still raised.
        with contextlib.suppress(asyncio.TimeoutError):
            await self._post(
                path="/import-from-raw",
                data={"StudyInstanceUID": study_uid, "QueryID": query_id},
            )

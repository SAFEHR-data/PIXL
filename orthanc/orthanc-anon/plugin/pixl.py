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
"""
Applies anonymisation scheme to datasets

This module:
-Modifies a DICOM instance received by Orthanc and applies anonymisation
-Upload the resource to a dicom-web server
"""

from __future__ import annotations

import json
import os
import threading
import traceback
from collections import defaultdict
from io import BytesIO
from time import sleep
from typing import TYPE_CHECKING, cast
from zipfile import ZipFile

import pika
import pydicom
import requests
from core.exceptions import PixlDiscardError, PixlSkipInstanceError
from core.metrics import (
    record_instance_deidentification_failure,
    record_study_deidentification_failure,
)
from core.project_config.pixl_config_model import load_project_config
from core.queue.subscriber import AnonymisationPixlConsumer
from core.telemetry import configure_logging, configure_metrics, configure_tracing
from decouple import config
from loguru import logger
from opentelemetry import trace
from opentelemetry.propagate import extract, inject
from opentelemetry.instrumentation.pika import PikaInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from pixl_dcmd._database import engine as pixl_db_engine
from pixl_dcmd._database import record_skip_reasons_for_study
from pixl_dcmd.dicom_helpers import get_study_info
from pixl_dcmd.main import (
    anonymise_dicom_and_update_db,
    get_series_to_skip,
    parse_validation_results,
    write_dataset_to_bytes,
)
from pydicom import dcmread
from sqlalchemy.exc import DBAPIError
import multiprocessing
import signal

import orthanc

if TYPE_CHECKING:
    from typing import Any

    from core.project_config.pixl_config_model import PixlConfig
    from core.queue.models import AnonymisationMessage
    from opentelemetry.context import Context
    from pixl_dcmd.dicom_helpers import StudyInfo

ORTHANC_USERNAME = config("ORTHANC_USERNAME")
ORTHANC_PASSWORD = config("ORTHANC_PASSWORD")
ORTHANC_URL = "http://localhost:8042"

ORTHANC_RAW_USERNAME = config("ORTHANC_RAW_USERNAME")
ORTHANC_RAW_PASSWORD = config("ORTHANC_RAW_PASSWORD")
ORTHANC_RAW_URL = "http://orthanc-raw:8042"

EXPORT_API_URL = "http://export-api:8000"

# Set up logging as main entry point
logging_level = config("LOG_LEVEL", default="INFO")
configure_logging(level=logging_level)

# Set up tracing to to correlate logs and traces.
# pixl_dcmd creates its SQLAlchemy engine at import time, so the engine must be
# passed explicitly to the instrumentor
configure_tracing()
SQLAlchemyInstrumentor().instrument(engine=pixl_db_engine)
RequestsInstrumentor().instrument()
# orthanc-anon runs as a plugin inside Orthanc rather than via `opentelemetry-instrument`,
# so pika isn't auto-instrumented and we need to do it explicitly to pick up the trace
# context propagated from the message publisher.
PikaInstrumentor().instrument()
tracer = trace.get_tracer("pixl.orthanc_anon")

configure_metrics()

logger.warning("Running logging at level {}", logging_level)

# Set up a multiprocessing pool for non-blocking calls to Orthanc.
# The pool itself is created at the bottom of this module, after the worker
# functions are defined: ForkPool workers are snapshotted at Pool() time, so
# they would not see later `def`s (pickle looks up functions by name).
max_workers = config("PIXL_MAX_MESSAGES_IN_FLIGHT", cast=int)


def child_process_initializer():
    # Ignore CTRL+C in the child processes
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def AzureAccessToken() -> str:
    """
    Send payload to oath2/token url and
    return the response
    """
    AZ_DICOM_ENDPOINT_CLIENT_ID = config("AZ_DICOM_ENDPOINT_CLIENT_ID")
    AZ_DICOM_ENDPOINT_CLIENT_SECRET = config("AZ_DICOM_ENDPOINT_CLIENT_SECRET")
    AZ_DICOM_ENDPOINT_TENANT_ID = config("AZ_DICOM_ENDPOINT_TENANT_ID")

    url = "https://login.microsoft.com/" + AZ_DICOM_ENDPOINT_TENANT_ID + "/oauth2/token"

    payload = {
        "client_id": AZ_DICOM_ENDPOINT_CLIENT_ID,
        "grant_type": "client_credentials",
        "client_secret": AZ_DICOM_ENDPOINT_CLIENT_SECRET,
        "resource": "https://dicom.healthcareapis.azure.com",
    }

    response = requests.post(url, data=payload, timeout=10)

    response_json = response.json()
    # We may wish to make use of the "expires_in" (seconds) value
    # to refresh this token less aggressively
    return cast("str", response_json["access_token"])


TIMER = None


def AzureDICOMTokenRefresh() -> None:
    """
    Refresh Azure DICOM token
    If this fails then wait 30s and try again
    If successful then access_token can be used in
    dicomweb_config to update DICOMweb token through API call
    """
    global TIMER
    TIMER = None

    orthanc.LogWarning("Refreshing Azure DICOM token")

    AZ_DICOM_TOKEN_REFRESH_SECS = int(config("AZ_DICOM_TOKEN_REFRESH_SECS"))
    AZ_DICOM_ENDPOINT_NAME = config("AZ_DICOM_ENDPOINT_NAME")
    AZ_DICOM_ENDPOINT_URL = config("AZ_DICOM_ENDPOINT_URL")
    AZ_DICOM_HTTP_TIMEOUT = int(config("HTTP_TIMEOUT"))

    try:
        access_token = AzureAccessToken()
    except Exception:  # noqa: BLE001
        orthanc.LogError(
            "Failed to get an Azure access token. Retrying in 30 seconds\n" + traceback.format_exc()
        )
        sleep(30)
        return AzureDICOMTokenRefresh()

    bearer_str = "Bearer " + access_token

    dicomweb_config = {
        "Url": AZ_DICOM_ENDPOINT_URL,
        "HttpHeaders": {
            # downstream auth token
            "Authorization": bearer_str,
        },
        "HasDelete": True,
        "Timeout": AZ_DICOM_HTTP_TIMEOUT,
    }

    headers = {"content-type": "application/json"}

    url = ORTHANC_URL + "/dicom-web/servers/" + AZ_DICOM_ENDPOINT_NAME
    # dynamically defining an DICOMWeb endpoint in Orthanc

    try:
        requests.put(
            url,
            auth=(ORTHANC_USERNAME, ORTHANC_PASSWORD),
            headers=headers,
            data=json.dumps(dicomweb_config),
            timeout=10,
        )
    except requests.exceptions.RequestException as e:
        orthanc.LogError("Failed to update DICOMweb token")
        raise SystemExit(e)  # noqa: B904

    orthanc.LogWarning("Updated DICOMweb token")

    TIMER = threading.Timer(AZ_DICOM_TOKEN_REFRESH_SECS, AzureDICOMTokenRefresh)
    TIMER.start()
    return None


def should_export() -> bool:
    """
    Checks whether ORTHANC_AUTOROUTE_ANON_TO_ENDPOINT environment variable is
    set to true or false
    """
    logger.trace("Checking value of autoroute")
    return os.environ.get("ORTHANC_AUTOROUTE_ANON_TO_ENDPOINT", "false").lower() == "true"


def _azure_available() -> bool:
    # Check if AZ_DICOM_ENDPOINT_CLIENT_ID is set
    return config("AZ_DICOM_ENDPOINT_CLIENT_ID", default="") != ""


def OnChange(changeType, level, resource):  # noqa: ARG001
    """
    - If `should_export` returns `false`, the do nothing
    - Otherwise:
        - If orthanc has started then start a timer to refresh the Azure token every 30 seconds
        - If orthanc has stopped then cancel the timer
    """
    if not should_export():
        return

    if changeType == orthanc.ChangeType.ORTHANC_STARTED and _azure_available():
        orthanc.LogWarning("Starting the scheduler")
        AzureDICOMTokenRefresh()
    elif changeType == orthanc.ChangeType.ORTHANC_STOPPED:
        if TIMER is not None:
            orthanc.LogWarning("Stopping the scheduler")
            TIMER.cancel()


def OnHeartBeat(output, uri, **request) -> Any:  # noqa: ARG001
    """Extends the REST API by registering a new route in the REST API"""
    orthanc.LogInfo("OK")
    output.AnswerBuffer("OK\n", "text/plain")


def process_anonymisation_message(
    message: AnonymisationMessage, parent_context: Context
) -> None:
    """
    Import studies from Orthanc Raw.

    Offload to a multiprocessing pool to avoid blocking the Orthanc main thread.

    :param parent_context: Trace context extracted from the queue message headers by
        AnonymisationPixlConsumer, to continue the trace from the message's publisher.
    """

    def on_success(anonymised_study_uids: set[str]) -> None:
        try:
            _notify_export_of_anonymised_studies(anonymised_study_uids, message)
        except Exception:  # noqa: BLE001
            logger.exception(
                "Failed to notify export-api after anonymising studies {}",
                message.resource_ids,
            )

    # OpenTelemetry Context objects contain thread locks and cannot be pickled
    # across the process boundary, so serialise the trace onto a dict carrier.
    trace_carrier: dict[str, str] = {}
    inject(trace_carrier, context=parent_context)

    POOL.apply_async(
        _pull_and_anonymise_study,
        (
            message.resource_ids,
            message.study_uids,
            message.project_name,
            message.series_uids,
            trace_carrier,
        ),
        callback=on_success,
        error_callback=_log_anonymisation_worker_error,
    )


def _notify_export_of_anonymised_studies(
    anonymised_study_uids: set[str] | None,
    message: AnonymisationMessage,
) -> None:
    """Look up Orthanc resource IDs and notify export-api. Must run in the parent process."""
    if not anonymised_study_uids:
        return

    # ensure we only have unique resource ids by using a set
    anonymised_study_uid_by_resource_ids = {
        _get_study_resource_id(anonymised_study_uid): anonymised_study_uid
        for anonymised_study_uid in anonymised_study_uids
    }

    logger.debug(
        "Notify export API to retrieve study resources. Original UID {} Anon UID: {}",
        message.resource_ids,
        list(anonymised_study_uid_by_resource_ids.values()),
    )

    for resource_id, anonymised_study_uid in anonymised_study_uid_by_resource_ids.items():
        with logger.contextualize(
            pseudo_study_uid=anonymised_study_uid,
            orthanc_resource_id=resource_id,
        ):
            send_study(study_id=resource_id, project_name=message.project_name)


def _log_anonymisation_worker_error(error: BaseException) -> None:
    logger.opt(exception=error).error("Anonymisation worker failed")


RABBITMQ_RECONNECT_DELAY_SECONDS = 5


def consume_anonymisation_queue() -> None:
    """
    Consume anonymisation requests from RabbitMQ and submit them for processing.

    Runs for the lifetime of the process. AnonymisationPixlConsumer only retries the
    initial connection; if RabbitMQ becomes unavailable afterwards (e.g. a restart),
    pika.BlockingConnection raises out of consumer.run() and would otherwise kill this
    thread permanently, since nothing else restarts it. So reconnect here instead.
    """
    while True:
        try:
            with AnonymisationPixlConsumer(
                queue_name="anonymisation",
                callback=process_anonymisation_message,
            ) as consumer:
                consumer.run()
        except pika.exceptions.AMQPConnectionError:
            logger.exception(
                "Anonymisation consumer lost connection to RabbitMQ; reconnecting in {} seconds",
                RABBITMQ_RECONNECT_DELAY_SECONDS,
            )
            sleep(RABBITMQ_RECONNECT_DELAY_SECONDS)


def _pull_and_anonymise_study(
    study_resource_ids: list[str],
    study_uids: list[str],
    project_name: str,
    series_to_keep: list[str],
    trace_carrier: dict[str, str],
) -> set[str]:
    """
    Import studies from Orthanc Raw.

    Args:
        study_resource_ids: Resource IDs of the study in Orthanc Raw
        project_name: Name of the project
        trace_carrier: W3C trace context injected by the parent process, to continue the trace

    - Pull studies from Orthanc Raw based on its resource ID
    - Iterate over instances and anonymise them
    - Upload the studies to orthanc-anon
    - Return the anonymised StudyInstanceUIDs so the parent process can notify export-api

    """
    parent_context = extract(trace_carrier)
    # Continue the trace from the incoming request and bind the project to every log within it.
    with (
        tracer.start_as_current_span(name="import_studies_from_raw", context=parent_context),
        logger.contextualize(project_name=project_name),
    ):
        anonymised_study_uids = []

        for study_resource_id, study_uid in zip(study_resource_ids, study_uids, strict=False):
            with logger.contextualize(study_uid=study_uid, orthanc_resource_id=study_resource_id):
                logger.debug("Processing project '{}', study '{}' ", project_name, study_uid)
                anonymised_uid = _anonymise_study_and_upload(
                    study_resource_id, project_name, series_to_keep
                )
                if anonymised_uid:
                    anonymised_study_uids.append(anonymised_uid)

        if not should_export():
            logger.info(
                "Not exporting anonymised studies {} as auto-routing is disabled",
                anonymised_study_uids,
            )
            return set()
        return set(anonymised_study_uids)

def _anonymise_study_and_upload(
    study_resource_id: str,
    project_name: str,
    series_to_keep: list[str],
) -> str | None:
    zipped_study_bytes = get_study_zip_archive_from_raw(resource_id=study_resource_id)

    study_info = _get_study_info_from_first_file(zipped_study_bytes)
    with (
        tracer.start_as_current_span(name="anonymise_study"),
        logger.contextualize(
            mrn=study_info.mrn,
            accession_number=study_info.accession_number,
            study_uid=study_info.study_uid,
        ),
    ):
        logger.info("Processing project '{}', {}", project_name, study_info)

        with ZipFile(zipped_study_bytes) as zipped_study:
            try:
                anonymised_instances_bytes, anonymised_study_uid = _anonymise_study_instances(
                    zipped_study=zipped_study,
                    study_info=study_info,
                    project_name=project_name,
                    series_to_keep=series_to_keep,
                )
            except PixlDiscardError as discard:
                logger.warning(
                    "Failed to anonymize project: '{}', {}: {}", project_name, study_info, discard
                )
                record_study_deidentification_failure(
                    project_name=project_name,
                    failure_type="PixlDiscardError",
                    message="All instances have been skipped",
                )
                return None
            except DBAPIError as e:
                logger.exception(
                    "Failed to anonymize project: '{}', {}: {}", project_name, study_info, e
                )
                # Keep only the first line of the error message as otherwise the message contains
                # the entire SQL query that failed. This would make the message have too high
                # cardinality for the metric to be useful, and would make it hard to query for
                # specific failure messages.
                record_study_deidentification_failure(
                    project_name=project_name,
                    failure_type=type(e.orig).__name__,
                    message=str(e.orig).splitlines()[0],
                )
                return None
            except Exception as e:  # noqa: BLE001
                logger.exception("Failed to anonymize project: '{}', {}", project_name, study_info)
                record_study_deidentification_failure(
                    project_name=project_name,
                    failure_type=type(e).__name__,
                    message=str(e).splitlines()[0],
                )
                return None

        with logger.contextualize(pseudo_study_uid=anonymised_study_uid):
            _upload_instances(anonymised_instances_bytes)
            logger.success("Anonymised and uploaded study '{}', {}", project_name, study_info)

        return anonymised_study_uid


def get_study_zip_archive_from_raw(resource_id: str) -> BytesIO:
    """Download zip archive of study resource from Orthanc Raw."""
    query = f"{ORTHANC_RAW_URL}/studies/{resource_id}/archive"
    response = requests.get(
        query,
        auth=(config("ORTHANC_RAW_USERNAME"), config("ORTHANC_RAW_PASSWORD")),
        timeout=config("PIXL_DICOM_TRANSFER_TIMEOUT", default=180, cast=int),
    )
    response.raise_for_status()
    logger.debug("Downloaded data for resource {} from Orthanc Raw", resource_id)
    return BytesIO(response.content)


def _get_study_info_from_first_file(zipped_study_bytes) -> StudyInfo:
    with ZipFile(zipped_study_bytes) as zipped_study:
        file_info = zipped_study.infolist()[0]
        with zipped_study.open(file_info) as file:
            dataset = dcmread(file)
            return get_study_info(dataset)


def _anonymise_study_instances(
    zipped_study: ZipFile,
    study_info: StudyInfo,
    project_name: str,
    series_to_keep: list[str],
) -> tuple[list[bytes], str]:
    """
    Iterate over all instances and anonymise them.

    Skip an instance if a PixlSkipInstanceError is raised during anonymisation.

    Return a list of the bytes of anonymised instances, and the anonymised StudyInstanceUID.
    """
    config = load_project_config(project_name)
    series_to_skip = get_series_to_skip(zipped_study, config.min_instances_per_series)
    anonymised_instances_bytes = []
    skipped_instance_counts = defaultdict(int)
    dicom_validation_errors = {}

    for file_info in zipped_study.infolist():
        with zipped_study.open(file_info) as file:
            logger.debug("Reading file {}", file)
            dataset = dcmread(file)

            if series_to_keep and dataset.SeriesInstanceUID not in series_to_keep:
                logger.debug(
                    "Skipping series {} for study {} as series not in series_to_keep",
                    dataset.SeriesInstanceUID,
                    study_info,
                )
                key = "DICOM instance discarded as series not requested"
                skipped_instance_counts[key] += 1
                record_instance_deidentification_failure(
                    project_name=project_name,
                    study_uid=study_info.study_uid,
                    failure_type="PixlSkipSeriesError",
                    message=key,
                )
                continue

            if dataset.SeriesInstanceUID in series_to_skip:
                logger.debug(
                    "Skipping series {} for study {} due to too few instances",
                    dataset.SeriesInstanceUID,
                    study_info,
                )
                key = "DICOM instance discarded as series has too few instances"
                skipped_instance_counts[key] += 1
                record_instance_deidentification_failure(
                    project_name=project_name,
                    study_uid=study_info.study_uid,
                    failure_type="PixlSkipSeriesError",
                    message=key,
                )
                continue

            try:
                anonymised_instance, instance_validation_errors = _anonymise_dicom_instance(
                    dataset, config
                )
            except PixlSkipInstanceError as e:
                logger.debug(
                    "Skipping instance {} for {}: {}",
                    dataset[0x0008, 0x0018].value,
                    study_info,
                    e,
                )
                skipped_instance_counts[str(e)] += 1
                record_instance_deidentification_failure(
                    project_name=project_name,
                    study_uid=study_info.study_uid,
                    failure_type="PixlSkipInstanceError",
                    message=str(e),
                )
            else:
                anonymised_instances_bytes.append(anonymised_instance)
                anonymised_study_uid = dataset[0x0020, 0x000D].value
                dicom_validation_errors |= instance_validation_errors

    if not anonymised_instances_bytes:
        message = f"All instances have been skipped for study: {dict(skipped_instance_counts)}"
        try:
            record_skip_reasons_for_study(
                project_slug=project_name,
                study_info=study_info,
                skip_reasons=dict(skipped_instance_counts),
            )
        except PixlDiscardError as e:
            raise PixlDiscardError(message) from e
        # Still raise the exception message
        raise PixlDiscardError(message)

    with logger.contextualize(pseudo_study_uid=anonymised_study_uid):
        logger.debug(
            "Project '{}' {}, skipped instances: {}",
            project_name,
            study_info,
            dict(skipped_instance_counts),
        )

        if dicom_validation_errors:
            logger.warning(
                "The anonymisation introduced the following validation errors:\n{}",
                parse_validation_results(dicom_validation_errors),
            )
        logger.info("Finished anonymising project '{}', {}", project_name, study_info)
    return anonymised_instances_bytes, anonymised_study_uid


def _anonymise_dicom_instance(dataset: pydicom.Dataset, config: PixlConfig) -> tuple[bytes, dict]:
    """Anonymise a DICOM instance."""
    validation_errors = anonymise_dicom_and_update_db(dataset, config=config)
    return write_dataset_to_bytes(dataset), validation_errors


def _upload_instances(instances_bytes: list[bytes]) -> None:
    """Upload instances to Orthanc"""
    files = []
    for index, dicom_bytes in enumerate(instances_bytes):
        files.append(("file", (f"instance{index}.dcm", dicom_bytes, "application/dicom")))

    # Using requests as doing:
    # `upload_response = orthanc.RestApiPost(f"/instances", anonymised_files)`
    # gives an error BadArgumentType error (orthanc.RestApiPost seems to only accept json)
    upload_response = requests.post(
        url=f"{ORTHANC_URL}/instances",
        auth=(ORTHANC_USERNAME, ORTHANC_PASSWORD),
        files=files,
        timeout=config("PIXL_DICOM_TRANSFER_TIMEOUT", default=180, cast=int),
    )
    upload_response.raise_for_status()


def _get_study_resource_id(study_uid: str) -> str:
    """
    Get the resource ID for an existing study based on its StudyInstanceUID.

    Returns None if there are no resources with the given StudyInstanceUID.
    Returns the resource ID if there is a single resource with the given StudyInstanceUID.
    Returns None if there are multiple resources with the given StudyInstanceUID and deletes
    the studies.
    """
    data = json.dumps(
        {
            "Level": "Study",
            "Query": {
                "StudyInstanceUID": study_uid,
            },
        }
    )
    # TODO run in main process
    study_resource_ids = json.loads(orthanc.RestApiPost("/tools/find", data))
    if not study_resource_ids:
        message = f"No study found with StudyInstanceUID {study_uid}"
        raise ValueError(message)
    if len(study_resource_ids) > 1:
        message = f"Multiple studies found with StudyInstanceUID {study_uid}"
        raise ValueError(message)

    return study_resource_ids[0]


def send_study(study_id: str, project_name: str) -> None:
    """
    Send the resource to the appropriate destination.
    Throws an exception if the image has already been exported.
    """
    logger.debug("Sending {}", study_id)
    notify_export_api_of_readiness(study_id, project_name)


def notify_export_api_of_readiness(study_id: str, project_name: str) -> None:
    """
    Tell export-api that our data is ready and it should download it from us and upload
    as appropriate
    """
    url = EXPORT_API_URL + "/export-dicom-from-orthanc"
    payload = {"study_id": study_id, "project_name": project_name}
    timeout: float = config("HTTP_TIMEOUT", default=30, cast=float)
    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()


# Create the pool only once functions are defined in this module.
POOL = multiprocessing.Pool(4, initializer=child_process_initializer)
logger.info("Using {} processes for anonymisation", max_workers)

consumer_thread = threading.Thread(
    target=consume_anonymisation_queue,
    daemon=True,
)
consumer_thread.start()

orthanc.RegisterOnChangeCallback(OnChange)
orthanc.RegisterRestCallback("/heart-beat", OnHeartBeat)

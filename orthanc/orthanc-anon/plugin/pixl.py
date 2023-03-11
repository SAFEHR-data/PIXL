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
import os
import traceback
from decouple import config
from io import BytesIO

from time import sleep
from pydicom import dcmread, dcmwrite
from pydicom.filebase import DicomFileLike

import hashlib
import json
import orthanc
import pprint
import requests
import sys
import threading
import yaml

import logging 

import pixl_dcmd

def AzureAccessToken():

    AZ_DICOM_ENDPOINT_CLIENT_ID = config('AZ_DICOM_ENDPOINT_CLIENT_ID')
    AZ_DICOM_ENDPOINT_CLIENT_SECRET = config('AZ_DICOM_ENDPOINT_CLIENT_SECRET')
    AZ_DICOM_ENDPOINT_TENANT_ID = config('AZ_DICOM_ENDPOINT_TENANT_ID')

    url = "https://login.microsoft.com/" + AZ_DICOM_ENDPOINT_TENANT_ID \
    + "/oauth2/token"

    payload = {
        'client_id': AZ_DICOM_ENDPOINT_CLIENT_ID,
        'grant_type': 'client_credentials',
        'client_secret': AZ_DICOM_ENDPOINT_CLIENT_SECRET,
        'resource': 'https://dicom.healthcareapis.azure.com'
    }

    response = requests.post(url, data=payload)
    #logging.info(f"{payload}")
    #logging.info(f"{response.content}")

    access_token = response.json()["access_token"]
    return access_token

def AzureDICOMTokenRefresh():
    global TIMER
    TIMER = None

    orthanc.LogWarning("Refreshing Azure DICOM token")

    ORTHANC_USERNAME = config('ORTHANC_USERNAME')
    ORTHANC_PASSWORD = config('ORTHANC_PASSWORD')

    AZ_DICOM_TOKEN_REFRESH_SECS = int(config('AZ_DICOM_TOKEN_REFRESH_SECS'))
    AZ_DICOM_ENDPOINT_NAME = config('AZ_DICOM_ENDPOINT_NAME')
    AZ_DICOM_ENDPOINT_URL = config('AZ_DICOM_ENDPOINT_URL')
    AZ_DICOM_HTTP_TIMEOUT = int(config('HTTP_TIMEOUT'))

    try:
        access_token = AzureAccessToken()
        # logging.info(f"{access_token}")
    except Exception:
        orthanc.LogError("Failed to get an Azure access token. Retrying in 30 seconds\n"
                         + traceback.format_exc())
        sleep(30)
        return AzureDICOMTokenRefresh()

    bearer_str = "Bearer " + access_token

    dicomweb_config = {
        "Url" : AZ_DICOM_ENDPOINT_URL,
        "HttpHeaders" : {
          "Authorization" : bearer_str,
        },
        "HasDelete": True,
        "Timeout" : AZ_DICOM_HTTP_TIMEOUT
    }

    #logging.info(f"{dicomweb_config}")

    headers = {'content-type': 'application/json'}

    url = "http://localhost:8042/dicom-web/servers/" + AZ_DICOM_ENDPOINT_NAME

    try:
        requests.put(url, auth=(ORTHANC_USERNAME, ORTHANC_PASSWORD), headers=headers, data=json.dumps(dicomweb_config))
    except requests.exceptions.RequestException as e:
        orthanc.LogError("Failed to update DICOMweb token")
        raise SystemExit(e)

    orthanc.LogWarning("Updated DICOMweb token")

    TIMER = threading.Timer(AZ_DICOM_TOKEN_REFRESH_SECS, AzureDICOMTokenRefresh)
    TIMER.start()

def SendViaStow(resourceId):

    ORTHANC_USERNAME = config('ORTHANC_USERNAME')
    ORTHANC_PASSWORD = config('ORTHANC_PASSWORD')

    AZ_DICOM_ENDPOINT_NAME = config('AZ_DICOM_ENDPOINT_NAME')

    url = "http://localhost:8042/dicom-web/servers/" + AZ_DICOM_ENDPOINT_NAME + "/stow"

    headers = {'content-type': 'application/json'}

    payload = {
        "Resources" : [
            resourceId
        ],
        "Synchronous" : False
    }

    logging.info(f"{payload}")

    try:
        requests.post(url, auth=(ORTHANC_USERNAME, ORTHANC_PASSWORD), headers=headers, data=json.dumps(payload))
    except requests.exceptions.RequestException as e:
        orthanc.LogError("Failed to send via STOW")

def ShouldAutoRoute():
    return os.environ.get("ORTHANC_AUTOROUTE_ANON_TO_AZURE", "false").lower() == "true"

def OnChange(changeType, level, resource):

    if not ShouldAutoRoute():
        return

    if changeType == orthanc.ChangeType.STABLE_STUDY and ShouldAutoRoute():
        print('Stable study: %s' % resource)
        SendViaStow(resource)

    if changeType == orthanc.ChangeType.ORTHANC_STARTED:
        orthanc.LogWarning("Starting the scheduler")
        AzureDICOMTokenRefresh()
    elif changeType == orthanc.ChangeType.ORTHANC_STOPPED:
        if TIMER != None:
            orthanc.LogWarning("Stopping the scheduler")
            TIMER.cancel()

def OnHeartBeat(output, uri, **request):
    orthanc.LogWarning("OK")
    output.AnswerBuffer('OK\n', 'text/plain')

def ReceivedInstanceCallback(receivedDicom, origin):
    """Modifies a DICOM instance received by Orthanc and applies anonymisation."""

    if origin == orthanc.InstanceOrigin.REST_API:
        orthanc.LogWarning('DICOM instance received from the REST API')
    elif origin == orthanc.InstanceOrigin.DICOM_PROTOCOL:
        orthanc.LogWarning('DICOM instance received from the DICOM protocol')
    
    # Read the bytes as DICOM/
    dataset = dcmread(BytesIO(receivedDicom))

    # Drop anything that is not an X-Ray
    if not (dataset.Modality == 'DX' or dataset.Modality == 'CR'):
        orthanc.LogWarning('Dropping DICOM that is not X-Ray')
        return orthanc.ReceivedInstanceAction.DISCARD, None

    # Attempt to anonymise and drop the study if any exceptions occur
    try:
        return AnonymiseCallback(dataset)
    except Exception as e:
        orthanc.LogWarning('Failed to anonymize study due to\n' + traceback.format_exc())
        return orthanc.ReceivedInstanceAction.DISCARD, None


def AnonymiseCallback(dataset):

    orthanc.LogWarning('***Anonymising received instance***')
    # Rip out all private tags/
    dataset.remove_private_tags()
    orthanc.LogWarning('Removed private tags')

    # Rip out overlays/
    dataset = pixl_dcmd.remove_overlays(dataset)
    orthanc.LogWarning('Removed overlays')

    # Apply anonymisation.
    with open('/etc/orthanc/tag-operations.yaml', 'r') as file:
        # Load tag operations scheme from YAML.
        tags = yaml.safe_load(file)
        # Apply scheme to instance
        dataset = pixl_dcmd.apply_tag_scheme(dataset,tags)
        # Apply whitelist
        dataset = pixl_dcmd.enforce_whitelist(dataset,tags)

    # Write anoymised instance to disk.
    return orthanc.ReceivedInstanceAction.MODIFY, pixl_dcmd.write_dataset_to_bytes(dataset)


orthanc.RegisterOnChangeCallback(OnChange)
orthanc.RegisterReceivedInstanceCallback(ReceivedInstanceCallback)
orthanc.RegisterRestCallback('/heart-beat', OnHeartBeat)
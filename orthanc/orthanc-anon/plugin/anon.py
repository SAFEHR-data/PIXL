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
from decouple import config
from io import BytesIO

from pydicom import dcmread, dcmwrite
from pydicom.filebase import DicomFileLike

import hashlib
import orthanc
import pprint
import threading
import yaml

import logging 

import pixl_dcmd

def AzureDICOMTokenRefresh():
    global TIMER
    TIMER = None

    orthanc.LogWarning("Refreshing Azure DICOM token")

    AZ_DICOM_TOKEN_REFRESH_SECS = int(config('AZ_DICOM_TOKEN_REFRESH_SECS'))
    AZ_DICOM_ENDPOINT_CLIENT_ID = config('AZ_DICOM_ENDPOINT_CLIENT_ID')
    AZ_DICOM_ENDPOINT_CLIENT_SECRET = config('AZ_DICOM_ENDPOINT_CLIENT_SECRET')
    AZ_DICOM_ENDPOINT_TENANT_ID = config('AZ_DICOM_ENDPOINT_TENANT_ID')

    #res = requests.post()
    TIMER = threading.Timer(AZ_DICOM_TOKEN_REFRESH_SECS, AzureDICOMTokenRefresh)
    TIMER.start()

def OnChange(changeType, level, resource):
    if changeType == orthanc.ChangeType.ORTHANC_STARTED:
        orthanc.LogWarning("Starting the scheduler")
        AzureDICOMTokenRefresh()

    elif changeType == orthanc.ChangeType.ORTHANC_STOPPED:
        if TIMER != None:
            orthanc.LogWarning("Stopping the scheduler")
            TIMER.cancel()

def ReceivedInstanceCallback(receivedDicom, origin):
    """Modifies a DICOM instance received by Orthanc and applies anonymisation."""

    if origin == orthanc.InstanceOrigin.REST_API:
        orthanc.LogWarning('DICOM instance received from the REST API')
    elif origin == orthanc.InstanceOrigin.DICOM_PROTOCOL:
        orthanc.LogWarning('DICOM instance received from the DICOM protocol')
    
    # Read the bytes as DICOM/
    dataset = dcmread(BytesIO(receivedDicom))

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
    
    # Write anoymised instance to disk.
    return orthanc.ReceivedInstanceAction.MODIFY, pixl_dcmd.write_dataset_to_bytes(dataset)

orthanc.RegisterReceivedInstanceCallback(ReceivedInstanceCallback)
orthanc.RegisterOnChangeCallback(OnChange)
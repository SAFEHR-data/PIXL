from io import BytesIO

from pydicom import dcmread, dcmwrite
from pydicom.filebase import DicomFileLike

import hashlib
import orthanc
import pprint
import yaml

import logging 

import pixl_dcmd

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
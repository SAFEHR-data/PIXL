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

"""Functions to write test DICOM files."""

import importlib
import json

import numpy as np
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.sequence import Sequence


def write_volume(filename_pattern: str):
    """
    Write a volumes worth of fake DICOM images

    Args:
        filename_pattern: The pattern to use for the filenames. This should
        include a {slice} which will be replaced with the slice number e.g.
        /tmp/slice{slice:03d}.dcm

    """
    # dicom_variables.json contains per slice information for a 3D image (geometry, windowing, etc.)
    dicom_variables_path = importlib.resources.files("pytest_pixl").joinpath(
        "data/dicom_variables.json"
    )
    variables = json.loads(dicom_variables_path.open("r").read())
    rng = np.random.default_rng(0)
    for i, slice_info in enumerate(variables):
        write_slice(
            file_name=filename_pattern.format(slice=i),
            pixel_data=rng.random(size=(256, 256)),
            **slice_info,
        )


# Remove the noqa comments once this function takes a sensible number of arguments
# and hard-coded values are moved to JSON
def write_slice(  # noqa: PLR0913, PLR0915
    instance_creation_time: str,
    sop_instance_uid: str,
    instance_number: str,
    image_position_patient: list[float],
    slice_location: float,
    window_centre: str,
    window_width: str,
    pixel_data: np.ndarray,
    file_name: str,
):
    """
    Write a single fake DICOM image

    Elements that vary between slices are exposed as arguments.  Values for
    these can be obtained from the dicom_variables.json file.
    """
    # File meta info data elements
    file_meta = FileMetaDataset()

    # Main data elements
    ds = Dataset()
    ds.SpecificCharacterSet = "ISO_IR 100"
    ds.ImageType = ["ORIGINAL", "PRIMARY", "M_FFE", "M", "FFE"]
    ds.InstanceCreationDate = "20230125"
    ds.InstanceCreationTime = instance_creation_time
    ds.InstanceCreatorUID = "1.3.46.670589.11.89.5"
    ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.4"
    ds.SOPInstanceUID = sop_instance_uid
    ds.StudyDate = "20230101"
    ds.SeriesDate = "20230101"
    ds.AcquisitionDate = "20230101"
    ds.ContentDate = "20230101"
    ds.StudyTime = "170902"
    ds.SeriesTime = "175518.96000"
    ds.AcquisitionTime = "175529.75"
    ds.ContentTime = "175529.75"
    ds.AccessionNumber = "BB01234567"
    ds.Modality = "MR"
    ds.ConversionType = ""
    ds.Manufacturer = "Company"
    ds.InstitutionName = "InstituteNeurology"
    ds.InstitutionAddress = "Some Address"
    ds.ReferringPhysicianName = ""
    ds.CodeValue = ""
    ds.CodingSchemeDesignator = ""
    ds.CodeMeaning = ""
    ds.StationName = "Compary-12345F"
    ds.StudyDescription = "STUDY"
    ds.SeriesDescription = "mri_sequence"
    ds.InstitutionalDepartmentName = "Imaging"
    ds.PerformingPhysicianName = ""
    ds.OperatorsName = ""
    ds.AdmittingDiagnosesDescription = ""
    ds.ManufacturerModelName = "Cool Scanner"

    # Referenced Performed Procedure Step Sequence
    refd_performed_procedure_step_sequence = Sequence()
    ds.ReferencedPerformedProcedureStepSequence = refd_performed_procedure_step_sequence

    # Referenced Performed Procedure Step Sequence: Referenced Performed Procedure Step 1
    refd_performed_procedure_step1 = Dataset()
    refd_performed_procedure_step_sequence.append(refd_performed_procedure_step1)
    refd_performed_procedure_step1.InstanceCreationDate = "20230101"
    refd_performed_procedure_step1.InstanceCreationTime = "170902.041"
    refd_performed_procedure_step1.InstanceCreatorUID = "1.3.46.670589.11.89.5"
    refd_performed_procedure_step1.ReferencedSOPClassUID = "1.2.840.10008.3.1.2.3.3"
    refd_performed_procedure_step1.ReferencedSOPInstanceUID = (
        "1.3.46.670589.11.38023.5.0.14068.2023012517090204001"
    )
    refd_performed_procedure_step1.InstanceNumber = instance_number

    # Referenced Image Sequence
    refd_image_sequence = Sequence()
    ds.ReferencedImageSequence = refd_image_sequence

    # Referenced Image Sequence: Referenced Image 1
    refd_image1 = Dataset()
    refd_image_sequence.append(refd_image1)
    refd_image1.ReferencedSOPClassUID = "1.2.840.10008.5.1.4.1.1.4"
    refd_image1.ReferencedSOPInstanceUID = "1.3.46.670589.11.38023.5.0.7404.2023012517191564042"

    # Referenced Image Sequence: Referenced Image 2
    refd_image2 = Dataset()
    refd_image_sequence.append(refd_image2)
    refd_image2.ReferencedSOPClassUID = "1.2.840.10008.5.1.4.1.1.4"
    refd_image2.ReferencedSOPInstanceUID = "1.3.46.670589.11.38023.5.0.7404.2023012517190467040"

    # Referenced Image Sequence: Referenced Image 3
    refd_image3 = Dataset()
    refd_image_sequence.append(refd_image3)
    refd_image3.ReferencedSOPClassUID = "1.2.840.10008.5.1.4.1.1.4"
    refd_image3.ReferencedSOPInstanceUID = "1.3.46.670589.11.38023.5.0.7404.2023012517185239035"

    ds.PatientName = "BillPatient"
    ds.PatientID = "ID123456"
    ds.PatientBirthDate = "20010101"
    ds.PatientSex = "O"
    ds.PatientAge = "022Y"
    ds.PatientWeight = "85.0"
    ds.MedicalAlerts = ""
    ds.Allergies = ""
    ds.EthnicGroup = ""
    ds.Occupation = ""
    ds.AdditionalPatientHistory = ""
    ds.PregnancyStatus = 4
    ds.PatientComments = ""
    ds.BodyPartExamined = "BRAIN"
    ds.ScanningSequence = "GR"
    ds.SequenceVariant = "MP"
    ds.ScanOptions = "OTHER"
    ds.MRAcquisitionType = "3D"
    ds.SliceThickness = "1.0"
    ds.RepetitionTime = "7.0"
    ds.EchoTime = "3.2"
    ds.NumberOfAverages = "1.0"
    ds.ImagingFrequency = "127.79932"
    ds.ImagedNucleus = "1H"
    ds.EchoNumbers = "1"
    ds.MagneticFieldStrength = "3.0"
    ds.SpacingBetweenSlices = "1.0"
    ds.NumberOfPhaseEncodingSteps = "256"
    ds.EchoTrainLength = "225"
    ds.PercentSampling = "78.5398178100586"
    ds.PercentPhaseFieldOfView = "100.0"
    ds.PixelBandwidth = "256.0"
    ds.DeviceSerialNumber = "38023"
    ds.SecondaryCaptureDeviceID = ""
    ds.SecondaryCaptureDeviceManufacturer = ""
    ds.SecondaryCaptureDeviceManufacturerModelName = ""
    ds.SecondaryCaptureDeviceSoftwareVersions = ""
    ds.SoftwareVersions = ["5.4.0", "5.4.0.0"]
    ds.VideoImageFormatAcquired = ""
    ds.DigitalImageFormatAcquired = ""
    ds.ProtocolName = "Scanning Protocol"
    ds.LowRRValue = "0"
    ds.HighRRValue = "0"
    ds.IntervalsAcquired = "0"
    ds.IntervalsRejected = "0"
    ds.HeartRate = "0"
    ds.ReconstructionDiameter = "256.0"
    ds.ReceiveCoilName = "MULTI COIL"
    ds.AcquisitionMatrix = [0, 256, 256, 0]
    ds.InPlanePhaseEncodingDirection = "ROW"
    ds.FlipAngle = "8.0"
    ds.SAR = "0.01492713019251"
    ds.dBdt = "51.8182716369628"
    ds.B1rms = 0.6147387027740479
    ds.PatientPosition = "HFS"
    ds.AcquisitionDuration = 115.6185302734375
    ds.DiffusionBValue = 0.0
    ds.DiffusionGradientOrientation = [0.0, 0.0, 0.0]
    ds.StudyInstanceUID = "1.3.46.670589.11.38023.5.0.14068.2023012517090166000"
    ds.SeriesInstanceUID = "1.3.46.670589.11.38023.5.0.7404.2023012517551898153"
    ds.StudyID = "727549740"
    ds.SeriesNumber = "901"
    ds.AcquisitionNumber = "9"
    ds.InstanceNumber = "1"
    ds.ImagePositionPatient = image_position_patient
    ds.ImageOrientationPatient = [
        -0.0065220510587,
        0.99990475177764,
        -0.0121616190299,
        0.05751159414649,
        -0.0117666730657,
        -0.9982755184173,
    ]
    ds.FrameOfReferenceUID = "1.3.46.670589.11.38023.5.0.12268.2023012517152734001"
    ds.Laterality = ""
    ds.TemporalPositionIdentifier = "1"
    ds.NumberOfTemporalPositions = "1"
    ds.PositionReferenceIndicator = ""
    ds.SliceLocation = slice_location
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.Rows = 256
    ds.Columns = 256
    ds.PixelSpacing = [1, 1]
    ds.BitsAllocated = 16
    ds.BitsStored = 12
    ds.HighBit = 11
    ds.PixelRepresentation = 0
    ds.WindowCenter = window_centre
    ds.WindowWidth = window_width
    ds.RescaleIntercept = "0.0"
    ds.RescaleSlope = "5.47863247863247"
    ds.RescaleType = "normalized"
    ds.RequestingPhysician = ""
    ds.RequestingService = ""
    ds.RequestedProcedureDescription = ""
    ds.RequestedContrastAgent = ""
    ds.StudyComments = ""
    ds.SpecialNeeds = ""
    ds.PatientState = ""
    ds.ScheduledPerformingPhysicianName = ""
    ds.PerformedStationAETitle = "STATIONAE"
    ds.PerformedStationName = ""
    ds.PerformedLocation = ""
    ds.PerformedProcedureStepStartDate = "20230101"
    ds.PerformedProcedureStepStartTime = "170902"
    ds.PerformedProcedureStepEndDate = "20230101"
    ds.PerformedProcedureStepEndTime = "170902"
    ds.PerformedProcedureStepStatus = ""
    ds.PerformedProcedureStepID = "727549740"
    ds.PerformedProcedureStepDescription = "Step Description"
    ds.PerformedProcedureTypeDescription = ""

    # Performed Protocol Code Sequence
    performed_protocol_code_sequence = Sequence()
    ds.PerformedProtocolCodeSequence = performed_protocol_code_sequence

    # Performed Protocol Code Sequence: Performed Protocol Code 1
    performed_protocol_code1 = Dataset()
    performed_protocol_code_sequence.append(performed_protocol_code1)
    performed_protocol_code1.CodeValue = "UNDEFINED"
    performed_protocol_code1.CodingSchemeDesignator = "UNDEFINED"
    performed_protocol_code1.CodeMeaning = "UNDEFINED"
    performed_protocol_code1.ContextGroupExtensionFlag = "N"

    ds.CommentsOnThePerformedProcedureStep = ""
    ds.RequestedProcedureID = ""
    ds.ReasonForTheRequestedProcedure = ""
    ds.RequestedProcedurePriority = ""
    ds.PatientTransportArrangements = ""
    ds.RequestedProcedureLocation = ""
    ds.RequestedProcedureComments = ""
    ds.ReasonForTheImagingServiceRequest = ""
    ds.IssueDateOfImagingServiceRequest = "20230101"
    ds.IssueTimeOfImagingServiceRequest = "170901.666"
    ds.OrderEntererLocation = ""
    ds.OrderCallbackPhoneNumber = ""
    ds.ImagingServiceRequestComments = ""

    # Real World Value Mapping Sequence
    real_world_value_mapping_sequence = Sequence()
    ds.RealWorldValueMappingSequence = real_world_value_mapping_sequence

    # Real World Value Mapping Sequence: Real World Value Mapping 1
    real_world_value_mapping1 = Dataset()
    real_world_value_mapping_sequence.append(real_world_value_mapping1)
    real_world_value_mapping1.LUTExplanation = "Real World Value Mapping for normalized"

    # Measurement Units Code Sequence
    measurement_units_code_sequence = Sequence()
    real_world_value_mapping1.MeasurementUnitsCodeSequence = measurement_units_code_sequence

    # Measurement Units Code Sequence: Measurement Units Code 1
    measurement_units_code1 = Dataset()
    measurement_units_code_sequence.append(measurement_units_code1)
    measurement_units_code1.CodeValue = "1"
    measurement_units_code1.CodingSchemeDesignator = "UCUM"
    measurement_units_code1.CodeMeaning = "no units"
    measurement_units_code1.ContextUID = "1.2.840.10008.6.1.918"

    real_world_value_mapping1.LUTLabel = "Philips"
    real_world_value_mapping1.RealWorldValueLastValueMapped = 4095
    real_world_value_mapping1.RealWorldValueFirstValueMapped = 0
    real_world_value_mapping1.RealWorldValueIntercept = 0.0
    real_world_value_mapping1.RealWorldValueSlope = 5.478632478632479

    ds.PresentationLUTShape = "IDENTITY"
    ds.PixelData = pixel_data

    ds.file_meta = file_meta
    ds.is_implicit_VR = True
    ds.is_little_endian = True
    ds.save_as(file_name, write_like_original=False)

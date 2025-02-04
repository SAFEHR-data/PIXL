# CXR tags - v1.0.3

The following tables list the DICOM tags with associated operations to produce the whitelist.

## Post-anonymisation

- All private tags will be deleted.
- All data in `(60xx,xxxx)` (Overlays) will be removed.


| Tag         | Attribute                                 | Op |
| ----------- | ----------------------------------------- | -  |
| (0008,0005) | Specific Character Set                    | keep |
| (0008,0008) | Image Type                                | keep |
| (0008,0016) | SOP Class UID                             | keep |
| (0008,0018) | SOP Instance UID                          | change |
| (0008,0020) | Study Date                                | keep |
| (0008,0021) | Series Date                               | keep |
| (0008,0022) | Acquisition Date                          | keep |
| (0008,0023) | Image Date                                | keep |
| (0008,002a) | Acquisition Date Time                     | date-shift |
| (0008,0030) | Study Time                                | date-shift |
| (0008,0031) | Series Time                               | date-shift |
| (0008,0032) | Acquisition Time                          | date-shift |
| (0008,0033) | Image Time                                | date-shift |
| (0008,0050) | Accession Number                          | secure-hash |
| (0008,0060) | Modality                                  | keep |
| (0008,0061) | Modalities In Study                       | keep |
| (0008,0070) | Manufacturer                              | keep |
| (0008,1030) | Study Description                         | keep |
| (0008,103e) | Series Description                        | keep |
| (0008,1090) | Manufacturers Model Name                  | keep |
| (0010,0010) | Patients Name                             | secure-hash |
| (0010,0020) | Patient ID                                | fixed |
| (0010,1010) | Patients Age                              | num-range |
| (0010,1020) | Patients Size                             | keep |
| (0010,1030) | Patients Weight                           | keep |
| (0018,0015) | Body Part Examined                        | keep |
| (0018,0060) | kVp                                       | keep |
| (0018,1020) | Software Version                          | keep |
| (0018,1149) | Field Of View Dimension                   | keep |
| (0018,1150) | Exposure Time                             | keep |
| (0018,1151) | X Ray Tube Current                        | keep |
| (0018,1152) | Exposure                                  | keep |
| (0018,1153) | Exposure In Uas                           | keep |
| (0018,115e) | Image Area Dose Product                   | keep |
| (0018,1164) | Imager Pixel Spacing                      | keep |
| (0018,1166) | Grid                                      | keep |
| (0018,1190) | Focal Spot                                | keep |
| (0018,1400) | Acquisition Device Processing Description | keep |
| (0018,1411) | Exposure Index                            | keep |
| (0018,1412) | Target Exposure Index                     | keep |
| (0018,1413) | Deviation Index                           | keep |
| (0018,1508) | Positioner Type                           | keep |
| (0018,1700) | Collemator Shape                          | keep |
| (0018,1720) | Vertices Of The Polygonal Collimator      | keep |
| (0018,5101) | View Position                             | keep |
| (0018,6000) | Sensitivity                               | keep |
| (0018,7001) | Detector Temperature                      | keep |
| (0018,7004) | Detector Type                             | keep |
| (0018,7005) | Detector Configuration                    | keep |
| (0018,700a) | Detector ID                               | keep |
| (0018,701a) | Detector Binning                          | keep |
| (0018,7020) | Detector Element Physical Size            | keep |
| (0018,7022) | Detector Element Spacing                  | keep |
| (0018,7024) | Detector Active Shape                     | keep |
| (0018,7026) | Detector Active Dimensions                | keep |
| (0018,7030) | Field Of View Origin                      | keep |
| (0018,7032) | Field Of View Rotation                    | keep |
| (0018,7034) | Field Of View Horizontal Flip             | keep |
| (0018,704c) | Grid Focal Distance                       | keep |
| (0018,7060) | Exposure Control Mode                     | keep |
| (0020,000d) | Study Instance UID                        | change |
| (0020,000e) | Series Instance UID                       | change |
| (0020,0010) | Study ID                                  | change |
| (0020,0011) | Series Number                             | keep |
| (0020,0013) | Image Number                              | keep |
| (0020,0020) | Patient Orientation                       | keep |
| (0020,0062) | Image Laterality                          | keep |
| (0028,0002) | Samples Per Pixel                         | keep |
| (0028,0004) | Photometric Interpretation                | keep |
| (0028,0010) | Rows                                      | keep |
| (0028,0011) | Columns                                   | keep |
| (0028,0030) | Pixel Spacing                             | keep |
| (0028,0100) | Bits Allocated                            | keep |
| (0028,0101) | Bits Stored                               | keep |
| (0028,0102) | High Bit                                  | keep |
| (0028,0103) | Pixel Representation                      | keep |
| (0028,0300) | Quality Control Image                     | keep |
| (0028,0301) | Burned In Annotation                      | keep |
| (0028,0a02) | Pixel Spacing Calibration Type            | keep |
| (0028,0a04) | Pixel Spacing Calibration Description     | keep |
| (0028,1040) | Pixel Intensity Relationship              | keep |
| (0028,1041) | Pixel Intensity Relationship Sign         | keep |
| (0028,1050) | Window Center                             | keep |
| (0028,1051) | Window Width                              | keep |
| (0028,1052) | Rescale Intercept                         | keep |
| (0028,1053) | Rescale Slope                             | keep |
| (0028,1054) | Rescale Type                              | keep |
| (0028,1055) | Window Center And Width Explanation       | keep |
| (0028,2110) | Lossy Image Compression                   | keep |
| (0028,3010) | VOI LUT Sequence                          | keep |
| (0054,0220) | View Code Sequence                        | keep |

## All tags

| Tag         | Attribute                                 | Op |
| ----------- | ----------------------------------------- | -  |
| (0008,0005) | Specific Character Set                    | keep |
| (0008,0008) | Image Type                                | keep |
| (0008,0016) | SOP Class UID                             | keep |
| (0008,0018) | SOP Instance UID                          | change |
| (0008,0020) | Study Date                                | keep |
| (0008,0021) | Series Date                               | keep |
| (0008,0022) | Acquisition Date                          | keep |
| (0008,0023) | Image Date                                | keep |
| (0008,002a) | Acquisition Date Time                     | date-shift |
| (0008,0030) | Study Time                                | date-shift |
| (0008,0031) | Series Time                               | date-shift |
| (0008,0032) | Acquisition Time                          | date-shift |
| (0008,0033) | Image Time                                | date-shift |
| (0008,0050) | Accession Number                          | secure-hash |
| (0008,0060) | Modality                                  | keep |
| (0008,0061) | Modalities In Study                       | keep |
| (0008,0068) | Presentation Intent Type                  | delete |
| (0008,0070) | Manufacturer                              | keep |
| (0008,0080) | Institution Name                          | delete |
| (0008,0081) | Institution Address                       | delete |
| (0008,0090) | Referring Physicians Name                 | delete |
| (0008,1010) | Station Name                              | delete |
| (0008,1030) | Study Description                         | keep |
| (0008,103e) | Series Description                        | keep |
| (0008,1040) | Institutional Department Name             | delete |
| (0008,1050) | Performing Physicians Name                | delete |
| (0008,1070) | Operators Name                            | delete |
| (0008,1090) | Manufacturers Model Name                  | keep |
| (0008,1110) | Referenced Study Sequence                 | delete |
| (0008,1120) | Referenced Patient Sequence               | delete |
| (0008,2112) | Source Image Sequence                     | delete |
| (0008,2218) | Anatomic Region Sequence                  | delete |
| (0008,3010) | Irradiation Event UID                     | delete |
| (0010,0010) | Patients Name                             | secure-hash |
| (0010,0020) | Patient ID                                | fixed |
| (0010,0021) | Issuer Of Patient ID                      | delete |
| (0010,0030) | Patients Birth Date                       | delete |
| (0010,0032) | Patients Birth Time                       | delete |
| (0010,0040) | Patients Sex                              | delete |
| (0010,1001) | Other Patient Names                       | delete |
| (0010,1010) | Patients Age                              | num-range |
| (0010,1020) | Patients Size                             | keep |
| (0010,1030) | Patients Weight                           | keep |
| (0010,2000) | Medical Alerts                            | delete |
| (0010,2110) | Contrast Allergies                        | delete |
| (0010,4000) | Patient Comments                          | delete |
| (0011,0010) | Private Creator Data Element              | delete |
| (0018,0015) | Body Part Examined                        | keep |
| (0018,0060) | kVp                                       | keep |
| (0018,1020) | Software Version                          | keep |
| (0018,1030) | Protocol Name                             | delete |
| (0018,1149) | Field Of View Dimension                   | keep |
| (0018,1150) | Exposure Time                             | keep |
| (0018,1151) | X Ray Tube Current                        | keep |
| (0018,1152) | Exposure                                  | keep |
| (0018,1153) | Exposure In Uas                           | keep |
| (0018,115e) | Image Area Dose Product                   | keep |
| (0018,1164) | Imager Pixel Spacing                      | keep |
| (0018,1166) | Grid                                      | keep |
| (0018,1190) | Focal Spot                                | keep |
| (0018,1400) | Acquisition Device Processing Description | keep |
| (0018,1411) | Exposure Index                            | keep |
| (0018,1412) | Target Exposure Index                     | keep |
| (0018,1413) | Deviation Index                           | keep |
| (0018,1508) | Positioner Type                           | keep |
| (0018,1700) | Collemator Shape                          | keep |
| (0018,1720) | Vertices Of The Polygonal Collimator      | keep |
| (0018,5101) | View Position                             | keep |
| (0018,6000) | Sensitivity                               | keep |
| (0018,7001) | Detector Temperature                      | keep |
| (0018,7004) | Detector Type                             | keep |
| (0018,7005) | Detector Configuration                    | keep |
| (0018,700a) | Detector ID                               | keep |
| (0018,701a) | Detector Binning                          | keep |
| (0018,7020) | Detector Element Physical Size            | keep |
| (0018,7022) | Detector Element Spacing                  | keep |
| (0018,7024) | Detector Active Shape                     | keep |
| (0018,7026) | Detector Active Dimensions                | keep |
| (0018,7030) | Field Of View Origin                      | keep |
| (0018,7032) | Field Of View Rotation                    | keep |
| (0018,7034) | Field Of View Horizontal Flip             | keep |
| (0018,704c) | Grid Focal Distance                       | keep |
| (0018,7060) | Exposure Control Mode                     | keep |
| (0020,000d) | Study Instance UID                        | change |
| (0020,000e) | Series Instance UID                       | change |
| (0020,0010) | Study ID                                  | change |
| (0020,0011) | Series Number                             | keep |
| (0020,0013) | Image Number                              | keep |
| (0020,0020) | Patient Orientation                       | keep |
| (0020,0062) | Image Laterality                          | keep |
| (0020,1208) | Number Of Study Related Images            | delete |
| (0028,0002) | Samples Per Pixel                         | keep |
| (0028,0004) | Photometric Interpretation                | keep |
| (0028,0010) | Rows                                      | keep |
| (0028,0011) | Columns                                   | keep |
| (0028,0030) | Pixel Spacing                             | keep |
| (0028,0100) | Bits Allocated                            | keep |
| (0028,0101) | Bits Stored                               | keep |
| (0028,0102) | High Bit                                  | keep |
| (0028,0103) | Pixel Representation                      | keep |
| (0028,0300) | Quality Control Image                     | keep |
| (0028,0301) | Burned In Annotation                      | keep |
| (0028,0a02) | Pixel Spacing Calibration Type            | keep |
| (0028,0a04) | Pixel Spacing Calibration Description     | keep |
| (0028,1040) | Pixel Intensity Relationship              | keep |
| (0028,1041) | Pixel Intensity Relationship Sign         | keep |
| (0028,1050) | Window Center                             | keep |
| (0028,1051) | Window Width                              | keep |
| (0028,1052) | Rescale Intercept                         | keep |
| (0028,1053) | Rescale Slope                             | keep |
| (0028,1054) | Rescale Type                              | keep |
| (0028,1055) | Window Center And Width Explanation       | keep |
| (0028,2110) | Lossy Image Compression                   | keep |
| (0028,3010) | VOI LUT Sequence                          | keep |
| (0038,0300) | Current Patient Location                  | delete |
| (0038,0500) | Patient State                             | delete |
| (0040,0244) | Performed Procedure Start Date            | delete |
| (0040,0245) | Performed Procedure Start Time            | delete |
| (0040,0253) | Performed Procedure Step ID               | delete |
| (0040,0254) | Performed Procedure Step Description      | delete |
| (0040,0260) | Performed Action Item Sequence            | delete |
| (0040,0275) | Request Attributes Sequence               | delete |
| (0040,0555) | Acquisition Context Sequence              | delete |
| (0040,1008) | Confidentiality Code                      | delete |
| (0045,0010) | Private Creator Data Element              | delete |
| (0054,0220) | View Code Sequence                        | keep |
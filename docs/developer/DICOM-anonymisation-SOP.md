# DICOM Anonymisation Standard Operating Procedure (SOP)

## Subject

DICOM Anonymisation SOP for the structured chest X-ray imaging data collected for the PIXL Nasogastric tube study. This SOP explains the procedure for
removing all identifiable data from the DICOM files while maintaining data fidelity. This can be extended to other imaging modalities and other
studies but would require re-validation of the anonymisation process for other scan modalities or anatomical regions.

## Purpose

To establish a standard process for anonymising chest X-ray images prior to use in the research project. Anonymisation protects patient privacy while
allowing data to be used for research purposes.

The criteria for successful anonymisation are:

- Removal of all direct identifiers from the DICOM files
- The process does not interfere with fidelity of data as defined below.
- The process is consistent when repeated, so that:
  - The same project-level unique ids are produced for a specific patient id, regardless of which historical archives the scans are retrieved from.

**Data fidelity** is defined as the faithfulness of the relationship with the original data:

- If there is associated data (e.g. radiology reports) then date or time shifts should be consistent

To ensure **Data fidelity** across modalities:

- Date or time jitters should be matched to ensure they are the same in both the scan (or DICOM) and any accompanying radiology report.
- The process can be repeated in a consistent way across the different modalities.

## Scope

This SOP applies to all research projects at UCLH. The process being used to anonymise the accompanying radiology reports can be found in SOP **ADD
TITLE**.

## Process

1. Set metadata tags as defined for per-project configuration, defaults shown in
2. If scan is isotropic and covers facial region at high resolution, a face removal script may be 
   run to anonymise facial features in image voxels (3D pixels) while maintaining remainder of voxel data integrity. 
   This will be considered on a case-by-case basis.
3. Document anonymisation process (separate SOPs)

## Relevant configuration

The relevant configuration for the orthanc-anon DICOM tag de-identification is
located in PIXL's [project config directory](https://github.com/SAFEHR-data/PIXL/tree/main/projects/configs) and the `tag-operations` sub directory.

### Delete Operations

If a tag isn't defined then it will be removed by default

### Kept without altering

These tags will be kept by default for all projects

| Name | Group | Element |
|----------------------------------------|--------|---------|
| Modality | 0x0008 | 0x0060 |
| Modalities in study | 0x0008 | 0x0061 |
| Manufacturer | 0x0008 | 0x0070 |
| Study Description | 0x0008 | 0x1030 |
| Series Description | 0x0008 | 0x103e |
| Patient Sex| 0x0010 | 0x0040 |


### Regeneration of UIDs

Table 1

| Name | Group | Element |
|----------------------------------------|--------|---------|
| SOP Instance UID | 0x0008 | 0x0018 |
| Study Instance UID | 0x0020 | 0x000d |
| Series Instance UID | 0x0020 | 0x000e |
| Instance Creator UID | 0x0008 | 0x0014 |
| Referenced SOP Instance UID | 0x0008 | 0x1155 |
| Frame of Reference UID | 0x0020 | 0x0052 |
| Synchronization Frame of Reference UID | 0x0020 | 0x0200 |
| Storage Media File-set UID | 0x0088 | 0x0140 |
| Referenced Frame of Reference UID | 0x3006 | 0x0024 |
| Related Frame of Reference UID | 0x3006 | 0x00C2 |
| UID | 0x0040 | 0xA124 |

### Hashing Operations

Hashing is used to replace identifiable data with a unique identifier. The following tags are hashed:

Table 2

| Name | Group | Element |
|----------------------------------------|--------|---------|
| Patient ID | 0x0010 | 0x0020 |

The hashing algorithm is the [BLAKE2](https://en.wikipedia.org/wiki/BLAKE_(hash_function)#BLAKE2) hashing function. 
A per-project salt, and a locally held salt are used. These are stored separately and not included in exports for users.

### Time Shifting Operations

Anonymisation may be performed without removal of dates and times where this can be justified. However, our default will be to remove these data.
This requires either deletion of dates and times from the DICOM file with
linkage on an accession number or similar.

Date and time fields that might be affected this are listed below.

Table 3

| Name | Group | Element |
|---------------------------|--------|---------|
| Study Date | 0x0008 | 0x0020 |
| Series Date | 0x0008 | 0x0021 |
| Acquisition Date | 0x0008 | 0x0022 |
| Image Date | 0x0008 | 0x0023 |
| Acquisition Date Time | 0x0008 | 0x002a |
| Study Time | 0x0008 | 0x0030 |
| Series Time | 0x0008 | 0x0031 |
| Acquisition Time | 0x0008 | 0x0032 |
| Image Time | 0x0008 | 0x0033 |

### Fixed tags

The following tag(s) are set to a fixed value:

Table 4

| Name | Group | Element |
|-----------|--------|---------|
| Study ID | 0x0020 | 0x0010 |
| Accession Number | 0x0008 | 0x0050 |
| Patient's Name | 0x0010 | 0x0010 |

## Other Anonymisation

- Other anatomical regions or 3D scans (for example DICOM MRI) would require slightly different anonymisation process (to be defined).

## Documentation

- PIXL automatically logs (audit trails) for steps taken and database tables used, they should have project name, and date at which anonymisation (the
  current process) is performed.
- Record any issues encountering during anonymisation process as Github issue while referring to this SOP.

## Monitoring Compliance

- Spot check anonymisation quality for names and dates on 1% of cases per project release (minimum of 100 and maximum of 500). Report issues as Github
  issues to the PIXL team. Iterate this process until the quality is acceptable and no identifiable data is remaining. The person checking the
  anonymisation should not be the same person who performed the anonymisation, it can be a manager, a CRIU member or a research team member under
  Confidentiality Advisory Group-approved project.
- Update SOP as needed based on results of compliance checks.

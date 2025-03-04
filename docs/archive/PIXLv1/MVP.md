# The PIXL MVP

## Deliverables
Delivering the `PIXL` MVP requires that

0. We pre-specify the cohort of patients who received chest X-rays (estimated ~300k images)
1. We intelligently query the PACS/VNA for the chest X-rays from this cohort without causing operational systems to fall over
1. We automatically de-identify DICOM elements with a simple whitelisting approach and removal of PII overlays
1. We automatically push DICOM instances to a DICOM node in Azure via DICOMweb
1. We extract EHR and free-text radiology reports for the specified cohort
1. We de-identify free-text radiology reports with Presidio
1. We de-identify PII EHR attributes using a blacklisting approach
1. We link de-identified data securely
1. We automatically push radiology reports & EHR data into Delta Lake on Azure
1. We automatically ingest data from Delta Lake into the Feathr feature store
1. We provide controlled access to the DICOM node and the Feathr feature store to an Azure TRE workspace
1. We offer useful written guidance to the research team
1. We provide workable policies and SOPs for managing image extraction via the PIXL pipeline


## Out of Scope
- Real-time data ingestion
- DICOM pixel data de-identification
- Identifiable patient data in Azure
- Perfection


## Target Delivery Date
~~mid-November 2022~~  
mid December 2022
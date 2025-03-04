# DICOM Service solution design

## Overview
![High-level diagram](./diagrams/PIXL-FlowEHR_DICOM_service.drawio.png?raw=true "High-level diagram of DICOM service.")

## References
- [REST API of Orthanc](https://book.orthanc-server.com/users/rest.html)
- [Performing Query/Retrieve (C-Find) and Find with REST](https://book.orthanc-server.com/users/rest.html#performing-query-retrieve-c-find-and-find-with-rest)
- [Performing Retrieve (C-Move)](https://book.orthanc-server.com/users/rest.html#performing-retrieve-c-move)
- [Quick reference of the REST API of Orthanc](https://book.orthanc-server.com/users/rest-cheatsheet.html#cheatsheet)
- [Python plugin for Orthanc](https://book.orthanc-server.com/plugins/python.html#id1)
- [DICOM Standard - Part 15](https://dicom.nema.org/medical/dicom/current/output/pdf/part15.pdf)

## Steps

### Orthanc `raw`
- [ ] Set up Orthanc `raw` with Postgres plugin. Configure to be index only, i.e. images stored on disk.
- [ ] Set up PACS/VNA as Q/R target.
- [ ] Perform C-FIND on PACS/VNA via `raw`  API  to collate dataset (if required).
- [ ] Retrieve dataset (C-MOVE) using API:
```
For each series/instance do:
	- Issue C-MOVE from PACS/VNA to raw.
	- Verify move success.
	- Remove series/instance from queue/list.
```

### Orthanc `anon`
- [ ] Set up Orthanc `anon` with DICOMweb plugin.
- [ ] Set up `raw` as Q/R target.
- [ ] Set up `Azure DICOM service` as DICOMweb endpoint
- [ ] Poll `raw` for new instances via API:
```
For each instance do:
	- C-MOVE from raw to anon.
	- Get patient UID from hasher.
```
- [ ] Python Plugin written to execute on `ReceivedInstanceCallback`. See [Modifying received instances (new in 4.0)](https://book.orthanc-server.com/plugins/python.html?highlight=python#id33)

### Callback plugin
```
For each received instance do:
	- GET anon. patient UID from hasher API.
	- Apply anonymisation.
	- Send via STOW to target.
	- Check instance received via WADO (?)
	- Drop Instance (i.e. do not write to disk)
```

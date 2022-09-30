## Sandbox for DICOM images/EMAP interaction

Build and up the test environment with:

```bash
docker compose --env-file .env.test -f docker-compose.test.yml up --build
```

Get a report query with

```bash
docker exec -it pixl_sandbox python report.py --mrn 3 --accession_number a
```

or an EHR set of data

```bash
docker exec -it pixl_sandbox python ehr.py -m 3 -a a -w 10000 -t 10000 -g 10000
```
see the CLI options
```bash
docker exec -it pixl_sandbox python ehr.py --help
```

> **Note**
> The EHR and report _could_ be returned together from a single call

*** 

To inspect DICOM images
```
docker build -t pixl-image-sandbox .
docker run -it pixl-image-sandbox /bin/bash
```

> **Note**
> The GAEs require defining the http(s) proxies when building:
> `docker build --build-arg https_proxy --build-arg HTTPS_PROXY --build-arg http_proxy --build-arg HTTP_PROXY -t pixl-sandbox`

Inspect a sample DICOM image with [https://github.com/pydicom/pydicom](https://github.com/pydicom/pydicom)

```
root@4dc984cf2645:/sandbox# python 
>>> from pydicom import dcmread
>>> from pydicom.data import get_testdata_file
>>> ds = dcmread(get_testdata_file("CT_small.dcm"))
>>> ds
Dataset.file_meta -------------------------------
(0002, 0000) File Meta Information Group Length  UL: 192
...
```


*** 
### Validation requirements

- Ensure GCS is between 3 and 15, from [paper](https://www.ncbi.nlm.nih.gov/books/NBK513298/)

## Sandbox for DICOM images/EMAP interaction

Build and enter a bash shell with
```bash
docker build -f ../docker/sandbox/Dockerfile -t pixl-sandbox .
docker run -it pixl-sandbox /bin/bash
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

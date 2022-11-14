FROM osimis/orthanc:22.9.0-full-stable
SHELL ["/bin/bash", "-o", "pipefail", "-e", "-u", "-x", "-c"]

COPY ./orthanc/orthanc-anon/plugin/anon.py /etc/orthanc/anon.py
COPY ./orthanc/orthanc-anon/plugin/tag-operations.yaml /etc/orthanc/tag-operations.yaml

COPY ./pixl_dcmd/src/requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY ./pixl_dcmd/src ./pixl_dcmd
RUN pip3 install --no-cache-dir ./pixl_dcmd
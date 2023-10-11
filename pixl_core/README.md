# Core

This directory contains a Python module with core PIXL functionality utilised by both the EHR and PACS APIs to
interact with RabbitMQ and ensure suitable rate limiting of requests to the upstream services.

### Install
```bash
pip install .
```

### Test

```bash
pip install .[test]
pytest -m "not pika"
```
or
```bash
cd tests
docker compose up --build --exit-code-from test
docker compose down
```

## Token buffer

The token buffer is needed to limit the download rate for images from PAX/VNA. Current specification suggests that a 
rate limit of five images per second should be sufficient, however that may have to be altered dynamically through 
command line interaction. 

The current implementation of the token buffer uses the 
[token bucket implementation from Falconry](https://github.com/falconry/token-bucket/). Furthermore, the token buffer is
not set up as a service as it is only needed for the image download rate. 


## Patient queue

Mechanism that allows driver to populate queues that can then be consumed by different services, e.g. patient data
or image download.

Two queues are currently planned: 
1. for download and de-identification of image data (default "pacs")
2. for download and de-identification of EHR demographic data (default "ehr")

The image anonymisation will be triggered automatically once the image has been downloaded to the raw Orthanc server.

### RabbitMQ

RabbitMQ is used for the queue implementation. 

The client of choice for RabbitMQ at this point in time is [pika](https://pika.readthedocs.io/en/stable/), which provides both a synchronous and 
asynchronous way of transferring messages. The former is geared towards high data throughput whereas the latter is geared towards stability. 
The asynchronous mode of transferring messages is a lot more complex as it is based on the 
[asyncio event loop](https://docs.python.org/3/library/asyncio-eventloop.html).

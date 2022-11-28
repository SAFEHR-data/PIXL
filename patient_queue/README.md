# Patient queue

Mechanism that allows driver to populate queues that can then be consumed by different services, e.g. patient data
or image download.

Two queues are currently planned: 
1. for download and de-identification of image data (default "pacs")
2. for download and de-identification of EHR demographic data (default "ehr")

The image anonymisation will be triggered automatically once the image has been downloaded to the raw Orthanc server.

## RabbitMQ

After consideration, development on [Apache Pulsar](https://pulsar.apache.org/) was put on hold in favour of using RabbitMQ. The downsides to Pulsar 
at this point in time were inferiority of the Python client and lack of suitable documentation that would reduce the burden of troubleshooting. 
RabbitMQ is used for the queue implementation. 

The client of choice for RabbitMQ at this point in time is [pika](https://pika.readthedocs.io/en/stable/), which provides both a synchronous and 
asynchronous way of transferring messages. The former is geared towards high data throughput whereas the latter is geared towards stability. 
The asynchronous mode of transferring messages is a lot more complex as it is based on the 
[asyncio event loop](https://docs.python.org/3/library/asyncio-eventloop.html).

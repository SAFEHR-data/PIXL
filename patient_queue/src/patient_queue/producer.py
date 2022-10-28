import pulsar

from patient_queue.utils import AvailableTopics
from patient_queue.utils import load_config_file


class PixlProducer:
    """Offers basic client functionality to patient queue.

    Providing different queues for subscription requires different producers for the different topics. The shared
    functionality across the different producers is provided through this base class. This class needs to be extended
    to create a topic-specific producer."""
    def __init__(self, topic_name):
        pulsar_binary_port = load_config_file(env_var="PULSAR_BINARY_PROTOCOL")
        self.client = pulsar.Client(f"pulsar://localhost:{pulsar_binary_port}")
        self.producer = self.client.create_producer(topic_name, block_if_queue_full=True)

    def create_queue_entry(self, msg: str):
        """Creates entry in queue.

        Allows for

        :param msg: entry information that is added to the queue.
        """
        self.producer.send(msg.encode('utf-8'))

    def shutdown(self):
        """Shuts down client connection to Pulsar service."""
        self.client.close()


class DicomProducer(PixlProducer):
    """Producer for adding DICOM tasks into the image download queue."""
    def __init__(self):
        super().__init__(topic_name=AvailableTopics.DICOM.__str__())


class EhrProducer(PixlProducer):
    """Producer for adding EHR download tasks to the respective queue."""
    def __init__(self):
        super().__init__(topic_name=AvailableTopics.EHR.__str__())


class OrthancProducer(PixlProducer):
    """Producer for adding EHR download tasks to the respective queue."""
    def __init__(self):
        super().__init__(topic_name=AvailableTopics.ORTHANC.__str__())

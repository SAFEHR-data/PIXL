import pulsar

from patient_queue.utils import AvailableTopics
from patient_queue.utils import load_config_file


class PixlClient:
    """S."""
    def __init__(self):
        pulsar_binary_port = load_config_file(env_var="PULSAR_BINARY_PROTOCOL")
        self.client = pulsar.Client(f"pulsar://localhost:{pulsar_binary_port}")

    def create_queue_entry(self, msg: str):
        """Creates entry in queue.

        When instantiating, a connection is established to the AvailableChannels.IMAGES topic (i.e. the patient queue) of

        :param msg: entry information that is added to the queue.
        """
        self.producer.send(msg.encode('utf-8'))

    def shutdown(self):
        """Shuts down client connection to Pulsar service."""
        self.client.close()


class DicomProducer(PixlClient):
    """Producer for adding DICOM tasks into the image download queue."""
    def __init__(self):
        super().__init__()
        self.producer = self.client.create_producer(AvailableTopics.DICOM.__str__(), block_if_queue_full=True)


class EhrProducer(PixlClient):
    """Producer for adding EHR download tasks to the respective queue."""
    def __init__(self):
        super().__init__()
        self.producer = self.client.create_producer(AvailableTopics.EHR.__str__(), block_if_queue_full=True)

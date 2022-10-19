import pulsar

from patient_queue.utils import AvailableTopics
from patient_queue.utils import load_config_file


class PulsarProducer:
    """Can be used to create entries in the patient queue (i.e. in topic)."""
    def __int__(self):
        pulsar_binary_port = load_config_file(env_var="PULSAR_BINARY_PROTOCOL")
        self.client = pulsar.Client(f"pulsar://localhost:{pulsar_binary_port}")
        self.producer = self.client.create_producer(AvailableTopics.PIXL, block_if_queue_full=True)

    def create_queue_entry(self, msg: str):
        """Creates entry in queue.

        When instantiating, a connection is established to the AvailableChannels.IMAGES topic (i.e. the patient queue) of

        :param msg: entry information that is added to the queue.
        """
        self.producer.send(msg.encode('utf-8'))

    def shutdown(self):
        """Shuts down client connection to Pulsar service."""
        self.client.close()

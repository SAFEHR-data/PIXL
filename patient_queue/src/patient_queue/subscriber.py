import pulsar

from patient_queue.utils import AvailableTopics
from patient_queue.utils import load_config_file


class PixlConsumer:
    """Can be used to create entries in the patient queue (i.e. in topic)."""

    def __int__(self, subscription: str) -> None:
        pulsar_binary_port = load_config_file(env_var="PULSAR_BINARY_PROTOCOL")
        self.client = pulsar.Client(f"pulsar://localhost:{pulsar_binary_port}")
        self.consumer = self.client.subscribe(AvailableTopics.PIXL, subscription_name=subscription)
        self.latest_msg = None

    def consume_next_msg(self):
        """Takes a message out of the queue.

        Pulsar holds a message queue for each topic that a consumer subscribes to. For each of the subscribers, the queue
        keeps track on which message has been taken out (based on [negative] acknowledgement).

        :returns: a string representing the message received from the topic subscription for the consumer.
        """
        self.latest_msg = self.client.receive()
        return self.latest_msg

    def acknowledge_msg(self) -> None:
        """Sends message receipt confirmation to server.

        Once a message has been received and successfully processed, an acknowledgement needs to be sent to the service
        so that the message will be removed from the message stream.

        :return:
        """
        self.client.acknowledge(self.latest_msg)

    def negative_acknowledge_msg(self) -> None:
        """Sends a negative acknowledgement message to server.

        Once a message has been received and there were problems in either receiving the message or handling it, a
        negative acknowledgement can be sent to the server. Upon receiving a negative acknowledgement, the server will
        continue to hold the message in a queue to send it again to the consumer at a later stage.

        :return:
        """
        self.client.negativeAcknowledge(self.latest_msg)

    def shutdown(self):
        """Shuts down client connection to Pulsar service."""
        self.client.close()

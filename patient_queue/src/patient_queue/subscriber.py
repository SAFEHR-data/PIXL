"""
Basically subscriber wants to "wait" on queue and automatically when something arrives, consume the message. It seems
that the other way round i.e. produce and then at some point connect & consume does not work with the code used.
"""

import pika


class PixlConsumer:
    """Connector to RabbitMQ. Consumes entries from a queue."""
    def __init__(self, _queue: str):
        self.queue = _queue
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=_queue)

    def callback(self, body):
        ### this needs the four parameters from the tutorial
        print(" [x] Received %r" % body)

    def retrieve_msg(self):
        ### problem is that consumer needs to hang ...
        self.channel.basic_consume(queue=self.queue, on_message_callback=self.callback, auto_ack=True)

    def shutdown(self):
        self.connection.close()

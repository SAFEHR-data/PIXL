import pika


class PixlConsumer:
    """Connector to RabbitMQ. Consumes entries from a queue."""
    def __init__(self, _queue: str):
        self.queue = _queue
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=_queue)

    def callback(self, body):
        print(" [x] Received %r" % body)

    def retrieve_msg(self):
        self.channel.basic_consume(queue=self.queue, on_message_callback=self.callback, auto_ack=True)

    def shutdown(self):
        self.connection.close()

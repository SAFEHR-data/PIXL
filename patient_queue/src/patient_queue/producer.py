import pika


class PixlProducer:
    """Connector to RabbitMQ. Generates entries on the queue, corresponding to data items that need to be downloaded
       from either EMAP or PACS/VNA."""
    def __init__(self, _queue: str):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=_queue)

    def create_entry(self, msg):
        self.channel.basic_publish(exchange='', routing_key='hello', body=msg)

    def shutdown(self):
        self.connection.close()

sadfsa
a asdf


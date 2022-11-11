"""
These tests require executing from within the EHR API container with the dependent
services being up
    - queue
    - pixl postgres db
    - emap star
"""
import pika
import logging

logger = logging.getLogger(__name__)
logger.setLevel("INFO")

message_body = "a,b,01/01/2022 00:01:00".encode("utf-8")


# TODO: Replace by PIXL queue package
def create_connection() -> pika.BlockingConnection:

    params = pika.ConnectionParameters(host="queue", port=5672)
    return pika.BlockingConnection(params)


def add_single_message_to_the_queue(queue_name: str = "test_queue"):

    connection = create_connection()
    channel = connection.channel()
    channel.queue_declare(queue="test_queue")
    channel.basic_publish(exchange="", routing_key=queue_name, body=message_body)
    print("published")
    connection.close()


if __name__ == '__main__':
    add_single_message_to_the_queue()

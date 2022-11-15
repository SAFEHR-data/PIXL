#  Copyright (c) 2022 University College London Hospitals NHS Foundation Trust
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import pika


class PixlConsumer:
    """Connector to RabbitMQ. Consumes entries from a queue."""
    def __init__(self, _queue: str):
        self.queue = _queue
        self.connection = pika.SelectConnection(pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=_queue)
        self.connection.ioloop.start()

    def callback(self, ch, method, properties, body):
        ### this needs the four parameters from the tutorial
        print(" [x] Received %r" % body)

    def retrieve_msg(self):
        ### problem is that consumer needs to hang ...
        method_frame, header_frame, body = self.channel.basic_get(queue=self.queue)
        return body

    def shutdown(self):
        self.channel.stop_consuming()
        self.connection.close()



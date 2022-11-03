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


sdfasfd

asdfasdf
adf
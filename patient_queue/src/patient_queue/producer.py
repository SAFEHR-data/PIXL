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

import functools
import logging
import json

import pika
from pika.exchange_type import ExchangeType

LOGGER = logging.getLogger(__name__)


class PixlProducer(object):
    """
    Generic publisher for RabbitMQ.
    """
    EXCHANGE = 'message'
    EXCHANGE_TYPE = ExchangeType.topic
    QUEUE = 'ehr'
    ROUTING_KEY = 'ehr'

    def __init__(self):
        """Setup the example publisher object, passing in the URL we will use
        to connect to RabbitMQ.
        :param str amqp_url: The URL for connecting to RabbitMQ
        """
        self._connection = None
        self._channel = None

    def connect(self):
        """This method connects to RabbitMQ, returning the connection handle.
        When the connection is established, the on_connection_open method
        will be invoked by pika.
        :rtype: pika.SelectConnection
        """
        LOGGER.info('Attempting to establish connection ... ')
        params = pika.ConnectionParameters()
        self._connection = pika.SelectConnection(params, on_open_callback=self.on_connected)
        self._connection.ioloop.start()

    def on_connected(self, new_connection):
        """
        :rtype: pika.SelectConnection
        """
        LOGGER.info('Attempting to establish channel')
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        """This method is invoked by pika when the channel has been opened.
        The channel object is passed in so we can make use of it.
        Since the channel is now open, we'll declare the exchange to use.
        :param pika.channel.Channel channel: The channel object
        """
        LOGGER.info('Channel opened')
        self._channel = channel
        self._channel.queue_declare(queue=self.QUEUE, callback=self.on_queue_declareok)

    def on_queue_declareok(self, _unused_frame):
        """Method invoked by pika when the Queue.Declare RPC call made in
        setup_queue has completed. In this method we will bind the queue
        and exchange together with the routing key by issuing the Queue.Bind
        RPC command. When this command is complete, the on_bindok method will
        be invoked by pika.
        :param pika.frame.Method _unused_frame: The Queue.DeclareOk frame
        """
        LOGGER.info('Binding %s to %s with %s', self.EXCHANGE, self.QUEUE,
                    self.ROUTING_KEY)
        self._channel.queue_bind(self.QUEUE,
                                 self.EXCHANGE,
                                 routing_key=self.ROUTING_KEY)

    def publish_message(self, msg):
        """If the class is not stopping, publish a message to RabbitMQ,
        appending a list of deliveries with the message number that was sent.
        This list will be used to check for delivery confirmations in the
        on_delivery_confirmations method.
        Once the message has been sent, schedule another message to be sent.
        The main reason I put scheduling in was just so you can get a good idea
        of how the process is flowing by slowing down and speeding up the
        delivery intervals by changing the PUBLISH_INTERVAL constant in the
        class.
        """
        self._connection.ioloop.call_later(1, self.send_message(msg=msg))

    def send_message(self, msg):
        self._channel.basic_publish(msg)

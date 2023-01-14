# Copyright (c) 2023 Ilia Sotnikov
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Simulates a G90 device with real network exhanges for tests.
"""
import asyncio
import logging

_LOGGER = logging.getLogger('Mock device')


class MockDeviceProtocol:
    """
    asyncio protocol for simulate G90 device exchange over network.

    :param list(bytes) device_sent_data: List of datagram payloads to simulate
     being sent from device as response to client requests
    """
    def __init__(self, device_sent_data):
        self._device_sent_data = iter(device_sent_data or [])
        self._device_recv_data = []
        self._transport = None

    def connection_made(self, transport):
        """
        Invoked when connection is made.

        :param transport: asyncio transport instance
        """
        self._transport = transport

    def connection_lost(self, _err):
        """
        Invoked when connection is lost.

        :param _err: Exception object
        """

    def datagram_received(self, data, addr):
        """
        Invoked when a datagram is received.
        """
        message = data.decode()
        self._device_recv_data.append(data)
        _LOGGER.debug('Received %s from %s:%s', message, *addr)
        try:
            sent_data = next(self._device_sent_data)
        except StopIteration:
            _LOGGER.info(
                'No more data to send, the client will experience a timeout'
                ' condition'
            )
            return

        _LOGGER.debug('Sent %s to %s:%s', sent_data, *addr)
        self._transport.sendto(sent_data, addr)

    @property
    def device_recv_data(self):
        """
        Returns all data received by the simulated device from the client.

        :return list: List of datagram paylods received
        """
        return self._device_recv_data


class MockNotificationProtocol:
    """
    asyncio protocol for simulate G90 device notifications over network.

    :param list(bytes) notification_data: List of datagram payloads to simulate
     being sent from device to client
    """
    def __init__(self, notification_data):
        self._notification_data = notification_data
        self._transport = None
        self._done = asyncio.get_running_loop().create_future()

    def connection_made(self, transport):
        """
        Invoked when connection is made to the client and simulated
        notification is ready to be sent.

        :param transport: asyncio transport instance
        """

        remote_addr = transport.get_extra_info('peername') or (None, None)
        _LOGGER.debug(
            'Sent notification data %s to %s:%s',
            self._notification_data, *remote_addr
        )
        transport.sendto(self._notification_data)
        self._done.set_result(True)

    def connection_lost(self, _err):
        """
        Invoked when connection is lost.

        :param _err: Exception object
        """

    @property
    def is_done(self):
        """
        Indicates if sending the notification payload has been completed.

        :return bool: True if sending has been completed
        """
        return self._done


class DeviceMock:  # pylint:disable=too-many-instance-attributes
    """
    Simulates G90 responses and notification messages over a real network
    connection.

    :param list(bytes) data: List of datagram payloads to simulate being sent
     from device as response to client requests
    :param list(bytes) notification_data: List of datagram payloads to simulate
     notifications being sent from device to client
    :param int device_port: The port simulated device listens on for client
     requests
    :param int notification_port: The destination port on the client the
     notifications will be sent to
    :param str device_host: The host the simulated device listen on for client
     requests
    :param str notification_host: The destination client host the notifications
     will be sent to
    """
    def __init__(  # pylint:disable=too-many-arguments
        self, data, notification_data,
        device_port, notification_port,
        device_host='127.0.0.1',
        notification_host='127.0.0.1',
    ):
        self._host = device_host
        self._port = device_port
        self._data = data
        self._transport = None
        self._protocol = None
        self._notification_data = iter(notification_data or [])
        self._notification_port = notification_port
        self._notification_host = notification_host
        _LOGGER.debug(
            'Ports - device: %s, notification: %s',
            self._port, self._notification_port
        )

    async def start(self):
        """
        Starts listening the simulate device for client requests.
        """
        loop = asyncio.get_running_loop()
        _LOGGER.debug(
            'Creating UDP server endpoint: %s:%s', self._host, self._port
        )
        self._transport, self._protocol = await loop.create_datagram_endpoint(
            lambda: MockDeviceProtocol(self._data),
            local_addr=(self._host, self._port)
        )

    @property
    def host(self):
        """
        Returns the host the simulated device listens on.

        :return str: Host name or address
        """
        return self._host

    @property
    def port(self):
        """
        Returns the port the simulated device listens on.

        :return int: Port number
        """
        return self._port

    @property
    def notification_host(self):
        """
        Returns the host the simulated notifications will be sent to.

        :return str: Host name or address
        """
        return self._notification_host

    @property
    def notification_port(self):
        """
        Returns the destination port will be used to send notifications to the
        client.

        :return int: Port number
        """
        return self._notification_port

    @property
    def recv_data(self):
        """
        Returns the data received by the simulated device from the client.

        :return list(bytes): Data received
        """
        return self._protocol.device_recv_data

    def stop(self):
        """
        Stops listening for client requests.
        """
        _LOGGER.debug(
            'Closing UDP server endpoint %s:%s', self._host, self._port
        )
        self._transport.close()

    async def send_next_notification(self):
        """
        Sends next simulated notification message to the client.

        The code uses `asyncio` intentionally to cooperate with async tests.
        """
        data = None
        try:
            data = next(self._notification_data)
        except StopIteration:
            _LOGGER.info(
                'No more notification data to send, skipping'
            )
            return

        _LOGGER.debug(
            'Creating UDP notification client to %s:%s',
            self._notification_host,
            self._notification_port
        )

        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: MockNotificationProtocol(data),
            remote_addr=(self._notification_host, self._notification_port)
        )
        await asyncio.wait([protocol.is_done])
        _LOGGER.debug('Closing UDP notification client')
        transport.close()

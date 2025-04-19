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
from __future__ import annotations
from typing import Optional, Tuple, List, Any, cast, Iterator
import asyncio
from asyncio.protocols import DatagramProtocol, Protocol, BaseProtocol
from asyncio.transports import DatagramTransport, BaseTransport, Transport
from asyncio import Future
import logging

_LOGGER = logging.getLogger('Mock device')


class MockDeviceError(Exception):
    """
    Base class for all mock device exceptions.
    """


class MockDeviceTransportNotAvailableError(MockDeviceError):
    """
    Exception raised when the transport is not available.
    """
    def __init__(self) -> None:
        self.args = (
            'Transport is not available, not sending',
        )


class MockDeviceRemoteAddrNotAvailableError(MockDeviceError):
    """
    Exception raised when the remote address is not available.
    """
    def __init__(self) -> None:
        self.args = (
            'Remote address is not available, not sending',
        )


class MockDeviceProtocolBase:
    """
    Base class for the mock device protocol.
    """
    def __init__(self, device_sent_data: Optional[List[bytes]] = None):
        self._device_sent_data: Iterator[bytes] = iter(device_sent_data or [])
        self._device_recv_data: List[bytes] = []
        self._done = asyncio.get_running_loop().create_future()
        self.remote_addr: Optional[Tuple[str, int]] = None

    def send(self, data: bytes, addr: Tuple[str, int]) -> None:
        """
        Sends data to the client.

        :param data: Data to be sent
        :param addr: Address of the client
        """

    def send_data(self, addr: Tuple[str, int]) -> None:
        """
        Sends the next data packet to the specified address.

        Retrieves the next data packet from the internal queue and sends it to
        the client. If there's no more data to send, marks the operation as
        done.

        :param addr: The address (host, port) tuple to send data to
        """
        try:
            sent_data = next(self._device_sent_data)
        except StopIteration:
            _LOGGER.info(
                'No more data to send, the client will experience a timeout'
                ' condition'
            )
            if not self._done.done():
                self._done.set_result(True)
            return

        self.send(sent_data, addr)
        _LOGGER.debug(
            'Sent %s (%s) to %s:%s',
            sent_data, sent_data.hex(' '), *addr
        )

        if not self._done.done():
            self._done.set_result(True)

    def handle_received_data(self, received_data: bytes) -> None:
        """
        Handles data received from the client.

        Logs the received data and stores it in the internal received data list
        for later inspection during tests.

        :param received_data: The raw bytes received from the client
        """
        if self.remote_addr:
            _LOGGER.debug(
                "Received '%s' (%s) from %s:%s",
                received_data, received_data.hex(' '),
                *self.remote_addr
            )
        else:
            _LOGGER.debug(
                'Received %s (%s)',
                received_data, received_data.hex(' ')
            )
        self._device_recv_data.append(received_data)

    @property
    def device_recv_data(self) -> List[Any]:
        """
        Returns all data received by the simulated device from the client.

        :return: List of datagram paylods received
        """
        return self._device_recv_data

    @property
    def is_done(self) -> Future[bool]:
        """
        Indicates if sending the notification payload has been completed.

        :return: Completed future if sending has been completed
        """
        return self._done


class MockDeviceProtocol(DatagramProtocol, MockDeviceProtocolBase):
    """
    asyncio protocol for simulate G90 device exchange over network.

    :param device_sent_data: List of datagram payloads to simulate being sent
     from device as response to client requests
    """
    def __init__(self, device_sent_data: List[bytes]):
        super().__init__(device_sent_data)
        self._transport: Optional[DatagramTransport] = None

    def connection_made(self, transport: BaseTransport) -> None:
        """
        Invoked when connection is made.

        :param transport: asyncio transport instance
        """
        self._transport = cast(DatagramTransport, transport)

    def connection_lost(self, _err: Optional[Exception]) -> None:
        """
        Invoked when connection is lost.

        :param _err: Exception object
        """

    def send(self, data: bytes, addr: Tuple[str, int]) -> None:
        """
        Sends data to the client.

        :param data: Data to be sent
        :param addr: Address of the client
        """
        if not self._transport:
            raise MockDeviceTransportNotAvailableError()

        super().send(data, addr)
        self._transport.sendto(data, addr)

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        """
        Invoked when a datagram is received.
        """
        self.handle_received_data(data)
        self.send_data(addr)


class MockNotificationProtocol(DatagramProtocol, MockDeviceProtocolBase):
    """
    asyncio protocol for simulate G90 device notifications over network.

    :param list(bytes) notification_data: List of datagram payloads to simulate
     being sent from device to client
    """
    def __init__(self, notification_data: List[bytes]):
        super().__init__(notification_data)
        self._transport: Optional[DatagramTransport] = None

    def send(self, data: bytes, addr: Tuple[str, int]) -> None:
        """
        Sends data to the client.

        :param data: Data to be sent
        :param addr: Address of the client
        """
        if not self._transport:
            raise MockDeviceTransportNotAvailableError()

        super().send(data, addr)
        self._transport.sendto(data)

    def connection_made(self, transport: BaseTransport) -> None:
        """
        Invoked when connection is made to the client and simulated
        notification is ready to be sent.

        :param transport: asyncio transport instance
        """
        self.remote_addr = transport.get_extra_info('peername')
        if not self.remote_addr:
            raise MockDeviceRemoteAddrNotAvailableError()
        _LOGGER.debug('Notification connection to %s:%s', *self.remote_addr)
        self._transport = cast(DatagramTransport, transport)

    def connection_lost(self, _err: Optional[Exception]) -> None:
        """
        Invoked when connection is lost.

        :param _err: Exception object
        """


class MockCloudProtocol(Protocol, MockDeviceProtocolBase):
    """
    asyncio protocol for simulate G90 device notifications over network.

    :param list(bytes) notification_data: List of datagram payloads to simulate
     being sent from device to client
    """
    def __init__(self, cloud_notification_data: List[bytes]):
        super().__init__(cloud_notification_data)
        self._transport: Optional[Transport] = None

    def send(self, data: bytes, addr: Tuple[str, int]) -> None:
        """
        Sends data to the client.

        :param data: Data to be sent
        :param addr: Address of the client
        """
        if not self._transport:
            raise MockDeviceTransportNotAvailableError()

        super().send(data, addr)
        self._transport.write(data)

    def connection_made(self, transport: BaseTransport) -> None:
        """
        Invoked when connection is made to the client and simulated
        notification is ready to be sent.

        :param transport: asyncio transport instance
        """
        self.remote_addr = transport.get_extra_info('peername')
        if not self.remote_addr:
            raise MockDeviceRemoteAddrNotAvailableError()
        self._transport = cast(Transport, transport)

    def data_received(self, data: bytes) -> None:
        """
        Invoked when data is received from the client.

        Handles the received data and stores it for later inspection during
        tests.

        :param data: The raw bytes received from the client
        """
        self.handle_received_data(data)

    def connection_lost(self, exc: Optional[Exception]) -> None:
        """
        Invoked when connection is lost.

        :param _err: Exception object
        """
        if exc:
            self._done.set_exception(exc)

        if not self._done.done():
            self._done.set_result(True)


class MockCloudUpstreamProtocol(Protocol, MockDeviceProtocolBase):
    """
    asyncio protocol for simulate G90 cloud notifications (as if coming from
    upstream service).

    :param list(bytes) notification_data: List of datagram payloads to simulate
     being sent from cloud to client
    """
    def __init__(self, upstream_sent_data: List[bytes]):
        super().__init__(upstream_sent_data)
        self._transport: Optional[Transport] = None

    def connection_made(self, transport: BaseTransport) -> None:
        """
        Invoked when connection is made to the client and simulated
        notification is ready to be sent.

        :param transport: asyncio transport instance
        """
        self.remote_addr = transport.get_extra_info('peername')
        if not self.remote_addr:
            raise MockDeviceRemoteAddrNotAvailableError()
        _LOGGER.debug('Upstream connection from %s:%s', *self.remote_addr)
        self._transport = cast(Transport, transport)

    def send(self, data: bytes, addr: Tuple[str, int]) -> None:
        """
        Sends data to the client.

        :param data: Data to be sent
        :param addr: Address of the client
        """
        if not self._transport:
            raise MockDeviceTransportNotAvailableError()

        super().send(data, addr)
        self._transport.write(data)

    def data_received(self, data: bytes) -> None:
        """
        Invoked when data is received from the client.

        Handles the received data and stores it for later inspection during
        tests.

        :param data: The raw bytes received from the client
        """
        if not self.remote_addr:
            raise MockDeviceRemoteAddrNotAvailableError()

        self.handle_received_data(data)
        self.send_data(self.remote_addr)

    def connection_lost(self, exc: Optional[Exception]) -> None:
        """
        Invoked when connection is lost.

        :param _err: Exception object
        """
        if exc:
            self._done.set_exception(exc)

        if not self._done.done():
            self._done.set_result(True)

    @property
    def transport(self) -> Optional[Transport]:
        """
        Returns the transport instance associated with the protocol.

        :return: Transport instance or None if not available
        """
        return self._transport


class DeviceMock:  # pylint:disable=too-many-instance-attributes
    """
    Simulates G90 responses and notification messages over a real network
    connection.

    :param data: List of datagram payloads to simulate being sent
     from device as response to client requests
    :param notification_data: List of datagram payloads to simulate
     notifications being sent from device to client
    :param device_port: The port simulated device listens on for client
     requests
    :param notification_port: The destination port on the client the
     notifications will be sent to
    :param device_host: The host the simulated device listen on for client
     requests
    :param notification_host: The destination client host the notifications
     will be sent to
    :param cloud_notification_data: List of TCP payloads to simulate being
     sent from cloud to the client, responses to requests from device
     typically
    :param cloud_host: The host the simulated cloud endpoint listens on for
     client requests
    :param cloud_port: The port the simulated cloud endpoint listens on for
     client requests
    :param cloud_upstream_data: List of TCP payloads to simulate being sent
     from cloud to the client (currently unused, intended to simulate
     cloud-initiated interactions)
    :param cloud_upstream_host: The host the simulated cloud upstream
     endpoint listens on for client requests
    :param cloud_upstream_port: The port the simulated cloud upstream
     endpoint listens on for client requests
    """
    def __init__(  # pylint:disable=too-many-arguments
        self, data: List[bytes], notification_data: List[bytes],
        device_port: int, notification_port: int,
        cloud_notification_data: Optional[List[bytes]] = None,
        cloud_upstream_data: Optional[List[bytes]] = None,
        device_host: str = '127.0.0.1',
        notification_host: str = '127.0.0.1',
        cloud_host: str = '127.0.0.1',
        cloud_port: int = 5678,
        cloud_upstream_host: str = '127.0.0.1',
        cloud_upstream_port: int = 5678,
    ):
        self._host = device_host
        self._port = device_port
        self._data = data
        self._device_transport: Optional[BaseTransport] = None
        self._device_protocol: Optional[MockDeviceProtocol] = None
        self._notification_data = notification_data or []
        self._notification_port = notification_port
        self._notification_host = notification_host
        self._notification_transport: Optional[BaseTransport] = None
        self._notification_protocol: Optional[
            MockNotificationProtocol
        ] = None
        self._cloud_data = cloud_notification_data or []
        self._cloud_recv_data: List[bytes] = []
        self._cloud_host = cloud_host
        self._cloud_port = cloud_port
        self._cloud_upstream_data = cloud_upstream_data
        self._cloud_upstream_host = cloud_upstream_host
        self._cloud_upstream_port = cloud_upstream_port
        self._cloud_upstream_protocol: Optional[
            MockCloudUpstreamProtocol
        ] = None
        self._cloud_notification_protocol: Optional[
            MockCloudProtocol
        ] = None
        self._cloud_notification_transport: Optional[BaseTransport] = None

        _LOGGER.debug(
            'Ports - device: %s, notification: %s'
            ', cloud: %s, cloud upstream: %s',
            self._port, self._notification_port,
            self._cloud_port, self._cloud_upstream_port
        )

    async def start(self) -> None:
        """
        Starts listening the simulated device for client requests (both local
        and cloud).
        """
        loop = asyncio.get_running_loop()
        _LOGGER.debug(
            'Creating UDP server endpoint: %s:%s', self._host, self._port
        )
        (
            self._device_transport, self._device_protocol
        ) = await loop.create_datagram_endpoint(
            lambda: MockDeviceProtocol(self._data),
            local_addr=(self._host, self._port)
        )

        if self._cloud_upstream_data:
            self._cloud_upstream_protocol = MockCloudUpstreamProtocol(
                self._cloud_upstream_data
            )
            _LOGGER.debug(
                'Creating TCP upstream endpoint: %s:%s',
                self._cloud_upstream_host, self._cloud_upstream_port
            )
            await loop.create_server(
                protocol_factory=lambda: cast(
                    BaseProtocol, self._cloud_upstream_protocol
                ),
                host=self._cloud_upstream_host, port=self._cloud_upstream_port
            )

    @property
    def host(self) -> str:
        """
        Returns the host the simulated device listens on.

        :return: Host name or address
        """
        return self._host

    @property
    def port(self) -> int:
        """
        Returns the port the simulated device listens on.

        :return: Port number
        """
        return self._port

    @property
    def notification_host(self) -> str:
        """
        Returns the host the simulated notifications will be sent to.

        :return: Host name or address
        """
        return self._notification_host

    @property
    def notification_port(self) -> int:
        """
        Returns the destination port will be used to send notifications to the
        client.

        :return: Port number
        """
        return self._notification_port

    @property
    def notification_data(self) -> Optional[List[bytes]]:
        """
        Returns the data to be sent from the simulated device to the client.
        """
        return self._notification_data

    @property
    def cloud_host(self) -> str:
        """
        Returns the host the simulated cloud endpoint listens on.

        :return: Host name or address
        """
        return self._cloud_host

    @property
    def cloud_port(self) -> int:
        """
        Returns the port the simulated cloud endpoint listens on.

        :return: Port number
        """
        return self._cloud_port

    @property
    def cloud_data(self) -> Optional[List[bytes]]:
        """
        Returns the data to be sent from the simulated cloud endpoint
        to the client.
        """
        return self._cloud_data

    @property
    def cloud_upstream_host(self) -> str:
        """
        Returns the host the simulated cloud endpoint listens on.

        :return: Host name or address
        """
        return self._cloud_upstream_host

    @property
    def cloud_upstream_port(self) -> int:
        """
        Returns the port the simulated cloud endpoint listens on.

        :return: Port number
        """
        return self._cloud_upstream_port

    @property
    def cloud_upstream_data(self) -> Optional[List[bytes]]:
        """
        Returns the data to be sent from the simulated cloud upstream
        endpoint to the client.
        """
        return self._cloud_upstream_data

    @property
    async def recv_data(self) -> List[bytes]:
        """
        Returns the data received by the simulated device from the client.

        :return: Data received
        """
        if not self._device_protocol:
            return []

        await asyncio.wait([self._device_protocol.is_done])
        return self._device_protocol.device_recv_data

    @property
    async def cloud_recv_data(self) -> List[bytes]:
        """
        Returns the data received by the simulated cloud service from the
        client.

        :return: Data received
        """
        if not self._cloud_notification_protocol:
            return []

        await asyncio.wait([self._cloud_notification_protocol.is_done])
        return self._cloud_notification_protocol.device_recv_data

    @property
    async def cloud_upstream_recv_data(self) -> List[bytes]:
        """
        Returns the data received by the simulated cloud service (upstream)
        from the client.

        :return: Data received
        """
        if not self._cloud_upstream_protocol:
            return []

        await asyncio.wait([self._cloud_upstream_protocol.is_done])
        return self._cloud_upstream_protocol.device_recv_data

    async def stop(self) -> None:
        """
        Stops listening for client requests.
        """
        if self._device_transport:
            _LOGGER.debug(
                'Closing UDP server endpoint %s:%s', self._host, self._port
            )
            self._device_transport.close()

        if (
            self._cloud_upstream_protocol is not None
            and self._cloud_upstream_protocol.transport
        ):
            _LOGGER.debug(
                'Closing TCP upstream endpoint %s:%s',
                self._cloud_upstream_host, self._cloud_upstream_port
            )
            self._cloud_upstream_protocol.transport.close()

    async def send_next_notification(self) -> None:
        """
        Sends next simulated notification message to the client.
        """

        if not self._notification_data:
            return

        if not self._notification_protocol:
            _LOGGER.debug(
                'Creating UDP notification client to %s:%s',
                self._notification_host,
                self._notification_port
            )

            loop = asyncio.get_running_loop()
            (
                self._notification_transport, self._notification_protocol
            ) = await loop.create_datagram_endpoint(
                lambda: MockNotificationProtocol(self._notification_data),
                remote_addr=(self._notification_host, self._notification_port)
            )

        self._notification_protocol.send_data(
            (self._notification_host, self._notification_port)
        )

        await asyncio.wait([self._notification_protocol.is_done])

    async def send_next_cloud_packet(self) -> None:
        """
        Sends next simulated cloud packet to the client.
        """
        if not self._cloud_data:
            return

        if not self._cloud_notification_protocol:
            _LOGGER.debug(
                'Creating TCP cloud client to %s:%s',
                self._cloud_host,
                self._cloud_port
            )

            loop = asyncio.get_running_loop()
            (
                self._cloud_notification_transport,
                self._cloud_notification_protocol
            ) = await loop.create_connection(
                lambda: MockCloudProtocol(self._cloud_data),
                host=self._cloud_host, port=self._cloud_port
            )

        self._cloud_notification_protocol.send_data(
            (self._cloud_host, self._cloud_port)
        )
        await asyncio.wait(
            [self._cloud_notification_protocol.is_done]
        )

        if self._cloud_upstream_protocol:
            await asyncio.wait(
                [self._cloud_upstream_protocol.is_done]
            )

# Copyright (c) 2025 Ilia Sotnikov
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
Implementation of G90 cloud protocol notifications service.

Provides a server that listens for connections from G90 alarm devices and
handles cloud protocol notifications.
"""
from typing import Optional, cast, Callable
import logging
import asyncio
from asyncio.transports import BaseTransport, Transport
from asyncio.protocols import Protocol, BaseProtocol
from asyncio import Future

from .protocol import (
    G90CloudHeader, G90CloudError, G90CloudMessageNoMatch,
    G90CloudMessageContext,
)
from .messages import (
    CLOUD_MESSAGE_CLASSES, G90CloudNotificationMessage,
    G90CloudStatusChangeAlarmReqMessage,
    G90CloudStatusChangeSensorReqMessage,
    G90CloudStatusChangeReqMessage,
    G90CloudHelloReqMessage,
    G90CloudHelloDiscoveryReqMessage,
)
from ..notifications.base import G90NotificationsBase
from ..notifications.protocol import G90NotificationProtocol
from ..const import (REMOTE_CLOUD_HOST, REMOTE_CLOUD_PORT)


_LOGGER = logging.getLogger(__name__)


# pylint:disable=too-many-instance-attributes
class G90CloudNotifications(G90NotificationsBase, asyncio.Protocol):
    """
    Cloud notifications service for G90 alarm systems.

    Implements a server that listens for connections from G90 alarm devices
    and processes cloud protocol messages, with optional forwarding to an
    upstream server.

    :param protocol_factory: Factory function to create notification
     protocol handlers
    :param local_host: Local host to bind the server to
    :param local_port: Local port to bind the server to
    :param upstream_host: Optional upstream host to forward messages to
    :param upstream_port: Optional upstream port to forward messages to
    :param keep_single_connection: Whether to keep only a single device
     connection
    """
    # pylint:disable=too-many-arguments
    def __init__(
        self,
        protocol_factory: Callable[[], G90NotificationProtocol],
        local_host: str, local_port: int,
        upstream_host: Optional[str] = None,
        upstream_port: Optional[int] = None,
        keep_single_connection: bool = True,
    ) -> None:
        super().__init__(protocol_factory)
        self._transport: Optional[Transport] = None
        self._server: Optional[asyncio.Server] = None
        self._local_host = local_host
        self._local_port = local_port
        self._upstream_host = upstream_host
        self._upstream_port = upstream_port
        self._keep_single_connection = keep_single_connection
        self._upstream_transport: Optional[Transport] = None
        self._done_sending: Optional[Future[bool]] = None
        self._upstream_task: Optional[asyncio.Task[None]] = None

    def connection_made(self, transport: BaseTransport) -> None:
        """
        Handle a new connection from a device.

        :param transport: The transport for the new connection
        """
        host, port = transport.get_extra_info('peername')
        _LOGGER.debug('Connection from device %s:%s', host, port)
        if self._keep_single_connection and self._transport:
            _LOGGER.debug(
                'Closing connection previously opened from %s:%s',
                *self._transport.get_extra_info('peername')
            )
            self._transport.close()
        self._transport = cast(Transport, transport)

    def connection_lost(self, exc: Optional[Exception]) -> None:
        """
        Handle connection loss from a device.

        :param exc: Exception that caused the connection loss, if any
        """
        if exc:
            _LOGGER.debug('Device connection error: %s', exc)

        # Mark device ID as unknown when connection with alarm panel is lost
        self.clear_device_id()

        if self._transport:
            self._transport.close()
        self._transport = None

    # pylint:disable=too-many-branches
    def data_received(self, data: bytes) -> None:
        """
        Process data received from a device.

        Parses messages from the device, handles them, and sends appropriate
        responses back to the device simulating the cloud server, unless
        upstream forwarding is configured - the data is passed thru to the
        upstream server unmodified.

        :param data: Bytes received from the device
        """
        if self._transport is None:
            return

        self.set_last_device_packet_time()

        # If upstream connection is configured, pass thru all data from the
        # panel. This is done in a separate task to avoid blocking the main
        # processing - the passhtru mode is somewhat supplementary, hence the
        # task is create-and-forget with no retries, error handling nor
        # ordering guarantees, it is assumed the cloud service will handle
        # those correctly.
        if (
            self._upstream_host is not None
            and self._upstream_port is not None
        ):
            self._upstream_task = asyncio.create_task(self.send_upstream(data))

        host, port = self._transport.get_extra_info('peername')
        _LOGGER.debug(
            'Data received from device %s:%s: %s', host, port, data.hex(' ')
        )

        try:
            while len(data):
                # Instantiate a context for the messages
                ctx = G90CloudMessageContext(
                    device_id=self.device_id,
                    local_host=self._local_host,
                    local_port=self._local_port,
                    cloud_host=REMOTE_CLOUD_HOST,
                    cloud_port=REMOTE_CLOUD_PORT,
                    upstream_host=self._upstream_host,
                    upstream_port=self._upstream_port,
                    remote_host=host,
                    remote_port=port
                )
                found = False

                for cls in CLOUD_MESSAGE_CLASSES:
                    try:
                        msg = cls.from_wire(data, context=ctx)
                    except G90CloudMessageNoMatch:
                        continue

                    _LOGGER.debug("Cloud message received: %s", msg)

                    # Only these messages carry on the device ID, store it so
                    # vefirication will be performed by `_handle_alert()`
                    # method
                    if cls in [
                        G90CloudHelloReqMessage,
                        G90CloudHelloDiscoveryReqMessage,
                    ]:
                        self.device_id = msg.guid

                    if cls == G90CloudNotificationMessage:
                        self.handle(msg.as_notification_message)

                    if cls in [
                        G90CloudStatusChangeAlarmReqMessage,
                        G90CloudStatusChangeSensorReqMessage,
                        G90CloudStatusChangeReqMessage,
                    ]:
                        alert = msg.as_device_alert
                        if alert:
                            self.handle_alert(
                                alert,
                                # Verifying device ID only makes sense when
                                # connection isn't closed each time a message
                                # is received
                                verify_device_id=(
                                    not self._keep_single_connection
                                )
                            )

                    found = True

                    # Sending message to upstream cloud service isn't
                    # configured, simulate the response and send those back to
                    # the panel
                    if not self._upstream_task:
                        self._done_sending = asyncio.Future()
                        for resp in msg.wire_responses(context=ctx):
                            self._transport.write(resp)
                            _LOGGER.debug(
                                'Sending response to device %s:%s: %s',
                                host, port, resp.hex(' ')
                            )
                        # Signal the future that sending is done
                        self._done_sending.set_result(True)

                    hdr = msg.header
                    break

                if not found:
                    _LOGGER.debug(
                        "Unknown command from device, wire data: '%s'",
                        data.hex(' ')
                    )
                    hdr = G90CloudHeader.from_wire(data, context=ctx)

                # Advance to the next message
                data = data[hdr.message_length:]
        except G90CloudError as exc:
            _LOGGER.error('Error processing data from device: %s', exc)

    def upstream_connection_made(self, transport: BaseTransport) -> None:
        """
        Handle successful connection to the upstream server.

        :param transport: The transport for the upstream connection
        """
        self._upstream_transport = cast(Transport, transport)

    def upstream_connection_lost(self, exc: Optional[Exception]) -> None:
        """
        Handle connection loss to the upstream server.

        :param exc: Exception that caused the connection loss, if any
        """
        if exc:
            _LOGGER.debug('Upstream connection error: %s', exc)

        if self._upstream_transport:
            self._upstream_transport.close()
        self._upstream_transport = None

    def upstream_data_received(self, data: bytes) -> None:
        """
        Process data received from the upstream server.

        Forwards the data to the connected device.

        :param data: Bytes received from the upstream server
        """
        self.set_last_upstream_packet_time()

        _LOGGER.debug('Data received from upstream: %s', data.hex(' '))

        if self._transport:
            host, port = self._transport.get_extra_info('peername')
            _LOGGER.debug(
                'Sending upstream data to device %s:%s', host, port
            )
            self._transport.write(data)

    def get_upstream_protocol(self) -> BaseProtocol:
        """
        Create and return a protocol for the upstream connection.

        :return: Protocol for handling the upstream connection
        """
        class UpstreamProtocol(Protocol):
            """
            Protocol for handling the upstream connection.
            """
            def __init__(self, parent: G90CloudNotifications) -> None:
                """
                Initialize the upstream protocol.

                :param parent: The parent notifications service
                """
                self._parent = parent

            def connection_made(self, transport: BaseTransport) -> None:
                """
                Handle successful connection to the upstream server.

                :param transport: The transport for the upstream connection
                """
                self._parent.upstream_connection_made(transport)

            def connection_lost(self, exc: Optional[Exception]) -> None:
                """
                Handle connection loss to the upstream server.

                :param exc: Exception that caused the connection loss, if any
                """
                self._parent.upstream_connection_lost(exc)

            def data_received(self, data: bytes) -> None:
                """
                Process data received from the upstream server.

                :param data: Bytes received from the upstream server
                """
                self._parent.upstream_data_received(data)

        return UpstreamProtocol(self)

    async def send_upstream(self, data: bytes) -> None:
        """
        Send data to the upstream server.

        Creates a connection to the upstream server if one doesn't exist,
        then sends the provided data.

        :param data: Bytes to send to the upstream server
        """
        if not self._upstream_host or not self._upstream_port:
            return

        try:
            if not self._upstream_transport:
                _LOGGER.debug(
                    'Creating upstream connection to %s:%s',
                    self._upstream_host, self._upstream_port
                )
                loop = asyncio.get_running_loop()

                self._upstream_transport, _ = await loop.create_connection(
                    self.get_upstream_protocol,
                    host=self._upstream_host, port=self._upstream_port
                )

            if self._upstream_transport:
                self._upstream_transport.write(data)
                _LOGGER.debug(
                    'Data sent to upstream %s:%s',
                    self._upstream_host, self._upstream_port
                )
        except (OSError, asyncio.TimeoutError) as exc:
            _LOGGER.debug(
                'Error sending data to upstream %s:%s: %s',
                self._upstream_host, self._upstream_port, exc
            )

    async def listen(self) -> None:
        """
        Start listening for connections from devices.

        Creates a server bound to the configured local host and port.
        """
        loop = asyncio.get_running_loop()

        _LOGGER.debug('Creating cloud endpoint for %s:%s',
                      self._local_host,
                      self._local_port)
        self._server = await loop.create_server(
            lambda: self,
            self._local_host, self._local_port
        )

    async def close(self) -> None:
        """
        Close the server and any active connections.

        Waits for any pending operations to complete, then closes the upstream
        connection and the local server.
        """
        # Ensure all responses are sent to the panel
        if self._done_sending:
            await asyncio.wait([self._done_sending])

        # Wait for the upstream task to finish if it exists
        if self._upstream_task:
            await asyncio.wait([self._upstream_task])

        if self._upstream_transport:
            _LOGGER.debug(
                'Closing upstream connection to %s:%s',
                self._upstream_host, self._upstream_port
            )
            self._upstream_transport.close()
            self._upstream_transport = None

        if self._server:
            _LOGGER.debug(
                'No longer listening for cloud connections on %s:%s',
                self._local_host, self._local_port
            )
            self._server.close()
            self._server = None

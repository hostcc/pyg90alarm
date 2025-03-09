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
tbd
"""
from typing import Optional, cast, Callable
import logging
import asyncio
from asyncio.transports import BaseTransport, Transport
from asyncio.protocols import Protocol, BaseProtocol

from .protocol import (
    G90CloudHeader, G90CloudError, G90CloudMessageNoMatch
)
from .messages import (
    CLOUD_MESSAGE_CLASSES, G90CloudNotificationMessage,
    G90CloudStatusChangeAlarmReqMessage,
    G90CloudStatusChangeSensorReqMessage,
    G90CloudStatusChangeReqMessage,
)
from ..notifications.base import G90NotificationsBase
from ..notifications.protocol import G90NotificationProtocol


_LOGGER = logging.getLogger(__name__)


# pylint:disable=too-many-instance-attributes
class G90CloudNotifications(G90NotificationsBase, asyncio.Protocol):
    """
    tbd
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
        """
        tbd
        """
        super().__init__(protocol_factory)
        self._transport: Optional[Transport] = None
        self._server: Optional[asyncio.Server] = None
        self._local_host = local_host
        self._local_port = local_port
        self._upstream_host = upstream_host
        self._upstream_port = upstream_port
        self._keep_single_connection = keep_single_connection
        self._upstream_transport: Optional[Transport] = None

    def connection_made(self, transport: BaseTransport) -> None:
        """
        tbd
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
        tbd
        """
        if exc:
            _LOGGER.debug('Device connection error: %s', exc)

        if self._transport:
            self._transport.close()
        self._transport = None

    # pylint:disable=too-many-branches
    def data_received(self, data: bytes) -> None:
        """
        tbd
        """
        if self._transport is None:
            return

        if (
            self._upstream_host is not None
            and self._upstream_port is not None
        ):
            asyncio.create_task(self.send_upstream(data))

        host, port = self._transport.get_extra_info('peername')
        _LOGGER.debug(
            'Data received from device %s:%s: %s', host, port, data.hex(' ')
        )

        try:
            while len(data):
                found = False

                for cls in CLOUD_MESSAGE_CLASSES:
                    try:
                        msg = cls.from_wire(data)
                    except G90CloudMessageNoMatch:
                        continue

                    _LOGGER.debug("Cloud message received: %s", msg)

                    if cls == G90CloudNotificationMessage:
                        self.handle(msg.as_notification_message)

                    if cls in [
                        G90CloudStatusChangeAlarmReqMessage,
                        G90CloudStatusChangeSensorReqMessage,
                        G90CloudStatusChangeReqMessage,
                    ]:
                        alert = msg.as_device_alert
                        if alert:
                            self._handle_alert(alert, verify_device_id=False)

                    found = True

                    if not self._upstream_transport:
                        for resp in msg.wire_responses():
                            self._transport.write(resp)

                    hdr = msg.header
                    break

                if not found:
                    _LOGGER.debug(
                        "Unknown command from device, wire data: '%s'",
                        data.hex(' ')
                    )
                    hdr = G90CloudHeader.from_wire(data)

                # Advance to the next message
                data = data[hdr.message_length:]
        except G90CloudError as exc:
            _LOGGER.error('Error processing data from device: %s', exc)

    def upstream_connection_made(self, transport: BaseTransport) -> None:
        """
        tbd
        """
        self._upstream_transport = cast(Transport, transport)

    def upstream_connection_lost(self, exc: Optional[Exception]) -> None:
        """
        tbd
        """
        if exc:
            _LOGGER.debug('Upstream connection error: %s', exc)

        if self._upstream_transport:
            self._upstream_transport.close()
        self._upstream_transport = None

    def upstream_data_received(self, data: bytes) -> None:
        """
        tbd
        """
        _LOGGER.debug('Data received from upstream: %s', data.hex(' '))

        if self._transport:
            host, port = self._transport.get_extra_info('peername')
            _LOGGER.debug(
                'Sending upstream data to device %s:%s', host, port
            )
            self._transport.write(data)

    def get_upstream_protocol(self) -> BaseProtocol:
        """
        tbd
        """
        class UpstreamProtocol(Protocol):
            """
            tbd
            """
            def __init__(self, parent: G90CloudNotifications) -> None:
                """
                tbd
                """
                self._parent = parent

            def connection_made(self, transport: BaseTransport) -> None:
                """
                tbd
                """
                self._parent.upstream_connection_made(transport)

            def connection_lost(self, exc: Optional[Exception]) -> None:
                """
                tbd
                """
                self._parent.upstream_connection_lost(exc)

            def data_received(self, data: bytes) -> None:
                """
                tbd
                """
                self._parent.upstream_data_received(data)

        return UpstreamProtocol(self)

    async def send_upstream(self, data: bytes) -> None:
        """
        tbd
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
        except (ConnectionError, OSError, asyncio.TimeoutError) as exc:
            _LOGGER.debug(
                'Error sending data to upstream %s:%s: %s',
                self._upstream_host, self._upstream_port, exc
            )

    async def listen(self) -> None:
        """
        tbd
        """
        loop = asyncio.get_running_loop()

        _LOGGER.debug('Creating cloud endpoint for %s:%s',
                      self._local_host,
                      self._local_port)
        self._server = await loop.create_server(
            lambda: self,
            self._local_host, self._local_port
        )

    def close(self) -> None:
        """
        Closes the listener.
        """
        if self._server:
            _LOGGER.debug(
                'No longer listening for cloud connections on %s:%s',
                self._local_host, self._local_port
            )
            self._server.close()
            self._server = None

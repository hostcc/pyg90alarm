# Copyright (c) 2021 Ilia Sotnikov
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
Implements support for notifications/alerts sent by G90 alarm panel.
"""
import logging
from typing import (
    Optional, Tuple, Callable
)
import asyncio
from asyncio.transports import BaseTransport
from asyncio.protocols import DatagramProtocol

from ..notifications.base import G90NotificationsBase
from ..notifications.protocol import G90NotificationProtocol

_LOGGER = logging.getLogger(__name__)


class G90LocalNotifications(G90NotificationsBase, DatagramProtocol):
    """
    Implements support for notifications/alerts sent by alarm panel.

    There is a basic check to ensure only notifications/alerts from the correct
    device are processed - the check uses the host and port of the device, and
    the device ID (GUID) that is set by the ancestor class that implements the
    commands (e.g. :class:`G90Alarm`). The latter to work correctly needs a
    command to be performed first, one that fetches device GUID and then stores
    it using :attr:`.device_id` (e.g. :meth:`G90Alarm.get_host_info`).

    :param protocol_factory: A callable that returns a new instance of the
     :class:`G90NotificationProtocol` class.
    :param port: The port on which the device is listening for notifications.
    :param host: The host on which the device is listening for notifications.
    :param local_port: The port on which the local host is listening for
     notifications.
    :param local_host: The host on which the local host is listening for
     notifications.
    """
    def __init__(  # pylint:disable=too-many-arguments
        self, protocol_factory: Callable[[], G90NotificationProtocol],
        port: int, host: str, local_port: int, local_host: str,
    ):
        super().__init__(protocol_factory)

        self._host = host
        self._port = port
        self._notifications_local_host = local_host
        self._notifications_local_port = local_port

    # Implementation of datagram protocol,
    # https://docs.python.org/3/library/asyncio-protocol.html#datagram-protocols
    def connection_made(self, transport: BaseTransport) -> None:
        """
        Invoked when connection from the device is made.
        """

    def connection_lost(self, exc: Optional[Exception]) -> None:
        """
        Same but when the connection is lost.
        """

    def datagram_received(
        self, data: bytes, addr: Tuple[str, int]
    ) -> None:
        """
        Invoked when datagram is received from the device.
        """
        if self._host and self._host != addr[0]:
            _LOGGER.error(
                "Received notification/alert from wrong host '%s',"
                " expected from '%s'",
                addr[0], self._host
            )
            return

        self.set_last_device_packet_time()

        _LOGGER.debug('Received device message from %s:%s: %s',
                      addr[0], addr[1], data)

        self.handle(data)

    async def listen(self) -> None:
        """
        Listens for notifications/alerts from the device.
        """
        loop = asyncio.get_running_loop()

        _LOGGER.debug('Creating UDP endpoint for %s:%s',
                      self._notifications_local_host,
                      self._notifications_local_port)
        (self._transport,
         _protocol) = await loop.create_datagram_endpoint(
            lambda: self,
            local_addr=(
                self._notifications_local_host, self._notifications_local_port
            ))

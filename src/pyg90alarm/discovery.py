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
Discovers G90 alarm panels.
"""

import asyncio
from asyncio.transports import BaseTransport
from asyncio.protocols import BaseProtocol
from typing import Tuple, Any, List, Dict, cast
import logging

from .base_cmd import G90BaseCommand, Self
from .host_info import G90HostInfo
from .const import G90Commands

_LOGGER = logging.getLogger(__name__)


class G90DiscoveryProtocol:
    """
    tbd

    :meta private:
    """
    def __init__(self, parent: 'G90Discovery') -> None:
        """
        tbd
        """
        self._parent = parent

    def connection_made(self, transport: BaseTransport) -> None:
        """
        tbd
        """

    def connection_lost(self, exc: Exception) -> None:
        """
        tbd
        """

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        """
        tbd
        """
        try:
            ret = self._parent.from_wire(data)
            host_info = G90HostInfo(*ret)
            _LOGGER.debug('Received from %s:%s: %s', addr[0], addr[1], ret)
            res = {
                'guid': host_info.host_guid,
                'host': addr[0],
                'port': addr[1]
            }
            res.update(host_info._asdict())
            _LOGGER.debug('Discovered device: %s', res)
            self._parent.add_device(res)

        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.warning('Got exception, ignoring: %s', exc)

    def error_received(self, exc: Exception) -> None:
        """
        tbd
        """


class G90Discovery(G90BaseCommand):
    """
    tbd
    """
    # pylint: disable=too-few-public-methods
    def __init__(self, timeout: float = 10, **kwargs: Any):
        """
        tbd
        """
        # pylint: disable=too-many-arguments
        super().__init__(code=G90Commands.GETHOSTINFO, timeout=timeout,
                         **kwargs)
        self._discovered_devices: List[Dict[str, Any]] = []

    async def process(self) -> Self:
        """
        tbd
        """
        _LOGGER.debug('Attempting device discovery...')
        transport, _ = await self._create_connection()
        transport.sendto(self.to_wire())
        await asyncio.sleep(self._timeout)
        transport.close()
        _LOGGER.debug('Discovered %s devices', len(self.devices))
        return cast(Self, self)

    @property
    def devices(self) -> List[Dict[str, Any]]:
        """
        tbd
        """
        return self._discovered_devices

    def add_device(self, value: Dict[str, Any]) -> None:
        """
        tbd
        """
        self._discovered_devices.append(value)

    def _proto_factory(self) -> BaseProtocol:
        """
        tbd
        """
        proto = G90DiscoveryProtocol(self)
        return cast(BaseProtocol, proto)

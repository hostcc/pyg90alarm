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
import logging

from .base_cmd import G90BaseCommand
from .host_info import G90HostInfo
from .const import G90Commands

_LOGGER = logging.getLogger(__name__)


class G90DiscoveryProtocol:
    """
    tbd

    :meta private:
    """
    def __init__(self, parent):
        """
        tbd
        """
        self._parent = parent

    def connection_made(self, transport):
        """
        tbd
        """

    def connection_lost(self, exc):
        """
        tbd
        """

    def datagram_received(self, data, addr):
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

    def error_received(self, exc):
        """
        tbd
        """


class G90Discovery(G90BaseCommand):
    """
    tbd
    """
    # pylint: disable=too-few-public-methods
    def __init__(self, timeout=10, **kwargs):
        """
        tbd
        """
        # pylint: disable=too-many-arguments
        super().__init__(code=G90Commands.GETHOSTINFO, timeout=timeout,
                         **kwargs)
        self._discovered_devices = []

    async def process(self):
        """
        tbd
        """
        _LOGGER.debug('Attempting device discovery...')
        transport, _ = await self._create_connection()
        transport.sendto(self.to_wire())
        await asyncio.sleep(self._timeout)
        transport.close()
        _LOGGER.debug('Discovered %s devices', len(self.devices))
        return self.devices

    @property
    def devices(self):
        """
        tbd
        """
        return self._discovered_devices

    def add_device(self, value):
        """
        tbd
        """
        self._discovered_devices.append(value)

    def _proto_factory(self):
        """
        tbd
        """
        return G90DiscoveryProtocol(self)

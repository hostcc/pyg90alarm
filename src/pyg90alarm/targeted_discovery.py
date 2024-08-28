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
Discovers G90 alarm panel devices with specific ID.
"""

import logging
from typing import NamedTuple, Tuple, Any, Optional
from asyncio.transports import BaseTransport
from .discovery import G90Discovery
from .exceptions import G90Error

_LOGGER = logging.getLogger(__name__)


class G90TargetedDiscoveryInfo(NamedTuple):
    """
    tbd

    :meta private:
    """
    message: str
    product_name: str
    wifi_protocol_version: str
    cloud_protocol_version: str
    mcu_hw_version: str
    fw_version: str
    gsm_status: str
    wifi_status: str
    server_status: str
    reserved1: str
    reserved2: str
    gsm_signal_level: str
    wifi_signal_level: str


class G90TargetedDiscovery(G90Discovery):
    """
    tbd
    """
    # pylint: disable=too-few-public-methods
    def __init__(self, device_id: str, **kwargs: Any):
        """
        tbd
        """
        super().__init__(**kwargs)
        self._device_id = device_id

    def connection_made(self, transport: BaseTransport) -> None:
        """
        tbd
        """

    def connection_lost(self, exc: Optional[Exception]) -> None:
        """
        tbd
        """

    # Implementation of datagram protocol,
    # https://docs.python.org/3/library/asyncio-protocol.html#datagram-protocols
    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        """
        tbd
        """
        try:
            _LOGGER.debug('Received from %s:%s: %s', addr[0], addr[1], data)
            decoded = data.decode('utf-8', errors='ignore')
            if not decoded.endswith('\0'):
                raise G90Error('Invalid discovery response')
            host_info = G90TargetedDiscoveryInfo(*decoded[:-1].split(','))
            if host_info.message != 'IWTAC_PROBE_DEVICE_ACK':
                raise G90Error('Invalid discovery response')
            res = {'guid': self._device_id,
                   'host': addr[0],
                   'port': addr[1]}
            res.update(host_info._asdict())
            _LOGGER.debug('Discovered device: %s', res)
            self.add_device(res)
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.warning('Got exception, ignoring: %s', exc)

    def error_received(self, exc: Exception) -> None:
        """
        tbd
        """

    def to_wire(self) -> bytes:
        """
        tbd
        """
        return bytes(f'IWTAC_PROBE_DEVICE,{self._device_id}\0', 'ascii')

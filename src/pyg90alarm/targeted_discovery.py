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
from __future__ import annotations
import logging
from typing import Tuple, Any, Optional, Dict, List
from dataclasses import dataclass, asdict
import asyncio
from asyncio.transports import BaseTransport
from .base_cmd import G90BaseCommand
from .const import G90Commands
from .exceptions import G90Error

_LOGGER = logging.getLogger(__name__)


@dataclass
# pylint: disable=too-many-instance-attributes
class G90TargetedDiscoveryInfo:
    """
    Wire representation of the information about discovered device.
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

    def _asdict(self) -> Dict[str, Any]:
        """
        Returns the information about discovered device as dictionary.
        """
        return asdict(self)


@dataclass
class G90DiscoveredDeviceTargeted(G90TargetedDiscoveryInfo):
    """
    Discovered device with specific ID.
    """
    host: str
    port: int
    guid: str


class G90TargetedDiscovery(G90BaseCommand):
    """
    Discovers alarm panel devices with specific ID.
    """
    # pylint: disable=too-few-public-methods
    def __init__(self, device_id: str, **kwargs: Any):
        super().__init__(
            # No actual command will be processed by base class, `NONE` is used
            # for proper typing only
            code=G90Commands.NONE, **kwargs
        )
        self._device_id = device_id
        self._discovered_devices: List[G90DiscoveredDeviceTargeted] = []

    def connection_made(self, transport: BaseTransport) -> None:
        """
        Invoked when connection is established.
        """

    def connection_lost(self, exc: Optional[Exception]) -> None:
        """
        Invoked when connection is lost.
        """

    # Implementation of datagram protocol,
    # https://docs.python.org/3/library/asyncio-protocol.html#datagram-protocols
    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        """
        Invoked when datagram is received.
        """
        try:
            _LOGGER.debug('Received from %s:%s: %s', addr[0], addr[1], data)
            try:
                decoded = data.decode('utf-8')
            except UnicodeDecodeError as exc:
                raise G90Error(
                    'Unable to decode discovery response from UTF-8'
                ) from exc
            if not decoded.endswith('\0'):
                raise G90Error('Invalid discovery response')
            host_info = G90TargetedDiscoveryInfo(*decoded[:-1].split(','))
            if host_info.message != 'IWTAC_PROBE_DEVICE_ACK':
                raise G90Error('Invalid discovery response')
            res = G90DiscoveredDeviceTargeted(
                host=addr[0],
                port=addr[1],
                guid=self._device_id,
                **host_info._asdict()
            )
            _LOGGER.debug('Discovered device: %s', res)
            self.add_device(res)
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.warning('Got exception, ignoring: %s', exc)

    def error_received(self, exc: Exception) -> None:
        """
        Invoked when error is received.
        """

    def to_wire(self) -> bytes:
        """
        Converts the command to wire representation.
        """
        return bytes(f'IWTAC_PROBE_DEVICE,{self._device_id}\0', 'ascii')

    async def process(self) -> G90TargetedDiscovery:
        """
        Initiates the device discovery process.
        """
        _LOGGER.debug('Attempting device discovery...')
        transport, _ = await self._create_connection()
        transport.sendto(self.to_wire())
        await asyncio.sleep(self._timeout)
        transport.close()
        _LOGGER.debug('Discovered %s devices', len(self.devices))
        return self

    @property
    def devices(self) -> List[G90DiscoveredDeviceTargeted]:
        """
        The list of discovered devices.
        """
        return self._discovered_devices

    def add_device(self, value: G90DiscoveredDeviceTargeted) -> None:
        """
        Adds discovered device to the list.
        """
        self._discovered_devices.append(value)

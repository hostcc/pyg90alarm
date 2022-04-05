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
from collections import namedtuple
from .discovery import G90Discovery
from .exceptions import G90Error

_LOGGER = logging.getLogger(__name__)

INCOMING_FIELDS = [
    'message',
    'product_name',
    'wifi_protocol_version',
    'cloud_protocol_version',
    'mcu_hw_version',
    'fw_version',
    'gsm_status',
    'wifi_status',
    'server_status',
    'reserved1',
    'reserved2',
    'gsm_signal_level',
    'wifi_signal_level'
]


class G90TargetedDiscoveryInfo(namedtuple('G90TargetedDiscoveryInfo',
                                          INCOMING_FIELDS)):
    """
    tbd

    :meta private:
    """


class G90TargetedDiscoveryProtocol:
    """
    tbd

    :meta private:
    """
    def __init__(self, device_id, parent):
        """
        tbd
        """
        self._parent = parent
        self._device_id = device_id

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
            self._parent.add_device(res)
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.warning('Got exception, ignoring: %s', exc)

    def error_received(self, exc):
        """
        tbd
        """


class G90TargetedDiscovery(G90Discovery):
    """
    tbd
    """

    # pylint: disable=too-few-public-methods
    def __init__(self, device_id, **kwargs):
        """
        tbd
        """

        super().__init__(**kwargs)
        self._device_id = device_id

    def to_wire(self):  # pylint: disable=no-self-use
        """
        tbd
        """
        return bytes(f'IWTAC_PROBE_DEVICE,{self._device_id}\0', 'ascii')

    def _proto_factory(self):
        """
        tbd
        """
        return G90TargetedDiscoveryProtocol(self._device_id,
                                            self)

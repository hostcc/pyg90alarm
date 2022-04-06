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
Protocol entity for G90 alarm panel information.
"""

from collections import namedtuple
from enum import IntEnum

INCOMING_FIELDS = [
    'host_guid',
    'product_name',
    'wifi_protocol_version',
    'cloud_protocol_version',
    'mcu_hw_version',
    'wifi_hw_version',
    'gsm_status_data',
    'wifi_status_data',
    'reserved1',
    'reserved2',
    'band_frequency',
    'gsm_signal_level',
    'wifi_signal_level'
]


class G90HostInfoGsmStatus(IntEnum):
    """
    Defines possible values of GSM module status.
    """
    POWERED_OFF = 0
    SIM_ABSENT = 1
    NO_SIGNAL = 2
    OPERATIONAL = 3


class G90HostInfoWifiStatus(IntEnum):
    """
    Defines possible values of Wifi module status.
    """
    POWERED_OFF = 0
    NOT_CONNECTED = 1
    OPERATIONAL = 3


class G90HostInfo(namedtuple('G90HostInfo', INCOMING_FIELDS)):
    """
    Interprets data fields of GETHOSTINFO command.
    """
    @property
    def gsm_status(self):
        """
        Translates the GSM module status received from the device into
        corresponding enum.

        :return: :class:`G90HostInfoGsmStatus`
        """
        return G90HostInfoGsmStatus(self.gsm_status_data)

    @property
    def wifi_status(self):
        """
        Translates the Wifi module status received from the device into
        corresponding enum.

        :return: :class:`G90HostInfoWifiStatus`
        """
        return G90HostInfoWifiStatus(self.wifi_status_data)

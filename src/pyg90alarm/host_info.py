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
from __future__ import annotations
from typing import Any, Dict
from dataclasses import dataclass, asdict
from enum import IntEnum


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
    NO_SIGNAL = 2
    OPERATIONAL = 3


@dataclass
class G90HostInfo:  # pylint: disable=too-many-instance-attributes
    """
    Interprets data fields of GETHOSTINFO command.
    """
    host_guid: str
    product_name: str
    wifi_protocol_version: str
    cloud_protocol_version: str
    mcu_hw_version: str
    wifi_hw_version: str
    gsm_status_data: int
    wifi_status_data: int
    reserved1: int
    reserved2: int
    band_frequency: str
    gsm_signal_level: int
    wifi_signal_level: int

    @property
    def gsm_status(self) -> G90HostInfoGsmStatus:
        """
        Translates the GSM module status received from the device into
        corresponding enum.
        """
        return G90HostInfoGsmStatus(self.gsm_status_data)

    @property
    def wifi_status(self) -> G90HostInfoWifiStatus:
        """
        Translates the Wifi module status received from the device into
        corresponding enum.
        """
        return G90HostInfoWifiStatus(self.wifi_status_data)

    def _asdict(self) -> Dict[str, Any]:
        """
        Returns the host information as dictionary.
        """
        return asdict(self)

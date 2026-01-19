# Copyright (c) 2026 Ilia Sotnikov
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
Interprets network configuration data fields of GETAPINFO/SETAPINFO commands.
"""
from __future__ import annotations
from enum import IntEnum
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from ..const import G90Commands
from ..dataclass.load_save import DataclassLoadSave, Metadata
from ..dataclass.validation import validated_int_field, validated_string_field


class G90APNAuth(IntEnum):
    """
    Supported APN authentication methods.
    """
    NONE = 0
    PAP = 1
    CHAP = 2
    PAP_OR_CHAP = 3


@dataclass
class G90NetConfig(DataclassLoadSave):
    """
    Interprets data fields of GETAPINFO/SETAPINFO commands.
    """
    # pylint: disable=too-many-instance-attributes
    LOAD_COMMAND = G90Commands.GETAPINFO
    SAVE_COMMAND = G90Commands.SETAPINFO

    # The field constraints below have been determined experimentally by
    # entering various values into panel configuration manually. All values
    # received from the panel remotely are trusted (i.e. bypass validation)

    # Whether the access point is enabled, so that the device can be accessed
    # via WiFi
    _ap_enabled: int = validated_int_field(
        min_value=False, max_value=True, trust_initial_value=True
    )
    # Access point password
    ap_password: str = validated_string_field(
        min_length=9, max_length=64, trust_initial_value=True
    )
    # Whether WiFi is enabled, so that the device can connect to WiFi network
    _wifi_enabled: int = validated_int_field(
        min_value=False, max_value=True, trust_initial_value=True
    )
    # Whether GPRS is enabled, so that the device can connect via cellular
    # network
    _gprs_enabled: int = validated_int_field(
        min_value=False, max_value=True, trust_initial_value=True
    )
    # Access Point Name (APN) for GPRS connection, as provided by the cellular
    # operator
    apn_name: str = validated_string_field(
        min_length=1, max_length=100, trust_initial_value=True
    )
    # User name for APN authentication, as provided by the cellular operator
    apn_user: str = validated_string_field(
        min_length=0, max_length=64, trust_initial_value=True
    )
    # Password for APN authentication, as provided by the cellular operator
    apn_password: str = validated_string_field(
        min_length=0, max_length=64, trust_initial_value=True
    )
    # APN authentication method, as provided by the cellular operator
    _apn_auth: int = validated_int_field(
        min_value=min(G90APNAuth), max_value=max(G90APNAuth),
        trust_initial_value=True
    )
    # GSM operator code, optional for devices lacking cellular module.
    # The field is always skipped when saving to device.
    gsm_operator: Optional[str] = field(
        metadata={Metadata.NO_SERIALIZE: True},
        default=None
    )

    @property
    def ap_enabled(self) -> bool:
        """
        Returns whether the access point is enabled.
        """
        return bool(self._ap_enabled)

    @ap_enabled.setter
    def ap_enabled(self, value: bool) -> None:
        self._ap_enabled = int(value)

    @property
    def wifi_enabled(self) -> bool:
        """
        Returns whether WiFi is enabled.
        """
        return bool(self._wifi_enabled)

    @wifi_enabled.setter
    def wifi_enabled(self, value: bool) -> None:
        self._wifi_enabled = int(value)

    @property
    def gprs_enabled(self) -> bool:
        """
        Returns whether GPRS is enabled.
        """
        return bool(self._gprs_enabled)

    @gprs_enabled.setter
    def gprs_enabled(self, value: bool) -> None:
        self._gprs_enabled = int(value)

    @property
    def apn_auth(self) -> G90APNAuth:
        """
        Returns the APN authentication method as an enum.
        """
        return G90APNAuth(self._apn_auth)

    @apn_auth.setter
    def apn_auth(self, value: G90APNAuth) -> None:
        self._apn_auth = value.value

    def _asdict(self) -> Dict[str, Any]:
        return {
            'ap_enabled': self.ap_enabled,
            'ap_password': '********',
            'wifi_enabled': self.wifi_enabled,
            'gprs_enabled': self.gprs_enabled,
            'apn_name': self.apn_name,
            'apn_user': self.apn_user,
            'apn_password': '********',
            'apn_auth': self.apn_auth,
            'gsm_operator': self.gsm_operator
        }

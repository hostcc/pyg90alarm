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
Protocol entity for G90 alarm panel phone numbers.
"""
from __future__ import annotations
from typing import Dict, Any
from dataclasses import dataclass
from ..const import G90Commands
from .dataclass_load_save import DataclassLoadSave


@dataclass
class G90AlarmPhones(DataclassLoadSave):
    """
    Interprets data fields of GETALMPHONE/SETALMPHONE commands.
    """
    # pylint: disable=too-many-instance-attributes
    LOAD_COMMAND = G90Commands.GETALMPHONE
    SAVE_COMMAND = G90Commands.SETALMPHONE

    # Password to operate the panel via SMS or incoming call.
    panel_password: str
    # Phone number of the alarm panel's SIM card.
    panel_phone_number: str
    # Alarm phone number to be called on alarm.
    # Should be in country code + number format.
    phone_number_1: str
    # Same, but for second alarm phone number.
    phone_number_2: str
    # Same, but for third alarm phone number.
    phone_number_3: str
    # Same, but for fourth alarm phone number.
    phone_number_4: str
    # Same, but for fifth alarm phone number.
    phone_number_5: str
    # Same, but for sixth alarm phone number.
    phone_number_6: str
    # Phone number to send SMS notifications on alarm.
    # Should be in country code + number format.
    sms_push_number_1: str
    # Same, but for second SMS notification phone number.
    sms_push_number_2: str

    def _asdict(self) -> Dict[str, Any]:
        """
        Returns the dataclass fields as a dictionary, masking sensitive data.
        """
        return {
            'panel_password': '********',
            'panel_phone_number': self.panel_phone_number,
            'phone_number_1': self.phone_number_1,
            'phone_number_2': self.phone_number_2,
            'phone_number_3': self.phone_number_3,
            'phone_number_4': self.phone_number_4,
            'phone_number_5': self.phone_number_5,
            'phone_number_6': self.phone_number_6,
            'sms_push_number_1': self.sms_push_number_1,
            'sms_push_number_2': self.sms_push_number_2,
        }

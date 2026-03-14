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
Interprets configuration data fields for CID (Contact ID) phone reporting,
GETCID/SETCID commands.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict

from ..const import G90Commands
from ..dataclass.load_save import DataclassLoadSave
from ..dataclass.validation import (
    validated_int_field,
    validated_string_field,
)


@dataclass
class G90CidConfig(DataclassLoadSave):
    """
    Interprets data fields of GETCID/SETCID commands.
    """

    LOAD_COMMAND = G90Commands.GETCID
    SAVE_COMMAND = G90Commands.SETCID

    # All values received from the panel are trusted.

    # Primary receiver phone number
    phone1: str = validated_string_field(
        min_length=0, max_length=15, trust_initial_value=True
    )
    # Secondary receiver phone number
    phone2: str = validated_string_field(
        min_length=0, max_length=15, trust_initial_value=True
    )
    # User identifier
    user: str = validated_string_field(
        min_length=0, max_length=7, trust_initial_value=True
    )
    # Whether CID phone reporting is enabled (0/1)
    _enabled: int = validated_int_field(
        min_value=0, max_value=1, trust_initial_value=True
    )
    # Event flags bitmask (always set to 'FFFF' on save)
    event_flags: str = validated_string_field(
        min_length=0, max_length=4, trust_initial_value=True
    )

    @property
    def enabled(self) -> bool:
        """
        Returns whether CID phone reporting is enabled.
        """
        return bool(self._enabled)

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = int(value)

    def serialize(self) -> list[Any]:
        """
        Returns the dataclass fields as a list suitable for SETCID.

        The `event_flags` element is always set to `FFFF` regardless
        of the current value, as expected by the panel.
        """
        self.event_flags = 'FFFF'
        return super().serialize()

    def _asdict(self) -> Dict[str, Any]:
        """
        Returns the dataclass fields as a dictionary for logging/debugging.
        """
        return {
            "phone1": self.phone1,
            "phone2": self.phone2,
            "user": self.user,
            "enabled": self.enabled,
            "event_flags": self.event_flags,
        }

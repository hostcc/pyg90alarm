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
Interprets configuration data fields for SIA Internet reporting, GETSIA/SETSIA
commands.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..const import G90Commands
from ..dataclass.load_save import (
    DataclassLoadSave,
    LoadOnceDataclassLoadPolicy,
    field_readonly_if_not_provided,
)
from ..dataclass.validation import (
    validated_int_field,
    validated_string_field,
)


@dataclass
class G90SiaConfig(DataclassLoadSave):
    """
    Interprets data fields of GETSIA/SETSIA commands.
    """
    # pylint: disable=too-many-instance-attributes

    LOAD_COMMAND = G90Commands.GETSIA
    SAVE_COMMAND = G90Commands.SETSIA
    # Due to an apparent bug in certain panel firmware versions, loading SIA
    # configuration periodically (seems in range of 10-20 iterations) leads to
    # paginated commands timing out. Hence, the configuration is loaded once
    # and then reused until the next load to avoid the issue.
    LOAD_POLICY = LoadOnceDataclassLoadPolicy()

    # IP address or hostname of the central station receiver
    host: str = validated_string_field(
        min_length=0, max_length=23, trust_initial_value=True
    )
    # Port of the central station receiver
    port: int = validated_int_field(
        min_value=0, max_value=65535, trust_initial_value=True
    )
    # Account identifier
    account: str = validated_string_field(
        min_length=0, max_length=30, trust_initial_value=True
    )
    # Receiver identifier/name
    receiver: str = validated_string_field(
        min_length=0, max_length=15, trust_initial_value=True
    )
    # Prefix for messages
    prefix: str = validated_string_field(
        min_length=0, max_length=15, trust_initial_value=True
    )
    # AES key (typically hex-encoded)
    aes_key: str = validated_string_field(
        min_length=0, max_length=19, trust_initial_value=True
    )
    # Whether encryption is enabled (0/1)
    _encryption: int = validated_int_field(
        min_value=0, max_value=1, trust_initial_value=True
    )
    # Whether SIA Internet reporting is enabled (0/1)
    _enabled: int = validated_int_field(
        min_value=0, max_value=1, trust_initial_value=True
    )
    # Event flags bitmask (always set to 'FFFFFFFF' on save)
    event_flags: str = validated_string_field(
        min_length=0, max_length=8, trust_initial_value=True
    )
    # Optional heartbeat interval, could only be modified if the
    # device has sent a value for it when loading the data (i.e. has a SIA
    # support enabled) otherwise it is read-only and None.
    # Valid values are 60-86400 seconds (not yet enforced by validation)
    heartbeat_interval: Optional[int] = field_readonly_if_not_provided(
        default=None
    )

    @property
    def encryption(self) -> bool:
        """
        Returns whether SIA encryption is enabled.
        """
        return bool(self._encryption)

    @encryption.setter
    def encryption(self, value: bool) -> None:
        self._encryption = int(value)
        self._dirty_fields.add('_encryption')

    @property
    def enabled(self) -> bool:
        """
        Returns whether SIA Internet reporting is enabled.
        """
        return bool(self._enabled)

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = int(value)
        self._dirty_fields.add('_enabled')

    def serialize(self) -> list[Any]:
        """
        Returns the dataclass fields as a list suitable for SETSIA.

        The `event_flags` element is always set to `FFFFFFFF`
        regardless of the current value, as expected by the panel.
        """
        # Serialize mutates the payload only; we must not permanently alter
        # local in-memory state because DataclassLoadSave.save() later
        # re-syncs fields from the refreshed instance.
        original_event_flags = self.event_flags
        try:
            self.event_flags = 'FFFFFFFF'
            return super().serialize()
        finally:
            self.event_flags = original_event_flags

    def _asdict(self) -> Dict[str, Any]:
        """
        Returns the dataclass fields as a dictionary for logging/debugging.
        """
        return {
            "host": self.host,
            "port": self.port,
            "account": self.account,
            "receiver": self.receiver,
            "prefix": self.prefix,
            "aes_key": "********",
            "encryption": self.encryption,
            "enabled": self.enabled,
            "event_flags": self.event_flags,
            "heartbeat_interval": self.heartbeat_interval,
        }

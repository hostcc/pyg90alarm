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
Represents various configuration aspects of the alarm panel.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Optional
import logging
from dataclasses import dataclass
from enum import IntFlag
from ..const import G90Commands
if TYPE_CHECKING:
    from ..alarm import G90Alarm


class G90AlertConfigFlags(IntFlag):
    """
    Alert configuration flags, used bitwise
    """
    AC_POWER_FAILURE = 1
    AC_POWER_RECOVER = 2
    ARM_DISARM = 4
    HOST_LOW_VOLTAGE = 8
    SENSOR_LOW_VOLTAGE = 16
    WIFI_AVAILABLE = 32
    WIFI_UNAVAILABLE = 64
    DOOR_OPEN = 128
    DOOR_CLOSE = 256
    SMS_PUSH = 512
    UNKNOWN1 = 2048
    UNKNOWN2 = 8192


_LOGGER = logging.getLogger(__name__)


@dataclass
class G90AlertConfigData:
    """
    Represents alert configuration data as received from the alarm panel.
    """
    flags_data: int

    @property
    def flags(self) -> G90AlertConfigFlags:
        """
        :return: The alert configuration flags
        """
        return G90AlertConfigFlags(self.flags_data)

    @flags.setter
    def flags(self, value: G90AlertConfigFlags) -> None:
        """
        :param value: The alert configuration flags
        """
        self.flags_data = value.value


class G90AlertConfig:
    """
    Represents alert configuration as received from the alarm panel.
    """
    def __init__(self, parent: G90Alarm) -> None:
        self._alert_config: Optional[G90AlertConfigData] = None
        self.parent = parent

    async def _get(self) -> G90AlertConfigData:
        """
        Retrieves the alert configuration flags from the device. Please note
        the configuration is cached upon first call, so you need to
        re-instantiate the class to reflect any updates there.

        :return: The alerts configured
        """
        if not self._alert_config:
            self._alert_config = await self._get_uncached()
        return self._alert_config

    async def _get_uncached(self) -> G90AlertConfigData:
        """
        Retrieves the alert configuration flags directly from the device.

        :return: The alerts configured
        """
        _LOGGER.debug('Retrieving alert configuration from the device')
        res = await self.parent.command(G90Commands.GETNOTICEFLAG)
        data = G90AlertConfigData(*res)
        _LOGGER.debug(
            'Alert configuration: %s, flags: %s', data,
            repr(data.flags)
        )
        return data

    async def set(self, flags: G90AlertConfigFlags) -> None:
        """
        Sets the alert configuration flags on the device.
        """
        # Use uncached method retrieving the alert configuration, to ensure the
        # actual value retrieved from the device
        _LOGGER.debug('Setting alert configuration to %s', repr(flags))
        alert_config = await self._get_uncached()
        if alert_config != self._alert_config:
            _LOGGER.warning(
                'Alert configuration changed externally,'
                ' overwriting (read "%s", will be set to "%s")',
                repr(alert_config), repr(flags)
            )
        await self.parent.command(G90Commands.SETNOTICEFLAG, [flags.value])
        # Update the alert configuration stored
        (await self._get()).flags = flags

    async def get_flag(self, flag: G90AlertConfigFlags) -> bool:
        """
        :param flag: The flag to check
        """
        return flag in await self.flags

    async def set_flag(self, flag: G90AlertConfigFlags, value: bool) -> None:
        """
        :param flag: The flag to set
        :param value: The value to set
        """
        # Skip updating the flag if it has the desired value
        if await self.get_flag(flag) == value:
            _LOGGER.debug(
                'Flag %s already set to %s, skipping update',
                repr(flag), value
            )
            return

        # Invert corresponding user flag and set it
        flags = await self.flags ^ flag
        await self.set(flags)

    @property
    async def flags(self) -> G90AlertConfigFlags:
        """
        :return: Symbolic names for corresponding flag bits
        """
        return (await self._get()).flags

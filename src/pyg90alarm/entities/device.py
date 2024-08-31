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
Provides interface to devices (switches) of G90 alarm panel.
"""
from __future__ import annotations
import logging
from .sensor import G90Sensor
from ..const import G90Commands


_LOGGER = logging.getLogger(__name__)


class G90Device(G90Sensor):
    """
    Interacts with device (relay) on G90 alarm panel.
    """

    async def turn_on(self) -> None:
        """
        Turns on the device (relay)
        """
        await self.parent.command(G90Commands.CONTROLDEVICE,
                                  [self.index, 0, self.subindex])

    async def turn_off(self) -> None:
        """
        Turns off the device (relay)
        """
        await self.parent.command(G90Commands.CONTROLDEVICE,
                                  [self.index, 1, self.subindex])

    @property
    def supports_enable_disable(self) -> bool:
        """
        Indicates if disabling/enabling the device (relay) is supported.

        :return: Support for enabling/disabling the device
        """
        # No support for manipulating of disable/enabled for the device, since
        # single protocol entity read from the G90 alarm panel results in
        # multiple `G90Device` instances and changing the state would
        # subsequently require a design change to allow multiple entities to
        # reflect that. Multiple device entities are for multi-channel relays
        # mostly.
        return False

    async def set_enabled(self, value: bool) -> None:
        """
        Changes the disabled/enabled state of the device (relay).

        :param value: Whether to enable or disable the device
        """
        _LOGGER.warning(
            'Manipulating with enable/disable for device is unsupported'
        )

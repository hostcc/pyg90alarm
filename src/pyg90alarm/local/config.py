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
from enum import IntFlag
from dataclasses import dataclass


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


@dataclass
class G90AlertConfig:
    """
    Represents alert configuration as received from the alarm panel.
    """
    flags_data: int

    @property
    def flags(self) -> G90AlertConfigFlags:
        """
        :return: Symbolic names for corresponding flag bits
        """
        return G90AlertConfigFlags(self.flags_data)

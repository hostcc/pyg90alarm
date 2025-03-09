# Copyright (c) 2025 Ilia Sotnikov
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
tbd
"""
from enum import IntEnum


class G90CloudDirection(IntEnum):
    """
    tbd
    """
    UNSPECIFIED = 0
    CLOUD = 32  # 0x20
    DEVICE = 16  # 0x10
    DEVICE_DISCOVERY = 48  # 0x30
    CLOUD_DISCOVERY = 208  # 0xD0


class G90CloudCommand(IntEnum):
    """
    tbd
    """
    HELLO = 0x01
    HELLO_ACK = 0x41
    NOTIFICATION = 0x22
    STATUS_CHANGE = 0x21
    HELLO_INFO = 0x63
    COMMAND = 0x29

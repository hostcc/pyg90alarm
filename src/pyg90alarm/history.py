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
History protocol entity.
"""

import time
from collections import namedtuple

INCOMING_FIELDS = [
    'log_type',  # (1 or 3 - alarm, 2 or 4 - notification)
    'param1',    # (type 1: 1 - SOS, 2 - tamper alarm; type 3 - device ID; type
                 #  2 - 5 stayarm, 3 - disarm, 4 - awayarm )
    'param2',    # (type 3: device type)
    'param3',
    'sensor_name',
    'unix_time',
    'rest',
]


class G90History(namedtuple('G90History', INCOMING_FIELDS)):
    """
    tbd
    """

    @property
    def datetime(self):
        """
        tbd
        """
        return time.ctime(self.unix_time)

    def __repr__(self):
        """
        tbd
        """
        return super().__repr__() + f'(datetime={str(self.datetime)})'

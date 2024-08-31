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
Python package to control G90-based alarm systems.
"""

from .alarm import G90Alarm
from .base_cmd import G90BaseCommand
from .paginated_result import G90PaginatedResult
from .device_notifications import (
    G90DeviceAlert,
)
from .entities.sensor import G90Sensor, G90SensorTypes
from .entities.device import G90Device
from .host_info import (
    G90HostInfo, G90HostInfoWifiStatus, G90HostInfoGsmStatus
)
from .host_status import G90HostStatus
from .const import (
    G90MessageTypes,
    G90NotificationTypes,
    G90ArmDisarmTypes,
    G90AlertTypes,
    G90AlertSources,
    G90AlertStates,
    G90AlertStateChangeTypes,
    G90HistoryStates,
)
from .exceptions import G90Error, G90TimeoutError

__all__ = [
    'G90Alarm', 'G90BaseCommand', 'G90PaginatedResult', 'G90DeviceAlert',
    'G90Sensor', 'G90SensorTypes', 'G90Device', 'G90HostInfo',
    'G90HostInfoWifiStatus', 'G90HostInfoGsmStatus', 'G90HostStatus',
    'G90MessageTypes', 'G90NotificationTypes', 'G90ArmDisarmTypes',
    'G90AlertTypes', 'G90AlertSources', 'G90AlertStates',
    'G90AlertStateChangeTypes', 'G90HistoryStates', 'G90Error',
    'G90TimeoutError',
]

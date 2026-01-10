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
from .local.base_cmd import G90BaseCommand
from .local.paginated_result import G90PaginatedResult
from .notifications.base import (
    G90DeviceAlert,
)
from .entities.sensor import (
    G90Sensor, G90SensorAlertModes, G90SensorUserFlags
)
from .entities.device import G90Device
from .local.host_info import (
    G90HostInfo, G90HostInfoWifiStatus, G90HostInfoGsmStatus
)
from .definitions.sensors import (
    G90SensorDefinitions
)
from .definitions.devices import (
    G90DeviceDefinitions
)
from .definitions.base import (
    G90PeripheralTypes,
)
from .local.alert_config import G90AlertConfigFlags
from .local.host_status import G90HostStatus
from .local.host_config import (
    G90HostConfig, G90VolumeLevel, G90SpeechLanguage
)
from .local.alarm_phones import G90AlarmPhones
from .local.net_config import G90NetConfig, G90APNAuth
from .local.history import G90History
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
from .exceptions import (
    G90Error, G90TimeoutError, G90CommandError, G90CommandFailure,
    G90EntityRegistrationError, G90PeripheralDefinitionNotFound,
)

__all__ = [
    'G90Alarm', 'G90BaseCommand', 'G90PaginatedResult', 'G90DeviceAlert',
    # Sensors and related
    'G90Sensor', 'G90PeripheralTypes', 'G90SensorAlertModes',
    'G90SensorUserFlags',
    'G90AlertConfigFlags',
    'G90Device',
    # Panel information and status
    'G90HostInfo', 'G90HostInfoWifiStatus', 'G90HostInfoGsmStatus',
    'G90HostStatus',
    # Types for alerts and notifications
    'G90MessageTypes', 'G90NotificationTypes', 'G90ArmDisarmTypes',
    'G90AlertTypes', 'G90AlertSources', 'G90AlertStates',
    'G90AlertStateChangeTypes', 'G90HistoryStates',
    # Exceptions
    'G90Error',
    'G90TimeoutError', 'G90CommandError', 'G90CommandFailure',
    'G90EntityRegistrationError', 'G90PeripheralDefinitionNotFound',
    # Definitions
    'G90SensorDefinitions', 'G90DeviceDefinitions',
    # Host Configuration
    'G90HostConfig', 'G90VolumeLevel', 'G90SpeechLanguage',
    # Network Configuration
    'G90NetConfig', 'G90APNAuth',
    # Alarm Phones
    'G90AlarmPhones',
    # History
    'G90History',
]

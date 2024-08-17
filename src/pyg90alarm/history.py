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

from datetime import datetime, timezone
from collections import namedtuple
from .const import (
    G90AlertTypes,
    G90AlertSources,
    G90AlertStates,
    G90AlertStateChangeTypes,
    G90HistoryStates,
)
from .device_notifications import G90DeviceAlert


# The state of the incoming history entries are mixed of `G90AlertStates` and
# `G90AlertStateChangeTypes`, depending on entry type - the mapping
# consilidates them into unified `G90HistoryStates`. The latter enum can't be
# just an union of former two, since those have conflicting values
states_mapping = {
    G90AlertStates.DOOR_CLOSE:
        G90HistoryStates.DOOR_CLOSE,
    G90AlertStates.DOOR_OPEN:
        G90HistoryStates.DOOR_OPEN,
    G90AlertStates.TAMPER:
        G90HistoryStates.TAMPER,
    G90AlertStates.LOW_BATTERY:
        G90HistoryStates.LOW_BATTERY,
    G90AlertStateChangeTypes.AC_POWER_FAILURE:
        G90HistoryStates.AC_POWER_FAILURE,
    G90AlertStateChangeTypes.AC_POWER_RECOVER:
        G90HistoryStates.AC_POWER_RECOVER,
    G90AlertStateChangeTypes.DISARM:
        G90HistoryStates.DISARM,
    G90AlertStateChangeTypes.ARM_AWAY:
        G90HistoryStates.ARM_AWAY,
    G90AlertStateChangeTypes.ARM_HOME:
        G90HistoryStates.ARM_HOME,
    G90AlertStateChangeTypes.LOW_BATTERY:
        G90HistoryStates.LOW_BATTERY,
    G90AlertStateChangeTypes.WIFI_CONNECTED:
        G90HistoryStates.WIFI_CONNECTED,
    G90AlertStateChangeTypes.WIFI_DISCONNECTED:
        G90HistoryStates.WIFI_DISCONNECTED,
}

INCOMING_FIELDS = [
    'type',
    'event_id',
    'source',
    'state',
    'sensor_name',
    'unix_time',
    'other',
]
# Class representing the data incoming from the device
ProtocolData = namedtuple('ProtocolData', INCOMING_FIELDS)


class G90History:
    """
    tbd
    """
    def __init__(self, *args, **kwargs):
        self._protocol_data = ProtocolData(*args, **kwargs)

    @property
    def datetime(self):
        """
        Date/time of the history entry.

        :rtype: :class:`datetime.datetime`
        """
        return datetime.fromtimestamp(
            self._protocol_data.unix_time, tz=timezone.utc
        )

    @property
    def type(self):
        """
        Type of the history entry.

        :rtype: :class:`.G90AlertTypes`
        """
        return G90AlertTypes(self._protocol_data.type)

    @property
    def state(self):
        """
        State for the history entry.

        :rtype: :class:`.G90HistoryStates`
        """
        # Door open/close type, mapped against `G90AlertStates` using `state`
        # incoming field
        if self.type == G90AlertTypes.DOOR_OPEN_CLOSE:
            return G90HistoryStates(
                states_mapping[G90AlertStates(self._protocol_data.state)]
            )

        # Device state change, mapped against `G90AlertStateChangeTypes` using
        # `event_id` incoming field
        if self.type == G90AlertTypes.STATE_CHANGE:
            return G90HistoryStates(
                states_mapping[
                    G90AlertStateChangeTypes(self._protocol_data.event_id)
                ]
            )

        # Alarm gets mapped to its counterpart in `G90HistoryStates`
        if self.type == G90AlertTypes.ALARM:
            return G90HistoryStates.ALARM

        # Other types are mapped against `G90AlertStateChangeTypes`
        return G90HistoryStates(
            states_mapping[
                G90AlertStateChangeTypes(self._protocol_data.event_id)
            ]
        )

    @property
    def source(self):
        """
        Source of the history entry.

        :rtype: :class:`.G90AlertSources`
        """
        # Device state changes or open/close events are mapped against
        # `G90AlertSources` using `source` incoming field
        if self.type in [
            G90AlertTypes.STATE_CHANGE, G90AlertTypes.DOOR_OPEN_CLOSE
        ]:
            return G90AlertSources(self._protocol_data.source)

        # Alarm will have `SENSOR` as the source, since that is likely what
        # triggered it
        if self.type == G90AlertTypes.ALARM:
            return G90AlertSources.SENSOR

        # Other sources are assumed to be initiated by device itself
        return G90AlertSources.DEVICE

    @property
    def sensor_name(self):
        """
        Name of the sensor related to the history entry, might be empty if none
        associated.

        :rtype: str|None
        """
        return self._protocol_data.sensor_name or None

    @property
    def sensor_idx(self):
        """
        ID of the sensor related to the history entry, might be empty if none
        associated.

        :rtype: str|None
        """
        # Sensor ID will only be available if entry source is a sensor
        if self.source == G90AlertSources.SENSOR:
            return self._protocol_data.event_id

        return None

    def as_device_alert(self):
        """
        Returns the history entry represented as device alert structure,
        suitable for :meth:`G90DeviceNotifications._handle_alert`.

        :rtype: :class:`.G90DeviceAlert`
        """
        return G90DeviceAlert(
            type=self._protocol_data.type,
            event_id=self._protocol_data.event_id,
            source=self._protocol_data.source,
            state=self._protocol_data.state,
            zone_name=self._protocol_data.sensor_name,
            device_id=None,
            unix_time=self._protocol_data.unix_time,
            resv4=None,
            other=self._protocol_data.other
        )

    def __repr__(self):
        """
        Textural representation of the history entry.

        :rtype: str
        """
        return f'type={repr(self.type)}' \
            + f' source={repr(self.source)}' \
            + f' state={repr(self.state)}' \
            + f' sensor_name={self.sensor_name}' \
            + f' sensor_idx={self.sensor_idx}' \
            + f' datetime={repr(self.datetime)}'

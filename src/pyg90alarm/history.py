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
from typing import Any, Optional, Dict
from dataclasses import dataclass
from datetime import datetime, timezone
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


@dataclass
class ProtocolData:
    """
    Class representing the data incoming from the device

    :meta private:
    """
    type: G90AlertTypes
    event_id: G90AlertStateChangeTypes
    source: G90AlertSources
    state: int
    sensor_name: str
    unix_time: int
    other: str


class G90History:
    """
    Represents a history entry from the alarm panel.
    """
    def __init__(self, *args: Any, **kwargs: Any):
        self._protocol_data = ProtocolData(*args, **kwargs)

    @property
    def datetime(self) -> datetime:
        """
        Date/time of the history entry.
        """
        return datetime.fromtimestamp(
            self._protocol_data.unix_time, tz=timezone.utc
        )

    @property
    def type(self) -> G90AlertTypes:
        """
        Type of the history entry.
        """
        return G90AlertTypes(self._protocol_data.type)

    @property
    def state(self) -> G90HistoryStates:
        """
        State for the history entry.
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
    def source(self) -> G90AlertSources:
        """
        Source of the history entry.
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
    def sensor_name(self) -> Optional[str]:
        """
        Name of the sensor related to the history entry, might be empty if none
        associated.
        """
        return self._protocol_data.sensor_name or None

    @property
    def sensor_idx(self) -> Optional[int]:
        """
        ID of the sensor related to the history entry, might be empty if none
        associated.
        """
        # Sensor ID will only be available if entry source is a sensor
        if self.source == G90AlertSources.SENSOR:
            return self._protocol_data.event_id

        return None

    def as_device_alert(self) -> G90DeviceAlert:
        """
        Returns the history entry represented as device alert structure,
        suitable for :meth:`G90DeviceNotifications._handle_alert`.
        """
        return G90DeviceAlert(
            type=self._protocol_data.type,
            event_id=self._protocol_data.event_id,
            source=self._protocol_data.source,
            state=self._protocol_data.state,
            zone_name=self._protocol_data.sensor_name,
            device_id='',
            unix_time=self._protocol_data.unix_time,
            resv4=0,
            other=self._protocol_data.other
        )

    def _asdict(self) -> Dict[str, Any]:
        """
        Returns the history entry as dictionary.
        """
        return {
            'type': self.type,
            'source': self.source,
            'state': self.state,
            'sensor_name': self.sensor_name,
            'sensor_idx': self.sensor_idx,
            'datetime': self.datetime,
        }

    def __repr__(self) -> str:
        """
        Textural representation of the history entry.
        """
        return f'type={repr(self.type)}' \
            + f' source={repr(self.source)}' \
            + f' state={repr(self.state)}' \
            + f' sensor_name={self.sensor_name}' \
            + f' sensor_idx={self.sensor_idx}' \
            + f' datetime={repr(self.datetime)}'

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
import logging

from typing import Any, Optional, Dict
from dataclasses import dataclass
from datetime import datetime, timezone
from .const import (
    G90AlertTypes,
    G90AlertSources,
    G90AlertStates,
    G90AlertStateChangeTypes,
    G90HistoryStates,
    G90RemoteButtonStates,
)
from .device_notifications import G90DeviceAlert

_LOGGER = logging.getLogger(__name__)


# The state of the incoming history entries are mixed of `G90AlertStates`,
# `G90AlertStateChangeTypes` and `G90RemoteButtonStates`, depending on entry
# type - hence separate dictionaries, since enums used for keys have
# conflicting values
states_mapping_alerts = {
    G90AlertStates.DOOR_CLOSE:
        G90HistoryStates.DOOR_CLOSE,
    G90AlertStates.DOOR_OPEN:
        G90HistoryStates.DOOR_OPEN,
    G90AlertStates.TAMPER:
        G90HistoryStates.TAMPER,
    G90AlertStates.LOW_BATTERY:
        G90HistoryStates.LOW_BATTERY,
}

states_mapping_state_changes = {
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

states_mapping_remote_buttons = {
    G90RemoteButtonStates.ARM_AWAY:
        G90HistoryStates.REMOTE_BUTTON_ARM_AWAY,
    G90RemoteButtonStates.ARM_HOME:
        G90HistoryStates.REMOTE_BUTTON_ARM_HOME,
    G90RemoteButtonStates.DISARM:
        G90HistoryStates.REMOTE_BUTTON_DISARM,
    G90RemoteButtonStates.SOS:
        G90HistoryStates.REMOTE_BUTTON_SOS,
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
        self._raw_data = args
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
    def type(self) -> Optional[G90AlertTypes]:
        """
        Type of the history entry.
        """
        try:
            return G90AlertTypes(self._protocol_data.type)
        except (ValueError, KeyError):
            _LOGGER.warning(
                "Can't interpret '%s' as alert type (decoded protocol"
                " data '%s', raw data '%s')",
                self._protocol_data.type, self._protocol_data, self._raw_data
            )
            return None

    @property
    def state(self) -> Optional[G90HistoryStates]:
        """
        State for the history entry.
        """
        # No meaningful state for SOS alerts initiated by the panel itself
        # (host)
        if self.type == G90AlertTypes.HOST_SOS:
            return None

        try:
            # State of the remote indicate which button has been pressed
            if (
                self.type in [
                    G90AlertTypes.SENSOR_ACTIVITY, G90AlertTypes.ALARM
                ] and self.source == G90AlertSources.REMOTE
            ):
                return states_mapping_remote_buttons[
                    G90RemoteButtonStates(self._protocol_data.state)
                ]

            # Door open/close or alert types, mapped against `G90AlertStates`
            # using `state` incoming field
            if self.type in [
                G90AlertTypes.SENSOR_ACTIVITY, G90AlertTypes.ALARM
            ]:
                return G90HistoryStates(
                    states_mapping_alerts[
                        G90AlertStates(self._protocol_data.state)
                    ]
                )
        except (ValueError, KeyError):
            _LOGGER.warning(
                "Can't interpret '%s' as alert state (decoded protocol"
                " data '%s', raw data '%s')",
                self._protocol_data.state, self._protocol_data, self._raw_data
            )
            return None

        try:
            # Other types are mapped against `G90AlertStateChangeTypes`
            return G90HistoryStates(
                states_mapping_state_changes[
                    G90AlertStateChangeTypes(self._protocol_data.event_id)
                ]
            )
        except (ValueError, KeyError):
            _LOGGER.warning(
                "Can't interpret '%s' as state change (decoded protocol"
                " data '%s', raw data '%s')",
                self._protocol_data.event_id, self._protocol_data,
                self._raw_data
            )
            return None

    @property
    def source(self) -> Optional[G90AlertSources]:
        """
        Source of the history entry.
        """
        try:
            # Device state changes, open/close or alarm events are mapped
            # against `G90AlertSources` using `source` incoming field
            if self.type in [
                G90AlertTypes.STATE_CHANGE, G90AlertTypes.SENSOR_ACTIVITY,
                G90AlertTypes.ALARM
            ]:
                return G90AlertSources(self._protocol_data.source)
        except (ValueError, KeyError):
            _LOGGER.warning(
                "Can't interpret '%s' as alert source (decoded protocol"
                " data '%s', raw data '%s')",
                self._protocol_data.source, self._protocol_data, self._raw_data
            )
            return None

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
        return super().__repr__() + f'({repr(self._asdict())})'

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
Implements support for notifications/alerts sent by G90 alarm panel.
"""
import json
import logging
from typing import (
    Optional, Tuple, List, Any
)
from dataclasses import dataclass
import asyncio
from asyncio.transports import BaseTransport
from asyncio.protocols import DatagramProtocol
from .callback import G90Callback
from .const import (
    G90MessageTypes,
    G90NotificationTypes,
    G90AlertTypes,
    G90AlertStateChangeTypes,
    G90ArmDisarmTypes,
    G90AlertSources,
    G90AlertStates,
)


_LOGGER = logging.getLogger(__name__)


@dataclass
class G90Message:
    """
    Represents the message received from the device.

    :meta private:
    """
    code: G90MessageTypes
    data: List[Any]


@dataclass
class G90Notification:
    """
    Represents the notification received from the device.

    :meta private:
    """
    kind: G90NotificationTypes
    data: List[Any]


@dataclass
class G90ZoneInfo:
    """
    Represents zone details received from the device.

    :meta private:
    """
    idx: int
    name: str


@dataclass
class G90ArmDisarmInfo:
    """
    Represents the arm/disarm state received from the device.

    :meta private:
    """
    state: int


@dataclass
class G90DeviceAlert:  # pylint: disable=too-many-instance-attributes
    """
    Represents alert received from the device.
    """
    type: G90AlertTypes
    event_id: G90AlertStateChangeTypes
    source: G90AlertSources
    state: int
    zone_name: str
    device_id: str
    unix_time: int
    resv4: int
    other: str


class G90DeviceNotifications(DatagramProtocol):
    """
    Implements support for notifications/alerts sent by alarm panel.
    """
    def __init__(self, port: int, host: str):
        # pylint: disable=too-many-arguments
        self._notification_transport: Optional[BaseTransport] = None
        self._notifications_host = host
        self._notifications_port = port

    def _handle_notification(
        self, addr: Tuple[str, int], notification: G90Notification
    ) -> None:
        # Sensor activity notification
        if notification.kind == G90NotificationTypes.SENSOR_ACTIVITY:
            g90_zone_info = G90ZoneInfo(*notification.data)
            _LOGGER.debug('Sensor notification: %s', g90_zone_info)
            G90Callback.invoke(
                self.on_sensor_activity,
                g90_zone_info.idx, g90_zone_info.name
            )
            return

        # Arm/disarm notification
        if notification.kind == G90NotificationTypes.ARM_DISARM:
            g90_armdisarm_info = G90ArmDisarmInfo(
                *notification.data)
            # Map the state received from the device to corresponding enum
            state = G90ArmDisarmTypes(g90_armdisarm_info.state)
            _LOGGER.debug('Arm/disarm notification: %s',
                          state)
            G90Callback.invoke(self.on_armdisarm, state)
            return

        _LOGGER.warning('Unknown notification received from %s:%s:'
                        ' kind %s, data %s',
                        addr[0], addr[1], notification.kind, notification.data)

    def _handle_alert(
        self, addr: Tuple[str, int], alert: G90DeviceAlert
    ) -> None:
        if alert.type == G90AlertTypes.DOOR_OPEN_CLOSE:
            if alert.state in (
                G90AlertStates.DOOR_OPEN, G90AlertStates.DOOR_CLOSE
            ):
                is_open = (
                    alert.source == G90AlertSources.SENSOR
                    and alert.state == G90AlertStates.DOOR_OPEN  # noqa: W503
                ) or alert.source == G90AlertSources.DOORBELL
                _LOGGER.debug('Door open_close alert: %s', alert)
                G90Callback.invoke(
                    self.on_door_open_close,
                    alert.event_id, alert.zone_name, is_open
                )
                return

            if (
                alert.source == G90AlertSources.SENSOR
                and alert.state == G90AlertStates.LOW_BATTERY  # noqa: W503
            ):
                _LOGGER.debug('Low battery alert: %s', alert)
                G90Callback.invoke(
                    self.on_low_battery,
                    alert.event_id, alert.zone_name
                )
                return

        if alert.type == G90AlertTypes.STATE_CHANGE:
            # Define the mapping between device state received in the alert, to
            # common `G90ArmDisarmTypes` enum that is used when setting device
            # arm state and received in the corresponding notifications. The
            # primary reason is to unify state as passed down to the callbacks.
            # The map covers only subset of state changes pertinent to
            # arm/disarm state changes
            alarm_arm_disarm_state_map = {
                G90AlertStateChangeTypes.ARM_HOME: G90ArmDisarmTypes.ARM_HOME,
                G90AlertStateChangeTypes.ARM_AWAY: G90ArmDisarmTypes.ARM_AWAY,
                G90AlertStateChangeTypes.DISARM: G90ArmDisarmTypes.DISARM
            }

            state = alarm_arm_disarm_state_map.get(alert.event_id)
            if state:
                # We received the device state change related to arm/disarm,
                # invoke the corresponding callback
                _LOGGER.debug('Arm/disarm state change: %s', state)
                G90Callback.invoke(self.on_armdisarm, state)
                return

        if alert.type == G90AlertTypes.ALARM:
            _LOGGER.debug('Alarm: %s', alert.zone_name)
            G90Callback.invoke(
                self.on_alarm,
                alert.event_id, alert.zone_name
            )
            return

        _LOGGER.warning('Unknown alert received from %s:%s:'
                        ' type %s, data %s',
                        addr[0], addr[1], alert.type, alert)

    # Implementation of datagram protocol,
    # https://docs.python.org/3/library/asyncio-protocol.html#datagram-protocols
    def connection_made(self, transport: BaseTransport) -> None:
        """
        Invoked when connection from the device is made.
        """

    def connection_lost(self, exc: Optional[Exception]) -> None:
        """
        Same but when the connection is lost.
        """

    def datagram_received(  # pylint:disable=R0911
        self, data: bytes, addr: Tuple[str, int]
    ) -> None:

        """
        Invoked from datagram is received from the device.
        """
        s_data = data.decode('utf-8')
        if not s_data.endswith('\0'):
            _LOGGER.error('Missing end marker in data')
            return
        payload = s_data[:-1]
        _LOGGER.debug('Received device message from %s:%s: %s',
                      addr[0], addr[1], payload)
        try:
            message = json.loads(payload)
            g90_message = G90Message(*message)
        except json.JSONDecodeError as exc:
            _LOGGER.error("Unable to parse device message '%s' as JSON: %s",
                          payload, exc)
            return
        except TypeError as exc:
            _LOGGER.error("Device message '%s' is malformed: %s",
                          payload, exc)
            return

        # Device notifications
        if g90_message.code == G90MessageTypes.NOTIFICATION:
            try:
                notification_data = G90Notification(*g90_message.data)
            except TypeError as exc:
                _LOGGER.error('Bad notification received from %s:%s: %s',
                              addr[0], addr[1], exc)
                return
            self._handle_notification(addr, notification_data)
            return

        # Device alerts
        if g90_message.code == G90MessageTypes.ALERT:
            try:
                alert_data = G90DeviceAlert(*g90_message.data)
            except TypeError as exc:
                _LOGGER.error('Bad alert received from %s:%s: %s',
                              addr[0], addr[1], exc)
                return
            self._handle_alert(addr, alert_data)
            return

        _LOGGER.warning('Unknown message received from %s:%s: %s',
                        addr[0], addr[1], message)

    async def on_armdisarm(self, state: G90ArmDisarmTypes) -> None:
        """
        Invoked when device is armed or disarmed.
        """

    async def on_sensor_activity(self, idx: int, name: str) -> None:
        """
        Invoked on sensor activity.
        """

    async def on_door_open_close(
        self, event_id: int, zone_name: str, is_open: bool
    ) -> None:
        """
        Invoked when door sensor reports it opened or closed.
        """

    async def on_low_battery(self, event_id: int, zone_name: str) -> None:
        """
        Invoked when a sensor reports it is low on battery.
        """

    async def on_alarm(self, event_id: int, zone_name: str) -> None:
        """
        Invoked when device triggers the alarm.
        """

    async def listen(self) -> None:
        """
        Listens for notifications/alers from the device.
        """
        try:
            loop = asyncio.get_running_loop()
        except AttributeError:
            loop = asyncio.get_event_loop()

        _LOGGER.debug('Creating UDP endpoint for %s:%s',
                      self._notifications_host,
                      self._notifications_port)
        (self._notification_transport,
         _protocol) = await loop.create_datagram_endpoint(
            lambda: self,
            local_addr=(
                self._notifications_host, self._notifications_port
            ))

    @property
    def listener_started(self) -> bool:
        """
        Indicates if the listener of the device notifications has been started.
        """
        return self._notification_transport is not None

    def close(self) -> None:
        """
        Closes the listener.
        """
        if self._notification_transport:
            _LOGGER.debug('No longer listening for device notifications')
            self._notification_transport.close()
            self._notification_transport = None

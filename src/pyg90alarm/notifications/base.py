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
Implements support for notifications/alerts sent by G90 alarm panel.
"""
import json
import logging
from typing import (
    Optional, List, Any, Callable
)
from dataclasses import dataclass
from asyncio.transports import BaseTransport
from datetime import datetime, timezone

from ..callback import G90Callback
from ..const import (
    G90MessageTypes,
    G90NotificationTypes,
    G90AlertTypes,
    G90AlertStateChangeTypes,
    G90ArmDisarmTypes,
    G90AlertSources,
    G90AlertStates,
    G90RemoteButtonStates,
)
from .protocol import G90NotificationProtocol

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


class G90NotificationsBase:
    """
    Implements support for notifications/alerts sent by alarm panel.

    There is a basic check to ensure only notifications/alerts from the correct
    device are processed - the check uses the host and port of the device, and
    the device ID (GUID) that is set by the ancestor class that implements the
    commands (e.g. :class:`G90Alarm`). The latter to work correctly needs a
    command to be performed first, one that fetches device GUID and then stores
    it using :attr:`.device_id` (e.g. :meth:`G90Alarm.get_host_info`).
    """
    def __init__(
        self, protocol_factory: Callable[[], G90NotificationProtocol],
    ):
        # pylint: disable=too-many-arguments
        self._transport: Optional[BaseTransport] = None
        # Same but for device ID (GUID) - the notifications logic uses it to
        # perform validation, but doesn't set it from messages received (it
        # will diminish the purpose of the validation, should be done by an
        # ancestor class).
        self._device_id: Optional[str] = None
        self._protocol = protocol_factory()
        self._last_device_packet_time: Optional[datetime] = None
        self._last_upstream_packet_time: Optional[datetime] = None

    def handle_notification(
        self, notification: G90Notification
    ) -> None:
        """
        Handles notification received from the device.

        :param notification: The notification to handle.
        """
        # Sensor activity notification
        if notification.kind == G90NotificationTypes.SENSOR_ACTIVITY:
            g90_zone_info = G90ZoneInfo(*notification.data)

            _LOGGER.debug('Sensor notification: %s', g90_zone_info)
            G90Callback.invoke(
                self._protocol.on_sensor_activity,
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
            G90Callback.invoke(self._protocol.on_armdisarm, state)

            return

        # An open door is detected when arming
        if notification.kind == G90NotificationTypes.DOOR_OPEN_WHEN_ARMING:
            g90_zone_info = G90ZoneInfo(*notification.data)
            _LOGGER.debug('Door open detected when arming: %s', g90_zone_info)
            G90Callback.invoke(
                self._protocol.on_door_open_when_arming,
                g90_zone_info.idx, g90_zone_info.name
            )
            return

        _LOGGER.warning('Unknown notification received:'
                        ' kind %s, data %s',
                        notification.kind, notification.data)

    def _handle_alert_sensor_activity(self, alert: G90DeviceAlert) -> bool:
        """
        Handles sensor activity alert.
        """
        if alert.source == G90AlertSources.REMOTE:
            _LOGGER.debug('Remote button press alert: %s', alert)
            G90Callback.invoke(
                self._protocol.on_remote_button_press,
                alert.event_id, alert.zone_name,
                G90RemoteButtonStates(alert.state)
            )

            return True

        if alert.state in (
            G90AlertStates.DOOR_OPEN, G90AlertStates.DOOR_CLOSE
        ):
            is_open = (
                alert.source == G90AlertSources.SENSOR
                and alert.state == G90AlertStates.DOOR_OPEN  # noqa: W503
            ) or alert.source == G90AlertSources.DOORBELL

            _LOGGER.debug('Door open_close alert: %s', alert)
            G90Callback.invoke(
                self._protocol.on_door_open_close,
                alert.event_id, alert.zone_name, is_open
            )

            return True

        if (
            alert.source == G90AlertSources.SENSOR
            and alert.state == G90AlertStates.LOW_BATTERY  # noqa: W503
        ):
            _LOGGER.debug('Low battery alert: %s', alert)
            G90Callback.invoke(
                self._protocol.on_low_battery,
                alert.event_id, alert.zone_name
            )

            return True

        return False

    def handle_alert(
        self, alert: G90DeviceAlert,
        verify_device_id: bool = True
    ) -> None:
        """
        Handles alert received from the device.

        :param alert: The alert to handle.
        :param verify_device_id: Whether to verify the device ID (GUID) in the
         alert. If set to False, the device ID will not be verified.
        """
        handled = False

        # Stop processing when alert is received from the device with different
        # GUID (if enabled)
        if (
            verify_device_id and self.device_id
            and alert.device_id != self.device_id
        ):
            _LOGGER.error(
                "Received alert from wrong device: expected '%s', got '%s'",
                self.device_id, alert.device_id
            )
            return

        if alert.type == G90AlertTypes.SENSOR_ACTIVITY:
            handled = self._handle_alert_sensor_activity(alert)

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

            state = alarm_arm_disarm_state_map.get(alert.event_id, None)
            if state:
                # We received the device state change related to arm/disarm,
                # invoke the corresponding callback
                _LOGGER.debug('Arm/disarm state change: %s', state)
                G90Callback.invoke(self._protocol.on_armdisarm, state)

            handled = True

        if alert.type == G90AlertTypes.ALARM:
            # Remote SOS
            if alert.source == G90AlertSources.REMOTE:
                _LOGGER.debug('SOS: %s', alert.zone_name)
                G90Callback.invoke(
                    self._protocol.on_sos,
                    alert.event_id, alert.zone_name, False
                )
            # Regular alarm
            else:
                is_tampered = alert.state == G90AlertStates.TAMPER
                _LOGGER.debug(
                    'Alarm: %s, is tampered: %s', alert.zone_name, is_tampered
                )
                G90Callback.invoke(
                    self._protocol.on_alarm,
                    alert.event_id, alert.zone_name, is_tampered
                )

            handled = True

        # Host SOS
        if alert.type == G90AlertTypes.HOST_SOS:
            zone_name = 'Host SOS'

            _LOGGER.debug('SOS: Host')
            G90Callback.invoke(
                self._protocol.on_sos, alert.event_id, zone_name, True
            )

            handled = True

        if not handled:
            _LOGGER.warning(
                'Unknown alert received: type %s, data %s',
                alert.type, alert
            )

    # pylint:disable=too-many-return-statements
    def handle(self, data: bytes) -> None:
        """
        Invoked when message is received from the device.
        """
        try:
            s_data = data.decode('utf-8')
        except UnicodeDecodeError:
            _LOGGER.error('Unable to decode device message from UTF-8')
            return

        if not s_data.endswith('\0'):
            _LOGGER.error('Missing end marker in data')
            return
        payload = s_data[:-1]

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
                _LOGGER.error('Bad notification received: %s', exc)
                return
            self.handle_notification(notification_data)
            return

        # Device alerts
        if g90_message.code == G90MessageTypes.ALERT:
            try:
                alert_data = G90DeviceAlert(*g90_message.data)
            except TypeError as exc:
                _LOGGER.error('Bad alert received: %s', exc)
                return
            self.handle_alert(alert_data)
            return

        _LOGGER.warning('Unknown message received: %s', message)

    async def listen(self) -> None:
        """
        Listens for notifications/alerts from the device.
        """
        raise NotImplementedError

    @property
    def listener_started(self) -> bool:
        """
        Indicates if the listener of the device notifications has been started.
        """
        return self._transport is not None

    async def close(self) -> None:
        """
        Closes the listener.
        """
        if self._transport:
            _LOGGER.debug('No longer listening for device notifications')
            self._transport.close()
            self._transport = None

    @property
    def device_id(self) -> Optional[str]:
        """
        The ID (GUID) of the panel being communicated with thru commands.

        Available when any panel command receives it from the device
        (`GETHOSTINFO` local command or Hello / HelloDiscovery cloud ones).
        """
        return self._device_id

    @device_id.setter
    def device_id(self, device_id: str) -> None:
        # Under not yet identified circumstances the device ID might be empty
        # string provided by :meth:`G90Alarm.get_host_info` - disallow that
        if not device_id or len(device_id.strip()) == 0:
            _LOGGER.debug(
                'Device ID is empty or contains whitespace only, not setting'
            )
            return

        self._device_id = device_id

    def clear_device_id(self) -> None:
        """
        Clears the device ID.
        """
        self._device_id = None

    @property
    def last_device_packet_time(self) -> Optional[datetime]:
        """
        Returns the timestamp of the last packet received from the device.

        This property can be used to monitor the communication health with the
        device.
        """
        return self._last_device_packet_time

    def set_last_device_packet_time(self) -> None:
        """
        Updates the timestamp of the last packet received from the device.

        This method is called internally when a packet is received from the
        device.
        """
        self._last_device_packet_time = datetime.now(tz=timezone.utc)
        _LOGGER.debug(
            'Last device packet time: %s', self._last_device_packet_time
        )

    @property
    def last_upstream_packet_time(self) -> Optional[datetime]:
        """
        Returns the timestamp of the last packet sent to the upstream server.

        This property can be used to monitor the communication health with the
        cloud/upstream server.
        """
        return self._last_upstream_packet_time

    def set_last_upstream_packet_time(self) -> None:
        """
        Updates the timestamp of the last packet sent to the upstream server.

        This method is called internally when a packet is sent to the upstream
        server.
        """
        self._last_upstream_packet_time = datetime.now(tz=timezone.utc)
        _LOGGER.debug(
            'Last upstream packet time: %s', self._last_upstream_packet_time
        )

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
# pylint: disable=too-many-lines

"""
Provides interface to G90 alarm panel.

.. note:: Both local protocol (referred to as 1.2) and cloud one
(mentioned as 1.1) are supported.

The next example queries the device with IP address `10.10.10.250` for the
information - the product name, protocol version, HW versions and such.

>>> import asyncio
>>> from pyg90alarm import G90Alarm
>>> async def main():
       g90 = G90Alarm(host='10.10.10.250')
       s = await g90.host_info
       print(s)
>>> asyncio.run(main())
G90HostInfo(host_guid='<...>',
            product_name='TSV018-C3SIA',
            wifi_protocol_version='1.2',
            cloud_protocol_version='1.1',
            mcu_hw_version='206',
            wifi_hw_version='206',
            gsm_status=3,
            wifi_status=3,
            reserved1=0,
            reserved2=0,
            band_frequency='4264',
            gsm_signal_level=50,
            wifi_signal_level=100)

"""
from __future__ import annotations
import asyncio
from asyncio import Task
from datetime import datetime
import logging
from typing import (
    TYPE_CHECKING, Any, List, Optional, AsyncGenerator,
    Callable, Coroutine, Union
)
from .const import (
    G90Commands, REMOTE_PORT,
    REMOTE_TARGETED_DISCOVERY_PORT,
    LOCAL_TARGETED_DISCOVERY_PORT,
    LOCAL_NOTIFICATIONS_HOST,
    LOCAL_NOTIFICATIONS_PORT,
    CLOUD_NOTIFICATIONS_HOST,
    CLOUD_NOTIFICATIONS_PORT,
    REMOTE_CLOUD_HOST,
    REMOTE_CLOUD_PORT,
    G90ArmDisarmTypes,
    G90RemoteButtonStates,
)
from .local.base_cmd import (G90BaseCommand, G90BaseCommandData)
from .local.paginated_result import G90PaginatedResult, G90PaginatedResponse
from .entities.sensor import (G90Sensor, G90SensorTypes)
from .entities.sensor_list import G90SensorList
from .entities.device import G90Device
from .entities.device_list import G90DeviceList
from .notifications.protocol import (
    G90NotificationProtocol
)
from .notifications.base import G90NotificationsBase
from .local.notifications import G90LocalNotifications
from .local.discovery import G90Discovery, G90DiscoveredDevice
from .local.targeted_discovery import (
    G90TargetedDiscovery, G90DiscoveredDeviceTargeted,
)
from .local.host_info import G90HostInfo
from .local.host_status import G90HostStatus
from .local.config import (G90AlertConfig, G90AlertConfigFlags)
from .local.history import G90History
from .local.user_data_crc import G90UserDataCRC
from .callback import G90Callback
from .exceptions import G90Error, G90TimeoutError
from .cloud.notifications import G90CloudNotifications

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    # Type alias for the callback functions available to the user, should be
    # compatible with `G90Callback.Callback` type, since `G90Callback.invoke`
    # is used to invoke them
    AlarmCallback = Union[
        Callable[[int, str, Any], None],
        Callable[[int, str, Any], Coroutine[None, None, None]]
    ]
    DoorOpenCloseCallback = Union[
        Callable[[int, str, bool], None],
        Callable[[int, str, bool], Coroutine[None, None, None]]
    ]
    SensorCallback = Union[
        Callable[[int, str, bool], None],
        Callable[[int, str, bool], Coroutine[None, None, None]]
    ]
    LowBatteryCallback = Union[
        Callable[[int, str], None],
        Callable[[int, str], Coroutine[None, None, None]]
    ]
    ArmDisarmCallback = Union[
        Callable[[G90ArmDisarmTypes], None],
        Callable[[G90ArmDisarmTypes], Coroutine[None, None, None]]
    ]
    SosCallback = Union[
        Callable[[int, str, bool], None],
        Callable[[int, str, bool], Coroutine[None, None, None]]
    ]
    RemoteButtonPressCallback = Union[
        Callable[[int, str, G90RemoteButtonStates], None],
        Callable[
            [int, str, G90RemoteButtonStates], Coroutine[None, None, None]
        ]
    ]
    DoorOpenWhenArmingCallback = Union[
        Callable[[int, str], None],
        Callable[[int, str], Coroutine[None, None, None]]
    ]
    TamperCallback = Union[
        Callable[[int, str], None],
        Callable[[int, str], Coroutine[None, None, None]]
    ]
    # Sensor-related callbacks for `G90Sensor` class - despite that class
    # stores them, the invocation is done by the `G90Alarm` class hence these
    # are defined here
    SensorStateCallback = Union[
        Callable[[bool], None],
        Callable[[bool], Coroutine[None, None, None]]
    ]
    SensorLowBatteryCallback = Union[
        Callable[[], None],
        Callable[[], Coroutine[None, None, None]]
    ]
    SensorDoorOpenWhenArmingCallback = Union[
        Callable[[], None],
        Callable[[], Coroutine[None, None, None]]
    ]
    SensorTamperCallback = Union[
        Callable[[], None],
        Callable[[], Coroutine[None, None, None]]
    ]


# pylint: disable=too-many-public-methods
class G90Alarm(G90NotificationProtocol):

    """
    Allows to interact with G90 alarm panel.

    :param host: Hostname or IP address of the alarm panel. Since the
     protocol is UDP-based it is ok to use broadcast or directed broadcast
     addresses, such as `255.255.255.255` or `10.10.10.255` (the latter assumes
     the device is on `10.10.10.0/24` network)
    :param port: The UDP port of the device where it listens for the
     protocol commands on WiFi interface, currently the devices don't allow it
     to be customized
    :param reset_occupancy_interval: The interval upon that the sensors are
     simulated to go into inactive state.
    """
    # pylint: disable=too-many-instance-attributes,too-many-arguments
    def __init__(
        self, host: str, port: int = REMOTE_PORT,
        reset_occupancy_interval: float = 3.0
    ) -> None:
        self._host: str = host
        self._port: int = port
        self._notifications: Optional[G90NotificationsBase] = None
        self._sensors = G90SensorList(self)
        self._devices = G90DeviceList(self)
        self._sensor_cb: Optional[SensorCallback] = None
        self._armdisarm_cb: Optional[ArmDisarmCallback] = None
        self._door_open_close_cb: Optional[DoorOpenCloseCallback] = None
        self._alarm_cb: Optional[AlarmCallback] = None
        self._low_battery_cb: Optional[LowBatteryCallback] = None
        self._sos_cb: Optional[SosCallback] = None
        self._remote_button_press_cb: Optional[
            RemoteButtonPressCallback
        ] = None
        self._door_open_when_arming_cb: Optional[
            DoorOpenWhenArmingCallback
        ] = None
        self._tamper_cb: Optional[TamperCallback] = None
        self._reset_occupancy_interval = reset_occupancy_interval
        self._alert_config = G90AlertConfig(self)
        self._sms_alert_when_armed = False
        self._alert_simulation_task: Optional[Task[Any]] = None
        self._alert_simulation_start_listener_back = False

    @property
    def host(self) -> str:
        """
        Returns the hostname or IP address of the alarm panel.

        This is the address used for communication with the device.
        """
        return self._host

    @property
    def port(self) -> int:
        """
        Returns the UDP port number used to communicate with the alarm panel.

        By default, this is set to the standard G90 protocol port.
        """
        return self._port

    async def command(
        self, code: G90Commands, data: Optional[G90BaseCommandData] = None
    ) -> G90BaseCommandData:
        """
        Invokes a command against the alarm panel.

        :param code: Command code
        :param data: Command data
        :return: The result of command invocation
        """
        cmd: G90BaseCommand = await G90BaseCommand(
            self._host, self._port, code, data).process()
        return cmd.result

    def paginated_result(
        self, code: G90Commands, start: int = 1, end: Optional[int] = None
    ) -> AsyncGenerator[G90PaginatedResponse, None]:
        """
        Returns asynchronous generator for a paginated command, that is -
        command operating on a range of records.

        :param code: Command code
        :param start: Starting record position (one-based)
        :param end: Ending record position (one-based)
        :return: Asynchronous generator over the result of command invocation.
        """
        return G90PaginatedResult(
            self._host, self._port, code, start, end
        ).process()

    @classmethod
    async def discover(cls) -> List[G90DiscoveredDevice]:
        """
        Initiates discovering devices available in the same network segment, by
        using global broadcast address as the destination.

        :return: List of discovered devices
        """
        cmd: G90Discovery = await G90Discovery(
            port=REMOTE_PORT,
            host='255.255.255.255'
        ).process()
        return cmd.devices

    @classmethod
    async def targeted_discover(
        cls, device_id: str
    ) -> List[G90DiscoveredDeviceTargeted]:
        """
        Initiates discovering devices available in the same network segment
        using targeted protocol, that is - specifying target device GUID in the
        request, so only the specific device should respond to the query.

        :param device_id: GUID of the target device to discover
        :return: List of discovered devices
        """
        cmd = await G90TargetedDiscovery(
            device_id=device_id,
            port=REMOTE_TARGETED_DISCOVERY_PORT,
            local_port=LOCAL_TARGETED_DISCOVERY_PORT,
            host='255.255.255.255'
        ).process()
        return cmd.devices

    @property
    async def sensors(self) -> List[G90Sensor]:
        """
        Returns the list of sensors configured in the device. Please note
        it doesn't update those from the panel except initially when the list
        if empty.

        :return: List of sensors
        """
        return await self._sensors.entities

    async def get_sensors(self) -> List[G90Sensor]:
        """
        Provides list of sensors configured in the device, updating them from
        panel on each call.

        :return: List of sensors
        """
        return await self._sensors.update()

    async def find_sensor(
        self, idx: int, name: str, exclude_unavailable: bool = True
    ) -> Optional[G90Sensor]:
        """
        Finds sensor by index and name.

        :param idx: Sensor index
        :param name: Sensor name
        :param exclude_unavailable: Flag indicating if unavailable sensors
         should be excluded from the search
        :return: Sensor instance
        """
        return await self._sensors.find(idx, name, exclude_unavailable)

    @property
    async def devices(self) -> List[G90Device]:
        """
        Returns the list of devices (switches) configured in the device. Please
        note it doesn't update those from the panel except initially when
        the list if empty.

        :return: List of devices
        """
        return await self._devices.entities

    async def get_devices(self) -> List[G90Device]:
        """
        Provides list of devices (switches) configured in the device, updating
        them from panel on each call. Multi-node devices, those
        having multiple ports, are expanded into corresponding number of
        resulting entries.

        :return: List of devices
        """
        return await self._devices.update()

    @property
    async def host_info(self) -> G90HostInfo:
        """
        Property over new :meth:`.get_host_info` method, retained for
        compatibility.
        """
        return await self.get_host_info()

    async def get_host_info(self) -> G90HostInfo:
        """
        Provides the device information (for example hardware versions, signal
        levels etc.).

        :return: Device information
        """
        res = await self.command(G90Commands.GETHOSTINFO)
        info = G90HostInfo(*res)
        if self._notifications:
            self._notifications.device_id = info.host_guid
        return info

    @property
    async def host_status(self) -> G90HostStatus:
        """
        Property over new :meth:`.get_host_status` method, retained for
        compatibility.
        """
        return await self.get_host_status()

    async def get_host_status(self) -> G90HostStatus:
        """
        Provides the device status (for example, armed or disarmed, configured
        phone number, product name etc.).

        :return: Device information

        """
        res = await self.command(G90Commands.GETHOSTSTATUS)
        return G90HostStatus(*res)

    @property
    def alert_config(self) -> G90AlertConfig:
        """
        Provides alert configuration object.

        :return: Alert configuration object
        """
        return self._alert_config

    async def get_alert_config(self) -> G90AlertConfigFlags:
        """
        Provides alert configuration flags, retained for compatibility - using
        `:attr:alert_config` and `:class:G90AlertConfig` is preferred.

        :return: The alerts configured
        """
        return await self.alert_config.flags

    async def set_alert_config(self, flags: G90AlertConfigFlags) -> None:
        """
        Sets the alert configuration flags, retained for compatibility - using
        `:attr:alert_config` and `:class:G90AlertConfig` is preferred.
        """
        await self.alert_config.set(flags)

    @property
    async def user_data_crc(self) -> G90UserDataCRC:
        """
        Property over new :meth:`.get_user_data_crc` method, retained for
        compatibility.
        """
        return await self.get_user_data_crc()

    async def get_user_data_crc(self) -> G90UserDataCRC:
        """
        Retieves checksums (CRC) for different on-device databases (history,
        sensors etc.). Might be used to detect if there is a change in a
        particular database.

        .. note:: Note that due to a bug in the firmware CRC for sensors and
          device databases change on each call even if there were no changes

        :return: Checksums for different databases
        """
        res = await self.command(G90Commands.GETUSERDATACRC)
        return G90UserDataCRC(*res)

    async def history(
        self, start: int = 1, count: int = 1
    ) -> List[G90History]:
        """
        Retrieves event history from the device.

        :param start: Starting record number (one-based)
        :param count: Number of records to retrieve
        :return: List of history entries
        """
        res = self.paginated_result(G90Commands.GETHISTORY,
                                    start, count)

        # Sort the history entries from older to newer - device typically does
        # that, but apparently that is not guaranteed
        return sorted(
            [G90History(*x.data) async for x in res],
            key=lambda x: x.datetime, reverse=True
        )

    async def on_sensor_activity(
        self, idx: int, name: str, occupancy: bool = True
    ) -> None:
        """
        Invoked both for sensor notifications and door open/close
        alerts, since the logic for both is same and could be reused.
        Fires corresponding callback if set by the user with
        :attr:`.sensor_callback`.

        Please note the method is for internal use by the class.

        :param idx: The index of the sensor the callback is invoked for.
         Please note the index is a property of sensor, not the direct index of
         :attr:`sensors` array
        :param name: The name of the sensor, along with the `idx` parameter
         it is used to look the sensor up from the :attr:`sensors` list
        :param occupancy: The flag indicating the target sensor state
         (=occupancy), will always be `True` for callbacks invoked from alarm
         panel notifications, and reflects actual sensor state for device
         alerts (only for `door` type sensors, if door open/close alerts are
         enabled)
        """
        _LOGGER.debug('on_sensor_activity: %s %s %s', idx, name, occupancy)
        sensor = await self.find_sensor(idx, name)
        if sensor:
            # Reset the low battery flag since the sensor reports activity,
            # implying it has sufficient battery power
            # pylint: disable=protected-access
            sensor._set_low_battery(False)
            # Set the sensor occupancy
            # pylint: disable=protected-access
            sensor._set_occupancy(occupancy)

            # Emulate turning off the occupancy - most of sensors will not
            # notify the device of that, nor the device would emit such
            # notification itself
            def reset_sensor_occupancy(sensor: G90Sensor) -> None:
                sensor._set_occupancy(False)
                G90Callback.invoke(sensor.state_callback, sensor.occupancy)

            # Determine if door close notifications are available for the given
            # sensor
            door_close_alert_enabled = await self.alert_config.get_flag(
                G90AlertConfigFlags.DOOR_CLOSE
            )
            # The condition intentionally doesn't account for cord sensors of
            # subtype door, since those won't send door open/close alerts, only
            # notifications
            sensor_is_door = sensor.type == G90SensorTypes.DOOR

            # Alarm panel could emit door close alerts (if enabled) for sensors
            # of type `door`, and such event will be used to reset the
            # occupancy for the given sensor. Otherwise, the sensor closing
            # event will be emulated
            if not door_close_alert_enabled or not sensor_is_door:
                _LOGGER.debug("Sensor '%s' is not a door (type %s),"
                              ' or door close alert is disabled'
                              ' (alert config flags %s) or is a cord sensor,'
                              ' closing event will be emulated upon'
                              ' %s seconds',
                              name, sensor.type,
                              await self.alert_config.flags,
                              self._reset_occupancy_interval)
                G90Callback.invoke_delayed(
                    self._reset_occupancy_interval,
                    reset_sensor_occupancy, sensor)

            # Invoke per-sensor callback if provided
            G90Callback.invoke(sensor.state_callback, occupancy)

        # Invoke global callback if provided
        G90Callback.invoke(self._sensor_cb, idx, name, occupancy)

    @property
    def sensor_callback(self) -> Optional[SensorCallback]:
        """
        Sensor activity callback, which is invoked when sensor activates.
        """
        return self._sensor_cb

    @sensor_callback.setter
    def sensor_callback(self, value: SensorCallback) -> None:
        self._sensor_cb = value

    async def on_door_open_close(
        self, event_id: int, zone_name: str, is_open: bool
    ) -> None:
        """
        Invoked when door open/close alert comes from the alarm
        panel. Fires corresponding callback if set by the user with
        :attr:`.door_open_close_callback`.

        Please note the method is for internal use by the class.

        .. seealso:: :meth:`.on_sensor_activity` method for arguments
        """
        # Same internal callback is reused both for door open/close alerts and
        # sensor notifications. The former adds reporting when a door is
        # closed, since the notifications aren't sent for such events
        await self.on_sensor_activity(event_id, zone_name, is_open)
        # Invoke user specified callback if any
        G90Callback.invoke(
            self._door_open_close_cb, event_id, zone_name, is_open
        )

    @property
    def door_open_close_callback(self) -> Optional[DoorOpenCloseCallback]:
        """
        The door open/close callback, which is invoked when door
        is opened or closed (if corresponding alert is configured on the
        device).
        """
        return self._door_open_close_cb

    @door_open_close_callback.setter
    def door_open_close_callback(self, value: DoorOpenCloseCallback) -> None:
        self._door_open_close_cb = value

    async def on_armdisarm(self, state: G90ArmDisarmTypes) -> None:
        """
        Invoked when the device is armed or disarmed.  Fires corresponding
        callback if set by the user with :attr:`.armdisarm_callback`.

        Please note the method is for internal use by the class.

        :param state: Device state (armed, disarmed, armed home)
        """
        if self._sms_alert_when_armed:
            await self.alert_config.set_flag(
                G90AlertConfigFlags.SMS_PUSH,
                state in (
                    G90ArmDisarmTypes.ARM_AWAY, G90ArmDisarmTypes.ARM_HOME
                )
            )

        # Reset the tampered and door open when arming flags on all sensors
        # having those set
        for sensor in await self.sensors:
            if sensor.is_tampered:
                # pylint: disable=protected-access
                sensor._set_tampered(False)
            if sensor.is_door_open_when_arming:
                # pylint: disable=protected-access
                sensor._set_door_open_when_arming(False)

        G90Callback.invoke(self._armdisarm_cb, state)

    @property
    def armdisarm_callback(self) -> Optional[ArmDisarmCallback]:
        """
        The device arm/disarm callback, which is invoked when device state
        changes.
        """
        return self._armdisarm_cb

    @armdisarm_callback.setter
    def armdisarm_callback(self, value: ArmDisarmCallback) -> None:
        self._armdisarm_cb = value

    async def on_alarm(
        self, event_id: int, zone_name: str, is_tampered: bool
    ) -> None:
        """
        Invoked when alarm is triggered. Fires corresponding callback if set by
        the user with :attr:`.alarm_callback`.

        Please note the method is for internal use by the class.

        :param event_id: Index of the sensor triggered alarm
        :param zone_name: Sensor name
        """
        sensor = await self.find_sensor(event_id, zone_name)
        extra_data = None
        if sensor:
            # The callback is still delivered to the caller even if the sensor
            # isn't found, only `extra_data` is skipped. That is to ensure the
            # important callback isn't filtered
            extra_data = sensor.extra_data

            # Invoke the sensor activity callback to set the sensor occupancy
            # if sensor is known, but only if that isn't already set - it helps
            # when device notifications on triggerring sensor's activity aren't
            # receveid by a reason
            if not sensor.occupancy:
                await self.on_sensor_activity(event_id, zone_name, True)

            if is_tampered:
                # Set the tampered flag on the sensor
                # pylint: disable=protected-access
                sensor._set_tampered(True)

                # Invoke per-sensor callback if provided
                G90Callback.invoke(sensor.tamper_callback)

        # Invoke global tamper callback if provided and the sensor is tampered
        if is_tampered:
            G90Callback.invoke(self._tamper_cb, event_id, zone_name)

        G90Callback.invoke(
            self._alarm_cb, event_id, zone_name, extra_data
        )

    @property
    def alarm_callback(self) -> Optional[AlarmCallback]:
        """
        The device alarm callback, which is invoked when device alarm triggers.
        """
        return self._alarm_cb

    @alarm_callback.setter
    def alarm_callback(self, value: AlarmCallback) -> None:
        self._alarm_cb = value

    async def on_low_battery(self, event_id: int, zone_name: str) -> None:
        """
        Invoked when the sensor reports on low battery. Fires
        corresponding callback if set by the user with
        :attr:`.on_low_battery_callback`.

        Please note the method is for internal use by the class.

        :param event_id: Index of the sensor triggered alarm
        :param zone_name: Sensor name
        """
        _LOGGER.debug('on_low_battery: %s %s', event_id, zone_name)
        sensor = await self.find_sensor(event_id, zone_name)
        if sensor:
            # Set the low battery flag on the sensor
            # pylint: disable=protected-access
            sensor._set_low_battery(True)
            # Invoke per-sensor callback if provided
            G90Callback.invoke(sensor.low_battery_callback)

        G90Callback.invoke(self._low_battery_cb, event_id, zone_name)

    @property
    def low_battery_callback(self) -> Optional[LowBatteryCallback]:
        """
        Low battery callback, which is invoked when sensor reports the
        condition.
        """
        return self._low_battery_cb

    @low_battery_callback.setter
    def low_battery_callback(self, value: LowBatteryCallback) -> None:
        self._low_battery_cb = value

    async def on_sos(
        self, event_id: int, zone_name: str, is_host_sos: bool
    ) -> None:
        """
        Invoked when SOS alert is triggered. Fires corresponding callback if
        set by the user with :attr:`.sos_callback`.

        Please note the method is for internal use by the class.

        :param event_id: Index of the sensor triggered alarm
        :param zone_name: Sensor name
        :param is_host_sos:
          Flag indicating if the SOS alert is triggered by the panel itself
          (host)
        """
        _LOGGER.debug('on_sos: %s %s %s', event_id, zone_name, is_host_sos)
        G90Callback.invoke(self._sos_cb, event_id, zone_name, is_host_sos)

        # Also report the event as alarm for unification, hard-coding the
        # sensor name in case of host SOS
        await self.on_alarm(
            event_id, zone_name='Host SOS' if is_host_sos else zone_name,
            is_tampered=False
        )

        if not is_host_sos:
            # Also report the remote button press for SOS - the panel will not
            # send corresponding alert
            await self.on_remote_button_press(
                event_id, zone_name, G90RemoteButtonStates.SOS
            )

    @property
    def sos_callback(self) -> Optional[SosCallback]:
        """
        SOS callback, which is invoked when SOS alert is triggered.
        """
        return self._sos_cb

    @sos_callback.setter
    def sos_callback(self, value: SosCallback) -> None:
        self._sos_cb = value

    async def on_remote_button_press(
        self, event_id: int, zone_name: str, button: G90RemoteButtonStates
    ) -> None:
        """
        Invoked when remote button is pressed. Fires corresponding callback if
        set by the user with :attr:`.remote_button_press_callback`.

        Please note the method is for internal use by the class.

        :param event_id: Index of the sensor triggered alarm
        :param zone_name: Sensor name
        :param button: The button pressed
        """
        _LOGGER.debug(
            'on_remote_button_press: %s %s %s', event_id, zone_name, button
        )
        G90Callback.invoke(
            self._remote_button_press_cb, event_id, zone_name, button
        )

        # Also report the event as sensor activity for unification (remote is
        # just a special type of the sensor)
        await self.on_sensor_activity(event_id, zone_name, True)

    @property
    def remote_button_press_callback(
        self
    ) -> Optional[RemoteButtonPressCallback]:
        """
        Remote button press callback, which is invoked when remote button is
        pressed.
        """
        return self._remote_button_press_cb

    @remote_button_press_callback.setter
    def remote_button_press_callback(
        self, value: RemoteButtonPressCallback
    ) -> None:
        self._remote_button_press_cb = value

    async def on_door_open_when_arming(
        self, event_id: int, zone_name: str
    ) -> None:
        """
        Invoked when door is open when arming the device. Fires corresponding
        callback if set by the user with
        :attr:`.door_open_when_arming_callback`.

        Please note the method is for internal use by the class.

        :param event_id: The index of the sensor being active when the panel
         is being armed.
        :param zone_name: The name of the sensor
        """
        _LOGGER.debug('on_door_open_when_arming: %s %s', event_id, zone_name)
        sensor = await self.find_sensor(event_id, zone_name)
        if sensor:
            # Set the low battery flag on the sensor
            # pylint: disable=protected-access
            sensor._set_door_open_when_arming(True)
            # Invoke per-sensor callback if provided
            G90Callback.invoke(sensor.door_open_when_arming_callback)

        G90Callback.invoke(self._door_open_when_arming_cb, event_id, zone_name)

    @property
    def door_open_when_arming_callback(
        self
    ) -> Optional[DoorOpenWhenArmingCallback]:
        """
        Door open when arming callback, which is invoked when sensor reports
        the condition.
        """
        return self._door_open_when_arming_cb

    @door_open_when_arming_callback.setter
    def door_open_when_arming_callback(
        self, value: DoorOpenWhenArmingCallback
    ) -> None:
        self._door_open_when_arming_cb = value

    @property
    async def tamper_callback(self) -> Optional[TamperCallback]:
        """
        Tamper callback, which is invoked when sensor reports the condition.
        """
        return self._tamper_cb

    @tamper_callback.setter
    def tamper_callback(self, value: TamperCallback) -> None:
        self._tamper_cb = value

    async def listen_notifications(self) -> None:
        """
        Starts internal listener for device notifications/alerts.
        """
        if self._notifications:
            await self._notifications.listen()

    async def close_notifications(self) -> None:
        """
        Closes the listener for device notifications/alerts.
        """
        if self._notifications:
            await self._notifications.close()

    async def arm_away(self) -> None:
        """
        Arms the device in away mode.
        """
        state = G90ArmDisarmTypes.ARM_AWAY
        await self.command(G90Commands.SETHOSTSTATUS,
                           [state])

    async def arm_home(self) -> None:
        """
        Arms the device in home mode.
        """
        state = G90ArmDisarmTypes.ARM_HOME
        await self.command(G90Commands.SETHOSTSTATUS,
                           [state])

    async def disarm(self) -> None:
        """
        Disarms the device.
        """
        state = G90ArmDisarmTypes.DISARM
        await self.command(G90Commands.SETHOSTSTATUS,
                           [state])

    @property
    def sms_alert_when_armed(self) -> bool:
        """
        When enabled, allows to save costs on SMS by having corresponding alert
        enabled only when device is armed.
        """
        return self._sms_alert_when_armed

    @sms_alert_when_armed.setter
    def sms_alert_when_armed(self, value: bool) -> None:
        self._sms_alert_when_armed = value

    async def start_simulating_alerts_from_history(
        self, interval: float = 5, history_depth: int = 5
    ) -> None:
        """
        Starts the separate task to simulate device alerts from history
        entries.

        The listener for device notifications will be stopped, so device
        notifications will not be processed thus resulting in possible
        duplicated if those could be received from the network.

        :param interval: Interval (in seconds) between polling for newer
          history entities
        :param history_depth: Amount of history entries to fetch during
          each polling cycle
        """
        # Remember if device notifications listener has been started already
        self._alert_simulation_start_listener_back = (
            self._notifications is not None
            and self._notifications.listener_started
        )
        # And then stop it
        await self.close_notifications()

        # Start the task
        self._alert_simulation_task = asyncio.create_task(
            self._simulate_alerts_from_history(interval, history_depth)
        )

    async def stop_simulating_alerts_from_history(self) -> None:
        """
        Stops the task simulating device alerts from history entries.

        The listener for device notifications will be started back, if it was
        running when simulation has been started.
        """
        # Stop the task simulating the device alerts from history if it was
        # running
        if self._alert_simulation_task:
            self._alert_simulation_task.cancel()
            self._alert_simulation_task = None

        # Start device notifications listener back if it was running when
        # simulated alerts have been enabled
        if (
            self._notifications
            and self._alert_simulation_start_listener_back
        ):
            await self._notifications.listen()

    async def _simulate_alerts_from_history(
        self, interval: float, history_depth: int
    ) -> None:
        """
        Periodically fetches history entries from the device and simulates
        device alerts off of those.

        Only the history entries occur after the process is started are
        handled, to avoid triggering callbacks retrospectively.

        See :meth:`.start_simulating_alerts_from_history` for the parameters.
        """
        dummy_notifications = G90NotificationsBase(
            protocol_factory=lambda: self
        )

        last_history_ts = None

        _LOGGER.debug(
            'Simulating device alerts from history:'
            ' interval %s, history depth %s',
            interval, history_depth
        )
        while True:
            try:
                # Retrieve the history entries of the specified amount - full
                # history retrieval might be an unnecessary long operation
                history = await self.history(count=history_depth)

                # Initial iteration where no timestamp of most recent history
                # entry is recorded - do that and skip to next iteration, since
                # it isn't yet known what entries would be considered as new
                # ones.
                # Empty history will skip recording the timestamp and the
                # looping over entries below, effectively skipping to next
                # iteration
                if not last_history_ts and history:
                    # First entry in the list is assumed to be the most recent
                    # one
                    last_history_ts = history[0].datetime
                    _LOGGER.debug(
                        'Initial time stamp of last history entry: %s',
                        last_history_ts
                    )
                    continue

                # Process history entries from older to newer to preserve the
                # order of happenings
                for item in reversed(history):
                    # Process only the entries newer than one been recorded as
                    # most recent one
                    if last_history_ts and item.datetime > last_history_ts:
                        _LOGGER.debug(
                            'Found newer history entry: %s, simulating alert',
                            repr(item)
                        )
                        # Send the history entry down the device notification
                        # code as alert, as if it came from the device and its
                        # notifications port
                        dummy_notifications.handle_alert(
                            item.as_device_alert(),
                            # Skip verifying device GUID, since history entry
                            # don't have it
                            verify_device_id=False
                        )

                        # Record the entry as most recent one
                        last_history_ts = item.datetime
                        _LOGGER.debug(
                            'Time stamp of last history entry: %s',
                            last_history_ts
                        )
            except (G90Error, G90TimeoutError) as exc:
                _LOGGER.debug(
                    'Error interacting with device, ignoring %s', repr(exc)
                )
            except Exception as exc:
                _LOGGER.error(
                    'Exception simulating device alerts from history: %s',
                    repr(exc)
                )
                raise exc

            # Sleep to next iteration
            await asyncio.sleep(interval)

    async def use_local_notifications(
        self, notifications_local_host: str = LOCAL_NOTIFICATIONS_HOST,
        notifications_local_port: int = LOCAL_NOTIFICATIONS_PORT
    ) -> None:
        """
        Switches to use local notifications for device alerts.
        """
        await self.close_notifications()

        self._notifications = G90LocalNotifications(
            protocol_factory=lambda: self,
            host=self._host,
            port=self._port,
            local_host=notifications_local_host,
            local_port=notifications_local_port
        )

    async def use_cloud_notifications(
        self, cloud_local_host: str = CLOUD_NOTIFICATIONS_HOST,
        cloud_local_port: int = CLOUD_NOTIFICATIONS_PORT,
        upstream_host: Optional[str] = REMOTE_CLOUD_HOST,
        upstream_port: Optional[int] = REMOTE_CLOUD_PORT,
        keep_single_connection: bool = True
    ) -> None:
        """
        Switches to use cloud notifications for device alerts.
        """
        await self.close_notifications()

        self._notifications = G90CloudNotifications(
            protocol_factory=lambda: self,
            upstream_host=upstream_host,
            upstream_port=upstream_port,
            local_host=cloud_local_host,
            local_port=cloud_local_port,
            keep_single_connection=keep_single_connection
        )

    @property
    def last_device_packet_time(self) -> Optional[datetime]:
        """
        Returns the time of the last packet received from the device.
        """
        if not self._notifications:
            return None

        return self._notifications.last_device_packet_time

    @property
    def last_upstream_packet_time(self) -> Optional[datetime]:
        """
        Returns the time of the last packet received from the upstream server.
        """
        if not self._notifications:
            return None

        return self._notifications.last_upstream_packet_time

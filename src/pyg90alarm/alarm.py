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
Provides interface to G90 alarm panel.

.. note:: Only protocol 1.2 is supported!

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
import asyncio
import logging
from .const import (
    G90Commands, REMOTE_PORT,
    REMOTE_TARGETED_DISCOVERY_PORT,
    LOCAL_TARGETED_DISCOVERY_PORT,
    NOTIFICATIONS_PORT,
    G90ArmDisarmTypes,
)
from .base_cmd import G90BaseCommand
from .paginated_result import G90PaginatedResult
from .entities.sensor import (G90Sensor, G90SensorTypes)
from .entities.device import G90Device
from .device_notifications import (
    G90DeviceNotifications,
)
from .discovery import G90Discovery
from .targeted_discovery import G90TargetedDiscovery
from .host_info import G90HostInfo
from .host_status import G90HostStatus
from .config import (G90AlertConfig, G90AlertConfigFlags)
from .history import G90History
from .user_data_crc import G90UserDataCRC
from .callback import G90Callback

_LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-public-methods
class G90Alarm(G90DeviceNotifications):

    """
    Allows to interact with G90 alarm panel.

    :param str host: Hostname or IP address of the alarm panel. Since the
     protocol is UDP-based it is ok to use broadcast or directed broadcast
     addresses, such as `255.255.255.255` or `10.10.10.255` (the latter assumes
     the device is on `10.10.10.0/24` network)
    :param port: The UDP port of the device where it listens for the
     protocol commands on WiFi interface, currently the devices don't allow it
     to be customized
    :type port: int, optional
    :param reset_occupancy_interval: The interval upon that the sensors are
     simulated to go into inactive state.
    :type reset_occupancy_interval: int, optional
    """
    # pylint: disable=too-many-instance-attributes,too-many-arguments
    def __init__(self, host, port=REMOTE_PORT,
                 reset_occupancy_interval=3,
                 notifications_host='0.0.0.0',
                 notifications_port=NOTIFICATIONS_PORT):
        super().__init__(host=notifications_host, port=notifications_port)
        self._host = host
        self._port = port
        self._sensors = []
        self._devices = []
        self._notifications = None
        self._sensor_cb = None
        self._armdisarm_cb = None
        self._door_open_close_cb = None
        self._alarm_cb = None
        self._low_battery_cb = None
        self._reset_occupancy_interval = reset_occupancy_interval
        self._alert_config = None
        self._sms_alert_when_armed = False
        self._alert_simulation_task = None
        self._alert_simulation_start_listener_back = False

    async def command(self, code, data=None):
        """
        Invokes a command against the alarm panel.

        :param code: Command code
        :type code: :class:`.G90Commands`
        :param data: Command data
        :type data: object or None, optional
        :return: :attr:`.G90BaseCommand.result` that contains the result of
         command invocation
        """
        cmd = await G90BaseCommand(
            self._host, self._port, code, data).process()
        return cmd.result

    def paginated_result(self, code, start=1, end=None):
        """
        Returns asynchronous generator for a paginated command, that is -
        command operating on a range of records.

        :param code: Command code
        :type code: :class:`.G90Commands`
        :param int start: Starting record position (one-based)
        :param int end: Ending record position (one-based)
        :return: :class:`.G90PaginatedResult` being asynchronous generator
          over the result of command invocation. Each access to the generator
          yields :class:`.G90PaginatedResponse` instance
        """
        return G90PaginatedResult(
            self._host, self._port, code, start, end
        ).process()

    @classmethod
    async def discover(cls):
        """
        Initiates discovering devices available in the same network segment, by
        using global broadcast address as the destination.

        :return: List of discovered devices
        :rtype: list[{'guid', 'host', 'port'}]
        """
        return await G90Discovery(
            port=REMOTE_PORT,
            host='255.255.255.255'
        ).process()

    @classmethod
    async def targeted_discover(cls, device_id):
        """
        Initiates discovering devices available in the same network segment
        using targeted protocol, that is - specifying target device GUID in the
        request, so only the specific device should respond to the query.

        :param device_id: GUID of the target device to discover
        :type device_id: str
        :return: List of discovered devices
        :rtype: list[{'guid', 'host', 'port'}]
        """
        return await G90TargetedDiscovery(
            device_id=device_id,
            port=REMOTE_TARGETED_DISCOVERY_PORT,
            local_port=LOCAL_TARGETED_DISCOVERY_PORT,
            host='255.255.255.255'
        ).process()

    @property
    async def sensors(self):
        """
        Property over new :meth:`.get_sensors` method, retained for
        compatibility.
        """
        return await self.get_sensors()

    async def get_sensors(self):
        """
        Provides list of sensors configured in the device. Please note the list
        is cached upon first call, so you need to re-instantiate the class to
        reflect any updates there.

        :return: List of sensors
        :rtype: list(:class:`.G90Sensor`)
        """
        if not self._sensors:
            sensors = self.paginated_result(
                G90Commands.GETSENSORLIST
            )
            async for sensor in sensors:
                obj = G90Sensor(
                    *sensor.data, parent=self, subindex=0,
                    proto_idx=sensor.proto_idx
                )
                self._sensors.append(obj)

            _LOGGER.debug('Total number of sensors: %s', len(self._sensors))

        return self._sensors

    async def find_sensor(self, idx, name):
        """
        Finds sensor by index and name.

        :param int idx: Sensor index
        :param str name: Sensor name
        :return: Sensor instance
        :rtype :class:`.G90Sensor`|None
        """
        sensors = await self.get_sensors()

        # Fast lookup by direct index
        if idx < len(sensors) and sensors[idx].name == name:
            sensor = sensors[idx]
            _LOGGER.debug('Found sensor via fast lookup: %s', sensor)
            return sensor

        # Fast lookup failed, perform slow one over the whole sensors list
        for sensor in sensors:
            if sensor.index == idx and sensor.name == name:
                _LOGGER.debug('Found sensor: %s', sensor)
                return sensor

        _LOGGER.error('Sensor not found: idx=%s, name=%s', idx, name)
        return None

    @property
    async def devices(self):
        """
        Property over new :meth:`.get_devices` method, retained for
        compatibility.
        """
        return await self.get_devices()

    async def get_devices(self):
        """
        Provides list of devices (switches) configured in the device. Please
        note the list is cached upon first call, so you need to re-instantiate
        the class to reflect any updates there. Multi-node devices, those
        having multiple ports, are expanded into corresponding number of
        resulting entries.

        :return: List of devices
        :rtype: list(:class:`.G90Device`)
        """
        if not self._devices:
            devices = self.paginated_result(
                G90Commands.GETDEVICELIST
            )
            async for device in devices:
                obj = G90Device(
                    *device.data, parent=self, subindex=0,
                    proto_idx=device.proto_idx
                )
                self._devices.append(obj)
                # Multi-node devices (first node has already been added
                # above
                for node in range(1, obj.node_count):
                    obj = G90Device(
                        *device.data, parent=self,
                        subindex=node, proto_idx=device.proto_idx
                    )
                    self._devices.append(obj)

            _LOGGER.debug('Total number of devices: %s', len(self._devices))

        return self._devices

    @property
    async def host_info(self):
        """
        Property over new :meth:`.get_host_info` method, retained for
        compatibility.
        """
        return await self.get_host_info()

    async def get_host_info(self):
        """
        Provides the device information (for example hardware versions, signal
        levels etc.).

        :return: Device information
        :rtype: Instance of :class:`.G90HostInfo`
        """
        res = await self.command(G90Commands.GETHOSTINFO)
        return G90HostInfo(*res)

    @property
    async def host_status(self):
        """
        Property over new :meth:`.get_host_status` method, retained for
        compatibility.
        """
        return await self.get_host_status()

    async def get_host_status(self):
        """
        Provides the device status (for example, armed or disarmed, configured
        phone number, product name etc.).

        :return: Device information
        :rtype: Instance of :class:`.G90HostStatus`

        """
        res = await self.command(G90Commands.GETHOSTSTATUS)
        return G90HostStatus(*res)

    @property
    async def alert_config(self):
        """
        Property over new :meth:`.get_alert_config` method, retained for
        compatibility.
        """
        return await self.get_alert_config()

    async def get_alert_config(self):
        """
        Retrieves the alert configuration flags from the device. Please note
        the configuration is cached upon first call, so you need to
        re-instantiate the class to reflect any updates there.

        :return: Instance of :class:`.G90AlertConfigFlags` containing the
         alerts configured
        """
        if not self._alert_config:
            self._alert_config = await self._alert_config_uncached()
        return self._alert_config

    async def _alert_config_uncached(self):
        """
        Retrieves the alert configuration flags directly from the device.

        :return: Instance of :class:`.G90AlertConfigFlags` containing the
         alerts configured
        """
        res = await self.command(G90Commands.GETNOTICEFLAG)
        return G90AlertConfig(*res).flags

    async def set_alert_config(self, value):
        """
        It might be possible to implement the async property setter with
        `async_as_sync` decorator, although it might have implications with the
        setter not executed if the program terminates earlier. Hence, for the
        sake of better predictability this is implemented as regular
        (non-property) method
        """
        # Use uncached method retrieving the alert configuration, to ensure the
        # actual value retrieved from the device
        alert_config = await self._alert_config_uncached()
        if alert_config != self._alert_config:
            _LOGGER.warning(
                'Alert configuration changed externally,'
                ' overwriting (read "%s", will be set to "%s")',
                str(alert_config), str(value)
            )
        await self.command(G90Commands.SETNOTICEFLAG, [value])
        # Update the alert configuration stored
        self._alert_config = value

    @property
    async def user_data_crc(self):
        """
        Property over new :meth:`.get_user_data_crc` method, retained for
        compatibility.
        """
        return await self.get_user_data_crc()

    async def get_user_data_crc(self):
        """
        Retieves checksums (CRC) for different on-device databases (history,
        sensors etc.). Might be used to detect if there is a change in a
        particular database.

        .. note:: Note that due to a bug in the firmware CRC for sensos and
          device databases change on each call even if there were no changes

        :return: Instance of :class:`.G90UserDataCRC` containing checksums for
          different databases
        """
        res = await self.command(G90Commands.GETUSERDATACRC)
        return G90UserDataCRC(*res)

    async def history(self, start=1, count=1):
        """
        Retrieves event history from the device.

        :param start: Starting record number (one-based)
        :type start: int
        :param count: Number of records to retrieve
        :type count: int
        :return: List of history entries
        :rtype: list[:class:`.G90History`]
        """
        res = self.paginated_result(G90Commands.GETHISTORY,
                                    start, count)

        # Sort the history entries from older to newer - device typically does
        # that, but apparently that is not guaranteed
        return sorted(
            [G90History(*x.data) async for x in res],
            key=lambda x: x.datetime, reverse=True
        )

    async def on_sensor_activity(self, idx, name, occupancy=True):
        """
        Callback that invoked both for sensor notifications and door open/close
        alerts, since the logic for both is same and could be reused. Please
        note the callback is for internal use by the class.

        :param int idx: The index of the sensor the callback is invoked for.
         Please note the index is a property of sensor, not the direct index of
         :attr:`sensors` array
        :param str name: The name of the sensor, along with the `idx` parameter
         it is used to look the sensor up from the :attr:`sensors` list
        :param bool occupancy: The flag indicating the target sensor state
         (=occupancy), will always be `True` for callbacks invoked from alarm
         panel notifications, and reflects actual sensor state for device
         alerts (only for `door` type sensors, if door open/close alerts are
         enabled)
        """
        _LOGGER.debug('on_sensor_acitvity: %s %s %s', idx, name, occupancy)
        sensor = await self.find_sensor(idx, name)
        if sensor:
            _LOGGER.debug('Setting occupancy to %s (previously %s)',
                          occupancy, sensor.occupancy)
            sensor.occupancy = occupancy

            # Emulate turning off the occupancy - most of sensors will not
            # notify the device of that, nor the device would emit such
            # notification itself
            def reset_sensor_occupancy(sensor):
                _LOGGER.debug('Resetting occupancy for sensor %s', sensor)
                sensor.occupancy = False
                G90Callback.invoke(sensor.state_callback, sensor.occupancy)

            # Determine if door close notifications are available for the given
            # sensor
            alert_config_flags = await self.alert_config
            door_close_alert_enabled = (
                G90AlertConfigFlags.DOOR_CLOSE in alert_config_flags)
            sensor_is_door = sensor.type == G90SensorTypes.DOOR

            # Alarm panel could emit door close alerts (if enabled) for sensors
            # of type `door`, and such event will be used to reset the
            # occupancy for the given sensor. Otherwise, the sensor closing
            # event will be emulated
            if not door_close_alert_enabled or not sensor_is_door:
                _LOGGER.debug("Sensor '%s' is not a door (type %s),"
                              ' or door close alert is disabled'
                              ' (alert config flags %s),'
                              ' closing event will be emulated upon'
                              ' %s seconds',
                              name, sensor.type, alert_config_flags,
                              self._reset_occupancy_interval)
                G90Callback.invoke_delayed(
                    self._reset_occupancy_interval,
                    reset_sensor_occupancy, sensor)

            # Invoke per-sensor callback if provided
            G90Callback.invoke(sensor.state_callback, occupancy)

        # Invoke global callback if provided
        G90Callback.invoke(self._sensor_cb, idx, name, occupancy)

    @property
    def sensor_callback(self):
        """
        Get or set sensor activity callback, the callback is invoked when
        sensor activates.

        :type: .. py:function:: ()(idx, name, occupancy)
        """
        return self._sensor_cb

    @sensor_callback.setter
    def sensor_callback(self, value):
        self._sensor_cb = value

    async def on_door_open_close(self, event_id, zone_name, is_open):
        """
        Callback that invoked when door open/close alert comes from the alarm
        panel. Please note the callback is for internal use by the class.

        .. seealso:: `method`:on_sensor_activity for arguments
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
    def door_open_close_callback(self):
        """
        Get or set door open/close callback, the callback is invoked when door
        is opened or closed (if corresponding alert is configured on the
        device).

        :type: .. py:function:: ()(idx: int, name: str, is_open: bool)
        """
        return self._door_open_close_cb

    @door_open_close_callback.setter
    def door_open_close_callback(self, value):
        """
        Sets callback for door open/close events.
        """
        self._door_open_close_cb = value

    async def on_armdisarm(self, state):
        """
        Callback that invoked when the device is armed or disarmed. Please note
        the callback is for internal use by the class.

        :param state: Device state (armed, disarmed, armed home)
        :type state: :class:`G90ArmDisarmTypes`
        """
        if self._sms_alert_when_armed:
            if state == G90ArmDisarmTypes.DISARM:
                # Disable SMS alerts from the device
                await self.set_alert_config(
                    await self.alert_config & ~G90AlertConfigFlags.SMS_PUSH
                )
            if state in (G90ArmDisarmTypes.ARM_AWAY,
                         G90ArmDisarmTypes.ARM_HOME):
                # Enable SMS alerts from the device
                await self.set_alert_config(
                    await self.alert_config | G90AlertConfigFlags.SMS_PUSH
                )
        G90Callback.invoke(self._armdisarm_cb, state)

    @property
    def armdisarm_callback(self):
        """
        Get or set device arm/disarm callback, the callback is invoked when
        device state changes.

        :type: .. py:function:: ()(state: :class:`.G90ArmDisarmTypes`)
        """
        return self._armdisarm_cb

    @armdisarm_callback.setter
    def armdisarm_callback(self, value):
        self._armdisarm_cb = value

    async def on_alarm(self, event_id, zone_name):
        """
        Callback that invoked when alarm is triggered. Fires alarm callback if
        set by the user with `:property:G90Alarm.alarm_callback`.
        Please note the callback is for internal use by the class.

        :param int: Index of the sensor triggered alarm
        :param str: Sensor name
        """
        sensor = await self.find_sensor(event_id, zone_name)
        # The callback is still delivered to the caller even if the sensor
        # isn't found, only `extra_data` is skipped. That is to ensur the
        # important callback isn't filtered
        extra_data = sensor.extra_data if sensor else None

        G90Callback.invoke(
            self._alarm_cb, event_id, zone_name, extra_data
        )

    @property
    def alarm_callback(self):
        """
        Get or set device alarm callback, the callback is invoked when
        device alarm triggers.

        :type:
          .. py:function:: ()(
            sensor_idx: int, sensor_name: str, extra_data: str|None
          )
        """
        return self._alarm_cb

    @alarm_callback.setter
    def alarm_callback(self, value):
        self._alarm_cb = value

    async def on_low_battery(self, event_id, zone_name):
        """
        Callback that invoked when the sensor reports on low battery. Fires
        corresponding callback if set by the user with
        `:property:G90Alarm.on_low_battery_callback`.
        Please note the callback is for internal use by the class.

        :param int: Index of the sensor triggered alarm
        :param str: Sensor name
        """
        sensor = await self.find_sensor(event_id, zone_name)
        if sensor:
            # Invoke per-sensor callback if provided
            G90Callback.invoke(sensor.low_battery_callback)

        G90Callback.invoke(self._low_battery_cb, event_id, zone_name)

    @property
    def low_battery_callback(self):
        """
        Get or set low battery callback, the callback is invoked when sensor
        the condition is reported by a sensor.

        :type: .. py:function:: ()(idx, name)
        """
        return self._low_battery_cb

    @low_battery_callback.setter
    def low_battery_callback(self, value):
        self._low_battery_cb = value

    async def listen_device_notifications(self):
        """
        Starts internal listener for device notifications/alerts.

        """
        await self.listen()

    def close_device_notifications(self):
        """
        Closes the listener for device notifications/alerts.
        """
        self.close()

    async def arm_away(self):
        """
        Arms the device in away mode.
        """
        state = G90ArmDisarmTypes.ARM_AWAY
        await self.command(G90Commands.SETHOSTSTATUS,
                           [state])

    async def arm_home(self):
        """
        Arms the device in home mode.
        """
        state = G90ArmDisarmTypes.ARM_HOME
        await self.command(G90Commands.SETHOSTSTATUS,
                           [state])

    async def disarm(self):
        """
        Disarms the device.
        """
        state = G90ArmDisarmTypes.DISARM
        await self.command(G90Commands.SETHOSTSTATUS,
                           [state])

    @property
    def sms_alert_when_armed(self):
        """
        When enabled, allows to save costs on SMS by having corresponding alert
        enabled only when device is armed.
        """
        return self._sms_alert_when_armed

    @sms_alert_when_armed.setter
    def sms_alert_when_armed(self, value):
        self._sms_alert_when_armed = value

    async def start_simulating_alerts_from_history(
        self, interval=5, history_depth=5
    ):
        """
        Starts the separate task to simulate device alerts from history
        entries.

        The listener for device notifications will be stopped, so device
        notifications will not be processed thus resulting in possible
        duplicated if those could be received from the network.

        :param int interval: Interval (in seconds) between polling for newer
          history entities
        :param int history_depth: Amount of history entries to fetch during
          each polling cycle
        """
        # Remember if device notifications listener has been started already
        self._alert_simulation_start_listener_back = self.listener_started
        # And then stop it
        self.close()

        # Start the task
        self._alert_simulation_task = asyncio.create_task(
            self._simulate_alerts_from_history(interval, history_depth)
        )

    async def stop_simulating_alerts_from_history(self):
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
        if self._alert_simulation_start_listener_back:
            await self.listen()

    async def _simulate_alerts_from_history(self, interval, history_depth):
        """
        Periodically fetches history entries from the device and simulates
        device alerts off of those.

        Only the history entries occur after the process is started are
        handled, to avoid triggering callbacks retrospectively.

        See :method:`start_simulating_alerts_from_history` for the parameters.
        """
        last_history_ts = None

        _LOGGER.debug(
            'Simulating device alerts from history:'
            ' interval %s, history depth %s',
            interval, history_depth
        )
        while True:
            # Retrieve the history entries of the specified amount - full
            # history retrieval might be an unnecessary long operation
            history = await self.history(count=history_depth)

            # Initial iteration where no timestamp of most recent history entry
            # is recorded - do that and skip to next iteration, since it isn't
            # yet known what entries would be considered as new ones
            if not last_history_ts:
                # First entry in the list is assumed to be the most recent one
                last_history_ts = history[0].datetime
                _LOGGER.debug(
                    'Initial time stamp of last history entry: %s',
                    last_history_ts
                )
                continue

            # Process history entries from older to newer to preserve the order
            # of happenings
            for item in reversed(history):
                # Process only the entries newer than one been recorded as most
                # recent one
                if item.datetime > last_history_ts:
                    _LOGGER.debug(
                        'Found newer history entry: %s, simulating alert',
                        repr(item)
                    )
                    # Send the history entry down the device notification code
                    # as alert, as if it came from the device and its
                    # notifications port
                    self._handle_alert(
                        (self._host, self._notifications_port),
                        item.as_device_alert()
                    )

                    # Record the entry as most recent one
                    last_history_ts = item.datetime
                    _LOGGER.debug(
                        'Time stamp of last history entry: %s', last_history_ts
                    )

            # Sleep to next iteration
            await asyncio.sleep(interval)

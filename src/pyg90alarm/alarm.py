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

import logging
from .const import (
    G90Commands, REMOTE_PORT,
    REMOTE_TARGETED_DISCOVERY_PORT,
    LOCAL_TARGETED_DISCOVERY_PORT,
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


class G90Alarm:  # pylint: disable=too-many-public-methods
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
    :param sock: The existing socket to operate on, instead of
     creating one internally. Primarily used by the tests to mock the network
     traffic
    :type sock: socket.socket or None, optional
    :param reset_occupancy_interval: The interval upon that the sensors are
     simulated to go into inactive state.
    :type reset_occupancy_interval: int, optional
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, host, port=REMOTE_PORT, sock=None,
                 reset_occupancy_interval=3):
        self._host = host
        self._port = port
        self._sensors = []
        self._devices = []
        self._notifications = None
        self._sock = sock
        self._sensor_cb = None
        self._armdisarm_cb = None
        self._door_open_close_cb = None
        self._reset_occupancy_interval = reset_occupancy_interval
        self._alert_config = None
        self._sms_alert_when_armed = False

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
            self._host, self._port, code, data, sock=self._sock).process()
        return cmd.result

    def paginated_result(self, code, start=1, end=None):
        """
        Returns asynchronous generator to for a paginated command, that is -
        command operating on a range of records.

        :param code: Command code
        :type code: :class:`.G90Commands`
        :param int start: Starting record position (one-based)
        :param int end: Ending record position (one-based)
        :return: :class:`.G90PaginatedResult` being asynchronous generator
          over the result of command invocation
        """
        return G90PaginatedResult(
            self._host, self._port, code, start, end, sock=self._sock
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
                obj = G90Sensor(*sensor, parent=self, subindex=0)
                self._sensors.append(obj)

            _LOGGER.debug('Total number of sensors: %s', len(self._sensors))

        return self._sensors

    @property
    async def devices(self):
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
            cmd = self.paginated_result(
                G90Commands.GETDEVICELIST
            )
            async for dev in cmd:
                obj = G90Device(*dev, parent=self, subindex=0)
                self._devices.append(obj)
                # Multi-node devices (first node has already been added
                # above
                for node in range(1, obj.node_count):
                    obj = G90Device(*dev, parent=self, subindex=node)
                    self._devices.append(obj)

            _LOGGER.debug('Total number of devices: %s', len(self._devices))

        return self._devices

    @property
    async def host_info(self):
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
        history = [G90History(*x) async for x in res]
        return history

    async def _internal_sensor_cb(self, idx, name, occupancy=True):
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
        sensors = await self.sensors

        # Fast lookup by direct index
        if idx < len(sensors) and sensors[idx].name == name:
            sensor = [sensors[idx]]
        # Fast lookup failed, perform slow one over the whole sensors list
        else:
            sensor = [
                x for x in sensors
                if x.index == idx and x.name == name
            ]
        if sensor:
            _LOGGER.debug('Found sensor: %s', sensor[0])
            _LOGGER.debug('Setting occupancy to %s (previously %s)',
                          occupancy, sensor[0].occupancy)
            sensor[0].occupancy = occupancy

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
            sensor_is_door = sensor[0].type == G90SensorTypes.DOOR

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
                              name, sensor[0].type, alert_config_flags,
                              self._reset_occupancy_interval)
                G90Callback.invoke_delayed(
                    self._reset_occupancy_interval,
                    reset_sensor_occupancy, sensor[0])

            # Invoke per-sensor callback if provided
            G90Callback.invoke(sensor[0].state_callback, occupancy)
        else:
            _LOGGER.error('Sensor not found: idx=%s, name=%s', idx, name)

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

    async def _internal_door_open_close_cb(self, idx, name, is_open):
        """
        Callback that invoked when door open/close alert comes from the alarm
        panel. Please note the callback is for internal use by the class.

        .. seealso:: `method`:_internal_sensor_cb for arguments
        """
        # Same internal callback is reused both for door open/close alerts and
        # sensor notifications. The former adds reporting when a door is
        # closed, since the notifications aren't sent for such events
        await self._internal_sensor_cb(idx, name, is_open)
        # Invoke user specified callback if any
        G90Callback.invoke(self._door_open_close_cb, idx, name, is_open)

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
        tbd
        """
        self._door_open_close_cb = value

    async def _internal_armdisarm_cb(self, state):
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

    async def listen_device_notifications(self, sock=None):
        """
        Starts internal listener for device notifications/alerts.

        :param sock: socket instance to listen on, mostly used by tests
        :type: socket.socket
        """
        self._notifications = G90DeviceNotifications(
            sensor_cb=self._internal_sensor_cb,
            door_open_close_cb=self._internal_door_open_close_cb,
            armdisarm_cb=self._internal_armdisarm_cb,
            sock=sock)
        await self._notifications.listen()

    def close_device_notifications(self):
        """
        Closes the listener for device notifications/alerts.
        """
        if self._notifications:
            self._notifications.close()

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

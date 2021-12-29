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
Provides interface to G90 Alarm panel.

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
)
from .base_cmd import G90BaseCommand
from .paginated_result import G90PaginatedResult
from .entities.sensor import G90Sensor
from .entities.device import G90Device
from .device_notifications import (
    G90DeviceNotifications,
)
from .discovery import G90Discovery
from .targeted_discovery import G90TargetedDiscovery
from .host_info import G90HostInfo
from .host_status import G90HostStatus
from .history import G90History
from .user_data_crc import G90UserDataCRC
from .callback import G90Callback

_LOGGER = logging.getLogger(__name__)


class G90Alarm:
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
        self._device_event_cb = None
        self._reset_occupancy_interval = reset_occupancy_interval

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
        Invokes a paginated command, that is - command operating on a range of
        records.

        :param code: Command code
        :type code: :class:`.G90Commands`
        :param int start: Starting record position (one-based)
        :param int end: Ending record position (one-based)
        :return: :class:`.G90PaginatedResult` that contains the result of
         command invocation
        """
        return G90PaginatedResult(
            self._host, self._port, code, start, end, sock=self._sock
        ).process()

    @classmethod
    async def discover(cls):
        """
        tbd
        """
        return await G90Discovery(
            port=REMOTE_PORT,
            host='255.255.255.255'
        ).process()

    @classmethod
    async def targeted_discover(cls, device_id):
        """
        tbd
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
        tbd
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
        tbd
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
        tbd
        """
        res = await self.command(G90Commands.GETHOSTINFO)
        return G90HostInfo(*res)

    @property
    async def host_status(self):
        """
        tbd
        """
        res = await self.command(G90Commands.GETHOSTSTATUS)
        return G90HostStatus(*res)

    @property
    async def user_data_crc(self):
        """
        tbd
        """
        res = await self.command(G90Commands.GETUSERDATACRC)
        return G90UserDataCRC(*res)

    async def history(self, start=1, count=1):
        """
        tbd
        """
        res = self.paginated_result(G90Commands.GETHISTORY,
                                    start, count)
        history = [G90History(*x) async for x in res]
        return history

    async def _internal_sensor_cb(self, idx, name):
        """
        tbd
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
            sensor[0].occupancy = True

            # Emulate turning off the ocuppancy - most of sensors will not
            # notify the device of that, nor the device would emit such
            # notification itself
            def reset_sensor_occupancy(sensor):
                _LOGGER.debug('Resetting occupancy for sensor %s', sensor)
                sensor.occupancy = False
                G90Callback.invoke(sensor.state_callback, sensor.occupancy)

            G90Callback.invoke_delayed(
                self._reset_occupancy_interval,
                reset_sensor_occupancy, sensor[0])

            # Invoke per-sensor callback if provided
            G90Callback.invoke(sensor[0].state_callback, sensor[0].occupancy)
        else:
            _LOGGER.error('Sensor not found: idx=%s, name=%s', idx, name)

        # Invoke global callback if provided
        G90Callback.invoke(self._sensor_cb, idx, name)

    @property
    def sensor_callback(self):
        """
        tbd
        """
        return self._sensor_cb

    @sensor_callback.setter
    def sensor_callback(self, value):
        """
        tbd
        """
        self._sensor_cb = value

    async def _internal_device_event_cb(self, data):
        """
        tbd
        """
        G90Callback.invoke(self._device_event_cb, data)

    @property
    def device_event_callback(self):
        """
        tbd
        """
        return self._device_event_cb

    @device_event_callback.setter
    def device_event_callback(self, value):
        """
        tbd
        """
        self._device_event_cb = value

    async def _internal_armdisarm_cb(self, state):
        """
        tbd
        """
        G90Callback.invoke(self._armdisarm_cb, state)

    @property
    def armdisarm_callback(self):
        """
        tbd
        """
        return self._armdisarm_cb

    @armdisarm_callback.setter
    def armdisarm_callback(self, value):
        """
        tbd
        """
        self._armdisarm_cb = value

    async def listen_device_notifications(self, sock=None):
        """
        tbd
        """
        self._notifications = G90DeviceNotifications(
            sensor_cb=self._internal_sensor_cb,
            device_event_cb=self._internal_device_event_cb,
            armdisarm_cb=self._internal_armdisarm_cb,
            sock=sock)
        await self._notifications.listen()

    def close_device_notifications(self):
        """
        tbd
        """
        if self._notifications:
            self._notifications.close()

    async def arm_away(self):
        """
        tbd
        """
        await self.command(G90Commands.SETHOSTSTATUS, [1])

    async def arm_home(self):
        """
        tbd
        """
        await self.command(G90Commands.SETHOSTSTATUS, [2])

    async def disarm(self):
        """
        tbd
        """
        await self.command(G90Commands.SETHOSTSTATUS, [3])

import sys
import asyncio
from unittest.mock import MagicMock
import asynctest
from .fixtures import G90Fixture
sys.path.extend(['src', '../src'])
from pyg90alarm.device_notifications import (   # noqa:E402
    G90DeviceNotifications,
    G90DeviceAlert,
)


class TestG90Notifications(G90Fixture):
    async def test_sensor_callback(self):
        future = self.loop.create_future()
        sensor_cb = MagicMock()
        sensor_cb.side_effect = lambda *args: future.set_result(True)
        notifications = G90DeviceNotifications(
            sensor_cb=sensor_cb, sock=self.socket_mock)
        await notifications.listen()
        asynctest.set_read_ready(self.socket_mock, self.loop)
        self.socket_mock.recvfrom.return_value = (
            b'[170,[5,[100,"Hall"]]]\0', ('mocked', 12345))
        await asyncio.wait([future], timeout=0.1)
        notifications.close()
        sensor_cb.assert_called_once_with(100, 'Hall')

    async def test_armdisarm_callback(self):
        future = self.loop.create_future()
        armdisarm_cb = MagicMock()
        armdisarm_cb.side_effect = lambda *args: future.set_result(True)
        notifications = G90DeviceNotifications(
            armdisarm_cb=armdisarm_cb, sock=self.socket_mock)
        await notifications.listen()
        asynctest.set_read_ready(self.socket_mock, self.loop)
        self.socket_mock.recvfrom.return_value = (
            b'[170,[1,[1]]]\0', ('mocked', 12345))
        await asyncio.wait([future], timeout=0.1)
        notifications.close()
        armdisarm_cb.assert_called_once_with(1)

    async def test_device_alert_callback(self):
        future = self.loop.create_future()
        device_alert_cb = MagicMock()
        device_alert_cb.side_effect = lambda *args: future.set_result(True)
        notifications = G90DeviceNotifications(
            device_alert_cb=device_alert_cb, sock=self.socket_mock)
        await notifications.listen()
        asynctest.set_read_ready(self.socket_mock, self.loop)
        self.socket_mock.recvfrom.return_value = (
            b'[208,[2,4,0,0,"","DUMMYGUID",1631545189,0,[""]]]\0',
            ('mocked', 12345))
        await asyncio.wait([future], timeout=0.1)
        notifications.close()
        device_alert_cb.assert_called_once_with(
            G90DeviceAlert(type=2, event_id=4, resv2=0, resv3=0,
                           zone_name='', device_id='DUMMYGUID',
                           unix_time=1631545189, resv4=0, other=['']))

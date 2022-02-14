import sys
import asyncio
from unittest.mock import MagicMock
import asynctest
from .fixtures import G90Fixture
sys.path.extend(['src', '../src'])
from pyg90alarm.device_notifications import (   # noqa:E402
    G90DeviceNotifications,
)


class TestG90Notifications(G90Fixture):
    async def test_device_notification_missing_header(self):
        def sock_data_awaitable(*args):
            future.set_result(True)
            return b'[170]\0', ('mocked', 12345)

        future = self.loop.create_future()
        notifications = G90DeviceNotifications(sock=self.socket_mock)
        await notifications.listen()
        self.socket_mock.recvfrom.side_effect = sock_data_awaitable
        asynctest.set_read_ready(self.socket_mock, self.loop)
        with self.assertLogs(level='ERROR') as cm:
            await asyncio.wait([future], timeout=0.1)
            self.assertIn(
                cm.output[0], [
                    'ERROR:pyg90alarm.device_notifications:Device message'
                    " '[170]' is malformed: <lambda>() missing 1 required"
                    " positional argument: 'data'",
                    'ERROR:pyg90alarm.device_notifications:Device message'
                    " '[170]' is malformed: __new__() missing 1 required"
                    " positional argument: 'data'",
                ]
            )
        notifications.close()

    async def test_device_notification_malformed_message(self):
        def sock_data_awaitable(*args):
            future.set_result(True)
            return b'[170,[1,[1]]\0', ('mocked', 12345)

        future = self.loop.create_future()
        notifications = G90DeviceNotifications(sock=self.socket_mock)
        await notifications.listen()
        self.socket_mock.recvfrom.side_effect = sock_data_awaitable
        asynctest.set_read_ready(self.socket_mock, self.loop)
        with self.assertLogs(level='ERROR') as cm:
            await asyncio.wait([future], timeout=0.1)
            self.assertIn(
                'ERROR:pyg90alarm.device_notifications:'
                "Unable to parse device message '[170,[1,[1]]' as JSON:",
                cm.output[0]
            )
        notifications.close()

    async def test_device_notification_missing_end_marker(self):
        def sock_data_awaitable(*args):
            future.set_result(True)
            return b'[170,[1,[1]]]', ('mocked', 12345)

        future = self.loop.create_future()
        notifications = G90DeviceNotifications(sock=self.socket_mock)
        await notifications.listen()
        self.socket_mock.recvfrom.side_effect = sock_data_awaitable
        asynctest.set_read_ready(self.socket_mock, self.loop)
        with self.assertLogs(level='ERROR') as cm:
            await asyncio.wait([future], timeout=0.1)
            self.assertEqual(
                cm.output[0],
                'ERROR:pyg90alarm.device_notifications:'
                'Missing end marker in data'
            )
        notifications.close()

    async def test_wrong_device_notification_format(self):
        def sock_data_awaitable(*args):
            future.set_result(True)
            return b'[170,[1]]\0', ('mocked', 12345)

        future = self.loop.create_future()
        notifications = G90DeviceNotifications(sock=self.socket_mock)
        await notifications.listen()
        self.socket_mock.recvfrom.side_effect = sock_data_awaitable
        asynctest.set_read_ready(self.socket_mock, self.loop)
        with self.assertLogs(level='ERROR') as cm:
            await asyncio.wait([future], timeout=0.1)
            self.assertIn(cm.output[0], [
                'ERROR:pyg90alarm.device_notifications:'
                'Bad notification received from mocked:12345:'
                " <lambda>() missing 1 required positional argument: 'data'",
                'ERROR:pyg90alarm.device_notifications:'
                'Bad notification received from mocked:12345:'
                " __new__() missing 1 required positional argument: 'data'",
            ])
        notifications.close()

    async def test_wrong_device_alert_format(self):
        def sock_data_awaitable(*args):
            future.set_result(True)
            return (b'[208,[]]\0', ('mocked', 12345))
        future = self.loop.create_future()
        notifications = G90DeviceNotifications(sock=self.socket_mock)
        await notifications.listen()
        self.socket_mock.recvfrom.side_effect = sock_data_awaitable
        asynctest.set_read_ready(self.socket_mock, self.loop)
        with self.assertLogs(level='ERROR') as cm:
            await asyncio.wait([future], timeout=0.1)
            self.assertIn(cm.output[0], [
                'ERROR:pyg90alarm.device_notifications:'
                'Bad alert received from mocked:12345:'
                " <lambda>() missing 9 required positional arguments: 'type',"
                " 'event_id', 'resv2', 'resv3', 'zone_name', 'device_id',"
                " 'unix_time', 'resv4', and 'other'",
                'ERROR:pyg90alarm.device_notifications:'
                'Bad alert received from mocked:12345:'
                " __new__() missing 9 required positional arguments: 'type',"
                " 'event_id', 'resv2', 'resv3', 'zone_name', 'device_id',"
                " 'unix_time', 'resv4', and 'other'",
            ])
        notifications.close()

    async def test_unknown_device_notification(self):
        def sock_data_awaitable(*args):
            future.set_result(True)
            return b'[170,[999,[1]]]\0', ('mocked', 12345)

        future = self.loop.create_future()
        notifications = G90DeviceNotifications(sock=self.socket_mock)
        await notifications.listen()
        self.socket_mock.recvfrom.side_effect = sock_data_awaitable
        asynctest.set_read_ready(self.socket_mock, self.loop)
        with self.assertLogs(level='WARNING') as cm:
            await asyncio.wait([future], timeout=0.1)
            self.assertEqual(cm.output, [
                'WARNING:pyg90alarm.device_notifications:'
                'Unknown notification received from mocked:12345: kind 999,'
                ' data [1]'
            ])
        notifications.close()

    async def test_unknown_device_alert(self):
        def sock_data_awaitable(*args):
            future.set_result(True)
            return (b'[208,[999,100,1,1,"Hall","DUMMYGUID",'
                    b'1631545189,0,[""]]]\0', ('mocked', 12345))
        future = self.loop.create_future()
        notifications = G90DeviceNotifications(sock=self.socket_mock)
        await notifications.listen()
        self.socket_mock.recvfrom.side_effect = sock_data_awaitable
        asynctest.set_read_ready(self.socket_mock, self.loop)
        with self.assertLogs(level='WARNING') as cm:
            await asyncio.wait([future], timeout=0.1)
            self.assertEqual(cm.output, [
                'WARNING:pyg90alarm.device_notifications:'
                'Unknown alert received from mocked:12345: type 999,'
                ' data G90DeviceAlert(type=999, event_id=100, resv2=1,'
                " resv3=1, zone_name='Hall', device_id='DUMMYGUID',"
                " unix_time=1631545189, resv4=0, other=[''])"
            ])
        notifications.close()

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

    async def test_armdisarm_notification_callback(self):
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

    async def test_armdisarm_alert_callback(self):
        future = self.loop.create_future()
        armdisarm_cb = MagicMock()
        armdisarm_cb.side_effect = lambda *args: future.set_result(True)
        notifications = G90DeviceNotifications(
            armdisarm_cb=armdisarm_cb, sock=self.socket_mock)
        await notifications.listen()
        asynctest.set_read_ready(self.socket_mock, self.loop)
        self.socket_mock.recvfrom.return_value = (
            b'[208,[2,4,0,0,"","DUMMYGUID",1630876128,0,[""]]]\0',
            ('mocked', 12345))
        await asyncio.wait([future], timeout=0.1)
        notifications.close()
        armdisarm_cb.assert_called_once_with(1)

    async def test_door_open_close_callback(self):
        future = self.loop.create_future()
        door_open_close_cb = MagicMock()
        door_open_close_cb.side_effect = lambda *args: future.set_result(True)
        notifications = G90DeviceNotifications(
            door_open_close_cb=door_open_close_cb, sock=self.socket_mock)
        await notifications.listen()
        asynctest.set_read_ready(self.socket_mock, self.loop)
        self.socket_mock.recvfrom.return_value = (
            b'[208,[4,100,1,1,"Hall","DUMMYGUID",1631545189,0,[""]]]\0',
            ('mocked', 12345))
        await asyncio.wait([future], timeout=0.1)
        notifications.close()
        door_open_close_cb.assert_called_once_with(100, 'Hall', True)

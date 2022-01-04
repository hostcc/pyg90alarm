import asyncio
import socket
import sys
from unittest.mock import MagicMock
import asynctest
from .fixtures import G90Fixture
sys.path.extend(['src', '../src'])
from pyg90alarm import (   # noqa:E402
    G90Alarm,
)
from pyg90alarm.host_info import (   # noqa:E402
    G90HostInfo,
)
from pyg90alarm.entities.sensor import (   # noqa:E402
    G90Sensor,
)
from pyg90alarm.entities.device import (   # noqa:E402
    G90Device,
)
from pyg90alarm.history import (   # noqa:E402
    G90History,
)
from pyg90alarm.host_status import (   # noqa:E402
    G90HostStatus,
)
from pyg90alarm.user_data_crc import (   # noqa:E402
    G90UserDataCRC,
)
from pyg90alarm.config import G90AlertConfig  # noqa: E402


class TestG90Alarm(G90Fixture):
    async def test_host_status(self):
        g90 = G90Alarm(host='mocked', port=12345, sock=self.socket_mock)
        data = b'ISTART[100,[3,"PHONE","PRODUCT","206","206"]]IEND\0'
        self.socket_mock.recvfrom.return_value = (data, ('mocked', 12345))

        res = await g90.host_status
        self.assert_callargs_on_sent_data([b'ISTART[100,100,""]IEND\0'])
        self.assertIsInstance(res, G90HostStatus)
        self.assertEqual(res.host_status, 3)
        self.assertEqual(res.product_name, 'PRODUCT')
        self.assertEqual(res.host_phone_number, 'PHONE')

    async def test_host_info(self):
        g90 = G90Alarm(host='mocked', port=12345, sock=self.socket_mock)
        data = b'ISTART[206,' \
            b'["DUMMYGUID","DUMMYPRODUCT",' \
            b'"1.2","1.1","206","206",3,3,0,2,"4242",50,100]]IEND\0'
        self.socket_mock.recvfrom.return_value = (data, ('mocked', 12345))

        res = await g90.host_info
        self.assert_callargs_on_sent_data([b'ISTART[206,206,""]IEND\0'])
        self.assertIsInstance(res, G90HostInfo)
        self.assertEqual(res.host_guid, 'DUMMYGUID')
        self.assertEqual(res.product_name, 'DUMMYPRODUCT')

    async def test_user_data_crc(self):
        g90 = G90Alarm(host='mocked', port=12345, sock=self.socket_mock)
        data = b'ISTART[160,["1","0xab","3","4","5","6"]]IEND\0'
        self.socket_mock.recvfrom.return_value = (data, ('mocked', 12345))

        res = await g90.user_data_crc
        self.assert_callargs_on_sent_data([b'ISTART[160,160,""]IEND\0'])
        self.assertIsInstance(res, G90UserDataCRC)
        self.assertEqual(res.sensor_list, '1')
        self.assertEqual(res.device_list, '0xab')
        self.assertEqual(res.history_list, '3')
        self.assertEqual(res.scene_list, '4')
        self.assertEqual(res.ifttt_list, '5')
        self.assertEqual(res.fingerprint_list, '6')

    async def test_devices(self):
        g90 = G90Alarm(host='mocked', port=12345, sock=self.socket_mock)
        data = b'ISTART[138,' \
               b'[[1,1,1],["Switch",10,0,10,1,0,32,0,0,16,1,0,""]]]IEND\0'
        self.socket_mock.recvfrom.return_value = (data, ('mocked', 12345))

        devices = await g90.devices
        self.assert_callargs_on_sent_data([
            b'ISTART[138,138,[138,[1,10]]]IEND\0',
        ])
        self.assertEqual(len(devices), 1)
        self.assertIsInstance(devices, list)
        self.assertIsInstance(devices[0], G90Device)
        self.assertEqual(devices[0].name, 'Switch')
        self.assertEqual(devices[0].index, 10)

    async def test_multinode_device(self):
        g90 = G90Alarm(host='mocked', port=12345, sock=self.socket_mock)
        data = b'ISTART[138,' \
               b'[[1,1,1],["Switch",10,0,10,1,0,32,0,0,16,2,0,""]]]IEND\0'
        self.socket_mock.recvfrom.return_value = (data, ('mocked', 12345))
        devices = await g90.devices
        self.assert_callargs_on_sent_data([
            b'ISTART[138,138,[138,[1,10]]]IEND\0',
        ])
        self.assertEqual(len(devices), 2)
        self.assertIsInstance(devices, list)
        self.assertIsInstance(devices[0], G90Device)
        self.assertEqual(devices[0].name, 'Switch#1')
        self.assertEqual(devices[0].index, 10)
        self.assertEqual(devices[0].subindex, 0)
        self.assertEqual(devices[1].name, 'Switch#2')
        self.assertEqual(devices[1].index, 10)
        self.assertEqual(devices[1].subindex, 1)

    async def test_control_device(self):
        g90 = G90Alarm(host='mocked', port=12345, sock=self.socket_mock)
        data = b'ISTART[138,' \
               b'[[1,1,1],["Switch",10,0,10,1,0,32,0,0,16,1,0,""]]]IEND\0'
        self.socket_mock.recvfrom.return_value = (data, ('mocked', 12345))
        devices = await g90.devices

        data = b'ISTARTIEND\0'
        self.socket_mock.recvfrom.return_value = (data, ('mocked', 12345))
        await devices[0].turn_on()
        await devices[0].turn_off()
        self.assert_callargs_on_sent_data([
            b'ISTART[138,138,[138,[1,10]]]IEND\0',
            b'ISTART[137,137,[137,[10,0,0]]]IEND\0',
            b'ISTART[137,137,[137,[10,1,0]]]IEND\0',
        ])

    async def test_single_sensor(self):
        g90 = G90Alarm(host='mocked', port=12345, sock=self.socket_mock)
        data = b'ISTART[102,' \
               b'[[1,1,1],["Remote",10,0,10,1,0,32,0,0,16,1,0,""]]]IEND\0'
        self.socket_mock.recvfrom.return_value = (data, ('mocked', 12345))

        sensors = await g90.sensors
        self.assert_callargs_on_sent_data([
            b'ISTART[102,102,[102,[1,10]]]IEND\0',
        ])
        self.assertEqual(len(sensors), 1)
        self.assertIsInstance(sensors, list)
        self.assertIsInstance(sensors[0], G90Sensor)
        self.assertEqual(sensors[0].name, 'Remote')
        self.assertEqual(sensors[0].index, 10)

    async def test_multiple_sensors_shorter_than_page(self):
        g90 = G90Alarm(host='mocked', port=12345, sock=self.socket_mock)
        data = [(b'ISTART[102,'
                 b'[[2,1,2],["Remote 1",10,0,10,1,0,32,0,0,16,1,0,""],'
                 b'["Remote 2",11,0,10,1,0,32,0,0,16,1,0,""]]]IEND\0',
                 ('mocked', 12345)),
                ]

        self.socket_mock.recvfrom.side_effect = data

        sensors = await g90.sensors
        self.assert_callargs_on_sent_data([
            b'ISTART[102,102,[102,[1,10]]]IEND\0',
        ])
        self.assertEqual(len(sensors), 2)
        self.assertIsInstance(sensors, list)
        self.assertIsInstance(sensors[0], G90Sensor)
        self.assertEqual(sensors[0].name, 'Remote 1')
        self.assertEqual(sensors[0].index, 10)
        self.assertIsInstance(sensors[1], G90Sensor)
        self.assertEqual(sensors[1].name, 'Remote 2')
        self.assertEqual(sensors[1].index, 11)

    async def test_multiple_sensors_longer_than_page(self):
        g90 = G90Alarm(host='mocked', port=12345, sock=self.socket_mock)
        data = [(b'ISTART[102,'
                 b'[[11,1,10],'
                 b'["Remote 1",10,0,10,1,0,32,0,0,16,1,0,""],'
                 b'["Remote 2",11,0,10,1,0,32,0,0,16,1,0,""],'
                 b'["Remote 3",12,0,10,1,0,32,0,0,16,1,0,""],'
                 b'["Remote 4",13,0,10,1,0,32,0,0,16,1,0,""],'
                 b'["Remote 5",14,0,10,1,0,32,0,0,16,1,0,""],'
                 b'["Remote 6",15,0,10,1,0,32,0,0,16,1,0,""],'
                 b'["Remote 7",16,0,10,1,0,32,0,0,16,1,0,""],'
                 b'["Remote 8",17,0,10,1,0,32,0,0,16,1,0,""],'
                 b'["Remote 9",18,0,10,1,0,32,0,0,16,1,0,""],'
                 b'["Remote 10",19,0,10,1,0,32,0,0,16,1,0,""]'
                 b']]IEND\0',
                 ('mocked', 12345)),
                (b'ISTART[102,'
                 b'[[11,11,1],'
                 b'["Remote 11",20,0,10,1,0,32,0,0,16,1,0,""]'
                 b']]IEND\0',
                 ('mocked', 12345)),
                ]

        self.socket_mock.recvfrom.side_effect = data

        sensors = await g90.sensors
        self.assert_callargs_on_sent_data([
            b'ISTART[102,102,[102,[1,10]]]IEND\0',
            b'ISTART[102,102,[102,[11,11]]]IEND\0',
        ])
        self.assertEqual(len(sensors), 11)
        self.assertIsInstance(sensors, list)
        self.assertIsInstance(sensors[0], G90Sensor)
        self.assertEqual(sensors[0].name, 'Remote 1')
        self.assertEqual(sensors[0].index, 10)

    async def test_sensor_event(self):
        reset_interval = 0.5
        g90 = G90Alarm(host='mocked', port=12345, sock=self.socket_mock,
                       reset_occupancy_interval=reset_interval)
        data = [(b'ISTART[102,'
                 b'[[1,1,1],["Remote",10,0,10,1,0,32,0,0,16,1,0,""]]]IEND\0',
                 ('mocked', 12345)),
                (b'ISTART[117,'
                 b'[256]]IEND\0',
                 ('mocked', 12345)),
                ]
        self.socket_mock.recvfrom.side_effect = data

        sensors = await g90.sensors
        future = self.loop.create_future()
        sensor = [x for x in sensors if x.index == 10 and x.name == 'Remote']
        sensor[0].state_callback = lambda *args: future.set_result(True)

        socket_ntfy_mock = asynctest.SocketMock()
        socket_ntfy_mock.type = socket.SOCK_DGRAM
        await g90.listen_device_notifications(socket_ntfy_mock)
        asynctest.set_read_ready(socket_ntfy_mock, self.loop)
        socket_ntfy_mock.recvfrom.return_value = (
            b'[170,[5,[10,"Remote"]]]\0', ('mocked', 12345))
        await asyncio.wait([future], timeout=0.1)
        g90.close_device_notifications()
        # Once passed this implies the G90Alarm sensor callback works as
        # expected, as it updates the occupancy states of the sensor
        self.assertEqual(sensor[0].occupancy, True)

        # Re-create future since the callback will be invoked again when the
        # occupancy state is reset
        future = self.loop.create_future()
        # Verify the occupancy state is reset upon configured interval
        await asyncio.sleep(reset_interval)
        self.assertEqual(sensor[0].occupancy, False)

    async def test_armdisarm_callback(self):
        future = self.loop.create_future()
        armdisarm_cb = MagicMock()
        armdisarm_cb.side_effect = lambda *args: future.set_result(True)
        g90 = G90Alarm(host='mocked', port=12345, sock=self.socket_mock)
        g90.armdisarm_callback = armdisarm_cb
        socket_ntfy_mock = asynctest.SocketMock()
        socket_ntfy_mock.type = socket.SOCK_DGRAM
        await g90.listen_device_notifications(socket_ntfy_mock)
        asynctest.set_read_ready(socket_ntfy_mock, self.loop)
        socket_ntfy_mock.recvfrom.return_value = (
            b'[170,[1,[1]]]\0', ('mocked', 12345))
        await asyncio.wait([future], timeout=0.1)
        g90.close_device_notifications()
        armdisarm_cb.assert_called_once_with(1)

    async def test_door_open_close_callback(self):
        future = self.loop.create_future()
        door_open_close_cb = MagicMock()
        door_open_close_cb.side_effect = lambda *args: future.set_result(True)
        g90 = G90Alarm(host='mocked', port=12345, sock=self.socket_mock)
        data = [(b'ISTART[102,'
                 b'[[1,1,1],["Door",100,0,1,1,0,32,0,0,16,1,0,""]]]IEND\0',
                 ('mocked', 12345)),
                (b'ISTART[117,'
                 b'[256]]IEND\0',
                 ('mocked', 12345)),
                # The GETNOTICEFLAG command is invoked twice, for each of
                # alerts simulated below
                (b'ISTART[117,'
                 b'[256]]IEND\0',
                 ('mocked', 12345)),
                ]
        self.socket_mock.recvfrom.side_effect = data

        g90.door_open_close_callback = door_open_close_cb
        socket_ntfy_mock = asynctest.SocketMock()
        socket_ntfy_mock.type = socket.SOCK_DGRAM
        await g90.listen_device_notifications(socket_ntfy_mock)
        # Simulate two device alerts - for opening and then closing the door
        socket_ntfy_mock.recvfrom.side_effect = [
            (b'[208,[4,100,1,1,"Door","DUMMYGUID",1631545189,0,[""]]]\0',
             ('mocked', 12345)),
            (b'[208,[4,100,1,0,"Door","DUMMYGUID",1631545189,0,[""]]]\0',
             ('mocked', 12345)),
        ]
        # Signal the first alert is ready
        asynctest.set_read_ready(socket_ntfy_mock, self.loop)
        await asyncio.wait([future], timeout=0.1)
        # Corresponding sensor should turn to occupied (=door opened)
        sensors = await g90.sensors
        self.assertEqual(sensors[0].occupancy, True)

        # Signal the second alert is ready, the future has to be re-created as
        # the corresponding callback will be fired again
        future = self.loop.create_future()
        asynctest.set_read_ready(socket_ntfy_mock, self.loop)
        await asyncio.wait([future], timeout=0.1)
        # The sensor should become inactive (=door closed)
        sensors = await g90.sensors
        self.assertEqual(sensors[0].occupancy, False)

        g90.close_device_notifications()

    async def test_arm_away(self):
        g90 = G90Alarm(host='mocked', port=12345, sock=self.socket_mock)
        self.socket_mock.recvfrom.return_value = (
            b'ISTARTIEND\0', ('mocked', 12345))
        await g90.arm_away()
        self.assert_callargs_on_sent_data([
            b'ISTART[101,101,[101,[1]]]IEND\0'
        ])

    async def test_arm_home(self):
        g90 = G90Alarm(host='mocked', port=12345, sock=self.socket_mock)
        self.socket_mock.recvfrom.return_value = (
            b'ISTARTIEND\0', ('mocked', 12345))
        await g90.arm_home()
        self.assert_callargs_on_sent_data([
            b'ISTART[101,101,[101,[2]]]IEND\0'
        ])

    async def test_disarm(self):
        g90 = G90Alarm(host='mocked', port=12345, sock=self.socket_mock)
        self.socket_mock.recvfrom.return_value = (
            b'ISTARTIEND\0', ('mocked', 12345))
        await g90.disarm()
        self.assert_callargs_on_sent_data([
            b'ISTART[101,101,[101,[3]]]IEND\0'
        ])

    async def test_history(self):
        g90 = G90Alarm(host='mocked', port=12345, sock=self.socket_mock)
        self.socket_mock.recvfrom.return_value = (
            b'ISTART[200,[[50,1,5],'
            b'[3,33,7,254,"Sensor 1",1630147285,""],'
            b'[2,3,0,0,"",1630142877,""],'
            b'[2,5,0,0,"",1630142871,""],'
            b'[2,4,0,0,"",1630142757,""],'
            b'[3,100,126,1,"Sensor 2",1630142297,""]]]IEND\0',
            ('mocked', 12345))
        history = await g90.history(count=5)
        self.assertEqual(len(history), 5)
        self.assertIsInstance(history[0], G90History)
        self.assert_callargs_on_sent_data([
            b'ISTART[200,200,[200,[1,5]]]IEND\0'
        ])

    async def test_alert_config(self):
        """ Tests for retrieving alert configuration from the device """
        g90 = G90Alarm(host='mocked', port=12345, sock=self.socket_mock)
        data = b'ISTART[117,[1]]IEND\0'
        self.socket_mock.recvfrom.return_value = (data, ('mocked', 12345))

        res = await g90.alert_config
        self.assert_callargs_on_sent_data([b'ISTART[117,117,""]IEND\0'])
        self.assertIsInstance(res, G90AlertConfig)

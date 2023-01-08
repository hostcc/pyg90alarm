import asyncio
import socket
import sys
from unittest.mock import MagicMock, call
from helpers import set_read_ready
# import asynctest
sys.path.extend(['src', '../src'])
from pyg90alarm import (   # noqa:E402
    G90Alarm,
)
from pyg90alarm.host_info import (   # noqa:E402
    G90HostInfo, G90HostInfoGsmStatus, G90HostInfoWifiStatus,
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
from pyg90alarm.config import (  # noqa: E402
    G90AlertConfigFlags,
)


async def test_host_status(mock_sock):
    g90 = G90Alarm(host='mocked', port=12345, sock=mock_sock)
    data = b'ISTART[100,[3,"PHONE","PRODUCT","206","206"]]IEND\0'
    mock_sock.recvfrom.return_value = (data, ('mocked', 12345))

    res = await g90.get_host_status()
    mock_sock.send.assert_called_with(b'ISTART[100,100,""]IEND\0')
    assert isinstance(res, G90HostStatus)
    assert res.host_status == 3
    assert res.product_name == 'PRODUCT'
    assert res.host_phone_number == 'PHONE'


async def test_host_info(mock_sock):
    g90 = G90Alarm(host='mocked', port=12345, sock=mock_sock)
    data = b'ISTART[206,' \
        b'["DUMMYGUID","DUMMYPRODUCT",' \
        b'"1.2","1.1","206","206",3,3,0,2,"4242",50,100]]IEND\0'
    mock_sock.recvfrom.return_value = (data, ('mocked', 12345))

    res = await g90.get_host_info()
    mock_sock.send.assert_called_with(b'ISTART[206,206,""]IEND\0')
    assert isinstance(res, G90HostInfo)
    assert res.host_guid == 'DUMMYGUID'
    assert res.product_name == 'DUMMYPRODUCT'
    assert res.gsm_status == G90HostInfoGsmStatus.OPERATIONAL
    assert res.wifi_status == G90HostInfoWifiStatus.OPERATIONAL


async def test_user_data_crc(mock_sock):
    g90 = G90Alarm(host='mocked', port=12345, sock=mock_sock)
    data = b'ISTART[160,["1","0xab","3","4","5","6"]]IEND\0'
    mock_sock.recvfrom.return_value = (data, ('mocked', 12345))

    crc = await g90.get_user_data_crc()
    prop_crc = await g90.user_data_crc
    assert crc == prop_crc

    mock_sock.send.assert_has_calls([
        call(b'ISTART[160,160,""]IEND\0'),
        call(b'ISTART[160,160,""]IEND\0'),
    ])
    assert isinstance(crc, G90UserDataCRC)
    assert crc.sensor_list == '1'
    assert crc.device_list == '0xab'
    assert crc.history_list == '3'
    assert crc.scene_list == '4'
    assert crc.ifttt_list == '5'
    assert crc.fingerprint_list == '6'


async def test_devices(mock_sock):
    g90 = G90Alarm(host='mocked', port=12345, sock=mock_sock)
    data = b'ISTART[138,' \
           b'[[1,1,1],["Switch",10,0,10,1,0,32,0,0,16,1,0,""]]]IEND\0'
    mock_sock.recvfrom.return_value = (data, ('mocked', 12345))

    devices = await g90.get_devices()
    prop_devices = await g90.devices
    assert devices == prop_devices
    mock_sock.send.assert_called_with(
        b'ISTART[138,138,[138,[1,10]]]IEND\0',
    )
    assert len(devices) == 1
    assert isinstance(devices, list)
    assert isinstance(devices[0], G90Device)
    assert devices[0].name == 'Switch'
    assert devices[0].index == 10


async def test_multinode_device(mock_sock):
    g90 = G90Alarm(host='mocked', port=12345, sock=mock_sock)
    data = b'ISTART[138,' \
           b'[[1,1,1],["Switch",10,0,10,1,0,32,0,0,16,2,0,""]]]IEND\0'
    mock_sock.recvfrom.return_value = (data, ('mocked', 12345))
    devices = await g90.get_devices()
    prop_devices = await g90.devices
    assert devices == prop_devices
    mock_sock.send.assert_called_with(
        b'ISTART[138,138,[138,[1,10]]]IEND\0',
    )
    assert len(devices) == 2
    assert isinstance(devices, list)
    assert isinstance(devices[0], G90Device)
    assert devices[0].name == 'Switch#1'
    assert devices[0].index == 10
    assert devices[0].subindex == 0
    assert devices[1].name == 'Switch#2'
    assert devices[1].index == 10
    assert devices[1].subindex == 1


async def test_control_device(mock_sock):
    g90 = G90Alarm(host='mocked', port=12345, sock=mock_sock)
    data = b'ISTART[138,' \
           b'[[1,1,1],["Switch",10,0,10,1,0,32,0,0,16,1,0,""]]]IEND\0'
    mock_sock.recvfrom.return_value = (data, ('mocked', 12345))
    devices = await g90.get_devices()
    prop_devices = await g90.devices
    assert devices == prop_devices

    data = b'ISTARTIEND\0'
    mock_sock.recvfrom.return_value = (data, ('mocked', 12345))
    await devices[0].turn_on()
    await devices[0].turn_off()
    mock_sock.send.assert_has_calls([
        call(b'ISTART[138,138,[138,[1,10]]]IEND\0'),
        call(b'ISTART[137,137,[137,[10,0,0]]]IEND\0'),
        call(b'ISTART[137,137,[137,[10,1,0]]]IEND\0'),
    ])


async def test_single_sensor(mock_sock):
    g90 = G90Alarm(host='mocked', port=12345, sock=mock_sock)
    data = b'ISTART[102,' \
           b'[[1,1,1],["Remote",10,0,10,1,0,32,0,0,16,1,0,""]]]IEND\0'
    mock_sock.recvfrom.return_value = (data, ('mocked', 12345))

    sensors = await g90.get_sensors()
    prop_sensors = await g90.sensors
    assert sensors == prop_sensors
    mock_sock.send.assert_called_with(
        b'ISTART[102,102,[102,[1,10]]]IEND\0',
    )
    assert len(sensors) == 1
    assert isinstance(sensors, list)
    assert isinstance(sensors[0], G90Sensor)
    assert sensors[0].name == 'Remote'
    assert sensors[0].index == 10


async def test_multiple_sensors_shorter_than_page(mock_sock):
    g90 = G90Alarm(host='mocked', port=12345, sock=mock_sock)
    data = [(b'ISTART[102,'
             b'[[2,1,2],["Remote 1",10,0,10,1,0,32,0,0,16,1,0,""],'
             b'["Remote 2",11,0,10,1,0,32,0,0,16,1,0,""]]]IEND\0',
             ('mocked', 12345)),
            ]

    mock_sock.recvfrom.side_effect = data

    sensors = await g90.get_sensors()
    prop_sensors = await g90.sensors
    assert sensors == prop_sensors
    mock_sock.send.assert_called_with(
        b'ISTART[102,102,[102,[1,10]]]IEND\0',
    )
    assert len(sensors) == 2
    assert isinstance(sensors, list)
    assert isinstance(sensors[0], G90Sensor)
    assert sensors[0].name == 'Remote 1'
    assert sensors[0].index == 10
    assert isinstance(sensors[1], G90Sensor)
    assert sensors[1].name == 'Remote 2'
    assert sensors[1].index == 11


async def test_multiple_sensors_longer_than_page(mock_sock):
    g90 = G90Alarm(host='mocked', port=12345, sock=mock_sock)
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

    mock_sock.recvfrom.side_effect = data

    sensors = await g90.get_sensors()
    prop_sensors = await g90.sensors
    assert sensors == prop_sensors
    mock_sock.send.assert_has_calls([
        call(b'ISTART[102,102,[102,[1,10]]]IEND\0'),
        call(b'ISTART[102,102,[102,[11,11]]]IEND\0'),
    ])
    assert len(sensors) == 11
    assert isinstance(sensors, list)
    assert isinstance(sensors[0], G90Sensor)
    assert sensors[0].name == 'Remote 1'
    assert sensors[0].index == 10


async def test_sensor_event(mock_sock):
    reset_interval = 0.5
    g90 = G90Alarm(host='mocked', port=12345, sock=mock_sock,
                   reset_occupancy_interval=reset_interval)
    data = [(b'ISTART[102,'
             b'[[1,1,1],["Remote",10,0,10,1,0,32,0,0,16,1,0,""]]]IEND\0',
             ('mocked', 12345)),
            (b'ISTART[117,'
             b'[256]]IEND\0',
             ('mocked', 12345)),
            ]
    mock_sock.recvfrom.side_effect = data

    sensors = await g90.get_sensors()
    prop_sensors = await g90.sensors
    assert sensors == prop_sensors
    future = asyncio.get_running_loop().create_future()
    sensor = [x for x in sensors if x.index == 10 and x.name == 'Remote']
    sensor[0].state_callback = lambda *args: future.set_result(True)

    socket_ntfy_mock = MagicMock()
    socket_ntfy_mock.type = socket.SOCK_DGRAM
    await g90.listen_device_notifications(socket_ntfy_mock)
    set_read_ready(socket_ntfy_mock)
    socket_ntfy_mock.recvfrom.return_value = (
        b'[170,[5,[10,"Remote"]]]\0', ('mocked', 12345))
    await asyncio.wait([future], timeout=0.1)
    g90.close_device_notifications()
    # Once passed this implies the G90Alarm sensor callback works as
    # expected, as it updates the occupancy states of the sensor
    assert sensor[0].occupancy

    # Re-create future since the callback will be invoked again when the
    # occupancy state is reset
    future = asyncio.get_running_loop().create_future()
    # Verify the occupancy state is reset upon configured interval
    await asyncio.sleep(reset_interval)
    assert not sensor[0].occupancy


async def test_armdisarm_callback(mock_sock):
    future = asyncio.get_running_loop().create_future()
    armdisarm_cb = MagicMock()
    armdisarm_cb.side_effect = lambda *args: future.set_result(True)
    g90 = G90Alarm(host='mocked', port=12345, sock=mock_sock)
    g90.armdisarm_callback = armdisarm_cb
    socket_ntfy_mock = MagicMock()
    socket_ntfy_mock.type = socket.SOCK_DGRAM
    await g90.listen_device_notifications(socket_ntfy_mock)
    set_read_ready(socket_ntfy_mock)
    socket_ntfy_mock.recvfrom.return_value = (
        b'[170,[1,[1]]]\0', ('mocked', 12345))
    await asyncio.wait([future], timeout=0.1)
    g90.close_device_notifications()
    armdisarm_cb.assert_called_once_with(1)


async def test_door_open_close_callback(mock_sock):
    future = asyncio.get_running_loop().create_future()
    door_open_close_cb = MagicMock()
    door_open_close_cb.side_effect = lambda *args: future.set_result(True)
    g90 = G90Alarm(host='mocked', port=12345, sock=mock_sock)
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
    mock_sock.recvfrom.side_effect = data

    g90.door_open_close_callback = door_open_close_cb

    # Simulate two device alerts - for opening (this one) and then closing the
    # door (see below)
    socket_ntfy_mock = MagicMock()
    socket_ntfy_mock.type = socket.SOCK_DGRAM
    await g90.listen_device_notifications(socket_ntfy_mock)
    socket_ntfy_mock.recvfrom.side_effect = [
        (b'[208,[4,100,1,1,"Door","DUMMYGUID",1631545189,0,[""]]]\0',
         ('mocked', 12345)),
    ]
    # Signal the first alert is ready
    set_read_ready(socket_ntfy_mock)

    await asyncio.wait([future], timeout=0.1)
    # Corresponding sensor should turn to occupied (=door opened)
    sensors = await g90.get_sensors()
    prop_sensors = await g90.sensors
    assert sensors == prop_sensors
    assert sensors[0].occupancy
    g90.close_device_notifications()

    # Simulate second device alert for door close
    socket_ntfy_mock = MagicMock()
    socket_ntfy_mock.type = socket.SOCK_DGRAM
    await g90.listen_device_notifications(socket_ntfy_mock)
    socket_ntfy_mock.recvfrom.side_effect = [
        (b'[208,[4,100,1,0,"Door","DUMMYGUID",1631545189,0,[""]]]\0',
         ('mocked', 12345)),
    ]
    # Signal the second alert is ready, the future has to be re-created as
    # the corresponding callback will be fired again
    future = asyncio.get_running_loop().create_future()
    set_read_ready(socket_ntfy_mock)

    await asyncio.wait([future], timeout=0.1)
    # The sensor should become inactive (=door closed)
    sensors = await g90.get_sensors()
    prop_sensors = await g90.sensors
    assert sensors == prop_sensors
    assert not sensors[0].occupancy

    g90.close_device_notifications()


async def test_alarm_callback(mock_sock):
    future = asyncio.get_running_loop().create_future()
    alarm_cb = MagicMock()
    alarm_cb.side_effect = lambda *args: future.set_result(True)
    g90 = G90Alarm(host='mocked', port=12345, sock=mock_sock)
    # Simulate panel with two sensors
    data = [(b'ISTART[102,'
             b'[[2,1,2],'
             b'["Hall",100,0,1,1,0,32,0,0,16,1,0,""],'
             b'["Room",101,0,1,1,0,32,0,0,16,1,0,""]'
             b']]IEND\0',
             ('mocked', 12345)),
            ]
    mock_sock.recvfrom.side_effect = data
    sensors = await g90.get_sensors()
    # Set extra data for the 1st sensor
    sensors[0].extra_data = 'Dummy extra data'

    g90.alarm_callback = alarm_cb
    socket_ntfy_mock = MagicMock()
    socket_ntfy_mock.type = socket.SOCK_DGRAM
    await g90.listen_device_notifications(socket_ntfy_mock)
    # Simulate three alarm notifications - for sensor with extra data,
    # another for sensor with no extra data, and third for non-existent
    # sensor
    socket_ntfy_mock.recvfrom.side_effect = [
        (b'[208,[3,100,1,1,"Hall","DUMMYGUID",1630876128,0,[""]]]\0',
         ('mocked', 12345)),
        (b'[208,[3,101,1,1,"Room","DUMMYGUID",1630876128,0,[""]]]\0',
         ('mocked', 12345)),
        (b'[208,[3,102,1,1,"No Room","DUMMYGUID",1630876128,0,[""]]]\0',
         ('mocked', 12345)),
    ]

    # Simulate alarm for sensor with extra data
    set_read_ready(socket_ntfy_mock)
    await asyncio.wait([future], timeout=0.1)
    # Verify extra data is passed to the callback
    alarm_cb.assert_called_once_with(100, 'Hall', 'Dummy extra data')

    # Simulate alarm for sensor with no extra data
    alarm_cb.reset_mock()
    future = asyncio.get_running_loop().create_future()
    set_read_ready(socket_ntfy_mock)
    await asyncio.wait([future], timeout=0.1)
    # Verify no extra data is passed to the callback
    alarm_cb.assert_called_once_with(101, 'Room', None)

    # Simulate alarm for non-existent sensor
    alarm_cb.reset_mock()
    future = asyncio.get_running_loop().create_future()
    set_read_ready(socket_ntfy_mock)
    await asyncio.wait([future], timeout=0.1)
    # Simulate callback is called with no data
    alarm_cb.assert_called_once_with(102, 'No Room', None)

    g90.close_device_notifications()


async def test_arm_away(mock_sock):
    g90 = G90Alarm(host='mocked', port=12345, sock=mock_sock)
    mock_sock.recvfrom.return_value = (
        b'ISTARTIEND\0', ('mocked', 12345))
    await g90.arm_away()
    mock_sock.send.assert_called_with(
        b'ISTART[101,101,[101,[1]]]IEND\0'
    )


async def test_arm_home(mock_sock):
    g90 = G90Alarm(host='mocked', port=12345, sock=mock_sock)
    mock_sock.recvfrom.return_value = (
        b'ISTARTIEND\0', ('mocked', 12345))
    await g90.arm_home()
    mock_sock.send.assert_called_with(
        b'ISTART[101,101,[101,[2]]]IEND\0'
    )


async def test_disarm(mock_sock):
    g90 = G90Alarm(host='mocked', port=12345, sock=mock_sock)
    mock_sock.recvfrom.return_value = (
        b'ISTARTIEND\0', ('mocked', 12345))
    await g90.disarm()
    mock_sock.send.assert_called_with(
        b'ISTART[101,101,[101,[3]]]IEND\0'
    )


async def test_history(mock_sock):
    g90 = G90Alarm(host='mocked', port=12345, sock=mock_sock)
    mock_sock.recvfrom.return_value = (
        b'ISTART[200,[[50,1,5],'
        b'[3,33,7,254,"Sensor 1",1630147285,""],'
        b'[2,3,0,0,"",1630142877,""],'
        b'[2,5,0,0,"",1630142871,""],'
        b'[2,4,0,0,"",1630142757,""],'
        b'[3,100,126,1,"Sensor 2",1630142297,""]]]IEND\0',
        ('mocked', 12345))
    history = await g90.history(count=5)
    assert len(history) == 5
    assert isinstance(history[0], G90History)
    mock_sock.send.assert_called_with(
        b'ISTART[200,200,[200,[1,5]]]IEND\0'
    )


async def test_alert_config(mock_sock):
    """ Tests for retrieving alert configuration from the device """
    g90 = G90Alarm(host='mocked', port=12345, sock=mock_sock)
    data = b'ISTART[117,[1]]IEND\0'
    mock_sock.recvfrom.return_value = (data, ('mocked', 12345))

    config = await g90.get_alert_config()
    prop_config = await g90.alert_config
    assert config == prop_config
    mock_sock.send.assert_called_with(b'ISTART[117,117,""]IEND\0')
    assert isinstance(config, G90AlertConfigFlags)


async def test_set_alert_config(mock_sock):
    """ Tests for setting alert configuration to the the device """
    g90 = G90Alarm(host="mocked", port=12345, sock=mock_sock)
    mock_sock.recvfrom.side_effect = [
        (b"ISTART[117,[1]]IEND\0", ("mocked", 12345)),
        (b"ISTART[117,[3]]IEND\0", ("mocked", 12345)),
        (b"ISTARTIEND\0", ("mocked", 12345)),
    ]

    await g90.set_alert_config(
        await g90.get_alert_config()
        | G90AlertConfigFlags.AC_POWER_FAILURE  # noqa:W503
        | G90AlertConfigFlags.HOST_LOW_VOLTAGE  # noqa:W503
    )
    mock_sock.send.assert_has_calls([
        call(b'ISTART[117,117,""]IEND\0'),
        call(b'ISTART[117,117,""]IEND\0'),
        call(b"ISTART[116,116,[116,[9]]]IEND\0"),
    ])
    # Validate we retrieve same alert configuration just has been set
    assert await g90.get_alert_config() == (
        G90AlertConfigFlags.AC_POWER_FAILURE
        | G90AlertConfigFlags.HOST_LOW_VOLTAGE  # noqa:W503
    )


async def test_sms_alert_when_armed(mock_sock):
    """ Tests for enabling SMS alerts when device is armed """
    future = asyncio.get_running_loop().create_future()
    armdisarm_cb = MagicMock()
    armdisarm_cb.side_effect = lambda *args: future.set_result(True)
    g90 = G90Alarm(host='mocked', port=12345, sock=mock_sock)
    g90.armdisarm_callback = armdisarm_cb
    g90.sms_alert_when_armed = True
    socket_ntfy_mock = MagicMock()
    socket_ntfy_mock.type = socket.SOCK_DGRAM
    await g90.listen_device_notifications(socket_ntfy_mock)
    set_read_ready(socket_ntfy_mock)
    mock_sock.recvfrom.side_effect = [
        # First command to get alert configuration is from
        # `G90Alarm.get_alert_config()` property
        (b"ISTART[117,[1]]IEND\0", ("mocked", 12345)),
        # Second command for same is invoked by `G90Alarm.set_alert_config`
        # that checks if alert config has been modified externally
        (b"ISTART[117,[1]]IEND\0", ("mocked", 12345)),
        (b"ISTARTIEND\0", ("mocked", 12345)),
    ]
    socket_ntfy_mock.recvfrom.side_effect = [
        (b'[170,[1,[1]]]\0', ('mocked', 12345)),
    ]
    await asyncio.wait([future], timeout=0.1)
    g90.close_device_notifications()
    mock_sock.send.assert_has_calls([
        call(b'ISTART[117,117,""]IEND\0'),
        call(b'ISTART[117,117,""]IEND\0'),
        call(b"ISTART[116,116,[116,[513]]]IEND\0"),
    ])


async def test_sms_alert_when_disarmed(mock_sock):
    """ Tests for disabling SMS alerts when device is disarmed """
    future = asyncio.get_running_loop().create_future()
    armdisarm_cb = MagicMock()
    armdisarm_cb.side_effect = lambda *args: future.set_result(True)
    g90 = G90Alarm(host='mocked', port=12345, sock=mock_sock)
    g90.armdisarm_callback = armdisarm_cb
    g90.sms_alert_when_armed = True
    socket_ntfy_mock = MagicMock()
    socket_ntfy_mock.type = socket.SOCK_DGRAM
    await g90.listen_device_notifications(socket_ntfy_mock)
    set_read_ready(socket_ntfy_mock)
    mock_sock.recvfrom.side_effect = [
        # See above for the clarification on command sequence
        (b"ISTART[117,[513]]IEND\0", ("mocked", 12345)),
        (b"ISTART[117,[513]]IEND\0", ("mocked", 12345)),
        (b"ISTARTIEND\0", ("mocked", 12345)),
    ]
    socket_ntfy_mock.recvfrom.side_effect = [
        (b'[170,[1,[3]]]\0', ('mocked', 12345)),
    ]
    await asyncio.wait([future], timeout=0.1)
    g90.close_device_notifications()
    mock_sock.send.assert_has_calls([
        call(b'ISTART[117,117,""]IEND\0'),
        call(b'ISTART[117,117,""]IEND\0'),
        call(b"ISTART[116,116,[116,[1]]]IEND\0"),
    ])


async def test_sensor_disable(mock_sock):
    g90 = G90Alarm(host='mocked', port=12345, sock=mock_sock)
    mock_sock.recvfrom.side_effect = [
        (
            b'ISTART[102,'
            b'[[2,1,2],'
            b'["Night Light1",11,0,138,0,0,33,0,0,17,1,0,""],'
            b'["Night Light2",10,0,138,0,0,33,0,0,17,1,0,""]'
            b']]IEND\0',
            ('mocked', 12345)
        ),
        (
            b'ISTART[102,'
            b'[[2,2,1],'
            b'["Night Light2",10,0,138,0,0,33,0,0,17,1,0,""]'
            b']]IEND\0',
            ('mocked', 12345)
        ),
        (b"ISTARTIEND\0", ("mocked", 12345)),
    ]

    sensors = await g90.get_sensors()
    prop_sensors = await g90.sensors
    assert sensors == prop_sensors
    assert sensors[1].enabled
    await sensors[1].set_enabled(False)
    assert not sensors[1].enabled
    mock_sock.send.assert_has_calls([
        call(b'ISTART[102,102,[102,[1,10]]]IEND\0'),
        call(b'ISTART[102,102,[102,[2,2]]]IEND\0'),
        call(
            b'ISTART[103,103,[103,'
            b'["Night Light2",10,0,138,0,0,32,0,0,17,1,0,2,"060A0600"]'
            b']]IEND\0'
        ),
    ])


async def test_sensor_disable_externally_modified(mock_sock):
    g90 = G90Alarm(host='mocked', port=12345, sock=mock_sock)
    mock_sock.recvfrom.side_effect = [
        (
            b'ISTART[102,'
            b'[[2,1,2],'
            b'["Night Light1",11,0,138,0,0,33,0,0,17,1,0,""],'
            b'["Night Light2",10,0,138,0,0,33,0,0,17,1,0,""]'
            b']]IEND\0',
            ('mocked', 12345)
        ),
        (
            b'ISTART[102,'
            b'[[2,2,1],'
            b'["Night Light2",10,0,138,0,0,1,0,0,17,1,0,""]'
            b']]IEND\0',
            ('mocked', 12345)
        ),
        (b"ISTARTIEND\0", ("mocked", 12345)),
    ]

    sensors = await g90.get_sensors()
    prop_sensors = await g90.sensors
    assert sensors == prop_sensors
    assert sensors[1].enabled
    await sensors[1].set_enabled(False)
    assert sensors[1].enabled
    mock_sock.send.assert_has_calls([
        call(b'ISTART[102,102,[102,[1,10]]]IEND\0'),
        call(b'ISTART[102,102,[102,[2,2]]]IEND\0'),
    ])


async def test_sensor_unsupported_disable(mock_sock):
    g90 = G90Alarm(host='mocked', port=12345, sock=mock_sock)
    mock_sock.recvfrom.side_effect = [
        (
            b'ISTART[102,'
            b'[[1,1,1],["Water",10,0,7,0,0,33,0,0,17,1,0,""]'
            b']]IEND\0',
            ('mocked', 12345)
        ),
        (b"ISTARTIEND\0", ("mocked", 12345)),
    ]

    sensors = await g90.get_sensors()
    prop_sensors = await g90.sensors
    assert sensors == prop_sensors
    assert sensors[0].enabled
    await sensors[0].set_enabled(False)
    mock_sock.send.assert_called_with(
        b'ISTART[102,102,[102,[1,10]]]IEND\0',
    )


async def test_sensor_disable_sensor_not_found_on_refresh(mock_sock):
    g90 = G90Alarm(host='mocked', port=12345, sock=mock_sock)
    mock_sock.recvfrom.side_effect = [
        (
            b'ISTART[102,'
            b'[[2,1,2],'
            b'["Night Light1",11,0,138,0,0,33,0,0,17,1,0,""],'
            b'["Night Light2",10,0,138,0,0,33,0,0,17,1,0,""]'
            b']]IEND\0',
            ('mocked', 12345)
        ),
        (
            b'ISTART[102,[[2,2,0]]]IEND\0',
            ('mocked', 12345)
        ),
    ]

    sensors = await g90.get_sensors()
    assert sensors[1].enabled
    await sensors[1].set_enabled(False)
    assert sensors[1].enabled
    mock_sock.send.assert_has_calls([
        call(b'ISTART[102,102,[102,[1,10]]]IEND\0'),
        call(b'ISTART[102,102,[102,[2,2]]]IEND\0'),
    ])


async def test_device_unsupported_disable(mock_sock):
    g90 = G90Alarm(host='mocked', port=12345, sock=mock_sock)
    mock_sock.recvfrom.side_effect = [
        (
            b'ISTART[138,'
            b'[[1,1,1],["Water",10,0,7,0,0,33,0,0,17,1,0,""]'
            b']]IEND\0',
            ('mocked', 12345)
        ),
        (b"ISTARTIEND\0", ("mocked", 12345)),
    ]

    devices = await g90.get_devices()
    prop_devices = await g90.devices
    assert devices == prop_devices
    assert devices[0].enabled
    await devices[0].set_enabled(False)
    mock_sock.send.assert_called_with(
        b'ISTART[138,138,[138,[1,10]]]IEND\0',
    )

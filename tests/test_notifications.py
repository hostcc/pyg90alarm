import sys
import asyncio
import re
from unittest.mock import MagicMock
import pytest

sys.path.extend(['src', '../src'])
from pyg90alarm.device_notifications import (   # noqa:E402
    G90DeviceNotifications,
)


@pytest.mark.g90device(notification_data=[
    b'[170]\0',
])
async def test_device_notification_missing_header(mock_device, caplog):
    notifications = G90DeviceNotifications(
        host=mock_device.notification_host, port=mock_device.notification_port
    )
    caplog.set_level('ERROR')
    await notifications.listen()
    await mock_device.send_next_notification()
    assert re.match(
        r"Device message '\[170\]' is malformed: .+ missing 1 required"
        " positional argument: 'data'",
        ''.join(caplog.messages)
    )
    notifications.close()


@pytest.mark.g90device(notification_data=[
    b'[170,[1,[1]]\0',
])
async def test_device_notification_malformed_message(mock_device, caplog):
    notifications = G90DeviceNotifications(
        host=mock_device.notification_host, port=mock_device.notification_port
    )
    caplog.set_level('ERROR')
    await notifications.listen()
    await mock_device.send_next_notification()
    assert (
        "Unable to parse device message '[170,[1,[1]]' as JSON:"
        in ''.join(caplog.messages)
    )
    notifications.close()


@pytest.mark.g90device(notification_data=[
    b'[170,[1,[1]]]',
])
async def test_device_notification_missing_end_marker(caplog, mock_device):
    notifications = G90DeviceNotifications(
        host=mock_device.notification_host, port=mock_device.notification_port
    )
    caplog.set_level('ERROR')
    await notifications.listen()
    await mock_device.send_next_notification()
    assert ''.join(caplog.messages) == 'Missing end marker in data'
    notifications.close()


@pytest.mark.g90device(notification_data=[
    b'[170,[1]]\0',
])
async def test_wrong_device_notification_format(mock_device, caplog):
    notifications = G90DeviceNotifications(
        host=mock_device.notification_host, port=mock_device.notification_port
    )
    caplog.set_level('ERROR')
    await notifications.listen()
    await mock_device.send_next_notification()
    assert re.match(
        rf'Bad notification received from {mock_device.host}:\d+:'
        " .+ missing 1 required positional argument: 'data'",
        ''.join(caplog.messages)
    )
    notifications.close()


@pytest.mark.g90device(notification_data=[
    b'[208,[]]\0',
])
async def test_wrong_device_alert_format(mock_device, caplog):
    notifications = G90DeviceNotifications(
        host=mock_device.notification_host, port=mock_device.notification_port
    )

    caplog.set_level('ERROR')
    await notifications.listen()
    await mock_device.send_next_notification()
    assert re.match(
        rf'Bad alert received from {mock_device.host}:\d+:'
        " .+ missing 9 required positional arguments: 'type',"
        " 'event_id', 'source', 'state', 'zone_name', 'device_id',"
        " 'unix_time', 'resv4', and 'other'",
        ''.join(caplog.messages)
    )
    notifications.close()


@pytest.mark.g90device(notification_data=[
    b'[170,[999,[1]]]\0',
])
async def test_unknown_device_notification(mock_device, caplog):
    notifications = G90DeviceNotifications(
        host=mock_device.notification_host, port=mock_device.notification_port
    )
    caplog.set_level('WARNING')
    await notifications.listen()
    await mock_device.send_next_notification()
    assert re.match(
        rf'Unknown notification received from {mock_device.host}:\d+:'
        r' kind 999, data \[1\]',
        ''.join(caplog.messages)
    )
    notifications.close()


@pytest.mark.g90device(notification_data=[
    b'[208,[999,100,1,1,"Hall","DUMMYGUID",'
    b'1631545189,0,[""]]]\0',
])
async def test_unknown_device_alert(mock_device, caplog):
    notifications = G90DeviceNotifications(
        host=mock_device.notification_host, port=mock_device.notification_port
    )
    caplog.set_level('WARNING')
    await notifications.listen()
    await mock_device.send_next_notification()
    assert re.match(
        rf'Unknown alert received from {mock_device.host}:\d+: type 999,'
        r' data G90DeviceAlert\(type=999, event_id=100, source=1,'
        r" state=1, zone_name='Hall', device_id='DUMMYGUID',"
        r" unix_time=1631545189, resv4=0, other=\[''\]\)",
        ''.join(caplog.messages)
    )
    notifications.close()


@pytest.mark.g90device(notification_data=[
    b'[170,[5,[100,"Hall"]]]\0',
])
async def test_sensor_callback(mock_device):
    future = asyncio.get_running_loop().create_future()
    sensor_cb = MagicMock()
    sensor_cb.side_effect = lambda *args: future.set_result(True)
    notifications = G90DeviceNotifications(
        host=mock_device.notification_host, port=mock_device.notification_port,
        sensor_cb=sensor_cb
    )
    await notifications.listen()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    notifications.close()
    sensor_cb.assert_called_once_with(100, 'Hall')


@pytest.mark.g90device(notification_data=[
    b'[170,[1,[1]]]\0',
])
async def test_armdisarm_notification_callback(mock_device):
    future = asyncio.get_running_loop().create_future()
    armdisarm_cb = MagicMock()
    armdisarm_cb.side_effect = lambda *args: future.set_result(True)
    notifications = G90DeviceNotifications(
        host=mock_device.notification_host, port=mock_device.notification_port,
        armdisarm_cb=armdisarm_cb
    )
    await notifications.listen()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    notifications.close()
    armdisarm_cb.assert_called_once_with(1)


@pytest.mark.g90device(notification_data=[
    b'[208,[2,4,0,0,"","DUMMYGUID",1630876128,0,[""]]]\0',
])
async def test_armdisarm_alert_callback(mock_device):
    future = asyncio.get_running_loop().create_future()
    armdisarm_cb = MagicMock()
    armdisarm_cb.side_effect = lambda *args: future.set_result(True)
    notifications = G90DeviceNotifications(
        host=mock_device.notification_host, port=mock_device.notification_port,
        armdisarm_cb=armdisarm_cb
    )
    await notifications.listen()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    notifications.close()
    armdisarm_cb.assert_called_once_with(1)


@pytest.mark.g90device(notification_data=[
    b'[208,[4,100,1,1,"Hall","DUMMYGUID",1631545189,0,[""]]]\0',
])
async def test_door_open_close_callback(mock_device):
    future = asyncio.get_running_loop().create_future()
    door_open_close_cb = MagicMock()
    door_open_close_cb.side_effect = lambda *args: future.set_result(True)
    notifications = G90DeviceNotifications(
        host=mock_device.notification_host, port=mock_device.notification_port,
        door_open_close_cb=door_open_close_cb
    )
    await notifications.listen()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    notifications.close()
    door_open_close_cb.assert_called_once_with(100, 'Hall', True)


@pytest.mark.g90device(notification_data=[
    b'[208,[4,111,12,0,"Doorbell","DUMMYGUID",1655745021,0,[""]]]\0',
])
async def test_doorbell_callback(mock_device):
    future = asyncio.get_running_loop().create_future()
    door_open_close_cb = MagicMock()
    door_open_close_cb.side_effect = lambda *args: future.set_result(True)
    notifications = G90DeviceNotifications(
        host=mock_device.notification_host, port=mock_device.notification_port,
        door_open_close_cb=door_open_close_cb
    )
    await notifications.listen()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    notifications.close()
    door_open_close_cb.assert_called_once_with(111, 'Doorbell', True)


@pytest.mark.g90device(notification_data=[
    b'[208,[3,11,1,1,"Hall","DUMMYGUID",1630876128,0,[""]]]\0',
])
async def test_alarm_callback(mock_device):
    future = asyncio.get_running_loop().create_future()
    alarm_cb = MagicMock()
    alarm_cb.side_effect = lambda *args: future.set_result(True)
    notifications = G90DeviceNotifications(
        host=mock_device.notification_host, port=mock_device.notification_port,
        alarm_cb=alarm_cb
    )
    await notifications.listen()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    notifications.close()
    alarm_cb.assert_called_once_with(11, 'Hall')

import sys
import asyncio
import re
from unittest.mock import MagicMock
from helpers import set_read_ready
sys.path.extend(['src', '../src'])
from pyg90alarm.device_notifications import (   # noqa:E402
    G90DeviceNotifications,
)


async def test_device_notification_missing_header(mock_sock, caplog):
    def sock_data_awaitable(*args):
        future.set_result(True)
        return b'[170]\0', ('mocked', 12345)

    future = asyncio.get_running_loop().create_future()
    notifications = G90DeviceNotifications(sock=mock_sock)
    await notifications.listen()
    mock_sock.recvfrom.side_effect = sock_data_awaitable
    set_read_ready(mock_sock)
    caplog.set_level('ERROR')
    await asyncio.wait([future], timeout=0.1)
    assert re.match(
        r"Device message '\[170\]' is malformed: .+ missing 1 required"
        " positional argument: 'data'",
        ''.join(caplog.messages)
    )
    notifications.close()


async def test_device_notification_malformed_message(mock_sock, caplog):
    def sock_data_awaitable(*args):
        future.set_result(True)
        return b'[170,[1,[1]]\0', ('mocked', 12345)

    future = asyncio.get_running_loop().create_future()
    notifications = G90DeviceNotifications(sock=mock_sock)
    await notifications.listen()
    mock_sock.recvfrom.side_effect = sock_data_awaitable
    set_read_ready(mock_sock)
    caplog.set_level('ERROR')
    await asyncio.wait([future], timeout=0.1)
    assert (
        "Unable to parse device message '[170,[1,[1]]' as JSON:"
        in ''.join(caplog.messages)
    )
    notifications.close()


async def test_device_notification_missing_end_marker(mock_sock, caplog):
    def sock_data_awaitable(*args):
        future.set_result(True)
        return b'[170,[1,[1]]]', ('mocked', 12345)

    future = asyncio.get_running_loop().create_future()
    notifications = G90DeviceNotifications(sock=mock_sock)
    await notifications.listen()
    mock_sock.recvfrom.side_effect = sock_data_awaitable
    set_read_ready(mock_sock)
    caplog.set_level('ERROR')
    await asyncio.wait([future], timeout=0.1)
    assert ''.join(caplog.messages) == 'Missing end marker in data'
    notifications.close()


async def test_wrong_device_notification_format(mock_sock, caplog):
    def sock_data_awaitable(*args):
        future.set_result(True)
        return b'[170,[1]]\0', ('mocked', 12345)

    future = asyncio.get_running_loop().create_future()
    notifications = G90DeviceNotifications(sock=mock_sock)
    await notifications.listen()
    mock_sock.recvfrom.side_effect = sock_data_awaitable
    set_read_ready(mock_sock)
    caplog.set_level('ERROR')
    await asyncio.wait([future], timeout=0.1)
    assert re.match(
        'Bad notification received from mocked:12345:'
        " .+ missing 1 required positional argument: 'data'",
        ''.join(caplog.messages)
    )
    notifications.close()


async def test_wrong_device_alert_format(mock_sock, caplog):
    def sock_data_awaitable(*args):
        future.set_result(True)
        return (b'[208,[]]\0', ('mocked', 12345))
    future = asyncio.get_running_loop().create_future()
    notifications = G90DeviceNotifications(sock=mock_sock)
    await notifications.listen()
    mock_sock.recvfrom.side_effect = sock_data_awaitable
    set_read_ready(mock_sock)
    caplog.set_level('ERROR')
    await asyncio.wait([future], timeout=0.1)
    assert re.match(
        'Bad alert received from mocked:12345:'
        " .+ missing 9 required positional arguments: 'type',"
        " 'event_id', 'source', 'state', 'zone_name', 'device_id',"
        " 'unix_time', 'resv4', and 'other'",
        ''.join(caplog.messages)
    )
    notifications.close()


async def test_unknown_device_notification(mock_sock, caplog):
    def sock_data_awaitable(*args):
        future.set_result(True)
        return b'[170,[999,[1]]]\0', ('mocked', 12345)

    future = asyncio.get_running_loop().create_future()
    notifications = G90DeviceNotifications(sock=mock_sock)
    await notifications.listen()
    mock_sock.recvfrom.side_effect = sock_data_awaitable
    set_read_ready(mock_sock)
    caplog.set_level('WARNING')
    await asyncio.wait([future], timeout=0.1)
    assert ''.join(caplog.messages) == (
        'Unknown notification received from mocked:12345: kind 999,'
        ' data [1]'
    )
    notifications.close()


async def test_unknown_device_alert(mock_sock, caplog):
    def sock_data_awaitable(*args):
        future.set_result(True)
        return (b'[208,[999,100,1,1,"Hall","DUMMYGUID",'
                b'1631545189,0,[""]]]\0', ('mocked', 12345))
    future = asyncio.get_running_loop().create_future()
    notifications = G90DeviceNotifications(sock=mock_sock)
    await notifications.listen()
    mock_sock.recvfrom.side_effect = sock_data_awaitable
    set_read_ready(mock_sock)
    caplog.set_level('WARNING')
    await asyncio.wait([future], timeout=0.1)
    assert ''.join(caplog.messages) == (
        'Unknown alert received from mocked:12345: type 999,'
        ' data G90DeviceAlert(type=999, event_id=100, source=1,'
        " state=1, zone_name='Hall', device_id='DUMMYGUID',"
        " unix_time=1631545189, resv4=0, other=[''])"
    )
    notifications.close()


async def test_sensor_callback(mock_sock):
    future = asyncio.get_running_loop().create_future()
    sensor_cb = MagicMock()
    sensor_cb.side_effect = lambda *args: future.set_result(True)
    notifications = G90DeviceNotifications(
        sensor_cb=sensor_cb, sock=mock_sock)
    await notifications.listen()
    set_read_ready(mock_sock)
    mock_sock.recvfrom.return_value = (
        b'[170,[5,[100,"Hall"]]]\0', ('mocked', 12345))
    await asyncio.wait([future], timeout=0.1)
    notifications.close()
    sensor_cb.assert_called_once_with(100, 'Hall')


async def test_armdisarm_notification_callback(mock_sock):
    future = asyncio.get_running_loop().create_future()
    armdisarm_cb = MagicMock()
    armdisarm_cb.side_effect = lambda *args: future.set_result(True)
    notifications = G90DeviceNotifications(
        armdisarm_cb=armdisarm_cb, sock=mock_sock)
    await notifications.listen()
    set_read_ready(mock_sock)
    mock_sock.recvfrom.return_value = (
        b'[170,[1,[1]]]\0', ('mocked', 12345))
    await asyncio.wait([future], timeout=0.1)
    notifications.close()
    armdisarm_cb.assert_called_once_with(1)


async def test_armdisarm_alert_callback(mock_sock):
    future = asyncio.get_running_loop().create_future()
    armdisarm_cb = MagicMock()
    armdisarm_cb.side_effect = lambda *args: future.set_result(True)
    notifications = G90DeviceNotifications(
        armdisarm_cb=armdisarm_cb, sock=mock_sock)
    await notifications.listen()
    set_read_ready(mock_sock)
    mock_sock.recvfrom.return_value = (
        b'[208,[2,4,0,0,"","DUMMYGUID",1630876128,0,[""]]]\0',
        ('mocked', 12345))
    await asyncio.wait([future], timeout=0.1)
    notifications.close()
    armdisarm_cb.assert_called_once_with(1)


async def test_door_open_close_callback(mock_sock):
    future = asyncio.get_running_loop().create_future()
    door_open_close_cb = MagicMock()
    door_open_close_cb.side_effect = lambda *args: future.set_result(True)
    notifications = G90DeviceNotifications(
        door_open_close_cb=door_open_close_cb, sock=mock_sock)
    await notifications.listen()
    set_read_ready(mock_sock)
    mock_sock.recvfrom.return_value = (
        b'[208,[4,100,1,1,"Hall","DUMMYGUID",1631545189,0,[""]]]\0',
        ('mocked', 12345))
    await asyncio.wait([future], timeout=0.1)
    notifications.close()
    door_open_close_cb.assert_called_once_with(100, 'Hall', True)


async def test_doorbell_callback(mock_sock):
    future = asyncio.get_running_loop().create_future()
    door_open_close_cb = MagicMock()
    door_open_close_cb.side_effect = lambda *args: future.set_result(True)
    notifications = G90DeviceNotifications(
        door_open_close_cb=door_open_close_cb, sock=mock_sock)
    await notifications.listen()
    set_read_ready(mock_sock)
    mock_sock.recvfrom.return_value = (
        b'[208,[4,111,12,0,"Doorbell","DUMMYGUID",1655745021,0,[""]]]\0',
        ('mocked', 12345))
    await asyncio.wait([future], timeout=0.1)
    notifications.close()
    door_open_close_cb.assert_called_once_with(111, 'Doorbell', True)


async def test_alarm_callback(mock_sock):
    future = asyncio.get_running_loop().create_future()
    alarm_cb = MagicMock()
    alarm_cb.side_effect = lambda *args: future.set_result(True)
    notifications = G90DeviceNotifications(
        alarm_cb=alarm_cb, sock=mock_sock)
    await notifications.listen()
    set_read_ready(mock_sock)
    mock_sock.recvfrom.return_value = (
        b'[208,[3,11,1,1,"Hall","DUMMYGUID",1630876128,0,[""]]]\0',
        ('mocked', 12345))
    await asyncio.wait([future], timeout=0.1)
    notifications.close()
    alarm_cb.assert_called_once_with(11, 'Hall')

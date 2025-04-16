"""
Tests for G90DeviceNotifications class
"""
import asyncio
import re
from unittest.mock import MagicMock
import pytest
from pytest import LogCaptureFixture

from pyg90alarm.local.notifications import (
    G90LocalNotifications,
)
from pyg90alarm.alarm import G90Alarm
from pyg90alarm.notifications.protocol import G90NotificationProtocol

from .device_mock import DeviceMock
from .conftest import data_receive_awaitable


@pytest.mark.g90device(notification_data=[
    b'\xdeadbeef\0',
])
async def test_device_notification_invalid_utf_data(
    mock_device: DeviceMock, caplog: LogCaptureFixture
) -> None:
    """
    Verifies that wrong UTF encoded data in device notification is handled
    correctly.
    """
    notifications = G90LocalNotifications(
        protocol_factory=lambda: MagicMock(spec=G90NotificationProtocol),
        host=mock_device.host,
        port=mock_device.port,
        local_host=mock_device.notification_host,
        local_port=mock_device.notification_port
    )
    future = data_receive_awaitable(notifications)

    caplog.set_level('ERROR')
    await notifications.listen()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()

    assert ''.join(caplog.messages) == (
        "Unable to decode device message from UTF-8"
    )


@pytest.mark.g90device(notification_data=[
    b'[170]\0',
])
async def test_device_notification_missing_header(
    mock_device: DeviceMock, caplog: LogCaptureFixture
) -> None:
    """
    Verifies that missing header in device notification is handled correctly.
    """
    notifications = G90LocalNotifications(
        protocol_factory=lambda: MagicMock(spec=G90NotificationProtocol),
        host=mock_device.host,
        port=mock_device.port,
        local_host=mock_device.notification_host,
        local_port=mock_device.notification_port
    )
    future = data_receive_awaitable(notifications)

    caplog.set_level('ERROR')
    await notifications.listen()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()

    assert re.match(
        r"Device message '\[170\]' is malformed: .+ missing 1 required"
        " positional argument: 'data'",
        ''.join(caplog.messages)
    )


@pytest.mark.g90device(notification_data=[
    b'[170,[1,[1]]\0',
])
async def test_device_notification_malformed_message(
    mock_device: DeviceMock,
    caplog: LogCaptureFixture
) -> None:
    """
    Verifies that malformed message in device notification is handled
    correctly.
    """
    notifications = G90LocalNotifications(
        protocol_factory=lambda: MagicMock(spec=G90NotificationProtocol),
        host=mock_device.host,
        port=mock_device.port,
        local_host=mock_device.notification_host,
        local_port=mock_device.notification_port
    )
    future = data_receive_awaitable(notifications)

    caplog.set_level('ERROR')
    await notifications.listen()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()

    assert (
        "Unable to parse device message '[170,[1,[1]]' as JSON:"
        in ''.join(caplog.messages)
    )


@pytest.mark.g90device(notification_data=[
    b'[170,[1,[1]]]',
])
async def test_device_notification_missing_end_marker(
    mock_device: DeviceMock, caplog: LogCaptureFixture
) -> None:
    """
    Verifies that missing end marker in device notification is handled
    correctly.
    """
    notifications = G90LocalNotifications(
        protocol_factory=lambda: MagicMock(spec=G90NotificationProtocol),
        host=mock_device.host,
        port=mock_device.port,
        local_host=mock_device.notification_host,
        local_port=mock_device.notification_port
    )
    future = data_receive_awaitable(notifications)

    caplog.set_level('ERROR')
    await notifications.listen()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()

    assert ''.join(caplog.messages) == 'Missing end marker in data'


@pytest.mark.g90device(notification_data=[
    b'[170,[1]]\0',
])
async def test_wrong_device_notification_format(
    mock_device: DeviceMock, caplog: LogCaptureFixture
) -> None:
    """
    Verifies that wrong device notification format is handled correctly.
    """
    notifications = G90LocalNotifications(
        protocol_factory=lambda: MagicMock(spec=G90NotificationProtocol),
        host=mock_device.host,
        port=mock_device.port,
        local_host=mock_device.notification_host,
        local_port=mock_device.notification_port
    )
    future = data_receive_awaitable(notifications)

    caplog.set_level('ERROR')
    await notifications.listen()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()

    assert re.match(
        'Bad notification received:'
        " .+ missing 1 required positional argument: 'data'",
        ''.join(caplog.messages)
    )


@pytest.mark.g90device(notification_data=[
    b'[208,[]]\0',
])
async def test_wrong_device_alert_format(
    mock_device: DeviceMock, caplog: LogCaptureFixture
) -> None:
    """
    Verifies that wrong device alert format is handled correctly.
    """
    notifications = G90LocalNotifications(
        protocol_factory=lambda: MagicMock(spec=G90NotificationProtocol),
        host=mock_device.host,
        port=mock_device.port,
        local_host=mock_device.notification_host,
        local_port=mock_device.notification_port
    )
    future = data_receive_awaitable(notifications)

    caplog.set_level('ERROR')
    await notifications.listen()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()

    assert re.match(
        'Bad alert received:'
        " .+ missing 9 required positional arguments: 'type',"
        " 'event_id', 'source', 'state', 'zone_name', 'device_id',"
        " 'unix_time', 'resv4', and 'other'",
        ''.join(caplog.messages)
    )


@pytest.mark.g90device(notification_data=[
    b'[170,[999,[1]]]\0',
])
async def test_unknown_device_notification(
    mock_device: DeviceMock, caplog: LogCaptureFixture
) -> None:
    """
    Verifies that unknown device notification is handled correctly.
    """
    notifications = G90LocalNotifications(
        protocol_factory=lambda: MagicMock(spec=G90NotificationProtocol),
        host=mock_device.host,
        port=mock_device.port,
        local_host=mock_device.notification_host,
        local_port=mock_device.notification_port
    )
    future = data_receive_awaitable(notifications)

    caplog.set_level('WARNING')
    await notifications.listen()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()

    assert re.match(
        'Unknown notification received:'
        r' kind 999, data \[1\]',
        ''.join(caplog.messages)
    )


@pytest.mark.g90device(notification_data=[
    b'[208,[999,100,1,1,"Hall","DUMMYGUID",'
    b'1631545189,0,[""]]]\0',
])
async def test_unknown_device_alert(
    mock_device: DeviceMock, caplog: LogCaptureFixture
) -> None:
    """
    Verifies that unknown device alert is handled correctly.
    """
    notifications = G90LocalNotifications(
        protocol_factory=lambda: MagicMock(spec=G90NotificationProtocol),
        host=mock_device.host,
        port=mock_device.port,
        local_host=mock_device.notification_host,
        local_port=mock_device.notification_port
    )
    future = data_receive_awaitable(notifications)

    caplog.set_level('WARNING')
    await notifications.listen()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()

    assert re.match(
        'Unknown alert received: type 999,'
        r' data G90DeviceAlert\(type=999, event_id=100, source=1,'
        r" state=1, zone_name='Hall', device_id='DUMMYGUID',"
        r" unix_time=1631545189, resv4=0, other=\[''\]\)",
        ''.join(caplog.messages)
    )


@pytest.mark.g90device(notification_data=[
    b'[208,[999,100,1,1,"Hall","DUMMYGUID",'
    b'1631545189,0,[""]]]\0',
])
async def test_wrong_host(
    mock_device: DeviceMock, caplog: LogCaptureFixture
) -> None:
    """
    Verifies that unknown device alert is handled correctly.
    """
    notifications = G90LocalNotifications(
        protocol_factory=lambda: MagicMock(spec=G90NotificationProtocol),
        host='1.2.3.4',
        port=mock_device.port,
        local_host=mock_device.notification_host,
        local_port=mock_device.notification_port
    )
    future = data_receive_awaitable(notifications)

    notifications.handle_alert = (  # type: ignore[method-assign]
        MagicMock()
    )
    notifications.handle_notification = (  # type: ignore[method-assign]
        MagicMock()
    )

    caplog.set_level('WARNING')
    await notifications.listen()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()

    assert ''.join(caplog.messages) == (
        "Received notification/alert from wrong host '127.0.0.1'"
        ", expected from '1.2.3.4'"
    )
    notifications.handle_alert.assert_not_called()
    notifications.handle_notification.assert_not_called()


@pytest.mark.g90device(
    sent_data=[
        b'ISTART[206,'
        b'["","DUMMYPRODUCT",'
        b'"1.2","1.1","206","206",3,3,0,2,"4242",50,100]]IEND\0',
    ],
)
async def test_empty_device_guid(mock_device: DeviceMock) -> None:
    """
    Verifies that alert from device with empty GUID is ignored.
    """
    g90 = G90Alarm(
        host=mock_device.host, port=mock_device.port
    )
    await g90.use_local_notifications(
        notifications_local_host=mock_device.notification_host,
        notifications_local_port=mock_device.notification_port
    )
    # The command will fetch the host info and store the GIUD
    await g90.get_host_info()
    await g90.close_notifications()
    # pylint: disable=protected-access
    assert g90._notifications is not None
    assert g90._notifications.device_id is None


@pytest.mark.g90device(notification_data=[
    b'[208,[2,4,0,0,"","DIFFERENTGUID",1630876128,0,[""]]]\0'
])
async def test_wrong_device_guid(
    mock_device: DeviceMock, caplog: LogCaptureFixture
) -> None:
    """
    Verifies that alert from device with different GUID is ignored.
    """
    mock = MagicMock(spec=G90NotificationProtocol)
    notifications = G90LocalNotifications(
        protocol_factory=lambda: mock,
        host=mock_device.host, port=mock_device.port,
        local_host=mock_device.notification_host,
        local_port=mock_device.notification_port
    )
    future = data_receive_awaitable(notifications)

    caplog.set_level('WARNING')
    notifications.device_id = 'DUMMYGUID'
    await notifications.listen()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()

    assert ''.join(caplog.messages) == (
        "Received alert from wrong device: expected 'DUMMYGUID'"
        ", got 'DIFFERENTGUID'"
    )
    # Verify the associated callback was not called
    mock.on_armdisarm.assert_not_called()


@pytest.mark.g90device(notification_data=[
    b'[170,[5,[100,"Hall"]]]\0',
])
async def test_sensor_callback(mock_device: DeviceMock) -> None:
    """
    Verifies that sensor notification callback is handled correctly.
    """
    future = asyncio.get_running_loop().create_future()
    mock = MagicMock(spec=G90NotificationProtocol)
    notifications = G90LocalNotifications(
        protocol_factory=lambda: mock,
        host=mock_device.host, port=mock_device.port,
        local_host=mock_device.notification_host,
        local_port=mock_device.notification_port
    )

    mock.on_sensor_activity.side_effect = (
        lambda *args: future.set_result(True)
    )
    await notifications.listen()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()
    mock.on_sensor_activity.assert_called_once_with(100, 'Hall')
    # Verify last packet from device got tracked
    assert notifications.last_device_packet_time is not None
    # Contrary, the local notification never send anything upstream - verify
    # that
    assert notifications.last_upstream_packet_time is None


@pytest.mark.g90device(notification_data=[
    b'[170,[1,[1]]]\0',
])
async def test_armdisarm_notification_callback(
    mock_device: DeviceMock
) -> None:
    """
    Verifies that arm/disarm notification callback is handled correctly.
    """
    future = asyncio.get_running_loop().create_future()
    mock = MagicMock(spec=G90NotificationProtocol)
    notifications = G90LocalNotifications(
        protocol_factory=lambda: mock,
        host=mock_device.host, port=mock_device.port,
        local_host=mock_device.notification_host,
        local_port=mock_device.notification_port
    )

    mock.on_armdisarm.side_effect = (
        lambda *args: future.set_result(True)
    )
    await notifications.listen()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()
    mock.on_armdisarm.assert_called_once_with(1)


@pytest.mark.g90device(notification_data=[
    b'[208,[2,4,0,0,"","DUMMYGUID",1630876128,0,[""]]]\0',
])
async def test_armdisarm_alert_callback(mock_device: DeviceMock) -> None:
    """
    Verifies that arm/disarm alert callback is handled correctly.
    """
    future = asyncio.get_running_loop().create_future()
    mock = MagicMock(spec=G90NotificationProtocol)
    notifications = G90LocalNotifications(
        protocol_factory=lambda: mock,
        host=mock_device.host, port=mock_device.port,
        local_host=mock_device.notification_host,
        local_port=mock_device.notification_port
    )

    mock.on_armdisarm.side_effect = (
        lambda *args: future.set_result(True)
    )
    await notifications.listen()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()
    mock.on_armdisarm.assert_called_once_with(1)


@pytest.mark.g90device(notification_data=[
    b'[208,[4,100,1,1,"Hall","DUMMYGUID",1631545189,0,[""]]]\0',
])
async def test_door_open_callback(mock_device: DeviceMock) -> None:
    """
    Verifies that door open callback is handled correctly.
    """
    future = asyncio.get_running_loop().create_future()
    mock = MagicMock(spec=G90NotificationProtocol)
    notifications = G90LocalNotifications(
        protocol_factory=lambda: mock,
        host=mock_device.host, port=mock_device.port,
        local_host=mock_device.notification_host,
        local_port=mock_device.notification_port
    )

    mock.on_door_open_close.side_effect = (
        lambda *args: future.set_result(True)
    )
    await notifications.listen()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()
    mock.on_door_open_close.assert_called_once_with(100, 'Hall', True)


@pytest.mark.g90device(notification_data=[
    b'[208,[4,100,1,0,"Hall","DUMMYGUID",1631545189,0,[""]]]\0',
])
async def test_door_close_callback(mock_device: DeviceMock) -> None:
    """
    Verifies that door close callback is handled correctly.
    """
    future = asyncio.get_running_loop().create_future()
    mock = MagicMock(spec=G90NotificationProtocol)
    notifications = G90LocalNotifications(
        protocol_factory=lambda: mock,
        host=mock_device.host, port=mock_device.port,
        local_host=mock_device.notification_host,
        local_port=mock_device.notification_port
    )

    mock.on_door_open_close.side_effect = (
        lambda *args: future.set_result(True)
    )
    await notifications.listen()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()
    mock.on_door_open_close.assert_called_once_with(
        100, 'Hall', False
    )


@pytest.mark.g90device(notification_data=[
    b'[208,[4,111,12,0,"Doorbell","DUMMYGUID",1655745021,0,[""]]]\0',
])
async def test_doorbell_callback(mock_device: DeviceMock) -> None:
    """
    Verifies that doorbell callback is handled correctly.
    """
    future = asyncio.get_running_loop().create_future()
    mock = MagicMock(spec=G90NotificationProtocol)
    notifications = G90LocalNotifications(
        protocol_factory=lambda: mock,
        host=mock_device.host, port=mock_device.port,
        local_host=mock_device.notification_host,
        local_port=mock_device.notification_port
    )

    mock.on_door_open_close.side_effect = (
        lambda *args: future.set_result(True)
    )
    await notifications.listen()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()
    mock.on_door_open_close.assert_called_once_with(
        111, 'Doorbell', True
    )


@pytest.mark.g90device(notification_data=[
    b'[208,[3,11,1,1,"Hall","DUMMYGUID",1630876128,0,[""]]]\0',
])
async def test_alarm_callback(mock_device: DeviceMock) -> None:
    """
    Verifies that alarm callback is handled correctly.
    """
    future = asyncio.get_running_loop().create_future()
    mock = MagicMock(spec=G90NotificationProtocol)
    notifications = G90LocalNotifications(
        protocol_factory=lambda: mock,
        host=mock_device.host, port=mock_device.port,
        local_host=mock_device.notification_host,
        local_port=mock_device.notification_port
    )

    mock.on_alarm.side_effect = (
        lambda *args: future.set_result(True)
    )
    await notifications.listen()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()
    mock.on_alarm.assert_called_once_with(11, 'Hall', False)


@pytest.mark.g90device(notification_data=[
    b'[208,[3,11,1,3,"Hall","DUMMYGUID",1630876128,0,[""]]]\0',
])
async def test_tamper_callback(mock_device: DeviceMock) -> None:
    """
    Verifies that alarm callback is handled correctly when a sensor is
    tampered.
    """
    future = asyncio.get_running_loop().create_future()
    mock = MagicMock(spec=G90NotificationProtocol)
    notifications = G90LocalNotifications(
        protocol_factory=lambda: mock,
        host=mock_device.host, port=mock_device.port,
        local_host=mock_device.notification_host,
        local_port=mock_device.notification_port
    )

    mock.on_alarm.side_effect = (
        lambda *args: future.set_result(True)
    )
    await notifications.listen()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()
    mock.on_alarm.assert_called_once_with(11, 'Hall', True)


@pytest.mark.g90device(notification_data=[
    # Host SOS
    b'[208,[1,1,0,0,"","DUMMYGUID",1734175050,0,[""]]]\0',
    # Remote SOS
    b'[208,[3,1,10,3,"Remote","DUMMYGUID",1734177048,0,[""]]]\0',
])
async def test_sos_callback(mock_device: DeviceMock) -> None:
    """
    Verifies that remote SOS callback is handled correctly.
    """
    future = asyncio.get_running_loop().create_future()
    mock = MagicMock(spec=G90NotificationProtocol)
    notifications = G90LocalNotifications(
        protocol_factory=lambda: mock,
        host=mock_device.host, port=mock_device.port,
        local_host=mock_device.notification_host,
        local_port=mock_device.notification_port
    )

    mock.on_sos.side_effect = (
        lambda *args: future.set_result(True)
    )
    await notifications.listen()

    # Host SOS
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    mock.on_sos.assert_called_with(1, 'Host SOS', True)

    # Remote SOS
    mock.on_sos.reset_mock()
    future = asyncio.get_running_loop().create_future()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    mock.on_sos.assert_called_with(1, 'Remote', False)

    await notifications.close()


@pytest.mark.g90device(notification_data=[
    b'[208,[4,26,1,4,"Hall","DUMMYGUID",1719223959,0,[""]]]\0'
])
async def test_low_battery_callback(mock_device: DeviceMock) -> None:
    """
    Verifies that low battery callback is handled correctly.
    """
    future = asyncio.get_running_loop().create_future()
    mock = MagicMock(spec=G90NotificationProtocol)
    notifications = G90LocalNotifications(
        protocol_factory=lambda: mock,
        host=mock_device.host, port=mock_device.port,
        local_host=mock_device.notification_host,
        local_port=mock_device.notification_port
    )

    mock.on_low_battery.side_effect = (
        lambda *args: future.set_result(True)
    )
    await notifications.listen()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()
    mock.on_low_battery.assert_called_once_with(26, 'Hall')


@pytest.mark.g90device(notification_data=[
    b'[170,[6,[21,"Hall"]]]\0'
])
async def test_door_open_when_arming_callback(mock_device: DeviceMock) -> None:
    """
    Verifies that door open when arming callback is handled correctly.
    """
    future = asyncio.get_running_loop().create_future()
    mock = MagicMock(spec=G90NotificationProtocol)
    notifications = G90LocalNotifications(
        protocol_factory=lambda: mock,
        host=mock_device.host, port=mock_device.port,
        local_host=mock_device.notification_host,
        local_port=mock_device.notification_port
    )

    mock.on_door_open_when_arming.side_effect = (
        lambda *args: future.set_result(True)
    )
    await notifications.listen()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()
    mock.on_door_open_when_arming.assert_called_once_with(21, 'Hall')

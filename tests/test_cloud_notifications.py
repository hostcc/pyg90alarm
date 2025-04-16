"""
Tests for G90CloudNotifications class.
"""
import asyncio
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from struct import pack

import pytest
from freezegun import freeze_time

from pyg90alarm.notifications.protocol import G90NotificationProtocol
from pyg90alarm.cloud import G90CloudNotifications
from pyg90alarm.cloud.protocol import (
    G90CloudMessage
)
from pyg90alarm.cloud.messages import (
    cloud_message
)
from pyg90alarm.cloud.const import G90CloudDirection, G90CloudCommand

from .device_mock import DeviceMock
from .conftest import data_receive_awaitable


@patch('pyg90alarm.cloud.messages.CLOUD_MESSAGE_CLASSES', [])
async def test_cloud_duplicate_message_defintion() -> None:
    """
    Tests that duplicate cloud message definitions raise a ValueError.
    """
    @dataclass
    @cloud_message
    class _TestMessage1(G90CloudMessage):
        _command = G90CloudCommand.HELLO
        _source = G90CloudDirection.DEVICE
        _destination = G90CloudDirection.CLOUD

    with pytest.raises(ValueError):
        @dataclass
        @cloud_message
        class _TestMessage2(G90CloudMessage):
            _command = G90CloudCommand.HELLO
            _source = G90CloudDirection.DEVICE
            _destination = G90CloudDirection.CLOUD


@pytest.mark.g90device(cloud_notification_data=[
    b'\x01\x10\x00\x00\x08',
])
async def test_cloud_short_header(
    mock_device: DeviceMock
) -> None:
    """
    Tests handling of cloud packets with headers that are too short.
    """
    notifications = G90CloudNotifications(
        protocol_factory=lambda: MagicMock(spec=G90NotificationProtocol),
        local_host=mock_device.cloud_host,
        local_port=mock_device.cloud_port
    )
    await notifications.listen()
    await mock_device.send_next_cloud_packet()
    await notifications.close()
    assert await mock_device.cloud_recv_data == []


@pytest.mark.g90device(cloud_notification_data=[
    b'\x01\x10\x00\x00\x09\x00\x00\x00',
])
async def test_cloud_short_packet(
    mock_device: DeviceMock
) -> None:
    """
    Tests handling of cloud packets that are shorter than expected length.
    """
    notifications = G90CloudNotifications(
        protocol_factory=lambda: MagicMock(spec=G90NotificationProtocol),
        local_host=mock_device.cloud_host,
        local_port=mock_device.cloud_port
    )
    future = data_receive_awaitable(notifications)

    await notifications.listen()
    await mock_device.send_next_cloud_packet()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()
    assert await mock_device.cloud_recv_data == []


@pytest.mark.g90device(cloud_notification_data=[
    b'\x01\x10\x00\x00\x08\x00\x00\x00',
])
async def test_cloud_ping(
    mock_device: DeviceMock
) -> None:
    """
    Tests the correct processing and response to cloud ping messages.
    """
    notifications = G90CloudNotifications(
        protocol_factory=lambda: MagicMock(spec=G90NotificationProtocol),
        local_host=mock_device.cloud_host,
        local_port=mock_device.cloud_port
    )
    future = data_receive_awaitable(notifications)

    await notifications.listen()
    await mock_device.send_next_cloud_packet()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()
    assert (
        b'\x01\x10\x00\x00\x08\x00\x00\x00'
    ) == bytes().join(await mock_device.cloud_recv_data)


@pytest.mark.g90device(cloud_notification_data=[
    b'\x01\x10\x00\x20\x48\x00\x00\x00\x01\x00\x00\x00'
    b'\x47\x41\x30\x30\x30\x30\x30\x41\x30\x30\x30\x30'
    b'\x30\x30\x30\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    b'\x02\x00\x00\x00\x00\x70\x00\x00\x32\x30\x37\x00'
    b'\x58\xba\x00\x20\x30\x00\x00\x00\x00\x00\x00\x00'
    b'\b07\x00\x00\x00\x1e\x00\x00\x00\x1e\x00'
])
async def test_cloud_hello(
    mock_device: DeviceMock
) -> None:
    """
    Tests the proper handling and response to cloud hello messages from
    devices.
    """
    notifications = G90CloudNotifications(
        protocol_factory=lambda: MagicMock(spec=G90NotificationProtocol),
        local_host=mock_device.cloud_host,
        local_port=mock_device.cloud_port
    )
    future = data_receive_awaitable(notifications)

    await notifications.listen()
    await mock_device.send_next_cloud_packet()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()
    assert (
        b'\x41\x20\x00\x10\x0d\x00\x00\x00\x01\x00\x01\x00\x01'
        b'\x01\x20\x00\x10\x0d\x00\x00\x00\x01\x00\x02\x00\x1f'
        b'\x63\x20\x00\x10\x10\x00\x00\x00\x01\x00\x03\x00'
        + pack('<i', mock_device.cloud_port)
    ) == bytes().join(await mock_device.cloud_recv_data)
    # Verify the last packet from the device got tracked
    assert notifications.last_device_packet_time is not None


@pytest.mark.g90device(cloud_notification_data=[
    b'\x01\x10\x00\x20\x48\x00\x00\x00\x11\x00\x00\x00'
    b'\x47\x41\x30\x30\x30\x30\x30\x41\x30\x30\x30\x30'
    b'\x30\x30\x30\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    b'\x02\x00\x00\x00\x00\x70\x00\x00\x32\x30\x37\x00'
    b'\x58\xba\x00\x20\x30\x00\x00\x00\x00\x00\x00\x00'
    b'\b07\x00\x00\x00\x1e\x00\x00\x00\x1e\x00'
])
async def test_cloud_hello_wrong_version(
    mock_device: DeviceMock
) -> None:
    """
    Tests rejection of cloud hello messages with an incorrect version number.
    """
    notifications = G90CloudNotifications(
        protocol_factory=lambda: MagicMock(spec=G90NotificationProtocol),
        local_host=mock_device.cloud_host,
        local_port=mock_device.cloud_port
    )
    future = data_receive_awaitable(notifications)

    await notifications.listen()
    await mock_device.send_next_cloud_packet()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()
    assert await mock_device.cloud_recv_data == []


@freeze_time("2025-01-01 00:00:00")
@pytest.mark.g90device(cloud_notification_data=[
    b'\x01\x30\x00\x20\x3c\x00\x00\x00\x01\x00\x00\x00\x47\x41\x30\x30'
    b'\x30\x30\x30\x41\x30\x30\x30\x30\x30\x30\x30\x00\x00\x00\x00\x00'
    b'\x00\x00\x00\x00\x01\x00\x00\x00\x00\x70\x00\x00\x32\x30\x37\x00'
    b'\x05\x05\x05\x05\x30\x00\x06\x06\x07\x07\x07\x07'
])
async def test_cloud_hello_discovery(
    mock_device: DeviceMock
) -> None:
    """
    Tests that devices respond correctly to discovery hello messages from the
    cloud.
    """
    notifications = G90CloudNotifications(
        protocol_factory=lambda: MagicMock(spec=G90NotificationProtocol),
        local_host=mock_device.cloud_host,
        local_port=mock_device.cloud_port
    )
    future = data_receive_awaitable(notifications)

    await notifications.listen()
    await mock_device.send_next_cloud_packet()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()
    assert (
        b'\x01\xd0\x00\x10\x2c\x00\x00\x00\x01\x00\x00\x00\x34\x37\x2e\x38'
        b'\x38\x2e\x37\x2e\x36\x31\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x2e\x16\x00\x00\x80\x85\x74\x67'
    ) == bytes().join(await mock_device.cloud_recv_data)


@pytest.mark.g90device(
    cloud_notification_data=[
        b'\x22\x10\x00\x20\x25\x00\x00\x00\x01\x00\x00\x00\x5b\x31\x37\x30'
        b'\x2c\x5b\x35\x2c\x5b\x31\x30\x31\x2c\x22\x43\x6f\x72\x64\x20\x31'
        b'\x22\x5d\x5d\x5d\x00',
    ],
    sent_data=[
        b'ISTART[102,'
        b'[[1,1,1],["Cord 1",101,0,126,1,0,32,0,5,16,1,0,""]]]IEND\0',
        b'ISTART[117,[256]]IEND\0',
    ]
)
async def test_cloud_notification(
    mock_device: DeviceMock
) -> None:
    """
    Tests handling of cloud notifications about sensor activity.
    """
    mock = MagicMock(spec=G90NotificationProtocol)
    notifications = G90CloudNotifications(
        protocol_factory=lambda: mock,
        local_host=mock_device.cloud_host,
        local_port=mock_device.cloud_port
    )
    future = asyncio.get_running_loop().create_future()
    mock.on_sensor_activity.side_effect = (
        lambda *args: future.set_result(True)
    )
    await notifications.listen()
    await mock_device.send_next_cloud_packet()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()
    assert await mock_device.cloud_recv_data == []
    mock.on_sensor_activity.assert_called_once_with(101, 'Cord 1')


@pytest.mark.g90device(cloud_notification_data=[
    # Hello message, to verify device ID is stored properly
    b'\x01\x10\x00\x20\x48\x00\x00\x00\x01\x00\x00\x00'
    b'\x47\x41\x30\x30\x30\x30\x30\x41\x30\x30\x30\x30'
    b'\x30\x30\x31\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    b'\x02\x00\x00\x00\x00\x70\x00\x00\x32\x30\x37\x00'
    b'\x58\xba\x00\x20\x30\x00\x00\x00\x00\x00\x00\x00'
    b'\b07\x00\x00\x00\x1e\x00\x00\x00\x1e\x00',
    # Disarm message
    b'\x21\x10\x00\x20\x78\x00\x00\x00\x01\x00\x00\x00\x02\x03\x37\x30'
    b'\x2c\x5b\x31\x2c\x5b\x33\x5d\x5d\x5d\x00\x00\x00\x00\x00\x00\x00'
    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    b'\x20\xa2\x94\x67\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    b'\x00\x00\x00\x00\x00\x00\x00\x00'
])
async def test_cloud_status_change_disarm(
    mock_device: DeviceMock
) -> None:
    """
    Tests handling of disarm status changes from the cloud.
    """
    mock = MagicMock(spec=G90NotificationProtocol)
    notifications = G90CloudNotifications(
        protocol_factory=lambda: mock,
        local_host=mock_device.cloud_host,
        local_port=mock_device.cloud_port
    )
    future = asyncio.get_running_loop().create_future()
    mock.on_armdisarm.side_effect = (
        lambda *args: future.set_result(True)
    )
    await notifications.listen()
    await mock_device.send_next_cloud_packet()
    await mock_device.send_next_cloud_packet()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()
    mock.on_armdisarm.assert_called_once_with(3)


@pytest.mark.parametrize("_title,expected_on_alarm_args", [
    pytest.param("tamper", (32, 'Cord 1', True), marks=pytest.mark.g90device(
        cloud_notification_data=[
            # Tamper alarm
            b'\x21\x10\x00\x20\x78\x00\x00\x00\x01\x00\x00\x00\x03\x20\x01\x03'
            b'\x43\x6f\x72\x64\x20\x31\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x0f\xdd\xa9\x67\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00'
        ],
        sent_data=[
            b'ISTART[102,'
            b'[[1,1,1],["Cord 1",32,0,126,1,0,32,0,5,16,1,0,""]]]IEND\0',
            b'ISTART[117,[256]]IEND\0',
        ])
    ),
    pytest.param("gas", (32, 'Cord 1', False), marks=pytest.mark.g90device(
        cloud_notification_data=[
            # Gas sensor alarm
            b'\x21\x10\x00\x20\x78\x00\x00\x00\x01\x00\x00\x00\x03\x20\x03\xfe'
            b'\x43\x6f\x72\x64\x20\x31\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\xd6\x85\xc4\x67\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00'
        ],
        sent_data=[
            b'ISTART[102,'
            b'[[1,1,1],["Cord 1",32,0,126,1,0,32,0,5,16,1,0,""]]]IEND\0',
            b'ISTART[117,[256]]IEND\0',
        ])
    ),
    pytest.param("regular", (32, 'Cord 1', False), marks=pytest.mark.g90device(
        cloud_notification_data=[
            # Regular alarm
            b'\x21\x10\x00\x20\x78\x00\x00\x00\x01\x00\x00\x00\x03\x20\x08\x00'
            b'\x43\x6f\x72\x64\x20\x31\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x08\x28\xa2\x67\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00'
        ],
        sent_data=[
            b'ISTART[102,'
            b'[[1,1,1],["Cord 1",32,0,126,1,0,32,0,5,16,1,0,""]]]IEND\0',
            b'ISTART[117,[256]]IEND\0',
        ])
    ),
])
async def test_cloud_status_change_alarm_sensor(
    _title: str,
    expected_on_alarm_args: tuple[int, str, bool],
    mock_device: DeviceMock
) -> None:
    """
    Tests handling of alarm status changes from sensors.
    """
    mock = MagicMock(spec=G90NotificationProtocol)
    notifications = G90CloudNotifications(
        protocol_factory=lambda: mock,
        local_host=mock_device.cloud_host,
        local_port=mock_device.cloud_port
    )
    future = asyncio.get_running_loop().create_future()
    mock.on_alarm.side_effect = (
        lambda *args: future.set_result(True)
    )
    await notifications.listen()
    await mock_device.send_next_cloud_packet()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()
    assert await mock_device.cloud_recv_data == []
    mock.on_alarm.assert_called_once_with(*expected_on_alarm_args)


@pytest.mark.g90device(
    cloud_notification_data=[
        b'\x21\x10\x00\x20\x78\x00\x00\x00\x01\x00\x00\x00\x04\x20\x01\x01'
        b'\x43\x6f\x72\x64\x20\x31\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\xb1\x30\xa2\x67\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00'
    ],
    sent_data=[
        b'ISTART[102,'
        b'[[1,1,1],["Cord 1",32,0,126,1,0,32,0,5,16,1,0,""]]]IEND\0',
        b'ISTART[117,[256]]IEND\0',
    ]
)
async def test_cloud_status_change_sensor_activity(
    mock_device: DeviceMock
) -> None:
    """
    Tests handling of sensor activity status changes from the cloud.
    """
    mock = MagicMock(spec=G90NotificationProtocol)
    notifications = G90CloudNotifications(
        protocol_factory=lambda: mock,
        local_host=mock_device.cloud_host,
        local_port=mock_device.cloud_port
    )
    future = asyncio.get_running_loop().create_future()
    mock.on_door_open_close.side_effect = (
        lambda *args: future.set_result(True)
    )
    await notifications.listen()
    await mock_device.send_next_cloud_packet()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()
    assert await mock_device.cloud_recv_data == []
    mock.on_door_open_close.assert_called_once_with(32, 'Cord 1', True)


@pytest.mark.g90device(
    cloud_notification_data=[
        b'\x01\x00\x00\x20\x3b\x00\x00\x00\x01\x00\x06\x00\x00\x00\x00\x00'
        b'\x06\x00\x00\x00\x6a\x00\x6a\x00\x5b\x31\x30\x36\x2c\x5b\x39\x30'
        b'\x30\x2c\x30\x2c\x30\x2c\x31\x2c\x32\x2c\x32\x2c\x36\x30\x2c\x32'
        b'\x2c\x30\x2c\x31\x38\x30\x2c\x32\x5d\x5d\x00'
    ]
)
async def test_cloud_command(
    mock_device: DeviceMock
) -> None:
    """
    Tests handling of cloud commands sent to the device.
    """
    notifications = G90CloudNotifications(
        protocol_factory=lambda: MagicMock(spec=G90NotificationProtocol),
        local_host=mock_device.cloud_host,
        local_port=mock_device.cloud_port
    )
    future = data_receive_awaitable(notifications)

    await notifications.listen()
    await mock_device.send_next_cloud_packet()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()

    # Cloud command shouldn't send any response
    assert await mock_device.cloud_recv_data == []


@pytest.mark.parametrize("_title", [
    pytest.param("simple", marks=pytest.mark.g90device(
        cloud_notification_data=[
            b'\x01\x10\x00\x20\x48\x00\x00\x00\x01\x00\x00\x00'
            b'\x47\x41\x30\x30\x30\x30\x30\x41\x30\x30\x30\x30'
            b'\x30\x30\x30\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x02\x00\x00\x00\x00\x70\x00\x00\x32\x30\x37\x00'
            b'\x58\xba\x00\x20\x30\x00\x00\x00\x00\x00\x00\x00'
            b'\b07\x00\x00\x00\x1e\x00\x00\x00\x1e\x00'],
        # The data isn't parsed by the package currently, rather serves as a
        # documented message example for the future changes
        cloud_upstream_data=[
            b'\x29\x50\x00\x10\x17\x00\x00\x00\x01\x00\x06\x00\x02\x00\x64\x00'
            b'\x64\x00\x05\x00\x00\x00\x00',
        ]
    )),
    pytest.param("paginated", marks=pytest.mark.g90device(
        cloud_notification_data=[
            b'\x01\x10\x00\x20\x48\x00\x00\x00\x01\x00\x00\x00'
            b'\x47\x41\x30\x30\x30\x30\x30\x41\x30\x30\x30\x30'
            b'\x30\x30\x30\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x02\x00\x00\x00\x00\x70\x00\x00\x32\x30\x37\x00'
            b'\x58\xba\x00\x20\x30\x00\x00\x00\x00\x00\x00\x00'
            b'\b07\x00\x00\x00\x1e\x00\x00\x00\x1e\x00'],
        # See above
        cloud_upstream_data=[
            b'\x29\x50\x00\x10\x23\x00\x00\x00\x01\x00\x05\x00\x02\x00\xc8\x00'
            b'\xc8\x00\x05\x00\x00\x00\x5b\x32\x30\x30\x2c\x5b\x31\x2c\x31\x30'
            b'\x5d\x5d\x00',
        ]
    )),
])
async def test_upstream_cloud_hello(
    _title: str,
    mock_device: DeviceMock
) -> None:
    """
    Tests handling of upstream cloud commands sent to the device.
    """
    notifications = G90CloudNotifications(
        protocol_factory=lambda: MagicMock(spec=G90NotificationProtocol),
        local_host=mock_device.cloud_host,
        local_port=mock_device.cloud_port,
        upstream_host=mock_device.cloud_upstream_host,
        upstream_port=mock_device.cloud_upstream_port
    )
    future = data_receive_awaitable(notifications)

    await notifications.listen()
    await mock_device.send_next_cloud_packet()
    await asyncio.wait([future], timeout=0.1)
    await notifications.close()

    # Verify the data from the device is sent to the upstream service umodified
    assert await mock_device.cloud_upstream_recv_data == mock_device.cloud_data
    # Verify the data from simulated upstream service is sent back to the
    # device unmodified
    assert await mock_device.cloud_recv_data == mock_device.cloud_upstream_data
    # Verify both device and upstream packet times are set
    assert notifications.last_device_packet_time is not None
    assert notifications.last_upstream_packet_time is not None

"""
Tests for notifications.
"""
from typing import Callable, Coroutine, Any
import asyncio
from unittest.mock import MagicMock, patch

import pytest

from pyg90alarm.notifications.base import G90NotificationsBase
from pyg90alarm.notifications.protocol import G90NotificationProtocol
from pyg90alarm.cloud import G90CloudNotifications
from pyg90alarm.local.notifications import G90LocalNotifications

from .device_mock import DeviceMock
from .conftest import data_receive_awaitable


@pytest.mark.parametrize("notifications_instance,send_device_packet_call", [
    pytest.param(
        lambda mock_device: G90CloudNotifications(
            protocol_factory=lambda: MagicMock(spec=G90NotificationProtocol),
            cloud_ip=mock_device.cloud_ip,
            cloud_port=mock_device.cloud_port,
            local_ip=mock_device.cloud_ip,
            local_port=mock_device.cloud_port
        ),
        lambda mock_device: mock_device.send_next_cloud_packet(),
        marks=pytest.mark.g90device(
            cloud_notification_data=[
                b'\x01\x10\x00\x20\x48\x00\x00\x00\x01\x00\x00\x00'
                b'\x47\x41\x30\x30\x30\x30\x30\x41\x30\x30\x30\x30'
                b'\x30\x30\x30\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                b'\x02\x00\x00\x00\x00\x70\x00\x00\x32\x30\x37\x00'
                b'\x58\xba\x00\x20\x30\x00\x00\x00\x00\x00\x00\x00'
                b'\b07\x00\x00\x00\x1e\x00\x00\x00\x1e\x00'
            ]),
        id="cloud",
    ),
    pytest.param(
        lambda mock_device: G90LocalNotifications(
            protocol_factory=lambda: MagicMock(spec=G90NotificationProtocol),
            host=mock_device.host,
            port=mock_device.port,
            local_ip=mock_device.notification_host,
            local_port=mock_device.notification_port
        ),
        lambda mock_device: mock_device.send_next_notification(),
        marks=pytest.mark.g90device(
            local_notification_data=[
                b'[170,[1]]\0',
            ]),
        id="local",
    )
])
async def test_notifications_close(
    mock_device: DeviceMock,
    notifications_instance: Callable[[DeviceMock], G90NotificationsBase],
    send_device_packet_call: Callable[[DeviceMock], Coroutine[Any, Any, None]]
) -> None:
    """
    Tests that closing the listener calls BaseTransport.close() on the device
    connection.
    """
    notifications = notifications_instance(mock_device)
    future = data_receive_awaitable(notifications)

    await notifications.listen()
    # Simulated device packet is needed to create the transport under test
    await send_device_packet_call(mock_device)
    await asyncio.wait([future], timeout=0.1)

    # Patch the instance of BaseTransport within notification class to capture
    # calls to its `close()` method
    # pylint: disable=protected-access
    assert notifications._transport is not None
    with patch.object(
        notifications._transport,  # pylint: disable=protected-access
        'close',
        # pylint: disable=protected-access
        # Chain to the actual call to ensure the transport is closed and
        # resources aren't leaking during the test
        wraps=notifications._transport.close,
    ) as close_mock:
        await notifications.close()

    # Verify the transport has been closed
    close_mock.assert_called()

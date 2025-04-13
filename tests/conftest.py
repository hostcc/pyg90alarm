# Copyright (c) 2023 Ilia Sotnikov
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
Performs runtime configuration and exposes custom fixtures for Pytest.
"""
from __future__ import annotations
from typing import AsyncIterator, Callable, Any
import asyncio
from unittest.mock import MagicMock, DEFAULT
import pytest
from pyg90alarm.notifications.base import G90NotificationsBase
from .device_mock import DeviceMock


def pytest_configure(config: pytest.Config) -> None:
    """
    Configures `pytest`.
    """
    config.addinivalue_line("markers", "g90device")


@pytest.fixture
async def mock_device(
    request: pytest.FixtureRequest,
    unused_udp_port_factory: Callable[..., int],
    unused_tcp_port_factory: Callable[..., int]
) -> AsyncIterator[DeviceMock]:
    """
    Fixture to instantiate a simulated G90 device allocating random unused
    ports for network exchanges.

    The fixture should be customized with `g90device` mark containing
    `sent_data` and `notification_data` lists of bytes to simulate the messages
    the device sends back to client and notification messages sent to client,
    respectively.
    """
    marker = getattr(
        request.node
        .get_closest_marker('g90device'),
        'kwargs', {}
    )
    data = marker.get('sent_data', [])
    notification_data = marker.get('notification_data', [])
    cloud_notification_data = marker.get('cloud_notification_data', [])
    cloud_upstream_data = marker.get('cloud_upstream_data', [])

    # Allocate unused ports to listen for client requests on, and to send
    # notification messages to, respectively

    # Note the `unised_udp_port_factory` comes from `pytest-asyncio` package
    device_port = unused_udp_port_factory()
    notification_port = unused_udp_port_factory()
    proxy_port = unused_tcp_port_factory()
    upstream_port = unused_tcp_port_factory()
    device = DeviceMock(
        data, notification_data,
        device_port=device_port, notification_port=notification_port,
        cloud_port=proxy_port,
        cloud_notification_data=cloud_notification_data,
        cloud_upstream_port=upstream_port,
        cloud_upstream_data=cloud_upstream_data
    )
    await device.start()
    yield device
    await device.stop()


def data_receive_awaitable(obj: G90NotificationsBase) -> asyncio.Future[bool]:
    """
    Creates an awaitable future that resolves when data is received by
    notification handler.

    This function wraps either the data_received or datagram_received method of
    the provided notification handler object with a mock that will resolve the
    returned future when called.

    :param obj: The notification handler object whose receive method will be
      wrapped
    :return: Future that resolves when data is received
    :raises ValueError: If no suitable method to wrap is found on the object
    """
    method = None
    method_name = None

    if hasattr(obj, 'data_received'):
        method = obj.data_received
        method_name = 'data_received'
    if hasattr(obj, 'datagram_received'):
        method = obj.datagram_received
        method_name = 'datagram_received'
    if not method or not method_name:
        raise ValueError('No method found to wrap')

    future = asyncio.get_running_loop().create_future()

    def wrapper(*_args: Any) -> DEFAULT:
        """
        Wrapper function that sets the future's result when called.

        :param _args: Arguments passed to the original method (unused)
        :return: Return value from unittest.mock.DEFAULT
        """
        future.set_result(True)
        # Signal that the original method should be called
        return DEFAULT

    setattr(obj, method_name, MagicMock(wraps=method, side_effect=wrapper))
    return future

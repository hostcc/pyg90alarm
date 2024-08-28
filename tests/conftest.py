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
from typing import AsyncIterator, Callable
import pytest
from .device_mock import DeviceMock


def pytest_configure(config: pytest.Config) -> None:
    """
    Configures `pytest`.
    """
    config.addinivalue_line("markers", "g90device")


@pytest.fixture
async def mock_device(
    request: pytest.FixtureRequest, unused_udp_port_factory: Callable[..., int]
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

    # Allocate unused ports to listen for client requests on, and to send
    # notification messages to, respectively

    # Note the `unised_udp_port_factory` comes from `pytest-asyncio` package
    device_port = unused_udp_port_factory()
    notification_port = unused_udp_port_factory()
    device = DeviceMock(
        data, notification_data,
        device_port=device_port, notification_port=notification_port
    )
    await device.start()
    yield device
    device.stop()

"""
Tests for the G90AlertConfig class.
"""
from __future__ import annotations
import pytest
from pyg90alarm.alarm import (
    G90Alarm,
)
from pyg90alarm.local.config import (
    G90AlertConfigFlags,
)
from .device_mock import DeviceMock


@pytest.mark.g90device(sent_data=[
    b'ISTART[117,[1]]IEND\0',
])
async def test_alert_config(mock_device: DeviceMock) -> None:
    """
    Tests for retrieving alert configuration from the device.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    config = await g90.alert_config.flags
    assert await mock_device.recv_data == [b'ISTART[117,117,""]IEND\0']
    assert isinstance(config, G90AlertConfigFlags)
    assert G90AlertConfigFlags.AC_POWER_FAILURE in config


@pytest.mark.g90device(sent_data=[
    b"ISTART[117,[1]]IEND\0",
    b"ISTART[117,[3]]IEND\0",
    b"ISTARTIEND\0",
])
async def test_set_alert_config(mock_device: DeviceMock) -> None:
    """
    Tests for setting alert configuration to the the device.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    await g90.alert_config.set_flag(G90AlertConfigFlags.AC_POWER_FAILURE, True)
    await g90.alert_config.set_flag(G90AlertConfigFlags.HOST_LOW_VOLTAGE, True)
    assert await mock_device.recv_data == [
        b'ISTART[117,117,""]IEND\0',
        b'ISTART[117,117,""]IEND\0',
        b"ISTART[116,116,[116,[9]]]IEND\0",
    ]
    # Validate we retrieve same alert configuration just has been set
    assert await g90.alert_config.get_flag(
        G90AlertConfigFlags.AC_POWER_FAILURE) is True
    assert await g90.alert_config.get_flag(
        G90AlertConfigFlags.HOST_LOW_VOLTAGE) is True

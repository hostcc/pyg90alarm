"""
Tests for system commands of G90 alarm panel.
"""
import pytest

from pyg90alarm.local.system_cmd import (
    G90SystemCommand, G90SystemConfigurationCommand
)
from pyg90alarm import G90Alarm
from pyg90alarm.const import G90SystemCommands, G90SystemConfigurationCommands
from .device_mock import DeviceMock


async def test_system_command(mock_device: DeviceMock) -> None:
    """
    Verifies that command has proper wire representation.
    """
    g90 = G90SystemCommand(
        host=mock_device.host, port=mock_device.port,
        code=G90SystemCommands.GSM_REBOOT
    )

    resp = await g90.process()
    assert resp.result == ''
    assert await mock_device.recv_data == [
        b'ISTART[0,100,"AT^IWT=1129,IWT"]IEND\0'
    ]


async def test_system_command_invalid_code(mock_device: DeviceMock) -> None:
    """
    Verifies that set configuration command raises exception.

    The code under test should rather be used with
    `G90SystemConfigurationCommand` class.
    """
    with pytest.raises(ValueError):
        G90SystemCommand(
            host=mock_device.host, port=mock_device.port,
            code=G90SystemCommands.SET_CONFIGURATION
        )


async def test_system_command_configuration_no_data(
    mock_device: DeviceMock
) -> None:
    """
    Verifies that system configuration command without data raises exception.
    """
    with pytest.raises(ValueError):
        G90SystemConfigurationCommand(
            cmd=G90SystemConfigurationCommands.SERVER_ADDRESS,
            host=mock_device.host, port=mock_device.port,
        )


async def test_system_command_mcu_reboot(
    mock_device: DeviceMock
) -> None:
    """
    Verifies that command to reboot MCU is handled properly.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    await g90.mcu_reboot()
    assert await mock_device.recv_data == [
        b'ISTART[0,100,"AT^IWT=1123,IWT"]IEND\0'
    ]


async def test_system_command_gsm_reboot(
    mock_device: DeviceMock
) -> None:
    """
    Verifies that command to reboot GSM is handled properly.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    await g90.gsm_reboot()
    assert await mock_device.recv_data == [
        b'ISTART[0,100,"AT^IWT=1129,IWT"]IEND\0'
    ]


async def test_system_command_wifi_reboot(
    mock_device: DeviceMock
) -> None:
    """
    Verifies that command to reboot WiFi is handled properly.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    await g90.wifi_reboot()
    assert await mock_device.recv_data == [
        b'ISTART[0,100,"AT^IWT=1006,IWT"]IEND\0'
    ]


async def test_system_command_reboot(
    mock_device: DeviceMock
) -> None:
    """
    Verifies that command to reboot the panel is handled properly.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    await g90.reboot()
    assert await mock_device.recv_data == [
        b'ISTART[0,100,"AT^IWT=1129,IWT"]IEND\0',
        b'ISTART[0,100,"AT^IWT=1123,IWT"]IEND\0',
        b'ISTART[0,100,"AT^IWT=1006,IWT"]IEND\0',
    ]


async def test_system_command_set_server_address(
    mock_device: DeviceMock
) -> None:
    """
    Verifies that command to set server address is handled properly.
    """
    g90 = G90Alarm(
        host=mock_device.host, port=mock_device.port,
    )
    await g90.set_cloud_server_address(
        cloud_ip='127.0.0.1', cloud_port=1234
    )

    assert await mock_device.recv_data == [
        b'ISTART[0,100,'
        b'"AT^IWT=1,78=127.0.0.1&127.0.0.1&1234,IWT"'
        b']IEND\0'
    ]

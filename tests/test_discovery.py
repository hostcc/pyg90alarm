"""
Tests for G90Discovery class
"""
import pytest
from pytest import LogCaptureFixture
from pyg90alarm.discovery import (
    G90Discovery,
)
from pyg90alarm.targeted_discovery import (
    G90TargetedDiscovery,
)
from pyg90alarm.const import (
    LOCAL_TARGETED_DISCOVERY_PORT,
)

from .device_mock import DeviceMock


@pytest.mark.g90device(sent_data=[
    b'ISTART[206,["DUMMYGUID1","","","","","",0,0,0,0,"",0,0]]IEND\0',
    b'ISTART[206,["DUMMYGUID2","","","","","",0,0,0,0,"",0,0]]IEND\0',
])
async def test_discovery(mock_device: DeviceMock) -> None:
    """
    Verifies that discovery process can find devices.
    """
    g90 = G90Discovery(host=mock_device.host,
                       port=mock_device.port,
                       timeout=0.1)
    cmd = await g90.process()
    discovered = cmd.devices
    assert discovered[0].guid == 'DUMMYGUID1'
    assert discovered[0].host == mock_device.host
    assert discovered[0].port == mock_device.port
    assert mock_device.recv_data == [b'ISTART[206,206,""]IEND\0']


@pytest.mark.g90device(sent_data=[
    b'IWTAC_PROBE_DEVICE_ACK,TSV018-3SIA'
    b',1.2,1.1,206,1.8,3,3,1,0,2,50,100\0',
])
async def test_targeted_discovery(mock_device: DeviceMock) -> None:
    """
    Verifies that discovery process can find device being targeted directly.
    """
    g90 = G90TargetedDiscovery(
        device_id='DUMMYGUID',
        host=mock_device.host,
        port=mock_device.port,
        local_port=LOCAL_TARGETED_DISCOVERY_PORT,
        timeout=0.1)
    cmd = await g90.process()
    discovered = cmd.devices
    assert discovered[0].guid == 'DUMMYGUID'
    assert discovered[0].host == mock_device.host
    assert discovered[0].port == mock_device.port
    assert mock_device.recv_data == [b'IWTAC_PROBE_DEVICE,DUMMYGUID\0']


@pytest.mark.g90device(sent_data=[
    b'\xdeadbeef'
])
async def test_targeted_discovery_invalid_utf_response(
    mock_device: DeviceMock, caplog: LogCaptureFixture
) -> None:
    """
    Verifies that invalid UTF-8 data in response to targeted discovery is
    logged but ignored.
    """
    g90 = G90TargetedDiscovery(
        device_id='DUMMYGUID',
        host=mock_device.host,
        port=mock_device.port,
        local_port=LOCAL_TARGETED_DISCOVERY_PORT,
        timeout=0.1)

    caplog.set_level('WARNING')
    await g90.process()
    assert ''.join(caplog.messages) == (
        'Got exception, ignoring:'
        ' Unable to decode discovery response from UTF-8'
    )


@pytest.mark.g90device(sent_data=[
    b'IWTAC_PROBE_DEVICE_ACK_BAD,TSV018-3SIA'
    b',1.2,1.1,206,1.8,3,3,1,0,2,50,100\0',
])
async def test_targeted_discovery_wrong_response_start_marker(
    mock_device: DeviceMock, caplog: LogCaptureFixture
) -> None:
    """
    Verifies that wrong start marker in response to targeted discovery is
    logged but ignored.
    """
    g90 = G90TargetedDiscovery(
        device_id='DUMMYGUID',
        host=mock_device.host,
        port=mock_device.port,
        local_port=LOCAL_TARGETED_DISCOVERY_PORT,
        timeout=0.1)

    caplog.set_level('WARNING')
    await g90.process()
    assert ''.join(caplog.messages) == (
        'Got exception, ignoring: Invalid discovery response'
    )


@pytest.mark.g90device(sent_data=[
    b'IWTAC_PROBE_DEVICE_ACK,TSV018-3SIA'
    b',1.2,1.1,206,1.8,3,3,1,0,2,50,100'
])
async def test_targeted_discovery_wrong_response_end_marker(
    mock_device: DeviceMock, caplog: LogCaptureFixture
) -> None:
    """
    Verifies that wrong end marker in response to targeted discovery is logged
    but ignored.
    """
    g90 = G90TargetedDiscovery(
        device_id='DUMMYGUID',
        host=mock_device.host,
        port=mock_device.port,
        local_port=LOCAL_TARGETED_DISCOVERY_PORT,
        timeout=0.1)

    caplog.set_level('WARNING')
    await g90.process()
    assert ''.join(caplog.messages) == (
        'Got exception, ignoring: Invalid discovery response'
    )

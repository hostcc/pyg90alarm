"""
Tests for CID (Contact ID) reporting configuration retrieval and modification.
"""
from __future__ import annotations

import pytest

from pyg90alarm.alarm import G90Alarm
from pyg90alarm.local.cid_config import G90CidConfig
from .device_mock import DeviceMock


@pytest.mark.g90device(
    sent_data=[
        b'ISTART[232,["+1234567890","+0987654321","USER1",1,"000F"]]IEND\0',
        b'ISTART[232,["+1234567890","+0987654321","USER1",1,"000F"]]IEND\0',
        b"ISTARTIEND\0",
    ]
)
async def test_cid_config_load_and_save(mock_device: DeviceMock) -> None:
    """
    Tests for retrieving and modifying CID reporting configuration from
    the device.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    # Retrieve configuration
    cfg = await g90.cid_config()
    assert isinstance(cfg, G90CidConfig)

    # Verify retrieved data
    assert cfg.phone1 == "+1234567890"
    assert cfg.phone2 == "+0987654321"
    assert cfg.user == "USER1"
    assert cfg.enabled is True
    assert cfg.event_flags == "000F"

    # Modify and save the configuration
    cfg.phone1 = "+1111111111"
    cfg.enabled = False
    await cfg.save()

    # Verify data sent to the device; event_flags must be forced to FFFF
    assert await mock_device.recv_data == [
        b'ISTART[232,232,""]IEND\0',
        b'ISTART[232,232,""]IEND\0',
        b'ISTART[233,233,[233,'
        b'["+1111111111","+0987654321","USER1",0,"FFFF"]'
        b"]]IEND\0",
    ]


@pytest.mark.g90device(
    sent_data=[
        b'ISTART[232,["+1234567890","+0987654321","USER1",1,"000F"]]IEND\0',
        b'ISTART[232,["+1111111111","+2222222222","USER2",0,"00FF"]]IEND\0',
    ]
)
async def test_cid_config_cache_and_force_refresh(
    mock_device: DeviceMock
) -> None:
    """
    Verifies CID configuration is load-once cached and can be force-refreshed.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    cfg_first = await g90.cid_config()
    cfg_cached = await g90.cid_config()
    cfg_refreshed = await g90.cid_config(force=True)

    assert cfg_first is cfg_cached
    assert cfg_first.phone1 == "+1234567890"
    assert cfg_refreshed.phone1 == "+1111111111"
    assert await mock_device.recv_data == [
        b'ISTART[232,232,""]IEND\0',
        b'ISTART[232,232,""]IEND\0',
    ]


@pytest.mark.g90device(
    sent_data=[
        b'ISTART[232,["+1234567890","+0987654321","USER1",1,"000F"]]IEND\0',
        b'ISTART[232,["+1234567890","+2222222222","USER1",1,"00FF"]]IEND\0',
        b"ISTARTIEND\0",
    ]
)
async def test_cid_config_save_persists_enabled_property(
    mock_device: DeviceMock
) -> None:
    """
    Private-backed ``enabled`` property must be tracked and persisted in RMW.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    cfg = await g90.cid_config()
    cfg.enabled = False
    await cfg.save()

    assert await mock_device.recv_data == [
        b'ISTART[232,232,""]IEND\0',
        b'ISTART[232,232,""]IEND\0',
        b'ISTART[233,233,[233,'
        b'["+1234567890","+2222222222","USER1",0,"FFFF"]'
        b"]]IEND\0",
    ]

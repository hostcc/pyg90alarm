"""
Tests for SIA reporting configuration retrieval and modification.
"""
from __future__ import annotations

import pytest

from pyg90alarm.alarm import G90Alarm
from pyg90alarm.local.sia_config import G90SiaConfig
from .device_mock import DeviceMock


@pytest.mark.parametrize(
    "expected_heartbeat_interval,expected_recv_data",
    [
        pytest.param(
            60, [
                b'ISTART[230,230,""]IEND\0',
                b'ISTART[230,230,""]IEND\0',
                b"ISTART[231,231,[231,"
                b'["127.0.0.1",12345,"ACCT1","RCVR1","PFX",'
                b'"001122334455667788",0,1,"FFFFFFFF",60]'
                b"]]IEND\0",
            ],
            marks=pytest.mark.g90device(sent_data=[
                b"ISTART[230,"
                b'["127.0.0.1",12345,"ACCT1","RCVR1","PFX",'
                b'"001122334455667788",1,1,"0000FFFF",60]'
                b"]IEND\0",
                b"ISTART[230,"
                b'["127.0.0.1",12345,"ACCT1","RCVR1","PFX",'
                b'"001122334455667788",1,1,"0000FFFF",60]'
                b"]IEND\0",
                b"ISTARTIEND\0",
            ]),
            id="With heartbeat interval",
        ),
        pytest.param(
            None, [
                b'ISTART[230,230,""]IEND\0',
                b'ISTART[230,230,""]IEND\0',
                b"ISTART[231,231,[231,"
                b'["127.0.0.1",12345,"ACCT1","RCVR1","PFX",'
                b'"001122334455667788",0,1,"FFFFFFFF"]'
                b"]]IEND\0",
            ],
            marks=pytest.mark.g90device(sent_data=[
                b"ISTART[230,"
                b'["127.0.0.1",12345,"ACCT1","RCVR1","PFX",'
                b'"001122334455667788",1,1,"0000FFFF"]'
                b"]IEND\0",
                b"ISTART[230,"
                b'["127.0.0.1",12345,"ACCT1","RCVR1","PFX",'
                b'"001122334455667788",1,1,"0000FFFF"]'
                b"]IEND\0",
                b"ISTARTIEND\0",
            ]),
            id="Without heartbeat interval",
        ),
    ],
)
async def test_sia_config_load_and_save(
    expected_heartbeat_interval: int | None,
    expected_recv_data: list[bytes],
    mock_device: DeviceMock,
) -> None:
    """
    Tests for retrieving and modifying SIA reporting configuration from
    the device.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    # Retrieve configuration
    cfg = await g90.sia_config()
    assert isinstance(cfg, G90SiaConfig)

    # Verify retrieved data
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 12345
    assert cfg.account == "ACCT1"
    assert cfg.receiver == "RCVR1"
    assert cfg.prefix == "PFX"
    assert cfg.aes_key == "001122334455667788"
    assert cfg.encryption is True
    assert cfg.enabled is True
    assert cfg.event_flags == "0000FFFF"
    assert cfg.heartbeat_interval == expected_heartbeat_interval

    # Modify and save the configuration
    cfg.encryption = False
    await cfg.save()

    # Serialize() forces event_flags in the outbound SET command payload,
    # but local in-memory state should not be permanently mutated.
    assert cfg.event_flags == "0000FFFF"

    # Verify data sent to the device
    assert await mock_device.recv_data == expected_recv_data


@pytest.mark.g90device(sent_data=[
    b"ISTART[230,"
    b'["127.0.0.1",12345,"ACCT1","RCVR1","PFX",'
    b'"001122334455667788",1,1,"0000FFFF",60]'
    b"]IEND\0",
    b"ISTART[230,"
    b'["127.0.0.2",22345,"ACCT2","RCVR2","PFX2",'
    b'"001122334455667788",0,0,"0000AAAA",120]'
    b"]IEND\0",
])
async def test_sia_config_cache_and_force_refresh(
    mock_device: DeviceMock
) -> None:
    """
    Verifies SIA configuration is load-once cached and can be force-refreshed.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    cfg_first = await g90.sia_config()
    cfg_cached = await g90.sia_config()
    cfg_refreshed = await g90.sia_config(force=True)

    assert cfg_first is cfg_cached
    assert cfg_first.host == "127.0.0.1"
    assert cfg_refreshed.host == "127.0.0.2"
    assert await mock_device.recv_data == [
        b'ISTART[230,230,""]IEND\0',
        b'ISTART[230,230,""]IEND\0',
    ]


@pytest.mark.g90device(sent_data=[
    b"ISTART[230,"
    b'["127.0.0.1",12345,"ACCT1","RCVR1","PFX",'
    b'"001122334455667788",1,1,"0000FFFF",60]'
    b"]IEND\0",
    b"ISTART[230,"
    b'["127.0.0.1",12345,"ACCT1","RCVR1","PFX",'
    b'"001122334455667788",1,1,"11111111",120]'
    b"]IEND\0",
    b"ISTARTIEND\0",
])
async def test_sia_config_save_persists_encryption_property(
    mock_device: DeviceMock,
) -> None:
    """
    Private-backed ``encryption`` property must be tracked and persisted in
    RMW.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    cfg = await g90.sia_config()
    cfg.encryption = False
    await cfg.save()

    assert await mock_device.recv_data == [
        b'ISTART[230,230,""]IEND\0',
        b'ISTART[230,230,""]IEND\0',
        b"ISTART[231,231,[231,"
        b'["127.0.0.1",12345,"ACCT1","RCVR1","PFX",'
        b'"001122334455667788",0,1,"FFFFFFFF",120]'
        b"]]IEND\0",
    ]

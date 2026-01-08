"""
Tests for network configuration retrieval and modification.
"""
import pytest
from pyg90alarm.alarm import (
    G90Alarm,
)
from pyg90alarm.local.net_config import (
    G90NetConfig, G90APNAuth
)
from .device_mock import DeviceMock


@pytest.mark.g90device(sent_data=[
    b'ISTART[212,'
    b'[0,"123456789",1,1,"apn.a.net","user","pwd",3,"54321"]'
    b']IEND\0',
    b'ISTARTIEND\0'
])
async def test_net_config(mock_device: DeviceMock) -> None:
    """
    Tests for retrieving and modifying network configuration from
    the device.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    # Retrieve configuration
    cfg = await g90.net_config()
    assert isinstance(cfg, G90NetConfig)

    # Verify retrieved data
    assert cfg.ap_enabled is False
    assert cfg.ap_password == "123456789"
    assert cfg.wifi_enabled is True
    assert cfg.gprs_enabled is True
    assert cfg.apn_name == "apn.a.net"
    assert cfg.apn_user == "user"
    assert cfg.apn_password == "pwd"
    assert cfg.apn_auth == G90APNAuth.PAP_OR_CHAP
    assert cfg.gsm_operator == '54321'

    # Modify and save the configuration
    cfg.ap_enabled = True
    await cfg.save()

    # Verify data sent to the device
    assert await mock_device.recv_data == [
        b'ISTART[212,212,""]IEND\0',
        b'ISTART[213,213,[213,'
        b'[1,"123456789",1,1,"apn.a.net","user","pwd",3,"54321"]'
        b']]IEND\0'
    ]

"""
Tests for network configuration retrieval and modification.
"""
from __future__ import annotations
from typing import Union, Optional
import pytest
from pyg90alarm.alarm import (
    G90Alarm,
)
from pyg90alarm.local.net_config import (
    G90NetConfig, G90APNAuth
)
from .device_mock import DeviceMock


@pytest.mark.parametrize('is_gsm_operator_expected', [
    pytest.param(
        True, marks=pytest.mark.g90device(sent_data=[
            b'ISTART[212,'
            b'[0,"123456789",1,1,"apn.a.net","user","pwd",3,"54321"]'
            b']IEND\0',
            b'ISTARTIEND\0'
        ]),
        id='Device with cellular module'
    ),
    pytest.param(
        False, marks=pytest.mark.g90device(sent_data=[
            b'ISTART[212,'
            b'[0,"123456789",1,1,"apn.a.net","user","pwd",3]'
            b']IEND\0',
            b'ISTARTIEND\0'
        ]),
        id='Device with no cellular module'
    ),
])
async def test_net_config(
    is_gsm_operator_expected: bool,
    mock_device: DeviceMock
) -> None:
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
    # Verify presence of optional `gsm_operator` field for devices with
    # cellular module
    if is_gsm_operator_expected:
        assert cfg.gsm_operator == '54321'
    else:
        assert cfg.gsm_operator is None

    # Modify and save the configuration
    cfg.ap_enabled = True
    await cfg.save()

    # Verify data sent to the device, `gsm_operator` field should not be sent
    # regardless if it was present when loading from device
    assert await mock_device.recv_data == [
        b'ISTART[212,212,""]IEND\0',
        b'ISTART[213,213,[213,'
        b'[1,"123456789",1,1,"apn.a.net","user","pwd",3]'
        b']]IEND\0'
    ]


@pytest.mark.parametrize(
    'field_name,invalid_value_low,invalid_value_high,valid_value', [
        pytest.param(
            'apn_name', None, 'a' * 101, 'valid.apn.net',
            id='apn_name'
        ),
        pytest.param(
            'apn_user', None, 'a' * 65, 'valid_user',
            id='apn_user'
        ),
        pytest.param(
            'apn_password', None, 'a' * 65, 'valid_password',
            id='apn_password'
        ),
        pytest.param(
            'ap_enabled', -1, 2, 1,
            id='ap_enabled'
        ),
        pytest.param(
            'wifi_enabled', -1, 2, 0,
            id='wifi_enabled'
        ),
        pytest.param(
            'gprs_enabled', -1, 2, 1,
            id='gprs_enabled'
        ),
        pytest.param(
            'ap_password', 'a' * 8, 'a' * 65, 'valid_password',
            id='ap_password'
        ),
        # Feeding invalid values to enums will not get to the validation, hence
        # underlying integer field is tested directly
        pytest.param(
            '_apn_auth', min(G90APNAuth) - 1, max(G90APNAuth) + 1,
            G90APNAuth.NONE,
            id='apn_auth'
        ),
    ]
)
@pytest.mark.g90device(sent_data=[
    b'ISTART[212,'
    b'[0,"123456789",1,1,"apn.a.net","user","pwd",3,"54321"]'
    b']IEND\0',
    b'ISTARTIEND\0'
])
async def test_net_config_constraints(
    field_name: str,
    invalid_value_low: Optional[Union[int, str]],
    invalid_value_high: Union[int, str],
    valid_value: Union[int, str],
    mock_device: DeviceMock
) -> None:
    """
    Tests for network configuration field validation constraints.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    # Retrieve configuration
    cfg = await g90.net_config()
    assert isinstance(cfg, G90NetConfig)

    # Test setting invalid low value for the fields having minimum length
    # constraint
    if invalid_value_low is not None:
        with pytest.raises(ValueError):
            setattr(cfg, field_name, invalid_value_low)

    # Test setting invalid high value
    with pytest.raises(ValueError):
        setattr(cfg, field_name, invalid_value_high)

    # Test setting valid value
    setattr(cfg, field_name, valid_value)
    assert getattr(cfg, field_name) == valid_value


@pytest.mark.g90device(sent_data=[
    b'ISTART[212,'
    b'[0,"123456789",1,1,"","user","pwd",3,"54321"]'
    b']IEND\0',
    b'ISTARTIEND\0'
])
async def test_net_config_apn_name_empty(
    mock_device: DeviceMock, caplog: pytest.LogCaptureFixture
) -> None:
    """
    Tests for handling network configuration with empty APN name.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    # Retrieve configuration
    cfg = await g90.net_config()
    assert isinstance(cfg, G90NetConfig)

    # Ensure that no validation error was logged for empty APN name, the value
    # of the field as recevied from the panel is trusted, so no exception will
    # be raised only error logged
    assert (
        'apn_name: Validation failed during initialization for trusted value'
    ) not in ''.join(caplog.messages)

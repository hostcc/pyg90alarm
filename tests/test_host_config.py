"""
Tests for alarm panel configuration retrieval and modification.
"""
from __future__ import annotations
import pytest
from pyg90alarm.alarm import (
    G90Alarm,
)
from pyg90alarm.local.host_config import (
    G90HostConfig, G90SpeechLanguage, G90VolumeLevel,
)
from .device_mock import DeviceMock


@pytest.mark.parametrize('is_ring_volume_expected,expected_recv_data', [
    pytest.param(
        True, [
            b'ISTART[106,106,""]IEND\0',
            b'ISTART[107,107,[107,'
            b'[600,0,0,1,2,2,60,2,0,60,2]'
            b']]IEND\0'
        ], marks=pytest.mark.g90device(sent_data=[
            b'ISTART[106,'
            b'[900,0,0,1,2,2,60,2,0,60,2]'
            b']IEND\0',
            b'ISTARTIEND\0'
        ]),
        id='Device with cellular module'
    ),
    pytest.param(
        False, [
            b'ISTART[106,106,""]IEND\0',
            b'ISTART[107,107,[107,'
            b'[600,0,0,1,2,2,60,2,0,60]'
            b']]IEND\0'
        ], marks=pytest.mark.g90device(sent_data=[
            b'ISTART[106,'
            b'[900,0,0,1,2,2,60,2,0,60]'
            b']IEND\0',
            b'ISTARTIEND\0'
        ]),
        id='Device with no cellular module'
    ),
])
async def test_host_config(
    is_ring_volume_expected: bool, expected_recv_data: list[bytes],
    mock_device: DeviceMock
) -> None:
    """
    Tests for retrieving and modifying alarm panel configuration from
    the device.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    # Retrieve configuration
    cfg = await g90.host_config()
    assert isinstance(cfg, G90HostConfig)

    # Verify retrieved values
    assert cfg.alarm_siren_duration == 900
    assert cfg.speech_language == G90SpeechLanguage.ENGLISH_MALE
    assert cfg.speech_volume_level == G90VolumeLevel.HIGH
    assert cfg.timezone_offset_m == 60
    assert cfg.key_tone_volume_level == G90VolumeLevel.MUTE
    assert cfg.ring_duration == 60
    assert cfg.alarm_delay == 0
    assert cfg.arm_delay == 0
    assert cfg.backlight_duration == 1
    assert cfg.alarm_volume_level == G90VolumeLevel.HIGH
    # The optional `ring_volume_level` field should be present only if the
    # device has cellular module
    if is_ring_volume_expected:
        assert cfg.ring_volume_level == G90VolumeLevel.HIGH
    else:
        assert cfg.ring_volume_level is None

    # Modify and save configuration
    cfg.alarm_siren_duration = 600
    await cfg.save()

    # Verify data sent to the device
    assert await mock_device.recv_data == expected_recv_data


@pytest.mark.parametrize(
    'field_name,invalid_value_low,invalid_value_high,valid_value', [
        pytest.param(
            'alarm_siren_duration', -1, 2551, 500,
            id='alarm_siren_duration'
        ),
        pytest.param(
            'ring_duration', -1, 2551, 200,
            id='ring_duration'
        ),
        pytest.param(
            'alarm_delay', -1, 2551, 100,
            id='alarm_delay'
        ),
        pytest.param(
            'arm_delay', -1, 2551, 200,
            id='arm_delay'
        ),
        pytest.param(
            'backlight_duration', -1, 2551, 5,
            id='backlight_duration'
        ),
        pytest.param(
            'timezone_offset_m', -720 - 1, 720 + 1, 0,
            id='timezone_offset_m'
        ),
        # Feeding invalid values to enums will not get to the validation, hence
        # underlying integer fields are tested directly
        pytest.param(
            '_speech_language', min(G90SpeechLanguage) - 1,
            max(G90SpeechLanguage) + 1, G90SpeechLanguage.ENGLISH_FEMALE,
            id='speech_language'
        ),
        pytest.param(
            '_speech_volume_level', min(G90VolumeLevel) - 1,
            max(G90VolumeLevel) + 1, G90VolumeLevel.LOW,
            id='speech_volume_level'
        ),
        pytest.param(
            '_alarm_volume_level', min(G90VolumeLevel) - 1,
            max(G90VolumeLevel) + 1, G90VolumeLevel.MUTE,
            id='alarm_volume_level'
        ),
        pytest.param(
            '_key_tone_volume_level', min(G90VolumeLevel) - 1,
            max(G90VolumeLevel) + 1, G90VolumeLevel.HIGH,
            id='key_tone_volume_level'
        ),
    ]
)
@pytest.mark.g90device(sent_data=[
    b'ISTART[106,'
    b'[900,0,0,1,2,2,60,2,0,60,2]'
    b']IEND\0',
    b'ISTARTIEND\0'
])
async def test_host_config_constrants(
    field_name: str,
    invalid_value_low: int,
    invalid_value_high: int,
    valid_value: int,
    mock_device: DeviceMock
) -> None:
    """
    Tests for validation constraints of host configuration fields.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    # Retrieve configuration
    cfg = await g90.host_config()

    # Test setting invalid low value
    with pytest.raises(ValueError):
        setattr(cfg, field_name, invalid_value_low)

    # Test setting invalid high value
    with pytest.raises(ValueError):
        setattr(cfg, field_name, invalid_value_high)

    # Test setting valid value
    setattr(cfg, field_name, valid_value)
    assert getattr(cfg, field_name) == valid_value

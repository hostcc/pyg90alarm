"""
Tests for alarm panel configuration retrieval and modification.
"""
import pytest
from pyg90alarm.alarm import (
    G90Alarm,
)
from pyg90alarm.local.host_config import (
    G90HostConfig, G90SpeechLanguage, G90VolumeLevel,
)
from .device_mock import DeviceMock


@pytest.mark.g90device(sent_data=[
    b'ISTART[106,'
    b'[900,0,0,1,2,2,60,2,0,60,2]'
    b']IEND\0',
    b'ISTARTIEND\0'
])
async def test_host_config(mock_device: DeviceMock) -> None:
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
    assert cfg.ring_volume_level == G90VolumeLevel.HIGH
    assert cfg.key_tone_volume_level == G90VolumeLevel.MUTE
    assert cfg.ring_duration == 60
    assert cfg.alarm_delay == 0
    assert cfg.arm_delay == 0
    assert cfg.backlight_duration == 1
    assert cfg.alarm_volume_level == G90VolumeLevel.HIGH

    # Modify and save configuration
    cfg.alarm_siren_duration = 600
    await cfg.save()

    # Verify data sent to the device
    assert await mock_device.recv_data == [
        b'ISTART[106,106,""]IEND\0',
        b'ISTART[107,107,[107,'
        b'[600,0,0,1,2,2,60,2,0,60,2]'
        b']]IEND\0'
    ]

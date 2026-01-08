"""
Tests for alarm phone numbers retrieval and configuration.
"""
import pytest
from pyg90alarm.alarm import (
    G90Alarm,
)
from pyg90alarm.local.alarm_phones import G90AlarmPhones
from .device_mock import DeviceMock


@pytest.mark.g90device(sent_data=[
    b'ISTART[114,'
    b'["1234", "11111111", "", "", "", "", "", "", "87654321", "12345678"]'
    b']IEND\0',
    b'ISTARTIEND\0'
])
async def test_alarm_phones_config(mock_device: DeviceMock) -> None:
    """
    Tests for retrieving and modifying alarm phones information from
    the device.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    # Retrieve alarm phones configuration
    phones = await g90.alarm_phones()
    assert isinstance(phones, G90AlarmPhones)

    # Verify retrieved data
    assert phones.panel_password == '1234'
    assert phones.panel_phone_number == '11111111'
    assert phones.phone_number_1 == ''
    assert phones.phone_number_2 == ''
    assert phones.phone_number_3 == ''
    assert phones.phone_number_4 == ''
    assert phones.phone_number_5 == ''
    assert phones.phone_number_6 == ''
    assert phones.sms_push_number_1 == '87654321'
    assert phones.sms_push_number_2 == '12345678'

    # Modify and save alarm phones configuration
    phones.panel_password = '5678'
    await phones.save()

    # Verify data sent to the device
    assert await mock_device.recv_data == [
        b'ISTART[114,114,""]IEND\0',
        b'ISTART[108,108,[108,'
        b'["5678","11111111","","","","","","","87654321","12345678"]'
        b']]IEND\0'
    ]

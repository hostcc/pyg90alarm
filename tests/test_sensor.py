"""
Tests for the G90Sensor class.
"""
from __future__ import annotations
import pytest
from pyg90alarm.alarm import (
    G90Alarm,
)
from pyg90alarm.entities.sensor import (
    G90Sensor, G90SensorUserFlags, G90SensorAlertModes,
)
from .device_mock import DeviceMock


@pytest.mark.g90device(sent_data=[
    b'ISTART[102,'
    b'[[3,1,3],["Remote 1",10,0,10,1,0,32,0,0,16,1,0,""],'
    b'["Remote 2",11,0,10,1,0,32,0,0,16,1,0,""],'
    b'["Cord 1",12,0,126,1,0,32,0,5,16,1,0,""]'
    b']]IEND\0',
])
async def test_multiple_sensors_shorter_than_page(
    mock_device: DeviceMock
) -> None:
    """
    Tests for retrieving multiple sensors from the panel, while the number of
    those is shorter than a single page.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    sensors = await g90.sensors

    assert await mock_device.recv_data == [
        b'ISTART[102,102,[102,[1,10]]]IEND\0',
    ]
    assert len(sensors) == 3
    assert isinstance(sensors, list)
    assert isinstance(sensors[0], G90Sensor)
    assert sensors[0].name == 'Remote 1'
    assert sensors[0].index == 10
    assert sensors[0].is_wireless is True
    assert isinstance(sensors[1], G90Sensor)
    assert sensors[1].name == 'Remote 2'
    assert sensors[1].index == 11
    assert sensors[1].is_wireless is True
    assert isinstance(sensors[2], G90Sensor)
    assert sensors[2].name == 'Cord 1'
    assert sensors[2].index == 12
    assert sensors[2].is_wireless is False


@pytest.mark.g90device(sent_data=[
    b'ISTART[102,'
    b'[[11,1,10],'
    b'["Remote 1",10,0,10,1,0,32,0,0,16,1,0,""],'
    b'["Remote 2",11,0,10,1,0,32,0,0,16,1,0,""],'
    b'["Remote 3",12,0,10,1,0,32,0,0,16,1,0,""],'
    b'["Remote 4",13,0,10,1,0,32,0,0,16,1,0,""],'
    b'["Remote 5",14,0,10,1,0,32,0,0,16,1,0,""],'
    b'["Remote 6",15,0,10,1,0,32,0,0,16,1,0,""],'
    b'["Remote 7",16,0,10,1,0,32,0,0,16,1,0,""],'
    b'["Remote 8",17,0,10,1,0,32,0,0,16,1,0,""],'
    b'["Remote 9",18,0,10,1,0,32,0,0,16,1,0,""],'
    b'["Remote 10",19,0,10,1,0,32,0,0,16,1,0,""]'
    b']]IEND\0',
    b'ISTART[102,'
    b'[[11,11,1],'
    b'["Remote 11",20,0,10,1,0,32,0,0,16,1,0,""]'
    b']]IEND\0',
])
async def test_multiple_sensors_longer_than_page(
    mock_device: DeviceMock
) -> None:
    """
    Tests for retrieving multiple sensors from the panel, while the number of
    those is longer than a single page.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    sensors = await g90.sensors

    assert await mock_device.recv_data == [
        b'ISTART[102,102,[102,[1,10]]]IEND\0',
        b'ISTART[102,102,[102,[11,11]]]IEND\0',
    ]
    assert len(sensors) == 11
    assert isinstance(sensors, list)
    assert isinstance(sensors[0], G90Sensor)
    assert sensors[0].name == 'Remote 1'
    assert sensors[0].index == 10


@pytest.mark.g90device(sent_data=[
    b'ISTART[102,'
    b'[[1,1,1],["Remote",10,0,10,1,0,32,0,0,16,1,0,""]]]IEND\0',
])
async def test_single_sensor(mock_device: DeviceMock) -> None:
    """
    Tests for retrieving single sensor from the panel.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    sensors = await g90.sensors

    assert await mock_device.recv_data == [
        b'ISTART[102,102,[102,[1,10]]]IEND\0',
    ]
    assert len(sensors) == 1
    assert isinstance(sensors, list)
    assert isinstance(sensors[0], G90Sensor)
    assert sensors[0].name == 'Remote'
    assert sensors[0].index == 10
    assert isinstance(sensors[0]._asdict(), dict)


@pytest.mark.g90device(sent_data=[
    b'ISTART[102,'
    b'[[2,1,2],'
    b'["Night Light1",11,0,138,0,0,63,0,0,17,1,0,""],'
    b'["Night Light2",10,0,138,0,0,63,0,0,17,1,0,""]'
    b']]IEND\0',
    b'ISTART[102,'
    b'[[2,2,1],'
    b'["Night Light2",10,0,138,0,0,63,0,0,17,1,0,""]'
    b']]IEND\0',
    b"ISTARTIEND\0",
])
@pytest.mark.parametrize(
    'flag,value_before,value_after,expected_data', [
        pytest.param(
            G90SensorUserFlags.ENABLED, True, False, [
                b'ISTART[102,102,[102,[1,10]]]IEND\0',
                b'ISTART[102,102,[102,[2,2]]]IEND\0',
                b'ISTART[103,103,[103,'
                b'["Night Light2",10,0,138,0,0,62,0,0,17,1,0,2,"060A0600"]'
                b']]IEND\0',
            ],
            id='enabled',
        ),
        pytest.param(
            G90SensorUserFlags.ENABLED, True, True, [
                b'ISTART[102,102,[102,[1,10]]]IEND\0',
            ],
            id='enabled-not-changed',
        ),
        pytest.param(
            G90SensorUserFlags.ARM_DELAY, True, False, [
                b'ISTART[102,102,[102,[1,10]]]IEND\0',
                b'ISTART[102,102,[102,[2,2]]]IEND\0',
                b'ISTART[103,103,[103,'
                b'["Night Light2",10,0,138,0,0,61,0,0,17,1,0,2,"060A0600"]'
                b']]IEND\0',
            ],
            id='arm_delay',
        ),
        pytest.param(
            G90SensorUserFlags.DETECT_DOOR, True, False, [
                b'ISTART[102,102,[102,[1,10]]]IEND\0',
                b'ISTART[102,102,[102,[2,2]]]IEND\0',
                b'ISTART[103,103,[103,'
                b'["Night Light2",10,0,138,0,0,59,0,0,17,1,0,2,"060A0600"]'
                b']]IEND\0',
            ],
            id='detect_door',
        ),
        pytest.param(
            G90SensorUserFlags.DOOR_CHIME, True, False, [
                b'ISTART[102,102,[102,[1,10]]]IEND\0',
                b'ISTART[102,102,[102,[2,2]]]IEND\0',
                b'ISTART[103,103,[103,'
                b'["Night Light2",10,0,138,0,0,55,0,0,17,1,0,2,"060A0600"]'
                b']]IEND\0',
            ],
            id='door_chime',
        ),
        pytest.param(
            G90SensorUserFlags.INDEPENDENT_ZONE, True, False, [
                b'ISTART[102,102,[102,[1,10]]]IEND\0',
                b'ISTART[102,102,[102,[2,2]]]IEND\0',
                b'ISTART[103,103,[103,'
                b'["Night Light2",10,0,138,0,0,47,0,0,17,1,0,2,"060A0600"]'
                b']]IEND\0',
            ],
            id='independent_zone',
        ),
    ]
)
async def test_sensor_user_flag(
    flag: G90SensorUserFlags,
    value_before: bool,
    value_after: bool,
    expected_data: list[bytes], mock_device: DeviceMock
) -> None:
    """
    Tests for settings flags on a sensor.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    sensors = await g90.sensors
    assert sensors[1].get_flag(flag) == value_before
    await sensors[1].set_flag(flag, value_after)
    assert sensors[1].get_flag(flag) == value_after
    assert await mock_device.recv_data == expected_data


@pytest.mark.g90device(sent_data=[
    b'ISTART[102,'
    b'[[2,1,2],'
    b'["Night Light1",11,0,138,0,0,63,0,0,17,1,0,""],'
    b'["Night Light2",10,0,138,0,0,63,0,0,17,1,0,""]'
    b']]IEND\0',
    b'ISTART[102,'
    b'[[2,2,1],'
    b'["Night Light2",10,0,138,0,0,63,0,0,17,1,0,""]'
    b']]IEND\0',
    b"ISTARTIEND\0",
])
@pytest.mark.parametrize(
    'value_before,value_after,expected_response', [
        pytest.param(
            G90SensorAlertModes.ALERT_WHEN_AWAY_AND_HOME,
            G90SensorAlertModes.ALERT_ALWAYS, [
                b'ISTART[102,102,[102,[1,10]]]IEND\0',
                b'ISTART[102,102,[102,[2,2]]]IEND\0',
                b'ISTART[103,103,[103,'
                b'["Night Light2",10,0,138,0,0,31,0,0,17,1,0,2,"060A0600"]'
                b']]IEND\0',
            ],
            id='always',
        ),
        pytest.param(
            G90SensorAlertModes.ALERT_WHEN_AWAY_AND_HOME,
            G90SensorAlertModes.ALERT_WHEN_AWAY, [
                b'ISTART[102,102,[102,[1,10]]]IEND\0',
                b'ISTART[102,102,[102,[2,2]]]IEND\0',
                b'ISTART[103,103,[103,'
                b'["Night Light2",10,0,138,0,0,95,0,0,17,1,0,2,"060A0600"]'
                b']]IEND\0',
            ],
            id='when-away',
        ),
        pytest.param(
            G90SensorAlertModes.ALERT_WHEN_AWAY_AND_HOME,
            G90SensorAlertModes.ALERT_WHEN_AWAY_AND_HOME, [
                b'ISTART[102,102,[102,[1,10]]]IEND\0',
            ],
            id='not-changed',
        ),
    ]
)
async def test_sensor_user_alert_mode(
    value_before: G90SensorAlertModes,
    value_after: G90SensorAlertModes,
    expected_response: list[bytes], mock_device: DeviceMock
) -> None:
    """
    Tests for setting alert mode on a sensor.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    sensors = await g90.sensors
    assert sensors[1].alert_mode == value_before
    await sensors[1].set_alert_mode(value_after)
    assert sensors[1].alert_mode == value_after
    assert await mock_device.recv_data == expected_response


@pytest.mark.g90device(sent_data=[
    b'ISTART[102,'
    b'[[2,1,2],'
    b'["Night Light1",11,0,138,0,0,33,0,0,17,1,0,""],'
    b'["Night Light2",10,0,138,0,0,33,0,0,17,1,0,""]'
    b']]IEND\0',
    b'ISTART[102,'
    b'[[2,2,1],'
    b'["Night Light2",10,0,138,0,0,1,0,0,17,1,0,""]'
    b']]IEND\0',
    b"ISTARTIEND\0",
])
async def test_sensor_disable_externally_modified(
    mock_device: DeviceMock
) -> None:
    """
    Tests for disabling a sensor that has been modified externally.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    sensors = await g90.sensors
    assert sensors[1].enabled
    await sensors[1].set_enabled(False)
    assert sensors[1].enabled
    assert await mock_device.recv_data == [
        b'ISTART[102,102,[102,[1,10]]]IEND\0',
        b'ISTART[102,102,[102,[2,2]]]IEND\0',
    ]


@pytest.mark.g90device(sent_data=[
    b'ISTART[102,'
    b'[[1,1,1],["Unsupported",10,0,255,0,0,33,0,0,17,1,0,""]'
    b']]IEND\0',
    b"ISTARTIEND\0",
])
async def test_sensor_unsupported_disable(mock_device: DeviceMock) -> None:
    """
    Tests for disabling an unsupported sensor.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    sensors = await g90.sensors
    assert sensors[0].enabled
    await sensors[0].set_enabled(False)
    assert await mock_device.recv_data == [
        b'ISTART[102,102,[102,[1,10]]]IEND\0',
    ]


@pytest.mark.g90device(sent_data=[
    b'ISTART[102,'
    b'[[2,1,2],'
    b'["Night Light1",11,0,138,0,0,33,0,0,17,1,0,""],'
    b'["Night Light2",10,0,138,0,0,33,0,0,17,1,0,""]'
    b']]IEND\0',
    b'ISTART[102,[[2,2,0]]]IEND\0',
])
async def test_sensor_disable_sensor_not_found_on_refresh(
    mock_device: DeviceMock
) -> None:
    """
    Tests for disabling a sensor that is not found on refresh.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    sensors = await g90.sensors
    assert sensors[1].enabled
    await sensors[1].set_enabled(False)
    assert sensors[1].enabled
    assert await mock_device.recv_data == [
        b'ISTART[102,102,[102,[1,10]]]IEND\0',
        b'ISTART[102,102,[102,[2,2]]]IEND\0',
    ]


@pytest.mark.g90device(sent_data=[
    b'ISTART[102,'
    b'[[1,1,1],'
    b'["Night Light2",10,0,138,0,0,33,0,0,17,1,0,""]'
    b']]IEND\0',
    b'ISTART[102,'
    b'[[1,1,1],'
    b'["Night Light2",10,0,138,0,0,33,0,0,17,1,0,""]'
    b']]IEND\0',
    b"ISTARTIEND\0",
])
@pytest.mark.parametrize(
    'flags,expected_response', [
        pytest.param(
            # Intentionally contains non-user settable flag, which should be
            # ignored and not configured for the sensor that initial doesn't
            # have it set
            G90SensorUserFlags.INDEPENDENT_ZONE | G90SensorUserFlags.ARM_DELAY
            | G90SensorUserFlags.SUPPORTS_UPDATING_SUBTYPE, [
                b'ISTART[102,102,[102,[1,10]]]IEND\0',
                b'ISTART[102,102,[102,[1,1]]]IEND\0',
                b'ISTART[103,103,[103,'
                b'["Night Light2",10,0,138,0,0,18,0,0,17,1,0,2,"060A0600"]'
                b']]IEND\0',
            ],
            id='set-flags',
        ),
        pytest.param(
            G90SensorUserFlags.ALERT_WHEN_AWAY_AND_HOME
            | G90SensorUserFlags.ENABLED, [
                b'ISTART[102,102,[102,[1,10]]]IEND\0',
                b'ISTART[102,102,[102,[1,1]]]IEND\0',
            ],
            id='set-flags-not-changed',
        ),
    ]
)
async def test_sensor_set_user_flags(
    flags: G90SensorUserFlags, expected_response: list[bytes],
    mock_device: DeviceMock
) -> None:
    """
    Tests for setting user flags on a sensor.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    sensors = await g90.sensors
    await sensors[0].set_user_flags(flags)
    assert await mock_device.recv_data == expected_response


@pytest.mark.g90device(sent_data=[
    b'ISTART[102,'
    b'[[1,1,1],'
    b'["Night Light2",10,0,138,0,0,33,0,0,17,1,0,""]'
    b']]IEND\0',
    b"ISTARTIEND\0",
])
async def test_sensor_delete(mock_device: DeviceMock) -> None:
    """
    Tests deleting the sensor.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    sensors = await g90.sensors
    await sensors[0].delete()
    assert sensors[0].is_unavailable
    assert await mock_device.recv_data == [
        b'ISTART[102,102,[102,[1,10]]]IEND\0',
        b'ISTART[131,131,[131,[10]]]IEND\0',
    ]

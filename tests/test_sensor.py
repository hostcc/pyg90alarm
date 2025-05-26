"""
Tests for the G90Sensor class.
"""
from __future__ import annotations
import asyncio
from unittest.mock import MagicMock
from contextlib import nullcontext, AbstractContextManager
import pytest
from pyg90alarm import (
    G90Alarm, G90Error, G90EntityRegistrationError,
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
    b'["Cord 1",11,0,126,1,0,63,0,5,16,1,0,""],'
    b'["Cord 2",10,0,126,1,0,63,0,5,16,1,0,""]'
    b']]IEND\0',
    b'ISTART[102,'
    b'[[2,2,1],'
    b'["Cord 2",10,0,126,1,0,63,0,5,16,1,0,""]'
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
                b'["Cord 2",10,0,126,1,0,62,0,5,16,1,0,0,"00"]'
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
                b'["Cord 2",10,0,126,1,0,61,0,5,16,1,0,0,"00"]'
                b']]IEND\0',
            ],
            id='arm_delay',
        ),
        pytest.param(
            G90SensorUserFlags.DETECT_DOOR, True, False, [
                b'ISTART[102,102,[102,[1,10]]]IEND\0',
                b'ISTART[102,102,[102,[2,2]]]IEND\0',
                b'ISTART[103,103,[103,'
                b'["Cord 2",10,0,126,1,0,59,0,5,16,1,0,0,"00"]'
                b']]IEND\0',
            ],
            id='detect_door',
        ),
        pytest.param(
            G90SensorUserFlags.DOOR_CHIME, True, False, [
                b'ISTART[102,102,[102,[1,10]]]IEND\0',
                b'ISTART[102,102,[102,[2,2]]]IEND\0',
                b'ISTART[103,103,[103,'
                b'["Cord 2",10,0,126,1,0,55,0,5,16,1,0,0,"00"]'
                b']]IEND\0',
            ],
            id='door_chime',
        ),
        pytest.param(
            G90SensorUserFlags.INDEPENDENT_ZONE, True, False, [
                b'ISTART[102,102,[102,[1,10]]]IEND\0',
                b'ISTART[102,102,[102,[2,2]]]IEND\0',
                b'ISTART[103,103,[103,'
                b'["Cord 2",10,0,126,1,0,47,0,5,16,1,0,0,"00"]'
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
    b'["Cord 1",11,0,126,1,0,63,0,5,16,1,0,""],'
    b'["Cord 2",10,0,126,1,0,63,0,5,16,1,0,""]'
    b']]IEND\0',
    b'ISTART[102,'
    b'[[2,2,1],'
    b'["Cord 2",10,0,126,1,0,63,0,5,16,1,0,""]'
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
                b'["Cord 2",10,0,126,1,0,31,0,5,16,1,0,0,"00"]'
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
                b'["Cord 2",10,0,126,1,0,95,0,5,16,1,0,0,"00"]'
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
    b'["Cord 1",11,0,126,1,0,33,0,5,16,1,0,""],'
    b'["Cord 2",10,0,126,1,0,33,0,5,16,1,0,""]'
    b']]IEND\0',
    b'ISTART[102,'
    b'[[2,2,1],'
    b'["Cord 2",10,0,126,1,0,1,0,5,16,1,0,""]'
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
    b'["Cord 1",11,0,126,1,0,33,0,5,16,1,0,""],'
    b'["Cord 2",10,0,126,1,0,33,0,5,16,1,0,""]'
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
    b'["Cord 2",10,0,126,1,0,33,0,5,16,1,0,""]'
    b']]IEND\0',
    b'ISTART[102,'
    b'[[1,1,1],'
    b'["Cord 2",10,0,126,1,0,33,0,5,16,1,0,""]'
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
                b'["Cord 2",10,0,126,1,0,18,0,5,16,1,0,0,"00"]'
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
    b'["Cord 2",10,0,126,1,0,33,0,5,16,1,0,""]'
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


REGISTER_SENSOR_SENT_DATA = [
    b'ISTART[102,'
    b'[[2,1,2],'
    b'["Cord 1",11,0,126,1,0,63,0,5,16,1,0,""],'
    b'["Cord 2",10,0,126,1,0,63,0,5,16,1,0,""]'
    b']]IEND\0',
    b'ISTARTIEND\0',
    b'ISTART[102,'
    b'[[3,1,3],'
    b'["Cord 1",11,0,126,1,0,63,0,5,16,1,0,""],'
    b'["Cord 2",10,0,126,1,0,63,0,5,16,1,0,""],'
    b'["Test sensor",3,0,1,3,0,33,0,0,0,1,0,""]'
    b']]IEND\0',
]


@pytest.mark.parametrize(
    'expected_exception', [
        # Normal operation, no exception expected
        pytest.param(
            nullcontext(),
            id='register-sensor-ok',
            marks=pytest.mark.g90device(
                sent_data=REGISTER_SENSOR_SENT_DATA,
                notification_data=[b'[170,[4,[3, "Test sensor", 1]]]\0']
            ),
        ),
        # Operartion simulates the panel sent the notification for the newly
        # added sensor, but it was not found in the list of sensors then
        pytest.param(
            pytest.raises(G90EntityRegistrationError),
            id='register-sensor-not-found',
            marks=pytest.mark.g90device(
                sent_data=REGISTER_SENSOR_SENT_DATA,
                notification_data=[b'[170,[4,[33, "Test sensor", 1]]]\0']
            ),
        ),
        # Operation simulates the panel did not send the notification
        # for the newly added sensor
        pytest.param(
            pytest.raises(G90EntityRegistrationError),
            id='register-sensor-timed-out',
            marks=pytest.mark.g90device(
                sent_data=REGISTER_SENSOR_SENT_DATA,
                notification_data=[]
            ),
        ),
        # Operation simulates the panel sent the notification for the newly
        # added sensor, but it retrieving sensor list afterwards resulted in
        # an error
        pytest.param(
            pytest.raises(G90Error),
            id='register-sensor-failed-update',
            marks=pytest.mark.g90device(
                sent_data=[
                    b'ISTART[102,'
                    b'[[2,1,2],'
                    b'["Cord 1",11,0,126,1,0,63,0,5,16,1,0,""],'
                    b'["Cord 2",10,0,126,1,0,63,0,5,16,1,0,""]'
                    b']]IEND\0',
                    b'ISTARTIEND\0',
                    b'garbage',
                ],
                notification_data=[b'[170,[4,[3, "Test sensor", 1]]]\0']
            ),
        ),
    ])
async def test_sensor_register(
    expected_exception: AbstractContextManager[Exception],
    mock_device: DeviceMock
) -> None:
    """
    Tests for registering a sensor.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    # Setup the notifications, since those are required to complete the
    # registration process
    await g90.use_local_notifications(
        notifications_local_host=mock_device.notification_host,
        notifications_local_port=mock_device.notification_port
    )
    await g90.listen_notifications()

    # Attempt to register a new sensor in parallel with simulating the
    # notification from the panel, otherwise the registration will timeout
    task = asyncio.create_task(
        g90.register_sensor('Door Sensor: WRDS01', 'Test sensor', timeout=0.2),
    )
    # Simulate some delay for panel to complete the registration and send the
    # notification
    await asyncio.sleep(0.1)
    await mock_device.send_next_notification()

    # Wait for registration to complete
    await asyncio.wait([task], timeout=0.5)

    with expected_exception:
        # Retrieve the sensor just registered
        sensor = task.result()

        # Verify the sensor is registered properly
        assert isinstance(sensor, G90Sensor)
        assert sensor.name == 'Test sensor'
        assert sensor.index == 3

        # Verify the sequence of commands sent to the panel
        assert await mock_device.recv_data == [
            b'ISTART[102,102,[102,[1,10]]]IEND\0',
            b'ISTART[156,156,[156,'
            b'["Test sensor",0,0,1,3,0,33,0,0,0,1,0,0,"00"]'
            b']]IEND\0',
            b'ISTART[102,102,[102,[1,10]]]IEND\0',
        ]

    await g90.close_notifications()


@pytest.mark.g90device(sent_data=[
    b'ISTART[102,'
    b'[[1,1,1],'
    b'["Cord 2",10,0,126,1,0,33,0,5,16,1,0,""]'
    b']]IEND\0',
    b'ISTART[102,'
    b'[[1,1,1],'
    b'["Cord 2",10,0,126,1,0,32,0,5,16,1,0,""]'
    b']]IEND\0',
])
async def test_sensor_update(mock_device: DeviceMock) -> None:
    """
    Tests updating the sensor and callback assocaited.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    # Set up the sensor list change callback to be called when the sensor
    # list is updated
    list_change_cb = MagicMock()
    g90.sensor_list_change_callback = list_change_cb
    future = asyncio.get_running_loop().create_future()
    list_change_cb.side_effect = (
        lambda *args: future.set_result(True)
    )

    # Trigger sensor list update
    sensors = await g90.get_sensors()

    # Verify the callback is called with correct parameters, indicating the
    # sensor has been added to the list
    await asyncio.wait([future], timeout=0.1)
    list_change_cb.assert_called_once_with(sensors[0], True)

    # Subsequently retrieving the list of sensors should result in same
    # callback invoked, but with different parameters
    future = asyncio.get_running_loop().create_future()
    await g90.get_sensors()
    await asyncio.wait([future], timeout=0.1)
    list_change_cb.assert_called_with(sensors[0], False)

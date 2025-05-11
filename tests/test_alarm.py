"""
Tests for G90Alarm class
"""
import asyncio
from itertools import cycle
from unittest.mock import MagicMock
import pytest

from pyg90alarm.alarm import (
    G90Alarm,
)
from pyg90alarm.local.host_info import (
    G90HostInfo, G90HostInfoGsmStatus, G90HostInfoWifiStatus,
)
from pyg90alarm.entities.device import (
    G90Device,
)
from pyg90alarm.local.host_status import (
    G90HostStatus,
)
from pyg90alarm.local.user_data_crc import (
    G90UserDataCRC,
)
from pyg90alarm.const import (
    G90RemoteButtonStates,
)
from .device_mock import DeviceMock


@pytest.mark.g90device(sent_data=[
    b'ISTART[100,[3,"PHONE","PRODUCT","206","206"]]IEND\0',
])
async def test_host_status(mock_device: DeviceMock) -> None:
    """
    Tests for retrieving host status from the device.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    res = await g90.get_host_status()

    assert await mock_device.recv_data == [b'ISTART[100,100,""]IEND\0']
    assert isinstance(res, G90HostStatus)
    assert res.host_status == 3
    assert res.product_name == 'PRODUCT'
    assert res.host_phone_number == 'PHONE'
    assert isinstance(res._asdict(), dict)


@pytest.mark.g90device(sent_data=[
    b'ISTART[206,'
    b'["DUMMYGUID","DUMMYPRODUCT",'
    b'"1.2","1.1","206","206",3,3,0,2,"4242",50,100]]IEND\0',
])
async def test_host_info(mock_device: DeviceMock) -> None:
    """
    Tests for retrieving host information from the device.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    res = await g90.get_host_info()

    assert await mock_device.recv_data == [b'ISTART[206,206,""]IEND\0']
    assert isinstance(res, G90HostInfo)
    assert res.host_guid == 'DUMMYGUID'
    assert res.product_name == 'DUMMYPRODUCT'
    assert res.gsm_status == G90HostInfoGsmStatus.OPERATIONAL
    assert res.wifi_status == G90HostInfoWifiStatus.OPERATIONAL
    assert isinstance(res._asdict(), dict)


@pytest.mark.g90device(sent_data=[
    b'ISTART[160,["1","0xab","3","4","5","6"]]IEND\0',
    b'ISTART[160,["1","0xab","3","4","5","6"]]IEND\0',
])
async def test_user_data_crc(mock_device: DeviceMock) -> None:
    """
    Tests for retrieving user data CRCs from the device.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    crc = await g90.get_user_data_crc()
    prop_crc = await g90.user_data_crc

    assert crc == prop_crc
    assert await mock_device.recv_data == [
        b'ISTART[160,160,""]IEND\0',
        b'ISTART[160,160,""]IEND\0',
    ]
    assert isinstance(crc, G90UserDataCRC)
    assert crc.sensor_list == '1'
    assert crc.device_list == '0xab'
    assert crc.history_list == '3'
    assert crc.scene_list == '4'
    assert crc.ifttt_list == '5'
    assert crc.fingerprint_list == '6'


@pytest.mark.g90device(sent_data=[
    b'ISTART[138,'
    b'[[1,1,1],["Switch",10,0,10,1,0,32,0,0,16,1,0,""]]]IEND\0',
])
async def test_devices(mock_device: DeviceMock) -> None:
    """
    Tests for retrieving devices from the panel.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    devices = await g90.get_devices()
    prop_devices = await g90.devices

    assert devices == prop_devices
    assert await mock_device.recv_data == [
        b'ISTART[138,138,[138,[1,10]]]IEND\0',
    ]
    assert len(devices) == 1
    assert isinstance(devices, list)
    assert isinstance(devices[0], G90Device)
    assert devices[0].name == 'Switch'
    assert devices[0].index == 10
    assert isinstance(devices[0]._asdict(), dict)


# Provide an endless sequence of simulated panel responses for the devices
# list. Each attempt will simulate a single device. This sequence will prevent
# `G90TimeoutError` if the code under test initiates more exchanges with the
# panel than the simulated data contains.
@pytest.mark.g90device(sent_data=cycle([
    b'ISTART[138,'
    b'[[1,1,1],["Switch",10,0,10,1,0,32,0,0,16,1,0,""]]]IEND\0',
]))
async def test_get_devices_concurrent(mock_device: DeviceMock) -> None:
    """
    Tests for concurrently retrieving list of devices produces consistent
    results.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    g90.paginated_result = MagicMock(  # type: ignore[method-assign]
        spec=g90.paginated_result, wraps=g90.paginated_result
    )

    # Issue two concurrent requests to retrieve devices
    res = await asyncio.gather(g90.get_devices(), g90.get_devices())
    # Ensure only single exchange with the panel
    assert g90.paginated_result.call_count == 2
    # While `pylint` demands use of generator, the comprehension is used
    # instead for ease of troubleshooting test failures as it will show the
    # list elements, not just generator instance
    # pylint: disable=use-a-generator
    assert all([len(x) == 1 for x in res])


@pytest.mark.g90device(sent_data=[
    b'ISTART[138,'
    b'[[1,1,1],["Switch",10,0,10,1,0,32,0,0,16,2,0,""]]]IEND\0'
])
async def test_multinode_device(mock_device: DeviceMock) -> None:
    """
    Tests for retrieving multi-node devices (e.g. multi-channel switch) from
    the panel.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    devices = await g90.get_devices()
    prop_devices = await g90.devices

    assert devices == prop_devices
    assert await mock_device.recv_data == [
        b'ISTART[138,138,[138,[1,10]]]IEND\0',
    ]
    assert len(devices) == 2
    assert isinstance(devices, list)
    assert isinstance(devices[0], G90Device)
    assert devices[0].name == 'Switch#1'
    assert devices[0].index == 10
    assert devices[0].subindex == 0
    assert devices[1].name == 'Switch#2'
    assert devices[1].index == 10
    assert devices[1].subindex == 1


@pytest.mark.g90device(sent_data=[
    b'ISTART[138,'
    b'[[1,1,1],["Switch",10,0,10,1,0,32,0,0,16,1,0,""]]]IEND\0',
    b'ISTARTIEND\0',
    b'ISTARTIEND\0',
])
async def test_control_device(mock_device: DeviceMock) -> None:
    """
    Tests for controlling devices from the panel.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    devices = await g90.get_devices()
    prop_devices = await g90.devices

    assert devices == prop_devices
    await devices[0].turn_on()
    await devices[0].turn_off()
    assert await mock_device.recv_data == [
        b'ISTART[138,138,[138,[1,10]]]IEND\0',
        b'ISTART[137,137,[137,[10,0,0]]]IEND\0',
        b'ISTART[137,137,[137,[10,1,0]]]IEND\0',
    ]


# See `test_get_devices_concurrent` for the explanation of the test
@pytest.mark.g90device(sent_data=cycle([
    b'ISTART[102,'
    b'[[1,1,1],["Remote",10,0,10,1,0,32,0,0,16,1,0,""]]]IEND\0',
]))
async def test_get_sensors_concurrent(mock_device: DeviceMock) -> None:
    """
    Tests for concurrently retrieving list of sensors produces consistent
    results.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    g90.paginated_result = MagicMock(  # type: ignore[method-assign]
        spec=g90.paginated_result, wraps=g90.paginated_result
    )

    res = await asyncio.gather(g90.get_sensors(), g90.get_sensors())
    assert g90.paginated_result.call_count == 2
    # pylint: disable=use-a-generator
    assert all([len(x) == 1 for x in res])


@pytest.mark.g90device(sent_data=[
    b'ISTART[102,'
    b'[[1,1,1],["Remote",10,0,10,1,0,32,0,0,16,1,0,""]]]IEND\0',
    b'ISTART[102,'
    b'[[1,1,1],["Remote",10,0,10,1,0,33,0,0,16,1,0,""]]]IEND\0',
    b'ISTART[102,'
    b'[[1,1,1],["Remote 2",11,0,10,1,0,33,0,0,16,1,0,""]]]IEND\0',
])
async def test_get_sensors_update(mock_device: DeviceMock) -> None:
    """
    Verifies updating the sensor list from the panel properly updates entitries
    exists in the list already, and marks those are not.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    # Ensure initial update results in single list entry
    sensors = await g90.get_sensors()
    assert len(sensors) == 1
    assert sensors[0].name == 'Remote'
    assert sensors[0].enabled is False
    # Check if existing enty is properly updated
    sensors = await g90.get_sensors()
    assert len(sensors) == 1
    assert sensors[0].name == 'Remote'
    assert sensors[0].enabled is True

    sensor_1 = sensors[0]

    # Ensure subsequent update results in two list entries, one being added and
    # another one is marked as unavailable (since it isn't present in the list
    # fetched from the device)
    sensors = await g90.get_sensors()
    assert len(sensors) == 2
    assert sensors[0].is_unavailable is True
    assert sensors[0].name == 'Remote'

    assert sensors[1].is_unavailable is False
    assert sensors[1].name == 'Remote 2'

    # Ensure the first entry is still in the list
    assert sensors[0] == sensor_1


@pytest.mark.g90device(sent_data=[
    b'ISTART[102,'
    b'[[1,1,1],["Remote",10,0,10,1,0,32,0,0,16,1,0,""]]]IEND\0',
    b'ISTART[102,'
    b'[[1,1,1],["Remote 2",11,0,10,1,0,33,0,0,16,1,0,""]]]IEND\0',
])
async def test_find_sensor(mock_device: DeviceMock) -> None:
    """
    Verifies updating the sensor list from the panel properly updates entitries
    exists in the list already, and marks those are not.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    sensor = await g90.find_sensor(10, 'Remote')
    assert sensor is not None
    assert sensor.name == 'Remote'

    await g90.get_sensors()
    sensor = await g90.find_sensor(10, 'Remote')
    assert sensor is None
    sensor = await g90.find_sensor(10, 'Remote', exclude_unavailable=False)
    assert sensor is not None


@pytest.mark.g90device(
    sent_data=[
        b'ISTART[102,'
        b'[[1,1,1],["Remote",10,0,10,1,0,32,0,0,16,1,0,""]]]IEND\0',
        b'ISTART[117,[256]]IEND\0',
    ],
    notification_data=[
        b'[170,[5,[10,"Remote"]]]\0',
    ]
)
async def test_sensor_callback(mock_device: DeviceMock) -> None:
    """
    Tests for sensor callback.
    """
    reset_interval = 0.5
    g90 = G90Alarm(
        host=mock_device.host, port=mock_device.port,
        reset_occupancy_interval=reset_interval
    )
    await g90.use_local_notifications(
        notifications_local_host=mock_device.notification_host,
        notifications_local_port=mock_device.notification_port
    )

    sensors = await g90.sensors

    future = asyncio.get_running_loop().create_future()
    sensor = [x for x in sensors if x.index == 10 and x.name == 'Remote']
    sensor[0].state_callback = lambda *args: future.set_result(True)

    await g90.listen_notifications()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    await g90.close_notifications()
    # Once passed this implies the G90Alarm sensor callback works as
    # expected, as it updates the occupancy states of the sensor
    assert sensor[0].occupancy

    # Re-create future since the callback will be invoked again when the
    # occupancy state is reset
    future = asyncio.get_running_loop().create_future()
    # Verify the occupancy state is reset upon configured interval
    await asyncio.sleep(reset_interval)
    assert not sensor[0].occupancy


@pytest.mark.g90device(
    sent_data=[
        b'ISTART[102,'
        b'[[1,1,1],["Remote",26,0,10,1,0,32,0,0,16,1,0,""]]]IEND\0',
        b'ISTART[117,[256]]IEND\0',
    ],
    notification_data=[
        b'[208,[4,26,1,4,"Remote","DUMMYGUID",1719223959,0,[""]]]\0',
        # Simulate sensor activity, which should reset low battery state for it
        b'[170,[5,[26,"Remote"]]]\0',
    ]
)
async def test_sensor_low_battery_callback(mock_device: DeviceMock) -> None:
    """
    Tests for sensor low battery callback.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    await g90.use_local_notifications(
        notifications_local_host=mock_device.notification_host,
        notifications_local_port=mock_device.notification_port
    )

    sensors = await g90.sensors

    future = asyncio.get_running_loop().create_future()
    sensor = [x for x in sensors if x.index == 26 and x.name == 'Remote']
    low_battery_sensor_cb = MagicMock()
    low_battery_sensor_cb.side_effect = lambda *args: future.set_result(True)
    sensor[0].low_battery_callback = low_battery_sensor_cb
    low_battery_cb = MagicMock()
    g90.low_battery_callback = low_battery_cb

    await g90.listen_notifications()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)

    low_battery_sensor_cb.assert_called_once_with()
    low_battery_cb.assert_called_once_with(26, 'Remote')
    # Verify the low battery state is set upon receiving the notification
    assert sensor[0].is_low_battery is True

    # Signal the second notification is ready, the future has to be re-created
    # as the corresponding callback will be fired again
    future = asyncio.get_running_loop().create_future()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)

    # Verify the low battery state is reset upon sensor activity
    assert sensor[0].is_low_battery is False

    await g90.close_notifications()


@pytest.mark.g90device(
    sent_data=[
        b'ISTART[102,'
        b'[[1,1,1],["Hall",21,0,10,1,0,32,0,0,16,1,0,""]]]IEND\0',
    ],
    notification_data=[
        b'[170,[6,[21,"Hall"]]]\0',
        b'[170,[1,[3]]]\0',
    ]
)
async def test_sensor_door_open_when_arming_callback(
    mock_device: DeviceMock
) -> None:
    """
    Tests for sensor door open when arming callback.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    await g90.use_local_notifications(
        notifications_local_host=mock_device.notification_host,
        notifications_local_port=mock_device.notification_port
    )

    sensors = await g90.sensors

    future = asyncio.get_running_loop().create_future()
    sensor = [x for x in sensors if x.index == 21 and x.name == 'Hall']
    door_open_when_arming_sensor_cb = MagicMock()
    door_open_when_arming_sensor_cb.side_effect = (
        lambda *args: future.set_result(True)
    )
    sensor[0].door_open_when_arming_callback = door_open_when_arming_sensor_cb
    door_open_when_arming_cb = MagicMock()
    g90.door_open_when_arming_callback = door_open_when_arming_cb

    await g90.listen_notifications()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)

    door_open_when_arming_sensor_cb.assert_called_once_with()
    door_open_when_arming_cb.assert_called_once_with(21, 'Hall')
    # Verify the door open when arming state is set upon receiving the
    # notification
    assert sensor[0].is_door_open_when_arming is True

    # Signal the second notification is ready, the future has to be re-created
    # as the corresponding callback will be fired again
    future = asyncio.get_running_loop().create_future()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)

    # Verify the door open when arming state is reset upon disarming
    assert sensor[0].is_door_open_when_arming is False

    await g90.close_notifications()


@pytest.mark.g90device(
    sent_data=[
        b'ISTART[102,'
        b'[[3,1,3],["Remote 1",10,0,10,1,0,32,0,0,16,1,0,""],'
        b'["Remote 2",11,0,10,1,0,32,0,0,16,1,0,""],'
        b'["Cord 1",12,0,126,1,0,32,0,5,16,1,0,""]'
        b']]IEND\0',
    ],
    notification_data=[
        b'[170,[1,[1]]]\0'
    ]
)
async def test_armdisarm_callback(mock_device: DeviceMock) -> None:
    """
    Tests for arm/disarm callback.
    """
    future = asyncio.get_running_loop().create_future()
    armdisarm_cb = MagicMock()
    armdisarm_cb.side_effect = lambda *args: future.set_result(True)
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    await g90.use_local_notifications(
        notifications_local_host=mock_device.notification_host,
        notifications_local_port=mock_device.notification_port
    )
    g90.armdisarm_callback = armdisarm_cb
    await g90.listen_notifications()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    await g90.close_notifications()
    armdisarm_cb.assert_called_once_with(1)


@pytest.mark.g90device(
    sent_data=[
        b'ISTART[102,'
        b'[[1,1,1],["Door",100,0,1,1,0,32,0,0,16,1,0,""]]]IEND\0',
        # The GETNOTICEFLAG command is invoked twice, for each of
        # alerts simulated below
        b'ISTART[117,[256]]IEND\0',
        b'ISTART[117,[256]]IEND\0',
    ],
    notification_data=[
        b'[208,[4,100,1,1,"Door","DUMMYGUID",1631545189,0,[""]]]\0',
        b'[208,[4,100,1,0,"Door","DUMMYGUID",1631545189,0,[""]]]\0',
    ]
)
async def test_door_open_close_callback(mock_device: DeviceMock) -> None:
    """
    Tests for door open/close callback.
    """
    future = asyncio.get_running_loop().create_future()
    door_open_close_cb = MagicMock()
    door_open_close_cb.side_effect = lambda *args: future.set_result(True)

    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    await g90.use_local_notifications(
        notifications_local_host=mock_device.notification_host,
        notifications_local_port=mock_device.notification_port
    )
    g90.door_open_close_callback = door_open_close_cb

    # Simulate two device alerts - for opening (this one) and then closing the
    # door (see below)
    await g90.listen_notifications()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    # Corresponding sensor should turn to occupied (=door opened)
    sensors = await g90.sensors
    assert sensors[0].occupancy

    # Simulate second device alert for door close
    await mock_device.send_next_notification()
    # Signal the second alert is ready, the future has to be re-created as
    # the corresponding callback will be fired again
    future = asyncio.get_running_loop().create_future()

    await asyncio.wait([future], timeout=0.1)
    # The sensor should become inactive (=door closed)
    sensors = await g90.sensors
    assert not sensors[0].occupancy

    await g90.close_notifications()


@pytest.mark.g90device(
    sent_data=[
        # Simulate panel with two sensors
        b'ISTART[102,'
        b'[[2,1,2],'
        b'["Hall",100,0,1,1,0,32,0,0,16,1,0,""],'
        b'["Room",101,0,1,1,0,32,0,0,16,1,0,""]'
        b']]IEND\0',
        # Alert configuration, used by sensor activity callback invoked when
        # handling alarm
        b'ISTART[117,[256]]IEND\0',
    ],
    notification_data=[
        b'[208,[3,100,1,1,"Hall","DUMMYGUID",1630876128,0,[""]]]\0',
        b'[208,[3,101,1,1,"Room","DUMMYGUID",1630876128,0,[""]]]\0',
        b'[208,[3,102,1,1,"No Room","DUMMYGUID",1630876128,0,[""]]]\0',
    ]
)
async def test_alarm_callback(mock_device: DeviceMock) -> None:
    """
    Tests for alarm callback.
    """
    future = asyncio.get_running_loop().create_future()
    alarm_cb = MagicMock()
    alarm_cb.side_effect = lambda *args: future.set_result(True)

    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    await g90.use_local_notifications(
        notifications_local_host=mock_device.notification_host,
        notifications_local_port=mock_device.notification_port
    )
    sensors = await g90.sensors
    # Set extra data for the 1st sensor
    sensors[0].extra_data = 'Dummy extra data'

    g90.alarm_callback = alarm_cb
    await g90.listen_notifications()
    # Simulate three alarm notifications - for sensor with extra data,
    # another for sensor with no extra data, and third for non-existent
    # sensor
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    # Verify extra data is passed to the callback
    alarm_cb.assert_called_once_with(100, 'Hall', 'Dummy extra data')
    # Verify the triggering sensor is set to active
    assert sensors[0].occupancy is True

    # Simulate alarm for sensor with no extra data
    alarm_cb.reset_mock()
    future = asyncio.get_running_loop().create_future()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    # Verify no extra data is passed to the callback
    alarm_cb.assert_called_once_with(101, 'Room', None)
    # Verify the triggering sensor is set to active
    assert sensors[0].occupancy is True

    # Simulate alarm for non-existent sensor
    alarm_cb.reset_mock()
    future = asyncio.get_running_loop().create_future()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    # Simulate callback is called with no data
    alarm_cb.assert_called_once_with(102, 'No Room', None)

    await g90.close_notifications()


@pytest.mark.g90device(
    sent_data=[
        b'ISTART[102,'
        b'[[1,1,1],["Hall",100,0,1,1,0,32,0,0,16,1,0,""]]]IEND\0',
        # Alert configuration, used by sensor activity callback invoked when
        # handling alarm
        b'ISTART[117,[256]]IEND\0',
    ],
    notification_data=[
        b'[208,[3,100,1,3,"Hall","DUMMYGUID",1630876128,0,[""]]]\0',
        b'[170,[1,[3]]]\0',
    ]
)
async def test_sensor_tamper_callback(
    mock_device: DeviceMock
) -> None:
    """
    Tests for sensor tamper callback.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    await g90.use_local_notifications(
        notifications_local_host=mock_device.notification_host,
        notifications_local_port=mock_device.notification_port
    )

    sensors = await g90.sensors

    future = asyncio.get_running_loop().create_future()
    sensor = [x for x in sensors if x.index == 100 and x.name == 'Hall']
    tamper_sensor_cb = MagicMock()
    tamper_sensor_cb.side_effect = (
        lambda *args: future.set_result(True)
    )
    sensor[0].tamper_callback = tamper_sensor_cb
    tamper_cb = MagicMock()
    g90.tamper_callback = tamper_cb

    await g90.listen_notifications()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)

    tamper_sensor_cb.assert_called_once_with()
    tamper_cb.assert_called_once_with(100, 'Hall')
    # Verify the sensor tampered state is set upon receiving the
    # notification
    assert sensor[0].is_tampered is True

    # Signal the second notification is ready, the future has to be re-created
    # as the corresponding callback will be fired again
    future = asyncio.get_running_loop().create_future()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)

    # Verify the sensor tampered state is reset upon disarming
    assert sensor[0].is_tampered is False

    await g90.close_notifications()


@pytest.mark.g90device(
    sent_data=[
        b'ISTART[102,'
        b'[[1,1,1],["Remote",11,0,10,1,0,32,0,0,16,1,0,""]]]IEND\0',
        b'ISTART[117,[256]]IEND\0',
    ],
    notification_data=[
        # Host SOS
        b'[208,[1,1,0,0,"","DUMMYGUID",1734175050,0,[""]]]\0',
        # Remote SOS
        b'[208,[3,11,10,3,"Remote","DUMMYGUID",1734177048,0,[""]]]\0',
    ]
)
async def test_sos_callback(mock_device: DeviceMock) -> None:
    """
    Tests for SOS callback.
    """
    future_sos = asyncio.get_running_loop().create_future()
    future_alarm = asyncio.get_running_loop().create_future()

    sos_cb = MagicMock()
    sos_cb.side_effect = lambda *args: future_sos.set_result(True)
    alarm_cb = MagicMock()
    alarm_cb.side_effect = lambda *args: future_alarm.set_result(True)

    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    await g90.use_local_notifications(
        notifications_local_host=mock_device.notification_host,
        notifications_local_port=mock_device.notification_port
    )
    g90.sos_callback = sos_cb
    g90.alarm_callback = alarm_cb

    await g90.listen_notifications()
    await mock_device.send_next_notification()
    await asyncio.wait([future_sos, future_alarm], timeout=0.1)
    sos_cb.assert_called_once_with(1, 'Host SOS', True)
    alarm_cb.assert_called_once_with(1, 'Host SOS', None)

    sos_cb.reset_mock()
    alarm_cb.reset_mock()
    future_sos = asyncio.get_running_loop().create_future()
    future_alarm = asyncio.get_running_loop().create_future()
    future_button = asyncio.get_running_loop().create_future()
    button_cb = MagicMock()
    button_cb.side_effect = lambda *args: future_button.set_result(True)
    g90.remote_button_press_callback = button_cb
    await mock_device.send_next_notification()
    await asyncio.wait([future_sos, future_alarm, future_button], timeout=0.1)
    sos_cb.assert_called_once_with(11, 'Remote', False)
    alarm_cb.assert_called_once_with(11, 'Remote', None)
    # Button press callback should be called with the remote button state, but
    # only for SOS initiated by the remote
    button_cb.assert_called_once_with(11, 'Remote', G90RemoteButtonStates.SOS)

    await g90.close_notifications()


@pytest.mark.g90device(
    sent_data=[
        b'ISTART[102,'
        b'[[1,1,1],["Remote",11,0,10,1,0,32,0,0,16,1,0,""]]]IEND\0',
        b'ISTART[117,[256]]IEND\0',
    ],
    notification_data=[
        b'[208,[4,11,10,0,"Remote","GA18018B3001021",1734176900,0,[""]]]\0',
    ]
)
async def test_remote_button_callback(mock_device: DeviceMock) -> None:
    """
    Tests for remote button callback.
    """
    future_sensor = asyncio.get_running_loop().create_future()
    future_button = asyncio.get_running_loop().create_future()
    sensor_cb = MagicMock()
    sensor_cb.side_effect = lambda *args: future_sensor.set_result(True)
    button_cb = MagicMock()
    button_cb.side_effect = lambda *args: future_button.set_result(True)

    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    await g90.use_local_notifications(
        notifications_local_host=mock_device.notification_host,
        notifications_local_port=mock_device.notification_port
    )
    g90.sensor_callback = sensor_cb
    g90.remote_button_press_callback = button_cb

    await g90.listen_notifications()
    await mock_device.send_next_notification()
    await asyncio.wait([future_sensor, future_button], timeout=0.1)
    sensor_cb.assert_called_once_with(11, 'Remote', True)
    button_cb.assert_called_once_with(
        11, 'Remote', G90RemoteButtonStates.ARM_AWAY
    )

    await g90.close_notifications()


@pytest.mark.g90device(sent_data=[
    b'ISTARTIEND\0',
])
async def test_arm_away(mock_device: DeviceMock) -> None:
    """
    Tests for arming the device in away mode.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    await g90.arm_away()
    assert await mock_device.recv_data == [
        b'ISTART[101,101,[101,[1]]]IEND\0',
    ]


@pytest.mark.g90device(sent_data=[
    b'ISTARTIEND\0',
])
async def test_arm_home(mock_device: DeviceMock) -> None:
    """
    Tests for arming the device in home mode.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    await g90.arm_home()
    assert await mock_device.recv_data == [
        b'ISTART[101,101,[101,[2]]]IEND\0',
    ]


@pytest.mark.g90device(sent_data=[
    b'ISTARTIEND\0',
])
async def test_disarm(mock_device: DeviceMock) -> None:
    """
    Tests for disarming the device.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    await g90.disarm()
    assert await mock_device.recv_data == [
        b'ISTART[101,101,[101,[3]]]IEND\0',
    ]


@pytest.mark.g90device(
    sent_data=[
        # First command to get alert configuration is from
        # `G90Alarm.get_alert_config()` property
        b"ISTART[117,[1]]IEND\0",
        # Second command for same is invoked by `G90Alarm.set_alert_config`
        # that checks if alert config has been modified externally
        b"ISTART[117,[1]]IEND\0",
        b"ISTARTIEND\0",
        # Simulated list of sensors, which is used to reset door open when
        # arming/tamper flags on those had the flags set when arming
        b'ISTART[102,'
        b'[[3,1,3],["Remote 1",10,0,10,1,0,32,0,0,16,1,0,""],'
        b'["Remote 2",11,0,10,1,0,32,0,0,16,1,0,""],'
        b'["Cord 1",12,0,126,1,0,32,0,5,16,1,0,""]'
        b']]IEND\0',
    ],
    notification_data=[
        b'[170,[1,[1]]]\0',
    ]
)
async def test_sms_alert_when_armed(mock_device: DeviceMock) -> None:
    """
    Tests for enabling SMS alerts when device is armed.
    """
    future = asyncio.get_running_loop().create_future()
    armdisarm_cb = MagicMock()
    armdisarm_cb.side_effect = lambda *args: future.set_result(True)
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    await g90.use_local_notifications(
        notifications_local_host=mock_device.notification_host,
        notifications_local_port=mock_device.notification_port
    )
    g90.armdisarm_callback = armdisarm_cb
    g90.sms_alert_when_armed = True
    await g90.listen_notifications()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    await g90.close_notifications()
    assert set([
        b'ISTART[117,117,""]IEND\0',
        b'ISTART[117,117,""]IEND\0',
        b"ISTART[116,116,[116,[513]]]IEND\0",
    ]).issubset(set(await mock_device.recv_data))


@pytest.mark.g90device(
    sent_data=[
        # See above for the clarification on command sequence
        b"ISTART[117,[513]]IEND\0",
        b"ISTART[117,[513]]IEND\0",
        b"ISTARTIEND\0",
        b'ISTART[102,'
        b'[[3,1,3],["Remote 1",10,0,10,1,0,32,0,0,16,1,0,""],'
        b'["Remote 2",11,0,10,1,0,32,0,0,16,1,0,""],'
        b'["Cord 1",12,0,126,1,0,32,0,5,16,1,0,""]'
        b']]IEND\0',
    ],
    notification_data=[
        b'[170,[1,[3]]]\0',
    ]
)
async def test_sms_alert_when_disarmed(mock_device: DeviceMock) -> None:
    """
    Tests for disabling SMS alerts when device is disarmed.
    """
    future = asyncio.get_running_loop().create_future()
    armdisarm_cb = MagicMock()
    armdisarm_cb.side_effect = lambda *args: future.set_result(True)
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    await g90.use_local_notifications(
        notifications_local_host=mock_device.notification_host,
        notifications_local_port=mock_device.notification_port
    )
    g90.armdisarm_callback = armdisarm_cb
    g90.sms_alert_when_armed = True
    await g90.listen_notifications()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    await g90.close_notifications()
    assert set([
        b'ISTART[117,117,""]IEND\0',
        b'ISTART[117,117,""]IEND\0',
        b"ISTART[116,116,[116,[1]]]IEND\0",
    ]).issubset(set(await mock_device.recv_data))


@pytest.mark.g90device(sent_data=[
    b'ISTART[138,'
    b'[[1,1,1],["Water",10,0,7,0,0,33,0,0,17,1,0,""]'
    b']]IEND\0',
    b"ISTARTIEND\0",
])
async def test_device_unsupported_disable(mock_device: DeviceMock) -> None:
    """
    Tests for disabling an unsupported device.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    devices = await g90.get_devices()
    prop_devices = await g90.devices
    assert devices == prop_devices
    assert devices[0].enabled
    await devices[0].set_enabled(False)
    assert await mock_device.recv_data == [
        b'ISTART[138,138,[138,[1,10]]]IEND\0',
    ]


@pytest.mark.g90device(sent_data=[
    b'ISTART[138,'
    b'[[1,1,1],["Water",10,0,7,0,0,33,0,0,17,1,0,""]'
    b']]IEND\0',
    b"ISTARTIEND\0",
])
async def test_device_delete(mock_device: DeviceMock) -> None:
    """
    Tests for deleting the device.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    devices = await g90.get_devices()
    await devices[0].delete()
    assert devices[0].is_unavailable
    assert await mock_device.recv_data == [
        b'ISTART[138,138,[138,[1,10]]]IEND\0',
        b'ISTART[136,136,[136,[10]]]IEND\0',
    ]

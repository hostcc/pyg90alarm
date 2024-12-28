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
from pyg90alarm.host_info import (
    G90HostInfo, G90HostInfoGsmStatus, G90HostInfoWifiStatus,
)
from pyg90alarm.entities.sensor import (
    G90Sensor,
)
from pyg90alarm.entities.device import (
    G90Device,
)

from pyg90alarm.host_status import (
    G90HostStatus,
)
from pyg90alarm.user_data_crc import (
    G90UserDataCRC,
)
from pyg90alarm.config import (
    G90AlertConfigFlags,
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

    assert mock_device.recv_data == [b'ISTART[100,100,""]IEND\0']
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

    assert mock_device.recv_data == [b'ISTART[206,206,""]IEND\0']
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
    assert mock_device.recv_data == [
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
    assert mock_device.recv_data == [
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
    g90.paginated_result.assert_called_once()
    # While `pylint` demands use of generator, the comprehension is used
    # instead for ease of trroubleshooting test failures as it will show the
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
    assert mock_device.recv_data == [
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
    assert mock_device.recv_data == [
        b'ISTART[138,138,[138,[1,10]]]IEND\0',
        b'ISTART[137,137,[137,[10,0,0]]]IEND\0',
        b'ISTART[137,137,[137,[10,1,0]]]IEND\0',
    ]


@pytest.mark.g90device(sent_data=[
    b'ISTART[102,'
    b'[[1,1,1],["Remote",10,0,10,1,0,32,0,0,16,1,0,""]]]IEND\0',
])
async def test_single_sensor(mock_device: DeviceMock) -> None:
    """
    Tests for retrieving single sensor from the panel.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    sensors = await g90.get_sensors()
    prop_sensors = await g90.sensors

    assert sensors == prop_sensors
    assert mock_device.recv_data == [
        b'ISTART[102,102,[102,[1,10]]]IEND\0',
    ]
    assert len(sensors) == 1
    assert isinstance(sensors, list)
    assert isinstance(sensors[0], G90Sensor)
    assert sensors[0].name == 'Remote'
    assert sensors[0].index == 10
    assert isinstance(sensors[0]._asdict(), dict)


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
    g90.paginated_result.assert_called_once()
    # pylint: disable=use-a-generator
    assert all([len(x) == 1 for x in res])


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

    sensors = await g90.get_sensors()
    prop_sensors = await g90.sensors

    assert sensors == prop_sensors
    assert mock_device.recv_data == [
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

    sensors = await g90.get_sensors()
    prop_sensors = await g90.sensors

    assert sensors == prop_sensors
    assert mock_device.recv_data == [
        b'ISTART[102,102,[102,[1,10]]]IEND\0',
        b'ISTART[102,102,[102,[11,11]]]IEND\0',
    ]
    assert len(sensors) == 11
    assert isinstance(sensors, list)
    assert isinstance(sensors[0], G90Sensor)
    assert sensors[0].name == 'Remote 1'
    assert sensors[0].index == 10


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
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port,
                   reset_occupancy_interval=reset_interval,
                   notifications_local_host=mock_device.notification_host,
                   notifications_local_port=mock_device.notification_port)

    sensors = await g90.get_sensors()
    prop_sensors = await g90.sensors

    assert sensors == prop_sensors
    future = asyncio.get_running_loop().create_future()
    sensor = [x for x in sensors if x.index == 10 and x.name == 'Remote']
    sensor[0].state_callback = lambda *args: future.set_result(True)

    await g90.listen_device_notifications()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    g90.close_device_notifications()
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
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port,
                   notifications_local_host=mock_device.notification_host,
                   notifications_local_port=mock_device.notification_port)

    sensors = await g90.get_sensors()
    prop_sensors = await g90.sensors

    assert sensors == prop_sensors
    future = asyncio.get_running_loop().create_future()
    sensor = [x for x in sensors if x.index == 26 and x.name == 'Remote']
    low_battery_sensor_cb = MagicMock()
    low_battery_sensor_cb.side_effect = lambda *args: future.set_result(True)
    sensor[0].low_battery_callback = low_battery_sensor_cb
    low_battery_cb = MagicMock()
    g90.low_battery_callback = low_battery_cb

    await g90.listen_device_notifications()
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

    g90.close_device_notifications()


@pytest.mark.g90device(
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
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port,
                   notifications_local_host=mock_device.notification_host,
                   notifications_local_port=mock_device.notification_port)
    g90.armdisarm_callback = armdisarm_cb
    await g90.listen_device_notifications()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    g90.close_device_notifications()
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

    g90 = G90Alarm(host=mock_device.host, port=mock_device.port,
                   notifications_local_host=mock_device.notification_host,
                   notifications_local_port=mock_device.notification_port)
    g90.door_open_close_callback = door_open_close_cb

    # Simulate two device alerts - for opening (this one) and then closing the
    # door (see below)
    await g90.listen_device_notifications()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    # Corresponding sensor should turn to occupied (=door opened)
    sensors = await g90.get_sensors()
    prop_sensors = await g90.sensors
    assert sensors == prop_sensors
    assert sensors[0].occupancy

    # Simulate second device alert for door close
    await mock_device.send_next_notification()
    # Signal the second alert is ready, the future has to be re-created as
    # the corresponding callback will be fired again
    future = asyncio.get_running_loop().create_future()

    await asyncio.wait([future], timeout=0.1)
    # The sensor should become inactive (=door closed)
    sensors = await g90.get_sensors()
    prop_sensors = await g90.sensors
    assert sensors == prop_sensors
    assert not sensors[0].occupancy

    g90.close_device_notifications()


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

    g90 = G90Alarm(host=mock_device.host, port=mock_device.port,
                   notifications_local_host=mock_device.notification_host,
                   notifications_local_port=mock_device.notification_port)
    sensors = await g90.get_sensors()
    # Set extra data for the 1st sensor
    sensors[0].extra_data = 'Dummy extra data'

    g90.alarm_callback = alarm_cb
    await g90.listen_device_notifications()
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

    g90.close_device_notifications()


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

    g90 = G90Alarm(host=mock_device.host, port=mock_device.port,
                   notifications_local_host=mock_device.notification_host,
                   notifications_local_port=mock_device.notification_port)
    g90.sos_callback = sos_cb
    g90.alarm_callback = alarm_cb

    await g90.listen_device_notifications()
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

    g90.close_device_notifications()


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

    g90 = G90Alarm(host=mock_device.host, port=mock_device.port,
                   notifications_local_host=mock_device.notification_host,
                   notifications_local_port=mock_device.notification_port)
    g90.sensor_callback = sensor_cb
    g90.remote_button_press_callback = button_cb

    await g90.listen_device_notifications()
    await mock_device.send_next_notification()
    await asyncio.wait([future_sensor, future_button], timeout=0.1)
    sensor_cb.assert_called_once_with(11, 'Remote', True)
    button_cb.assert_called_once_with(
        11, 'Remote', G90RemoteButtonStates.ARM_AWAY
    )

    g90.close_device_notifications()


@pytest.mark.g90device(sent_data=[
    b'ISTARTIEND\0',
])
async def test_arm_away(mock_device: DeviceMock) -> None:
    """
    Tests for arming the device in away mode.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    await g90.arm_away()
    assert mock_device.recv_data == [
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
    assert mock_device.recv_data == [
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
    assert mock_device.recv_data == [
        b'ISTART[101,101,[101,[3]]]IEND\0',
    ]


@pytest.mark.g90device(sent_data=[
    b'ISTART[117,[1]]IEND\0',
])
async def test_alert_config(mock_device: DeviceMock) -> None:
    """
    Tests for retrieving alert configuration from the device.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    config = await g90.get_alert_config()
    prop_config = await g90.alert_config
    assert config == prop_config
    assert mock_device.recv_data == [b'ISTART[117,117,""]IEND\0']
    assert isinstance(config, G90AlertConfigFlags)


@pytest.mark.g90device(sent_data=[
    b"ISTART[117,[1]]IEND\0",
    b"ISTART[117,[3]]IEND\0",
    b"ISTARTIEND\0",
])
async def test_set_alert_config(mock_device: DeviceMock) -> None:
    """
    Tests for setting alert configuration to the the device.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    await g90.set_alert_config(
        await g90.get_alert_config()
        | G90AlertConfigFlags.AC_POWER_FAILURE  # noqa:W503
        | G90AlertConfigFlags.HOST_LOW_VOLTAGE  # noqa:W503
    )
    assert mock_device.recv_data == [
        b'ISTART[117,117,""]IEND\0',
        b'ISTART[117,117,""]IEND\0',
        b"ISTART[116,116,[116,[9]]]IEND\0",
    ]
    # Validate we retrieve same alert configuration just has been set
    assert await g90.get_alert_config() == (
        G90AlertConfigFlags.AC_POWER_FAILURE
        | G90AlertConfigFlags.HOST_LOW_VOLTAGE  # noqa:W503
    )


@pytest.mark.g90device(
    sent_data=[
        # First command to get alert configuration is from
        # `G90Alarm.get_alert_config()` property
        b"ISTART[117,[1]]IEND\0",
        # Second command for same is invoked by `G90Alarm.set_alert_config`
        # that checks if alert config has been modified externally
        b"ISTART[117,[1]]IEND\0",
        b"ISTARTIEND\0",
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
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port,
                   notifications_local_host=mock_device.notification_host,
                   notifications_local_port=mock_device.notification_port)
    g90.armdisarm_callback = armdisarm_cb
    g90.sms_alert_when_armed = True
    await g90.listen_device_notifications()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    g90.close_device_notifications()
    assert mock_device.recv_data == [
        b'ISTART[117,117,""]IEND\0',
        b'ISTART[117,117,""]IEND\0',
        b"ISTART[116,116,[116,[513]]]IEND\0",
    ]


@pytest.mark.g90device(
    sent_data=[
        # See above for the clarification on command sequence
        b"ISTART[117,[513]]IEND\0",
        b"ISTART[117,[513]]IEND\0",
        b"ISTARTIEND\0",
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
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port,
                   notifications_local_host=mock_device.notification_host,
                   notifications_local_port=mock_device.notification_port)
    g90.armdisarm_callback = armdisarm_cb
    g90.sms_alert_when_armed = True
    await g90.listen_device_notifications()
    await mock_device.send_next_notification()
    await asyncio.wait([future], timeout=0.1)
    g90.close_device_notifications()
    assert mock_device.recv_data == [
        b'ISTART[117,117,""]IEND\0',
        b'ISTART[117,117,""]IEND\0',
        b"ISTART[116,116,[116,[1]]]IEND\0",
    ]


@pytest.mark.g90device(sent_data=[
    b'ISTART[102,'
    b'[[2,1,2],'
    b'["Night Light1",11,0,138,0,0,33,0,0,17,1,0,""],'
    b'["Night Light2",10,0,138,0,0,33,0,0,17,1,0,""]'
    b']]IEND\0',
    b'ISTART[102,'
    b'[[2,2,1],'
    b'["Night Light2",10,0,138,0,0,33,0,0,17,1,0,""]'
    b']]IEND\0',
    b"ISTARTIEND\0",
])
async def test_sensor_disable(mock_device: DeviceMock) -> None:
    """
    Tests for disabling a sensor.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    sensors = await g90.get_sensors()
    prop_sensors = await g90.sensors
    assert sensors == prop_sensors
    assert sensors[1].enabled
    await sensors[1].set_enabled(False)
    assert not sensors[1].enabled
    assert mock_device.recv_data == [
        b'ISTART[102,102,[102,[1,10]]]IEND\0',
        b'ISTART[102,102,[102,[2,2]]]IEND\0',
        b'ISTART[103,103,[103,'
        b'["Night Light2",10,0,138,0,0,32,0,0,17,1,0,2,"060A0600"]'
        b']]IEND\0',
    ]


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

    sensors = await g90.get_sensors()
    prop_sensors = await g90.sensors
    assert sensors == prop_sensors
    assert sensors[1].enabled
    await sensors[1].set_enabled(False)
    assert sensors[1].enabled
    assert mock_device.recv_data == [
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

    sensors = await g90.get_sensors()
    prop_sensors = await g90.sensors
    assert sensors == prop_sensors
    assert sensors[0].enabled
    await sensors[0].set_enabled(False)
    assert mock_device.recv_data == [
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

    sensors = await g90.get_sensors()
    assert sensors[1].enabled
    await sensors[1].set_enabled(False)
    assert sensors[1].enabled
    assert mock_device.recv_data == [
        b'ISTART[102,102,[102,[1,10]]]IEND\0',
        b'ISTART[102,102,[102,[2,2]]]IEND\0',
    ]


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
    assert mock_device.recv_data == [
        b'ISTART[138,138,[138,[1,10]]]IEND\0',
    ]

"""
Tests for G90History class.
"""
import asyncio
from itertools import cycle
from unittest.mock import MagicMock, DEFAULT, ANY
import pytest
from pytest import LogCaptureFixture

from pyg90alarm.alarm import (
    G90Alarm,
)
from pyg90alarm.history import (
    G90History,
)
from pyg90alarm.const import (
    G90AlertTypes, G90AlertSources,
    G90HistoryStates,
)
from pyg90alarm.exceptions import (
    G90TimeoutError,
)

from .device_mock import DeviceMock


@pytest.mark.g90device(sent_data=[
    b'ISTART[200,[[50,1,7],'
    b'[3,33,1,1,"Sensor 1",1630147285,""],'
    b'[2,3,0,0,"",1630142877,""],'
    b'[2,5,0,0,"",1630142871,""],'
    b'[2,4,0,0,"",1630142757,""],'
    b'[3,100,1,1,"Sensor 2",1630142297,""],'
    b'[3,1,10,3,"Remote",1734177048,""],'
    b'[1,1,0,0,"",1734175049,""]'
    b']]IEND\0',
])
async def test_history(mock_device: DeviceMock) -> None:
    """
    Tests for retrieving history from the device.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    history = await g90.history(count=7)
    assert len(history) == 7
    assert isinstance(history[0], G90History)
    assert mock_device.recv_data == [
        b'ISTART[200,200,[200,[1,7]]]IEND\0',
    ]
    assert all(isinstance(h._asdict(), dict) for h in history)
    assert [h._asdict() for h in history] == [
        {
            'datetime': ANY,
            'sensor_idx': None,
            'sensor_name': 'Remote',
            'source': G90AlertSources.REMOTE,
            'state': G90HistoryStates.REMOTE_BUTTON_SOS,
            'type': G90AlertTypes.ALARM,
        },
        {
            'datetime': ANY,
            'sensor_idx': None,
            'sensor_name': None,
            'source': G90AlertSources.DEVICE,
            'state': None,
            'type': G90AlertTypes.HOST_SOS,
        },
        {
            'type': G90AlertTypes.ALARM,
            'source': G90AlertSources.SENSOR,
            'state': G90HistoryStates.DOOR_OPEN,
            'sensor_name': 'Sensor 1',
            'sensor_idx': 33,
            'datetime': ANY,
        },
        {
            'type': G90AlertTypes.STATE_CHANGE,
            'source': G90AlertSources.DEVICE,
            'state': G90HistoryStates.DISARM,
            'sensor_idx': None,
            'sensor_name': None,
            'datetime': ANY,
        },
        {
            'type': G90AlertTypes.STATE_CHANGE,
            'source': G90AlertSources.DEVICE,
            'state': G90HistoryStates.ARM_HOME,
            'sensor_idx': None,
            'sensor_name': None,
            'datetime': ANY,
        },
        {
            'type': G90AlertTypes.STATE_CHANGE,
            'source': G90AlertSources.DEVICE,
            'state': G90HistoryStates.ARM_AWAY,
            'sensor_idx': None,
            'sensor_name': None,
            'datetime': ANY,
        },
        {
            'type': G90AlertTypes.ALARM,
            'source': G90AlertSources.SENSOR,
            'state': G90HistoryStates.DOOR_OPEN,
            'sensor_name': 'Sensor 2',
            'sensor_idx': 100,
            'datetime': ANY,
        },
    ]


@pytest.mark.g90device(sent_data=[
    b'ISTART[200,[[3,1,3],'
    # Wrong state
    b'[3,33,7,254,"Sensor 1",1630147285,""],'
    # Wrong source
    b'[2,33,254,1,"Sensor 1",1630147285,""],'
    # Wrong type
    b'[254,33,1,1,"Sensor 1",1630147285,""]'
    b']]IEND\0',
])
async def test_history_parsing_error(mock_device: DeviceMock) -> None:
    """
    Tests for processing history from the device, when the parsing error
    occurs.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    history = await g90.history(count=5)
    assert len(history) == 3
    assert isinstance(history[0], G90History)
    assert isinstance(history[0]._asdict(), dict)
    # Wrong entry element should result in corresponding key having 'None'
    # value
    assert history[0]._asdict()['state'] is None
    assert history[1]._asdict()['source'] is None
    assert history[2]._asdict()['type'] is None


@pytest.mark.g90device(sent_data=[
    # Host info
    b'ISTART[206,'
    b'["DUMMYGUID","DUMMYPRODUCT",'
    b'"1.2","1.1","206","206",3,3,0,2,"4242",50,100]]IEND\0',
    # Simulate empty history initially
    b'ISTART[200,[[0,0,0]]]IEND\0',
    # The history records will be used to remember the timestamp of most recent
    # one
    b'ISTART[200,[[1,1,1],'
    b'[2,5,0,0,"",1630142871,""]'
    b']]IEND\0',
    # The records will be used to simulate the device alerts, but only for
    # those newer that one above
    b'ISTART[200,[[3,1,3],'
    b'[3,33,1,1,"Sensor 1",1630147285,""],'
    b'[2,3,0,0,"",1630142877,""],'
    b'[2,5,0,0,"",1630142871,""]'
    b']]IEND\0',
    # Simulated list of devices, will be used by alarm callback
    b'ISTART[102,'
    b'[[2,1,2],'
    b'["Sensor 1",33,0,138,0,0,33,0,0,17,1,0,""],'
    b'["Sensor 2",100,0,138,0,0,33,0,0,17,1,0,""]'
    b']]IEND\0',
    # Alert configuration, used by sensor activity callback invoked when
    # handling alarm
    b'ISTART[117,[256]]IEND\0',
])
async def test_simulate_alerts_from_history(mock_device: DeviceMock) -> None:
    """
    Tests for simulating device alerts from the history.
    """
    # Callback handlers for alarm and arm/disarm, just setting their
    # corresponding future when called
    future_alarm = asyncio.get_running_loop().create_future()
    future_armdisarm = asyncio.get_running_loop().create_future()
    alarm_cb = MagicMock()
    alarm_cb.side_effect = lambda *args: future_alarm.set_result(True)
    armdisarm_cb = MagicMock()
    armdisarm_cb.side_effect = lambda *args: future_armdisarm.set_result(True)

    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    # Call the method to store device GUID, so that its validation in
    # `G90DeviceNotifications._handle_alert()` is involved
    await g90.get_host_info()
    g90.alarm_callback = alarm_cb
    g90.armdisarm_callback = armdisarm_cb
    # Simulate device timeout exception every 2nd call to `G90Alarm.history()`
    # method - the processing should still result in callbacks invoked
    g90.history = MagicMock(wraps=g90.history)  # type: ignore[method-assign]
    g90.history.side_effect = cycle([G90TimeoutError, DEFAULT])
    # Simulate device notifications from the history data above, small interval
    # is set to shorten the test run time
    await g90.start_simulating_alerts_from_history(interval=0.1)
    # Both callbacks should be called, wait for that - the timeout should be
    # sufficient for extra iterations in the method under test, to accommodate
    # the simulated exceptions above
    await asyncio.wait([future_alarm, future_armdisarm], timeout=0.5)
    # Stop simulating the alert from history
    await g90.stop_simulating_alerts_from_history()

    sensors = await g90.get_sensors()
    # Ensure callbacks have been called and with expected arguments
    alarm_cb.assert_called_once_with(33, 'Sensor 1', None)
    armdisarm_cb.assert_called_once_with(3)
    assert sensors[0].occupancy is True


async def test_simulate_alerts_from_history_exception(
    mock_device: DeviceMock, caplog: LogCaptureFixture
) -> None:
    """
    Tests for simulating device alerts from the history, when an exception is
    raised when interacting with the device.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    # Simulate a generic error fetching history entries
    g90.history = MagicMock()  # type: ignore[method-assign]
    simulated_error = Exception('dummy error')
    g90.history.side_effect = simulated_error
    caplog.set_level('WARNING')
    # Start simulating alerts from history
    await g90.start_simulating_alerts_from_history()
    # Allow task to settle
    await asyncio.sleep(0.1)
    # Verify the task is no longer running and resulted in particular exception
    task = g90._alert_simulation_task  # pylint:disable=protected-access
    assert task is not None
    assert task.exception() == simulated_error
    assert task.done()
    # Stop simulating the alert from history
    await g90.stop_simulating_alerts_from_history()
    # Verify the error logged
    assert ''.join(caplog.messages).startswith(
        'Exception simulating device alerts from history'
    )

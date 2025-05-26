"""
Tests for the G90Alarm class and its methods related to devices.
"""
import asyncio
from itertools import cycle
from contextlib import nullcontext, AbstractContextManager
from unittest.mock import MagicMock
import pytest
from pyg90alarm import (
    G90Alarm, G90Device, G90EntityRegistrationError,
)
from .device_mock import DeviceMock


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
    # Ensure only corresponding number of exchanges with the panel
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


@pytest.mark.parametrize(
    'expected_exception', [
        # Normal operation, no exception expected
        pytest.param(
            nullcontext(),
            id='register-device-ok',
            marks=pytest.mark.g90device(sent_data=[
                b'ISTART[138,'
                b'[[1,1,1],'
                b'["Existing socket",11,0,128,3,0,32,0,0,16,1,0,""]'
                b']]IEND\0',
                b'ISTARTIEND\0',
                b'ISTART[162,[0]]IEND\0',
                b'ISTART[138,'
                b'[[1,1,2],'
                b'["Existing socket",11,0,128,3,0,32,0,0,16,1,0,""],'
                b'["Test socket",0,0,128,3,0,32,0,0,16,1,0,""]'
                b']]IEND\0',
            ]),
        ),
        # Operation simulating the panel responded with no index for the new
        # device
        pytest.param(
            pytest.raises(G90EntityRegistrationError),
            id='register-device-no-index-received',
            marks=pytest.mark.g90device(sent_data=[
                b'ISTART[138,'
                b'[[1,1,1],'
                b'["Existing socket",11,0,128,3,0,32,0,0,16,1,0,""]'
                b']]IEND\0',
                b'ISTARTIEND\0',
                b'ISTARTIEND\0',
            ]),
        ),
        # Operation simulating panel responded with an index for the new
        # device, but such entity isn't found in the devices list
        pytest.param(
            pytest.raises(G90EntityRegistrationError),
            id='register-device-not-found',
            marks=pytest.mark.g90device(sent_data=[
                b'ISTART[138,'
                b'[[1,1,1],'
                b'["Existing socket",11,0,128,3,0,32,0,0,16,1,0,""]'
                b']]IEND\0',
                b'ISTARTIEND\0',
                b'ISTART[162,[999]]IEND\0',
                b'ISTART[138,'
                b'[[1,1,2],'
                b'["Existing socket",11,0,128,3,0,32,0,0,16,1,0,""],'
                b'["Test socket",0,0,128,3,0,32,0,0,16,1,0,""]'
                b']]IEND\0',
            ]),
        ),
    ]
)
async def test_device_register(
    expected_exception: AbstractContextManager[Exception],
    mock_device: DeviceMock
) -> None:
    """
    Tests for adding a new device to the panel.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    with expected_exception:
        # Attempt to register a new device
        added_device = await g90.register_device(
            'Socket: S07', 'Test socket', timeout=1
        )

        # Verify sequence of commands sent to the panel
        assert await mock_device.recv_data == [
            b'ISTART[138,138,[138,[1,10]]]IEND\0',
            b'ISTART[134,134,[134,'
            b'["Test socket",0,0,128,3,0,1,1190,0,17,1,0,2,"060A0600"]'
            b']]IEND\0',
            b'ISTART[162,162,[162,[1]]]IEND\0',
            b'ISTART[138,138,[138,[1,10]]]IEND\0',
        ]

        devices = await g90.devices
        # Verify the device list contains the new device
        assert len(devices) == 2
        new_device = devices[1]
        assert isinstance(new_device, G90Device)
        assert added_device is new_device
        assert new_device.name == "Test socket"
        assert new_device.index == 0
        assert new_device.type == 128


@pytest.mark.g90device(sent_data=[
    b'ISTART[138,'
    b'[[1,1,1],["Existing socket",11,0,128,3,0,32,0,0,16,1,0,""]]]IEND\0',
    b'ISTARTIEND\0',
    b'ISTART[162,[0]]IEND\0',
    b'ISTART[138,'
    b'[[1,1,2],'
    b'["Existing socket",11,0,128,3,0,32,0,0,16,1,0,""],'
    b'["Test socket",0,0,128,0,0,1,1480,0,17,4,0,""]'
    b']]IEND\0',
])
async def test_multinode_device_register(mock_device: DeviceMock) -> None:
    """
    Tests for adding a new multi-node device to the panel.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)
    # Attempt to register a new multi-node device
    await g90.register_device('Socket: JDQ', 'Test socket')

    # Verify sequence of commands sent to the panel
    assert await mock_device.recv_data == [
        b'ISTART[138,138,[138,[1,10]]]IEND\0',
        b'ISTART[134,134,[134,'
        b'["Test socket",0,0,128,0,0,1,1480,0,17,4,0,2,"0707070B0B0D0D0E0E00"]'
        b']]IEND\0',
        b'ISTART[162,162,[162,[1]]]IEND\0',
        b'ISTART[138,138,[138,[1,10]]]IEND\0',
    ]

    devices = await g90.devices
    # Verify the device list contains the new multi-node device
    assert len(devices) == 5
    new_device = devices[1]
    assert isinstance(new_device, G90Device)
    assert devices[1].name == "Test socket#1"


@pytest.mark.g90device(sent_data=[
    b'ISTART[138,'
    b'[[1,1,1],["Switch",10,0,10,1,0,32,0,0,16,1,0,""]]]IEND\0',
    b'ISTART[138,'
    b'[[1,1,1],["Switch",10,0,10,1,0,32,0,0,16,1,0,""]]]IEND\0',
])
async def test_device_update(mock_device: DeviceMock) -> None:
    """
    Tests updating the device and callback assocaited.
    """
    g90 = G90Alarm(host=mock_device.host, port=mock_device.port)

    # Set up the sensor list change callback to be called when the sensor
    # list is updated
    list_change_cb = MagicMock()
    g90.device_list_change_callback = list_change_cb
    future = asyncio.get_running_loop().create_future()
    list_change_cb.side_effect = (
        lambda *args: future.set_result(True)
    )

    # Trigger device list update
    devices = await g90.get_devices()

    # Verify the callback is called with correct parameters, indicating the
    # device has been added to the list
    await asyncio.wait([future], timeout=0.1)
    list_change_cb.assert_called_once_with(devices[0], True)

    # Subsequently retrieving the list of devices should result in same
    # callback invoked, but with different parameters
    future = asyncio.get_running_loop().create_future()
    await g90.get_devices()
    await asyncio.wait([future], timeout=0.1)
    list_change_cb.assert_called_with(devices[0], False)

'''
Tests for G90PaginatedCommand class
'''
import pytest

from pyg90alarm.paginated_cmd import (
    G90PaginatedCommand,
)
from pyg90alarm.exceptions import G90Error
from pyg90alarm.const import G90Commands

from .device_mock import DeviceMock


@pytest.mark.g90device(sent_data=[
    b'ISTART[102,[[]]]IEND\0',
])
async def test_missing_pagination_header(mock_device: DeviceMock) -> None:
    '''
    Verifies that missing pagination header raises an exception.
    '''
    g90 = G90PaginatedCommand(
        host=mock_device.host, port=mock_device.port,
        code=G90Commands.GETSENSORLIST,
        start=1, end=1
    )

    with pytest.raises(
        G90Error,
        match=(
            r"Wrong pagination data \[\] -"
            ' .+ missing 3 required positional arguments:'
            " 'total', 'start', and 'nelems'"
        )
    ):
        await g90.process()

    assert mock_device.recv_data == [
        b'ISTART[102,102,[102,[1,1]]]IEND\0'
    ]


@pytest.mark.g90device(sent_data=[
    b'ISTART[102,[[1,1,1]]]IEND\0',
])
async def test_no_paginated_data(mock_device: DeviceMock) -> None:
    '''
    Verifies that no paginated data raises an exception.
    '''
    g90 = G90PaginatedCommand(
        host=mock_device.host, port=mock_device.port,
        code=G90Commands.GETSENSORLIST,
        start=1, end=1
    )

    with pytest.raises(
        G90Error,
        match=(
            'Truncated data provided in paginated response -'
            ' expected 1 entities as per response, received 0'
        )
    ):
        await g90.process()
    assert mock_device.recv_data == [
        b'ISTART[102,102,[102,[1,1]]]IEND\0'
    ]


@pytest.mark.g90device(sent_data=[
    b'ISTART[102,[[1,1,1],[""]]]IEND\0',
])
async def test_partial_paginated_data(mock_device: DeviceMock) -> None:
    '''
    Verifies that paginated data shorter than requested is properly handled.
    '''
    g90 = G90PaginatedCommand(
        host=mock_device.host, port=mock_device.port,
        code=G90Commands.GETSENSORLIST,
        start=1, end=2
    )

    await g90.process()
    assert mock_device.recv_data == [
        b'ISTART[102,102,[102,[1,2]]]IEND\0'
    ]


@pytest.mark.g90device(sent_data=[
    b'ISTART[102,[[2,1,2],[""],[""]]]IEND\0',
])
async def test_extra_paginated_data(mock_device: DeviceMock) -> None:
    '''
    Verifies that extra paginated data raises an exception.
    '''
    g90 = G90PaginatedCommand(
        host=mock_device.host, port=mock_device.port,
        code=G90Commands.GETSENSORLIST,
        start=1, end=1
    )

    with pytest.raises(
        G90Error,
        match=(
            'Extra data provided in paginated response -'
            ' expected 1 entities as per request, received 2'
        )
    ):
        await g90.process()
    assert mock_device.recv_data == [
        b'ISTART[102,102,[102,[1,1]]]IEND\0'
    ]

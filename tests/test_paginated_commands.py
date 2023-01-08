import sys
import pytest
sys.path.extend(['src', '../src'])

from pyg90alarm.paginated_cmd import (   # noqa:E402
    G90PaginatedCommand,
)
from pyg90alarm.exceptions import G90Error  # noqa:E402


async def test_missing_pagination(mock_sock):
    g90 = G90PaginatedCommand(
        host='mocked', port=12345, code=102, start=1, end=1,
        sock=mock_sock)
    mock_sock.recvfrom.return_value = (
        b'ISTART[102,[[]]]IEND\0', ('mocked', 12345))

    with pytest.raises(
        G90Error,
        match=(
            r"Wrong pagination data \[\] -"
            ' .+ missing 3 required positional arguments:'
            " 'total', 'start', and 'count'"
        )
    ):
        await g90.process()

    mock_sock.send.assert_called_with(
        b'ISTART[102,102,[102,[1,1]]]IEND\0'
    )


async def test_no_paginated_data(mock_sock):
    g90 = G90PaginatedCommand(
        host='mocked', port=12345, code=102, start=1, end=1,
        sock=mock_sock)
    mock_sock.recvfrom.return_value = (
        b'ISTART[102,[[1,1,1]]]IEND\0', ('mocked', 12345))

    with pytest.raises(
        G90Error,
        match=(
            'Truncated data provided in paginated response -'
            ' expected 1 entities as per response, received 0'
        )
    ):
        await g90.process()
    mock_sock.send.assert_called_with(
        b'ISTART[102,102,[102,[1,1]]]IEND\0'
    )


async def test_partial_paginated_data(mock_sock):
    g90 = G90PaginatedCommand(
        host='mocked', port=12345, code=102, start=1, end=2,
        sock=mock_sock)
    mock_sock.recvfrom.return_value = (
        b'ISTART[102,[[1,1,1],[""]]]IEND\0', ('mocked', 12345))

    await g90.process()
    mock_sock.send.assert_called_with(
        b'ISTART[102,102,[102,[1,2]]]IEND\0'
    )


async def test_extra_paginated_data(mock_sock):
    g90 = G90PaginatedCommand(
        host='mocked', port=12345, code=102, start=1, end=1,
        sock=mock_sock)
    mock_sock.recvfrom.return_value = (
        b'ISTART[102,[[2,1,2],[""],[""]]]IEND\0', ('mocked', 12345))

    with pytest.raises(
        G90Error,
        match=(
            'Extra data provided in paginated response -'
            ' expected 1 entities as per request, received 2'
        )
    ):
        await g90.process()
    mock_sock.send.assert_called_with(
        b'ISTART[102,102,[102,[1,1]]]IEND\0'
    )

import sys
from unittest.mock import call
import re
import pytest

sys.path.extend(['src', '../src'])

from pyg90alarm.base_cmd import (  # noqa:E402
    G90BaseCommand
)
from pyg90alarm.exceptions import (G90Error, G90TimeoutError)  # noqa:E402


async def test_network_unreachable(mock_sock):
    g90 = G90BaseCommand(
        host='mocked', port=12345, code=206, sock=mock_sock)
    mock_sock.recvfrom.side_effect = OSError('Host unreachable')

    with pytest.raises(OSError, match="Host unreachable"):
        await g90.process()


async def test_wrong_host(mock_sock):
    g90 = G90BaseCommand(
        host='mocked', port=12345, code=206, sock=mock_sock)
    mock_sock.recvfrom.return_value = (
        b'ISTARTIEND\0', ('another_host', 12345))

    with pytest.raises(
        G90Error,
        match=(
            'Received response from wrong host another_host,'
            ' expected from mocked'
        )
    ):
        await g90.process()


async def test_wrong_port(mock_sock):
    g90 = G90BaseCommand(
        host='mocked', port=12345, code=206, sock=mock_sock)
    mock_sock.recvfrom.return_value = (
        b'ISTARTIEND\0', ('mocked', 54321))

    with pytest.raises(
        G90Error,
        match='Received response from wrong port 54321, expected from 12345'
    ):
        await g90.process()


async def test_timeout(mock_sock):
    g90 = G90BaseCommand(
        host='mocked', port=12345, code=206,
        timeout=0.1, retries=2, sock=mock_sock)
    mock_sock.recvfrom.return_value = (b'', ('mocked', 12345))

    with pytest.raises(G90TimeoutError):
        await g90.process()
    mock_sock.send.assert_has_calls([
        call(b'ISTART[206,206,""]IEND\0'),
        call(b'ISTART[206,206,""]IEND\0'),
    ])


async def test_wrong_format(mock_sock):
    g90 = G90BaseCommand(
        host='mocked', port=12345, code=206, sock=mock_sock)
    mock_sock.recvfrom.return_value = (
        b'ISTART[IEND\0', ('mocked', 12345))

    with pytest.raises(
        G90Error,
        match=re.escape("Unable to parse response as JSON: '['")
    ):
        await g90.process()
    mock_sock.send.assert_called_with(b'ISTART[206,206,""]IEND\0')


async def test_no_response(mock_sock):
    g90 = G90BaseCommand(
        host='mocked', port=12345, code=206, sock=mock_sock)
    mock_sock.recvfrom.return_value = (b'', ('mocked', 12345))

    with pytest.raises(G90Error, match='Missing start marker in data'):
        await g90.process()
    mock_sock.send.assert_called_with(b'ISTART[206,206,""]IEND\0')


async def test_empty_response(mock_sock):
    g90 = G90BaseCommand(
        host='mocked', port=12345, code=206, sock=mock_sock)
    mock_sock.recvfrom.return_value = (
        b'ISTARTIEND\0', ('mocked', 12345))

    await g90.process()
    mock_sock.send.assert_called_with(b'ISTART[206,206,""]IEND\0')


async def test_no_code_response(mock_sock):
    g90 = G90BaseCommand(
        host='mocked', port=12345, code=206, sock=mock_sock)
    mock_sock.recvfrom.return_value = (
        b'ISTART[]IEND\0', ('mocked', 12345))

    with pytest.raises(
        G90Error,
        match=re.escape("Missing code in response: '[]'")
    ):
        await g90.process()
    mock_sock.send.assert_called_with(b'ISTART[206,206,""]IEND\0')


async def test_wrong_code_response(mock_sock):
    g90 = G90BaseCommand(
        host='mocked', port=12345, code=206, sock=mock_sock)
    mock_sock.recvfrom.return_value = (
        b'ISTART[106,[""]]IEND\0', ('mocked', 12345))

    with pytest.raises(
        G90Error,
        match='Wrong response - received code 106, expected code 206'
    ):
        await g90.process()
    mock_sock.send.assert_called_with(b'ISTART[206,206,""]IEND\0')


async def test_no_data_response(mock_sock):
    g90 = G90BaseCommand(
        host='mocked', port=12345, code=206, sock=mock_sock)
    mock_sock.recvfrom.return_value = (
        b'ISTART[206]IEND\0', ('mocked', 12345))

    with pytest.raises(
        G90Error,
        match=re.escape("Missing data in response: '[206]'")
    ):
        await g90.process()
    mock_sock.send.assert_called_with(b'ISTART[206,206,""]IEND\0')


async def test_no_end_marker(mock_sock):
    g90 = G90BaseCommand(
        host='mocked', port=12345, code=206, sock=mock_sock)
    mock_sock.recvfrom.return_value = (
        b'ISTART[206,[]]IEND', ('mocked', 12345))

    with pytest.raises(G90Error, match='Missing end marker in data'):
        await g90.process()
    mock_sock.send.assert_called_with(b'ISTART[206,206,""]IEND\0')

"""
Tests for G90BaseCommand class
"""
from unittest.mock import patch, DEFAULT
import re
import pytest

from pyg90alarm.base_cmd import (
    G90BaseCommand,
)
from pyg90alarm.exceptions import (G90Error, G90TimeoutError)
from pyg90alarm.const import G90Commands

from .device_mock import DeviceMock


async def test_network_unreachable() -> None:
    """
    Verifies that network unreachable error is handled properly.
    """
    with patch.multiple(
        'socket', socket=DEFAULT, getaddrinfo=DEFAULT
    ) as mocks:
        g90 = G90BaseCommand(
            host='mocked', port=12345, code=G90Commands.GETHOSTINFO)

        # Simulate sending to device results in OS error
        mocks['socket'].return_value.send.side_effect = OSError(
            'Host unreachable'
        )
        mocks['getaddrinfo'].return_value = (5 * ('',),)

        with pytest.raises(OSError, match="Host unreachable"):
            await g90.process()


@pytest.mark.g90device(sent_data=[
    b'ISTARTIEND\0',
])
async def test_wrong_host(
    mock_device: DeviceMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Verifies that response from wrong host is handled properly.
    """
    orig = G90BaseCommand.datagram_received
    # Alter receving method of the device protocol as if it gets datagaram from
    # `another_host`
    monkeypatch.setattr(
        G90BaseCommand, 'datagram_received',
        lambda self, data, addr: orig(self, data, ('another_host', addr[1]))
    )
    g90 = G90BaseCommand(
        host=mock_device.host, port=mock_device.port,
        code=G90Commands.GETHOSTINFO
    )

    with pytest.raises(
        G90Error,
        match=(
            'Received response from wrong host another_host,'
            f' expected from {mock_device.host}'
        )
    ):
        await g90.process()


@pytest.mark.g90device(sent_data=[
    b'ISTARTIEND\0',
])
async def test_wrong_port(
    mock_device: DeviceMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Verifies that response from wrong port is handled properly.
    """
    orig = G90BaseCommand.datagram_received
    # Alter receving method of the device protocol as if it gets datagaram from
    # proper host but different port `54321`
    monkeypatch.setattr(
        G90BaseCommand, 'datagram_received',
        lambda self, data, addr: orig(self, data, (addr[0], 54321))
    )
    g90 = G90BaseCommand(
        host=mock_device.host, port=mock_device.port,
        code=G90Commands.GETHOSTINFO
    )

    with pytest.raises(
        G90Error,
        match=(
            'Received response from wrong port 54321,'
            f' expected from {mock_device.port}'
        )
    ):
        await g90.process()


# No data the simulated device sends back will result in receive timeout for
# the client
@pytest.mark.g90device(sent_data=[])
async def test_timeout(mock_device: DeviceMock) -> None:
    """
    Verifies that timeout is handled properly.
    """
    g90 = G90BaseCommand(
        host=mock_device.host, port=mock_device.port,
        code=G90Commands.GETHOSTINFO,
        timeout=0.1, retries=2
    )

    with pytest.raises(G90TimeoutError):
        await g90.process()
    assert mock_device.recv_data == [
        b'ISTART[206,206,""]IEND\0',
        b'ISTART[206,206,""]IEND\0',
    ]


@pytest.mark.g90device(sent_data=[
    b'\xdeadbeef\0',
])
async def test_invalid_utf8_encoding(mock_device: DeviceMock) -> None:
    """
    Verifies that invalid UTF-8 encoding of response is handled properly.
    """
    g90 = G90BaseCommand(
        host=mock_device.host, port=mock_device.port,
        code=G90Commands.GETHOSTINFO
    )

    with pytest.raises(
        G90Error,
        match=re.escape("Unable to decode response from UTF-8")
    ):
        await g90.process()
    assert mock_device.recv_data == [b'ISTART[206,206,""]IEND\0']


@pytest.mark.g90device(sent_data=[
    b'ISTART[IEND\0',
])
async def test_wrong_format(mock_device: DeviceMock) -> None:
    """
    Verifies that wrong format of response is handled properly.
    """
    g90 = G90BaseCommand(
        host=mock_device.host, port=mock_device.port,
        code=G90Commands.GETHOSTINFO
    )

    with pytest.raises(
        G90Error,
        match=re.escape("Unable to parse response as JSON: '['")
    ):
        await g90.process()
    assert mock_device.recv_data == [b'ISTART[206,206,""]IEND\0']


@pytest.mark.g90device(sent_data=[
    b'ISTARTIEND\0',
])
async def test_empty_response(mock_device: DeviceMock) -> None:
    """
    Verifies that empty response is handled properly.
    """
    g90 = G90BaseCommand(
        host=mock_device.host, port=mock_device.port,
        code=G90Commands.GETHOSTINFO
    )

    await g90.process()
    assert mock_device.recv_data == [b'ISTART[206,206,""]IEND\0']


@pytest.mark.g90device(sent_data=[
    b'ISTART[]IEND\0',
])
async def test_no_code_response(mock_device: DeviceMock) -> None:
    """
    Verifies that response without code is handled properly.
    """
    g90 = G90BaseCommand(
        host=mock_device.host, port=mock_device.port,
        code=G90Commands.GETHOSTINFO
    )

    with pytest.raises(
        G90Error,
        match=re.escape("Missing code in response: '[]'")
    ):
        await g90.process()
    assert mock_device.recv_data == [b'ISTART[206,206,""]IEND\0']


@pytest.mark.g90device(sent_data=[
    b'ISTART[106,[""]]IEND\0',
])
async def test_wrong_code_response(mock_device: DeviceMock) -> None:
    """
    Verifies that response with wrong code is handled properly.
    """
    g90 = G90BaseCommand(
        host=mock_device.host, port=mock_device.port,
        code=G90Commands.GETHOSTINFO
    )

    with pytest.raises(
        G90Error,
        match='Wrong response - received code 106, expected code 206'
    ):
        await g90.process()
    assert mock_device.recv_data == [b'ISTART[206,206,""]IEND\0']


@pytest.mark.g90device(sent_data=[
    b'ISTART[206]IEND\0',
])
async def test_no_data_response(mock_device: DeviceMock) -> None:
    """
    Verifies that response without data is handled properly.
    """
    g90 = G90BaseCommand(
        host=mock_device.host, port=mock_device.port,
        code=G90Commands.GETHOSTINFO
    )

    with pytest.raises(
        G90Error,
        match=re.escape("Missing data in response: '[206]'")
    ):
        await g90.process()
    assert mock_device.recv_data == [b'ISTART[206,206,""]IEND\0']


@pytest.mark.g90device(sent_data=[
    b'dummy',
])
async def test_no_start_marker(mock_device: DeviceMock) -> None:
    """
    Verifies that response without start marker is handled properly.
    """
    g90 = G90BaseCommand(
        host=mock_device.host, port=mock_device.port,
        code=G90Commands.GETHOSTINFO
    )

    with pytest.raises(G90Error, match='Missing start marker in data'):
        await g90.process()
    assert mock_device.recv_data == [b'ISTART[206,206,""]IEND\0']


@pytest.mark.g90device(sent_data=[
    b'ISTART[206,[]]IEND',
])
async def test_no_end_marker(mock_device: DeviceMock) -> None:
    """
    Verifies that response without end marker is handled properly.
    """
    g90 = G90BaseCommand(
        host=mock_device.host, port=mock_device.port,
        code=G90Commands.GETHOSTINFO
    )

    with pytest.raises(G90Error, match='Missing end marker in data'):
        await g90.process()
    assert mock_device.recv_data == [b'ISTART[206,206,""]IEND\0']


async def test_command_code_none_error(mock_device: DeviceMock) -> None:
    """
    Verifies that using `NONE` command code is disallowed by `G90BaseCommand`
    class.
    """
    g90 = G90BaseCommand(
        host=mock_device.host, port=mock_device.port,
        code=G90Commands.NONE
    )

    with pytest.raises(G90Error, match="'NONE' command code is disallowed"):
        await g90.process()

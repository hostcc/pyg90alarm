"""
Tests for G90BaseCommand class
"""
from unittest.mock import patch, DEFAULT
import re
import pytest

from pyg90alarm.local.base_cmd import (
    G90BaseCommand,
)
from pyg90alarm.exceptions import (
    G90Error, G90TimeoutError, G90RetryableError,
    G90CommandError, G90CommandFailure
)
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
    assert await mock_device.recv_data == [
        b'ISTART[206,206,""]IEND\0',
        b'ISTART[206,206,""]IEND\0',
    ]


@pytest.mark.g90device(sent_data=[
    b'ISTART\xdeadbeefIEND\0',
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
        match=re.escape("Unable to parse response as JSON: '�adbeef'")
    ):
        await g90.process()
    assert await mock_device.recv_data == [b'ISTART[206,206,""]IEND\0']


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
    assert await mock_device.recv_data == [b'ISTART[206,206,""]IEND\0']


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
    assert await mock_device.recv_data == [b'ISTART[206,206,""]IEND\0']


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
    assert await mock_device.recv_data == [b'ISTART[206,206,""]IEND\0']


@pytest.mark.g90device(sent_data=[
    b'ISTART[106,[""]]IEND\0',
])
async def test_wrong_code_response(mock_device: DeviceMock) -> None:
    """
    Verifies that response with wrong code raises retryable error.
    """
    g90 = G90BaseCommand(
        host=mock_device.host, port=mock_device.port,
        code=G90Commands.GETHOSTINFO,
        retries=1
    )

    with pytest.raises(
        G90RetryableError,
        match='Wrong response - received code 106, expected code 206'
    ):
        await g90.process()
    assert await mock_device.recv_data == [b'ISTART[206,206,""]IEND\0']


@pytest.mark.g90device(sent_data=[
    b'ISTART[106,[""]]IEND\0',
    b'ISTART[206,[""]]IEND\0',
])
async def test_retryable_error_retried_then_success(
    mock_device: DeviceMock,
) -> None:
    """
    Verifies that retryable error (wrong code) is retried and succeeds
    when the second response is valid.
    """
    g90 = G90BaseCommand(
        host=mock_device.host, port=mock_device.port,
        code=G90Commands.GETHOSTINFO,
        retries=3
    )

    await g90.process()
    assert g90.result == ['']
    assert await mock_device.recv_data == [
        b'ISTART[206,206,""]IEND\0',
        b'ISTART[206,206,""]IEND\0',
    ]


@pytest.mark.g90device(sent_data=[
    b'ISTART[106,[""]]IEND\0',
    b'ISTART[106,[""]]IEND\0',
])
async def test_retryable_error_exhausted(mock_device: DeviceMock) -> None:
    """
    Verifies that after exhausting retries on retryable error,
    G90RetryableError is raised.
    """
    g90 = G90BaseCommand(
        host=mock_device.host, port=mock_device.port,
        code=G90Commands.GETHOSTINFO,
        timeout=0.1, retries=2
    )

    with pytest.raises(
        G90RetryableError,
        match='Wrong response - received code 106, expected code 206'
    ):
        await g90.process()
    assert await mock_device.recv_data == [
        b'ISTART[206,206,""]IEND\0',
        b'ISTART[206,206,""]IEND\0',
    ]


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
    assert await mock_device.recv_data == [b'ISTART[206,206,""]IEND\0']


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
    assert await mock_device.recv_data == [b'ISTART[206,206,""]IEND\0']


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
    assert await mock_device.recv_data == [b'ISTART[206,206,""]IEND\0']


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


@pytest.mark.g90device(sent_data=[
    b'ISTARTfailIEND\0',
])
async def test_command_failure(mock_device: DeviceMock) -> None:
    """
    Verifies that command failure is handled properly.
    """
    g90 = G90BaseCommand(
        host=mock_device.host, port=mock_device.port,
        code=G90Commands.GETHOSTINFO
    )

    with pytest.raises(
        G90CommandFailure,
        match=re.escape('Command GETHOSTINFO (code=206) failed')
    ):
        await g90.process()


@pytest.mark.g90device(sent_data=[
    b'ISTARTerrordummyIEND\0',
])
async def test_command_error(mock_device: DeviceMock) -> None:
    """
    Verifies that command error is handled properly.
    """
    g90 = G90BaseCommand(
        host=mock_device.host, port=mock_device.port,
        code=G90Commands.GETHOSTINFO
    )

    with pytest.raises(
        G90CommandError,
        match=re.escape(
            "Command GETHOSTINFO (code=206) failed with error: 'dummy'"
        )
    ):
        await g90.process()


def test_attempt_delay_exponential_schedule() -> None:
    """
    Verifies that _get_attempt_delay implements exponential backoff
    scaled by timeout and capped at timeout.
    """
    timeout = 3.0
    retries = 3
    cmd = G90BaseCommand(
        host='mocked', port=12345, code=G90Commands.GETHOSTINFO,
        timeout=timeout, retries=retries
    )

    # base = timeout / (2 ** retries) = 3.0 / 8 = 0.375
    # pylint: disable=protected-access
    assert cmd._get_attempt_delay(0) == pytest.approx(0.375)
    assert cmd._get_attempt_delay(1) == pytest.approx(0.75)
    assert cmd._get_attempt_delay(2) == pytest.approx(1.5)
    # Further attempts are capped at timeout
    assert cmd._get_attempt_delay(3) == pytest.approx(timeout)
    assert cmd._get_attempt_delay(4) == pytest.approx(timeout)


def test_attempt_delay_no_retries_returns_timeout() -> None:
    """
    Verifies that when retries <= 0, _get_attempt_delay always
    returns timeout regardless of attempt index.
    """
    timeout = 2.5
    cmd = G90BaseCommand(
        host='mocked', port=12345, code=G90Commands.GETHOSTINFO,
        timeout=timeout, retries=0
    )

    # pylint: disable=protected-access
    for idx in range(5):
        assert cmd._get_attempt_delay(idx) == pytest.approx(timeout)

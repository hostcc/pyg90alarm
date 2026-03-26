# Copyright (c) 2021 Ilia Sotnikov
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Provides support for basic commands of G90 alarm panel.
"""
from __future__ import annotations
import logging
import json
import asyncio
from asyncio import Future
from asyncio.protocols import DatagramProtocol
from asyncio.transports import DatagramTransport, BaseTransport
from typing import (
    Optional, Tuple, List, Any, TypeVar, Generic, TYPE_CHECKING, cast
)
from dataclasses import dataclass
from ..exceptions import (
    G90Error, G90TimeoutError, G90RetryableError,
    G90CommandFailure, G90CommandError
)
from ..const import G90Commands, G90CommandsBase
if TYPE_CHECKING:
    from typing_extensions import Self

_LOGGER = logging.getLogger(__name__)

CommandT = TypeVar('CommandT', bound=G90CommandsBase)
CommandDataT = TypeVar('CommandDataT')


class G90Command(DatagramProtocol, Generic[CommandT, CommandDataT]):
    """
    Base class for command handling for alarm panel protocol.
    """
    # pylint: disable=too-many-instance-attributes
    # Lock need to be shared across all of the class instances
    _sk_lock = asyncio.Lock()

    # pylint: disable=too-many-positional-arguments,too-many-arguments
    def __init__(self, host: str, port: int, code: CommandT,
                 data: Optional[CommandDataT] = None,
                 local_port: Optional[int] = None,
                 timeout: float = 30.0, retries: int = 3) -> None:
        self._remote_host = host
        self._remote_port = port
        self._local_port = local_port
        self._code = code
        self._timeout = timeout
        self._retries = retries
        self._result: Optional[CommandDataT] = None
        self._connection_result: Optional[
            Future[Tuple[str, int, bytes]]
        ] = None
        self._data = self.encode_data(data)
        self._transport: Optional[DatagramTransport] = None

    # Implementation of datagram protocol,
    # https://docs.python.org/3/library/asyncio-protocol.html#datagram-protocols
    def connection_made(self, transport: BaseTransport) -> None:
        """
        Invoked when connection is established.
        """

    def connection_lost(self, exc: Optional[Exception]) -> None:
        """
        Invoked when connection is lost.
        """

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        """
        Invoked when datagram is received.
        """
        if asyncio.isfuture(self._connection_result):
            if self._connection_result.done():
                _LOGGER.debug(
                    'Excessive packet received from %s:%s: %s',
                    addr[0], addr[1], data
                )
                return
            self._connection_result.set_result((*addr, data))

    def error_received(self, exc: Exception) -> None:
        """
        Invoked when error is received.
        """
        if (
            asyncio.isfuture(self._connection_result) and not
            self._connection_result.done()
        ):
            self._connection_result.set_exception(exc)

    async def _create_connection(self) -> None:
        """
        Creates UDP connection to the alarm panel.
        """
        loop = asyncio.get_running_loop()

        _LOGGER.debug('Creating UDP endpoint for %s:%s',
                      self.host, self.port)
        local_addr = None
        if self._local_port:
            local_addr = ('0.0.0.0', self._local_port)

        self._transport, _ = await loop.create_datagram_endpoint(
            lambda: self,
            remote_addr=(self.host, self.port),
            allow_broadcast=True,
            local_addr=local_addr)

    def _close_connection(self) -> None:
        """
        Closes the connection to the alarm panel.
        """
        if self._transport is not None:
            _LOGGER.debug('Closing connection to %s:%s', self.host, self.port)
            self._transport.close()
        self._transport = None

    def _validate_response_sender(self, host: str, port: int) -> None:
        """
        Verifies the response is from the expected host and port.
        Closes the transport and raises G90Error if not.
        """
        if self.host != '255.255.255.255':
            if self.host != host or host == '255.255.255.255':
                self._close_connection()
                raise G90Error(
                    f'Received response from wrong host '
                    f'{host}, expected from {self.host}'
                )
        if self.port != port:
            self._close_connection()
            raise G90Error(
                f'Received response from wrong port '
                f'{port}, expected from {self.port}'
            )

    async def _send_only(self, sleep_for: Optional[float] = None) -> None:
        """
        Sends the command without waiting for a response.
        Used when expects_response is False.

        :param sleep_for: The amount of time to sleep after sending the command
          before returning. Used by discovery commands to wait all available
          devices to be discovered.
        """
        try:
            await self._create_connection()

            async with self._sk_lock:
                _LOGGER.debug(
                    '(code %s) Sending request to %s:%s',
                    self._code, self.host, self.port
                )
                # _create_connection() ensures that _transport is not None
                cast(DatagramTransport, self._transport).sendto(self.to_wire())
            # The sleep is not protected by the lock, to avoid blocking the
            # main thread - the primary purpose of sleeping it is to allow
            # multiple responses to be received, which shouldn't conflict with
            # command processing (which is protected by the lock).
            if sleep_for is not None:
                await asyncio.sleep(sleep_for)
            self._result = None
        finally:
            self._close_connection()

    async def _send_and_wait_for_response(
        self,
        timeout: float,
    ) -> Optional[Tuple[str, int, bytes]]:
        """
        Sends the command and waits for a response.
        Returns (host, port, data) on success, or None on timeout.
        """
        try:
            await self._create_connection()

            loop = asyncio.get_running_loop()
            self._connection_result = loop.create_future()
            # Both sending and waiting for response are protected by the same
            # lock, to avoid next command to start before the current one is
            # finished.
            async with self._sk_lock:
                _LOGGER.debug(
                    '(code %s) Sending request to %s:%s',
                    self._code, self.host, self.port
                )
                # See comment above
                cast(DatagramTransport, self._transport).sendto(self.to_wire())
                done, _ = await asyncio.wait(
                    [self._connection_result], timeout=timeout
                )
                self._close_connection()
                if self._connection_result in done:
                    return self._connection_result.result()
        finally:
            self._close_connection()
        return None

    def encode_data(self, data: Optional[CommandDataT]) -> str:
        """
        Encodes the command data to JSON string.
        """
        raise NotImplementedError()

    def decode_data(self, payload: Optional[str]) -> CommandDataT:
        """
        Decodes the command data from JSON string.
        """
        raise NotImplementedError()

    def to_wire(self) -> bytes:
        """
        Serializes the command to wire format.
        """
        raise NotImplementedError()

    def from_wire(self, data: bytes) -> Optional[CommandDataT]:
        """
        Deserializes the command from wire format.
        """
        raise NotImplementedError()

    @property
    def result(self) -> CommandDataT:
        """
        The result of the command.
        """
        raise NotImplementedError()

    @property
    def host(self) -> str:
        """
        The hostname/IP address of the alarm panel.
        """
        return self._remote_host

    @property
    def port(self) -> int:
        """
        The port of the alarm panel.
        """
        return self._remote_port

    @property
    def expects_response(self) -> bool:
        """
        Indicates whether the command expects a response.
        """
        return True

    def _get_attempt_delay(self, attempt: int) -> float:
        """
        Returns delay (seconds) used as both per-attempt timeout and
        sleep interval before the given retry attempt.

        :param attempt: The attempt number (1-based typically)
        :return: The delay in seconds
        """
        if self._retries <= 0:
            return self._timeout

        # Exponential schedule scaled by overall timeout.
        base = self._timeout / (2 ** self._retries)
        delay = base * (2 ** attempt)
        return float(min(self._timeout, delay))

    async def process(self) -> Self:  # G90Command[CommandT, CommandDataT]:
        """
        Processes the command.
        """
        # Disallow using `NONE` command, which is intended to use by inheriting
        # classes overriding `process()` method
        if self._code == G90Commands.NONE:
            raise G90Error("'NONE' command code is disallowed")

        if not self.expects_response:
            await self._send_only()
            return self

        attempt = 1
        while True:
            delay = self._get_attempt_delay(attempt)
            response = await self._send_and_wait_for_response(delay)

            # Handle timeout
            if response is None:
                if self._connection_result is not None:
                    self._connection_result.cancel()
                _LOGGER.debug(
                    'Timed out after %s seconds (attempt %s)%s',
                    delay, attempt,
                    ', retrying' if attempt < self._retries else ''
                )
                if attempt >= self._retries:
                    raise G90TimeoutError()
                attempt += 1
                continue

            host, port, data = response
            _LOGGER.debug('Received response from %s:%s', host, port)
            self._validate_response_sender(host, port)
            try:
                self._result = self.from_wire(data)
                break
            # Handle retryable error
            except G90RetryableError as exc:
                if attempt >= self._retries:
                    raise
                _LOGGER.debug(
                    'Retryable error (%s), retrying in %s seconds'
                    ' (attempt %d)',
                    exc, delay, attempt
                )
                attempt += 1
                await asyncio.sleep(delay)

        return self

    def __repr__(self) -> str:
        """
        Returns string representation of the command.
        """
        return f'Command: {self._code}, request: {self._data},' \
            f' response: {self.result}'


BaseCommandsT = G90Commands
BaseCommandsDataT = List[Any]


@dataclass
class G90Header:
    """
    Represents JSON structure of the header used in base panel commands.

    :meta private:
    """
    code: Optional[int] = None
    data: Optional[BaseCommandsDataT] = None


class G90BaseCommand(G90Command[BaseCommandsT, BaseCommandsDataT]):
    """
    Class for handling base G90 panel commands.
    """
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._resp = G90Header()

    def encode_data(self, data: Optional[BaseCommandsDataT]) -> str:
        """
        Encodes the command data to JSON string.
        """
        if data is None:
            return '""'
        return json.dumps([self._code, data],
                          # No newlines to be inserted
                          indent=None,
                          # No whitespace around entities
                          separators=(',', ':'))

    def decode_data(self, payload: Optional[str]) -> BaseCommandsDataT:
        """
        Decodes the command data from JSON string.
        """
        # Also, panel may report an error supplying specific reason, e.g.
        # command and its arguments that have failed
        if not payload:
            return []
        if payload.startswith('error'):
            error = payload[5:]
            raise G90CommandError(
                f"Command {self._code.name}"
                f" (code={self._code.value}) failed"
                f" with error: '{error}'")

        resp = None
        try:
            resp = json.loads(payload, strict=False)
        except json.JSONDecodeError as exc:
            raise G90Error(
                f"Unable to parse response as JSON: '{payload}'"
            ) from exc

        if not isinstance(resp, list):
            raise G90Error(
                f"Malformed response, 'list' expected: '{payload}'"
            )

        if resp is not None:
            self._resp = G90Header(*resp)
            _LOGGER.debug('Parsed from wire: %s', self._resp)

            if not self._resp.code:
                raise G90Error(f"Missing code in response: '{payload}'")
            # Check there is data if the response is non-empty
            if not self._resp.data:
                raise G90Error(f"Missing data in response: '{payload}'")

            if self._resp.code != self._code:
                raise G90RetryableError(
                    'Wrong response - received code '
                    f"{self._resp.code}, expected code {self._code}")

        return self._resp.data or []

    def to_wire(self) -> bytes:
        """
        Returns the command in wire format.
        """
        wire = bytes(f'ISTART[{self._code},{self._code},{self._data}]IEND\0',
                     'utf-8')
        _LOGGER.debug('Encoded to wire format %s', wire)
        return wire

    def from_wire(self, data: bytes) -> BaseCommandsDataT:
        """
        Parses the response from the alarm panel.
        """
        _LOGGER.debug('To be decoded from wire format %s', data)

        # Protocol markers must be processed strictly on bytes to avoid
        # invalid UTF-8 corrupting marker detection.
        start_marker = b'ISTART'
        if not data.startswith(start_marker):
            raise G90Error('Missing start marker in data')

        end_marker = b'IEND\0'
        if not data.endswith(end_marker):
            raise G90Error('Missing end marker in data')

        payload_bytes = data[len(start_marker):-len(end_marker)]
        try:
            payload = payload_bytes.decode('utf-8')
        except UnicodeDecodeError as exc:
            _LOGGER.debug(
                "Unable to decode response '%s' as strict UTF-8 (%s),"
                " invalid characters will be replaced",
                payload_bytes, exc
            )
            payload = payload_bytes.decode('utf-8', errors='replace')
        _LOGGER.debug("Decoded from wire: string '%s'", payload)

        if not payload:
            return []

        # Panel may report the last command has failed
        if payload == 'fail':
            raise G90CommandFailure(
                f"Command {self._code.name}"
                f" (code={self._code.value}) failed"
            )

        return self.decode_data(payload)

    @property
    def result(self) -> BaseCommandsDataT:
        """
        The result of the command.
        """
        if self._result is None:
            return []
        return self._result

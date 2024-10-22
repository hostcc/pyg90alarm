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
from typing import Optional, Tuple, List, Any
from dataclasses import dataclass
from .exceptions import (G90Error, G90TimeoutError)
from .const import G90Commands


_LOGGER = logging.getLogger(__name__)
G90BaseCommandData = List[Any]


@dataclass
class G90Header:
    """
    Represents JSON structure of the header used in alarm panel commands.

    :meta private:
    """
    code: Optional[int] = None
    data: Optional[G90BaseCommandData] = None


class G90BaseCommand(DatagramProtocol):
    """
    Implements basic command handling for alarm panel protocol.
    """
    # pylint: disable=too-many-instance-attributes
    # Lock need to be shared across all of the class instances
    _sk_lock = asyncio.Lock()

    def __init__(self, host: str, port: int, code: G90Commands,
                 data: Optional[G90BaseCommandData] = None,
                 local_port: Optional[int] = None,
                 timeout: float = 3.0, retries: int = 3) -> None:
        # pylint: disable=too-many-arguments
        self._remote_host = host
        self._remote_port = port
        self._local_port = local_port
        self._code = code
        self._timeout = timeout
        self._retries = retries
        self._data = '""'
        self._result: G90BaseCommandData = []
        self._connection_result: Optional[
            Future[Tuple[str, int, bytes]]
        ] = None
        if data:
            self._data = json.dumps([code, data],
                                    # No newlines to be inserted
                                    indent=None,
                                    # No whitespace around entities
                                    separators=(',', ':'))
        self._resp = G90Header()

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
                _LOGGER.warning('Excessive packet received'
                                ' from %s:%s: %s',
                                addr[0], addr[1], data)
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

    async def _create_connection(self) -> (
        Tuple[DatagramTransport, DatagramProtocol]
    ):
        """
        Creates UDP connection to the alarm panel.
        """
        try:
            loop = asyncio.get_running_loop()
        except AttributeError:
            loop = asyncio.get_event_loop()

        _LOGGER.debug('Creating UDP endpoint for %s:%s',
                      self.host, self.port)
        local_addr = None
        if self._local_port:
            local_addr = ('0.0.0.0', self._local_port)

        transport, protocol = await loop.create_datagram_endpoint(
            lambda: self,
            remote_addr=(self.host, self.port),
            allow_broadcast=True,
            local_addr=local_addr)

        return (transport, protocol)

    def to_wire(self) -> bytes:
        """
        Returns the command in wire format.
        """
        wire = bytes(f'ISTART[{self._code},{self._code},{self._data}]IEND\0',
                     'utf-8')
        _LOGGER.debug('Encoded to wire format %s', wire)
        return wire

    def from_wire(self, data: bytes) -> G90BaseCommandData:
        """
        Parses the response from the alarm panel.
        """
        _LOGGER.debug('To be decoded from wire format %s', data)
        try:
            self._parse(data.decode('utf-8'))
        except UnicodeDecodeError as exc:
            raise G90Error(
                'Unable to decode response from UTF-8'
            ) from exc
        return self._resp.data or []

    def _parse(self, data: str) -> None:
        """
        Processes the response from the alarm panel.
        """
        if not data.startswith('ISTART'):
            raise G90Error('Missing start marker in data')
        if not data.endswith('IEND\0'):
            raise G90Error('Missing end marker in data')
        payload = data[6:-5]
        _LOGGER.debug("Decoded from wire: JSON string '%s'", payload)

        resp = None
        if payload:
            try:
                resp = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise G90Error('Unable to parse response as JSON:'
                               f" '{payload}'") from exc

            if not isinstance(resp, list):
                raise G90Error('Mailformed response,'
                               f" 'list' expected: '{payload}'")

        if resp is not None:
            self._resp = G90Header(*resp)
            _LOGGER.debug('Parsed from wire: %s', self._resp)

            if not self._resp.code:
                raise G90Error(f"Missing code in response: '{payload}'")
            # Check there is data if the response is non-empty
            if not self._resp.data:
                raise G90Error(f"Missing data in response: '{payload}'")

            if self._resp.code != self._code:
                raise G90Error(
                    'Wrong response - received code '
                    f"{self._resp.code}, expected code {self._code}")

    @property
    def result(self) -> G90BaseCommandData:
        """
        The result of the command.
        """
        return self._result

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

    async def process(self) -> G90BaseCommand:
        """
        Processes the command.
        """
        # Disallow using `NONE` command, which is intended to use by inheriting
        # classes overriding `process()` method
        if self._code == G90Commands.NONE:
            raise G90Error("'NONE' command code is disallowed")

        transport, _ = await self._create_connection()
        attempts = self._retries
        while True:
            attempts = attempts - 1
            loop = asyncio.get_running_loop()
            self._connection_result = loop.create_future()
            async with self._sk_lock:
                _LOGGER.debug('(code %s) Sending request to %s:%s',
                              self._code, self.host, self.port)
                transport.sendto(self.to_wire())
                done, _ = await asyncio.wait([self._connection_result],
                                             timeout=self._timeout)
            if self._connection_result in done:
                break
            # Cancel the future to signal protocol handler it is no longer
            # valid, the future will be re-created on next retry
            self._connection_result.cancel()
            if not attempts:
                transport.close()
                raise G90TimeoutError()
            _LOGGER.debug('Timed out, retrying')
        transport.close()
        (host, port, data) = self._connection_result.result()
        _LOGGER.debug('Received response from %s:%s', host, port)
        if self.host != '255.255.255.255':
            if self.host != host or host == '255.255.255.255':
                raise G90Error(f'Received response from wrong host {host},'
                               f' expected from {self.host}')
        if self.port != port:
            raise G90Error(f'Received response from wrong port {port},'
                           f' expected from {self.port}')

        ret = self.from_wire(data)
        self._result = ret
        return self

    def __repr__(self) -> str:
        """
        Returns string representation of the command.
        """
        return f'Command: {self._code}, request: {self._data},' \
            f' response: {self._resp.data}'

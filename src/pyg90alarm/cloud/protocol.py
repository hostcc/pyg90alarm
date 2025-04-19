# Copyright (c) 2025 Ilia Sotnikov
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
Protocol implementation for G90 cloud communication.

This module defines the base classes and structures used for encoding and
decoding messages that flow between G90 alarm devices and their cloud servers.

Combination of Python `dataclasses` and `struct` is used to define the
protocol messages. The `dataclass` decorator is used to define the message
classes, while the `struct` module is used to define the binary format of
the messages.
"""
from __future__ import annotations
from typing import ClassVar, cast, List, Type, TypeVar, Optional
from struct import unpack, calcsize, pack, error as StructError
from dataclasses import dataclass, astuple, asdict, InitVar
from datetime import datetime, timezone
import logging

from .const import G90CloudDirection, G90CloudCommand
from ..const import G90AlertTypes

_LOGGER = logging.getLogger(__name__)
CloudBaseT = TypeVar('CloudBaseT', bound='G90CloudBase')
CloudHeaderT = TypeVar('CloudHeaderT', bound='G90CloudHeader')
CloudMessageT = TypeVar('CloudMessageT', bound='G90CloudMessage')

PROTOCOL_VERSION = 1


class G90CloudError(Exception):
    """
    Base exception for G90 cloud protocol errors.
    """


class G90CloudMessageNoMatch(G90CloudError):
    """
    Raised when a message does not match the expected format or type.
    """


class G90CloudMessageInvalid(G90CloudError):
    """
    Raised when a message is invalid or cannot be processed.
    """


@dataclass
class G90CloudMessageContext:  # pylint:disable=too-many-instance-attributes
    """
    Context for G90 cloud messages.

    This class holds information about the local and remote hosts and ports,
    as well as the cloud server and upstream connection details.
    """
    local_host: str
    local_port: int
    remote_host: str
    remote_port: int
    cloud_host: str
    cloud_port: int
    upstream_host: Optional[str]
    upstream_port: Optional[int]
    device_id: Optional[str]


@dataclass
class G90CloudBase:
    """
    Base class for G90 cloud protocol messages.

    Provides methods for encoding and decoding messages to and from their wire
    representation.
    """
    # Format of the binary data representing the message, see `struct` module
    # for the format supported
    _format: ClassVar[str]
    # Context for the message, should be provided when instsantiating the
    # message class
    context: InitVar[G90CloudMessageContext]
    # Stored context
    _context: ClassVar[G90CloudMessageContext]

    @classmethod
    def from_wire(
        cls: Type[CloudBaseT], data: bytes, context: G90CloudMessageContext
    ) -> CloudBaseT:
        """
        Decode a message from its wire representation.

        :param data: The raw bytes of the message.
        :param context: The message context.
        :return: An instance of the message class.
        """
        assert cls.format() is not None
        assert data is not None

        cls._context = context

        try:
            elems = unpack(cls.format(), data[0:cls.size()])
        except StructError as exc:
            raise G90CloudError(
                f"Failed to unpack data: {exc}"
                f", supplied data length: {len(data)}, format: {cls.format()}"
            ) from exc

        try:
            obj = cls(context, *elems)
        except TypeError as exc:
            raise G90CloudError(
                f"Failed to create object: {exc}"
                f", supplied data length: {len(data)}, format: {cls.format()}"
            ) from exc

        return obj

    def to_wire(self) -> bytes:
        """
        Encode the message to its wire representation.

        :return: The raw bytes of the message.
        """
        ret = pack(self.format(), *astuple(self))
        return ret

    @classmethod
    def size(cls) -> int:
        """
        Get the size of the message in bytes.

        :return: The size of the message.
        """
        return calcsize(cls.format())

    @classmethod
    def format(cls) -> str:
        """
        Get the format string for the message.

        :return: The format string.
        """
        return cls._format

    def __str__(self) -> str:
        """
        Get a string representation of the message.

        :return: A string representation of the message.
        """
        return (
            f"{type(self).__name__}("
            f"wire_representation={self.to_wire().hex(' ')}"
        )


@dataclass
class G90CloudHeader(G90CloudBase):
    """
    Header for G90 cloud protocol messages.

    Contains metadata about the message, such as its command, source,
    destination, and payload length.
    """
    _format = '<4Bi'

    command: int
    _source: int
    flag1: int
    _destination: int
    message_length: int

    def __post_init__(self, context: G90CloudMessageContext) -> None:
        """
        Initialize the header and its payload.

        :param context: The message context.
        """
        super().__init__(context)
        self._payload: bytes = bytes()

    @property
    def source(self) -> G90CloudDirection:
        """
        Get the source direction of the message.

        :return: The source direction.
        """
        return G90CloudDirection(self._source)

    @property
    def destination(self) -> G90CloudDirection:
        """
        Get the destination direction of the message.

        :return: The destination direction.
        """
        return G90CloudDirection(self._destination)

    @classmethod
    def from_wire(
        cls: Type[CloudHeaderT], data: bytes, context: G90CloudMessageContext
    ) -> CloudHeaderT:
        """
        Decode a header from its wire representation.

        :param data: The raw bytes of the header.
        :param context: The message context.
        :return: An instance of the header class.
        """
        obj = super().from_wire(data, context)

        message_length = obj.message_length  # pylint:disable=no-member
        if message_length > len(data):
            raise G90CloudError(
                f"Message length of {message_length} specified in header"
                f" exceeds actual data length {len(data)}"
            )

        obj._payload = bytes()  # pylint:disable=protected-access
        if cls.size() < len(data):
            # Payload length in header includes the header size, remove it from
            # resulting payload
            # pylint:disable=no-member,protected-access
            obj._payload = data[cls.size():obj.message_length]
        return obj

    @property
    def payload(self) -> bytes:
        """
        Get the payload of the message.

        :return: The raw bytes of the payload.
        """
        return self._payload

    @property
    def payload_length(self) -> int:
        """
        Get the length of the payload in bytes.

        :return: The payload length.
        """
        return self.message_length - self.size()

    def matches(self, value: G90CloudHeader) -> bool:
        """
        Check if the header matches another header.

        :param value: The header to compare against.
        :return: True if the headers match, False otherwise.
        """
        try:
            return (
                self.command == value.command
                and self._source == value._source
                # pylint:disable=protected-access
                and self._destination == value._destination
            )
        except AttributeError:
            return False

    def __str__(self) -> str:
        """
        Get a string representation of the header.

        :return: A string representation of the header.
        """
        return (
            f"{super().__str__()}"
            f", source={repr(self.source)}"
            f", destination={repr(self.destination)}"
            f", payload({self.payload_length})={self.payload.hex(' ')})"
        )


@dataclass
class G90CloudHeaderVersioned(G90CloudHeader):
    """
    Versioned header for G90 cloud protocol messages.

    Adds version and sequence information to the header.
    """
    _format = '<4BiHH'

    version: int = PROTOCOL_VERSION
    # Sequence will be initialized by :class:`G90CloudMessage` class, has to
    # have a default value as required by `dataclass` (non-default fields
    # cannot follow ones with defaults)
    sequence: int = 0

    def __post_init__(self, context: G90CloudMessageContext) -> None:
        super().__post_init__(context)
        if self.version != PROTOCOL_VERSION:
            raise G90CloudMessageInvalid(
                f'Invalid version in header: {self.version}'
            )

    def __str__(self) -> str:
        """
        Get a string representation of the versioned header.

        :return: A string representation of the versioned header.
        """
        return (
            f"{super().__str__()}"
            f", version={self.version}"
            f", sequence={self.sequence}"
        )


@dataclass
class G90CloudMessage(G90CloudBase):
    """
    Base class for G90 cloud protocol messages with headers.

    Provides methods for encoding and decoding messages with headers, as well
    as handling responses.
    """
    _command: ClassVar[G90CloudCommand]
    _destination: ClassVar[G90CloudDirection]
    _source: ClassVar[G90CloudDirection]
    _responses: ClassVar[List[Type[G90CloudMessage]]] = []
    _header_kls: ClassVar[Type[G90CloudHeader]] = G90CloudHeaderVersioned

    def __post_init__(self, context: G90CloudMessageContext) -> None:
        """
        Initialize the message and its header.

        :param context: The message context.
        """
        self.header = self._header_kls(
            command=self._command, _source=self._source,
            _destination=self._destination, flag1=0,
            message_length=self._header_kls.size() + self.size(),
            context=context
        )

    @classmethod
    def from_wire(
        cls: Type[CloudMessageT], data: bytes, context: G90CloudMessageContext
    ) -> CloudMessageT:
        """
        Decode a message from its wire representation.

        :param data: The raw bytes of the message.
        :param context: The message context.
        :return: An instance of the message class.
        """
        header = cls._header_kls.from_wire(data, context)

        header_matches = cls.header_matches(header)
        if not header_matches:
            raise G90CloudMessageNoMatch('Header does not match')

        try:
            # pylint:disable=no-member
            obj = super().from_wire(header.payload, context)
        except ValueError as exc:
            _LOGGER.error(
                "Failed to create %s from wire: %s",
                cls.__name__, exc
            )
            raise G90CloudMessageNoMatch('Failed to create object') from exc

        obj_matches = cls.matches(obj)
        if not obj_matches:
            raise G90CloudMessageNoMatch('Message does not match')

        obj.header = header
        return obj

    def to_wire(self) -> bytes:
        """
        Encode the message to its wire representation.

        :return: The raw bytes of the message.
        """
        # Reconstruct the wire representation of the block using header plus
        # payload
        ret = self.header.to_wire() + super().to_wire()
        return ret

    def wire_responses(self, context: G90CloudMessageContext) -> List[bytes]:
        """
        Get the wire representations of the responses to this message.

        :param context: The message context.
        :return: A list of raw bytes for the responses.
        """
        result = []
        for idx, response in enumerate(self._responses):
            obj = response(context)
            # Only messages with versioned headers can have sequence numbers
            if isinstance(obj.header, G90CloudHeaderVersioned):
                # Sequence numbers are either 0 for single message responses,
                # or start from 1 if there are multiple ones
                obj.header.sequence = 0
                if len(self._responses) > 1:
                    obj.header.sequence = idx + 1
            _LOGGER.debug(
                "%s: Will send response: %s", type(self).__name__, obj
            )
            result.append(obj.to_wire())
        return result

    @classmethod
    def matches(cls, value: G90CloudMessage) -> bool:
        """
        Check if the message matches another message.

        :param value: The message to compare against.
        :return: True if the messages match, False otherwise.
        """
        try:
            return (
                # pylint:disable=protected-access
                cls._command == value._command
                and cls._source == value._source
                # pylint:disable=protected-access
                and cls._destination == value._destination
            )
        except AttributeError:
            return False

    @classmethod
    def header_matches(cls, value: G90CloudHeader) -> bool:
        """
        Check if the header matches the expected header for this message type.

        :param value: The header to compare against.
        :return: True if the headers match, False otherwise.
        """
        try:
            return (
                cls._command == value.command
                and cls._source == value.source
                and cls._destination == value.destination
            )
        except AttributeError:
            return False

    def __str__(self) -> str:
        """
        Get a string representation of the message.

        :return: A string representation of the message.
        """
        b = [f"{k}={v}" for k, v in asdict(self).items()]
        return (
            f"{type(self).__name__}("
            f"header={str(self.header)}"
            f", wire_representation={self.to_wire().hex(' ')}"
            f", {', '.join(b)})"
        )


class G90CloudStatusChangeReqMessageBase(G90CloudMessage):
    """
    Base class for status change request messages in the G90 cloud protocol.

    Provides methods for handling status change requests and their timestamps.
    """
    _type: ClassVar[G90AlertTypes]

    type: int
    _timestamp: int  # Unix timestamp

    @property
    def timestamp(self) -> datetime:
        """
        Get the timestamp as a datetime object.

        :return: The message timestamp converted to a datetime object with UTC
         timezone.
        """
        return datetime.fromtimestamp(
            self._timestamp, tz=timezone.utc
        )

    @classmethod
    def matches(
        cls, value: G90CloudMessage
    ) -> bool:
        """
        Check if the message matches the expected type and format.

        :param value: The message to compare against.
        :return: True if the messages match, False otherwise.
        """
        try:
            obj = cast(G90CloudStatusChangeReqMessageBase, value)
            return (
                super().matches(value)
                and obj.type == cls._type
            )
        except AttributeError:
            return False

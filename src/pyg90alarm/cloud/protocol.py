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
tbd
"""
from __future__ import annotations
from typing import ClassVar, cast, List, Type, TypeVar
from struct import unpack, calcsize, pack, error as StructError
from dataclasses import dataclass, astuple, asdict
from datetime import datetime, timezone
import logging

from .const import G90CloudDirection, G90CloudCommand
from ..const import G90AlertTypes

_LOGGER = logging.getLogger(__name__)
CloudBaseT = TypeVar('CloudBaseT', bound='G90CloudBase')
CloudHeaderT = TypeVar('CloudHeaderT', bound='G90CloudHeader')
CloudMessageT = TypeVar('CloudMessageT', bound='G90CloudMessage')


class G90CloudError(Exception):
    """
    tbd
    """


class G90CloudMessageNoMatch(G90CloudError):
    """
    tbd
    """


@dataclass
class G90CloudBase:
    """
    tbd
    """
    _format: ClassVar[str]

    @classmethod
    def from_wire(cls: Type[CloudBaseT], data: bytes) -> CloudBaseT:
        """
        tbd
        """
        assert cls.format() is not None
        assert data is not None

        try:
            elems = unpack(cls.format(), data[0:cls.size()])
        except StructError as exc:
            raise G90CloudError(
                f"Failed to unpack data: {exc}"
                f", supplied data length: {len(data)}, format: {cls.format()}"
            ) from exc

        try:
            obj = cls(*elems)
        except TypeError as exc:
            raise G90CloudError(
                f"Failed to create object: {exc}"
                f", supplied data length: {len(data)}, format: {cls.format()}"
            ) from exc

        return obj

    def to_wire(self) -> bytes:
        """
        tbd
        """
        ret = pack(self.format(), *astuple(self))
        return ret

    @classmethod
    def size(cls) -> int:
        """
        tbd
        """
        return calcsize(cls.format())

    @classmethod
    def format(cls) -> str:
        """
        tbd
        """
        return cls._format

    def __str__(self) -> str:
        """
        tbd
        """
        return (
            f"{type(self).__name__}("
            # f"{', '.join(map(repr, astuple(self)))}, "
            f"wire_representation={self.to_wire().hex(' ')}"
        )


@dataclass
class G90CloudHeader(G90CloudBase):
    """
    tbd
    """
    _format = '<4Bi'

    command: int
    _source: int
    flag1: int
    _destination: int
    message_length: int

    def __post_init__(self) -> None:
        """
        tbd
        """
        self._payload: bytes = bytes()

    @property
    def source(self) -> G90CloudDirection:
        """
        tbd
        """
        return G90CloudDirection(self._source)

    @property
    def destination(self) -> G90CloudDirection:
        """
        tbd
        """
        return G90CloudDirection(self._destination)

    @classmethod
    def from_wire(cls: Type[CloudHeaderT], data: bytes) -> CloudHeaderT:
        """
        tbd
        """
        obj = super().from_wire(data)

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
        tbd
        """
        return self._payload

    @property
    def payload_length(self) -> int:
        """
        tbd
        """
        # Return size of payload from header minus header size itself
        return self.message_length - self.size()

    def matches(self, value: G90CloudHeader) -> bool:
        """
        tbd
        """
        try:
            # pylint:disable=protected-access
            return (
                self.command == value.command
                and self._source == value._source
                and self._destination == value._destination
            )
        except AttributeError:
            return False

    def __str__(self) -> str:
        """
        tbd
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
    tbd
    """
    _format = '<4BiHH'

    version: int = 1
    sequence: int = 0

    def __str__(self) -> str:
        """
        tbd
        """
        return (
            f"{super().__str__()}"
            f", version={self.version}"
            f", sequence={self.sequence}"
        )


@dataclass
class G90CloudMessage(G90CloudBase):
    """
    tbd
    """
    _command: ClassVar[G90CloudCommand]
    _destination: ClassVar[G90CloudDirection]
    _source: ClassVar[G90CloudDirection]
    _responses: ClassVar[List[Type[G90CloudMessage]]] = []
    _header_kls: ClassVar[Type[G90CloudHeader]] = G90CloudHeaderVersioned

    def __post_init__(self) -> None:
        """
        tbd
        """
        self.header = self._header_kls(
            command=self._command, _source=self._source,
            _destination=self._destination, flag1=0,
            message_length=self._header_kls.size() + self.size()
        )

    @classmethod
    def from_wire(cls: Type[CloudMessageT], data: bytes) -> CloudMessageT:
        """
        tbd
        """
        header = cls._header_kls.from_wire(data)

        header_matches = cls.header_matches(header)
        if not header_matches:
            raise G90CloudMessageNoMatch('Header does not match')

        try:
            obj = super().from_wire(header.payload)  # pylint:disable=no-member
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
        tbd
        """
        # Reconstruct the wire representation of the block using header plus
        # payload
        ret = self.header.to_wire() + super().to_wire()
        return ret

    def wire_responses(self) -> List[bytes]:
        """
        tbd
        """
        result = []
        for idx, response in enumerate(self._responses):
            obj = response()
            if (
                isinstance(obj.header, G90CloudHeaderVersioned)
                and len(self._responses) > 1
            ):
                obj.header.sequence = idx + 1
            _LOGGER.debug(
                "%s: Will send response: %s", type(self).__name__, obj
            )
            result.append(obj.to_wire())
        return result

    @classmethod
    def matches(cls, value: G90CloudMessage) -> bool:
        """
        tbd
        """
        try:
            # pylint:disable=protected-access
            return (
                cls._command == value._command
                and cls._source == value._source
                and cls._destination == value._destination
            )
        except AttributeError:
            return False

    @classmethod
    def header_matches(cls, value: G90CloudHeader) -> bool:
        """
        tbd
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
        tbd
        """

        b = [f"{k}={v}" for k, v in asdict(self).items()]
        return (
            f"{type(self).__name__}("
            # f"{', '.join(map(str, astuple(self)))}, "
            f"header={str(self.header)}"
            f", wire_representation={self.to_wire().hex(' ')}"
            f", {', '.join(b)})"
        )


# @dataclass
# pylint:disable=too-many-instance-attributes
class G90CloudStatusChangeReqMessageBase(G90CloudMessage):
    """
    tbd
    """
    _type: ClassVar[G90AlertTypes]

    type: int
    _timestamp: int  # Unix timestamp

    @property
    def timestamp(self) -> datetime:
        """
        tbd
        """
        return datetime.fromtimestamp(
            self._timestamp, tz=timezone.utc
        )

    @classmethod
    def matches(
        cls, value: G90CloudMessage
    ) -> bool:
        """
        tbd
        """
        try:
            obj = cast(G90CloudStatusChangeReqMessageBase, value)
            # pylint:disable=protected-access
            return (
                super().matches(value)
                and obj.type == cls._type
            )
        except AttributeError:
            return False

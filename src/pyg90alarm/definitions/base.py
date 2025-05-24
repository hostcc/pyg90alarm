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
Base entities for peripheral definitions.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import groupby
from enum import IntEnum
from abc import ABC, abstractmethod
import logging
from ..exceptions import G90PeripheralDefinitionNotFound, G90Error

_LOGGER = logging.getLogger(__name__)


class G90PeripheralProtocols(IntEnum):
    """
    Protocol types for the peripherals.
    """
    RF_1527 = 0
    RF_2262 = 1
    RF_PRIVATE = 2
    RF_SLIDER = 3
    CORD = 5
    WIFI = 4
    USB = 6


class G90PeripheralTypes(IntEnum):
    """
    Peripheral types.
    """
    DOOR = 1
    GLASS = 2
    GAS = 3
    SMOKE = 4
    SOS = 5
    VIB = 6
    WATER = 7
    INFRARED = 8
    IN_BEAM = 9
    REMOTE = 10
    RFID = 11
    DOORBELL = 12
    BUTTONID = 13
    WATCH = 14
    FINGER_LOCK = 15
    SUBHOST = 16
    REMOTE_2_4G = 17
    GAS_VALVE = 18
    CORD_SENSOR = 126
    SOCKET = 128
    SIREN = 129
    CURTAIN = 130
    SLIDINGWIN = 131
    AIRCON = 133
    TV = 135
    TV_BOX = 136
    SMART_SWITCH = 137
    NIGHTLIGHT = 138
    SOCKET_2_4G = 140
    SIREN_2_4G = 141
    SWITCH_2_4G = 142
    TOUCH_SWITCH_2_4G = 143
    CURTAIN_2_4G = 144
    IR_2_4G = 145
    CORD_DEV = 254
    UNKNOWN = 255


class G90PeripheralMatchModes(IntEnum):
    """
    Defines compare (match) mode for the peripheral.
    """
    ALL = 0
    ONLY20BITS = 1
    ONLY16BITS = 2


class G90PeripheralRwModes(IntEnum):
    """
    Defines read/write mode for the peripheral.
    """
    READ = 0
    WRITE = 1
    READ_WRITE = 2


@dataclass(frozen=True)
class G90PeripheralDefinition:
    # pylint: disable=too-many-instance-attributes
    """
    Holds peripheral definition data.
    """
    type: G90PeripheralTypes
    subtype: int
    rx: int
    tx: int
    private_data: str
    rw_mode: G90PeripheralRwModes
    match_mode: G90PeripheralMatchModes
    name: str
    protocol: G90PeripheralProtocols
    timeout: int
    baudrate: int
    node_count: int

    @property
    def reserved_data(self) -> int:
        """
        Peripheral's 'reserved_data' field to be written, combined of match
        and RW mode values bitwise.
        """
        return self.match_mode.value << 4 | self.rw_mode.value


def unique_definitions(
    obj: type[G90PeripheralDefinitionsBase]
) -> type[G90PeripheralDefinitionsBase]:
    """
    Decorator to ensure that peripheral definitions are unique by name
    and type/subtype/protocol.

    :param obj: Class to decorate.
    :return: Decorated class with unique definitions.
    :raises G90Error: If definitions are not unique.
    """
    names = groupby(
        sorted(obj.definitions(), key=lambda x: x.name),
        lambda x: x.name
    )
    type_subtype = groupby(
        sorted(
            obj.definitions(),
            key=lambda x: (x.type, x.subtype, x.protocol)
        ),
        lambda x: (x.type, x.subtype, x.protocol)
    )
    non_unique_names = [
        k for _, group in names if len(k := list(group)) > 1
    ]
    non_unique_types = [
        k for _, group in type_subtype if len(k := list(group)) > 1
    ]

    msgs = []
    if non_unique_names:
        msgs.append(
            f"{obj}: Peripheral definitions have non-unique names: \n"
            f"{non_unique_names}"
        )
    if non_unique_types:
        msgs.append(
            f"{obj}: Peripheral definitions have non-unique types: \n"
            f"{non_unique_types}"
        )

    if msgs:
        raise G90Error('.\n'.join(msgs))

    return obj


class G90PeripheralDefinitionsBase(ABC):
    """
    Base class for peripheral definitions.
    """
    @classmethod
    @abstractmethod
    def definitions(cls) -> list[G90PeripheralDefinition]:
        """
        Get all peripheral definitions.

        :return: List of peripheral definitions.
        """

    @classmethod
    def get_by_id(
        cls, id_type: G90PeripheralTypes, id_subtype: int,
        protocol: G90PeripheralProtocols
    ) -> G90PeripheralDefinition:
        """
        Gets peripheral definition by type, subtype and protocol.

        :param id_type: Peripheral type.
        :param id_subtype: Peripheral subtype.
        :param protocol: Peripheral protocol.
        :raises G90PeripheralDefinitionNotFound: If definition not found.
        """
        for definition in cls.definitions():
            if (
                definition.type == id_type
                and definition.subtype == id_subtype
                and definition.protocol == protocol
            ):
                _LOGGER.debug(
                    "Found peripheral definition by"
                    " type %d, subtype %d and protocol %d: %s",
                    id_type, id_subtype, protocol, definition
                )
                return definition

        raise G90PeripheralDefinitionNotFound(
            "Peripheral definition not found"
            f" by type={id_type}, subtype={id_subtype}"
            f" and protocol={protocol}",
        )

    @classmethod
    def get_by_name(
        cls, name: str
    ) -> G90PeripheralDefinition:
        """
        Gets peripheral definition by name.

        :param name: Peripheral name.
        :raises G90PeripheralDefinitionNotFound: If definition not found.
        """
        for definition in cls.definitions():
            if definition.name == name:
                _LOGGER.debug(
                    "Found peripheral definition by name '%s': %s",
                    name, definition
                )
                return definition

        raise G90PeripheralDefinitionNotFound(
            f"Peripheral definition not found by name='{name}'"
        )

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
Device (relays, sockets) definitions for G90 alarm panel.
"""
from __future__ import annotations
import logging
from .base import (
    G90PeripheralDefinition,
    G90PeripheralDefinitionsBase,
    G90PeripheralTypes,
    G90PeripheralProtocols,
    G90PeripheralRwModes,
    G90PeripheralMatchModes,
    unique_definitions,
)

_LOGGER = logging.getLogger(__name__)


@unique_definitions
class G90DeviceDefinitions(G90PeripheralDefinitionsBase):
    """
    Device definitions, required when modifying them since
    writing a device to the panel requires values not present on read.
    """
    DEVICE_DEFINITIONS = [
        G90PeripheralDefinition(
            type=G90PeripheralTypes.CORD_DEV,
            subtype=0,
            rx=0,
            tx=0,
            private_data='00',
            rw_mode=G90PeripheralRwModes.WRITE,
            match_mode=G90PeripheralMatchModes.ONLY20BITS,
            name="Wired",
            protocol=G90PeripheralProtocols.CORD,
            timeout=0,
            baudrate=1480,
            node_count=1
        ),
        G90PeripheralDefinition(
            type=G90PeripheralTypes.SOCKET,
            subtype=3,
            rx=0,
            tx=2,
            private_data='060A0600',
            rw_mode=G90PeripheralRwModes.WRITE,
            match_mode=G90PeripheralMatchModes.ONLY20BITS,
            name="Socket: S07",
            protocol=G90PeripheralProtocols.RF_1527,
            timeout=0,
            baudrate=1190,
            node_count=1
        ),
        G90PeripheralDefinition(
            type=G90PeripheralTypes.SOCKET,
            subtype=0,
            rx=0,
            tx=2,
            private_data='0707070B0B0D0D0E0E00',
            rw_mode=G90PeripheralRwModes.WRITE,
            match_mode=G90PeripheralMatchModes.ONLY20BITS,
            name="Socket: JDQ",
            protocol=G90PeripheralProtocols.RF_1527,
            timeout=0,
            baudrate=1480,
            node_count=4
        ),
        G90PeripheralDefinition(
            type=G90PeripheralTypes.SOCKET,
            subtype=1,
            rx=0,
            tx=2,
            private_data='07070700',
            rw_mode=G90PeripheralRwModes.WRITE,
            match_mode=G90PeripheralMatchModes.ONLY20BITS,
            name="Socket: Single channel",
            protocol=G90PeripheralProtocols.RF_1527,
            timeout=0,
            baudrate=1480,
            node_count=1
        ),
        G90PeripheralDefinition(
            type=G90PeripheralTypes.SOCKET,
            subtype=4,
            rx=0,
            tx=2,
            private_data='050D0500',
            rw_mode=G90PeripheralRwModes.WRITE,
            match_mode=G90PeripheralMatchModes.ONLY20BITS,
            name="Socket Switch",
            protocol=G90PeripheralProtocols.RF_1527,
            timeout=0,
            baudrate=840,
            node_count=1
        ),
        G90PeripheralDefinition(
            type=G90PeripheralTypes.SOCKET,
            subtype=5,
            rx=0,
            tx=2,
            private_data='070A0E080D060B00',
            rw_mode=G90PeripheralRwModes.WRITE,
            match_mode=G90PeripheralMatchModes.ONLY20BITS,
            name="Socket: 3 channel",
            protocol=G90PeripheralProtocols.RF_1527,
            timeout=0,
            baudrate=960,
            node_count=3
        ),
        G90PeripheralDefinition(
            type=G90PeripheralTypes.SOCKET,
            subtype=6,
            rx=0,
            tx=2,
            private_data='0B0D0E0B0C090A070800',
            rw_mode=G90PeripheralRwModes.WRITE,
            match_mode=G90PeripheralMatchModes.ONLY20BITS,
            name="Socket: 4 channel",
            protocol=G90PeripheralProtocols.RF_1527,
            timeout=0,
            baudrate=960,
            node_count=4
        ),
        G90PeripheralDefinition(
            type=G90PeripheralTypes.CURTAIN,
            subtype=0,
            rx=0,
            tx=7,
            private_data='070B0E0D0C09030100',
            rw_mode=G90PeripheralRwModes.WRITE,
            match_mode=G90PeripheralMatchModes.ONLY20BITS,
            name="Curtain: Rolling",
            protocol=G90PeripheralProtocols.RF_1527,
            timeout=0,
            baudrate=960,
            node_count=1
        ),
        G90PeripheralDefinition(
            type=G90PeripheralTypes.CURTAIN,
            subtype=1,
            rx=0,
            tx=7,
            private_data='0804010200',
            rw_mode=G90PeripheralRwModes.WRITE,
            match_mode=G90PeripheralMatchModes.ONLY16BITS,
            name="Curtain",
            protocol=G90PeripheralProtocols.RF_SLIDER,
            timeout=0,
            baudrate=500,
            node_count=1
        ),
        G90PeripheralDefinition(
            type=G90PeripheralTypes.CURTAIN,
            subtype=1,
            rx=0,
            tx=7,
            private_data='0E0B0E0D0C09030100',
            rw_mode=G90PeripheralRwModes.WRITE,
            match_mode=G90PeripheralMatchModes.ONLY20BITS,
            name="Curtain: Sliding",
            protocol=G90PeripheralProtocols.RF_1527,
            timeout=0,
            baudrate=960,
            node_count=1
        ),
        G90PeripheralDefinition(
            type=G90PeripheralTypes.CURTAIN,
            subtype=2,
            rx=0,
            tx=7,
            private_data='070B0E0D0C09030100',
            rw_mode=G90PeripheralRwModes.WRITE,
            match_mode=G90PeripheralMatchModes.ONLY20BITS,
            name="Curtain: Push",
            protocol=G90PeripheralProtocols.RF_1527,
            timeout=0,
            baudrate=960,
            node_count=1
        ),
        G90PeripheralDefinition(
            type=G90PeripheralTypes.AIRCON,
            subtype=0,
            rx=0,
            tx=0,
            private_data='00',
            rw_mode=G90PeripheralRwModes.WRITE,
            match_mode=G90PeripheralMatchModes.ONLY20BITS,
            name="Air Conditioner",
            protocol=G90PeripheralProtocols.RF_PRIVATE,
            timeout=0,
            baudrate=800,
            node_count=1
        ),
        G90PeripheralDefinition(
            type=G90PeripheralTypes.TV,
            subtype=0,
            rx=0,
            tx=0,
            private_data='00',
            rw_mode=G90PeripheralRwModes.WRITE,
            match_mode=G90PeripheralMatchModes.ONLY20BITS,
            name="TV",
            protocol=G90PeripheralProtocols.RF_PRIVATE,
            timeout=0,
            baudrate=800,
            node_count=1
        ),
        G90PeripheralDefinition(
            type=G90PeripheralTypes.SIREN,
            subtype=0,
            rx=0,
            tx=2,
            private_data='FEFEF600',
            rw_mode=G90PeripheralRwModes.WRITE,
            match_mode=G90PeripheralMatchModes.ONLY16BITS,
            name="Siren: SS08",
            protocol=G90PeripheralProtocols.RF_1527,
            timeout=0,
            baudrate=1480,
            node_count=1
        ),
        G90PeripheralDefinition(
            type=G90PeripheralTypes.SIREN,
            subtype=4,
            rx=0,
            tx=2,
            private_data='FEFEF600',
            rw_mode=G90PeripheralRwModes.WRITE,
            match_mode=G90PeripheralMatchModes.ONLY16BITS,
            name="Siren: SS07A",
            protocol=G90PeripheralProtocols.RF_1527,
            timeout=0,
            baudrate=1480,
            node_count=1
        ),
        G90PeripheralDefinition(
            type=G90PeripheralTypes.SIREN,
            subtype=5,
            rx=0,
            tx=2,
            private_data='FCFCCF00',
            rw_mode=G90PeripheralRwModes.WRITE,
            match_mode=G90PeripheralMatchModes.ONLY16BITS,
            name="Siren: SS04",
            protocol=G90PeripheralProtocols.RF_2262,
            timeout=0,
            baudrate=1480,
            node_count=1
        ),
        G90PeripheralDefinition(
            type=G90PeripheralTypes.SIREN,
            subtype=1,
            rx=0,
            tx=2,
            private_data='FCFCCF00',
            rw_mode=G90PeripheralRwModes.WRITE,
            match_mode=G90PeripheralMatchModes.ONLY16BITS,
            name="Siren: SS02B",
            protocol=G90PeripheralProtocols.RF_2262,
            timeout=0,
            baudrate=1480,
            node_count=1
        ),
        G90PeripheralDefinition(
            type=G90PeripheralTypes.SIREN,
            subtype=2,
            rx=0,
            tx=2,
            private_data='FEFEFD00',
            rw_mode=G90PeripheralRwModes.WRITE,
            match_mode=G90PeripheralMatchModes.ONLY16BITS,
            name="Siren: Solar",
            protocol=G90PeripheralProtocols.RF_1527,
            timeout=0,
            baudrate=2200,
            node_count=1
        ),
        G90PeripheralDefinition(
            type=G90PeripheralTypes.NIGHTLIGHT,
            subtype=0,
            rx=0,
            tx=2,
            private_data='060A0600',
            rw_mode=G90PeripheralRwModes.WRITE,
            match_mode=G90PeripheralMatchModes.ONLY20BITS,
            name="Night Light",
            protocol=G90PeripheralProtocols.RF_1527,
            timeout=0,
            baudrate=1190,
            node_count=1
        ),
        G90PeripheralDefinition(
            type=G90PeripheralTypes.SOCKET_2_4G,
            subtype=1,
            rx=0,
            tx=0,
            private_data='00',
            rw_mode=G90PeripheralRwModes.WRITE,
            match_mode=G90PeripheralMatchModes.ONLY20BITS,
            name="Socket: 2.4G",
            protocol=G90PeripheralProtocols.RF_1527,
            timeout=0,
            baudrate=960,
            node_count=1
        ),
        G90PeripheralDefinition(
            type=G90PeripheralTypes.SIREN_2_4G,
            subtype=1,
            rx=0,
            tx=0,
            private_data='00',
            rw_mode=G90PeripheralRwModes.WRITE,
            match_mode=G90PeripheralMatchModes.ONLY16BITS,
            name="Siren: 2.4G",
            protocol=G90PeripheralProtocols.RF_1527,
            timeout=0,
            baudrate=2200,
            node_count=1
        ),
        G90PeripheralDefinition(
            type=G90PeripheralTypes.CURTAIN_2_4G,
            subtype=1,
            rx=0,
            tx=0,
            private_data='00',
            rw_mode=G90PeripheralRwModes.WRITE,
            match_mode=G90PeripheralMatchModes.ONLY20BITS,
            name="Curtain: 2.4G",
            protocol=G90PeripheralProtocols.RF_1527,
            timeout=0,
            baudrate=960,
            node_count=1
        ),
    ]

    @classmethod
    def definitions(cls) -> list[G90PeripheralDefinition]:
        """
        Gets all device definitions.

        :return: List of device definitions.
        """
        _LOGGER.debug(
            "Number of sensor definitions: %d", len(cls.DEVICE_DEFINITIONS)
        )
        return cls.DEVICE_DEFINITIONS

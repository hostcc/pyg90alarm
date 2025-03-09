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
from typing import List, Type, cast, ClassVar, Any, TypeVar
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from .protocol import (
    G90CloudMessage, G90CloudStatusChangeReqMessageBase, G90CloudHeader
)
from .const import G90CloudDirection, G90CloudCommand
from ..const import (
    G90AlertStateChangeTypes, REMOTE_CLOUD_HOST, REMOTE_CLOUD_PORT,
    G90AlertTypes, G90AlertSources, G90AlertStates,
)
from ..entities.sensor import G90SensorTypes
from ..notifications.base import G90DeviceAlert


_LOGGER = logging.getLogger(__name__)
CLOUD_MESSAGE_CLASSES: List[Type[Any]] = []
CloudMessageT = TypeVar('CloudMessageT', bound='G90CloudMessage')


def cloud_message(obj: Type[CloudMessageT]) -> Type[CloudMessageT]:
    """
    tbd
    """
    for cls in CLOUD_MESSAGE_CLASSES:
        if cls.matches(obj):
            # pylint:disable=protected-access
            raise ValueError(
                f"Duplicate command={obj._command}"
                f"/source={obj._source}/destination={obj._destination}"
                f" in {cls} and {obj}"
            )
    CLOUD_MESSAGE_CLASSES.append(obj)
    return obj


@dataclass
class G90CloudPingRespMessage(G90CloudMessage):
    """
    tbd
    """
    _format = ''
    _command = G90CloudCommand.HELLO
    _source = G90CloudDirection.DEVICE
    _destination = G90CloudDirection.UNSPECIFIED
    _header_kls = G90CloudHeader


@cloud_message
@dataclass
class G90CloudPingReqMessage(G90CloudMessage):
    """
    Every minute.
    """
    _format = ''
    _command = G90CloudCommand.HELLO
    _source = G90CloudDirection.DEVICE
    _destination = G90CloudDirection.UNSPECIFIED
    _responses = [G90CloudPingRespMessage]
    _header_kls = G90CloudHeader


@dataclass
class G90CloudHelloAckMessage(G90CloudMessage):
    """
    tbd
    """
    _format = '<B'
    _command = G90CloudCommand.HELLO_ACK
    _source = G90CloudDirection.CLOUD
    _destination = G90CloudDirection.DEVICE

    flag: int = 1


@dataclass
class G90CloudHelloRespMessage(G90CloudMessage):
    """
    tbd
    """
    _format = '<B'
    _command = G90CloudCommand.HELLO
    _source = G90CloudDirection.CLOUD
    _destination = G90CloudDirection.DEVICE

    flag: int = 0x1f


@dataclass
class G90CloudHelloInfoRespMessage(G90CloudMessage):
    """
    tbd
    """
    _format = '<i'
    _command = G90CloudCommand.HELLO_INFO
    _source = G90CloudDirection.CLOUD
    _destination = G90CloudDirection.DEVICE

    port: int = 0x7202  # 29186, could be 0x6502 = 25858


@cloud_message
@dataclass
# pylint:disable=too-many-instance-attributes
class G90CloudHelloReqMessage(G90CloudMessage):
    """
    Every minute.
    """
    _format = '<15sx4i3sx6i'
    _command = G90CloudCommand.HELLO
    _source = G90CloudDirection.DEVICE
    _destination = G90CloudDirection.CLOUD
    _responses = [
        G90CloudHelloAckMessage, G90CloudHelloRespMessage,
        G90CloudHelloInfoRespMessage
    ]

    guid: str
    flag1: int      # Typically is 1
    flag2: int      # Typically is 0
    flag3: int      # Typically is 2
    flag4: int      # Typically is 28672 (0x7000)
    fw_ver: str
    flag5: int      # Typically is 0x2000NNNN
    flag6: int      # Typically is 48 (0x30)
    flag7: int      # Typically is 0
    flag8: int      # Typically is 7
    flag9: int      # Typically is 30 (0x1E)
    flag10: int     # Typically is 30 (0x1E)


@dataclass
class G90CloudHelloDiscoveryRespMessage(G90CloudMessage):
    """
    tbd
    """
    _format = '<16s4i'
    _command = G90CloudCommand.HELLO
    _source = G90CloudDirection.CLOUD_DISCOVERY
    _destination = G90CloudDirection.DEVICE

    ip_addr: bytes = REMOTE_CLOUD_HOST.encode()
    flag2: int = 0
    flag3: int = 0
    port: int = REMOTE_CLOUD_PORT
    _timestamp: int = 0  # unix timestamp

    def __post_init__(self) -> None:
        super().__post_init__()

        self._timestamp = int(datetime.now(timezone.utc).timestamp())
        _LOGGER.debug(
            "%s: Timestamp added: %s", type(self).__name__, str(self)
        )

    @property
    def timestamp(self) -> datetime:
        """
        tbd
        """
        return datetime.fromtimestamp(
            self._timestamp, tz=timezone.utc
        )

    def __str__(self) -> str:
        return (
            f"{type(self).__name__}"
            f"({super().__str__()}"
            f", timestamp={self.timestamp})"
        )


@cloud_message
@dataclass
# pylint:disable=too-many-instance-attributes
class G90CloudHelloDiscoveryReqMessage(G90CloudMessage):
    """
    tbd
    """
    _format = '<15sx4i3sx3i'
    _command = G90CloudCommand.HELLO
    _source = G90CloudDirection.DEVICE_DISCOVERY
    _destination = G90CloudDirection.CLOUD
    _responses = [G90CloudHelloDiscoveryRespMessage]

    guid: str
    flag1: int      # Typically is 0
    flag2: int      # Typically is 0
    flag3: int      # Typically is 1
    flag4: int      # Typically is 28672 (0x7000)
    fw_ver: str
    flag5: int      # Typically is 0x05050505
    flag6: int      # Typically is 0x06060030
    flag7: int      # Typically is 0x07070707


@cloud_message
@dataclass
# pylint:disable=too-many-instance-attributes
class G90CloudStatusChangeReqMessage(G90CloudStatusChangeReqMessageBase):
    """
    tbd
    """
    # 68x are typically zeros, while 34x is some garbage from previous
    # notification message (0x22) with its head overwritten with old/new status
    # values
    _format = '<2B34xi68x'
    _command = G90CloudCommand.STATUS_CHANGE
    _source = G90CloudDirection.DEVICE
    _destination = G90CloudDirection.CLOUD
    _type = G90AlertTypes.STATE_CHANGE

    type: int
    _state: G90AlertStateChangeTypes
    _timestamp: int  # Unix timestamp

    @property
    def state(self) -> G90AlertStateChangeTypes:
        """
        tbd
        """
        return G90AlertStateChangeTypes(self._state)

    @property
    def as_device_alert(self) -> G90DeviceAlert:
        """
        tbd
        """
        return G90DeviceAlert(
            device_id='',
            state=self.state,
            event_id=self.state,
            zone_name='',
            type=self._type,
            source=G90AlertSources.DEVICE,
            unix_time=self._timestamp,
            resv4=0,
            other='',
        )

    def __str__(self) -> str:
        return (
            f"{type(self).__name__}"
            f"({super().__str__()}"
            f", type={self.type}"
            f", state={repr(self.state)}"
            f", timestamp={self.timestamp})"
        )


@cloud_message
@dataclass
# pylint:disable=too-many-instance-attributes
class G90CloudStatusChangeSensorReqMessage(G90CloudStatusChangeReqMessageBase):
    """
    tbd
    """
    _format = '<4B32si68x'
    _command = G90CloudCommand.STATUS_CHANGE
    _source = G90CloudDirection.DEVICE
    _destination = G90CloudDirection.CLOUD
    _type: ClassVar[G90AlertTypes] = G90AlertTypes.SENSOR_ACTIVITY

    type: int
    sensor_id: int
    _sensor_type: G90SensorTypes
    _sensor_state: int
    _sensor: bytes
    _timestamp: int  # Unix timestamp

    @property
    def sensor_type(self) -> G90SensorTypes:
        """
        tbd
        """
        return G90SensorTypes(self._sensor_type)

    @property
    def sensor_state(self) -> G90AlertStates:
        """
        tbd
        """
        return G90AlertStates(self._sensor_state)

    @property
    def sensor(self) -> str:
        """
        tbd
        """
        return self._sensor.decode().rstrip('\x00')

    @property
    def as_device_alert(self) -> G90DeviceAlert:
        """
        tbd
        """
        return G90DeviceAlert(
            device_id='',
            state=self.sensor_state,
            event_id=cast(G90AlertStateChangeTypes, self.sensor_id),
            zone_name=self.sensor,
            type=self._type,
            source=G90AlertSources.SENSOR,
            unix_time=self._timestamp,
            resv4=0,
            other='',
        )

    def __str__(self) -> str:
        return (
            f"{type(self).__name__}"
            f"({super().__str__()}"
            f", type={self.type}"
            f", sensor={repr(self.sensor)}"
            f", sensor id ={self.sensor_id}"
            f", sensor type={repr(self.sensor_type)}"
            f", sensor state={repr(self.sensor_state)}"
            f", timestamp={self.timestamp})"
        )


@cloud_message
@dataclass
# pylint:disable=too-many-instance-attributes
class G90CloudStatusChangeAlarmReqMessage(G90CloudStatusChangeReqMessageBase):
    """
    tbd
    """
    _format = '<4B32si68x'
    _command = G90CloudCommand.STATUS_CHANGE
    _source = G90CloudDirection.DEVICE
    _destination = G90CloudDirection.CLOUD
    _type: ClassVar[G90AlertTypes] = G90AlertTypes.ALARM

    type: int
    sensor_id: int
    _sensor_type: G90SensorTypes
    _sensor_state: int
    _sensor: bytes
    _timestamp: int  # Unix timestamp

    @property
    def sensor_state(self) -> G90AlertStates:
        """
        tbd
        """
        return G90AlertStates(self._sensor_state)

    @property
    def sensor(self) -> str:
        """
        tbd
        """
        return self._sensor.decode().rstrip('\x00')

    @property
    def sensor_type(self) -> G90SensorTypes:
        """
        tbd
        """
        return G90SensorTypes(self._sensor_type)

    @property
    def as_device_alert(self) -> G90DeviceAlert:
        """
        tbd
        """
        return G90DeviceAlert(
            device_id='',
            state=self.sensor_state,
            event_id=cast(G90AlertStateChangeTypes, self.sensor_id),
            zone_name=self.sensor,
            type=self._type,
            source=G90AlertSources.DEVICE,
            unix_time=self._timestamp,
            resv4=0,
            other='',
        )

    def __str__(self) -> str:
        return (
            f"{type(self).__name__}"
            f"({super().__str__()}"
            f", type={self.type}"
            f", _type={self._type}"
            f", sensor={repr(self.sensor)}"
            f", sensor id ={self.sensor_id}"
            f", sensor type={repr(self.sensor_type)}"
            f", sensor state={repr(self.sensor_state)}"
            f", timestamp={self.timestamp})"
        )


@cloud_message
@dataclass
class G90CloudNotificationMessage(G90CloudMessage):
    """
    tbd
    """
    _format = ''
    _command = G90CloudCommand.NOTIFICATION
    _source = G90CloudDirection.DEVICE
    _destination = G90CloudDirection.CLOUD

    @property
    def as_notification_message(self) -> bytes:
        """
        tbd
        """
        notification_message = self.header.payload[self.size():]
        _LOGGER.debug(
            "%s: Unpacked notification message: %s",
            type(self).__name__, notification_message.decode()
        )

        return notification_message

    def __str__(self) -> str:
        return (
            f"{type(self).__name__}"
            f"({super().__str__()}"
            f", notification_message={self.as_notification_message.decode()})"
        )


@cloud_message
@dataclass
class G90CloudCmdRespMessage(G90CloudMessage):
    """
    Every minute.
    """
    _format = '<HiHi2H'
    _command = G90CloudCommand.HELLO
    _source = G90CloudDirection.UNSPECIFIED
    _destination = G90CloudDirection.CLOUD
    _header_kls = G90CloudHeader

    flag1: int
    seq_num1: int
    flag3: int
    seq_num2: int
    cmd: int
    subcmd: int

    @property
    def body(self) -> bytes:
        """
        tbd
        """
        body = self.header.payload[self.size():]
        _LOGGER.debug(
            "%s: Unpacked response: %s",
            type(self).__name__, body.decode()
        )

        return body

    def __str__(self) -> str:
        return (
            f"{type(self).__name__}"
            f"({super().__str__()}"
            f", cmd={self.cmd}"
            f", subcmd={self.subcmd}"
            f", seq_num={self.seq_num1}"
            f", body={self.body.decode()})"
        )

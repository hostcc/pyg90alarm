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
Cloud message implementations for G90 alarm systems.

This module provides concrete message classes for cloud communication with G90
alarm systems, including ping messages, discovery messages, status change
notifications, and alarm notifications.
"""
from typing import List, Type, cast, ClassVar, Any, TypeVar
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from pyg90alarm.cloud.protocol import G90CloudMessageContext

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
    Register a cloud message class.

    This decorator registers the cloud message class in the global registry
    and ensures there are no duplicate registrations for the same command/
    source/destination combination.

    :param obj: The cloud message class to register
    :return: The registered cloud message class
    :raises ValueError: If a class with the same command/source/destination is
     already registered
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
    Response message for ping requests.

    A message sent in response to a ping request from the device.
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
    Ping request message sent by the device to the cloud server.

    This message is sent every minute as a keepalive mechanism.

    :attr _responses: The possible response message classes
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
    Acknowledgement message sent by the cloud server in response to a hello
    message.

    This message confirms receipt of the hello request from the device.
    """
    _format = '<B'
    _command = G90CloudCommand.HELLO_ACK
    _source = G90CloudDirection.CLOUD
    _destination = G90CloudDirection.DEVICE

    flag: int = 1


@dataclass
class G90CloudHelloRespMessage(G90CloudMessage):
    """
    Response message from the cloud server to a hello request from a device.
    """
    _format = '<B'
    _command = G90CloudCommand.HELLO
    _source = G90CloudDirection.CLOUD
    _destination = G90CloudDirection.DEVICE

    flag: int = 0x1f


@dataclass
class G90CloudHelloInfoRespMessage(G90CloudMessage):
    """
    Information response message from the cloud server to a device's hello
    request.

    This message contains information about the port the device should use for
    communication.
    """
    _format = '<i'
    _command = G90CloudCommand.HELLO_INFO
    _source = G90CloudDirection.CLOUD
    _destination = G90CloudDirection.DEVICE

    # Actual port is set from context in `__post_init__()` method below
    port: int = 0

    def __post_init__(self, context: G90CloudMessageContext) -> None:
        super().__post_init__(context)
        self.port = context.local_port


@cloud_message
@dataclass
# pylint:disable=too-many-instance-attributes
class G90CloudHelloReqMessage(G90CloudMessage):
    """
    Hello request message sent by the device to the cloud server.

    This message is sent every minute as part of the device's heartbeat
    mechanism.
    """
    _format = '<15sx4i3sx6i'
    _command = G90CloudCommand.HELLO
    _source = G90CloudDirection.DEVICE
    _destination = G90CloudDirection.CLOUD
    _responses = [
        G90CloudHelloAckMessage, G90CloudHelloRespMessage,
        G90CloudHelloInfoRespMessage
    ]

    _guid: bytes
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

    @property
    def guid(self) -> str:
        """
        Get the device GUID as a string.

        :return: The device's GUID decoded from bytes to string
        """
        return self._guid.decode()


@dataclass
class G90CloudHelloDiscoveryRespMessage(G90CloudMessage):
    """
    Discovery response message from the cloud to the device.

    This message contains information about the cloud server's IP, port, and
    timestamp.
    """
    _format = '<16s4i'
    _command = G90CloudCommand.HELLO
    _source = G90CloudDirection.CLOUD_DISCOVERY
    _destination = G90CloudDirection.DEVICE

    # Simulated cloud response always contains known IP address of the vendor's
    # cloud service - that is, all interactions between alarm panel and
    # simulated cloud service will use same IP address for unification (i.e.
    # traffic redicrection will always be used to divert panel's cloud traffic
    # to the simulated cloud service)
    ip_addr: bytes = REMOTE_CLOUD_HOST.encode()
    flag2: int = 0
    flag3: int = 0
    port: int = REMOTE_CLOUD_PORT
    _timestamp: int = 0  # unix timestamp

    def __post_init__(self, context: G90CloudMessageContext) -> None:
        super().__post_init__(context)

        self._timestamp = int(datetime.now(timezone.utc).timestamp())
        _LOGGER.debug(
            "%s: Timestamp added: %s", type(self).__name__, str(self)
        )
        self.ip_addr = context.cloud_host.encode()
        self.port = context.cloud_port

    @property
    def timestamp(self) -> datetime:
        """
        Get the timestamp as a datetime object.

        :return: The message timestamp converted to a datetime object with UTC
         timezone
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
    Hello discovery request message sent by the device.

    This message is used during the device discovery process to locate the
    cloud server.
    """
    _format = '<15sx4i3sx3i'
    _command = G90CloudCommand.HELLO
    _source = G90CloudDirection.DEVICE_DISCOVERY
    _destination = G90CloudDirection.CLOUD
    _responses = [G90CloudHelloDiscoveryRespMessage]

    _guid: bytes
    flag1: int      # Typically is 0
    flag2: int      # Typically is 0
    flag3: int      # Typically is 1
    flag4: int      # Typically is 28672 (0x7000)
    fw_ver: str
    flag5: int      # Typically is 0x05050505
    flag6: int      # Typically is 0x06060030
    flag7: int      # Typically is 0x07070707

    @property
    def guid(self) -> str:
        """
        Get the device GUID as a string.

        :return: The device's GUID decoded from bytes to string
        """
        return self._guid.decode()


@cloud_message
@dataclass
# pylint:disable=too-many-instance-attributes
class G90CloudStatusChangeReqMessage(G90CloudStatusChangeReqMessageBase):
    """
    Status change request message from the device to the cloud.

    This message is sent when the device's status changes, such as arming or
    disarming.
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
        Get the state change type.

        :return: The alert state change type
        """
        return G90AlertStateChangeTypes(self._state)

    @property
    def as_device_alert(self) -> G90DeviceAlert:
        """
        Convert the message to a device alert object.

        :return: A G90DeviceAlert object constructed from the message
         properties
        """
        return G90DeviceAlert(
            device_id=self._context.device_id or '',
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
    Status change sensor request message from the device to the cloud.

    This message is sent when a sensor's status changes, such as when motion is
    detected or a door/window is opened.
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
        Get the sensor type.

        :return: The type of the sensor that triggered the event
        """
        return G90SensorTypes(self._sensor_type)

    @property
    def sensor_state(self) -> G90AlertStates:
        """
        Get the sensor state.

        :return: The state of the sensor that triggered the event
        """
        return G90AlertStates(self._sensor_state)

    @property
    def sensor(self) -> str:
        """
        Get the sensor name as a string.

        :return: The sensor name decoded from bytes with null characters
         removed
        """
        return self._sensor.decode().rstrip('\x00')

    @property
    def as_device_alert(self) -> G90DeviceAlert:
        """
        Convert the message to a device alert object.

        :return: A G90DeviceAlert object constructed from the message
         properties
        """
        return G90DeviceAlert(
            device_id=self._context.device_id or '',
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
    Status change alarm request message from the device to the cloud.

    This message is sent when an alarm is triggered on the device, such as when
    an intrusion is detected or when the panic button is pressed.
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
        Get the sensor state for the alarm event.

        :return: The state of the sensor that triggered the alarm
        """
        return G90AlertStates(self._sensor_state)

    @property
    def sensor(self) -> str:
        """
        Get the sensor name as a string.

        :return: The sensor name decoded from bytes with null characters
         removed
        """
        return self._sensor.decode().rstrip('\x00')

    @property
    def sensor_type(self) -> G90SensorTypes:
        """
        Get the sensor type for the alarm event.

        :return: The type of sensor that triggered the alarm
        """
        return G90SensorTypes(self._sensor_type)

    @property
    def as_device_alert(self) -> G90DeviceAlert:
        """
        Convert the message to a device alert object.

        :return: A G90DeviceAlert object constructed from the message
         properties
        """
        return G90DeviceAlert(
            device_id=self._context.device_id or '',
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
    Notification message from the device to the cloud server.

    This message carries notification data from the device that may include
    sensor data or other information.
    """
    _format = ''
    _command = G90CloudCommand.NOTIFICATION
    _source = G90CloudDirection.DEVICE
    _destination = G90CloudDirection.CLOUD

    @property
    def as_notification_message(self) -> bytes:
        """
        Extract the notification message payload.

        :return: The raw notification message bytes extracted from the header
         payload
        """
        return self.header.payload[self.size():]

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
    Command response message sent by the device.

    This message contains command and sequence information.
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
        Extract the response body payload.

        :return: The raw response body bytes extracted from the header payload
        """
        return self.header.payload[self.size():]

    def __str__(self) -> str:
        return (
            f"{type(self).__name__}"
            f"({super().__str__()}"
            f", cmd={self.cmd}"
            f", subcmd={self.subcmd}"
            f", seq_num={self.seq_num1}"
            f", body={self.body.decode()})"
        )

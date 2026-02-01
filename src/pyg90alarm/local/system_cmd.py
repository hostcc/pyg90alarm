# Copyright (c) 2026 Ilia Sotnikov
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
Provides support for system commands of the G90 alarm panel.
"""
from __future__ import annotations
from typing import Any, Optional, TypeVar, List
import logging

from ..const import G90SystemCommands, G90SystemConfigurationCommands
from .base_cmd import G90Command

_LOGGER = logging.getLogger(__name__)


SystemCommandsT = TypeVar('SystemCommandsT', bound=G90SystemCommands)
SystemCommandsDataT = TypeVar('SystemCommandsDataT')


class G90SystemCommandBase(G90Command[SystemCommandsT, SystemCommandsDataT]):
    """
    Base class for system commands of the G90 alarm panel.

    :param code: System command code
    :param kwargs: Additional arguments passed to the base class
    """
    def __init__(
        self, *, code: SystemCommandsT, **kwargs: Any
    ) -> None:
        super().__init__(code=code, **kwargs)

    @property
    def expects_response(self) -> bool:
        """
        Indicates whether the command expects a response.

        System commands do not return any response.

        :return: False
        """
        return False

    def encode_data(self, data: Optional[SystemCommandsDataT]) -> str:
        """
        Encodes the command data to string.

        :param data: Data for the command
        :return: Encoded data string
        """
        # Placeholder as required by the base class
        raise NotImplementedError()  # pragma: no cover

    def decode_data(self, payload: Optional[str]) -> SystemCommandsDataT:
        """
        Decodes the command data from string.

        :param payload: Payload string
        :return: Decoded data
        """
        # Placeholder as required by the base class
        raise NotImplementedError()  # pragma: no cover

    def to_wire(self) -> bytes:
        """
        Serializes the command to wire format as expected by the panel.

        :return: Wire data
        """
        wire = bytes(
            f'ISTART[0,100,"AT^IWT={self._code}{self._data},IWT"]IEND\0',
            'utf-8'
        )

        _LOGGER.debug('Encoded to wire format %s', wire)
        return wire

    def from_wire(self, data: bytes) -> SystemCommandsDataT:
        """
        Deserializes the command from wire format.

        :param data: Wire data
        :return: Decoded data
        """
        # Placeholder as required by the base class
        raise NotImplementedError()  # pragma: no cover

    @property
    def result(self) -> SystemCommandsDataT:
        """
        The result of the command.

        :return: Decoded data
        """
        # Placeholder as required by the base class
        raise NotImplementedError()  # pragma: no cover


class G90SystemCommand(
    G90SystemCommandBase[SystemCommandsT, str]
):
    """
    Represents a system command of the G90 alarm panel.

    :param code: System command code
    :param kwargs: Additional arguments passed to the base class
    """
    def __init__(
        self, *, code: SystemCommandsT, **kwargs: Any
    ) -> None:
        if code in [G90SystemCommands.SET_CONFIGURATION,
                    G90SystemCommands.GET_CONFIGURATION]:
            raise ValueError(
                'Use G90SystemConfigurationCommand class for '
                'SET_CONFIGURATION and GET_CONFIGURATION commands'
            )
        super().__init__(code=code, **kwargs)

    def encode_data(self, data: Optional[str]) -> str:
        """
        Encodes the command data to string.

        :param data: Data for the command
        :return: Encoded data string
        """
        return data or ''

    def decode_data(self, payload: Optional[str]) -> str:
        """
        Decodes the command data from string.

        No response is expected for system commands.

        :param payload: Payload string (ignored)
        :return: Empty string
        """
        # No response is expected for system commands
        return ''  # pragma: no cover

    def from_wire(self, data: bytes) -> str:
        """
        Deserializes the command from wire format.

        No response is expected for system commands.

        :param data: Wire data (ignored)
        :return: Empty string
        """
        # No response is expected for system commands
        return ''  # pragma: no cover

    @property
    def result(self) -> str:
        """
        The result of the command.

        No response is expected for system commands.

        :return: Empty string
        """
        # No response is expected for system commands
        return ''  # pragma: no cover


class G90SystemConfigurationCommand(
    G90SystemCommandBase[G90SystemCommands, List[str]]
):
    """
    Represents a system configuration command of the G90 alarm panel.

    :param cmd: Sub-command code for configuration command
    :param data: Data for the command
    :param kwargs: Additional arguments passed to the base class
    """
    def __init__(
        self, *, cmd: G90SystemConfigurationCommands,
        data: Optional[List[str]] = None,
        **kwargs: Any
    ) -> None:
        self._cmd = cmd
        super().__init__(
            code=G90SystemCommands.SET_CONFIGURATION, data=data, **kwargs
        )

    def encode_data(self, data: Optional[List[str]]) -> str:
        """
        Encodes the command data to string.

        :param data: Data for the command
        :return: Encoded data string
        """
        if data is None:
            raise ValueError('Data must be provided for configuration command')

        res = f',{self._cmd.value}={"&".join(data)}'
        _LOGGER.debug('Encoded data "%s" to string format: %s', data, res)
        return res

    def decode_data(self, payload: Optional[str]) -> List[str]:
        """
        Decodes the command data from string.

        System configuration commands do not return any response.

        :param payload: Payload string
        :return: Empty list
        """
        # System configuration commands do not return any response.
        return []  # pragma: no cover

    def from_wire(self, data: bytes) -> List[str]:
        """
        Deserializes the command from wire format.

        System configuration commands do not return any response.

        :param data: Wire data
        :return: Empty list
        """
        # System configuration commands do not return any response.
        return []  # pragma: no cover

    @property
    def result(self) -> List[str]:
        """
        The result of the command.

        System configuration commands do not return any response.

        :return: Empty list
        """
        # System configuration commands do not return any response.
        return []  # pragma: no cover


class G90SetServerAddressCommand(
    G90SystemConfigurationCommand
):
    """
    Sets the server address for the panel to comminicate with using the cloud
    notifications protocol.

    :param cloud_ip: IP address of the cloud server
    :param cloud_port: Port number of the cloud server
    :param kwargs: Additional arguments passed to the base class
    """
    def __init__(
        self, *, cloud_ip: str, cloud_port: int,
        **kwargs: Any
    ) -> None:
        super().__init__(
            cmd=G90SystemConfigurationCommands.SERVER_ADDRESS,
            # The command requires two fields for the cloud server address, 1st
            # is used by the panel to communicate with the server, while 2nd
            # might potentially be a fallback address or alike. However,
            # experiments did not show any attempts by the panel to use the 2nd
            # address, so we set both to the same value in an avoidance of
            # doubt.
            data=[cloud_ip, cloud_ip, str(cloud_port)], **kwargs
        )

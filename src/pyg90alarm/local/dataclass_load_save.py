
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
Base class for loading/saving dataclasses to a device.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Type, TypeVar, Optional, ClassVar, Any, Dict
import logging
from dataclasses import dataclass, astuple, asdict
from ..const import G90Commands
if TYPE_CHECKING:
    from ..alarm import G90Alarm


_LOGGER = logging.getLogger(__name__)
S = TypeVar('S', bound='DataclassLoadSave')


@dataclass
class DataclassLoadSave:
    """
    Base class for loading/saving dataclasses to a device.

    There are multiple ways to implement the functionality:
     - Encapsulate the dataclass inside another class that handles
       loading/saving and exposes dataclass fields as properties. The latter
       part gets complex as properties need to be asynchronous, as well as
       added dynamically at runtime to improve maintainability.
     - Inherit from this class, which provides `load` and `save` methods on top
       of standard dataclasses. This is believed to be more concise and easier
       to understand.

    Implementing classes must define `LOAD_COMMAND` and `SAVE_COMMAND` class
    variables to specify which commands to use for loading and saving data.

    Example usage:

        @dataclass
        class G90ExampleConfig(DataclassLoadSave):
            LOAD_COMMAND = G90Commands.GETEXAMPLECONFIG
            SAVE_COMMAND = G90Commands.SETEXAMPLECONFIG
            field1: int
            field2: str

        # Loading data
        config = await G90ExampleConfig.load(G90_alarm_instance)
        print(config.field1, config.field2)

        # Modifying and saving data
        config.field1 = 42
        await config.save()
    """
    LOAD_COMMAND: ClassVar[Optional[G90Commands]] = None
    SAVE_COMMAND: ClassVar[Optional[G90Commands]] = None

    def __post_init__(self) -> None:
        """
        Post-initialization processing.
        """
        # Instance variable to hold reference to parent G90Alarm instance,
        # declared here to avoid being part of dataclass fields
        self._parent: Optional[G90Alarm] = None

    async def save(self) -> None:
        """
        Save the current data to the device.
        """
        assert self.SAVE_COMMAND is not None, '`SAVE_COMMAND` must be defined'
        assert self._parent is not None, 'Please call `load()` first'

        _LOGGER.debug('Setting data to the device: %s', str(self))
        await self._parent.command(
            self.SAVE_COMMAND,
            list(astuple(self))
        )

    @classmethod
    async def load(cls: Type[S], parent: G90Alarm) -> S:
        """
        Create an instance with values loaded from the device.

        :return: An instance of the dataclass loaded from the device.
        """
        assert cls.LOAD_COMMAND is not None, '`LOAD_COMMAND` must be defined'
        assert parent is not None, '`parent` must be provided'

        data = await parent.command(cls.LOAD_COMMAND)
        obj = cls(*data)
        _LOGGER.debug('Loaded data: %s', str(obj))

        obj._parent = parent

        return obj

    def _asdict(self) -> Dict[str, Any]:
        """
        Returns the dataclass fields as a dictionary.

        :return: A dictionary representation.
        """
        return asdict(self)

    def __str__(self) -> str:
        """
        Textual representation of the entry.

        `str()` is used instead of `repr()` since dataclass provides `repr()`
        by default, and it would be impractical to require each ancestor to
        disable that.

        :return: A textual representation.
        """
        return super().__repr__() + f'({str(self._asdict())})'

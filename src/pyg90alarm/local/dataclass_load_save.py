
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
from typing import (
    TYPE_CHECKING, Type, TypeVar, Optional, ClassVar, Any, Dict, List, Generic,
    cast,
)
import logging
from dataclasses import dataclass, asdict, field, fields
from ..const import G90Commands
if TYPE_CHECKING:
    from ..alarm import G90Alarm


_LOGGER = logging.getLogger(__name__)
DataclassLoadSaveT = TypeVar('DataclassLoadSaveT', bound='DataclassLoadSave')
T = TypeVar('T')


class Metadata:
    """
    Metadata keys for DataclassLoadSave fields.
    """
    # pylint: disable=too-few-public-methods
    NO_SERIALIZE = 'no_serialize'
    SKIP_NONE = 'skip_none'


class ReadOnlyIfNotProvided(Generic[T]):
    """
    Descriptor for dataclass fields to be read-only if not provided during
    initialization.

    The field can be read, but attempts to modify it will raise an
    AttributeError if the field was not provided during initialization. In
    other words, the only way to set the value is during object creation.

    Example usage:

        @dataclass
        class Example:
            read_only_field: Optional[int] = field_readonly_if_not_provided(
                default=None
            )

        # Works ok
        ex = Example(read_only_field=42)
        print(ex.read_only_field)  # Outputs: 42
        ex.read_only_field = 100  # Works ok

        # Raises AttributeError
        ex2 = Example()
        print(ex2.read_only_field)  # Outputs: None
        ex2.read_only_field = 100  # Raises AttributeError

    :param default: Default value to return upon read if not provided during
     initialization.
    """
    def __init__(self, default: Optional[T] = None) -> None:
        self._name: Optional[str] = None
        self._default = default

    def __set_name__(self, owner: type, name: str) -> None:
        # Store the name of the attribute this descriptor is assigned to
        # Prepending underscore is required to avoid recursion between
        # __get__() and __set__(), since those aren't called for such attribute
        self._name = "_" + name

    def __get__(self, obj: Any, objtype: Optional[type] = None) -> Optional[T]:
        # Dataclass is requesting the default value
        if obj is None:
            return self._default

        assert self._name is not None, 'Descriptor not initialized properly'

        # Value being `self` indicates that it was not provided during
        # initialization of the dataclass - supply the default value instead
        value = getattr(obj, self._name, self._default)
        if value is self:
            value = self._default
        return value

    def __set__(self, obj: Any, value: T) -> None:
        assert self._name is not None, 'Descriptor not initialized properly'

        # Prevent setting the value if it was not provided during
        # initialization. The condition is determined by checking if the
        # current value is `self` - i.e. the descriptor instance hasn't been
        # replaced with an actual value
        if getattr(obj, self._name, self._default) is self:
            raise AttributeError(
                # `_name[1:]` converts to the actual field name, see
                # __set_name__()
                f'Field {self._name[1:]} is read-only because it was not'
                ' provided during initialization'
            )

        # Set the value otherwise
        setattr(obj, self._name, value)


def field_readonly_if_not_provided(
    *args: Any, default: Optional[T] = None, **kwargs: Any
) -> T:
    """
    Helper function to create a dataclass field with ReadOnlyIfNotProvided
    descriptor.

    :param args: Positional arguments to pass to `dataclasses.field()`.
    :param default: Default value to return upon read if not provided during
     initialization.
    :param kwargs: Keyword arguments to pass to `dataclasses.field()`.
    :return: A dataclass field with ReadOnlyIfNotProvided descriptor attached.
    """
    # Also set SKIP_NONE metadata if default is None, so that the field is
    # skipped during serialization when its value is None
    if default is None:
        if 'metadata' not in kwargs:
            kwargs['metadata'] = {}
        kwargs['metadata'][Metadata.SKIP_NONE] = True

    # Instantiate the field with ReadOnlyIfNotProvided descriptor and rest of
    # the provided arguments
    # pylint: disable=invalid-field-call
    return cast(T, field(
        *args, **kwargs,
        default=ReadOnlyIfNotProvided[T](default)
    ))


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

    def serialize(self) -> List[Any]:
        """
        Returns the dataclass fields as a list.

        Handles specific metadata for the fields.
        :seealso:`Metadata`.

        :return: Dataclass serialized as list.
        """
        result = []

        for f in fields(self):
            # Skip fields marked with NO_SERIALIZE metadata
            if f.metadata.get(Metadata.NO_SERIALIZE, False):
                continue

            # Skip fields with None value if SKIP_NONE metadata is set
            if (
                f.metadata.get(Metadata.SKIP_NONE, False)
                and getattr(self, f.name) is None
            ):
                continue

            # Append field value to the result list
            result.append(getattr(self, f.name))

        return result

    async def save(self) -> None:
        """
        Save the current data to the device.
        """
        assert self.SAVE_COMMAND is not None, '`SAVE_COMMAND` must be defined'
        assert self._parent is not None, 'Please call `load()` first'

        _LOGGER.debug('Setting data to the device: %s', str(self))
        await self._parent.command(
            self.SAVE_COMMAND,
            self.serialize()
        )

    @classmethod
    async def load(
        cls: Type[DataclassLoadSaveT], parent: G90Alarm
    ) -> DataclassLoadSaveT:
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


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
    TYPE_CHECKING, Type, TypeVar, Optional, ClassVar, Any, Dict, List, Set,
    Union, Tuple, cast
)
import logging
import time
import weakref
from dataclasses import dataclass, asdict, field, fields
from .validation import ValidatorBase, _DefaultNotSet
from ..const import G90Commands
if TYPE_CHECKING:
    from ..alarm import G90Alarm


_LOGGER = logging.getLogger(__name__)
DataclassLoadSaveT = TypeVar('DataclassLoadSaveT', bound='DataclassLoadSave')
T = TypeVar('T')


class DataclassLoadPolicy:
    """
    Defines strategy for loading dataclass-backed panel configuration.
    """
    # pylint: disable=too-few-public-methods
    async def load(
        self,
        cls: Type[DataclassLoadSaveT],
        parent: G90Alarm,
        force: bool = False,
    ) -> DataclassLoadSaveT:
        """
        Load configuration according to the policy.
        """
        raise NotImplementedError()


class NoCacheDataclassLoadPolicy(DataclassLoadPolicy):
    """
    Always loads configuration from the panel.
    """
    # pylint: disable=too-few-public-methods
    async def load(
        self,
        cls: Type[DataclassLoadSaveT],
        parent: G90Alarm,
        force: bool = False,
    ) -> DataclassLoadSaveT:
        """
        Always load from the device, ignoring `force`.
        """
        return await cls.load_uncached(parent)


class TtlDataclassLoadPolicy(DataclassLoadPolicy):
    """
    Reuses loaded configuration for a given parent within a TTL.
    """
    # pylint: disable=too-few-public-methods
    def __init__(self, ttl_seconds: float) -> None:
        self._ttl_seconds = max(0.0, ttl_seconds)
        self._cache: weakref.WeakKeyDictionary[
            G90Alarm, Tuple[DataclassLoadSave, float]
        ] = weakref.WeakKeyDictionary()

    async def load(
        self,
        cls: Type[DataclassLoadSaveT],
        parent: G90Alarm,
        force: bool = False,
    ) -> DataclassLoadSaveT:
        """
        Load from cache when fresh, otherwise read from the device.
        """
        if not force and self._ttl_seconds > 0:
            cached = self._cache.get(parent)
            if cached is not None:
                obj, loaded_at_monotonic = cached
                if (
                    isinstance(obj, cls)
                    and (time.monotonic() - loaded_at_monotonic)
                    < self._ttl_seconds
                ):
                    return obj

        loaded = await cls.load_uncached(parent)
        self._cache[parent] = (loaded, time.monotonic())
        return loaded


class LoadOnceDataclassLoadPolicy(DataclassLoadPolicy):
    """
    Loads configuration from the device once per ``G90Alarm`` instance.

    Subsequent ``load`` calls return the same in-memory object until
    ``force=True`` (or the parent alarm instance is garbage-collected).
    """
    # pylint: disable=too-few-public-methods
    def __init__(self) -> None:
        self._cache: weakref.WeakKeyDictionary[
            G90Alarm, DataclassLoadSave
        ] = weakref.WeakKeyDictionary()

    async def load(
        self,
        cls: Type[DataclassLoadSaveT],
        parent: G90Alarm,
        force: bool = False,
    ) -> DataclassLoadSaveT:
        """
        Load from cache when present, otherwise read from the device.
        """
        if not force:
            cached = self._cache.get(parent)
            if cached is not None:
                obj = cached
                if isinstance(obj, cls):
                    return obj

        loaded = await cls.load_uncached(parent)
        self._cache[parent] = loaded
        return loaded


class Metadata:
    """
    Metadata keys for DataclassLoadSave fields.
    """
    # pylint: disable=too-few-public-methods
    NO_SERIALIZE = 'no_serialize'
    SKIP_NONE = 'skip_none'


class ReadOnlyIfNotProvidedError(ValueError):
    """
    Raised when assigning to a :class:`ReadOnlyIfNotProvided` field that was
    omitted during instance construction.
    """


class ReadOnlyIfNotProvided(ValidatorBase[T]):
    """
    Descriptor for dataclass fields to be read-only if not provided during
    initialization.

    The field can be read, but attempts to modify it will raise
    :class:`ReadOnlyIfNotProvidedError` (a ``ValueError`` subclass) if the
    field was not provided during initialization. In other words, the only
    way to set the value is during object creation.

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

        # Raises ReadOnlyIfNotProvidedError
        ex2 = Example()
        print(ex2.read_only_field)  # Outputs: None
        ex2.read_only_field = 100  # Raises ReadOnlyIfNotProvidedError

    :param default: Default value to return upon read if not provided during
     initialization.
    """
    # pylint: disable=too-few-public-methods

    def __validate__(self, obj: Any, value: T) -> bool:
        """
        Validation method.
        """
        # Prevent setting the value if it was not provided during
        # initialization. The condition is determined by checking if the
        # current value is `self` - i.e. the descriptor instance hasn't been
        # replaced with an actual value
        if getattr(obj, self.__field_name__, self._default) is self:
            raise ReadOnlyIfNotProvidedError(
                f'Field {self.__unmangled_name__} is read-only because'
                ' it was not provided during initialization'
            )
        return True


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
        default=ReadOnlyIfNotProvided[T](
            cast(Union[T, _DefaultNotSet], default)
        )
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
    LOAD_POLICY: ClassVar[DataclassLoadPolicy] = NoCacheDataclassLoadPolicy()

    def __post_init__(self) -> None:
        """
        Post-initialization processing.
        """
        # Instance variable to hold reference to parent G90Alarm instance,
        # declared here to avoid being part of dataclass fields
        self._parent: Optional[G90Alarm] = None
        # Track which fields were modified after initialization/loading.
        self._dirty_fields: Set[str] = set()
        self._track_field_changes = True

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Set attribute value and mark dataclass fields as dirty when modified.
        """
        object.__setattr__(self, name, value)

        if name.startswith('_'):
            return

        if not getattr(self, '_track_field_changes', False):
            return

        if not any(f.name == name for f in fields(self)):
            return

        self._dirty_fields.add(name)

    def _clear_dirty_fields(self) -> None:
        """
        Clear tracked dirty fields.
        """
        self._dirty_fields.clear()

    def _sync_from(self, other: DataclassLoadSave) -> None:
        """
        Copy all dataclass fields from another instance.
        """
        self._track_field_changes = False
        try:
            for dataclass_field in fields(self):
                current_value = getattr(self, dataclass_field.name)
                refreshed_value = getattr(other, dataclass_field.name)
                if current_value == refreshed_value:
                    continue
                try:
                    setattr(
                        self,
                        dataclass_field.name,
                        refreshed_value
                    )
                except ReadOnlyIfNotProvidedError:
                    # Omitted-at-init read-only field; validator will reject
                    # sync since it was not provided during initialization.
                    continue
        finally:
            self._track_field_changes = True

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

        Refreshes the load policy cache (if any): the initial
        ``load(..., force=True)`` repopulates the policy's entry for this
        parent with the newly loaded instance used for read-modify-write.
        """
        assert self.LOAD_COMMAND is not None, '`LOAD_COMMAND` must be defined'
        assert self.SAVE_COMMAND is not None, '`SAVE_COMMAND` must be defined'
        assert self._parent is not None, 'Please call `load()` first'

        # Reload the configuration from the device to get the latest values
        refreshed = await type(self).load(self._parent, force=True)
        # Update the dirty fields in the refreshed instance with the current
        # values from the local instance
        for field_name in self._dirty_fields:
            setattr(refreshed, field_name, getattr(self, field_name))

        _LOGGER.debug('Setting data to the device: %s', str(refreshed))
        await self._parent.command(
            self.SAVE_COMMAND,
            refreshed.serialize()
        )

        # Sync the dirty fields from the local instance to the refreshed
        # instance
        self._sync_from(refreshed)
        # Clear the dirty fields to avoid them being saved again on the next
        # `save()` call
        self._clear_dirty_fields()

    @classmethod
    async def load(
        cls: Type[DataclassLoadSaveT], parent: G90Alarm, force: bool = False
    ) -> DataclassLoadSaveT:
        """
        Create an instance with values loaded from the device.

        :param force: If True, bypass policy cache (if any).
        :return: An instance of the dataclass loaded from the device.
        """
        return await cls.LOAD_POLICY.load(cls, parent, force=force)

    @classmethod
    async def load_uncached(
        cls: Type[DataclassLoadSaveT], parent: G90Alarm
    ) -> DataclassLoadSaveT:
        """
        Create an instance with values loaded from the device bypassing cache.
        """
        assert cls.LOAD_COMMAND is not None, '`LOAD_COMMAND` must be defined'
        assert parent is not None, '`parent` must be provided'

        data = await parent.command(cls.LOAD_COMMAND)
        obj = cls(*data)
        _LOGGER.debug('Loaded data: %s', str(obj))

        obj._parent = parent
        # Clear the dirty fields to avoid them being saved again on the next
        # `save()` call
        obj._clear_dirty_fields()

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

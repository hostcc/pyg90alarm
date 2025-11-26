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
Base entity list.
"""
from abc import ABC, abstractmethod
from typing import (
    List, AsyncGenerator, Optional, TypeVar, Generic, cast, TYPE_CHECKING,
    Callable, Coroutine, Union
)
import asyncio
import logging

from ..exceptions import G90Error
from .base_entity import G90BaseEntity
from ..callback import G90Callback

T = TypeVar('T', bound=G90BaseEntity)
ListChangeCallback = Union[
    Callable[[T, bool], None],
    Callable[[T, bool], Coroutine[None, None, None]]
]

if TYPE_CHECKING:
    from ..alarm import G90Alarm
else:
    # Alias G90Alarm to object avoid circular imports
    # (`G90Alarm` -> `G90SensorList` -> `G90BaseList` -> `G90Alarm`)
    G90Alarm = object

_LOGGER = logging.getLogger(__name__)


class G90BaseList(Generic[T], ABC):
    """
    Base entity list class.

    :param parent: Parent alarm panel instance.
    """
    def __init__(self, parent: G90Alarm) -> None:
        self._entities: List[T] = []
        self._lock = asyncio.Lock()
        self._parent = parent
        self._list_change_cb: Optional[ListChangeCallback[T]] = None

    @abstractmethod
    async def _fetch(self) -> AsyncGenerator[T, None]:
        """
        Fetch the list of entities from the panel.

        :return: Async generator of entities
        """
        yield cast(T, None)  # pragma: no cover

    @property
    async def entities(self) -> List[T]:
        """
        Return the list of entities.

        :meth:`update` is called if the list is empty.

        :return: List of entities
        """
        # Please see below for the explanation of the lock usage
        async with self._lock:
            entities = self._entities

        if not entities:
            return await self.update()

        return entities

    async def update(self) -> List[T]:
        """
        Update the list of entities from the panel.

        :return: List of entities
        """
        # Use lock around the operation, to ensure no duplicated entries in the
        # resulting list or redundant exchanges with panel are made when the
        # method is called concurrently
        async with self._lock:
            entities = self._fetch()

            non_existing_entities = self._entities.copy()
            try:
                async for entity in entities:
                    try:
                        existing_entity = next(
                            x for x in self._entities if x == entity
                        )
                    except StopIteration:
                        existing_entity = None

                    if existing_entity is not None:
                        # Update the existing entity with the new data
                        _LOGGER.debug(
                            "Updating existing entity '%s' from protocol"
                            " data '%s'", existing_entity, entity
                        )

                        existing_entity.update(entity)
                        non_existing_entities.remove(existing_entity)

                        # Invoke the list change callback for the existing
                        # entity to notify about the update
                        G90Callback.invoke(
                            self._list_change_cb, existing_entity, False
                        )
                    else:
                        # Add the new entity to the list
                        _LOGGER.debug('Adding new entity: %s', entity)
                        self._entities.append(entity)
                        # Invoke the list change callback for the new entity
                        G90Callback.invoke(self._list_change_cb, entity, True)
            except TypeError as err:
                _LOGGER.error(
                    'Failed to fetch entities: %s', err
                )
                raise G90Error(err) from err

            # Mark the entities that are no longer in the list
            for unavailable_entity in non_existing_entities:
                _LOGGER.debug(
                    'Marking entity as unavailable: %s', unavailable_entity
                )
                unavailable_entity.is_unavailable = True

            _LOGGER.debug(
                'Total number of entities: %s, unavailable: %s',
                len(self._entities), len(non_existing_entities)
            )

            return self._entities

    async def find_by_idx(
        self, idx: int, exclude_unavailable: bool, subindex: int = 0
    ) -> Optional[T]:
        """
        Finds entity by index.

        :param idx: Entity index
        :param exclude_unavailable: Exclude unavailable entities
        :param subindex: Entity subindex
        :return: Entity instance or None if not found
        """
        entities = await self.entities

        found = None
        if idx < len(entities):
            entity = entities[idx]
            if entity.index == idx and entity.subindex == subindex:
                # Fast lookup by direct index
                _LOGGER.debug('Found entity via fast lookup: %s', entity)
                found = entity

        if not found:
            for entity in entities:
                if entity.index == idx and entity.subindex == subindex:
                    _LOGGER.debug('Found entity: %s', entity)
                    found = entity

        if found:
            if not exclude_unavailable or not found.is_unavailable:
                return found

            _LOGGER.debug(
                'Entity is found but unavailable, will result in none returned'
            )

        _LOGGER.error(
            'Entity not found by index=%s and subindex=%s', idx, subindex
        )
        return None

    async def find(
        self, idx: int, name: str, exclude_unavailable: bool, subindex: int = 0
    ) -> Optional[T]:
        """
        Finds entity by index, subindex and name.

        :param idx: Entity index
        :param name: Entity name
        :param exclude_unavailable: Exclude unavailable entities
        :param subindex: Entity subindex
        :return: Entity instance or None if not found
        """
        found = await self.find_by_idx(idx, exclude_unavailable, subindex)
        if not found:
            return None

        if found.name == name:
            return found

        _LOGGER.error(
            'Entity not found: index=%s, subindex=%s, name=%s',
            idx, subindex, name
        )
        return None

    async def find_free_idx(self) -> int:
        """
        Finds the first free index in the list.

        The index is from protocol point of view (`.index` attribute of the
        protocol data), not the index in the list. The index is required when
        registering a new entity on the panel.

        :return: Free index
        """
        entities = await self.entities

        # Collect indexes in use by the existing entities
        occupied_indexes = set(x.index for x in entities)
        # Generate a set of possible indexes from 0 to the maximum index in
        # use, or provide an empty set if there are no existing entities
        if occupied_indexes:
            possible_indexes = set(range(0, max(occupied_indexes)))
        else:
            # No occupied indexes, so possible_indexes is empty
            possible_indexes = set()

        try:
            # Find the first free index by taking difference between
            # possible indexes and occupied ones, and then taking the minimum
            # value off the difference
            free_idx = min(
                possible_indexes.difference(occupied_indexes)
            )
        except ValueError:
            # If no gaps in existing indexes, then return the index next to
            # the last existing entity
            free_idx = len(entities)

        _LOGGER.debug(
            'Found free index=%s out of occupied indexes: %s',
            free_idx, occupied_indexes
        )
        return free_idx

    @property
    def list_change_callback(self) -> Optional[ListChangeCallback[T]]:
        """
        List change callback.

        Invoked when the list of entities is changed, i.e. when a new entity is
        added or an existing one is updated.

        :return: Callback
        """
        return self._list_change_cb

    @list_change_callback.setter
    def list_change_callback(self, value: ListChangeCallback[T]) -> None:
        self._list_change_cb = value

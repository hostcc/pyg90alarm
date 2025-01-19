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
)
import asyncio
import logging

from .base_entity import G90BaseEntity
if TYPE_CHECKING:
    from ..alarm import G90Alarm
else:
    # Alias G90Alarm to object avoid circular imports
    # (`G90Alarm` -> `G90SensorList` -> `G90BaseList` -> `G90Alarm`)
    G90Alarm = object

T = TypeVar('T', bound=G90BaseEntity)
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

    @abstractmethod
    async def _fetch(self) -> AsyncGenerator[T, None]:
        """
        Fetch the list of entities from the panel.

        :return: Async generator of entities
        """
        yield cast(T, None)

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
            async for entity in entities:
                try:
                    existing_entity_idx = self._entities.index(entity)
                except ValueError:
                    existing_entity_idx = None

                if existing_entity_idx is not None:
                    existing_entity = self._entities[existing_entity_idx]
                    # Update the existing entity with the new data
                    _LOGGER.debug(
                        "Updating existing entity '%s' from protocol"
                        " data '%s'", existing_entity, entity
                    )

                    self._entities[existing_entity_idx].update(entity)
                    non_existing_entities.remove(entity)
                else:
                    # Add the new entity to the list
                    _LOGGER.debug('Adding new entity: %s', entity)
                    self._entities.append(entity)

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

    async def find(
        self, idx: int, name: str, exclude_unavailable: bool
    ) -> Optional[T]:
        """
        Finds entity by index and name.

        :param idx: Entity index
        :param name: Entity name
        :param exclude_unavailable: Exclude unavailable entities
        :return: Entity instance
        """
        entities = await self.entities

        found = None
        # Fast lookup by direct index
        if idx < len(entities) and entities[idx].name == name:
            entity = entities[idx]
            _LOGGER.debug('Found entity via fast lookup: %s', entity)
            found = entity

        # Fast lookup failed, perform slow one over the whole entities list
        if not found:
            for entity in entities:
                if entity.index == idx and entity.name == name:
                    _LOGGER.debug('Found entity: %s', entity)
                    found = entity

        if found:
            if not exclude_unavailable or not found.is_unavailable:
                return found

            _LOGGER.debug(
                'Entity is found but unavailable, will result in none returned'
            )

        _LOGGER.error('Entity not found: idx=%s, name=%s', idx, name)
        return None

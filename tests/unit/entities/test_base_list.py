"""
Tests for G90BaseList class
"""
from __future__ import annotations
from typing import AsyncGenerator
from unittest.mock import MagicMock

from pyg90alarm.entities.base_list import G90BaseList


class TestBaseList(G90BaseList[MagicMock]):
    """
    Mock subclass for testing G90BaseList.
    """

    # Prevent pytest from collecting this class as a test case
    __test__ = False

    async def _fetch(self) -> AsyncGenerator[MagicMock, None]:
        """Mock _fetch method."""
        if False:  # pragma: no cover
            yield MagicMock()


async def test_find_free_idx_empty_list() -> None:
    """
    Tests find_free_idx with empty entities list.
    """

    parent = MagicMock()
    base_list = TestBaseList(parent)
    base_list._entities = []

    result = await base_list.find_free_idx()

    assert result == 0


async def test_find_free_idx_one_entity_at_zero() -> None:
    """
    Tests find_free_idx with one entity at index 0.
    """

    base_list = TestBaseList(parent=MagicMock())
    base_list._entities = [MagicMock(index=0)]

    result = await base_list.find_free_idx()

    assert result == 1


async def test_find_free_idx_returns_lowest_available_index() -> None:
    """
    Tests find_free_idx with two entities at indexes 10 and 11.
    """

    base_list = TestBaseList(parent=MagicMock())
    base_list._entities = [MagicMock(index=10), MagicMock(index=11)]

    result = await base_list.find_free_idx()

    assert result == 0


async def test_find_free_idx_returns_lowest_available_index_over_gap() -> None:
    """
    Tests find_free_idx with two entities at indexes 10 and 11.
    """

    base_list = TestBaseList(parent=MagicMock())
    base_list._entities = [
        MagicMock(index=0), MagicMock(index=10), MagicMock(index=11)
    ]

    result = await base_list.find_free_idx()

    assert result == 1


async def test_find_entity_by_idx_and_name() -> None:
    """
    Tests find with matching index, subindex, and name.
    """

    base_list = TestBaseList(parent=MagicMock())
    entity = MagicMock()
    entity.index = 0
    entity.subindex = 0
    entity.name = "Test Entity"
    entity.is_unavailable = False
    base_list._entities = [entity]

    result = await base_list.find(
        idx=0, name="Test Entity", exclude_unavailable=False
    )

    assert result == entity


async def test_find_entity_name_mismatch() -> None:
    """
    Tests find with matching index but mismatched name.
    """

    base_list = TestBaseList(parent=MagicMock())
    entity = MagicMock()
    entity.index = 0
    entity.subindex = 0
    entity.name = "Test Entity"
    entity.is_unavailable = False
    base_list._entities = [entity]

    result = await base_list.find(
        idx=0, name="Wrong Name", exclude_unavailable=False
    )

    assert result is None


async def test_find_entity_not_found() -> None:
    """
    Tests find with non-existing index.
    """

    base_list = TestBaseList(parent=MagicMock())
    base_list._entities = []

    result = await base_list.find(
        idx=0, name="Test Entity", exclude_unavailable=False
    )

    assert result is None


async def test_find_entity_unavailable_excluded() -> None:
    """
    Tests find with unavailable entity and exclude_unavailable=True.
    """

    base_list = TestBaseList(parent=MagicMock())
    entity = MagicMock()
    entity.index = 0
    entity.subindex = 0
    entity.name = "Test Entity"
    entity.is_unavailable = True
    base_list._entities = [entity]

    result = await base_list.find(
        idx=0, name="Test Entity", exclude_unavailable=True
    )

    assert result is None


async def test_find_entity_unavailable_not_excluded() -> None:
    """
    Tests find with unavailable entity and exclude_unavailable=False.
    """

    base_list = TestBaseList(parent=MagicMock())
    entity = MagicMock()
    entity.index = 0
    entity.subindex = 0
    entity.name = "Test Entity"
    entity.is_unavailable = True
    base_list._entities = [entity]

    result = await base_list.find(
        idx=0, name="Test Entity", exclude_unavailable=False
    )

    assert result == entity


async def test_find_entity_with_subindex() -> None:
    """
    Tests find with specific subindex.
    """

    base_list = TestBaseList(parent=MagicMock())
    entity = MagicMock()
    entity.index = 0
    entity.subindex = 1
    entity.name = "Test Entity"
    entity.is_unavailable = False
    base_list._entities = [entity]

    result = await base_list.find(
        idx=0, name="Test Entity", exclude_unavailable=False, subindex=1
    )

    assert result == entity

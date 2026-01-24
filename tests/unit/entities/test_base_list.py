"""
Tests for G90BaseList class
"""
from __future__ import annotations
from typing import AsyncGenerator
from unittest.mock import MagicMock

from pyg90alarm.entities.base_list import G90BaseList


async def test_find_free_idx_empty_list() -> None:
    """
    Tests find_free_idx with empty entities list.
    """
    class TestClass(G90BaseList[MagicMock]):
        """
        Mock subclass for testing G90BaseList.
        """
        async def _fetch(self) -> AsyncGenerator[MagicMock, None]:
            """
            Mock no entities.
            """
            x: MagicMock
            for x in []:
                yield x

    base_list = TestClass(parent=MagicMock())
    result = await base_list.find_free_idx()

    assert result == 0


async def test_find_free_idx_one_entity_at_zero() -> None:
    """
    Tests find_free_idx with one entity at index 0.
    """
    class TestClass(G90BaseList[MagicMock]):
        """
        Mock subclass for testing G90BaseList.
        """
        async def _fetch(self) -> AsyncGenerator[MagicMock, None]:
            """
            Mock one entity at index 0.
            """
            for x in [MagicMock(index=0)]:
                yield x

    base_list = TestClass(parent=MagicMock())
    result = await base_list.find_free_idx()

    assert result == 1


async def test_find_free_idx_returns_lowest_available_index() -> None:
    """
    Tests find_free_idx with two entities at indexes 10 and 11.
    """
    class TestClass(G90BaseList[MagicMock]):
        """
        Mock subclass for testing G90BaseList.
        """
        async def _fetch(self) -> AsyncGenerator[MagicMock, None]:
            """
            Mock entities at indexes 10 and 11.
            """
            for x in [MagicMock(index=10), MagicMock(index=11)]:
                yield x

    base_list = TestClass(parent=MagicMock())
    result = await base_list.find_free_idx()

    assert result == 0


async def test_find_free_idx_returns_lowest_available_index_over_gap() -> None:
    """
    Tests find_free_idx with two entities at indexes 10 and 11.
    """
    class TestClass(G90BaseList[MagicMock]):
        """
        Mock subclass for testing G90BaseList.
        """
        async def _fetch(self) -> AsyncGenerator[MagicMock, None]:
            """
            Mock entities at indexes 0, 10 and 11.
            """
            for x in [
                MagicMock(index=0), MagicMock(index=10), MagicMock(index=11)
            ]:
                yield x

    base_list = TestClass(parent=MagicMock())
    result = await base_list.find_free_idx()

    assert result == 1


async def test_find_entity_by_idx_and_name() -> None:
    """
    Tests find with matching index, subindex, and name.
    """
    entity = MagicMock()
    entity.index = 0
    entity.subindex = 0
    entity.name = "Test Entity"
    entity.is_unavailable = False

    class TestClass(G90BaseList[MagicMock]):
        """
        Mock subclass for testing G90BaseList.
        """
        async def _fetch(self) -> AsyncGenerator[MagicMock, None]:
            """
            Mock one entity.
            """
            yield entity

    base_list = TestClass(parent=MagicMock())
    result = await base_list.find(
        idx=0, name="Test Entity", exclude_unavailable=False
    )

    assert result == entity


async def test_find_entity_name_mismatch() -> None:
    """
    Tests find with matching index but mismatched name.
    """
    class TestClass(G90BaseList[MagicMock]):
        """
        Mock subclass for testing G90BaseList.
        """
        async def _fetch(self) -> AsyncGenerator[MagicMock, None]:
            """
            Mock one entity.
            """
            entity = MagicMock()
            entity.index = 0
            entity.subindex = 0
            entity.name = "Test Entity"
            entity.is_unavailable = False
            yield entity

    base_list = TestClass(parent=MagicMock())
    result = await base_list.find(
        idx=0, name="Wrong Name", exclude_unavailable=False
    )

    assert result is None


async def test_find_entity_not_found() -> None:
    """
    Tests find with non-existing index.
    """
    class TestClass(G90BaseList[MagicMock]):
        """
        Mock subclass for testing G90BaseList.
        """
        async def _fetch(self) -> AsyncGenerator[MagicMock, None]:
            """
            Mock no entities.
            """
            x: MagicMock
            for x in []:
                yield x

    base_list = TestClass(parent=MagicMock())
    result = await base_list.find(
        idx=0, name="Test Entity", exclude_unavailable=False
    )

    assert result is None


async def test_find_entity_unavailable_excluded() -> None:
    """
    Tests find with unavailable entity and exclude_unavailable=True.
    """
    class TestClass(G90BaseList[MagicMock]):
        """
        Mock subclass for testing G90BaseList.
        """
        async def _fetch(self) -> AsyncGenerator[MagicMock, None]:
            """
            Mock one entity.
            """
            entity = MagicMock()
            entity.index = 0
            entity.subindex = 0
            entity.name = "Test Entity"
            entity.is_unavailable = True
            yield entity

    base_list = TestClass(parent=MagicMock())
    result = await base_list.find(
        idx=0, name="Test Entity", exclude_unavailable=True
    )

    assert result is None


async def test_find_entity_unavailable_not_excluded() -> None:
    """
    Tests find with unavailable entity and exclude_unavailable=False.
    """
    entity = MagicMock()
    entity.index = 0
    entity.subindex = 0
    entity.name = "Test Entity"
    entity.is_unavailable = True

    class TestClass(G90BaseList[MagicMock]):
        """
        Mock subclass for testing G90BaseList.
        """
        async def _fetch(self) -> AsyncGenerator[MagicMock, None]:
            """
            Mock one entity.
            """
            yield entity

    base_list = TestClass(parent=MagicMock())
    result = await base_list.find(
        idx=0, name="Test Entity", exclude_unavailable=False
    )

    assert result == entity


async def test_find_entity_with_subindex() -> None:
    """
    Tests find with specific subindex.
    """
    entity = MagicMock()
    entity.index = 0
    entity.subindex = 1
    entity.name = "Test Entity"
    entity.is_unavailable = False

    class TestClass(G90BaseList[MagicMock]):
        """
        Mock subclass for testing G90BaseList.
        """
        async def _fetch(self) -> AsyncGenerator[MagicMock, None]:
            """
            Mock one entity.
            """
            yield entity

    base_list = TestClass(parent=MagicMock())
    result = await base_list.find(
        idx=0, name="Test Entity", exclude_unavailable=False, subindex=1
    )

    assert result == entity


async def test_duplicate_entities() -> None:
    """
    Tests that duplicate entities are handled correctly during update.
    """
    existing_entity = MagicMock()
    existing_entity.index = 1
    existing_entity.subindex = 0
    existing_entity.name = "Existing entity"
    existing_entity.is_unavailable = False

    new_entity = MagicMock()
    new_entity.index = 1
    new_entity.subindex = 0
    new_entity.name = "Test entity"
    new_entity.is_unavailable = False

    mock_entities = iter([
        # Initial fetch returns one existing entity
        [existing_entity],
        # Second fetch returns duplicate new entities
        [new_entity, new_entity],
    ])

    class TestClass(G90BaseList[MagicMock]):
        """
        Mock subclass for testing G90BaseList.
        """
        async def _fetch(self) -> AsyncGenerator[MagicMock, None]:
            """
            Mock test list entities.
            """
            # Yield entities under test
            for x in next(mock_entities):
                yield x

    base_list = TestClass(parent=MagicMock())
    # Initial update to simulate the existing entity
    await base_list.update()
    # Second update to test handling of duplicates, should not raise
    result = await base_list.update()

    assert len(result) == 2
    # Initial entities not present in second update result should be marked
    # unavailable
    assert result[0] == existing_entity
    assert result[0].is_unavailable is True
    assert result[1] == new_entity

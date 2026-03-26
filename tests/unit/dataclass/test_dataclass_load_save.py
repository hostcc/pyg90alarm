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
Unit tests for DataclassLoadSave functionality.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from unittest.mock import AsyncMock, call, patch

import pytest

from pyg90alarm.const import G90Commands
from pyg90alarm.dataclass.load_save import (
    DataclassLoadSave,
    LoadOnceDataclassLoadPolicy,
    Metadata,
    TtlDataclassLoadPolicy,
    field_readonly_if_not_provided,
)


@dataclass
class SimpleReadOnlyConfig(DataclassLoadSave):
    """
    Test dataclass with read-only field.
    """
    LOAD_COMMAND = G90Commands.GETHOSTINFO
    SAVE_COMMAND = G90Commands.SETHOSTSTATUS

    read_only_field: Optional[int] = field_readonly_if_not_provided(
        default=None
    )
    regular_field: int = 0


def test_mixed_readonly_and_metadata_asdict() -> None:
    """
    Test _asdict with both read-only fields and metadata.
    """

    @dataclass
    class TestClass(DataclassLoadSave):
        """
        Test dataclass combining read-only fields with metadata.
        """
        readonly_normal: int = field_readonly_if_not_provided(default=100)
        readonly_skip_none: Optional[int] = field_readonly_if_not_provided(
            default=None
        )
        regular_no_serialize: int = field(
            default=200, metadata={Metadata.NO_SERIALIZE: True}
        )
        regular_skip_none: Optional[int] = field(
            default=None, metadata={Metadata.SKIP_NONE: True}
        )

    obj = TestClass(readonly_normal=101)
    result = obj._asdict()

    assert result["readonly_normal"] == 101
    assert result["readonly_skip_none"] is None
    assert result["regular_no_serialize"] == 200
    assert result["regular_skip_none"] is None


async def test_load_creates_instance_with_parent() -> None:
    """
    Test that load() creates an instance and sets parent.
    """
    mock_parent = AsyncMock()
    mock_parent.command = AsyncMock(return_value=[42, 0])

    obj = await SimpleReadOnlyConfig.load(mock_parent)

    assert obj.read_only_field == 42
    assert obj.regular_field == 0
    assert obj._parent is mock_parent


async def test_load_with_readonly_fields() -> None:
    """
    Test load() with multiple read-only fields.
    """

    @dataclass
    class MultipleReadOnlyConfig(DataclassLoadSave):
        """
        Test dataclass with multiple read-only fields.
        """
        LOAD_COMMAND = G90Commands.GETHOSTINFO
        SAVE_COMMAND = G90Commands.SETHOSTSTATUS

        required_field: int = field_readonly_if_not_provided(
            default=42
        )
        optional_field: Optional[str] = field_readonly_if_not_provided(
            default=None
        )
        regular_field: str = "test"

    mock_parent = AsyncMock()
    mock_parent.command = AsyncMock(return_value=[99, "value", "test"])

    obj = await MultipleReadOnlyConfig.load(mock_parent)

    assert obj.required_field == 99
    assert obj.optional_field == "value"
    assert obj.regular_field == "test"


async def test_save_calls_parent_command() -> None:
    """
    Test that save() calls parent.command with serialized data.
    """
    mock_parent = AsyncMock()
    mock_parent.command = AsyncMock(return_value=[42, 0])
    obj = await SimpleReadOnlyConfig.load(mock_parent)

    await obj.save()

    mock_parent.command.assert_has_calls(
        [
            call(G90Commands.GETHOSTINFO),
            call(G90Commands.GETHOSTINFO),
            call(G90Commands.SETHOSTSTATUS, [42, 0]),
        ]
    )


async def test_save_without_parent_raises_assertion() -> None:
    """
    Test that save() raises AssertionError if parent is not set.
    """
    obj = SimpleReadOnlyConfig()

    with pytest.raises(AssertionError):
        await obj.save()


async def test_load_command_required() -> None:
    """
    Test that DataclassLoadSave requires LOAD_COMMAND.
    """

    @dataclass
    class NoLoadCommand(DataclassLoadSave):
        LOAD_COMMAND = None

        field1: int = 0

    with pytest.raises(AssertionError):
        await NoLoadCommand.load(AsyncMock())


async def test_save_command_required() -> None:
    """
    Test that DataclassLoadSave requires SAVE_COMMAND.
    """

    @dataclass
    class NoSaveCommand(DataclassLoadSave):
        SAVE_COMMAND = None

        field1: int = 0

    obj = NoSaveCommand()
    obj._parent = AsyncMock()

    with pytest.raises(AssertionError):
        await obj.save()


async def test_save_read_modify_write_preserves_external_fields() -> None:
    """
    Test save() overlays local dirty fields on refreshed panel data.
    """
    mock_parent = AsyncMock()
    mock_parent.command = AsyncMock(
        side_effect=[
            [10, 20],  # initial load
            [11, 21],  # refresh during save
            None,      # save command result
        ]
    )

    obj = await SimpleReadOnlyConfig.load(mock_parent)
    obj.regular_field = 99
    await obj.save()

    mock_parent.command.assert_has_calls(
        [
            call(G90Commands.GETHOSTINFO),
            call(G90Commands.GETHOSTINFO),
            call(G90Commands.SETHOSTSTATUS, [11, 99]),
        ]
    )
    assert obj.read_only_field == 11
    assert obj.regular_field == 99


async def test_save_read_modify_write_with_multiple_dirty_fields() -> None:
    """
    Test save() overlays multiple local dirty fields on refreshed data.
    """

    @dataclass
    class MultiFieldConfig(DataclassLoadSave):
        LOAD_COMMAND = G90Commands.GETHOSTINFO
        SAVE_COMMAND = G90Commands.SETHOSTSTATUS

        a: int = 0
        b: int = 0
        c: int = 0

    mock_parent = AsyncMock()
    mock_parent.command = AsyncMock(
        side_effect=[
            [1, 2, 3],   # initial load
            [10, 20, 30],  # refresh during save
            None,          # save command result
        ]
    )
    obj = await MultiFieldConfig.load(mock_parent)
    obj.a = 100
    obj.c = 300

    await obj.save()

    mock_parent.command.assert_has_calls(
        [
            call(G90Commands.GETHOSTINFO),
            call(G90Commands.GETHOSTINFO),
            call(G90Commands.SETHOSTSTATUS, [100, 20, 300]),
        ]
    )
    assert obj.a == 100
    assert obj.b == 20
    assert obj.c == 300


@dataclass
class LoadOnceTestConfig(DataclassLoadSave):
    """
    Config using load-once policy for unit tests.
    """
    LOAD_COMMAND = G90Commands.GETHOSTINFO
    SAVE_COMMAND = G90Commands.SETHOSTSTATUS
    LOAD_POLICY = LoadOnceDataclassLoadPolicy()

    x: int = 0


async def test_load_once_policy_reuses_instance() -> None:
    """
    Load-once returns the same object for repeated loads; ``force`` refetches.
    """
    mock_parent = AsyncMock()
    mock_parent.command = AsyncMock(return_value=[1])

    first = await LoadOnceTestConfig.load(mock_parent)
    second = await LoadOnceTestConfig.load(mock_parent)
    assert first is second
    assert mock_parent.command.call_count == 1

    refreshed = await LoadOnceTestConfig.load(mock_parent, force=True)
    assert mock_parent.command.call_count == 2
    assert refreshed is not first

    third = await LoadOnceTestConfig.load(mock_parent)
    assert third is refreshed
    assert mock_parent.command.call_count == 2


async def test_ttl_policy_reuses_instance_within_ttl() -> None:
    """
    TTL policy should return cached instance while entry is fresh.
    """

    @dataclass
    class TtlConfig(DataclassLoadSave):
        LOAD_COMMAND = G90Commands.GETHOSTINFO
        SAVE_COMMAND = G90Commands.SETHOSTSTATUS
        LOAD_POLICY = TtlDataclassLoadPolicy(ttl_seconds=10.0)

        x: int = 0

    mock_parent = AsyncMock()
    mock_parent.command = AsyncMock(side_effect=[[1], [2]])

    with patch(
        "pyg90alarm.dataclass.load_save.time.monotonic",
        side_effect=[100.0, 105.0],
    ):
        first = await TtlConfig.load(mock_parent)
        second = await TtlConfig.load(mock_parent)

    assert first is second
    assert first.x == 1
    assert mock_parent.command.call_count == 1


async def test_ttl_policy_refreshes_after_expiry() -> None:
    """
    TTL policy should reload when cached entry is stale.
    """

    @dataclass
    class TtlConfig(DataclassLoadSave):
        LOAD_COMMAND = G90Commands.GETHOSTINFO
        SAVE_COMMAND = G90Commands.SETHOSTSTATUS
        LOAD_POLICY = TtlDataclassLoadPolicy(ttl_seconds=10.0)

        x: int = 0

    mock_parent = AsyncMock()
    mock_parent.command = AsyncMock(side_effect=[[1], [2]])

    with patch(
        "pyg90alarm.dataclass.load_save.time.monotonic",
        side_effect=[100.0, 111.0, 112.0],
    ):
        first = await TtlConfig.load(mock_parent)
        second = await TtlConfig.load(mock_parent)

    assert first is not second
    assert first.x == 1
    assert second.x == 2
    assert mock_parent.command.call_count == 2


async def test_ttl_policy_force_refreshes_even_within_ttl() -> None:
    """
    TTL policy should bypass cache when ``force=True``.
    """

    @dataclass
    class TtlConfig(DataclassLoadSave):
        LOAD_COMMAND = G90Commands.GETHOSTINFO
        SAVE_COMMAND = G90Commands.SETHOSTSTATUS
        LOAD_POLICY = TtlDataclassLoadPolicy(ttl_seconds=10.0)

        x: int = 0

    mock_parent = AsyncMock()
    mock_parent.command = AsyncMock(side_effect=[[1], [2]])

    with patch(
        "pyg90alarm.dataclass.load_save.time.monotonic",
        side_effect=[100.0, 101.0],
    ):
        first = await TtlConfig.load(mock_parent)
        second = await TtlConfig.load(mock_parent, force=True)

    assert first is not second
    assert first.x == 1
    assert second.x == 2
    assert mock_parent.command.call_count == 2


@dataclass
class ReadOnlySyncConfig(DataclassLoadSave):
    """
    Config with ReadOnlyIfNotProvided field for _sync_from tests.
    """
    LOAD_COMMAND = G90Commands.GETHOSTINFO
    SAVE_COMMAND = G90Commands.SETHOSTSTATUS

    ro: Optional[int] = field_readonly_if_not_provided(default=None)
    x: int = 0


def test_sync_from_skips_ro_not_provided_when_refresh_has_value() -> None:
    """
    Never-provided read-only fields must not be setattr-synced from refresh.
    """
    local = ReadOnlySyncConfig(x=1)
    refreshed = ReadOnlySyncConfig(ro=50, x=2)
    local._sync_from(refreshed)
    assert local.ro is None
    assert local.x == 2


def test_sync_from_updates_readonly_when_explicitly_provided() -> None:
    """
    Read-only fields provided at init (including explicit None) may sync.
    """
    local = ReadOnlySyncConfig(ro=None, x=1)
    refreshed = ReadOnlySyncConfig(ro=50, x=1)
    local._sync_from(refreshed)
    assert local.ro == 50

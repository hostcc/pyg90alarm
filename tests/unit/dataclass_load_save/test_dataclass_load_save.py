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
from unittest.mock import AsyncMock, call

import pytest

from pyg90alarm.const import G90Commands
from pyg90alarm.local.dataclass_load_save import (
    DataclassLoadSave,
    Metadata,
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
    obj = SimpleReadOnlyConfig(read_only_field=42)
    obj._parent = mock_parent

    await obj.save()

    mock_parent.command.assert_called_once()
    mock_parent.command.assert_has_calls([
        call(G90Commands.SETHOSTSTATUS, [42, 0])
    ])


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

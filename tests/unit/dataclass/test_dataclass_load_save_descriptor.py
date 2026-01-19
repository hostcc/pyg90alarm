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
Unit tests for ReadOnlyIfNotProvided descriptor, field_readonly_if_not_provided
function.
"""
from __future__ import annotations
from dataclasses import dataclass, fields
from typing import Any, Optional

import pytest

from pyg90alarm.dataclass.load_save import (
    DataclassLoadSave,
    Metadata,
    field_readonly_if_not_provided,
)


@dataclass
class SimpleReadOnlyConfig(DataclassLoadSave):
    """
    Test dataclass with read-only field.
    """
    read_only_field: Optional[int] = field_readonly_if_not_provided(
        default=None
    )
    regular_field: int = 0


@pytest.mark.parametrize(
    "default_value,expected_default",
    [
        pytest.param(None, None, id="None default"),
        pytest.param(42, 42, id="int default"),
        pytest.param("test", "test", id="str default"),
        pytest.param([1, 2, 3], [1, 2, 3], id="list default"),
        pytest.param({"key": "value"}, {"key": "value"}, id="dict default"),
    ],
)
def test_readonly_descriptor_read_not_provided(
    default_value: Any, expected_default: Any
) -> None:
    """
    Test reading a read-only field that was not provided during initialization.
    """

    @dataclass
    class TestClass:
        field_ro: Any = field_readonly_if_not_provided(default=default_value)

    obj = TestClass()
    assert obj.field_ro == expected_default


@pytest.mark.parametrize(
    "init_value,expected_value",
    [
        pytest.param(42, 42, id="int value"),
        pytest.param("hello", "hello", id="str value"),
        pytest.param([1, 2], [1, 2], id="list value"),
        pytest.param(0, 0, id="zero value"),
        pytest.param("", "", id="empty string"),
    ],
)
def test_readonly_descriptor_read_provided(
    init_value: Any, expected_value: Any
) -> None:
    """
    Test reading a read-only field that was provided during initialization.
    """

    @dataclass
    class TestClass:
        field_ro: Any = field_readonly_if_not_provided(default=None)

    obj = TestClass(field_ro=init_value)
    assert obj.field_ro == expected_value


def test_readonly_descriptor_write_not_provided_raises_error() -> None:
    """
    Test that writing to a non-provided read-only field raises ValueError.
    """
    obj = SimpleReadOnlyConfig()

    with pytest.raises(ValueError):
        obj.read_only_field = 100


def test_readonly_descriptor_write_provided_succeeds() -> None:
    """
    Test that writing to a provided read-only field succeeds.
    """
    obj = SimpleReadOnlyConfig(read_only_field=42)

    # Should not raise
    obj.read_only_field = 100
    assert obj.read_only_field == 100


@pytest.mark.parametrize(
    "new_value",
    [
        pytest.param(123, id="int value"),
        pytest.param(0, id="zero"),
        pytest.param(-1, id="negative"),
        pytest.param(None, id="None"),
    ],
)
def test_readonly_descriptor_write_provided_multiple_values(
    new_value: Any,
) -> None:
    """
    Test writing multiple values to a provided read-only field.
    """
    obj = SimpleReadOnlyConfig(read_only_field=1)

    obj.read_only_field = new_value
    assert obj.read_only_field == new_value


def test_readonly_descriptor_multiple_instances_independent() -> None:
    """
    Test that read-only descriptors work independently for different instances.
    """
    obj1 = SimpleReadOnlyConfig(read_only_field=10)
    obj2 = SimpleReadOnlyConfig()

    # obj1 should allow writes
    obj1.read_only_field = 20
    assert obj1.read_only_field == 20

    # obj2 should raise on write
    with pytest.raises(ValueError):
        obj2.read_only_field = 30

    # Values should be independent
    assert obj1.read_only_field == 20
    assert obj2.read_only_field is None


def test_readonly_descriptor_error_message_includes_field_name() -> None:
    """
    Test that ValueError message includes the correct field name.
    """
    obj = SimpleReadOnlyConfig()

    with pytest.raises(ValueError) as exc_info:
        obj.read_only_field = 100

    assert "read_only_field" in str(exc_info.value)
    assert "read-only" in str(exc_info.value)


def test_field_readonly_creates_dataclass_field() -> None:
    """
    Test that field_readonly_if_not_provided returns a valid dataclass field.
    """

    @dataclass
    class TestClass:
        field_ro: int = field_readonly_if_not_provided(default=42)

    obj = TestClass()
    assert obj.field_ro == 42


def test_field_readonly_with_none_default_sets_skip_none_metadata() -> None:
    """
    Test that SKIP_NONE metadata is set when default is None.
    """

    @dataclass
    class TestClass(DataclassLoadSave):
        field_ro: Optional[int] = field_readonly_if_not_provided(default=None)

    field_meta = fields(TestClass)[0]
    assert Metadata.SKIP_NONE in field_meta.metadata
    assert field_meta.metadata[Metadata.SKIP_NONE] is True


def test_field_readonly_with_non_none_default_no_skip_none() -> None:
    """
    Test that SKIP_NONE is not set when default is not None.
    """

    @dataclass
    class TestClass:
        field_ro: int = field_readonly_if_not_provided(default=42)

    field_meta = fields(TestClass)[0]
    assert Metadata.SKIP_NONE not in field_meta.metadata


def test_field_readonly_preserves_existing_metadata() -> None:
    """
    Test that field_readonly_if_not_provided preserves existing metadata.
    """

    @dataclass
    class TestClass:
        field_ro: Optional[int] = field_readonly_if_not_provided(
            default=None, metadata={Metadata.NO_SERIALIZE: True}
        )

    field_meta = fields(TestClass)[0]
    assert Metadata.SKIP_NONE in field_meta.metadata
    assert Metadata.NO_SERIALIZE in field_meta.metadata


def test_field_readonly_with_custom_metadata() -> None:
    """
    Test field_readonly_if_not_provided with custom metadata dict.
    """

    @dataclass
    class TestClass:
        field_ro: Optional[str] = field_readonly_if_not_provided(
            default=None, metadata={"custom_key": "custom_value"}
        )

    field_meta = fields(TestClass)[0]
    assert field_meta.metadata["custom_key"] == "custom_value"
    assert Metadata.SKIP_NONE in field_meta.metadata


def test_multiple_readonly_fields_independent() -> None:
    """
    Test that multiple read-only fields are independent.
    """

    @dataclass
    class TestClass(DataclassLoadSave):
        """
        Test dataclass with multiple read-only fields.
        """
        required_field: int = field_readonly_if_not_provided(
            default=42
        )
        optional_field: Optional[str] = field_readonly_if_not_provided(
            default=None
        )
        regular_field: str = "test"

    obj = TestClass(required_field=10, optional_field="test")

    # Both should be writable
    obj.required_field = 20
    obj.optional_field = "changed"

    assert obj.required_field == 20
    assert obj.optional_field == "changed"

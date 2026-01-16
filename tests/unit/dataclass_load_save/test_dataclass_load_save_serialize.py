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
Unit tests for serialize functionality.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional

import pytest

from pyg90alarm.local.dataclass_load_save import (
    DataclassLoadSave,
    Metadata,
    field_readonly_if_not_provided,
)


@dataclass
class MultipleReadOnlyConfig(DataclassLoadSave):
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


def test_serialize_all_fields_by_default() -> None:
    """
    Test that serialize includes all fields by default.
    """

    @dataclass
    class TestClass(DataclassLoadSave):
        """
        Test dataclass with various metadata configurations.
        """
        normal_field: int = 10
        no_serialize_field: int = field(
            default=20, metadata={Metadata.NO_SERIALIZE: True}
        )
        skip_none_field: Optional[int] = field(
            default=None, metadata={Metadata.SKIP_NONE: True}
        )
        skip_none_with_value: Optional[int] = field(
            default=30, metadata={Metadata.SKIP_NONE: True}
        )
        both_metadata: Optional[int] = field(
            default=None,
            metadata={Metadata.NO_SERIALIZE: True, Metadata.SKIP_NONE: True},
        )

    obj = TestClass(
        normal_field=10,
        no_serialize_field=20,
        skip_none_field=None,
        skip_none_with_value=30,
        both_metadata=None,
    )

    result = obj.serialize()
    # Verify that only normal_field and skip_none_with_value are included
    assert result == [10, 30]


def test_serialize_skips_no_serialize_fields() -> None:
    """
    Test that fields with NO_SERIALIZE metadata are skipped.
    """

    @dataclass
    class TestClass(DataclassLoadSave):
        normal_field: int = 10
        no_serialize_field: int = field(
            default=20, metadata={Metadata.NO_SERIALIZE: True}
        )

    obj = TestClass()
    result = obj.serialize()
    assert result == [10]
    assert 20 not in result


@pytest.mark.parametrize(
    "value,should_skip",
    [
        pytest.param(None, True, id="None value with SKIP_NONE"),
        pytest.param(42, False, id="int value with SKIP_NONE"),
        pytest.param("", False, id="empty string with SKIP_NONE"),
        pytest.param(0, False, id="zero with SKIP_NONE"),
        pytest.param(False, False, id="False with SKIP_NONE"),
    ],
)
def test_serialize_skip_none_behavior(value: Any, should_skip: bool) -> None:
    """
    Test that SKIP_NONE metadata correctly skips only None values.
    """

    @dataclass
    class TestClass(DataclassLoadSave):
        normal_field: int = 100
        skip_none_field: Any = field(
            default=value, metadata={Metadata.SKIP_NONE: True}
        )

    obj = TestClass(skip_none_field=value)
    result = obj.serialize()

    if should_skip:
        assert result == [100]
    else:
        assert result == [100, value]


def test_serialize_field_order_preserved() -> None:
    """
    Test that serialize preserves field declaration order.
    """

    @dataclass
    class TestClass(DataclassLoadSave):
        field_a: int = 1
        field_b: int = 2
        field_c: int = 3

    obj = TestClass()
    result = obj.serialize()
    assert result == [1, 2, 3]


def test_serialize_with_mixed_metadata() -> None:
    """
    Test serialize with complex combinations of metadata.
    """

    @dataclass
    class TestClass(DataclassLoadSave):
        field_1: int = 1
        field_2: int = field(default=2, metadata={Metadata.NO_SERIALIZE: True})
        field_3: Optional[int] = field(
            default=None, metadata={Metadata.SKIP_NONE: True}
        )
        field_4: int = 4
        field_5: Optional[int] = field(
            default=5, metadata={Metadata.SKIP_NONE: True}
        )

    obj = TestClass()
    result = obj.serialize()
    # Verify that field_2 and field_3 are skipped
    assert result == [1, 4, 5]


def test_serialize_with_readonly_fields() -> None:
    """
    Test that serialize includes read-only fields.
    """

    @dataclass
    class TestClass(DataclassLoadSave):
        readonly_field: int = field_readonly_if_not_provided(default=42)
        normal_field: int = 100

    obj = TestClass(readonly_field=50)
    result = obj.serialize()
    assert result == [50, 100]


def test_serialize_readonly_with_none_default() -> None:
    """
    Test that read-only fields with None default skip properly.
    """
    obj = MultipleReadOnlyConfig()
    result = obj.serialize()
    # Verify that only fields not being None are included
    assert result == [42, "test"]


def test_serialize_readonly_with_provided_value() -> None:
    """
    Test serialize with provided read-only field.
    """
    obj = MultipleReadOnlyConfig(optional_field="provided")
    result = obj.serialize()
    assert result == [42, "provided", "test"]


def test_mixed_readonly_and_metadata_serialize() -> None:
    """
    Test serialize with both read-only fields and metadata.
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

    obj = TestClass(
        readonly_normal=101,
        readonly_skip_none=None,
        regular_no_serialize=201,
        regular_skip_none=None,
    )
    result = obj.serialize()

    # Verify that only the appropriate fields are included
    assert result == [101]


def test_dataclass_with_only_readonly_fields() -> None:
    """
    Test dataclass composed entirely of read-only fields.
    """

    @dataclass
    class TestClass(DataclassLoadSave):
        field1: int = field_readonly_if_not_provided(default=1)
        field2: str = field_readonly_if_not_provided(default="test")

    obj = TestClass(field1=10, field2="value")
    assert obj.serialize() == [10, "value"]

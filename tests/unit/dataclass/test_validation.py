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
Unit tests for dataclass validation module.
"""
from __future__ import annotations
from typing import Optional
import pytest
from dataclasses import dataclass
from pyg90alarm.dataclass.validation import (
    validated_int_field,
    validated_string_field,
    get_field_validation_constraints,
    ValidationConstraintsAbsent,
    IntValidationConstraints,
)


@pytest.mark.parametrize(
    "trust_initial_value,init_should_fail,set_should_fail,"
    "min_value,max_value,initial_value,new_value", [
        pytest.param(
            False, False, False, None, None, -1000, 1000000,
            id="No constraints"
        ),
        pytest.param(
            False, False, False, None, 10, 1, 10,
            id="Valid with max value only"
        ),
        pytest.param(
            False, False, True, None, 10, 1, 11,
            id="Invalid with max value only"
        ),
        pytest.param(
            False, False, False, 5, None, 5, 10,
            id="Valid with min value only"
        ),
        pytest.param(
            False, False, True, 5, None, 5, 4,
            id="Invalid with min value only"
        ),
        pytest.param(
            False, False, False, 1, 10, 5, 10,
            id="Valid"
        ),
        pytest.param(
            False, True, False, 1, 10, 11, 10,
            id="Invalid with init not trusted"
        ),
        pytest.param(
            True, False, False, 1, 10, 11, 10,
            id="Invalid with init trusted"
        ),
        pytest.param(
            False, False, False, 1, 10, 5, 1,
            id="Valid boundary min"
        ),
        pytest.param(
            False, False, False, 1, 10, 5, 10,
            id="Valid boundary max"
        ),
        pytest.param(
            False, False, True, 1, 10, 5, 0,
            id="Invalid below min"
        ),
        pytest.param(
            False, False, True, 1, 10, 5, 11,
            id="Invalid above max"
        ),
        pytest.param(
            False, False, False, 1, 10, 5, 7,
            id="Valid mid range"
        ),
    ]
)
def test_int_validator(
    trust_initial_value: bool, init_should_fail: bool,
    set_should_fail: bool,
    min_value: Optional[int], max_value: Optional[int],
    initial_value: int, new_value: int
) -> None:
    """
    Parametrized test for integer range validation.
    """
    @dataclass
    class Config:
        value: int = validated_int_field(
            min_value=min_value, max_value=max_value,
            trust_initial_value=trust_initial_value
        )

    # Invalid value during construction should raise ValueError
    if init_should_fail:
        with pytest.raises(ValueError):
            Config(value=initial_value)
    else:
        config = Config(value=initial_value)
        assert config.value == initial_value

    if init_should_fail:
        return

    # Setting new value should be validated
    if set_should_fail:
        with pytest.raises(ValueError):
            config.value = new_value
    else:
        config.value = new_value
        assert config.value == new_value


@pytest.mark.parametrize(
    "trust_initial_value,init_should_fail,set_should_fail,"
    "min_length,max_length,initial_value,new_value", [
        pytest.param(
            False, False, False, None, None, "x" * 1000, "x" * 1000,
            id="No constraints"
        ),
        pytest.param(
            False, False, False, None, 10, "hello", "a" * 10,
            id="Valid with max length only"
        ),
        pytest.param(
            False, False, True, None, 10, "hello", "a" * 11,
            id="Invalid with max length only"
        ),
        pytest.param(
            False, False, False, 5, None, "hello", "a" * 10,
            id="Valid with min length only"
        ),
        pytest.param(
            False, False, True, 5, None, "hello", "a" * 4,
            id="Invalid with min length only"
        ),
        pytest.param(
            False, False, False, 1, 10, "hello", "a", id="Valid"
        ),
        pytest.param(
            False, True, False, 1, 10, "01234567890", "0123456789",
            id="Invalid with init not trusted"
        ),
        pytest.param(
            True, False, False, 1, 10, "01234567890", "0123456789",
            id="Invalid with init trusted"
        ),
        pytest.param(
            False, False, False, 1, 10, "hello", "a",
            id="Valid boundary min"
        ),
        pytest.param(
            False, False, False, 1, 10, "hello", "0123456789",
            id="Valid boundary max"
        ),
        pytest.param(
            False, False, True, 1, 10, "hello", "",
            id="Invalid below min"
        ),
        pytest.param(
            False, False, True, 1, 10, "hello", "01234567890",
            id="Invalid above max"
        ),
        pytest.param(
            False, False, False, 1, 10, "hello", "abc",
            id="Valid mid range"
        ),
    ]
)
def test_str_validator(
    trust_initial_value: bool, init_should_fail: bool,
    set_should_fail: bool,
    min_length: Optional[int], max_length: Optional[int],
    initial_value: str, new_value: str
) -> None:
    """
    Parametrized test for string length validation.
    """
    @dataclass
    class Config:
        name: str = validated_string_field(
            min_length=min_length, max_length=max_length,
            trust_initial_value=trust_initial_value
        )

    # Invalid value during construction should raise ValueError
    if init_should_fail:
        with pytest.raises(ValueError):
            Config(name=initial_value)
    else:
        config = Config(name=initial_value)
        assert config.name == initial_value

    if init_should_fail:
        return

    # Setting new value should be validated
    if set_should_fail:
        with pytest.raises(ValueError):
            config.name = new_value
    else:
        config.name = new_value
        assert config.name == new_value


@pytest.mark.parametrize('min_value,max_value', [
    pytest.param(10, None, id="Min value only"),
    pytest.param(None, 100, id="Max value only"),
    pytest.param(0, 100, id="Min and max values"),
])
def test_metadata_stored_for_int(
    min_value: Optional[int], max_value: Optional[int]
) -> None:
    """
    Test that int value constraint is stored in field metadata.
    """
    @dataclass
    class Config:
        value: int = validated_int_field(
            min_value=min_value, max_value=max_value
        )

    constraints = get_field_validation_constraints(Config, 'value', int)
    assert constraints.max_value is max_value
    assert constraints.min_value is min_value


@pytest.mark.parametrize('min_length,max_length', [
    pytest.param(1, None, id="Min length only"),
    pytest.param(None, 50, id="Max length only"),
    pytest.param(1, 50, id="Min and max lengths"),
])
def test_metadata_stored_for_str(
    min_length: Optional[int], max_length: Optional[int]
) -> None:
    """
    Test that string value constraint is stored in field metadata.
    """
    @dataclass
    class Config:
        name: str = validated_string_field(
            min_length=min_length, max_length=max_length
        )

    constraints = get_field_validation_constraints(Config, 'name', str)
    assert constraints.max_length is max_length
    assert constraints.min_length is min_length


def test_metadata_for_nonexistent_field() -> None:
    """
    Test getting constraints for field that doesn't exist.
    """
    @dataclass
    class Config:
        value: int = validated_int_field(min_value=0, max_value=100)

    constraints = get_field_validation_constraints(Config, 'nonexistent', int)
    assert isinstance(constraints, ValidationConstraintsAbsent)


def test_metadata_for_non_dataclass() -> None:
    """
    Test getting constraints for non-dataclass type.
    """
    constraints = get_field_validation_constraints(
        str, 'value', str   # type: ignore
    )
    assert isinstance(constraints, ValidationConstraintsAbsent)


def test_metadata_for_field_without_validation() -> None:
    """
    Test getting constraints for regular field without validation.
    """
    @dataclass
    class Config:
        value: int = 0

    constraints = get_field_validation_constraints(Config, 'value', int)
    assert isinstance(constraints, IntValidationConstraints)


def test_multiple_int_fields() -> None:
    """
    Test dataclass with multiple validated integer fields.
    """
    @dataclass
    class Config:
        min_val: int = validated_int_field(min_value=0)
        max_val: int = validated_int_field(max_value=100)
        range_val: int = validated_int_field(min_value=10, max_value=90)

    config = Config(min_val=0, max_val=50, range_val=50)
    assert config.min_val == 0
    assert config.max_val == 50
    assert config.range_val == 50

    # Each field validates independently
    with pytest.raises(ValueError):
        config.min_val = -1

    with pytest.raises(ValueError):
        config.max_val = 101

    with pytest.raises(ValueError):
        config.range_val = 5


def test_multiple_string_fields() -> None:
    """
    Test dataclass with multiple validated string fields.
    """
    @dataclass
    class Config:
        short: str = validated_string_field(max_length=10)
        long: str = validated_string_field(min_length=5)
        range: str = validated_string_field(min_length=3, max_length=5)

    config = Config(short="abc", long="hello", range="test")
    assert config.short == "abc"
    assert config.long == "hello"
    assert config.range == "test"

    # Each field validates independently
    with pytest.raises(ValueError):
        config.short = "x" * 11

    with pytest.raises(ValueError):
        config.long = "ab"

    with pytest.raises(ValueError):
        config.range = "xy"


def test_mixed_validated_and_regular_fields() -> None:
    """
    Test dataclass with both validated and regular fields.
    """
    @dataclass
    class Config:
        validated_int: int = validated_int_field(
            min_value=0, max_value=100
        )
        regular_int: int = 42
        validated_str: str = validated_string_field(
            min_length=1, max_length=10
        )
        regular_str: str = "default"

    config = Config(
        validated_int=50,
        regular_int=100,
        validated_str="hello",
        regular_str="custom"
    )

    assert config.validated_int == 50
    assert config.regular_int == 100
    assert config.validated_str == "hello"
    assert config.regular_str == "custom"

    # Regular fields can be set to any value
    config.regular_int = -1000000
    config.regular_str = "x" * 10000

    # Validated fields still enforce constraints
    with pytest.raises(ValueError):
        config.validated_int = 101

    with pytest.raises(ValueError):
        config.validated_str = ""


def test_int_field_with_default_value() -> None:
    """
    Test integer field with default value.
    """
    @dataclass
    class Config:
        value: int = validated_int_field(
            min_value=0, max_value=100, default=50
        )

    # Use default
    config1 = Config()
    assert config1.value == 50

    # Override default
    config2 = Config(value=75)
    assert config2.value == 75


def test_string_field_with_default_value() -> None:
    """
    Test string field with default value.
    """
    @dataclass
    class Config:
        name: str = validated_string_field(
            min_length=1, max_length=50, default="default"
        )

    # Use default
    config1 = Config()
    assert config1.name == "default"

    # Override default
    config2 = Config(name="custom")
    assert config2.name == "custom"


def test_default_value_is_validated() -> None:
    """
    Test that default value respects validation constraints.
    """
    @dataclass
    class Config:
        invalid: int = validated_int_field(
            min_value=0, max_value=100, default=101
        )

    with pytest.raises(ValueError):
        Config()

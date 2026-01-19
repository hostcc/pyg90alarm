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
Validation descriptors for dataclass fields.

This module provides descriptor-based validation for dataclass fields,
supporting integer range validation and string length validation.

Example usage:

    from dataclasses import dataclass
    from pyg90alarm.validation import (
        validated_int_field,
        validated_string_field,
    )

    @dataclass
    class Config:
        # Integer field with range validation
        count: int = validated_int_field(min=0, max=100)

        # String field with length validation
        name: str = validated_string_field(min=1, max=50)
"""
from __future__ import annotations
from typing import (
    Optional, Any, cast, TYPE_CHECKING, overload, TypeVar, Generic
)
import logging
from dataclasses import dataclass, field, fields, is_dataclass

from ..const import BUG_REPORT_URL
if TYPE_CHECKING:
    from _typeshed import DataclassInstance

_LOGGER = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class ValidationConstraintsAbsent:
    """
    Base class for validation constraints containers.
    """


@dataclass
class IntValidationConstraints:
    """
    Container for integer validation constraints.
    """
    min_value: Optional[int] = None
    max_value: Optional[int] = None


@dataclass
class StrValidationConstraints:
    """
    Container for string validation constraints.
    """
    min_length: Optional[int] = None
    max_length: Optional[int] = None


METADATA_KEY = 'validation_constraints'
T = TypeVar('T')


class ValidatorBase(Generic[T]):
    """
    Base dataclass descriptor for validating field values.

    :param default: Default value to return upon read if not provided during
     initialization.
    :param trust_initial_value: If True, skips validation during dataclass
     initialization assuming init value is valid.
    """
    def __init__(
        self,
        default: Optional[T] = None,
        trust_initial_value: bool = False
    ) -> None:
        self._name: Optional[str] = None
        self._default = default
        self._trust_initial_value = trust_initial_value

    def __validate__(self, obj: Any, value: T) -> bool:
        """
        Validates the value before setting.

        This method should be overridden by subclasses to implement specific
        validation logic.

        :param obj: The dataclass instance.
        :param value: The value to validate.
        :raises ValueError: Optional exception to raise if the value is
         invalid.
        :return: True if the value is valid, False otherwise. Only returned if
         no exception is raised, which will have invalid value being silently
         ignored.
        """
        raise NotImplementedError(
            'Subclasses must implement __validate__() method'
        )

    def __set_name__(self, owner: type, name: str) -> None:
        """
        Stores the name of the attribute this descriptor is assigned to.

        Note that the name is prepended with an underscore to avoid recursion
        between __get__() and __set__(), since those aren't called for such an
        attribute

        :param owner: The owner class.
        :param name: The name of the attribute.
        """
        self._name = "_" + name

    @property
    def __unmangled_name__(self) -> str:
        """
        Returns the unmangled field name.

        :return: Unmangled field name.
        """
        return self.__field_name__[1:]

    @property
    def __field_name__(self) -> str:
        """
        Returns the field name the descriptor is assigned to.

        Note that the name is mangled, see :py:meth:`__set_name__`.

        :return: Field name.
        """
        assert self._name is not None, 'Descriptor not initialized properly'
        return self._name

    def __get__(
        self, obj: Any, objtype: Optional[type] = None
    ) -> Optional[T]:
        """
        Retrieves the field value, returning default if not set.

        :param obj: The dataclass instance.
        :param objtype: The dataclass type.
        :return: The field value or default if not set.
        """
        # Dataclass requests the default value for the field
        if obj is None:
            return self._default

        # Return stored value if it exists, otherwise return default if the
        # value is the descriptor itself, i.e. not set
        value = getattr(obj, self.__field_name__, self._default)
        if value is self:
            _LOGGER.debug(
                "%s: Getting default value '%s'",
                self.__unmangled_name__, self._default
            )
            value = self._default
        return value

    def __set__(self, obj: Any, value: T) -> None:
        """
        Sets the field value after validating it.

        :param obj: The dataclass instance.
        :param value: The value to set.
        """
        # Default value assignment, e.g. when field not provided during
        # initialization thus being assigned the descriptor instance itself
        if isinstance(value, ValidatorBase) and self._default is not None:
            _LOGGER.debug(
                "%s: Assigning default value '%s'",
                self.__unmangled_name__, self._default
            )
            value = self._default

        # First time setting the value during dataclass initialization and it's
        # value should be trusted if `trust_initial_value` is True
        trusted_init_value = (
            not hasattr(obj, self.__field_name__)
            and self._trust_initial_value
        )

        # Validate the value before setting
        _LOGGER.debug(
            "%s: Validating value '%s'", self.__unmangled_name__, value
        )

        try:
            if (
                not self.__validate__(obj, value)
                and not trusted_init_value
            ):
                _LOGGER.debug(
                    "%s: Validation failed for value '%s'",
                    self.__unmangled_name__, value
                )
                # For unification, raise ValueError if validation fails if the
                # validation method just returned False
                raise ValueError(
                    f"Invalid value '{value}' for field"
                    f' {self.__unmangled_name__}'
                )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Validation failed for the value not being trusted during initial
            # assignment, re-raise the exception
            if not trusted_init_value:
                raise exc

            # Log a warning about the validation failure during trusted init,
            # so that constraints can be revised
            _LOGGER.warning(
                "%s: Validation failed during initialization for trusted value"
                " '%s' (%s). Please create bug report at %s if you see this"
                " warning.",
                self.__unmangled_name__, value, exc, BUG_REPORT_URL
            )

        # Set the validated value
        _LOGGER.debug(
            "%s: Setting value to '%s'", self.__unmangled_name__, value
        )
        setattr(obj, self.__field_name__, value)


class IntRangeValidator(ValidatorBase[int]):
    """
    Descriptor for validating integer field values against min/max constraints.

    The field value is validated when set. A ValueError is raised if the value
    is outside the specified range.

    Example usage:

        @dataclass
        class Example:
            value: int = validated_int_field(min=0, max=100)

        ex = Example(value=50)  # OK
        ex.value = 100  # OK
        ex.value = 101  # Raises ValueError

    :param min_value: Minimum allowed value (inclusive), or None for no
     minimum.
    :param max_value: Maximum allowed value (inclusive), or None for no
     maximum.:
    :param *: Rest of the params are passed to base class.
    """
    def __init__(
        self, *,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(**kwargs)
        self._min_value = min_value
        self._max_value = max_value

    def __validate__(self, obj: Any, value: int) -> bool:
        # Validate the value before setting
        if self._min_value is not None and value < self._min_value:
            msg = (
                f'{self.__unmangled_name__}: Value {value} is below minimum'
                f' allowed value {self._min_value}'
            )
            _LOGGER.debug(msg)
            raise ValueError(msg)

        if self._max_value is not None and value > self._max_value:
            msg = (
                f'{self.__unmangled_name__}: Value {value} is above maximum'
                f' allowed value {self._max_value}'
            )
            _LOGGER.debug(msg)
            raise ValueError(msg)

        return True


class StringLengthValidator(ValidatorBase[str]):
    """
    Descriptor for validating string field values against length constraints.

    The field value is validated when set. A ValueError is raised if the string
    length is outside the specified range.

    Example usage:

        @dataclass
        class Example:
            name: str = validated_string_field(min=1, max=50)

        ex = Example(name="hello")  # OK
        ex.name = "a"  # OK
        ex.name = ""  # Raises ValueError

    :param min_length: Minimum string length (inclusive), or None for no
     minimum.
    :param max_length: Maximum string length (inclusive), or None for no
     maximum.
    :param *: Rest of the params are passed to base class.
    """
    def __init__(
        self,
        *,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(**kwargs)
        self._min_length = min_length
        self._max_length = max_length

    def __validate__(self, obj: Any, value: str) -> bool:
        length = len(value)

        # Validate the length before setting
        if self._min_length is not None and length < self._min_length:
            msg = (
                f'{self.__unmangled_name__}: String length {length} is below'
                f' minimum allowed length {self._min_length}'
            )
            _LOGGER.debug(msg)
            raise ValueError(msg)

        if self._max_length is not None and length > self._max_length:
            msg = (
                f'{self.__unmangled_name__}: String length {length} is above'
                f' maximum allowed length {self._max_length}'
            )
            _LOGGER.debug(msg)
            raise ValueError(msg)

        return True


def validated_int_field(
    *,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
    default: Optional[int] = None,
    trust_initial_value: bool = False,
    **kwargs: Any
) -> int:
    """
    Create a dataclass field with integer range validation.

    The field value will be validated when set, raising ValueError if outside
    the specified range. Validation constraints are stored in field metadata
    for later retrieval.

    :param min_value: Minimum allowed value (inclusive), or None for no
     minimum.
    :param max_value: Maximum allowed value (inclusive), or None for no
     maximum.
    :param default: Default value for the field, or None for no default.
    :param trust_initial_value: If True, skips validation during dataclass
     initialization assuming init value is valid.
    :param kwargs: Additional keyword arguments to pass to dataclasses.field().
    :return: A dataclass field with IntRangeValidator descriptor and metadata.

    Example:

        @dataclass
        class Config:
            count: int = validated_int_field(
                min_value=0, max_value=100, default=50
            )
    """
    # Store validation constraints in metadata
    if 'metadata' not in kwargs:
        kwargs['metadata'] = {}

    metadata = IntValidationConstraints(min_value, max_value)
    kwargs['metadata'][METADATA_KEY] = metadata

    # Create the field with the descriptor as default, passing along default
    # value
    # pylint: disable=invalid-field-call
    return cast(int, field(
        **kwargs,
        default=IntRangeValidator(
            min_value=min_value, max_value=max_value, default=default,
            trust_initial_value=trust_initial_value
        )
    ))


def validated_string_field(
    *,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    default: Optional[str] = None,
    trust_initial_value: bool = False,
    **kwargs: Any
) -> str:
    """
    Create a dataclass field with string length validation.

    The field value will be validated when set, raising ValueError if the
    string length is outside the specified range. Validation constraints are
    stored in field metadata for later retrieval.

    :param min_length: Minimum string length (inclusive), or None for no
     minimum.
    :param max_length: Maximum string length (inclusive), or None for no
     maximum.
    :param default: Default value for the field, or None for no default.
    :param trust_initial_value: If True, skips validation during dataclass
     initialization assuming init value is valid.
    :param kwargs: Additional keyword arguments to pass to dataclasses.field().
    :return: A dataclass field with StringLengthValidator descriptor and
     metadata.

    Example:

        @dataclass
        class Config:
            name: str = validated_string_field(
                min_length=1, max_length=50, default="default"
            )
    """
    # Store validation constraints in metadata
    if 'metadata' not in kwargs:
        kwargs['metadata'] = {}

    metadata = StrValidationConstraints(min_length, max_length)
    kwargs['metadata'][METADATA_KEY] = metadata

    # Create the field with the descriptor as default, passing along default
    # value
    # pylint: disable=invalid-field-call
    return cast(str, field(
        **kwargs,
        default=StringLengthValidator(
            min_length=min_length, max_length=max_length, default=default,
            trust_initial_value=trust_initial_value
        )
    ))


# `get_field_validation_constraints` overload for `int` type
@overload
def get_field_validation_constraints(
    dataclass_type: DataclassInstance | type[DataclassInstance],
    field_name: str, expected_type: type[int]
) -> IntValidationConstraints:
    ...


# `get_field_validation_constraints` overload for `str` type
@overload
def get_field_validation_constraints(
    dataclass_type: DataclassInstance | type[DataclassInstance],
    field_name: str, expected_type: type[str]
) -> StrValidationConstraints:
    ...


# `get_field_validation_constraints` overload when no expected type is given
@overload
def get_field_validation_constraints(
    dataclass_type: DataclassInstance | type[DataclassInstance],
    field_name: str, expected_type: None = None
) -> ValidationConstraintsAbsent:
    ...


def get_field_validation_constraints(
    dataclass_type: DataclassInstance | type[DataclassInstance],
    field_name: str, expected_type: Optional[type] = None
) -> Any:
    """
    Retrieve validation constraints for a specific dataclass field.

    :param dataclass_type: The dataclass type or instance to inspect.
    :param field_name: The name of the field to get constraints for.
    :param expected_type: Expected type of the field to
     determine which constraints to retrieve.
    :return: Validation constraints container, or ValidationConstraintsAbsent
     if none found. The latter is to avoid returning None and free callers from
     having to check for it.

    Example:

        constraints = get_field_validation_constraints(Config, 'count', int)
        # Returns: object with `constraints.min_value`, `constraints.max_value`
    """
    if not is_dataclass(dataclass_type):
        # Not a dataclass, return absent indicator
        return ValidationConstraintsAbsent()

    fields_list = fields(dataclass_type)
    for f in fields_list:
        # Find the field by name and check if validation metadata exists
        if (
            f.name == field_name
            and METADATA_KEY in getattr(f, 'metadata', {})
        ):
            for typ, klass in (
                # Constraints for `int` field
                (int, IntValidationConstraints),
                # Constraints for `str` field
                (str, StrValidationConstraints),
            ):
                if expected_type is typ:
                    # Return stored constraints if available
                    if isinstance(
                        f.metadata[METADATA_KEY], klass
                    ):
                        return f.metadata[METADATA_KEY]
                    # Otherwise return empty constraints
                    return klass()

    # No validation constraints found, return absent indicator
    return ValidationConstraintsAbsent()

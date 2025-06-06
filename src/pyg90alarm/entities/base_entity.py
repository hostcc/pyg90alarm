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
Base entity.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
# `Self` has been introduced in Python 3.11, need to use `typing_extensions`
# for earlier versions
try:
    from typing import Self  # type: ignore[attr-defined,unused-ignore]
except ImportError:
    from typing_extensions import Self


class G90BaseEntity(ABC):
    """
    Base entity class.

    Contains minimal set of method for :class:`.G90BaseList` class
    """
    @abstractmethod
    def update(
        self,
        obj: Self  # pylint: disable=used-before-assignment
    ) -> None:
        """
        Update the entity from another one.

        :param obj: Object to update from.
        """

    @property
    @abstractmethod
    def is_unavailable(self) -> bool:
        """
        Check if the entity is unavailable.

        :return: True if the entity is unavailable.
        """

    @is_unavailable.setter
    @abstractmethod
    def is_unavailable(self, value: bool) -> None:
        """
        Set the entity as unavailable.

        :param value: Value to set.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Get the name of the entity.

        :return: Name of the entity.
        """

    @property
    @abstractmethod
    def index(self) -> int:
        """
        Get the index of the entity.

        :return: Index of the entity.
        """

    @property
    @abstractmethod
    def subindex(self) -> int:
        """
        Get the subindex of the entity.

        :return: Subindex of the entity.
        """

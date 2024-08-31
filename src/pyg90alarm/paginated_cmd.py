# Copyright (c) 2021 Ilia Sotnikov
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
Implements paginated command for G90 alarm panel protocol.
"""
from __future__ import annotations
import logging
from typing import Any, cast
from dataclasses import dataclass
from .base_cmd import G90BaseCommand, G90BaseCommandData
from .exceptions import G90Error
from .const import G90Commands

_LOGGER = logging.getLogger(__name__)


@dataclass
class G90PaginationFields:
    """
    Represents structure of the pagination fields used by alarm panel.

    :meta private:
    """
    total: int
    start: int
    nelems: int


class G90PaginatedCommand(G90BaseCommand):
    """
    Implements paginated command for alarm panel protocol.
    """
    def __init__(
        self, host: str, port: int, code: G90Commands, start: int, end: int,
        **kwargs: Any
    ) -> None:
        # pylint: disable=too-many-arguments
        self._start = start
        self._end = end
        self._expected_nelems = end - start + 1
        self._nelems = 0
        self._total = 0
        super().__init__(host, port, code, [self._start, self._end],
                         **kwargs)

    @property
    def total(self) -> int:
        """
        Total number of records available.
        """
        return self._total

    @property
    def start(self) -> int:
        """
        Index of the first record in the response.
        """
        return self._start

    @property
    def count(self) -> int:
        """
        Number of records in the response.
        """
        return self._nelems

    def _parse(self, data: str) -> None:
        """
        Parses the response from the alarm panel.
        """
        super()._parse(data)
        resp_data: G90BaseCommandData = self._resp.data or []
        try:
            page_data = resp_data.pop(0)
            page_info = G90PaginationFields(*page_data)
        except TypeError as exc:
            raise G90Error(f'Wrong pagination data {page_data} - {str(exc)}'
                           ) from exc
        except IndexError as exc:
            raise G90Error(f"Missing pagination in response '{self._resp}'"
                           ) from exc

        self._total = page_info.total
        self._start = page_info.start
        self._nelems = page_info.nelems

        errors = []
        if self._nelems != len(resp_data):
            qualifier = (
                "Truncated" if self._nelems > len(resp_data) else "Extra"
            )
            errors.append(
                f'{qualifier} data provided in paginated response -'
                f' expected {self._nelems} entities as per response,'
                f' received {len(resp_data)}')

        if self._expected_nelems < len(resp_data):
            errors.append(
                f'Extra data provided in paginated response -'
                f' expected {self._expected_nelems} entities as per request,'
                f' received {len(resp_data)}')

        if errors:
            raise G90Error('. '.join(errors))

        _LOGGER.debug('Paginated command response: '
                      'total records %s, start record %s, record count %s',
                      page_info.total, page_info.start, page_info.nelems)

    async def process(self) -> G90PaginatedCommand:
        """
        Initiates the command processing.
        """
        return cast(G90PaginatedCommand, await super().process())

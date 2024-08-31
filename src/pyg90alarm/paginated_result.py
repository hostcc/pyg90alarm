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
Extends paginated command for G90 alarm panel providing convenience interface
to work with results of paginated commands.
"""

import logging
from typing import Any, Optional, AsyncGenerator, Iterable, cast
from dataclasses import dataclass
from .paginated_cmd import G90PaginatedCommand
from .const import (
    G90Commands,
    CMD_PAGE_SIZE,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class G90PaginatedResponse:
    """
    Response yielded from the :meth:`.G90PaginatedResult.process` method
    """
    proto_idx: int
    data: str


class G90PaginatedResult:
    """
    Processes paginated response from G90 corresponding panel commands.
    """
    # pylint: disable=too-few-public-methods
    def __init__(
        self, host: str, port: int, code: G90Commands, start: int = 1,
        end: Optional[int] = None, **kwargs: Any
    ):
        # pylint: disable=too-many-arguments
        self._host = host
        self._port = port
        self._code = code
        self._start = start
        self._end = end
        self._kwargs = kwargs

    async def process(self) -> AsyncGenerator[G90PaginatedResponse, None]:
        """
        Process paginated response yielding :class:`.G90PaginatedResponse`
        instance for each element.
        """
        page = CMD_PAGE_SIZE
        start = self._start
        count = 0
        while True:
            # The start record number is one-based, so subtract one when
            # calculating the number of the end record for the current
            # iteration
            end = start + page - 1
            # Use the smallest of requested end record number and calculated
            # one (based of page size), allows for number of records less than
            # in page
            if self._end:
                end = min(end, self._end)

            _LOGGER.debug('Invoking paginated command for %s..%s range',
                          start, end)
            cmd = await G90PaginatedCommand(
                host=self._host, port=self._port, code=self._code,
                start=start, end=end,
                **self._kwargs
            ).process()

            # The caller didn't supply the end record number, use the records
            # total since it is now known
            if not self._end:
                self._end = cmd.total
            # The supplied end record number is higher than total records
            # available, reset to the latter
            if self._end > cmd.total:
                _LOGGER.warning('Requested record range (%i) exceeds number of'
                                ' available records (%i), setting to the'
                                ' latter', self._end, cmd.total)
                self._end = cmd.total

            _LOGGER.debug('Retrieved %i records in the iteration,'
                          ' %i available in total, target end'
                          ' record number is %i',
                          cmd.count, cmd.total, self._end)

            # Produce the resulting records for the consumer
            for idx, data in enumerate(cast(Iterable[str], cmd.result)):
                # Protocol uses one-based indexes, `start` implies that so no
                # further additions to resulting value is needed.
                # Note the index provided here is running one across multiple
                # pages hence use of `start` variable
                yield G90PaginatedResponse(start + idx, data)

            # Count the number of processed records
            count += cmd.count

            # End the loop if we processed same number of sensors as in the
            # pagination header (or attempted to process more than that by
            # an error), or no records have been received
            if not cmd.count:
                break
            if cmd.start + cmd.count - 1 >= self._end:
                break
            # Move to the next page for another iteration
            start = start + page

        _LOGGER.debug('Total number of paginated entries:'
                      ' processed %s, expected %s',
                      count,
                      # Again, both end and start record numbers are one-based,
                      # so need to add one to calculate how many records have
                      # been requested
                      self._end - self._start + 1)

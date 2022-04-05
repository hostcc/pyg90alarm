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

import logging
from collections import namedtuple
from .base_cmd import G90BaseCommand
from .exceptions import G90Error

_LOGGER = logging.getLogger(__name__)


class G90PaginationFields(namedtuple('G90PaginationFields',
                                     ['total', 'start', 'count'])):
    """
    tbd

    :meta private:
    """


class G90PaginatedCommand(G90BaseCommand):
    """
    tbd
    """
    def __init__(self, host, port, code, start, end, **kwargs):
        """
        tbd
        """
        # pylint: disable=too-many-arguments
        self._start = start
        self._end = end
        self._expected_count = end - start + 1
        self._count = 0
        self._total = 0
        super().__init__(host, port, code, [self._start, self._end],
                         **kwargs)

    @property
    def total(self):
        """
        tbd
        """
        return self._total

    @property
    def start(self):
        """
        tbd
        """
        return self._start

    @property
    def count(self):
        """
        tbd
        """
        return self._count

    def _parse(self, data):
        """
        tbd
        """
        super()._parse(data)
        data = self._resp.data or []
        try:
            page_data = data.pop(0)
            page_info = G90PaginationFields(*page_data)
        except TypeError as exc:
            raise G90Error(f'Wrong pagination data {page_data} - {str(exc)}'
                           ) from exc
        except IndexError as exc:
            raise G90Error(f"Missing pagination in response '{self._resp}'"
                           ) from exc

        self._total = page_info.total
        self._start = page_info.start
        self._count = page_info.count

        errors = []
        if self._count != len(data):
            qualifier = "Truncated" if self._count > len(data) else "Extra"
            errors.append(
                f'{qualifier} data provided in paginated response -'
                f' expected {self._count} entities as per response,'
                f' received {len(data)}')

        if self._expected_count < len(data):
            errors.append(
                f'Extra data provided in paginated response -'
                f' expected {self._expected_count} entities as per request,'
                f' received {len(data)}')

        if errors:
            raise G90Error('. '.join(errors))

        _LOGGER.debug('Paginated command response: '
                      'total records %s, start record %s, record count %s',
                      page_info.total, page_info.start, page_info.count)

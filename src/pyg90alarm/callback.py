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
tbd
"""

import asyncio
import functools
import logging

_LOGGER = logging.getLogger(__name__)


class G90Callback:
    """
    tbd
    """
    @staticmethod
    def invoke(callback, *args, **kwargs):
        """
        tbd
        """
        if not callback:
            return None

        _LOGGER.debug('Attempting to invoke callback %s'
                      ' (args: %s, kwargs: %s)',
                      callback, args, kwargs)
        try:
            if asyncio.iscoroutinefunction(callback):
                if hasattr(asyncio, 'create_task'):
                    return asyncio.create_task(callback(*args, **kwargs))
                # Python 3.6 has only `ensure_future` method
                return asyncio.ensure_future(callback(*args, **kwargs))
            return callback(*args, **kwargs)
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error('Got exception when invoking'
                          ' callback: %s', exc)
            return None

    @staticmethod
    def invoke_delayed(delay, callback, *args, **kwargs):
        """
        tbd
        """
        if hasattr(asyncio, 'get_running_loop'):
            loop = asyncio.get_running_loop()
        else:
            # Python 3.6 has no `get_running_loop`, only `get_event_loop`
            loop = asyncio.get_event_loop()
        loop.call_later(delay, functools.partial(callback, *args, **kwargs))

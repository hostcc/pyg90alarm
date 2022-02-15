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
from functools import (partial, wraps)
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
            return

        _LOGGER.debug('Attempting to invoke callback %s'
                      ' (args: %s, kwargs: %s)',
                      callback, args, kwargs)

        if not asyncio.iscoroutinefunction(callback):
            def async_wrapper(func):
                """
                Wraps the regular callback function into coroutine, so it could
                later be created as async task.
                """
                @wraps(func)
                async def wrapper(*args, **kwds):
                    return func(*args, **kwds)
                return wrapper

            callback = async_wrapper(callback)

        if hasattr(asyncio, 'create_task'):
            task = asyncio.create_task(callback(*args, **kwargs))
        else:
            # Python 3.6 has only `ensure_future` method
            task = asyncio.ensure_future(callback(*args, **kwargs))

        def reap_callback_exception(task):
            """
            Reaps an exception (if any) from the task logging it, to prevent
            `asyncio` reporting that task exception was never retrieved.
            """
            exc = task.exception()
            if exc:
                _LOGGER.error('Got exception when invoking'
                              " callback '%s(...)': %s",
                              task.get_coro().__qualname__, exc)

        task.add_done_callback(reap_callback_exception)

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
        loop.call_later(delay, partial(callback, *args, **kwargs))

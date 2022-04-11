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
Implements callbacks.
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
                              " callback '%s(...)':",
                              task.get_coro().__qualname__,
                              exc_info=exc, stack_info=False)

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


def async_as_sync(func):
    """
    Invokes an async function as regular one via :py:func:`G90Callback.invoke`.
    One of possible use cases is implementing property setter for async code,
    where the function could be used an decorator:

    .. code-block:: python

     @property
     async def a_property(...):
         ...

     @a_property.setter
     @async_as_sync
     async def a_property(...):
         ...

    Since the function internally submits the wrapped async code as
    :py:mod:`asyncio` task, it execution isn't guaranteed as the program could
    be terminated earlier that it is processed in the loop.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        return G90Callback.invoke(func, *args, **kwargs)
    return wrapper

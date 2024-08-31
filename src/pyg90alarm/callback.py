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
from __future__ import annotations
import asyncio
from functools import (partial, wraps)
from asyncio import Task
from typing import Any, Callable, Coroutine, cast, Optional, Union
import logging

_LOGGER = logging.getLogger(__name__)

Callback = Optional[
    Union[
        Callable[..., None],
        Callable[..., Coroutine[None, None, None]],
    ]
]


class G90Callback:
    """
    Implements callbacks.
    """
    @staticmethod
    def invoke(
        callback: Callback, *args: Any, **kwargs: Any
    ) -> None:
        """
        Invokes the callback.
        """
        if not callback:
            return

        _LOGGER.debug('Attempting to invoke callback %s'
                      ' (args: %s, kwargs: %s)',
                      callback, args, kwargs)

        if not asyncio.iscoroutinefunction(callback):
            def async_wrapper(
                func: Callable[..., None]
            ) -> Callable[..., Coroutine[Any, Any, None]]:
                """
                Wraps the regular callback function into coroutine, so it could
                later be created as async task.
                """
                @wraps(func)
                async def wrapper(
                    *args: Any, **kwds: Any
                ) -> None:
                    return func(*args, **kwds)

                return cast(Callable[..., Coroutine[Any, Any, None]], wrapper)

            task = asyncio.create_task(
                async_wrapper(
                    cast(Callable[..., None], callback)
                )(*args, **kwargs)
            )
        else:
            task = asyncio.create_task(callback(*args, **kwargs))

        def reap_callback_exception(task: Task[Any]) -> None:
            """
            Reaps an exception (if any) from the task logging it, to prevent
            `asyncio` reporting that task exception was never retrieved.
            """
            exc = task.exception()
            if exc:
                _LOGGER.error(
                    "Got exception when invoking callback '%s(...)':",
                    cast(
                        Coroutine[Any, Any, None], task.get_coro()
                    ).__qualname__,
                    exc_info=exc, stack_info=False
                )

        task.add_done_callback(reap_callback_exception)

    @staticmethod
    def invoke_delayed(
        delay: float, callback: Callable[..., None], *args: Any, **kwargs: Any
    ) -> None:
        """
        Invokes the callback after a delay.
        """
        loop = asyncio.get_running_loop()
        loop.call_later(delay, partial(callback, *args, **kwargs))

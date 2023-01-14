import asyncio
import sys
from pyg90alarm.callback import (   # noqa:E402
    async_as_sync,
)
sys.path.extend(['src', '../src'])


async def test_async_as_sync_decorator():
    """ Tests for `async_as_sync` decorator """
    class TestProperty:
        _prop = None

        @property
        async def test_property(self):
            return self._prop

        @test_property.setter
        @async_as_sync
        async def test_property(self, value):
            self._prop = value

    test_instance = TestProperty()
    test_instance.test_property = 'test value'
    # Allow the async task the decorator submits to finish
    await asyncio.sleep(0)
    assert await test_instance.test_property == 'test value'

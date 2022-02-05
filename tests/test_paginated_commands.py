import sys
from .fixtures import G90Fixture
sys.path.extend(['src', '../src'])

from pyg90alarm.paginated_cmd import (   # noqa:E402
    G90PaginatedCommand,
)
from pyg90alarm.exceptions import G90Error  # noqa:E402


class TestG90PaginatedCommand(G90Fixture):

    async def test_missing_pagination(self):
        g90 = G90PaginatedCommand(
            host='mocked', port=12345, code=102, start=1, end=1,
            sock=self.socket_mock)
        self.socket_mock.recvfrom.return_value = (
            b'ISTART[102,[[]]]IEND\0', ('mocked', 12345))

        with self.assertRaises(G90Error, ) as cm:
            await g90.process()
        self.assertIn(cm.exception.args[0],
                      ['Wrong pagination data [] -'
                       ' <lambda>() missing 3 required positional arguments:'
                       " 'total', 'start', and 'count'",
                       'Wrong pagination data [] -'
                       ' __new__() missing 3 required positional arguments:'
                       " 'total', 'start', and 'count'"])

        self.assert_callargs_on_sent_data([
            b'ISTART[102,102,[102,[1,1]]]IEND\0'
        ])

    async def test_no_paginated_data(self):
        g90 = G90PaginatedCommand(
            host='mocked', port=12345, code=102, start=1, end=1,
            sock=self.socket_mock)
        self.socket_mock.recvfrom.return_value = (
            b'ISTART[102,[[1,1,1]]]IEND\0', ('mocked', 12345))

        with self.assertRaises(G90Error) as cm:
            await g90.process()
        self.assertIn('Truncated data provided in paginated response -'
                      ' expected 1 entities as per response, received 0',
                      cm.exception.args)
        self.assert_callargs_on_sent_data([
            b'ISTART[102,102,[102,[1,1]]]IEND\0'
        ])

    async def test_partial_paginated_data(self):
        g90 = G90PaginatedCommand(
            host='mocked', port=12345, code=102, start=1, end=2,
            sock=self.socket_mock)
        self.socket_mock.recvfrom.return_value = (
            b'ISTART[102,[[1,1,1],[""]]]IEND\0', ('mocked', 12345))

        await g90.process()
        self.assert_callargs_on_sent_data([
            b'ISTART[102,102,[102,[1,2]]]IEND\0'
        ])

    async def test_extra_paginated_data(self):
        g90 = G90PaginatedCommand(
            host='mocked', port=12345, code=102, start=1, end=1,
            sock=self.socket_mock)
        self.socket_mock.recvfrom.return_value = (
            b'ISTART[102,[[2,1,2],[""],[""]]]IEND\0', ('mocked', 12345))

        with self.assertRaises(G90Error) as cm:
            await g90.process()
        self.assertIn('Extra data provided in paginated response -'
                      ' expected 1 entities as per request, received 2',
                      cm.exception.args)
        self.assert_callargs_on_sent_data([
            b'ISTART[102,102,[102,[1,1]]]IEND\0'
        ])

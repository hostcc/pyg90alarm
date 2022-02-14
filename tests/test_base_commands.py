import sys
from .fixtures import G90Fixture
sys.path.extend(['src', '../src'])

from pyg90alarm.base_cmd import (  # noqa:E402
    G90BaseCommand
)
from pyg90alarm.exceptions import (G90Error, G90TimeoutError)  # noqa:E402


class TestG90BaseCommand(G90Fixture):
    async def test_network_unreachable(self):
        g90 = G90BaseCommand(
            host='mocked', port=12345, code=206, sock=self.socket_mock)
        self.socket_mock.recvfrom.side_effect = OSError('Host unreachable')

        with self.assertRaises(OSError) as cm:
            await g90.process()
        self.assertIn("Host unreachable", cm.exception.args)

    async def test_wrong_host(self):
        g90 = G90BaseCommand(
            host='mocked', port=12345, code=206, sock=self.socket_mock)
        self.socket_mock.recvfrom.return_value = (
            b'ISTARTIEND\0', ('another_host', 12345))

        with self.assertRaises(G90Error) as cm:
            await g90.process()
        self.assertIn('Received response from wrong host another_host,'
                      ' expected from mocked', cm.exception.args)

    async def test_wrong_port(self):
        g90 = G90BaseCommand(
            host='mocked', port=12345, code=206, sock=self.socket_mock)
        self.socket_mock.recvfrom.return_value = (
            b'ISTARTIEND\0', ('mocked', 54321))

        with self.assertRaises(G90Error) as cm:
            await g90.process()
        self.assertIn('Received response from wrong port 54321,'
                      ' expected from 12345', cm.exception.args)

    async def test_timeout(self):
        g90 = G90BaseCommand(
            host='mocked', port=12345, code=206,
            timeout=0.1, retries=2, sock=self.socket_mock)
        self.socket_mock.recvfrom.return_value = (b'', ('mocked', 12345))

        with self.assertRaises(G90TimeoutError):
            await g90.process()
        self.assert_callargs_on_sent_data([
            b'ISTART[206,206,""]IEND\0',
            b'ISTART[206,206,""]IEND\0',
        ])

    async def test_wrong_format(self):
        g90 = G90BaseCommand(
            host='mocked', port=12345, code=206, sock=self.socket_mock)
        self.socket_mock.recvfrom.return_value = (
            b'ISTART[IEND\0', ('mocked', 12345))

        with self.assertRaises(G90Error) as cm:
            await g90.process()
        self.assertIn("Unable to parse response as JSON: '['",
                      cm.exception.args)
        self.assert_callargs_on_sent_data([b'ISTART[206,206,""]IEND\0'])

    async def test_no_response(self):
        g90 = G90BaseCommand(
            host='mocked', port=12345, code=206, sock=self.socket_mock)
        self.socket_mock.recvfrom.return_value = (b'', ('mocked', 12345))

        with self.assertRaises(G90Error) as cm:
            await g90.process()
        self.assertIn('Missing start marker in data', cm.exception.args)
        self.assert_callargs_on_sent_data([b'ISTART[206,206,""]IEND\0'])

    async def test_empty_response(self):
        g90 = G90BaseCommand(
            host='mocked', port=12345, code=206, sock=self.socket_mock)
        self.socket_mock.recvfrom.return_value = (
            b'ISTARTIEND\0', ('mocked', 12345))

        await g90.process()
        self.assert_callargs_on_sent_data([b'ISTART[206,206,""]IEND\0'])

    async def test_no_code_response(self):
        g90 = G90BaseCommand(
            host='mocked', port=12345, code=206, sock=self.socket_mock)
        self.socket_mock.recvfrom.return_value = (
            b'ISTART[]IEND\0', ('mocked', 12345))

        with self.assertRaises(G90Error) as cm:
            await g90.process()
        self.assertIn("Missing code in response: '[]'", cm.exception.args)
        self.assert_callargs_on_sent_data([b'ISTART[206,206,""]IEND\0'])

    async def test_wrong_code_response(self):
        g90 = G90BaseCommand(
            host='mocked', port=12345, code=206, sock=self.socket_mock)
        self.socket_mock.recvfrom.return_value = (
            b'ISTART[106,[""]]IEND\0', ('mocked', 12345))

        with self.assertRaises(G90Error) as cm:
            await g90.process()
        self.assertIn('Wrong response - received code 106, expected code 206',
                      cm.exception.args)
        self.assert_callargs_on_sent_data([b'ISTART[206,206,""]IEND\0'])

    async def test_no_data_response(self):
        g90 = G90BaseCommand(
            host='mocked', port=12345, code=206, sock=self.socket_mock)
        self.socket_mock.recvfrom.return_value = (
            b'ISTART[206]IEND\0', ('mocked', 12345))

        with self.assertRaises(G90Error) as cm:
            await g90.process()
        self.assertIn("Missing data in response: '[206]'",
                      cm.exception.args)
        self.assert_callargs_on_sent_data([b'ISTART[206,206,""]IEND\0'])

    async def test_no_end_marker(self):
        g90 = G90BaseCommand(
            host='mocked', port=12345, code=206, sock=self.socket_mock)
        self.socket_mock.recvfrom.return_value = (
            b'ISTART[206,[]]IEND', ('mocked', 12345))

        with self.assertRaises(G90Error) as cm:
            await g90.process()
        self.assertIn('Missing end marker in data', cm.exception.args)
        self.assert_callargs_on_sent_data([b'ISTART[206,206,""]IEND\0'])

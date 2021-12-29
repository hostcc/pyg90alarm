import sys
import socket
from unittest.mock import call
import asynctest


PYTHON36 = sys.version_info.major == 3 and sys.version_info.minor == 6


class G90Fixture(asynctest.TestCase):

    def setUp(self):
        def mocked_sendto(data, *_, **__):
            if 'timeout' not in self._testMethodName:
                asynctest.set_read_ready(self.socket_mock, self.loop)
            return len(data)

        self.socket_mock = asynctest.SocketMock()
        self.socket_mock.type = socket.SOCK_DGRAM
        if PYTHON36:
            self.socket_mock.sendto.side_effect = mocked_sendto
        else:
            self.socket_mock.send.side_effect = mocked_sendto

    def assert_callargs_on_sent_data(self, data):
        if PYTHON36:
            call_args = [call(x, None) for x in data]
            self.assertEqual(self.socket_mock.sendto.call_args_list, call_args)
        else:
            call_args = [call(x) for x in data]
            self.assertEqual(self.socket_mock.send.call_args_list, call_args)

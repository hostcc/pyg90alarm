import socket
import pytest
from unittest.mock import MagicMock
from helpers import set_read_ready


@pytest.fixture
def mock_sock(request):
    socket_mock = MagicMock()
    socket_mock.type = socket.SOCK_DGRAM

    def mocked_sendto(data, *_, **__):
        if 'timeout' not in request.node.name:
            set_read_ready(socket_mock)
        return len(data)

    socket_mock.send.side_effect = mocked_sendto
    return socket_mock

import sys
import asynctest
from .fixtures import G90Fixture
sys.path.extend(['src', '../src'])
from pyg90alarm.discovery import (   # noqa:E402
    G90Discovery,
)
from pyg90alarm.targeted_discovery import (   # noqa:E402
    G90TargetedDiscovery,
)
from pyg90alarm.const import (  # noqa:E402
    REMOTE_PORT, REMOTE_TARGETED_DISCOVERY_PORT,
    LOCAL_TARGETED_DISCOVERY_PORT,
)


class TestG90Discovery(G90Fixture):
    async def test_discovery(self):
        discovery_data = [
            (b'ISTART[206,["DUMMYGUID1","","","","","",0,0,0,0,"",0,0]]IEND\0',
             ('mocked1', 12345)),
            (b'ISTART[206,["DUMMYGUID2","","","","","",0,0,0,0,"",0,0]]IEND\0',
             ('mocked2', 54321)),
        ]

        def discovery_recvfrom(*_args, **_kwargs):
            try:
                ret = discovery_data.pop(0)
            except IndexError:
                ret = None
            # Indicate the socket is ready for another read if there is mocked
            # data avaialble still
            if discovery_data:
                asynctest.set_read_ready(self.socket_mock, self.loop)
            return ret

        g90 = G90Discovery(host='255.255.255.255',
                           port=REMOTE_PORT,
                           timeout=0.1, sock=self.socket_mock)
        self.socket_mock.recvfrom.side_effect = discovery_recvfrom
        discovered = await g90.process()
        self.assertEqual(discovered[0]['guid'], 'DUMMYGUID1')
        self.assertEqual(discovered[0]['host'], 'mocked1')
        self.assertEqual(discovered[0]['port'], 12345)
        self.assertEqual(discovered[1]['guid'], 'DUMMYGUID2')
        self.assertEqual(discovered[1]['host'], 'mocked2')
        self.assertEqual(discovered[1]['port'], 54321)
        self.assert_callargs_on_sent_data([b'ISTART[206,206,""]IEND\0'])


class TestG90TargetedDiscovery(G90Fixture):
    async def test_targeted_discovery(self):
        data = b'IWTAC_PROBE_DEVICE_ACK,TSV018-3SIA' \
               b',1.2,1.1,206,1.8,3,3,1,0,2,50,100\0'

        g90 = G90TargetedDiscovery(
            device_id='DUMMYGUID',
            host='255.255.255.255',
            port=REMOTE_TARGETED_DISCOVERY_PORT,
            local_port=LOCAL_TARGETED_DISCOVERY_PORT,
            timeout=0.1, sock=self.socket_mock)
        self.socket_mock.recvfrom.return_value = (data, ('mocked', 12345))
        discovered = await g90.process()
        self.assertEqual(discovered[0]['guid'], 'DUMMYGUID')
        self.assertEqual(discovered[0]['host'], 'mocked')
        self.assertEqual(discovered[0]['port'], 12345)
        self.assert_callargs_on_sent_data([b'IWTAC_PROBE_DEVICE,DUMMYGUID\0'])

    async def test_targeted_discovery_wrong_response_start_marker(self):
        data = b'IWTAC_PROBE_DEVICE_ACK_BAD,TSV018-3SIA' \
               b',1.2,1.1,206,1.8,3,3,1,0,2,50,100\0'

        g90 = G90TargetedDiscovery(
            device_id='DUMMYGUID',
            host='255.255.255.255',
            port=REMOTE_TARGETED_DISCOVERY_PORT,
            local_port=LOCAL_TARGETED_DISCOVERY_PORT,
            timeout=0.1, sock=self.socket_mock)
        self.socket_mock.recvfrom.return_value = (data, ('mocked', 12345))

        with self.assertLogs(level='WARNING') as cm:
            await g90.process()
            self.assertEqual(cm.output, [
                'WARNING:pyg90alarm.targeted_discovery:'
                'Got exception, ignoring: Invalid discovery response'
            ])

    async def test_targeted_discovery_wrong_response_end_marker(self):
        data = b'IWTAC_PROBE_DEVICE_ACK,TSV018-3SIA' \
               b',1.2,1.1,206,1.8,3,3,1,0,2,50,100'

        g90 = G90TargetedDiscovery(
            device_id='DUMMYGUID',
            host='255.255.255.255',
            port=REMOTE_TARGETED_DISCOVERY_PORT,
            local_port=LOCAL_TARGETED_DISCOVERY_PORT,
            timeout=0.1, sock=self.socket_mock)
        self.socket_mock.recvfrom.return_value = (data, ('mocked', 12345))

        with self.assertLogs(level='WARNING') as cm:
            await g90.process()
            self.assertEqual(cm.output, [
                'WARNING:pyg90alarm.targeted_discovery:'
                'Got exception, ignoring: Invalid discovery response'
            ])

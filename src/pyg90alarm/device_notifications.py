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

import json
import logging
from collections import namedtuple
import asyncio
from .callback import G90Callback

_LOGGER = logging.getLogger(__name__)


class G90NotificationInfo(namedtuple('G90NotificationInfo',
                                     ['code', 'data'])):
    """
    tbd

    :meta private:
    """


class G90ZoneNotification(namedtuple('G90ZoneNotification',
                                     ['kind', 'data'])):
    """
    tbd

    :meta private:
    """


class G90ZoneInfo(namedtuple('G90ZoneInfo',
                             ['idx', 'name'])):
    """
    tbd

    :meta private:
    """


class G90ArmDisarmInfo(namedtuple('G90ArmDisarmInfo',
                                  ['state'])):
    """
    tbd

    :meta private:
    """


class G90DeviceEvent(namedtuple('G90DeviceEvent',
                                ['type', 'event_id', 'resv2', 'resv3',
                                 'zone_name', 'device_id', 'unix_time',
                                 'resv4', 'other'])):
    """
    tbd

    :meta private:
    """


class G90DeviceNotificationProtocol:
    """
    tbd

    :meta private:
    """
    def __init__(self, armdisarm_cb=None, sensor_cb=None,
                 device_event_cb=None):
        """
        tbd
        """
        self._armdisarm_cb = armdisarm_cb
        self._sensor_cb = sensor_cb
        self._device_event_cb = device_event_cb

    def connection_made(self, transport):
        """
        tbd
        """

    def connection_lost(self, exc):
        """
        tbd
        """

    def datagram_received(self, data, addr):

        """
        tbd
        """
        s_data = data.decode('utf-8')
        if not s_data.endswith('\0'):
            raise Exception('Missing end marker in data')
        payload = s_data[:-1]
        _LOGGER.debug('Received device notification from %s:%s: %s',
                      addr[0], addr[1], payload)
        info = json.loads(payload)
        g90_notification_info = G90NotificationInfo(*info)

        # Device notifications
        if g90_notification_info.code == 170:
            g90_zone_notification = G90ZoneNotification(
                *g90_notification_info.data)

            # Zone notification
            if g90_zone_notification.kind == 5:
                g90_zone_info = G90ZoneInfo(*g90_zone_notification.data)
                _LOGGER.debug('Sensor notification: %s', g90_zone_info)
                G90Callback.invoke(self._sensor_cb,
                                   g90_zone_info.idx,
                                   g90_zone_info.name)
                return

            # Arm/disarm notification
            if g90_zone_notification.kind == 1:
                g90_armdisarm_info = G90ArmDisarmInfo(
                    *g90_zone_notification.data)
                _LOGGER.debug('Arm/disarm notification: %s',
                              g90_armdisarm_info)
                G90Callback.invoke(self._armdisarm_cb,
                                   g90_armdisarm_info.state)
                return

        if g90_notification_info.code == 208:  # Device event
            g90_device_event = G90DeviceEvent(*g90_notification_info.data)
            _LOGGER.debug('Device event: %s', g90_device_event)
            G90Callback.invoke(self._device_event_cb,
                               g90_device_event)
            return

        _LOGGER.warning('Unknown notification received from %s:%s: %s',
                        addr[0], addr[1], info)


class G90DeviceNotifications:
    """
    tbd
    """
    def __init__(self, port=12901, armdisarm_cb=None, sensor_cb=None,
                 device_event_cb=None, sock=None):
        # pylint: disable=too-many-arguments
        self._notification_transport = None
        self._port = port
        self._armdisarm_cb = armdisarm_cb
        self._sensor_cb = sensor_cb
        self._device_event_cb = device_event_cb
        self._sock = sock

    def proto_factory(self):
        """
        tbd
        """
        return G90DeviceNotificationProtocol(
            self._armdisarm_cb, self._sensor_cb, self._device_event_cb)

    async def listen(self):
        """
        tbd
        """
        try:
            loop = asyncio.get_running_loop()
        except AttributeError:
            loop = asyncio.get_event_loop()

        if self._sock:
            _LOGGER.debug('Using provided socket %s', self._sock)
            (self._notification_transport,
             _protocol) = await loop.create_datagram_endpoint(
                self.proto_factory,
                sock=self._sock)
        else:
            _LOGGER.debug('Creating UDP endpoint for 0.0.0.0:%s',
                          self._port)
            (self._notification_transport,
             _protocol) = await loop.create_datagram_endpoint(
                self.proto_factory,
                local_addr=('0.0.0.0', self._port))

    def close(self):
        """
        tbd
        """
        if self._notification_transport:
            self._notification_transport.close()

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
Implements support for notifications/alerts sent by G90 alarm panel.
"""

import json
import logging
from collections import namedtuple
import asyncio
from .callback import G90Callback
from .const import (
    G90MessageTypes,
    G90NotificationTypes,
    G90AlertTypes,
    G90AlertStateChangeTypes,
    G90ArmDisarmTypes,
    G90AlertSources,
)


_LOGGER = logging.getLogger(__name__)


class G90Message(namedtuple('G90Message',
                            ['code', 'data'])):
    """
    tbd

    :meta private:
    """


class G90Notification(namedtuple('G90Notification',
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


class G90DeviceAlert(namedtuple('G90DeviceAlert',
                                ['type', 'event_id', 'source', 'state',
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
                 door_open_close_cb=None, alarm_cb=None):
        """
        tbd
        """
        self._armdisarm_cb = armdisarm_cb
        self._sensor_cb = sensor_cb
        self._door_open_close_cb = door_open_close_cb
        self._alarm_cb = alarm_cb

    def connection_made(self, transport):
        """
        tbd
        """

    def connection_lost(self, exc):
        """
        tbd
        """

    def _handle_notification(self, addr, notification):
        # Sensor activity notification
        if notification.kind == G90NotificationTypes.SENSOR_ACTIVITY:
            g90_zone_info = G90ZoneInfo(*notification.data)
            _LOGGER.debug('Sensor notification: %s', g90_zone_info)
            G90Callback.invoke(self._sensor_cb,
                               g90_zone_info.idx,
                               g90_zone_info.name)
            return

        # Arm/disarm notification
        if notification.kind == G90NotificationTypes.ARM_DISARM:
            g90_armdisarm_info = G90ArmDisarmInfo(
                *notification.data)
            # Map the state received from the device to corresponding enum
            state = G90ArmDisarmTypes(g90_armdisarm_info.state)
            _LOGGER.debug('Arm/disarm notification: %s',
                          state)
            G90Callback.invoke(self._armdisarm_cb,
                               state)
            return

        _LOGGER.warning('Unknown notification received from %s:%s:'
                        ' kind %s, data %s',
                        addr[0], addr[1], notification.kind, notification.data)

    def _handle_alert(self, addr, alert):
        if alert.type == G90AlertTypes.DOOR_OPEN_CLOSE:
            is_open = (
                alert.source == G90AlertSources.SENSOR and alert.state == 1
            ) or alert.source == G90AlertSources.DOORBELL
            _LOGGER.debug('Door open_close alert: %s', alert)
            G90Callback.invoke(self._door_open_close_cb,
                               alert.event_id, alert.zone_name,
                               is_open)
            return

        if alert.type == G90AlertTypes.STATE_CHANGE:
            # Define the mapping between device state received in the alert, to
            # common `G90ArmDisarmTypes` enum that is used when setting device
            # arm state and received in the corresponding notifications. The
            # primary reason is to unify state as passed down to the callbacks.
            # The map covers only subset of state changes pertinent to
            # arm/disarm state changes
            alarm_arm_disarm_state_map = {
                G90AlertStateChangeTypes.ARM_HOME: G90ArmDisarmTypes.ARM_HOME,
                G90AlertStateChangeTypes.ARM_AWAY: G90ArmDisarmTypes.ARM_AWAY,
                G90AlertStateChangeTypes.DISARM: G90ArmDisarmTypes.DISARM
            }

            state = alarm_arm_disarm_state_map.get(alert.event_id, None)
            if state:
                # We received the device state change related to arm/disarm,
                # invoke the corresponding callback
                _LOGGER.debug('Arm/disarm state change: %s', state)
                G90Callback.invoke(self._armdisarm_cb, state)
                return

        if alert.type == G90AlertTypes.ALARM:
            _LOGGER.debug('Alarm: %s', alert.zone_name)
            G90Callback.invoke(self._alarm_cb, alert.event_id, alert.zone_name)
            return

        _LOGGER.warning('Unknown alert received from %s:%s:'
                        ' type %s, data %s',
                        addr[0], addr[1], alert.type, alert)

    def datagram_received(self, data, addr):  # pylint:disable=R0911
        """
        tbd
        """
        s_data = data.decode('utf-8')
        if not s_data.endswith('\0'):
            _LOGGER.error('Missing end marker in data')
            return
        payload = s_data[:-1]
        _LOGGER.debug('Received device message from %s:%s: %s',
                      addr[0], addr[1], payload)
        try:
            message = json.loads(payload)
            g90_message = G90Message(*message)
        except json.JSONDecodeError as exc:
            _LOGGER.error("Unable to parse device message '%s' as JSON: %s",
                          payload, exc)
            return
        except TypeError as exc:
            _LOGGER.error("Device message '%s' is malformed: %s",
                          payload, exc)
            return

        # Device notifications
        if g90_message.code == G90MessageTypes.NOTIFICATION:
            try:
                data = G90Notification(*g90_message.data)
            except TypeError as exc:
                _LOGGER.error('Bad notification received from %s:%s: %s',
                              addr[0], addr[1], exc)
                return
            self._handle_notification(addr, data)
            return

        # Device alerts
        if g90_message.code == G90MessageTypes.ALERT:
            try:
                data = G90DeviceAlert(*g90_message.data)
            except TypeError as exc:
                _LOGGER.error('Bad alert received from %s:%s: %s',
                              addr[0], addr[1], exc)
                return
            self._handle_alert(addr, data)
            return

        _LOGGER.warning('Unknown message received from %s:%s: %s',
                        addr[0], addr[1], message)


class G90DeviceNotifications:
    """
    tbd
    """
    def __init__(self, port, host,
                 armdisarm_cb=None, sensor_cb=None,
                 door_open_close_cb=None, alarm_cb=None):
        # pylint: disable=too-many-arguments
        self._notification_transport = None
        self._host = host
        self._port = port
        self._armdisarm_cb = armdisarm_cb
        self._sensor_cb = sensor_cb
        self._door_open_close_cb = door_open_close_cb
        self._alarm_cb = alarm_cb

    def proto_factory(self):
        """
        tbd
        """
        return G90DeviceNotificationProtocol(
            armdisarm_cb=self._armdisarm_cb,
            sensor_cb=self._sensor_cb,
            door_open_close_cb=self._door_open_close_cb,
            alarm_cb=self._alarm_cb
        )

    async def listen(self):
        """
        tbd
        """
        try:
            loop = asyncio.get_running_loop()
        except AttributeError:
            loop = asyncio.get_event_loop()

        _LOGGER.debug('Creating UDP endpoint for %s:%s',
                      self._host, self._port)
        (self._notification_transport,
         _protocol) = await loop.create_datagram_endpoint(
            self.proto_factory,
            local_addr=(self._host, self._port))

    def close(self):
        """
        tbd
        """
        if self._notification_transport:
            self._notification_transport.close()

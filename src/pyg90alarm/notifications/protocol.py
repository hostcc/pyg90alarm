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
Defines notification protocol for `NotificationBase` class.
"""

from ..const import (
    G90ArmDisarmTypes,
    G90RemoteButtonStates,
)


class G90NotificationProtocol:
    """
    Protocol for notification handling.
    """
    async def on_armdisarm(self, state: G90ArmDisarmTypes) -> None:
        """
        Invoked when device is armed or disarmed.

        :param state: State of the device
        """

    async def on_sensor_activity(self, idx: int, name: str) -> None:
        """
        Invoked on sensor activity.

        :param idx: Index of the sensor.
        :param name: Name of the sensor.
        """

    async def on_door_open_when_arming(
        self, event_id: int, zone_name: str
    ) -> None:
        """
        Invoked when door open is detected when panel is armed.

        :param event_id: Index of the sensor.
        :param zone_name: Name of the sensor that reports door open.
        """

    async def on_door_open_close(
        self, event_id: int, zone_name: str, is_open: bool
    ) -> None:
        """
        Invoked when door sensor reports it opened or closed.

        :param event_id: Index of the sensor reporting the event.
        :param zone_name: Name of the sensor that reports door open/close.
        :param is_open: Indicates if the door is open.
        """

    async def on_low_battery(self, event_id: int, zone_name: str) -> None:
        """
        Invoked when a sensor reports it is low on battery.

        :param event_id: Index of the sensor.
        :param zone_name: Name of the sensor that reports low battery.
        """

    async def on_alarm(
        self, event_id: int, zone_name: str, is_tampered: bool
    ) -> None:
        """
        Invoked when device triggers the alarm.

        :param event_id: Index of the sensor.
        :param zone_name: Name of the zone that triggered the alarm.
        """

    async def on_remote_button_press(
        self, event_id: int, zone_name: str, button: G90RemoteButtonStates
    ) -> None:
        """
        Invoked when a remote button is pressed.

        Please note there will only be call to the method w/o invoking
        :meth:`G90DeviceNotifications.on_sensor_activity`.

        :param event_id: Index of the sensor associated with the remote.
        :param zone_name: Name of the sensor that reports remote button press.
        :param button: The button pressed on the remote
        """

    async def on_sos(
        self, event_id: int, zone_name: str, is_host_sos: bool
    ) -> None:
        """
        Invoked when SOS is triggered.

        Please note that the panel might not set its status to alarm
        internally, so that :meth:`G90DeviceNotifications` might need an
        explicit call in the derived class to simulate that.

        :param event_id: Index of the sensor.
        :param zone_name: Name of the sensor that reports SOS.
        :param is_host_sos: Indicates if the SOS is host-initiated.
        """

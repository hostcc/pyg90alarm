# Copyright (c) 2025 Ilia Sotnikov
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
Sensor list.
"""
from __future__ import annotations
from typing import AsyncGenerator, Optional, TYPE_CHECKING
import logging
import asyncio

from .sensor import G90Sensor
from .base_list import G90BaseList
from ..const import G90Commands
from ..exceptions import G90EntityRegistrationError, G90Error
from ..definitions.sensors import G90SensorDefinitions
from ..entities.sensor import G90SensorUserFlags

if TYPE_CHECKING:
    from ..alarm import G90Alarm

_LOGGER = logging.getLogger(__name__)


class G90SensorList(G90BaseList[G90Sensor]):
    """
    Sensor list class.
    """
    def __init__(self, parent: G90Alarm) -> None:
        super().__init__(parent)
        self._sensor_change_future: Optional[asyncio.Future[G90Sensor]] = None

    async def _fetch(self) -> AsyncGenerator[G90Sensor, None]:
        """
        Fetch the list of sensors from the panel.

        :yields: G90Sensor: Sensor entity.
        """
        entities = self._parent.paginated_result(
            G90Commands.GETSENSORLIST
        )

        async for entity in entities:
            yield G90Sensor(
                *entity.data, parent=self._parent, subindex=0,
                proto_idx=entity.proto_idx
            )

    async def sensor_change_callback(
        self, idx: int, name: str, added: bool
    ) -> None:
        """
        Sensor change callback.

        Should be invoked from corresponding panel's notification handler to
        finish the registration process.

        :param idx: Sensor index.
        :param name: Sensor name.
        :param added: True if the sensor was added, False if removed.
        """
        _LOGGER.debug(
            "Sensor change callback: name='%s', index=%d, added=%s",
            name, idx, added
        )
        # The method depends on the future to be created before it is called
        if not self._sensor_change_future:
            raise G90EntityRegistrationError(
                "Sensor change callback called without a future"
            )

        # Update the sensor list to get the latest data, unfortunately there is
        # no panel command to get just a single sensor
        try:
            await self.update()
        except G90Error as err:
            _LOGGER.debug(
                "Failed to update the sensor list: %s", err
            )
            # Indicate the error to the caller
            self._sensor_change_future.set_exception(err)
            return

        # Attempt to find the sensor just changed by its index
        if not (found := await self.find_by_idx(
            idx, exclude_unavailable=False
        )):
            msg = (
                f"Failed to find the added sensor '{name}'"
                f' at index {idx}'
            )
            _LOGGER.debug(msg)
            # Indicate the error to the caller
            self._sensor_change_future.set_exception(
                G90EntityRegistrationError(msg)
            )
            return

        # Provide the found sensor as the future result so that the caller
        # can use it
        self._sensor_change_future.set_result(found)

    async def register(
        self, definition_name: str,
        room_id: int, timeout: float, name: Optional[str] = None,
    ) -> G90Sensor:
        """
        Registers sensor to the panel.

        :param definition_name: Sensor definition name.
        :param room_id: Room ID to assign the sensor to.
        :param timeout: Timeout for the registration process.
        :param name: Optional name for the sensor, if not provided, the
         definition name will be used.
        :raises G90EntityRegistrationError: If the registration fails.
        :return: G90Sensor: The registered sensor entity.
        """
        sensor_definition = G90SensorDefinitions.get_by_name(definition_name)
        dev_name = name or sensor_definition.name

        # Future is needed to coordinate the registration process with panel
        # notifications (see `sensor_change_callback()` method)
        self._sensor_change_future = asyncio.get_running_loop().create_future()

        # Register the sensor with the panel
        await self._parent.command(
            G90Commands.ADDSENSOR, [
                dev_name,
                # Registering sensor requires to provide a free index from
                # panel point of view
                await self.find_free_idx(),
                room_id,
                sensor_definition.type,
                sensor_definition.subtype,
                sensor_definition.timeout,
                # Newly registered sensors are enabled by default and set to
                # alarm in away and home modes
                G90SensorUserFlags.ENABLED
                | G90SensorUserFlags.ALERT_WHEN_AWAY_AND_HOME,
                sensor_definition.baudrate,
                sensor_definition.protocol,
                sensor_definition.reserved_data,
                sensor_definition.node_count,
                sensor_definition.rx,
                sensor_definition.tx,
                sensor_definition.private_data
            ]
        )

        # Waiting for the registration to finish, where panel will send
        # corresponding notification processed by `sensor_change_callback()`
        # method, which manipulates the future created above.
        done, _ = await asyncio.wait(
            [self._sensor_change_future], timeout=timeout
        )

        if self._sensor_change_future not in done:
            msg = f"Failed to learn the device '{dev_name}', timed out"
            _LOGGER.debug(msg)
            raise G90EntityRegistrationError(msg)

        # Propagate any exception that might have occurred in
        # `sensor_change_callback()` method during the registration process
        self._sensor_change_future.exception()

        # Return the registered sensor entity
        return self._sensor_change_future.result()

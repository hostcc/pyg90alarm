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
Device list.
"""
from typing import AsyncGenerator, Optional
import logging
import asyncio
from .device import G90Device
from .base_list import G90BaseList
from ..const import G90Commands
from ..definitions.devices import G90DeviceDefinitions
from ..entities.sensor import G90SensorUserFlags
from ..exceptions import G90EntityRegistrationError

_LOGGER = logging.getLogger(__name__)


class G90DeviceList(G90BaseList[G90Device]):
    """
    Device list class.
    """
    async def _fetch(self) -> AsyncGenerator[G90Device, None]:
        """
        Fetch the list of devices from the panel.

        :yields: G90Device: Device entity.
        """
        devices = self._parent.paginated_result(
            G90Commands.GETDEVICELIST
        )

        async for device in devices:
            obj = G90Device(
                *device.data, parent=self._parent, subindex=0,
                proto_idx=device.proto_idx
            )

            yield obj

            # Multi-node devices (first node has already been handled
            # above)
            for node in range(1, obj.node_count):
                obj = G90Device(
                    *device.data, parent=self._parent,
                    subindex=node, proto_idx=device.proto_idx
                )
                yield obj

    async def register(
        self, definition_name: str,
        room_id: int, timeout: float, name: Optional[str] = None,
    ) -> G90Device:
        """
        Register the devices (switches) to the panel.

        Contrary to registering the sensors, the registration of devices does
        not have an associated notification from the panel, hence the list of
        devices is polled to determine when new device is added.

        :param definition_name: Name of the device definition to register.
        :param room_id: ID of the room to assign the device to.
        :param timeout: Timeout in seconds to wait for the device to be added.
        :param name: Optional name for the device, if not provided, the
         name from the definition will be used.
        :raises G90EntityRegistrationError: If the device could not be
         registered or found after the registration.
        :return: G90Device: The registered device entity.
        """
        device_definition = G90DeviceDefinitions.get_by_name(definition_name)
        dev_name = name or device_definition.name

        # Register the device with the panel
        await self._parent.command(
            G90Commands.ADDDEVICE, [
                dev_name,
                # Registering device requires to provide a free index from
                # panel point of view
                await self.find_free_idx(),
                room_id,
                device_definition.type,
                device_definition.subtype,
                device_definition.timeout,
                # Newly registered devices are enabled by default
                G90SensorUserFlags.ENABLED,
                device_definition.baudrate,
                device_definition.protocol,
                device_definition.reserved_data,
                device_definition.node_count,
                device_definition.rx,
                device_definition.tx,
                device_definition.private_data
            ]
        )

        # Confirm the registration of the device to the panel
        res = await self._parent.command(
            G90Commands.SENDREGDEVICERESULT,
            # 1 = register, 0 = cancel
            [1]
        )

        # The command above returns the index of the added device in the
        # device list from panel point of view
        try:
            added_at = next(iter(res))
            _LOGGER.debug('Device added at index=%s', added_at)
        except StopIteration:
            msg = (
                f"Failed to register device '{dev_name}' - response does not"
                ' contain the index in the device list'
            )
            _LOGGER.debug(msg)
            # pylint: disable=raise-missing-from
            raise G90EntityRegistrationError(msg)

        # Update the list of devices polling for the new entity
        # to appear in the list - it takes some time for the panel
        # to process the registration and add the device to the list
        found = None
        for _ in range(int(timeout)):
            # Update the list of devices from the panel
            await self.update()
            # Try to find the device by the index it was added at
            if found := await self.find_by_idx(
                added_at, exclude_unavailable=False
            ):
                break
            await asyncio.sleep(1)

        if found:
            return found

        msg = (
            f"Failed to find the added device '{dev_name}'"
            f' at index {added_at}'
        )
        _LOGGER.debug(msg)
        raise G90EntityRegistrationError(msg)

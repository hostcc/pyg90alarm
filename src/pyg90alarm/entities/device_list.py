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
from typing import AsyncGenerator
from .device import G90Device
from .base_list import G90BaseList
from ..const import G90Commands


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

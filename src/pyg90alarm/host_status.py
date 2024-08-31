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
Protocol entity for G90 alarm panel status.
"""
from __future__ import annotations
from typing import Any, Dict
from dataclasses import dataclass, asdict
from .const import G90ArmDisarmTypes


@dataclass
class G90HostStatus:
    """
    Interprets data fields of GETHOSTSTATUS command.
    """
    host_status_data: int
    host_phone_number: str
    product_name: str
    mcu_hw_version: str
    wifi_hw_version: str

    @property
    def host_status(self) -> G90ArmDisarmTypes:
        """
        Translates host status data to G90ArmDisarmTypes.
        """
        return G90ArmDisarmTypes(self.host_status_data)

    def _asdict(self) -> Dict[str, Any]:
        """
        Returns the host information as dictionary.
        """
        return asdict(self)

# Copyright (c) 2026 Ilia Sotnikov
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
Defines mapping of various events.
"""
from __future__ import annotations
from typing import Dict, TYPE_CHECKING
import logging
from .const import (
    G90AlertSources,
    G90AlertStates,
    G90CommonSensorAlertStates,
    G90InfraredAlertStates,
)

_LOGGER = logging.getLogger(__name__)


def map_alert_state(
    source: G90AlertSources, state: int
) -> G90AlertStates:
    """
    Converts alert state of infrared and other sensors to consolidated one.

    :param source: Source of the alert
    :param state: State code as received from the panel
    :return: Consolidated alert state
    """
    if TYPE_CHECKING:
        # Forward declarations
        key: G90CommonSensorAlertStates | G90InfraredAlertStates
        mapping: Dict[
            G90CommonSensorAlertStates | G90InfraredAlertStates,
            G90AlertStates
        ]

    # Mapping for common sensors
    mapping = {
        G90CommonSensorAlertStates.DOOR_CLOSE:
            G90AlertStates.DOOR_CLOSE,
        G90CommonSensorAlertStates.DOOR_OPEN:
            G90AlertStates.DOOR_OPEN,
        G90CommonSensorAlertStates.SOS:
            G90AlertStates.SOS,
        G90CommonSensorAlertStates.TAMPER:
            G90AlertStates.TAMPER,
        G90CommonSensorAlertStates.LOW_BATTERY:
            G90AlertStates.LOW_BATTERY,
        G90CommonSensorAlertStates.ALARM:
            G90AlertStates.ALARM,
    }
    key = G90CommonSensorAlertStates(state)
    mapping_kind = 'common'

    # Mapping for infrared sensors
    if source == G90AlertSources.INFRARED:
        mapping = {
            G90InfraredAlertStates.MOTION_DETECTED:
                G90AlertStates.MOTION_DETECTED,
            G90InfraredAlertStates.TAMPER:
                G90AlertStates.TAMPER,
            G90InfraredAlertStates.LOW_BATTERY:
                G90AlertStates.LOW_BATTERY,
        }
        key = G90InfraredAlertStates(state)
        mapping_kind = 'infrared'

    try:
        result = mapping[key]
    except KeyError as exc:
        # Raise the error similar to Enum if state is invalid
        raise ValueError(
            f'{state} is not valid for source {source}'
        ) from exc

    _LOGGER.debug(
        'Mapped %s sensor alert state %d to consolidated state %s'
        ' for source %s',
        mapping_kind, state, repr(result), repr(source)
    )
    return result

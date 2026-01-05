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
Protocol entity for G90 alarm panel config.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import IntEnum
from .dataclass_load_save import DataclassLoadSave
from ..const import G90Commands


class G90SpeechLanguage(IntEnum):
    """
    Supported speech languages.
    """
    ENGLISH_FEMALE = 1
    ENGLISH_MALE = 2
    CHINESE_FEMALE = 3
    CHINESE_MALE = 4
    GERMAN_FEMALE = 5
    GERMAN_MALE = 6
    SPANISH_FEMALE = 7
    SPANISH_MALE = 8
    DUTCH_FEMALE = 9
    DUTCH_MALE = 10
    SWEDEN_FEMALE = 11
    SWEDEN_MALE = 12
    FRENCH_FEMALE = 13
    FRENCH_MALE = 14
    TURKISH_FEMALE = 15
    TURKISH_MALE = 16
    RUSSIAN_FEMALE = 17
    RUSSIAN_MALE = 18


@dataclass
class G90HostConfig(DataclassLoadSave):
    """
    Interprets data fields of GETHOSTCONFIG/SETHOSTCONFIG commands.
    """
    # pylint: disable=too-many-instance-attributes
    LOAD_COMMAND = G90Commands.GETHOSTCONFIG
    SAVE_COMMAND = G90Commands.SETHOSTCONFIG

    alarm_siren_duration: int
    arm_delay: int
    alarm_delay: int
    backlight_duration: int
    alarm_volume: int
    speech_volume: int
    call_in_ring_duration: int
    _speech_language: int
    key_tone_volume: int
    timezone_offset_m: int
    gsm_volume: int

    @property
    def speech_language(self) -> G90SpeechLanguage:
        """
        Returns the speech language as an enum.
        """
        return G90SpeechLanguage(self._speech_language)

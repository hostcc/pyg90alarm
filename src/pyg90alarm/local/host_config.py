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
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import IntEnum
from ..dataclass.load_save import (
    DataclassLoadSave, field_readonly_if_not_provided,
)
from ..dataclass.validation import validated_int_field
from ..const import G90Commands


class G90SpeechLanguage(IntEnum):
    """
    Supported speech languages.
    """
    NONE = 0
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
    SWEDISH_FEMALE = 11
    SWEDISH_MALE = 12
    FRENCH_FEMALE = 13
    FRENCH_MALE = 14
    TURKISH_FEMALE = 15
    TURKISH_MALE = 16
    RUSSIAN_FEMALE = 17
    RUSSIAN_MALE = 18


class G90VolumeLevel(IntEnum):
    """
    Supported volume levels.
    """
    MUTE = 0
    LOW = 1
    HIGH = 2


@dataclass
class G90HostConfig(DataclassLoadSave):
    """
    Interprets data fields of GETHOSTCONFIG/SETHOSTCONFIG commands.
    """
    # pylint: disable=too-many-instance-attributes
    LOAD_COMMAND = G90Commands.GETHOSTCONFIG
    SAVE_COMMAND = G90Commands.SETHOSTCONFIG

    # The field constraints below have been determined experimentally by
    # entering various values into panel configuration manually. All values
    # received from the panel remotely are trusted (i.e. bypass validation)

    # Duration of the alarm siren when triggered, in seconds
    alarm_siren_duration: int = validated_int_field(
        min_value=0, max_value=999, trust_initial_value=True
    )
    # Delay before arming the panel, in seconds
    arm_delay: int = validated_int_field(
        min_value=0, max_value=255, trust_initial_value=True
    )
    # Delay before the alarm is triggered, in seconds
    alarm_delay: int = validated_int_field(
        min_value=0, max_value=255, trust_initial_value=True
    )
    # Duration of the backlight, in seconds
    backlight_duration: int = validated_int_field(
        min_value=0, max_value=255, trust_initial_value=True
    )
    # Alarm volume level, applies to panel's built-in speaker
    _alarm_volume_level: int = validated_int_field(
        min_value=min(G90VolumeLevel), max_value=max(G90VolumeLevel),
        trust_initial_value=True
    )
    # Speech volume level
    _speech_volume_level: int = validated_int_field(
        min_value=min(G90VolumeLevel), max_value=max(G90VolumeLevel),
        trust_initial_value=True
    )
    # Duration of the ring for the incoming call, in seconds
    ring_duration: int = validated_int_field(
        min_value=0, max_value=255, trust_initial_value=True
    )
    # Speech language
    _speech_language: int = validated_int_field(
        min_value=min(G90SpeechLanguage), max_value=max(G90SpeechLanguage),
        trust_initial_value=True
    )
    # Key tone volume level
    _key_tone_volume_level: int = validated_int_field(
        min_value=min(G90VolumeLevel), max_value=max(G90VolumeLevel),
        trust_initial_value=True
    )
    # Timezone offset, in minutes
    timezone_offset_m: int = validated_int_field(
        min_value=-720, max_value=720, trust_initial_value=True
    )
    # Ring volume level for incoming calls, could only be modified if the
    # device has sent a value for it when loading the data (i.e. has a cellular
    # module) otherwise it is read-only and None
    _ring_volume_level: Optional[int] = field_readonly_if_not_provided(
        default=None
    )

    @property
    def speech_language(self) -> G90SpeechLanguage:
        """
        Returns the speech language as an enum.
        """
        return G90SpeechLanguage(self._speech_language)

    @speech_language.setter
    def speech_language(self, value: G90SpeechLanguage) -> None:
        self._speech_language = value.value

    @property
    def alarm_volume_level(self) -> G90VolumeLevel:
        """
        Returns the alarm volume level as an enum.
        """
        return G90VolumeLevel(self._alarm_volume_level)

    @alarm_volume_level.setter
    def alarm_volume_level(self, value: G90VolumeLevel) -> None:
        self._alarm_volume_level = value.value

    @property
    def speech_volume_level(self) -> G90VolumeLevel:
        """
        Returns the speech volume level as an enum.
        """
        return G90VolumeLevel(self._speech_volume_level)

    @speech_volume_level.setter
    def speech_volume_level(self, value: G90VolumeLevel) -> None:
        self._speech_volume_level = value.value

    @property
    def key_tone_volume_level(self) -> G90VolumeLevel:
        """
        Returns the key tone volume level as an enum.
        """
        return G90VolumeLevel(self._key_tone_volume_level)

    @key_tone_volume_level.setter
    def key_tone_volume_level(self, value: G90VolumeLevel) -> None:
        self._key_tone_volume_level = value.value

    @property
    def ring_volume_level(self) -> Optional[G90VolumeLevel]:
        """
        Returns the ring volume level as an enum.

        :return: Ring volume level, or `None` if the device does not have
         cellular module.
        """
        if self._ring_volume_level is None:
            return None

        return G90VolumeLevel(self._ring_volume_level)

    @ring_volume_level.setter
    def ring_volume_level(self, value: G90VolumeLevel) -> None:
        self._ring_volume_level = value.value

    def _asdict(self) -> Dict[str, Any]:
        """
        Returns the dataclass fields as a dictionary.
        """
        return {
            'alarm_siren_duration': self.alarm_siren_duration,
            'arm_delay': self.arm_delay,
            'alarm_delay': self.alarm_delay,
            'backlight_duration': self.backlight_duration,
            'alarm_volume_level': self.alarm_volume_level.name,
            'speech_volume_level': self.speech_volume_level.name,
            'ring_duration': self.ring_duration,
            'speech_language': self.speech_language.name,
            'key_tone_volume_level': self.key_tone_volume_level.name,
            'timezone_offset_m': self.timezone_offset_m,
            # The field is optional
            'ring_volume_level': getattr(self.ring_volume_level, 'name', None)
        }

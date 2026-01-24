"""
Tests for package-specific exceptions.
"""
from __future__ import annotations
import pytest

from pyg90alarm.exceptions import G90TimeoutError, G90Error


def test_g90_timeout_error_inheritance() -> None:
    """
    Test that catching G90Error also catches G90TimeoutError.
    """

    with pytest.raises(G90Error):
        raise G90TimeoutError("Timeout occurred")

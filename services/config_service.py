"""
Configuration service for runtime system settings.
"""
import os
from typing import Optional


_DOWNTIME_HOURLY_RATE: Optional[float] = None


def get_downtime_hourly_rate() -> float:
    """Return the configured downtime hourly rate (ZAR)."""
    global _DOWNTIME_HOURLY_RATE
    if _DOWNTIME_HOURLY_RATE is not None:
        return _DOWNTIME_HOURLY_RATE

    env_value = os.getenv("DOWNTIME_HOURLY_RATE")
    if env_value:
        try:
            return float(env_value)
        except ValueError:
            return 250.0

    return 250.0


def set_downtime_hourly_rate(rate: float) -> None:
    """Override the downtime hourly rate in memory."""
    global _DOWNTIME_HOURLY_RATE
    _DOWNTIME_HOURLY_RATE = float(rate)

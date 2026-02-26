"""
Configuration service for runtime system settings.
"""
import os
from typing import Optional


_DOWNTIME_HOURLY_RATE: Optional[float] = None
_DEFAULT_EXPORT_CLIENTS = ["HULAMIN", "PG_BISON"]
_DEFAULT_IMPORT_CLIENTS = ["SACD_IMPORT"]


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


def get_booking_clients(booking_type: str) -> list[str]:
    normalized = str(booking_type or "EXPORT").strip().upper()
    if normalized == "IMPORT":
        env_value = os.getenv("IMPORT_CLIENTS")
        fallback = _DEFAULT_IMPORT_CLIENTS
    else:
        env_value = os.getenv("EXPORT_CLIENTS")
        fallback = _DEFAULT_EXPORT_CLIENTS

    if not env_value:
        return fallback

    values = [item.strip().upper().replace(" ", "_") for item in env_value.split(",") if item.strip()]
    return values or fallback

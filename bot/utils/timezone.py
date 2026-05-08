from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Tashkent")


def now() -> datetime:
    return datetime.now(TZ)


def now_str() -> str:
    return now().strftime("%H:%M:%S")


def now_db() -> str:
    """Formatted string for SQLite storage."""
    return now().strftime("%Y-%m-%d %H:%M:%S")

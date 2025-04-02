from datetime import datetime, timezone

def get_utc_date() -> str:
    """
    Returns the current date and time in UTC as a string in the format 'YYYY-MM-DD HH:MM:SS'.
    """
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


__all__ = ["get_utc_date"] 
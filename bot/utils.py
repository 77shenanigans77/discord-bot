from datetime import datetime, timezone


def normalize_key(value: str) -> str:
    return value.strip().lower().replace(" ", "-")


def split_list(value: str):
    if not value:
        return []
    return [part.strip() for part in value.split("|") if part.strip()]


def parse_color(value: str | None, fallback: int) -> int:
    if not value:
        return fallback
    cleaned = value.strip().replace("#", "")
    if len(cleaned) != 6:
        return fallback
    try:
        return int(cleaned, 16)
    except ValueError:
        return fallback


def now_date_string() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def utc_now():
    return datetime.now(timezone.utc)


def status_config(status: str):
    value = (status or "").lower()
    if value == "stable":
        return {"label": "Stable", "color": 0x57F287, "icon": "🟢"}
    if value == "degraded":
        return {"label": "Degraded", "color": 0xFEE75C, "icon": "🟡"}
    if value == "broken":
        return {"label": "Broken", "color": 0xED4245, "icon": "🔴"}
    if value == "updating":
        return {"label": "Updating", "color": 0x5865F2, "icon": "🔵"}
    if value == "discontinued":
        return {"label": "Discontinued", "color": 0x747F8D, "icon": "⚫"}
    return {"label": "Unknown", "color": 0x2B2D31, "icon": "⚪"}

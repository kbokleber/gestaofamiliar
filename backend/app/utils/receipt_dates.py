from datetime import date, datetime
from typing import Any


_SUPPORTED_DATE_FORMATS = (
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
)


def _parse_receipt_date_string(raw_date: str) -> date | None:
    normalized = raw_date.strip()
    if not normalized:
        return None

    for fmt in _SUPPORTED_DATE_FORMATS:
        try:
            return datetime.strptime(normalized, fmt).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(normalized.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def resolve_receipt_date(ai_data: dict[str, Any], fallback_date: date) -> date:
    raw_date = ai_data.get("date")
    if not raw_date:
        return fallback_date

    if isinstance(raw_date, date):
        return raw_date

    if isinstance(raw_date, datetime):
        return raw_date.date()

    if isinstance(raw_date, str):
        parsed_date = _parse_receipt_date_string(raw_date)
        if parsed_date is not None:
            return parsed_date
        return fallback_date

    return fallback_date

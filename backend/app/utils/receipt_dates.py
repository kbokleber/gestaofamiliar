from datetime import date, datetime
from typing import Any


def resolve_receipt_date(ai_data: dict[str, Any], fallback_date: date) -> date:
    raw_date = ai_data.get("date")
    if not raw_date:
        return fallback_date

    if isinstance(raw_date, date):
        return raw_date

    if isinstance(raw_date, datetime):
        return raw_date.date()

    if isinstance(raw_date, str):
        try:
            return datetime.strptime(raw_date.strip(), "%Y-%m-%d").date()
        except ValueError:
            return fallback_date

    return fallback_date

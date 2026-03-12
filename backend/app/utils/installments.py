import calendar
import re
from datetime import date
from decimal import Decimal
from typing import Any


def _coerce_positive_int(value: Any) -> int | None:
    if value is None:
        return None

    if isinstance(value, int):
        return value if value > 0 else None

    if isinstance(value, float):
        value = int(value)
        return value if value > 0 else None

    if isinstance(value, str):
        digits = re.findall(r"\d+", value)
        if not digits:
            return None
        parsed = int(digits[0])
        return parsed if parsed > 0 else None

    return None


def parse_installment_info(ai_data: dict[str, Any]) -> tuple[int, int]:
    installment_value = ai_data.get("installment") or ai_data.get("installment_info")
    if isinstance(installment_value, str):
        match = re.search(r"(\d+)\s*/\s*(\d+)", installment_value)
        if match:
            current = int(match.group(1))
            total = int(match.group(2))
            if current > 0 and total >= current:
                return current, total

    current = (
        _coerce_positive_int(ai_data.get("current_installment"))
        or _coerce_positive_int(ai_data.get("installment_current"))
        or _coerce_positive_int(ai_data.get("installment_number"))
        or 1
    )
    total = (
        _coerce_positive_int(ai_data.get("total_installments"))
        or _coerce_positive_int(ai_data.get("installment_total"))
        or _coerce_positive_int(ai_data.get("installments"))
        or 1
    )

    if total < current:
        total = current

    return current, total


def add_months_preserving_day(base_date: date, months_to_add: int) -> date:
    year = base_date.year + (base_date.month - 1 + months_to_add) // 12
    month = (base_date.month - 1 + months_to_add) % 12 + 1
    day = min(base_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def build_installment_entries(
    *,
    description: str,
    amount: Decimal,
    entry_date: date,
    total_installments: int,
    current_installment: int,
    is_paid: bool,
) -> list[dict[str, Any]]:
    if total_installments <= 1:
        return [
            {
                "description": description,
                "amount": amount,
                "date": entry_date,
                "is_paid": is_paid,
            }
        ]

    entries: list[dict[str, Any]] = []
    for installment_number in range(current_installment, total_installments + 1):
        month_offset = installment_number - current_installment
        entries.append(
            {
                "description": f"{description} (Parcela {installment_number}/{total_installments})",
                "amount": amount,
                "date": add_months_preserving_day(entry_date, month_offset),
                "is_paid": is_paid if installment_number == current_installment else False,
            }
        )

    return entries

import calendar
import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable


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


def split_amount_across_installments(amount: Decimal, total_installments: int) -> list[Decimal]:
    if total_installments <= 1:
        return [amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)]

    total_cents = int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    base_cents = total_cents // total_installments
    remainder_cents = total_cents % total_installments

    amounts: list[Decimal] = []
    for installment_index in range(total_installments):
        cents = base_cents + (1 if installment_index < remainder_cents else 0)
        amounts.append((Decimal(cents) / Decimal("100")).quantize(Decimal("0.01")))

    return amounts


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

    installment_amounts = split_amount_across_installments(amount, total_installments)
    entries: list[dict[str, Any]] = []
    for installment_number in range(current_installment, total_installments + 1):
        month_offset = installment_number - current_installment
        entries.append(
            {
                "description": f"{description} (Parcela {installment_number}/{total_installments})",
                "amount": installment_amounts[installment_number - 1],
                "date": add_months_preserving_day(entry_date, month_offset),
                "is_paid": is_paid if installment_number == current_installment else False,
            }
        )

    return entries


def _normalize_description(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _build_entry_signature(
    *,
    description: str,
    amount: Decimal,
    entry_date: date,
    entry_type: str,
) -> tuple[str, Decimal, date, str]:
    return (
        _normalize_description(description),
        Decimal(str(amount)).quantize(Decimal("0.01")),
        entry_date,
        entry_type.strip().upper(),
    )


def find_duplicate_installment_entries(
    existing_entries: Iterable[Any],
    installment_entries: list[dict[str, Any]],
    *,
    entry_type: str,
) -> list[dict[str, Any]]:
    existing_signatures = {
        _build_entry_signature(
            description=entry.description,
            amount=entry.amount,
            entry_date=entry.date,
            entry_type=getattr(entry, "type", entry_type),
        )
        for entry in existing_entries
    }

    return [
        installment_entry
        for installment_entry in installment_entries
        if _build_entry_signature(
            description=installment_entry["description"],
            amount=installment_entry["amount"],
            entry_date=installment_entry["date"],
            entry_type=entry_type,
        )
        in existing_signatures
    ]

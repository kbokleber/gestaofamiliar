from datetime import date
from decimal import Decimal

from app.utils.installments import build_installment_entries, parse_installment_info


def test_parse_installment_info_supports_fraction_string():
    current, total = parse_installment_info(
        {
            "installment": "3/10",
        }
    )

    assert current == 3
    assert total == 10


def test_build_installment_entries_creates_current_and_future_months():
    entries = build_installment_entries(
        description="Fatura Cartao",
        amount=Decimal("120.50"),
        entry_date=date(2026, 3, 12),
        total_installments=3,
        current_installment=1,
        is_paid=True,
    )

    assert len(entries) == 3

    assert entries[0]["description"] == "Fatura Cartao (Parcela 1/3)"
    assert entries[0]["date"] == date(2026, 3, 12)
    assert entries[0]["amount"] == Decimal("120.50")
    assert entries[0]["is_paid"] is True

    assert entries[1]["description"] == "Fatura Cartao (Parcela 2/3)"
    assert entries[1]["date"] == date(2026, 4, 12)
    assert entries[1]["is_paid"] is False

    assert entries[2]["description"] == "Fatura Cartao (Parcela 3/3)"
    assert entries[2]["date"] == date(2026, 5, 12)
    assert entries[2]["is_paid"] is False


def test_build_installment_entries_clamps_shorter_months():
    entries = build_installment_entries(
        description="Notebook",
        amount=Decimal("300.00"),
        entry_date=date(2026, 1, 31),
        total_installments=3,
        current_installment=1,
        is_paid=True,
    )

    assert [entry["date"] for entry in entries] == [
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 31),
    ]

from datetime import date

from app.utils.receipt_dates import resolve_receipt_date


def test_resolve_receipt_date_prefers_extracted_purchase_date():
    resolved = resolve_receipt_date(
        {"date": "2026-03-05"},
        fallback_date=date(2026, 3, 12),
    )

    assert resolved == date(2026, 3, 5)


def test_resolve_receipt_date_uses_upload_date_when_missing():
    resolved = resolve_receipt_date(
        {},
        fallback_date=date(2026, 3, 12),
    )

    assert resolved == date(2026, 3, 12)


def test_resolve_receipt_date_uses_upload_date_when_invalid():
    resolved = resolve_receipt_date(
        {"date": "data-invalida"},
        fallback_date=date(2026, 3, 12),
    )

    assert resolved == date(2026, 3, 12)


def test_resolve_receipt_date_accepts_common_brazilian_format():
    resolved = resolve_receipt_date(
        {"date": "05/03/2026"},
        fallback_date=date(2026, 3, 12),
    )

    assert resolved == date(2026, 3, 5)


def test_resolve_receipt_date_accepts_iso_datetime_string():
    resolved = resolve_receipt_date(
        {"date": "2026-03-05T14:22:00"},
        fallback_date=date(2026, 3, 12),
    )

    assert resolved == date(2026, 3, 5)

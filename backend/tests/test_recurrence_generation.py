from app.utils.recurrence_generation import resolve_months_to_process


def test_resolve_months_to_process_returns_full_year_when_month_is_none():
    assert resolve_months_to_process(None) == list(range(1, 13))


def test_resolve_months_to_process_returns_single_selected_month():
    assert resolve_months_to_process(6) == [6]


def test_resolve_months_to_process_rejects_invalid_month():
    try:
        resolve_months_to_process(13)
    except ValueError as exc:
        assert str(exc) == "Mês inválido. Informe um valor entre 1 e 12."
    else:
        raise AssertionError("Expected ValueError for invalid month")

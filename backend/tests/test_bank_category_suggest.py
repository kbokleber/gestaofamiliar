from types import SimpleNamespace

from app.utils.bank_category_suggest import suggest_category_for_bank_line
from app.utils.category_matching import score_category_name_vs_description


def test_score_category_name_vs_description_uses_description_only():
    assert score_category_name_vs_description("Supermercado", "recibo supermercado bh") >= 0.72
    assert score_category_name_vs_description("Moradia", "ifood lanche") < 0.72


def test_suggest_category_for_bank_line_ifood_alimentacao():
    cats = [
        SimpleNamespace(id=1, name="Alimentação", type="EXPENSE", is_active=True),
        SimpleNamespace(id=2, name="Transporte", type="EXPENSE", is_active=True),
    ]
    cat, conf = suggest_category_for_bank_line("IFood pedido", "EXPENSE", cats)
    assert cat is cats[0]
    assert conf in ("high", "low")


def test_suggest_category_for_bank_line_shell_combustivel():
    cats = [
        SimpleNamespace(id=1, name="Combustível", type="EXPENSE", is_active=True),
        SimpleNamespace(id=2, name="Alimentação", type="EXPENSE", is_active=True),
    ]
    cat, conf = suggest_category_for_bank_line("COMPRA POSTO SHELL", "EXPENSE", cats)
    assert cat is cats[0]
    assert conf in ("high", "low")

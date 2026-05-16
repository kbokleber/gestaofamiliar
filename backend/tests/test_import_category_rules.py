from types import SimpleNamespace

from app.utils.import_category_rules import match_import_category_rule


def _cat(cid, typ):
    return SimpleNamespace(id=cid, type=typ, is_active=True)


def test_rule_contains_normalized_mc_donalds():
    rules = [
        SimpleNamespace(
            id=1,
            pattern="mc don",
            entry_type="BOTH",
            category_id=10,
            is_active=True,
        )
    ]
    cats = {10: _cat(10, "EXPENSE")}
    cat, conf = match_import_category_rule(
        rules, cats, "MC DONALDS SHOPPING", "EXPENSE"
    )
    assert cat is not None and cat.id == 10
    assert conf == "high"


def test_rule_respects_entry_type():
    rules = [
        SimpleNamespace(
            id=1,
            pattern="pix",
            entry_type="INCOME",
            category_id=5,
            is_active=True,
        )
    ]
    cats = {5: _cat(5, "INCOME")}
    cat, _ = match_import_category_rule(rules, cats, "PIX recebido", "EXPENSE")
    assert cat is None


def test_first_rule_by_priority_order():
    rules = [
        SimpleNamespace(
            id=1,
            pattern="loja",
            entry_type="BOTH",
            category_id=1,
            is_active=True,
        ),
        SimpleNamespace(
            id=2,
            pattern="loja x",
            entry_type="BOTH",
            category_id=2,
            is_active=True,
        ),
    ]
    cats = {1: _cat(1, "EXPENSE"), 2: _cat(2, "EXPENSE")}
    cat, _ = match_import_category_rule(rules, cats, "compra loja x centro", "EXPENSE")
    assert cat.id == 1

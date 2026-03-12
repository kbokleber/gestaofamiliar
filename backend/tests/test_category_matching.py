from types import SimpleNamespace

from app.utils.category_matching import find_best_matching_category


def test_find_best_matching_category_ignores_accents_and_case():
    categories = [
        SimpleNamespace(id=1, name="Alimentação"),
        SimpleNamespace(id=2, name="Saúde"),
    ]

    category = find_best_matching_category(
        categories,
        category_name="alimentacao",
        description="Compra do mes",
    )

    assert category is categories[0]


def test_find_best_matching_category_matches_related_existing_name():
    categories = [
        SimpleNamespace(id=1, name="Supermercado"),
        SimpleNamespace(id=2, name="Farmácia"),
    ]

    category = find_best_matching_category(
        categories,
        category_name="Compra mercado",
        description="Recibo do supermercado bh",
    )

    assert category is categories[0]


def test_find_best_matching_category_returns_none_when_unrelated():
    categories = [
        SimpleNamespace(id=1, name="Moradia"),
        SimpleNamespace(id=2, name="Educação"),
    ]

    category = find_best_matching_category(
        categories,
        category_name="Veterinario",
        description="Consulta do cachorro",
    )

    assert category is None

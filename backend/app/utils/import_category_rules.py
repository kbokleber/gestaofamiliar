"""Match user-defined import rules (contains) before bank heuristics."""

from __future__ import annotations

from typing import Any, Iterable, Tuple

from app.utils.category_matching import normalize_category_text


def match_import_category_rule(
    rules: Iterable[Any],
    categories_by_id: dict[int, Any],
    description: str,
    entry_type: str,
) -> Tuple[Any | None, str | None]:
    """
    First matching rule wins (caller must sort rules by priority ASC, id ASC).
    Returns (category, 'high') or (None, None).
    """
    if entry_type not in ("INCOME", "EXPENSE"):
        return None, None

    norm_desc = normalize_category_text(description)
    if not norm_desc:
        return None, None

    for rule in rules:
        if not getattr(rule, "is_active", True):
            continue

        rule_et = getattr(rule, "entry_type", None)
        if rule_et not in ("INCOME", "EXPENSE", "BOTH"):
            continue
        if rule_et != "BOTH" and rule_et != entry_type:
            continue

        pattern = getattr(rule, "pattern", "") or ""
        norm_pat = normalize_category_text(pattern)
        if not norm_pat or norm_pat not in norm_desc:
            continue

        cat_id = getattr(rule, "category_id", None)
        cat = categories_by_id.get(cat_id) if cat_id is not None else None
        if cat is None or not getattr(cat, "is_active", True):
            continue
        if getattr(cat, "type", None) != entry_type:
            continue

        return cat, "high"

    return None, None

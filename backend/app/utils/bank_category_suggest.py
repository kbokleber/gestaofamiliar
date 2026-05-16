"""Suggest finance category for a bank statement line (description + INCOME/EXPENSE)."""

from __future__ import annotations

from typing import Any, Iterable

from app.utils.bank_category_keywords import keyword_category_name_bonus
from app.utils.category_matching import normalize_category_text, score_category_name_vs_description

# Slightly below receipt matcher so keyword boost can push borderline matches over the line
_MIN_SCORE = 0.72
_HIGH_CONFIDENCE = 0.86


def suggest_category_for_bank_line(
    description: str,
    entry_type: str,
    categories: Iterable[Any],
) -> tuple[Any | None, str | None]:
    """
    Returns (category_or_none, confidence) where confidence is 'high', 'low', or None.
    """
    desc = (description or "").strip()
    if not desc:
        return None, None

    cats = [
        c
        for c in categories
        if getattr(c, "type", None) == entry_type and getattr(c, "is_active", True)
    ]
    if not cats:
        return None, None

    best: Any | None = None
    best_score = 0.0

    for cat in cats:
        name = getattr(cat, "name", "") or ""
        base = score_category_name_vs_description(name, desc)
        norm_name = normalize_category_text(name)
        boosted = min(1.0, base + keyword_category_name_bonus(desc, norm_name))
        if boosted > best_score:
            best_score = boosted
            best = cat

    if best is None or best_score < _MIN_SCORE:
        return None, None

    conf = "high" if best_score >= _HIGH_CONFIDENCE else "low"
    return best, conf

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, Iterable


def normalize_category_text(value: str | None) -> str:
    if not value:
        return ""

    normalized = unicodedata.normalize("NFKD", value)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _tokenize(value: str) -> set[str]:
    return {token for token in normalize_category_text(value).split() if len(token) >= 3}


def _score_candidate(category_name: str, *, reference_name: str, description: str) -> float:
    candidate = normalize_category_text(category_name)
    if not candidate:
        return 0.0

    references = [normalize_category_text(reference_name), normalize_category_text(description)]
    best_score = 0.0

    for reference in references:
        if not reference:
            continue

        if candidate == reference:
            return 1.0

        if candidate in reference or reference in candidate:
            best_score = max(best_score, 0.92)

        candidate_tokens = _tokenize(candidate)
        reference_tokens = _tokenize(reference)
        if candidate_tokens and reference_tokens:
            overlap = len(candidate_tokens & reference_tokens) / max(len(candidate_tokens), len(reference_tokens))
            if overlap >= 0.5:
                best_score = max(best_score, 0.85 + min(overlap, 1.0) * 0.1)

        similarity = SequenceMatcher(None, candidate, reference).ratio()
        if similarity >= 0.72:
            best_score = max(best_score, similarity)

    return best_score


def find_best_matching_category(
    categories: Iterable[Any],
    *,
    category_name: str | None,
    description: str | None = None,
) -> Any | None:
    best_category = None
    best_score = 0.0

    for category in categories:
        score = _score_candidate(
            getattr(category, "name", ""),
            reference_name=category_name or "",
            description=description or "",
        )
        if score > best_score:
            best_category = category
            best_score = score

    return best_category if best_score >= 0.78 else None

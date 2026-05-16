"""
Heuristic keywords for Brazilian bank statement descriptions (Banco do Brasil and similar).
Used only to boost category matching; final pick still uses fuzzy name vs description.
"""

from __future__ import annotations

import re
from typing import Tuple

# (pattern on description, hints that should appear in normalized category name for a bonus)
_KEYWORD_RULES: list[Tuple[re.Pattern[str], tuple[str, ...]]] = [
    (
        re.compile(
            r"drogasil|drogaraia|pacheco|ultrafarma|panvel|farma|farmaci|remedio|drogaria",
            re.I,
        ),
        ("farm", "droga", "remed", "saude", "medic"),
    ),
    (
        re.compile(
            r"shell|ipiranga|petrobras|posto|combust|gasolina|etanol|diesel|raizen|vibra|ale",
            re.I,
        ),
        ("combust", "posto", "gasol", "veicul", "carro", "auto"),
    ),
    (
        re.compile(
            r"ifood|rappi|uber\s*eats|99food|zé\s*delivery|padaria|supermercado|carrefour|"
            r"atacadao|atacadão|pao\s*de|padoca|restaur|lanch|mcdon|burguer|bk\b|subway|"
            r"assai|extra|pao\s*de\s*acucar|pão\s*de\s*açúcar|big\s*lar|walmart",
            re.I,
        ),
        ("aliment", "mercad", "compras", "refeicao", "restaur", "lanche"),
    ),
    (
        re.compile(
            r"uber(?!\s*eats)|99\s*taxi|99pop|cabify|bolt|onibus|passagem|pedagio|pedágio|"
            r"estaciona|concessionaria|metro|trem",
            re.I,
        ),
        ("transport", "locomo", "viagem", "uber", "taxi", "veicul"),
    ),
    (
        re.compile(
            r"netflix|spotify|amazon\s*prime|disney|hbo|globoplay|youtube|apple\s*com|"
            r"google\s*play|steam|playstation|xbox|assinatura",
            re.I,
        ),
        ("lazer", "entreten", "assinat", "streaming", "divers"),
    ),
    (
        re.compile(
            r"energia|cemig|copel|light|enel|equatorial|água|agua|sabesp|sanepar|"
            r"condomin|aluguel|imobiliar|iptu",
            re.I,
        ),
        ("moradia", "casa", "aluguel", "condom", "luz", "agua", "energia"),
    ),
    (
        re.compile(
            r"escola|faculd|univers|curso|mensalidade|educacao|educação|senac|sesi|"
            r"anglo|wizard|kumon",
            re.I,
        ),
        ("educac", "escola", "curso", "estudo"),
    ),
    (
        re.compile(
            r"hospital|clinica|clínica|laboratorio|laboratório|unimed|amil|bradesco\s*saude|"
            r"plano\s*de\s*saude|dentista|ortodont",
            re.I,
        ),
        ("saude", "medic", "hospital", "clinic"),
    ),
    (
        re.compile(
            r"pix\s*enviad|ted\s*enviad|doc\s*enviad|transferencia\s*enviad|transferência\s*enviad|"
            r"pagamento\s*boleto|boleto",
            re.I,
        ),
        ("transfer", "pagamento", "despes", "geral"),
    ),
    (
        re.compile(
            r"pix\s*receb|ted\s*receb|doc\s*receb|transferencia\s*receb|transferência\s*receb|"
            r"deposito|depósito|salario|salário|holerite|fgts|rendimento|dividend",
            re.I,
        ),
        ("salari", "renda", "receb", "invest", "extra"),
    ),
]


def keyword_category_name_bonus(description: str, normalized_category_name: str) -> float:
    """Extra score when description matches a rule and category name aligns with hints (dominant signal for bank lines)."""
    if not description or not normalized_category_name:
        return 0.0
    for pattern, hints in _KEYWORD_RULES:
        if not pattern.search(description):
            continue
        for h in hints:
            if len(h) >= 3 and h in normalized_category_name:
                return 0.82
    return 0.0

from typing import Optional


def resolve_months_to_process(month: Optional[int]) -> list[int]:
    if month is None:
        return list(range(1, 13))

    if month < 1 or month > 12:
        raise ValueError("Mês inválido. Informe um valor entre 1 e 12.")

    return [month]

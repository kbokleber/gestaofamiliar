"""Menus que o aplicativo pode liberar por usuário."""
from typing import Optional

MENU_KEYS = ("dashboard", "saude", "manutencao", "financas", "estudos")


def normalize_menus(value: Optional[list[str]]) -> Optional[list[str]]:
    if value is None:
        return None
    unknown = [key for key in value if key not in MENU_KEYS]
    if unknown:
        names = ", ".join(unknown)
        raise ValueError(f"Menu desconhecido: {names}")
    return [key for key in MENU_KEYS if key in value]

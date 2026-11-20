"""Menus que o aplicativo pode liberar por usuário."""
from typing import Optional

MENU_KEYS = ("dashboard", "saude", "manutencao", "financas", "estudos", "localizacao", "compartilhar_localizacao")

# "compartilhar_localizacao": adulto (ex.: avô ou avó) que SÓ compartilha a própria posição pelo app,
# sem ver o mapa nem ninguém da família. Quem tem "localizacao" já pode compartilhar e ver.

# A criança não vê estes menus, mesmo que a lista salva os inclua.
MENUS_SO_ADULTO = frozenset({"localizacao", "compartilhar_localizacao"})


def normalize_menus(value: Optional[list[str]]) -> Optional[list[str]]:
    if value is None:
        return None
    unknown = [key for key in value if key not in MENU_KEYS]
    if unknown:
        names = ", ".join(unknown)
        raise ValueError(f"Menu desconhecido: {names}")
    return [key for key in MENU_KEYS if key in value]


def aplicar_perfil_menus(menus: Optional[list[str]], *, is_child: bool) -> Optional[list[str]]:
    """Tira da criança o menu que só o adulto acompanha."""
    if menus is None or not is_child:
        return menus
    return [key for key in menus if key not in MENUS_SO_ADULTO]

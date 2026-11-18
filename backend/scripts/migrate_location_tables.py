"""Cria as tabelas de localização da família, se ainda não existirem.

É o mesmo create_all que a API roda ao subir, restrito a estas tabelas.
Não apaga dados e não altera tabelas que já existem.

Não execute com o DATABASE_URL de produção sem o ok do Kleber.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import Base, engine
from app.models.location import (  # noqa: F401
    LocationDevice,
    LocationPairingCode,
    LocationPlace,
    LocationPlaceEvent,
    LocationPlaceState,
    LocationPoint,
)


TABELAS = [
    LocationPairingCode.__table__,
    LocationDevice.__table__,
    LocationPoint.__table__,
    LocationPlace.__table__,
    LocationPlaceState.__table__,
    LocationPlaceEvent.__table__,
]


def criar_tabelas_de_localizacao():
    print("[INICIO] Verificando tabelas de localização...")
    Base.metadata.create_all(bind=engine, tables=TABELAS)
    for tabela in TABELAS:
        print(f"[OK] {tabela.name}")
    print("[FIM] Tabelas de localização prontas.")


if __name__ == "__main__":
    criar_tabelas_de_localizacao()

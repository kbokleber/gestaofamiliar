"""O 500 só leva o texto do erro com ENVIRONMENT=development definido de propósito. App de verdade, em processo separado."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
SEGREDO = "Guilhermina-Segredo -23.987654"

PROGRAMA = r"""
import json, sys
from fastapi.testclient import TestClient
import app.main
from app.core.config import settings

@app.main.app.get("/explode")
def explode():
    raise ValueError(sys.argv[1])

r = TestClient(app.main.app, raise_server_exceptions=False).get("/explode")
print("SAIDA" + json.dumps([settings.ENVIRONMENT, r.status_code, r.json(), r.text, str(dict(r.headers))]))
"""


def _rodar(tmp_path, valor):
    ambiente = {k: v for k, v in os.environ.items() if k != "ENVIRONMENT" and "SENTRY" not in k}
    ambiente.update(DATABASE_URL="postgresql://u:p@localhost/db", SECRET_KEY="x", PYTHONPATH=str(BACKEND))
    if valor is not None:
        ambiente["ENVIRONMENT"] = valor
    r = subprocess.run([sys.executable, "-c", PROGRAMA, SEGREDO], cwd=tmp_path, env=ambiente,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-1500:]
    return json.loads(r.stdout.split("SAIDA", 1)[1].splitlines()[0])


@pytest.mark.parametrize("valor", [None, "production", "", "Development", "dev", "staging", " development"])
def test_500_nao_devolve_o_texto_do_erro(tmp_path, valor):
    ambiente, status, corpo, texto, cabecalhos = _rodar(tmp_path, valor)
    assert ambiente == ("production" if valor is None else valor)
    assert status == 500
    assert corpo["detail"] == "Erro interno do servidor."
    assert set(corpo) == {"detail", "type"}
    for parte in SEGREDO.split():
        assert parte not in texto + cabecalhos


def test_development_explicito_continua_mostrando_o_erro(tmp_path):
    ambiente, status, corpo, _, _ = _rodar(tmp_path, "development")
    assert (ambiente, status, corpo["detail"]) == ("development", 500, SEGREDO)


def test_compose_de_producao_repassa_o_ambiente_com_padrao_seguro():
    compose = BACKEND.parent / "docker-compose.external-db.yml"
    if not compose.exists():
        pytest.skip("fora do repositório completo")
    linhas = [linha.strip() for linha in compose.read_text(encoding="utf-8").splitlines()]
    assert linhas.count("ENVIRONMENT: ${ENVIRONMENT:-production}") == 1

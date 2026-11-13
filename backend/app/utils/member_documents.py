"""Anexos do membro: metadados para a edição e preservação do conteúdo no PUT."""
import json
from typing import Any, Optional


def _parse_documents(raw: Optional[str], strict: bool = False) -> Optional[list]:
    if raw is None:
        return None
    if isinstance(raw, str) and not raw.strip():
        return []
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        if strict:
            raise ValueError("documents não é um JSON válido")
        return None
    if not isinstance(parsed, list):
        if strict:
            raise ValueError("documents precisa ser uma lista JSON")
        return None
    return parsed


def documents_metadata(raw: Optional[str]) -> Optional[str]:
    """Lista JSON só com index, name, type e size. Sem o base64."""
    docs = _parse_documents(raw)
    if not docs:
        return None
    meta = []
    for index, doc in enumerate(docs):
        if not isinstance(doc, dict):
            continue
        size = doc.get("size") or 0
        try:
            size = int(size)
        except (TypeError, ValueError):
            size = 0
        meta.append({
            "index": index,
            "name": str(doc.get("name") or ""),
            "type": str(doc.get("type") or ""),
            "size": size,
        })
    if not meta:
        return None
    return json.dumps(meta, ensure_ascii=False)


def merge_member_documents(stored_json: Optional[str], incoming_json: Optional[str]) -> Optional[str]:
    """Monta a lista que será gravada.

    None ou lista vazia apaga os anexos.
    Item com data grava esse conteúdo.
    Item sem data e com index copia o arquivo já gravado nessa posição,
    sem exigir que o cliente reenvie o base64.
    """
    if incoming_json is None:
        return None
    incoming = _parse_documents(incoming_json, strict=True)
    if not incoming:
        return None
    stored = _parse_documents(stored_json) or []
    merged: list[dict[str, Any]] = []
    for item in incoming:
        if not isinstance(item, dict):
            raise ValueError("item de documents inválido")
        data = item.get("data")
        if isinstance(data, str) and data:
            merged.append({
                "name": str(item.get("name") or ""),
                "type": str(item.get("type") or ""),
                "size": item.get("size") or 0,
                "data": data,
            })
            continue
        if "index" not in item or item.get("index") is None:
            raise ValueError(
                "anexo sem conteúdo precisa do index para preservar o arquivo já gravado"
            )
        try:
            index = int(item["index"])
        except (TypeError, ValueError):
            raise ValueError("index de anexo inválido")
        if index < 0 or index >= len(stored):
            raise ValueError(f"anexo {index} não existe")
        original = stored[index]
        if not isinstance(original, dict) or not original.get("data"):
            raise ValueError(f"anexo {index} não tem conteúdo gravado")
        merged.append(original)
    return json.dumps(merged, ensure_ascii=False)

import base64
import io
import json
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

def get_document_response(documents_json: str, doc_index: int, item_name: str = "Item"):
    """
    Extrai um documento de uma string JSON (array de documentos base64) e retorna um StreamingResponse.
    """
    if not documents_json:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{item_name} não possui documentos."
        )
    
    try:
        documents = json.loads(documents_json)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao processar a lista de documentos."
        )
    
    if not isinstance(documents, list) or doc_index < 0 or doc_index >= len(documents):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anexo {doc_index} não encontrado."
        )
    
    doc = documents[doc_index]
    doc_name = doc.get("name", f"documento_{doc_index}")
    doc_type = doc.get("type", "application/octet-stream")
    doc_data = doc.get("data")
    
    if not doc_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conteúdo do anexo não encontrado."
        )
    
    try:
        # Decodificar base64
        file_bytes = base64.b64decode(doc_data)
        file_io = io.BytesIO(file_bytes)
        
        return StreamingResponse(
            file_io,
            media_type=doc_type,
            headers={
                "Content-Disposition": f'attachment; filename="{doc_name}"'
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao decodificar o arquivo: {str(e)}"
        )

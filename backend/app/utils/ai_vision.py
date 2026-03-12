import base64
import json
import logging
from typing import Optional, Dict, Any
from openai import OpenAI, AzureOpenAI
from sqlalchemy.orm import Session
from app.models.telegram import FamilyAIConfig

logger = logging.getLogger(__name__)

def get_ai_client(family_id: int, db: Session) -> Optional[tuple]:
    """Retorna (cliente, model) para a família usando FamilyAIConfig."""
    cfg = db.query(FamilyAIConfig).filter(FamilyAIConfig.family_id == family_id).first()
    if not cfg or not cfg.enabled or cfg.provider == "none":
        return None
    
    if cfg.provider == "azure":
        if not cfg.azure_endpoint or not cfg.azure_api_key:
            return None
        client = AzureOpenAI(
            azure_endpoint=cfg.azure_endpoint.rstrip("/"),
            api_key=cfg.azure_api_key,
            api_version="2024-02-15-preview",
        )
        model = cfg.azure_deployment or cfg.openai_model or "gpt-4o-mini"
        return (client, model)
    
    if cfg.provider == "openai" and cfg.openai_api_key:
        client = OpenAI(api_key=cfg.openai_api_key)
        model = cfg.openai_model or "gpt-4o-mini"
        return (client, model)
        
    return None

def analyze_receipt(image_bytes: bytes, family_id: int, db: Session) -> Optional[Dict[str, Any]]:
    """
    Usa a API de Visão para extrair dados de um comprovante.
    Retorna um dicionário com: description, amount, date, category_name.
    """
    client_and_model = get_ai_client(family_id, db)
    if not client_and_model:
        logger.warning(f"Família {family_id} não possui configuração de IA ativa para visão.")
        return None
    
    client, model = client_and_model
    
    # Codificar imagem em base64
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    prompt = """
    Analise esta imagem de um comprovante ou recibo financeiro e extraia as seguintes informações em formato JSON:
    - description: Uma descrição curta do que foi comprado ou pago.
    - amount: O valor total (apenas números, use ponto para decimais).
    - date: A data do comprovante no formato YYYY-MM-DD.
    - category_name: Uma sugestão de categoria (ex: Alimentação, Saúde, Transporte, Lazer, Moradia, etc).

    Retorne APENAS o JSON puro, sem markdown ou explicações.
    """
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=300
        )
        
        content = response.choices[0].message.content.strip()
        # Limpar possível markdown
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
            
        data = json.loads(content)
        return data
    except Exception as e:
        logger.exception("Erro ao analisar comprovante com IA")
        return None

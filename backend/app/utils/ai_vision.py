import base64
import json
import logging
from typing import Optional, Dict, Any
import pymupdf
from openai import OpenAI, AzureOpenAI
from sqlalchemy.orm import Session
from app.models.telegram import FamilyAIConfig

logger = logging.getLogger(__name__)
NVIDIA_NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"


def _is_nvidia_nim_config(cfg: FamilyAIConfig) -> bool:
    model = (cfg.openai_model or "").strip()
    return cfg.provider == "nvidia-nim" or model.startswith("nvidia-nim/")


def _get_nvidia_nim_model(cfg: FamilyAIConfig) -> str:
    model = (cfg.openai_model or "moonshotai/kimi-k2.5").strip()
    return model.replace("nvidia-nim/", "", 1)

def get_ai_client(family_id: int, db: Session) -> Optional[tuple]:
    """Retorna (cliente, model, provider) para a família usando FamilyAIConfig."""
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
        return (client, model, "azure")
    
    if _is_nvidia_nim_config(cfg) and cfg.openai_api_key:
        client = OpenAI(
            api_key=cfg.openai_api_key,
            base_url=NVIDIA_NIM_BASE_URL,
        )
        model = _get_nvidia_nim_model(cfg)
        return (client, model, "nvidia-nim")

    if cfg.provider == "openai" and cfg.openai_api_key:
        client = OpenAI(api_key=cfg.openai_api_key)
        model = cfg.openai_model or "gpt-4o-mini"
        return (client, model, "openai")
        
    return None

def _prepare_visual_input(file_bytes: bytes, mime_type: Optional[str]) -> tuple[str, bytes]:
    if mime_type == "application/pdf":
        pdf = pymupdf.open(stream=file_bytes, filetype="pdf")
        if pdf.page_count == 0:
            raise ValueError("PDF sem páginas.")

        page = pdf.load_page(0)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
        return "image/png", pix.tobytes("png")

    return mime_type or "image/jpeg", file_bytes


def analyze_receipt(file_bytes: bytes, family_id: int, db: Session, mime_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Usa a API de Visão para extrair dados de um comprovante.
    Retorna um dicionário com: description, amount, date, category_name e dados de parcelamento.
    """
    client_and_model = get_ai_client(family_id, db)
    if not client_and_model:
        logger.warning(f"Família {family_id} não possui configuração de IA ativa para visão.")
        return None
    
    client, model, provider = client_and_model
    
    visual_mime_type, visual_bytes = _prepare_visual_input(file_bytes, mime_type)
    base64_image = base64.b64encode(visual_bytes).decode('utf-8')
    
    prompt = """
    Analise este comprovante ou recibo financeiro e extraia as seguintes informações no formato JSON:
    - description: O nome do estabelecimento comercial (ex: "Supermercado Zaffari", "Posto Ipiranga", "Farmácia São João"). Use nomes genéricos (ex: "Alimentação", "Compras") apenas se for totalmente impossível identificar o nome do local.
    - amount: O valor total da compra/recibo (apenas números, use ponto para decimais).
    - date: A data EXATA da compra/transação/emissão no formato YYYY-MM-DD.
    - category_name: Uma sugestão de categoria (ex: Alimentação, Saúde, Transporte, Lazer, Moradia, etc).
    - current_installment: Número da parcela atual, se estiver parcelado. Se não estiver parcelado, retorne 1.
    - total_installments: Total de parcelas, se estiver parcelado. Se não estiver parcelado, retorne 1.

    Regras para a data:
    - Priorize a data verdadeira em que a compra/transação aconteceu. Cuidado com datas antigas (como de fundação da empresa ou CNPJ).
    - Se houver mais de uma data, escolha a data de emissão do cupom fiscal.
    - Não use data de vencimento, fechamento de fatura, data prevista ou data de upload.
    - Se não existir data de compra/transação legível, retorne null.

    Retorne APENAS o JSON puro, sem blocos markdown (```) e sem explicações no texto.
    """
    
    try:
        request_kwargs = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{visual_mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 800,
        }
        if provider == "nvidia-nim":
            request_kwargs["extra_body"] = {"chat_template_kwargs": {"thinking": False}}

        response = client.chat.completions.create(
            **request_kwargs
        )
        
        content = (response.choices[0].message.content or "").strip()
        if not content:
            logger.warning("Resposta vazia ao analisar comprovante com provider=%s e model=%s", provider, model)
            return None
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

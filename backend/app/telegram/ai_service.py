"""
Serviço de IA para o bot Telegram.
Interpreta mensagens do usuário e chama as ferramentas do backend (equipamentos, dashboard, saúde).
Usa a configuração de IA da família (FamilyAIConfig): cada família cola sua API key OpenAI ou Azure.
"""
import json
import logging
from typing import Any, Optional

from sqlalchemy.orm import Session
from openai import OpenAI, AzureOpenAI

from app.models.user import User
from app.models.telegram import FamilyAIConfig
from app.models.healthcare import FamilyMember, MedicalAppointment, Medication
from app.models.maintenance import Equipment, MaintenanceOrder
from app.api.deps import get_user_family_ids
from sqlalchemy import func
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# --- Definição das ferramentas (tools) para o LLM ---
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_dashboard_stats",
            "description": "Retorna resumo do dashboard: total de membros, consultas futuras, equipamentos, medicações ativas, ordens de manutenção.",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_equipment",
            "description": "Lista equipamentos da família. Pode filtrar por tipo (eletronico, eletrodomestico, movel, veiculo, outro) ou status (OPERACIONAL, EM_MANUTENCAO, FORA_DE_USO, RESERVA).",
            "parameters": {
                "type": "object",
                "properties": {
                    "type_filter": {"type": "string", "description": "Filtrar por tipo do equipamento"},
                    "status_filter": {"type": "string", "description": "Filtrar por status"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_family_members",
            "description": "Lista os membros da família com nome e data de nascimento (útil para aniversários).",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_upcoming_appointments",
            "description": "Lista as próximas consultas médicas da família (data, membro, médico, especialidade).",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Máximo de consultas a retornar", "default": 10},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_active_medications",
            "description": "Lista medicações em uso pelos membros da família (nome do membro, medicamento, dosagem).",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_maintenance_orders",
            "description": "Lista ordens de manutenção (equipamento, status, descrição).",
            "parameters": {
                "type": "object",
                "properties": {
                    "status_filter": {"type": "string", "description": "Filtrar por status da ordem"},
                },
            },
        },
    },
]

SYSTEM_PROMPT = """Você é um assistente do sistema de Gestão Familiar, acessível pelo Telegram.
O usuário pode pedir informações sobre a família dele: equipamentos, consultas médicas, medicações, membros, resumo do dashboard, etc.
Use as ferramentas disponíveis para buscar dados reais e responda em português, de forma clara e objetiva.
Se não tiver ferramenta para o pedido, diga que no momento só pode ajudar com: resumo do dashboard, lista de equipamentos, membros da família, próximas consultas, medicações em uso e ordens de manutenção.
Seja breve nas respostas para caber bem no Telegram."""


def _get_family_id(user: User, db: Session) -> Optional[int]:
    if user.family_id:
        return user.family_id
    ids = get_user_family_ids(user, db)
    return ids[0] if ids else None


def _execute_tool(name: str, arguments: dict, db: Session, user: User) -> str:
    """Executa uma ferramenta e retorna o resultado em texto para o LLM."""
    family_id = _get_family_id(user, db)
    if not family_id:
        return "Erro: usuário não está associado a nenhuma família."

    now = datetime.now(timezone.utc)

    try:
        if name == "get_dashboard_stats":
            total_members = db.query(func.count(FamilyMember.id)).filter(FamilyMember.family_id == family_id).scalar() or 0
            total_appointments = db.query(func.count(MedicalAppointment.id)).join(
                FamilyMember, MedicalAppointment.family_member_id == FamilyMember.id
            ).filter(
                FamilyMember.family_id == family_id,
                MedicalAppointment.appointment_date >= now
            ).scalar() or 0
            total_equipment = db.query(func.count(Equipment.id)).filter(Equipment.family_id == family_id).scalar() or 0
            active_medications = db.query(func.count(Medication.id)).join(
                FamilyMember, Medication.family_member_id == FamilyMember.id
            ).filter(
                FamilyMember.family_id == family_id,
                (Medication.end_date == None) | (Medication.end_date >= now.date())
            ).scalar() or 0
            total_orders = db.query(func.count(MaintenanceOrder.id)).join(
                Equipment, MaintenanceOrder.equipment_id == Equipment.id
            ).filter(Equipment.family_id == family_id).scalar() or 0
            return json.dumps({
                "total_members": total_members,
                "total_appointments": total_appointments,
                "total_equipment": total_equipment,
                "active_medications": active_medications,
                "total_orders": total_orders,
            }, ensure_ascii=False)

        if name == "list_equipment":
            q = db.query(Equipment).filter(Equipment.family_id == family_id)
            if arguments.get("type_filter"):
                q = q.filter(Equipment.type == arguments["type_filter"])
            if arguments.get("status_filter"):
                q = q.filter(Equipment.status == arguments["status_filter"])
            items = q.order_by(Equipment.created_at.desc()).limit(50).all()
            list_data = [
                {"name": e.name, "type": e.type, "status": e.status, "brand": e.brand, "model": e.model}
                for e in items
            ]
            return json.dumps(list_data, ensure_ascii=False)

        if name == "list_family_members":
            members = db.query(FamilyMember).filter(
                FamilyMember.family_id == family_id
            ).order_by(FamilyMember.order, FamilyMember.name).all()
            list_data = [
                {"name": m.name, "birth_date": str(m.birth_date), "relationship_type": m.relationship_type}
                for m in members
            ]
            return json.dumps(list_data, ensure_ascii=False)

        if name == "list_upcoming_appointments":
            limit = arguments.get("limit") or 10
            appointments = (
                db.query(MedicalAppointment, FamilyMember.name)
                .join(FamilyMember, MedicalAppointment.family_member_id == FamilyMember.id)
                .filter(
                    FamilyMember.family_id == family_id,
                    MedicalAppointment.appointment_date >= now
                )
                .order_by(MedicalAppointment.appointment_date)
                .limit(limit)
                .all()
            )
            list_data = [
                {
                    "member": name,
                    "date": str(apt.appointment_date),
                    "doctor": apt.doctor_name,
                    "specialty": apt.specialty,
                }
                for apt, name in appointments
            ]
            return json.dumps(list_data, ensure_ascii=False)

        if name == "list_active_medications":
            meds = (
                db.query(Medication, FamilyMember.name)
                .join(FamilyMember, Medication.family_member_id == FamilyMember.id)
                .filter(
                    FamilyMember.family_id == family_id,
                    (Medication.end_date == None) | (Medication.end_date >= now.date())
                )
                .all()
            )
            list_data = [
                {"member": name, "medication": m.name, "dosage": m.dosage or ""}
                for m, name in meds
            ]
            return json.dumps(list_data, ensure_ascii=False)

        if name == "list_maintenance_orders":
            q = (
                db.query(MaintenanceOrder, Equipment.name)
                .join(Equipment, MaintenanceOrder.equipment_id == Equipment.id)
                .filter(Equipment.family_id == family_id)
            )
            if arguments.get("status_filter"):
                q = q.filter(MaintenanceOrder.status == arguments["status_filter"])
            orders = q.order_by(MaintenanceOrder.created_at.desc()).limit(30).all()
            list_data = [
                {"equipment": eq_name, "status": o.status, "description": o.description or ""}
                for o, eq_name in orders
            ]
            return json.dumps(list_data, ensure_ascii=False)

        return json.dumps({"error": f"Ferramenta desconhecida: {name}"})
    except Exception as e:
        logger.exception("Erro ao executar tool %s", name)
        return json.dumps({"error": str(e)})


def _get_openai_client(family_id: Optional[int], db: Session) -> Optional[tuple[OpenAI | AzureOpenAI, str]]:
    """
    Retorna (cliente, model) para a família. Usa FamilyAIConfig.
    """
    if not family_id:
        return None
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


def process_message_with_ai(message: str, user: User, db: Session) -> str:
    """
    Processa a mensagem do usuário com IA: chama o LLM com as ferramentas,
    executa as chamadas solicitadas e retorna a resposta final em texto.
    Usa a config de IA da família (FamilyAIConfig).
    """
    family_id = _get_family_id(user, db)
    client_and_model = _get_openai_client(family_id, db)
    if not client_and_model:
        return _fallback_response()

    client, model = client_and_model

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": message},
    ]

    max_rounds = 5
    for _ in range(max_rounds):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
        except Exception as e:
            logger.exception("Erro ao chamar LLM")
            return f"Erro ao processar com IA: {str(e)[:200]}"

        choice = response.choices[0]
        if not choice.message.tool_calls:
            text = (choice.message.content or "").strip()
            return text or _fallback_response()

        messages.append(choice.message)

        for tc in choice.message.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            result = _execute_tool(name, args, db, user)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    return "Limite de etapas atingido. Tente um pedido mais simples."


def _fallback_response() -> str:
    return (
        "Use /ajuda para ver os comandos disponíveis. "
        "Para respostas com IA, um admin pode configurar a API (OpenAI ou Azure) em Administração > Famílias > Editar família."
    )

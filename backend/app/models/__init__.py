from app.models.user import User, Profile
from app.models.dashboard import DashboardPreference
from app.models.family import Family
from app.models.user_family import user_families
from app.models.healthcare import FamilyMember, MedicalAppointment, MedicalProcedure, Medication
from app.models.maintenance import Equipment, EquipmentAttachment, MaintenanceOrder, MaintenanceImage
from app.models.telegram import (
    FamilyTelegramConfig,
    FamilyAIConfig,
    TelegramUserLink,
    TelegramLinkCode,
)
from app.models.estudo import Apontamento, ApontamentoLido, Atividade, ComunicadoLido
from app.models.whatsapp import FamilyWhatsAppConfig
from app.models.app_android import AppAndroid, AppDispositivoAdulto, AppPublicacaoToken
from app.models.lembrete import AvisoApp, FamilyLembreteConfig, PushInscricao
from app.models.prova import (
    Avaliacao,
    AvaliacaoHistorico,
    AvaliacaoItem,
    AvaliacaoOcorrencia,
    Boletim,
    BoletimLinha,
    Cronograma,
    CronogramaAluno,
    EventoEscolar,
    NotaParcial,
)
from app.models.finance import (
    FinanceCategory,
    FinanceEntry,
    FinanceImportCategoryRule,
    FinanceRecurrence,
)
from app.models.location import (
    LocationChildSettings,
    LocationDevice,
    LocationPairingCode,
    LocationPlace,
    LocationPlaceEvent,
    LocationPlaceState,
    LocationPoint,
    LocationSos,
    LocationSosDestinatario,
)

__all__ = [
    "User",
    "Profile",
    "DashboardPreference",
    "Family",
    "user_families",
    "FamilyMember",
    "MedicalAppointment",
    "MedicalProcedure",
    "Medication",
    "Equipment",
    "EquipmentAttachment",
    "MaintenanceOrder",
    "MaintenanceImage",
    "FamilyTelegramConfig",
    "FamilyAIConfig",
    "TelegramUserLink",
    "TelegramLinkCode",
    "FinanceCategory",
    "FinanceEntry",
    "FinanceRecurrence",
    "FinanceImportCategoryRule",
    "Atividade",
    "Apontamento",
    "ApontamentoLido",
    "ComunicadoLido",
    "FamilyWhatsAppConfig",
    "FamilyLembreteConfig",
    "PushInscricao",
    "Cronograma",
    "CronogramaAluno",
    "Avaliacao",
    "AvaliacaoOcorrencia",
    "AvaliacaoItem",
    "EventoEscolar",
    "AvaliacaoHistorico",
    "Boletim",
    "BoletimLinha",
    "NotaParcial",
    "LocationPairingCode",
    "LocationDevice",
    "LocationPoint",
    "LocationPlace",
    "LocationPlaceState",
    "LocationPlaceEvent",
    "LocationChildSettings",
    "AvisoApp",
    "AppAndroid",
    "AppPublicacaoToken",
    "AppDispositivoAdulto",
]

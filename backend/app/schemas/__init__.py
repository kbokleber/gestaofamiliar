from app.schemas.user import (
    User, UserCreate, UserUpdate, UserWithProfile,
    Profile, ProfileCreate, ProfileUpdate
)
from app.schemas.token import Token, TokenPayload
from app.schemas.dashboard import (
    DashboardPreference, DashboardPreferenceCreate, DashboardPreferenceUpdate
)
from app.schemas.healthcare import (
    FamilyMember, FamilyMemberCreate, FamilyMemberUpdate, FamilyMemberDetail,
    MedicalAppointment, MedicalAppointmentCreate, MedicalAppointmentUpdate,
    MedicalProcedure, MedicalProcedureCreate, MedicalProcedureUpdate,
    Medication, MedicationCreate, MedicationUpdate
)
from app.schemas.maintenance import (
    Equipment, EquipmentCreate, EquipmentUpdate, EquipmentDetail,
    EquipmentAttachment, EquipmentAttachmentCreate,
    MaintenanceOrder, MaintenanceOrderCreate, MaintenanceOrderUpdate, MaintenanceOrderDetail,
    MaintenanceImage, MaintenanceImageCreate
)

__all__ = [
    # User & Profile
    "User", "UserCreate", "UserUpdate", "UserWithProfile",
    "Profile", "ProfileCreate", "ProfileUpdate",
    # Token
    "Token", "TokenPayload",
    # Dashboard
    "DashboardPreference", "DashboardPreferenceCreate", "DashboardPreferenceUpdate",
    # Healthcare
    "FamilyMember", "FamilyMemberCreate", "FamilyMemberUpdate", "FamilyMemberDetail",
    "MedicalAppointment", "MedicalAppointmentCreate", "MedicalAppointmentUpdate",
    "MedicalProcedure", "MedicalProcedureCreate", "MedicalProcedureUpdate",
    "Medication", "MedicationCreate", "MedicationUpdate",
    # Maintenance
    "Equipment", "EquipmentCreate", "EquipmentUpdate", "EquipmentDetail",
    "EquipmentAttachment", "EquipmentAttachmentCreate",
    "MaintenanceOrder", "MaintenanceOrderCreate", "MaintenanceOrderUpdate", "MaintenanceOrderDetail",
    "MaintenanceImage", "MaintenanceImageCreate",
]

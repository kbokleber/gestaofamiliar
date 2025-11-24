from pydantic import BaseModel, field_serializer, field_validator
from typing import Optional, List, Any
from datetime import date, datetime
import base64

# FamilyMember Schemas
class FamilyMemberBase(BaseModel):
    name: str
    birth_date: date
    gender: Optional[str] = None
    relationship_type: Optional[str] = None
    blood_type: str = ""
    allergies: str = ""
    chronic_conditions: str = ""
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    notes: str = ""
    order: int = 0

class FamilyMemberCreate(FamilyMemberBase):
    photo: Optional[str] = None  # Base64 string da foto

class FamilyMemberUpdate(BaseModel):
    name: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    relationship_type: Optional[str] = None
    blood_type: Optional[str] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    notes: Optional[str] = None
    order: Optional[int] = None
    photo: Optional[str] = None

class FamilyMember(FamilyMemberBase):
    id: int
    photo: Optional[Any] = None
    created_at: datetime
    updated_at: datetime
    
    @field_serializer('photo')
    def serialize_photo(self, photo: Any, _info) -> Optional[str]:
        """Converter photo de bytes para base64 string ou retornar None"""
        if photo is None:
            return None
        if isinstance(photo, bytes):
            return base64.b64encode(photo).decode('utf-8')
        if isinstance(photo, memoryview):
            return base64.b64encode(bytes(photo)).decode('utf-8')
        return str(photo) if photo else None
    
    class Config:
        from_attributes = True

# MedicalAppointment Schemas
class MedicalAppointmentBase(BaseModel):
    doctor_name: str
    specialty: str
    appointment_date: datetime
    location: str = ""
    reason: str
    diagnosis: str = ""
    prescription: str = ""
    next_appointment: Optional[datetime] = None
    notes: str = ""
    documents: Optional[str] = None  # JSON string com array de documentos

class MedicalAppointmentCreate(MedicalAppointmentBase):
    family_member_id: int

class MedicalAppointmentUpdate(BaseModel):
    doctor_name: Optional[str] = None
    specialty: Optional[str] = None
    appointment_date: Optional[datetime] = None
    location: Optional[str] = None
    reason: Optional[str] = None
    diagnosis: Optional[str] = None
    prescription: Optional[str] = None
    next_appointment: Optional[datetime] = None
    notes: Optional[str] = None
    documents: Optional[str] = None

class MedicalAppointment(MedicalAppointmentBase):
    id: int
    family_member_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# MedicalProcedure Schemas
class MedicalProcedureBase(BaseModel):
    procedure_name: str
    procedure_date: datetime
    doctor_name: str
    location: str
    description: str
    results: str = ""
    follow_up_notes: str = ""
    next_procedure_date: Optional[datetime] = None
    documents: Optional[str] = None  # JSON string com array de documentos

class MedicalProcedureCreate(MedicalProcedureBase):
    family_member_id: int

class MedicalProcedureUpdate(BaseModel):
    procedure_name: Optional[str] = None
    procedure_date: Optional[datetime] = None
    doctor_name: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    results: Optional[str] = None
    follow_up_notes: Optional[str] = None
    next_procedure_date: Optional[datetime] = None
    documents: Optional[str] = None

class MedicalProcedure(MedicalProcedureBase):
    id: int
    family_member_id: int
    documents: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Medication Schemas
class MedicationBase(BaseModel):
    name: str
    dosage: str
    frequency: str
    start_date: date
    end_date: Optional[date] = None
    prescribed_by: str = ""
    prescription_number: str = ""
    instructions: str = ""
    side_effects: str = ""
    notes: str = ""
    documents: Optional[str] = None  # JSON string com array de documentos

class MedicationCreate(MedicationBase):
    family_member_id: int

class MedicationUpdate(BaseModel):
    name: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    prescribed_by: Optional[str] = None
    prescription_number: Optional[str] = None
    instructions: Optional[str] = None
    side_effects: Optional[str] = None
    notes: Optional[str] = None
    documents: Optional[str] = None

class Medication(MedicationBase):
    id: int
    family_member_id: int
    documents: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    @field_validator('start_date', 'end_date', mode='before')
    @classmethod
    def convert_datetime_to_date(cls, v):
        """Converter datetime para date se necessário"""
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.date()
        return v
    
    class Config:
        from_attributes = True

# Schema para reordenação
class FamilyMemberOrderItem(BaseModel):
    id: int
    order: int

class FamilyMemberReorder(BaseModel):
    items: List[FamilyMemberOrderItem]

# Schemas com relacionamentos
class FamilyMemberDetail(FamilyMember):
    appointments: List[MedicalAppointment] = []
    procedures: List[MedicalProcedure] = []
    medications: List[Medication] = []


from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

# Equipment Schemas
class EquipmentBase(BaseModel):
    name: str
    type: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    purchase_date: Optional[date] = None
    warranty_expiry: Optional[date] = None
    service_provider: str = ""  # Empresa Prestadora do Serviço
    status: str = "OPERACIONAL"
    notes: str = ""
    documents: Optional[str] = None  # JSON string com array de documentos
    has_documents: Optional[bool] = None  # Indica se existem documentos (para listagem)

class EquipmentCreate(EquipmentBase):
    owner_id: Optional[int] = None

class EquipmentUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    purchase_date: Optional[date] = None
    warranty_expiry: Optional[date] = None
    service_provider: Optional[str] = None
    status: Optional[str] = None
    owner_id: Optional[int] = None
    notes: Optional[str] = None
    documents: Optional[str] = None
    has_documents: Optional[bool] = None

class Equipment(EquipmentBase):
    id: int
    owner_id: Optional[int] = None
    documents: Optional[str] = None
    has_documents: Optional[bool] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# EquipmentAttachment Schemas
class EquipmentAttachmentBase(BaseModel):
    description: str = ""

class EquipmentAttachmentCreate(EquipmentAttachmentBase):
    equipment_id: int
    file: str

class EquipmentAttachment(EquipmentAttachmentBase):
    id: int
    equipment_id: int
    file: str
    uploaded_at: datetime
    uploaded_by_id: Optional[int] = None
    
    class Config:
        from_attributes = True

# MaintenanceOrder Schemas
class MaintenanceOrderBase(BaseModel):
    title: str
    description: str
    status: str = "PENDENTE"
    priority: str = "MEDIA"
    service_provider: str = ""
    completion_date: Optional[date] = None
    cost: Optional[Decimal] = None
    warranty_expiration: Optional[date] = None
    warranty_terms: str = ""
    invoice_number: str = ""
    notes: str = ""

class MaintenanceOrderCreate(MaintenanceOrderBase):
    equipment_id: int
    documents: Optional[str] = None  # JSON string com array de documentos
    has_documents: Optional[bool] = None

class MaintenanceOrderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    service_provider: Optional[str] = None
    completion_date: Optional[date] = None
    cost: Optional[Decimal] = None
    warranty_expiration: Optional[date] = None
    warranty_terms: Optional[str] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = None
    documents: Optional[str] = None  # JSON string com array de documentos
    has_documents: Optional[bool] = None

class MaintenanceOrder(MaintenanceOrderBase):
    id: int
    equipment_id: int
    equipment_name: Optional[str] = None  # Nome do equipamento (preenchido na listagem para evitar N+1 e "Desconhecido")
    invoice_file: Optional[str] = None
    documents: Optional[str] = None  # JSON string com array de documentos
    has_documents: Optional[bool] = None
    created_by_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# MaintenanceImage Schemas
class MaintenanceImageBase(BaseModel):
    description: str = ""

class MaintenanceImageCreate(MaintenanceImageBase):
    order_id: int
    image: str

class MaintenanceImage(MaintenanceImageBase):
    id: int
    order_id: int
    image: str
    uploaded_at: datetime
    
    class Config:
        from_attributes = True

# Schemas com relacionamentos
class EquipmentDetail(Equipment):
    maintenance_orders: List[MaintenanceOrder] = []
    attachments: List[EquipmentAttachment] = []

class MaintenanceOrderDetail(MaintenanceOrder):
    # Manter compatibilidade com frontend que pode esperar images
    images: List[MaintenanceImage] = []


from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class Equipment(Base):
    """
    Equipamento
    App: maintenance
    """
    __tablename__ = "maintenance_equipment"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=True)  # eletronico, eletrodomestico, movel, veiculo, outro
    brand = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=True)
    purchase_date = Column(Date, nullable=True)
    warranty_expiry = Column(Date, nullable=True)
    service_provider = Column(String(200), nullable=False, default='')  # Empresa Prestadora do Serviço
    status = Column(String(20), nullable=False, default='OPERACIONAL')  # OPERACIONAL, EM_MANUTENCAO, FORA_DE_USO, RESERVA
    owner_id = Column(Integer, ForeignKey("auth_user.id"), nullable=True)
    family_id = Column(Integer, ForeignKey("families_family.id"), nullable=False, index=True)
    notes = Column(Text, nullable=False, default='')
    documents = Column(Text, nullable=True)  # JSON com array de documentos em base64
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relacionamentos
    family = relationship("Family", back_populates="equipment")
    owner = relationship("User", back_populates="equipments_owned")
    maintenance_orders = relationship("MaintenanceOrder", back_populates="equipment", cascade="all, delete-orphan")
    attachments = relationship("EquipmentAttachment", back_populates="equipment", cascade="all, delete-orphan")

class EquipmentAttachment(Base):
    """
    Anexo do Equipamento (documentos, fotos, etc)
    App: maintenance
    """
    __tablename__ = "maintenance_equipmentattachment"
    
    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("maintenance_equipment.id"), nullable=False)
    file = Column(String(100), nullable=False)  # FileField do Django armazena o caminho
    description = Column(String(255), nullable=False, default='')
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    uploaded_by_id = Column(Integer, ForeignKey("auth_user.id"), nullable=True)
    
    # Relacionamentos
    equipment = relationship("Equipment", back_populates="attachments")
    uploaded_by = relationship("User", back_populates="uploaded_attachments")

class MaintenanceOrder(Base):
    """
    Ordem de Manutenção
    App: maintenance
    """
    __tablename__ = "maintenance_maintenanceorder"
    
    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("maintenance_equipment.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default='PENDENTE')  # PENDENTE, EM_ANDAMENTO, CONCLUIDA, CANCELADA
    priority = Column(String(20), nullable=False, default='MEDIA')  # BAIXA, MEDIA, ALTA, URGENTE
    service_provider = Column(String(200), nullable=False, default='')
    completion_date = Column(Date, nullable=True)
    cost = Column(Numeric(10, 2), nullable=True)
    warranty_expiration = Column(Date, nullable=True)
    warranty_terms = Column(Text, nullable=False, default='')
    invoice_number = Column(String(50), nullable=False, default='')
    invoice_file = Column(String(100), nullable=True)  # FileField do Django
    notes = Column(Text, nullable=False, default='')
    documents = Column(Text, nullable=True)  # JSON com array de documentos em base64 (igual às outras telas)
    created_by_id = Column(Integer, ForeignKey("auth_user.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=False)
    
    # Relacionamentos
    equipment = relationship("Equipment", back_populates="maintenance_orders")
    created_by = relationship("User", back_populates="maintenance_orders")
    images = relationship("MaintenanceImage", back_populates="order", cascade="all, delete-orphan")

class MaintenanceImage(Base):
    """
    Imagem da Manutenção
    App: maintenance
    """
    __tablename__ = "maintenance_maintenanceimage"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("maintenance_maintenanceorder.id"), nullable=False)
    image = Column(Text, nullable=False)  # Armazena base64 completo (pode ser muito grande)
    description = Column(String(200), nullable=False, default='')
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relacionamento
    order = relationship("MaintenanceOrder", back_populates="images")


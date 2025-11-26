from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class FamilyMember(Base):
    """
    Membro da Família
    App: healthcare
    NOTA: No banco real não existe user_id, os membros são compartilhados
    """
    __tablename__ = "healthcare_familymember"
    
    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    photo = Column(Text, nullable=True)  # Armazena imagem em base64
    birth_date = Column(Date, nullable=False)
    gender = Column(String(1), nullable=True)  # M, F, O
    relationship_type = Column("relationship", String(50), nullable=True)
    blood_type = Column(String(5), nullable=False, default='')
    allergies = Column(Text, nullable=False, default='')
    chronic_conditions = Column(Text, nullable=False, default='')
    emergency_contact = Column(String(100), nullable=True)
    emergency_phone = Column(String(20), nullable=True)
    notes = Column(Text, nullable=False, default='')
    order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relacionamentos
    family = relationship("Family", back_populates="family_members")
    appointments = relationship("MedicalAppointment", back_populates="family_member", cascade="all, delete-orphan")
    procedures = relationship("MedicalProcedure", back_populates="family_member", cascade="all, delete-orphan")
    medications = relationship("Medication", back_populates="family_member", cascade="all, delete-orphan")

class MedicalAppointment(Base):
    """
    Consulta Médica
    App: healthcare
    """
    __tablename__ = "healthcare_medicalappointment"
    
    id = Column(Integer, primary_key=True, index=True)
    family_member_id = Column(Integer, ForeignKey("healthcare_familymember.id"), nullable=False)
    doctor_name = Column(String(100), nullable=False)
    specialty = Column(String(100), nullable=False)
    appointment_date = Column(DateTime(timezone=True), nullable=False)
    location = Column(String(200), nullable=False, default='')
    reason = Column(Text, nullable=False)
    diagnosis = Column(Text, nullable=False, default='')
    prescription = Column(Text, nullable=False, default='')
    next_appointment = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=False, default='')
    documents = Column(Text, nullable=True)  # JSON com array de documentos em base64
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relacionamento
    family_member = relationship("FamilyMember", back_populates="appointments")

class MedicalProcedure(Base):
    """
    Procedimento Médico
    App: healthcare
    """
    __tablename__ = "healthcare_medicalprocedure"
    
    id = Column(Integer, primary_key=True, index=True)
    family_member_id = Column(Integer, ForeignKey("healthcare_familymember.id"), nullable=False)
    procedure_name = Column(String(200), nullable=False)
    procedure_date = Column(DateTime(timezone=True), nullable=False)
    doctor_name = Column(String(100), nullable=False)
    location = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    results = Column(Text, nullable=False, default='')
    follow_up_notes = Column(Text, nullable=False, default='')
    next_procedure_date = Column(DateTime(timezone=True), nullable=True)
    documents = Column(Text, nullable=True)  # JSON com array de documentos em base64
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relacionamento
    family_member = relationship("FamilyMember", back_populates="procedures")

class Medication(Base):
    """
    Medicamento
    App: healthcare
    """
    __tablename__ = "healthcare_medication"
    
    id = Column(Integer, primary_key=True, index=True)
    family_member_id = Column(Integer, ForeignKey("healthcare_familymember.id"), nullable=False)
    name = Column(String(100), nullable=False)
    dosage = Column(String(50), nullable=False)
    frequency = Column(String(20), nullable=False)  # once, twice, three_times, etc.
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    prescribed_by = Column(String(100), nullable=False, default='')
    prescription_number = Column(String(50), nullable=False, default='')
    instructions = Column(Text, nullable=False, default='')
    side_effects = Column(Text, nullable=False, default='')
    notes = Column(Text, nullable=False, default='')
    documents = Column(Text, nullable=True)  # JSON com array de documentos em base64
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relacionamento
    family_member = relationship("FamilyMember", back_populates="medications")


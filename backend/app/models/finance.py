from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, Numeric, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class FinanceCategory(Base):
    """
    Categoria Financeira (ex: Alimentação, Aluguel, Salário)
    App: finance
    """
    __tablename__ = "finance_category"
    
    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    icon = Column(String(50), nullable=True)  # Nome do ícone Lucide
    color = Column(String(20), nullable=True) # Hex color
    type = Column(String(10), nullable=False) # 'INCOME' ou 'EXPENSE'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relacionamentos
    family = relationship("Family", back_populates="finance_categories")
    entries = relationship("FinanceEntry", back_populates="category")
    recurrences = relationship("FinanceRecurrence", back_populates="category")

class FinanceEntry(Base):
    """
    Lançamento Financeiro (Receita ou Despesa)
    App: finance
    """
    __tablename__ = "finance_entry"
    
    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("finance_category.id"), nullable=True)
    description = Column(String(200), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    date = Column(Date, nullable=False)
    type = Column(String(10), nullable=False) # 'INCOME' ou 'EXPENSE'
    payment_method = Column(String(50), nullable=True)
    is_paid = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    documents = Column(Text, nullable=True) # JSON com array de documentos base64
    
    # Se originado por uma recorrência
    recurrence_id = Column(Integer, ForeignKey("finance_recurrence.id"), nullable=True)
    
    created_by_id = Column(Integer, ForeignKey("auth_user.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relacionamentos
    family = relationship("Family", back_populates="finance_entries")
    category = relationship("FinanceCategory", back_populates="entries")
    created_by = relationship("User", back_populates="finance_entries")
    recurrence = relationship("FinanceRecurrence", back_populates="entries")

class FinanceRecurrence(Base):
    """
    Configuração de Recorrência (ex: Aluguel mensal)
    App: finance
    """
    __tablename__ = "finance_recurrence"
    
    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("finance_category.id"), nullable=True)
    description = Column(String(200), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    type = Column(String(10), nullable=False) # 'INCOME' ou 'EXPENSE'
    day_of_month = Column(Integer, nullable=False) # 1 a 31
    is_active = Column(Boolean, default=True)
    
    # Controle de geração
    last_generated_date = Column(Date, nullable=True) 
    
    created_by_id = Column(Integer, ForeignKey("auth_user.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relacionamentos
    family = relationship("Family", back_populates="finance_recurrences")
    category = relationship("FinanceCategory", back_populates="recurrences")
    entries = relationship("FinanceEntry", back_populates="recurrence")

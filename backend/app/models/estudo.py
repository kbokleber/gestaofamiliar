from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Atividade(Base):
    """Atividade de estudo de um filho."""

    __tablename__ = "estudo_atividade"

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("auth_user.id"), nullable=False, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    titulo = Column(String(200), nullable=False)
    descricao = Column(Text, nullable=False, default="")
    disciplina = Column(String(120), nullable=True, default="")
    professor = Column(String(150), nullable=False, default="")
    data = Column(Date, nullable=False, index=True)
    prazo_entrega = Column(DateTime(timezone=True), nullable=True)
    tipo = Column(String(20), nullable=False, default="atividade", server_default="atividade")
    autor = Column(String(150), nullable=True)
    numero = Column(String(40), nullable=True)
    anexos = Column(Text, nullable=True)
    anexos_resumo = Column(Text, nullable=True)
    status = Column(String(20), nullable=True, default="pendente", server_default="pendente")
    concluida_em = Column(DateTime(timezone=True), nullable=True)
    created_by_id = Column(Integer, ForeignKey("auth_user.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    aluno = relationship("User", foreign_keys=[aluno_id])
    created_by = relationship("User", foreign_keys=[created_by_id])

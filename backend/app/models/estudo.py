from sqlalchemy import Boolean, Column, Integer, String, Text, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class Apontamento(Base):
    """Observação/apontamento do portal e-class sobre o aluno."""

    __tablename__ = "estudo_apontamento"
    __table_args__ = (
        UniqueConstraint("family_id", "chave_origem", name="uq_estudo_apontamento_origem"),
    )

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    aluno_id = Column(Integer, ForeignKey("auth_user.id"), nullable=False, index=True)
    chave_origem = Column(String(160), nullable=False)
    data = Column(Date, nullable=True, index=True)
    disciplina = Column(String(120), nullable=False, default="")
    professor = Column(String(150), nullable=False, default="")
    tipo = Column(String(80), nullable=False, default="")
    titulo = Column(String(200), nullable=False, default="")
    descricao = Column(Text, nullable=False, default="")
    bimestre = Column(Integer, nullable=True)
    ano_letivo = Column(Integer, nullable=False)
    fonte = Column(String(20), nullable=False, default="e-class")
    scraped_at = Column(DateTime(timezone=True), nullable=True)
    hash_conteudo = Column(String(64), nullable=False, default="")
    created_by_id = Column(Integer, ForeignKey("auth_user.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    aluno = relationship("User", foreign_keys=[aluno_id])


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
    # True = criado pela tela do app (editável). False = integração via X-API-Token
    # (comunicados bloqueados para PUT/DELETE). Dados antigos: False (bloqueados).
    criado_pelo_app = Column(Boolean, nullable=False, default=False, server_default="false")
    created_by_id = Column(Integer, ForeignKey("auth_user.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    aluno = relationship("User", foreign_keys=[aluno_id])
    created_by = relationship("User", foreign_keys=[created_by_id])


class ComunicadoLido(Base):
    """Marca de leitura de um comunicado por uma pessoa (staff/admin/adulto).

    O estado de "lido" é individual: cada usuário tem a sua própria marca para
    cada linha de comunicado. Filhos não têm registros aqui.
    """

    __tablename__ = "estudo_comunicado_lido"
    __table_args__ = (
        UniqueConstraint("user_id", "atividade_id", name="uq_comunicado_lido_user_atividade"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("auth_user.id"), nullable=False, index=True)
    atividade_id = Column(Integer, ForeignKey("estudo_atividade.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", foreign_keys=[user_id])
    atividade = relationship("Atividade", foreign_keys=[atividade_id])

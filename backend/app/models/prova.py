from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, Boolean, Numeric, JSON, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base


class Cronograma(Base):
    """PDF de critérios avaliativos de uma turma num bimestre."""

    __tablename__ = "estudo_cronograma"
    __table_args__ = (
        UniqueConstraint("family_id", "chave_origem", name="uq_estudo_cronograma_origem"),
    )

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    chave_origem = Column(String(120), nullable=False)
    titulo = Column(String(255), nullable=False, default="")
    subtitulo = Column(String(255), nullable=False, default="")
    turma = Column(String(60), nullable=False, default="")
    turmas = Column(JSON, nullable=False, default=list)
    serie = Column(String(40), nullable=True)
    bimestre = Column(Integer, nullable=False)
    ano_letivo = Column(Integer, nullable=False)
    escola = Column(String(150), nullable=True)
    data_publicacao = Column(Date, nullable=True)
    autor = Column(String(150), nullable=True)
    aviso = Column(Text, nullable=False, default="")
    introducao = Column(Text, nullable=False, default="")
    orientacoes = Column(JSON, nullable=False, default=list)
    calendario_organizacional = Column(JSON, nullable=True)
    comunicado_id = Column(Integer, ForeignKey("estudo_atividade.id"), nullable=True)
    anexo_idx = Column(Integer, nullable=True)
    anexo_nome = Column(String(255), nullable=True)
    hash_conteudo = Column(String(64), nullable=False, default="")
    status = Column(String(20), nullable=False, default="ativo")
    created_by_id = Column(Integer, ForeignKey("auth_user.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    vinculos = relationship("CronogramaAluno", cascade="all, delete-orphan", back_populates="cronograma")
    avaliacoes = relationship("Avaliacao", cascade="all, delete-orphan", back_populates="cronograma")
    eventos = relationship("EventoEscolar", cascade="all, delete-orphan", back_populates="cronograma")
    comunicado = relationship("Atividade", foreign_keys=[comunicado_id])


class CronogramaAluno(Base):
    """Filhos para quem o cronograma vale."""

    __tablename__ = "estudo_cronograma_aluno"

    cronograma_id = Column(Integer, ForeignKey("estudo_cronograma.id", ondelete="CASCADE"), primary_key=True)
    aluno_id = Column(Integer, ForeignKey("auth_user.id"), primary_key=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("auth_user.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    cronograma = relationship("Cronograma", back_populates="vinculos")
    aluno = relationship("User", foreign_keys=[aluno_id])


class Avaliacao(Base):
    """Uma linha das tabelas de disciplina do PDF."""

    __tablename__ = "estudo_avaliacao"
    __table_args__ = (
        UniqueConstraint("family_id", "chave_origem", name="uq_estudo_avaliacao_origem"),
    )

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    cronograma_id = Column(Integer, ForeignKey("estudo_cronograma.id", ondelete="CASCADE"), nullable=False, index=True)
    chave_origem = Column(String(160), nullable=False)
    disciplina = Column(String(120), nullable=False)
    categoria = Column(String(20), nullable=False)
    categoria_rotulo = Column(String(40), nullable=True)
    tipo_codigo_eclass = Column(String(20), nullable=True, index=True)
    sequencia = Column(Integer, nullable=False, default=1)
    ordem = Column(Integer, nullable=False, default=1)
    titulo = Column(String(200), nullable=False)
    data_texto = Column(String(120), nullable=False, default="")
    sem_data = Column(Boolean, nullable=False, default=False)
    data_inicio = Column(Date, nullable=True, index=True)
    data_fim = Column(Date, nullable=True)
    valor = Column(Numeric(5, 2), nullable=True)
    valor_texto = Column(String(20), nullable=True)
    nota_alcancada = Column(Numeric(5, 2), nullable=True)
    professor = Column(String(150), nullable=True)
    composicao = Column(JSON, nullable=True)
    fonte = Column(String(20), nullable=False, default="pdf")
    objeto_conhecimento = Column(Text, nullable=False, default="")
    criterio_correcao = Column(Text, nullable=False, default="")
    material_necessario = Column(Text, nullable=True)
    observacoes = Column(Text, nullable=True)
    ambiguidades = Column(JSON, nullable=False, default=list)
    hash_conteudo = Column(String(64), nullable=False, default="")
    atividade_id = Column(Integer, ForeignKey("estudo_atividade.id"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("auth_user.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    cronograma = relationship("Cronograma", back_populates="avaliacoes")
    ocorrencias = relationship(
        "AvaliacaoOcorrencia",
        cascade="all, delete-orphan",
        back_populates="avaliacao",
        order_by="AvaliacaoOcorrencia.data_inicio",
    )
    itens = relationship(
        "AvaliacaoItem",
        cascade="all, delete-orphan",
        back_populates="avaliacao",
        order_by="AvaliacaoItem.ordem",
    )
    historico = relationship("AvaliacaoHistorico", cascade="all, delete-orphan", back_populates="avaliacao")


class AvaliacaoOcorrencia(Base):
    """Um dia ou um período em que a avaliação aparece no calendário."""

    __tablename__ = "estudo_avaliacao_ocorrencia"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    avaliacao_id = Column(Integer, ForeignKey("estudo_avaliacao.id", ondelete="CASCADE"), nullable=False, index=True)
    data_inicio = Column(Date, nullable=False, index=True)
    data_fim = Column(Date, nullable=False, index=True)
    turma = Column(String(20), nullable=True)
    created_by_id = Column(Integer, ForeignKey("auth_user.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    avaliacao = relationship("Avaliacao", back_populates="ocorrencias")


class AvaliacaoItem(Base):
    """Item numerado do critério de correção."""

    __tablename__ = "estudo_avaliacao_item"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    avaliacao_id = Column(Integer, ForeignKey("estudo_avaliacao.id", ondelete="CASCADE"), nullable=False, index=True)
    ordem = Column(Integer, nullable=False)
    descricao = Column(Text, nullable=False, default="")
    pontos = Column(Numeric(5, 2), nullable=True)
    por_unidade = Column(Boolean, nullable=False, default=False)
    quantidade = Column(Integer, nullable=True)
    created_by_id = Column(Integer, ForeignKey("auth_user.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    avaliacao = relationship("Avaliacao", back_populates="itens")


class EventoEscolar(Base):
    """Datas da legenda do calendário visual: recesso, semanas de prova, resultado."""

    __tablename__ = "estudo_evento_escolar"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    cronograma_id = Column(Integer, ForeignKey("estudo_cronograma.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo = Column(String(30), nullable=False)
    legenda = Column(String(150), nullable=False, default="")
    data_inicio = Column(Date, nullable=False, index=True)
    data_fim = Column(Date, nullable=False)
    created_by_id = Column(Integer, ForeignKey("auth_user.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    cronograma = relationship("Cronograma", back_populates="eventos")


class AvaliacaoHistorico(Base):
    """Mudança de datas, quando a escola remarca uma avaliação."""

    __tablename__ = "estudo_avaliacao_historico"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    avaliacao_id = Column(Integer, ForeignKey("estudo_avaliacao.id", ondelete="CASCADE"), nullable=False, index=True)
    ocorrencias_antes = Column(JSON, nullable=False, default=list)
    ocorrencias_depois = Column(JSON, nullable=False, default=list)
    motivo = Column(Text, nullable=True)
    comunicado_id = Column(Integer, ForeignKey("estudo_atividade.id"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("auth_user.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    avaliacao = relationship("Avaliacao", back_populates="historico")


class Boletim(Base):
    """Boletim (Notas e Faltas) sincronizado do e-class, por aluno × ano letivo."""

    __tablename__ = "estudo_boletim"
    __table_args__ = (
        UniqueConstraint("family_id", "aluno_id", "ano_letivo", name="uq_estudo_boletim_aluno_ano"),
    )

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    aluno_id = Column(Integer, ForeignKey("auth_user.id"), nullable=False, index=True)
    ano_letivo = Column(Integer, nullable=False)
    scraped_at = Column(DateTime(timezone=True), nullable=True)
    fonte = Column(String(20), nullable=False, default="e-class")
    total_faltas_por_bimestre = Column(JSON, nullable=True)
    created_by_id = Column(Integer, ForeignKey("auth_user.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    aluno = relationship("User", foreign_keys=[aluno_id])
    linhas = relationship("BoletimLinha", cascade="all, delete-orphan", back_populates="boletim")


class BoletimLinha(Base):
    """Uma disciplina no boletim, com nota/faltas por bimestre."""

    __tablename__ = "estudo_boletim_linha"
    __table_args__ = (
        UniqueConstraint("boletim_id", "disciplina", name="uq_estudo_boletim_linha_disciplina"),
    )

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    boletim_id = Column(Integer, ForeignKey("estudo_boletim.id", ondelete="CASCADE"), nullable=False, index=True)
    disciplina = Column(String(120), nullable=False)
    professor = Column(String(150), nullable=True)
    b1_nota = Column(Numeric(5, 2), nullable=True)
    b1_faltas = Column(Integer, nullable=True)
    b2_nota = Column(Numeric(5, 2), nullable=True)
    b2_faltas = Column(Integer, nullable=True)
    b3_nota = Column(Numeric(5, 2), nullable=True)
    b3_faltas = Column(Integer, nullable=True)
    b4_nota = Column(Numeric(5, 2), nullable=True)
    b4_faltas = Column(Integer, nullable=True)
    # Conceitos A/R (ou MB/B/…) por bimestre — Cultura Geral e afins no e-class.
    conceitos_por_bimestre = Column(JSON, nullable=True)
    nota_parcial = Column(Numeric(5, 2), nullable=True)
    bimestre_nota_parcial = Column(Integer, nullable=True)
    created_by_id = Column(Integer, ForeignKey("auth_user.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    boletim = relationship("Boletim", back_populates="linhas")

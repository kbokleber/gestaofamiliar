"""Localização dos celulares das crianças e lugares da família."""
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.db.base import Base


class LocationPairingCode(Base):
    """Código de uso único que o adulto gera e o celular da criança troca por um token."""

    __tablename__ = "location_pairing_code"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    child_user_id = Column(Integer, ForeignKey("auth_user.id"), nullable=False, index=True)
    code_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_by_id = Column(Integer, ForeignKey("auth_user.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LocationDevice(Base):
    """Celular pareado. O token em claro só existe no aparelho; aqui fica o hash."""

    __tablename__ = "location_device"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    child_user_id = Column(Integer, ForeignKey("auth_user.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    label = Column(String(80), nullable=False, default="")
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    # Informados pelo app a cada envio: versão (versionCode) e se as notificações estão liberadas.
    app_versao = Column(Integer, nullable=True)
    notificacoes_ativas = Column(Boolean, nullable=True)
    # Quando o alerta "sem enviar há 30 min" já foi dado; zera ao chegar um ponto novo.
    alerta_sem_sinal_em = Column(DateTime(timezone=True), nullable=True)
    created_by_id = Column(Integer, ForeignKey("auth_user.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LocationPoint(Base):
    """Um ponto enviado pelo celular: posição, precisão, velocidade e bateria."""

    __tablename__ = "location_point"
    __table_args__ = (
        Index("ix_location_point_child_time", "child_user_id", "recorded_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("location_device.id"), nullable=False, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    child_user_id = Column(Integer, ForeignKey("auth_user.id"), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy_m = Column(Float, nullable=True)
    speed_mps = Column(Float, nullable=True)
    battery_level = Column(Integer, nullable=True)
    recorded_at = Column(DateTime(timezone=True), nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LocationPlace(Base):
    """Lugar da família (Casa, Escola) com um ponto e um raio."""

    __tablename__ = "location_place"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    nome = Column(String(80), nullable=False)
    preposicao = Column(String(2), nullable=False, default="em")
    endereco = Column(String(200), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    raio_m = Column(Integer, nullable=False, default=150)
    created_by_id = Column(Integer, ForeignKey("auth_user.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class LocationPlaceState(Base):
    """Última situação conhecida da criança em cada lugar, para detectar chegada e saída."""

    __tablename__ = "location_place_state"
    __table_args__ = (
        UniqueConstraint("child_user_id", "place_id", name="uq_location_place_state"),
    )

    id = Column(Integer, primary_key=True, index=True)
    child_user_id = Column(Integer, ForeignKey("auth_user.id"), nullable=False, index=True)
    place_id = Column(Integer, ForeignKey("location_place.id", ondelete="CASCADE"), nullable=False, index=True)
    inside = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LocationPlaceEvent(Base):
    """Chegada ou saída. O nome do lugar fica copiado para o histórico sobreviver à exclusão."""

    __tablename__ = "location_place_event"
    __table_args__ = (
        Index("ix_location_place_event_child_time", "child_user_id", "recorded_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    child_user_id = Column(Integer, ForeignKey("auth_user.id"), nullable=False, index=True)
    device_id = Column(Integer, ForeignKey("location_device.id"), nullable=True)
    place_id = Column(Integer, ForeignKey("location_place.id", ondelete="SET NULL"), nullable=True)
    lugar_nome = Column(String(80), nullable=False)
    preposicao = Column(String(2), nullable=False, default="em")
    tipo = Column(String(10), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)


class LocationChildSettings(Base):
    """Preferências do mapa por criança, como o apelido que aparece no marcador."""

    __tablename__ = "location_child_settings"

    child_user_id = Column(Integer, ForeignKey("auth_user.id"), primary_key=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    apelido = Column(String(12), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class LocationSos(Base):
    """Pedido de socorro feito pelo botão SOS do app (criança ou adulto que compartilha)."""

    __tablename__ = "location_sos"
    __table_args__ = (Index("ix_location_sos_device_time", "device_id", "created_at"),)

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("auth_user.id"), nullable=False, index=True)
    device_id = Column(Integer, ForeignKey("location_device.id"), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    accuracy_m = Column(Float, nullable=True)
    battery_level = Column(Integer, nullable=True)
    posicao_em = Column(DateTime(timezone=True), nullable=True)
    avisados = Column(Integer, nullable=False, default=0)
    # Por que ninguém foi avisado (ex.: "sem destinatário elegível"); o site mostra ao admin.
    motivo = Column(String(60), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    visto_em = Column(DateTime(timezone=True), nullable=True)
    visto_por_id = Column(Integer, ForeignKey("auth_user.id"), nullable=True)


class LocationSosDestinatario(Base):
    """Familiar escolhido para receber o SOS da família (só adultos que veem o mapa)."""

    __tablename__ = "location_sos_destinatario"
    __table_args__ = (UniqueConstraint("family_id", "user_id", name="uq_location_sos_destinatario"),)

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("auth_user.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LocationSosAvisado(Base):
    """Quem recebeu o aviso de um SOS: só essas pessoas veem o SOS (com posição) e marcam "Visto"."""

    __tablename__ = "location_sos_avisado"
    __table_args__ = (UniqueConstraint("sos_id", "user_id", name="uq_location_sos_avisado"),)

    id = Column(Integer, primary_key=True, index=True)
    sos_id = Column(Integer, ForeignKey("location_sos.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("auth_user.id"), nullable=False, index=True)

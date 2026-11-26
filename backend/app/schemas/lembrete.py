from pydantic import BaseModel, field_validator


SONS = {"desligado", "padrao", "mp3"}
VOLUMES = {"medio", "alto"}


def _opcao(valor: str, opcoes: set[str], mensagem: str) -> str:
    valor = (valor or "").strip().lower()
    if valor not in opcoes:
        raise ValueError(mensagem)
    return valor


class FamilyLembreteConfigResponse(BaseModel):
    enabled: bool
    intervalo: int
    unidade: str
    som: str = "desligado"
    volume: str = "medio"


class FamilyLembreteConfigUpdate(BaseModel):
    enabled: bool = False
    intervalo: int = 2
    unidade: str = "horas"
    # Sem os campos (site antigo), o alarme continua como estava.
    som: str | None = None
    volume: str | None = None

    @field_validator("som")
    @classmethod
    def som_conhecido(cls, valor: str | None) -> str | None:
        return None if valor is None else _opcao(valor, SONS, "O som deve ser desligado, padrao ou mp3.")

    @field_validator("volume")
    @classmethod
    def volume_conhecido(cls, valor: str | None) -> str | None:
        return None if valor is None else _opcao(valor, VOLUMES, "O volume deve ser medio ou alto.")

    @field_validator("unidade")
    @classmethod
    def unidade_conhecida(cls, valor: str) -> str:
        valor = valor.strip().lower()
        if valor not in {"horas", "minutos"}:
            raise ValueError("A unidade deve ser horas ou minutos.")
        return valor

    def validar(self) -> None:
        if self.unidade == "minutos" and not 1 <= self.intervalo <= 180:
            raise ValueError("Em minutos, use de 1 a 180.")
        if self.unidade == "horas" and not 1 <= self.intervalo <= 12:
            raise ValueError("Em horas, use de 1 a 12.")


class PushInscricaoCreate(BaseModel):
    endpoint: str
    keys: dict

    def p256dh(self) -> str:
        return str(self.keys.get("p256dh") or "")

    def auth_key(self) -> str:
        return str(self.keys.get("auth") or "")


class TesteAlarmeIn(BaseModel):
    """Teste do alarme no celular do próprio adulto. Sem campos, usa padrao/alto."""
    som: str = "padrao"
    volume: str = "alto"

    @field_validator("som")
    @classmethod
    def som_que_toca(cls, valor: str) -> str:
        return _opcao(valor, SONS - {"desligado"}, "No teste, o som deve ser padrao ou mp3.")

    @field_validator("volume")
    @classmethod
    def volume_conhecido(cls, valor: str) -> str:
        return _opcao(valor, VOLUMES, "O volume deve ser medio ou alto.")

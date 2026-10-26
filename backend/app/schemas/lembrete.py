from pydantic import BaseModel, field_validator


class FamilyLembreteConfigResponse(BaseModel):
    enabled: bool
    intervalo: int
    unidade: str


class FamilyLembreteConfigUpdate(BaseModel):
    enabled: bool = False
    intervalo: int = 2
    unidade: str = "horas"

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

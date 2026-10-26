from pydantic import BaseModel, field_validator
from urllib.parse import urlparse


class FamilyWhatsAppConfigResponse(BaseModel):
    enabled: bool
    url: str
    destino: str


class FamilyWhatsAppConfigUpdate(BaseModel):
    enabled: bool = False
    url: str = ""
    destino: str = ""

    @field_validator("url", "destino")
    @classmethod
    def sem_pontas(cls, valor: str) -> str:
        return valor.strip()

    def validar(self) -> None:
        if not self.enabled:
            return
        if not self.url or not self.destino:
            raise ValueError("Informe a URL e o grupo ou número.")
        if len(self.destino) > 120:
            raise ValueError("O grupo ou número é longo demais.")
        partes = urlparse(self.url)
        if partes.scheme not in {"http", "https"} or not partes.netloc:
            raise ValueError("A URL precisa começar com http:// ou https://.")

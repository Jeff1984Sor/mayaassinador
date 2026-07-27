"""Schemas de documento."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.documento import StatusDocumento
from app.models.envio_email import StatusEnvio
from app.models.evento import TipoEvento


class DocumentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome_original: str
    status: StatusDocumento
    rubricado: bool
    paginas: int | None
    tamanho: int | None
    hash_sha256: str | None
    codigo_verificacao: str | None
    erro_msg: str | None
    criado_em: datetime
    processado_em: datetime | None


class EventoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: TipoEvento
    detalhe: str | None
    criado_em: datetime


class DocumentoDetalhe(DocumentoOut):
    eventos: list[EventoOut] = []
    envios: list["EnvioOut"] = []


class ListaDocumentos(BaseModel):
    itens: list[DocumentoOut]
    total: int
    pagina: int
    paginas: int


class EnvioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    destinatarios: list[str]
    assunto: str
    status: StatusEnvio
    erro_msg: str | None
    enviado_em: datetime | None
    criado_em: datetime


class EnviarEmailRequest(BaseModel):
    destinatarios: list[EmailStr] = Field(min_length=1, max_length=20)
    assunto: str = Field(min_length=1, max_length=255)
    mensagem: str = Field(default="", max_length=5000)
    remetente_nome: str | None = Field(default=None, max_length=200)
    remetente_email: EmailStr | None = None


class PadraoEmail(BaseModel):
    """Valores que a tela usa para pre-preencher o modal de envio."""

    assunto: str
    mensagem: str
    remetente_nome: str
    remetente_email: str
    smtp_configurado: bool


class RenomearRequest(BaseModel):
    nome_original: str = Field(min_length=1, max_length=480)


class ResumoDocumentos(BaseModel):
    total: int
    prontos: int
    enviados_email: int
    com_erro: int
    processando: int

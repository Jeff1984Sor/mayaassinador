"""Schemas de documento."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.documento import StatusDocumento
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


class ListaDocumentos(BaseModel):
    itens: list[DocumentoOut]
    total: int
    pagina: int
    paginas: int


class ResumoDocumentos(BaseModel):
    total: int
    prontos: int
    enviados_email: int
    com_erro: int
    processando: int

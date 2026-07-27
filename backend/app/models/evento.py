"""Trilha de auditoria do documento — advogado adora rastro."""

from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.documento import Documento


class TipoEvento(StrEnum):
    CRIADO = "criado"
    PROCESSAMENTO_INICIADO = "processamento_iniciado"
    CABECALHO_APLICADO = "cabecalho_aplicado"
    RODAPE_APLICADO = "rodape_aplicado"
    CONVERTIDO_PDF = "convertido_pdf"
    RUBRICA_APLICADA = "rubrica_aplicada"
    ASSINATURA_APLICADA = "assinatura_aplicada"
    HASH_GERADO = "hash_gerado"
    PRONTO = "pronto"
    ERRO = "erro"
    REPROCESSADO = "reprocessado"
    EMAIL_ENVIADO = "email_enviado"
    DOWNLOAD = "download"
    EXCLUIDO = "excluido"


class EventoDocumento(Base, TimestampMixin):
    __tablename__ = "eventos_documento"

    id: Mapped[int] = mapped_column(primary_key=True)
    documento_id: Mapped[int] = mapped_column(
        ForeignKey("documentos.id", ondelete="CASCADE"), index=True, nullable=False
    )
    tipo: Mapped[TipoEvento] = mapped_column(
        SAEnum(TipoEvento, name="tipo_evento", native_enum=False, length=40), nullable=False
    )
    detalhe: Mapped[str | None] = mapped_column(Text)

    documento: Mapped["Documento"] = relationship(back_populates="eventos")

"""Historico de envios por email (tela 4.5)."""

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.documento import Documento


class StatusEnvio(StrEnum):
    PENDENTE = "pendente"
    ENVIADO = "enviado"
    ERRO = "erro"


class EnvioEmail(Base, TimestampMixin):
    __tablename__ = "envios_email"

    id: Mapped[int] = mapped_column(primary_key=True)
    documento_id: Mapped[int] = mapped_column(
        ForeignKey("documentos.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # lista de emails
    destinatarios: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    assunto: Mapped[str] = mapped_column(String(255), nullable=False)
    mensagem: Mapped[str | None] = mapped_column(Text)

    status: Mapped[StatusEnvio] = mapped_column(
        SAEnum(StatusEnvio, name="status_envio", native_enum=False, length=20),
        default=StatusEnvio.PENDENTE,
        nullable=False,
    )
    erro_msg: Mapped[str | None] = mapped_column(Text)
    enviado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    documento: Mapped["Documento"] = relationship(back_populates="envios")

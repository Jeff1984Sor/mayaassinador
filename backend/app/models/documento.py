"""Documento — o centro do produto.

A tabela tambem funciona como FILA do pipeline: o worker busca os
documentos em status ENVIADO com SELECT ... FOR UPDATE SKIP LOCKED.
Decisao da F0: o unico Redis do prod2 pertence ao container do Evolution,
entao nao dependemos de infra de outro produto.
"""

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.envio_email import EnvioEmail
    from app.models.evento import EventoDocumento


class StatusDocumento(StrEnum):
    ENVIADO = "enviado"
    PROCESSANDO = "processando"
    PRONTO = "pronto"
    ENVIADO_EMAIL = "enviado_email"
    ERRO = "erro"


class Documento(Base, TimestampMixin):
    __tablename__ = "documentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )

    nome_original: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[StatusDocumento] = mapped_column(
        SAEnum(StatusDocumento, name="status_documento", native_enum=False, length=20),
        default=StatusDocumento.ENVIADO,
        index=True,
        nullable=False,
    )
    rubricado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # caminhos relativos ao STORAGE_ROOT: {tenant}/{documento_id}/original.docx
    caminho_original: Mapped[str | None] = mapped_column(String(500))
    caminho_final: Mapped[str | None] = mapped_column(String(500))

    hash_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    # codigo curto da pagina publica /verificar/{codigo}
    codigo_verificacao: Mapped[str | None] = mapped_column(String(12), unique=True, index=True)

    tamanho: Mapped[int | None] = mapped_column(BigInteger)
    paginas: Mapped[int | None] = mapped_column()
    erro_msg: Mapped[str | None] = mapped_column(Text)

    # ---- controle da fila ----
    tentativas: Mapped[int] = mapped_column(default=0, nullable=False)
    processando_desde: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # soft delete — o anexo original do cliente e sagrado
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    envios: Mapped[list["EnvioEmail"]] = relationship(
        back_populates="documento", cascade="all, delete-orphan"
    )
    eventos: Mapped[list["EventoDocumento"]] = relationship(
        back_populates="documento", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Documento {self.id} {self.nome_original} [{self.status}]>"

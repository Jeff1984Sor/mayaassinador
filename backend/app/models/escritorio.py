"""Dados institucionais do escritorio — FONTE UNICA DA VERDADE.

Estes campos alimentam cabecalho, rodape, template de email e a pagina
publica de verificacao. Cadastra uma vez, reflete em tudo.
"""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.tenant import Tenant


class Escritorio(Base, TimestampMixin):
    __tablename__ = "escritorios"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    razao_social: Mapped[str] = mapped_column(String(255), nullable=False)
    nome_fantasia: Mapped[str | None] = mapped_column(String(255))
    cnpj: Mapped[str | None] = mapped_column(String(18))

    oab_numero: Mapped[str | None] = mapped_column(String(30))
    oab_seccional: Mapped[str | None] = mapped_column(String(2))

    # Quem assina os documentos. Separado da razao social porque quem assina
    # e a pessoa (o advogado), nao a pessoa juridica — e e este nome que o
    # pipeline procura no PDF para ancorar a imagem da assinatura.
    signatario_nome: Mapped[str | None] = mapped_column(String(200))
    signatario_oab: Mapped[str | None] = mapped_column(String(30))

    logradouro: Mapped[str | None] = mapped_column(String(255))
    numero: Mapped[str | None] = mapped_column(String(20))
    complemento: Mapped[str | None] = mapped_column(String(100))
    bairro: Mapped[str | None] = mapped_column(String(100))
    cidade: Mapped[str | None] = mapped_column(String(100))
    uf: Mapped[str | None] = mapped_column(String(2))
    cep: Mapped[str | None] = mapped_column(String(9))

    telefone: Mapped[str | None] = mapped_column(String(20))
    whatsapp: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    site: Mapped[str | None] = mapped_column(String(255))

    # caminho relativo dentro do STORAGE_ROOT
    logo_path: Mapped[str | None] = mapped_column(String(500))

    tenant: Mapped["Tenant"] = relationship(back_populates="escritorio")

    def __repr__(self) -> str:
        return f"<Escritorio {self.razao_social}>"

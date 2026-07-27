"""Tenant — o escritorio como unidade de isolamento. Hoje 1, mas a
arquitetura ja nasce multi-tenant (slug na URL)."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.configuracao import ConfiguracaoTenant
    from app.models.escritorio import Escritorio
    from app.models.usuario import Usuario


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="tenant")
    escritorio: Mapped["Escritorio | None"] = relationship(
        back_populates="tenant", uselist=False
    )
    configuracao: Mapped["ConfiguracaoTenant | None"] = relationship(
        back_populates="tenant", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Tenant {self.slug}>"

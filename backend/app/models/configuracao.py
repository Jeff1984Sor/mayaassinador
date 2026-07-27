"""Configuracao do tenant: imagens, composicao de cabecalho/rodape,
tipografia e SMTP.

IMPORTANTE (achado da F0): as fontes disponiveis sao apenas as instaladas
no prod2. Qualquer fonte fora de FONTES_DISPONIVEIS seria substituida pelo
LibreOffice na conversao, e o PDF sairia diferente do preview.
"""

from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.tenant import Tenant


# Fonte instalada no servidor -> rotulo exibido no dropdown.
# Carlito e Caladea sao metricamente identicos a Calibri e Cambria.
FONTES_DISPONIVEIS: dict[str, str] = {
    "Arial": "Arial",
    "Times New Roman": "Times New Roman",
    "Georgia": "Georgia",
    "Courier New": "Courier New",
    "Carlito": "Calibri (Carlito)",
    "Caladea": "Cambria (Caladea)",
}

TIPOGRAFIA_PADRAO: dict[str, Any] = {
    "fonte": "Arial",
    "tamanho": 10,
    "alinhamento": "centro",  # esquerda | centro | direita
    "negrito": False,
    "italico": False,
    "cor": "#1E2D6B",
}


class ConfiguracaoTenant(Base, TimestampMixin):
    __tablename__ = "configuracoes_tenant"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    # ---- Cabecalho ----
    # quais campos do Escritorio aparecem no cabecalho (checkboxes na tela 4.4)
    cabecalho_campos: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=lambda: {"razao_social": True, "oab": True, "endereco": True,
                                "telefone": True, "email": True, "site": False}
    )
    cabecalho_tipografia: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=lambda: dict(TIPOGRAFIA_PADRAO)
    )
    # esquerda | direita | acima | sem_logo
    logo_posicao: Mapped[str] = mapped_column(String(20), default="esquerda")

    # ---- Rodape ----
    # mesma ideia do cabecalho: quais dados do escritorio aparecem.
    # Padrao tudo false — o rodape historicamente so tinha texto livre.
    rodape_campos: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=lambda: {"razao_social": False, "cnpj": False, "oab": False,
                                "endereco": False, "telefone": False, "whatsapp": False,
                                "email": False, "site": False}
    )
    rodape_texto: Mapped[str | None] = mapped_column(Text)
    rodape_tipografia: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=lambda: dict(TIPOGRAFIA_PADRAO)
    )
    rodape_numeracao: Mapped[bool] = mapped_column(Boolean, default=True)
    # alinhamento da numeracao, independente do texto do rodape
    rodape_numeracao_alinhamento: Mapped[str] = mapped_column(String(20), default="direita")

    # ---- Imagens (caminhos relativos ao STORAGE_ROOT) ----
    rubrica_path: Mapped[str | None] = mapped_column(String(500))
    assinatura_path: Mapped[str | None] = mapped_column(String(500))
    rubricar_por_padrao: Mapped[bool] = mapped_column(Boolean, default=False)

    # QR de verificacao na ultima pagina. Opcional: nem todo escritorio quer
    # um QR estampado no documento. Desligado, o hash e o codigo continuam
    # sendo gerados e o documento segue verificavel pela pagina publica.
    qrcode_ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    # ---- SMTP (senha criptografada com Fernet, nunca em texto puro) ----
    smtp_host: Mapped[str | None] = mapped_column(String(255))
    smtp_porta: Mapped[int | None] = mapped_column()
    smtp_usuario: Mapped[str | None] = mapped_column(String(255))
    smtp_senha_cripto: Mapped[str | None] = mapped_column(Text)
    smtp_tls: Mapped[bool] = mapped_column(Boolean, default=True)
    email_remetente_nome: Mapped[str | None] = mapped_column(String(200))
    email_assunto_padrao: Mapped[str | None] = mapped_column(String(255))
    email_mensagem_padrao: Mapped[str | None] = mapped_column(Text)

    tenant: Mapped["Tenant"] = relationship(back_populates="configuracao")

    def __repr__(self) -> str:
        return f"<ConfiguracaoTenant tenant_id={self.tenant_id}>"

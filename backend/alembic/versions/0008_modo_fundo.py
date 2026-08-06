"""F6: modo de remocao de fundo (branco ou automatico)

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-06
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# "branco" preserva o comportamento de quem ja tem imagens tratadas: elas
# nao mudam de aparencia sozinhas ao subir esta versao.
IMAGENS = ("logo", "rubrica", "assinatura")


def upgrade() -> None:
    for imagem in IMAGENS:
        op.add_column(
            "configuracoes_tenant",
            sa.Column(
                f"{imagem}_modo_fundo",
                sa.String(10),
                nullable=False,
                server_default="branco",
            ),
        )
        op.alter_column(
            "configuracoes_tenant", f"{imagem}_modo_fundo", server_default=None
        )


def downgrade() -> None:
    for imagem in reversed(IMAGENS):
        op.drop_column("configuracoes_tenant", f"{imagem}_modo_fundo")

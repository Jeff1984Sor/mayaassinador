"""F6: tolerancia da remocao de fundo por imagem + logo opcionalmente tratado

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-06
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 40 e a tolerancia que estava fixa em imagens.remover_fundo; o logo continua
# sem tratamento por padrao, como sempre foi.
COLUNAS = (
    ("rubrica_tolerancia", sa.Integer(), "40"),
    ("assinatura_tolerancia", sa.Integer(), "40"),
    ("logo_tolerancia", sa.Integer(), "40"),
    ("logo_remover_fundo", sa.Boolean(), sa.false()),
)


def upgrade() -> None:
    for nome, tipo, padrao in COLUNAS:
        op.add_column(
            "configuracoes_tenant",
            sa.Column(nome, tipo, nullable=False, server_default=padrao),
        )
        op.alter_column("configuracoes_tenant", nome, server_default=None)


def downgrade() -> None:
    for nome, _, _ in reversed(COLUNAS):
        op.drop_column("configuracoes_tenant", nome)

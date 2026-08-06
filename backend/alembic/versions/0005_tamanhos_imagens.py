"""F5: tamanho configuravel do logo, da rubrica e da assinatura

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-06
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Os defaults sao exatamente os valores que estavam fixos no codigo, para
# que quem ja tem documentos gerados nao veja o timbre mudar sozinho.
COLUNAS = (
    ("logo_altura", 34),
    ("rubrica_altura", 26),
    ("assinatura_altura", 84),
)


def upgrade() -> None:
    for nome, padrao in COLUNAS:
        op.add_column(
            "configuracoes_tenant",
            sa.Column(nome, sa.Integer(), nullable=False, server_default=str(padrao)),
        )
        op.alter_column("configuracoes_tenant", nome, server_default=None)


def downgrade() -> None:
    for nome, _ in reversed(COLUNAS):
        op.drop_column("configuracoes_tenant", nome)

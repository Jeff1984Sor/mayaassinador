"""F5: numeracao de pagina no cabecalho ou no rodape

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-27
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # "rodape" preserva o comportamento de quem ja tem documentos gerados
    op.add_column(
        "configuracoes_tenant",
        sa.Column(
            "numeracao_local", sa.String(10), nullable=False, server_default="rodape"
        ),
    )
    op.alter_column("configuracoes_tenant", "numeracao_local", server_default=None)


def downgrade() -> None:
    op.drop_column("configuracoes_tenant", "numeracao_local")

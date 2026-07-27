"""F5: signatario e posicionamento ancorado da assinatura

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-27
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("escritorios", sa.Column("signatario_nome", sa.String(200)))
    op.add_column("escritorios", sa.Column("signatario_oab", sa.String(30)))

    # "fixa" preserva o comportamento atual de quem ja tem documentos gerados
    op.add_column(
        "configuracoes_tenant",
        sa.Column(
            "assinatura_modo",
            sa.String(10),
            nullable=False,
            server_default="fixa",
        ),
    )
    op.add_column(
        "configuracoes_tenant", sa.Column("assinatura_ancora", sa.String(200))
    )
    op.add_column(
        "configuracoes_tenant",
        sa.Column(
            "assinatura_relativa",
            sa.String(10),
            nullable=False,
            server_default="abaixo",
        ),
    )
    op.add_column(
        "configuracoes_tenant",
        sa.Column(
            "assinatura_deslocamento",
            sa.Integer(),
            nullable=False,
            server_default="6",
        ),
    )

    for coluna in (
        "assinatura_modo",
        "assinatura_relativa",
        "assinatura_deslocamento",
    ):
        op.alter_column("configuracoes_tenant", coluna, server_default=None)


def downgrade() -> None:
    op.drop_column("configuracoes_tenant", "assinatura_deslocamento")
    op.drop_column("configuracoes_tenant", "assinatura_relativa")
    op.drop_column("configuracoes_tenant", "assinatura_ancora")
    op.drop_column("configuracoes_tenant", "assinatura_modo")
    op.drop_column("escritorios", "signatario_oab")
    op.drop_column("escritorios", "signatario_nome")

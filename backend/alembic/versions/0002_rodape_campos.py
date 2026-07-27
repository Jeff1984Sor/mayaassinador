"""F5: campos do escritorio no rodape + QR opcional

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-27
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PADRAO = (
    '{"razao_social": false, "cnpj": false, "oab": false, "endereco": false, '
    '"telefone": false, "whatsapp": false, "email": false, "site": false}'
)


def upgrade() -> None:
    # server_default preenche as linhas existentes; removido em seguida para
    # que o padrao passe a vir do model, como nas outras colunas JSONB.
    op.add_column(
        "configuracoes_tenant",
        sa.Column(
            "rodape_campos",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text(f"'{PADRAO}'::jsonb"),
        ),
    )
    op.alter_column("configuracoes_tenant", "rodape_campos", server_default=None)

    # ligado para quem ja usava: o comportamento anterior era sempre carimbar
    op.add_column(
        "configuracoes_tenant",
        sa.Column(
            "qrcode_ativo", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
    )
    op.alter_column("configuracoes_tenant", "qrcode_ativo", server_default=None)


def downgrade() -> None:
    op.drop_column("configuracoes_tenant", "qrcode_ativo")
    op.drop_column("configuracoes_tenant", "rodape_campos")

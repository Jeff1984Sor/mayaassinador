"""F6: rotacao e recorte das imagens

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-06
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

IMAGENS = ("logo", "rubrica", "assinatura")


def upgrade() -> None:
    for imagem in IMAGENS:
        # graus no sentido horario; 0 = como veio
        op.add_column(
            "configuracoes_tenant",
            sa.Column(
                f"{imagem}_rotacao", sa.Integer(), nullable=False, server_default="0"
            ),
        )
        op.alter_column("configuracoes_tenant", f"{imagem}_rotacao", server_default=None)

        # {x, y, largura, altura} em fracao do lado; NULL = imagem inteira
        op.add_column(
            "configuracoes_tenant",
            sa.Column(f"{imagem}_recorte", JSONB(), nullable=True),
        )


def downgrade() -> None:
    for imagem in reversed(IMAGENS):
        op.drop_column("configuracoes_tenant", f"{imagem}_recorte")
        op.drop_column("configuracoes_tenant", f"{imagem}_rotacao")

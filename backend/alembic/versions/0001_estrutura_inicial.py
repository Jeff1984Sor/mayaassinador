"""F1: estrutura inicial

Revision ID: 0001
Revises:
Create Date: 2026-07-27
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("criado_em", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    # ---------------- tenants ----------------
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(60), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)

    # ---------------- usuarios ----------------
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("senha_hash", sa.String(255), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("tenant_id", "email", name="uq_usuario_tenant_email"),
    )
    op.create_index("ix_usuarios_tenant_id", "usuarios", ["tenant_id"])
    op.create_index("ix_usuarios_email", "usuarios", ["email"])

    # ---------------- escritorios ----------------
    op.create_table(
        "escritorios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("razao_social", sa.String(255), nullable=False),
        sa.Column("nome_fantasia", sa.String(255)),
        sa.Column("cnpj", sa.String(18)),
        sa.Column("oab_numero", sa.String(30)),
        sa.Column("oab_seccional", sa.String(2)),
        sa.Column("logradouro", sa.String(255)),
        sa.Column("numero", sa.String(20)),
        sa.Column("complemento", sa.String(100)),
        sa.Column("bairro", sa.String(100)),
        sa.Column("cidade", sa.String(100)),
        sa.Column("uf", sa.String(2)),
        sa.Column("cep", sa.String(9)),
        sa.Column("telefone", sa.String(20)),
        sa.Column("whatsapp", sa.String(20)),
        sa.Column("email", sa.String(255)),
        sa.Column("site", sa.String(255)),
        sa.Column("logo_path", sa.String(500)),
        *_timestamps(),
    )

    # ---------------- configuracoes_tenant ----------------
    op.create_table(
        "configuracoes_tenant",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("cabecalho_campos", postgresql.JSONB(), nullable=False),
        sa.Column("cabecalho_tipografia", postgresql.JSONB(), nullable=False),
        sa.Column("logo_posicao", sa.String(20), nullable=False),
        sa.Column("rodape_texto", sa.Text()),
        sa.Column("rodape_tipografia", postgresql.JSONB(), nullable=False),
        sa.Column("rodape_numeracao", sa.Boolean(), nullable=False),
        sa.Column("rodape_numeracao_alinhamento", sa.String(20), nullable=False),
        sa.Column("rubrica_path", sa.String(500)),
        sa.Column("assinatura_path", sa.String(500)),
        sa.Column("rubricar_por_padrao", sa.Boolean(), nullable=False),
        sa.Column("smtp_host", sa.String(255)),
        sa.Column("smtp_porta", sa.Integer()),
        sa.Column("smtp_usuario", sa.String(255)),
        sa.Column("smtp_senha_cripto", sa.Text()),
        sa.Column("smtp_tls", sa.Boolean(), nullable=False),
        sa.Column("email_remetente_nome", sa.String(200)),
        sa.Column("email_assunto_padrao", sa.String(255)),
        sa.Column("email_mensagem_padrao", sa.Text()),
        *_timestamps(),
    )

    # ---------------- documentos ----------------
    op.create_table(
        "documentos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("usuario_id", sa.Integer(),
                  sa.ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("nome_original", sa.String(500), nullable=False),
        sa.Column(
            "status",
            sa.Enum("enviado", "processando", "pronto", "enviado_email", "erro",
                    name="status_documento", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("rubricado", sa.Boolean(), nullable=False),
        sa.Column("caminho_original", sa.String(500)),
        sa.Column("caminho_final", sa.String(500)),
        sa.Column("hash_sha256", sa.String(64)),
        sa.Column("codigo_verificacao", sa.String(12), unique=True),
        sa.Column("tamanho", sa.BigInteger()),
        sa.Column("paginas", sa.Integer()),
        sa.Column("erro_msg", sa.Text()),
        sa.Column("tentativas", sa.Integer(), nullable=False),
        sa.Column("processando_desde", sa.DateTime(timezone=True)),
        sa.Column("processado_em", sa.DateTime(timezone=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        *_timestamps(),
    )
    op.create_index("ix_documentos_tenant_id", "documentos", ["tenant_id"])
    op.create_index("ix_documentos_status", "documentos", ["status"])
    op.create_index("ix_documentos_hash_sha256", "documentos", ["hash_sha256"])
    op.create_index("ix_documentos_codigo_verificacao", "documentos",
                    ["codigo_verificacao"], unique=True)
    op.create_index("ix_documentos_deleted_at", "documentos", ["deleted_at"])
    # indice parcial da FILA: o worker busca so os pendentes, nao varre a tabela
    op.execute(
        "CREATE INDEX ix_documentos_fila ON documentos (criado_em) "
        "WHERE status = 'enviado' AND deleted_at IS NULL"
    )

    # ---------------- envios_email ----------------
    op.create_table(
        "envios_email",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("documento_id", sa.Integer(),
                  sa.ForeignKey("documentos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("destinatarios", postgresql.JSONB(), nullable=False),
        sa.Column("assunto", sa.String(255), nullable=False),
        sa.Column("mensagem", sa.Text()),
        sa.Column(
            "status",
            sa.Enum("pendente", "enviado", "erro",
                    name="status_envio", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("erro_msg", sa.Text()),
        sa.Column("enviado_em", sa.DateTime(timezone=True)),
        *_timestamps(),
    )
    op.create_index("ix_envios_email_documento_id", "envios_email", ["documento_id"])

    # ---------------- eventos_documento ----------------
    op.create_table(
        "eventos_documento",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("documento_id", sa.Integer(),
                  sa.ForeignKey("documentos.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "tipo",
            sa.Enum("criado", "processamento_iniciado", "cabecalho_aplicado",
                    "rodape_aplicado", "convertido_pdf", "rubrica_aplicada",
                    "assinatura_aplicada", "hash_gerado", "pronto", "erro",
                    "reprocessado", "email_enviado", "download", "excluido",
                    name="tipo_evento", native_enum=False, length=40),
            nullable=False,
        ),
        sa.Column("detalhe", sa.Text()),
        *_timestamps(),
    )
    op.create_index("ix_eventos_documento_documento_id",
                    "eventos_documento", ["documento_id"])


def downgrade() -> None:
    op.drop_table("eventos_documento")
    op.drop_table("envios_email")
    op.execute("DROP INDEX IF EXISTS ix_documentos_fila")
    op.drop_table("documentos")
    op.drop_table("configuracoes_tenant")
    op.drop_table("escritorios")
    op.drop_table("usuarios")
    op.drop_table("tenants")

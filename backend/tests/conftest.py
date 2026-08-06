"""Infra minima de teste: banco em memoria, sem tocar no Postgres do prod2.

Nao ha banco de teste no servidor e nao queremos um: os testes precisam
rodar em qualquer maquina, inclusive na sua, antes do deploy.
"""

import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://teste:teste@localhost/teste")
os.environ.setdefault("SECRET_KEY", "chave-de-teste")
os.environ.setdefault("FERNET_KEY", "T3st3T3st3T3st3T3st3T3st3T3st3T3st3T3st3T3U=")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


@compiles(JSONB, "sqlite")
def _jsonb_no_sqlite(type_, compiler, **kw):  # noqa: ANN001
    """O SQLite nao tem JSONB. Para o que testamos aqui, JSON basta."""
    return "JSON"


@pytest.fixture
def db() -> Session:
    from app.db.base import Base
    import app.models  # noqa: F401 — registra os mapeamentos antes do create_all

    # StaticPool: sem ele cada conexao abre um banco em memoria NOVO, e a
    # thread do TestClient nao enxergaria as linhas inseridas pelo teste
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    sessao = Session(engine)
    try:
        yield sessao
    finally:
        sessao.close()
        engine.dispose()

"""Ponto de entrada da API do MayaAssinador."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes import arquivos, auth, configuracao, documentos, escritorio
from app.core.config import settings
from app.db.session import engine

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(escritorio.router, prefix="/api")
app.include_router(configuracao.router, prefix="/api")
app.include_router(documentos.router, prefix="/api")
app.include_router(arquivos.router, prefix="/api")


@app.get("/api/health", tags=["infra"])
def health() -> dict[str, object]:
    """Checa API + banco + storage. E o teste de fumaca do deploy."""
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:  # noqa: BLE001 — health nunca deve levantar
        db_ok = False

    return {
        "status": "ok" if db_ok else "degraded",
        "app": settings.APP_NAME,
        "versao": "0.1.0",
        "banco": db_ok,
        "storage": settings.STORAGE_ROOT.exists(),
    }

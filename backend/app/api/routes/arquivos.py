"""Servir imagens do storage — sempre autenticado.

O nginx nunca expoe /var/mayaassinador/storage diretamente.

Detalhe: <img src> nao envia header Authorization, entao este endpoint
tambem aceita o token por query string. E o unico lugar do sistema onde
isso e permitido, e so serve imagens de configuracao do proprio tenant.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.api.deps import DbSession
from app.core.security import decodificar_token
from app.core.storage import dir_config
from app.models import Tenant, Usuario

router = APIRouter(prefix="/{tenant}/arquivos", tags=["arquivos"])

ARQUIVOS_CONFIG = {
    "logo": "logo.png",
    "rubrica": "rubrica.png",
    "assinatura": "assinatura.png",
    "rubrica_original": "rubrica_original.png",
    "assinatura_original": "assinatura_original.png",
}


@router.get("/{nome}")
def servir_arquivo(
    tenant: Annotated[str, Path()],
    nome: Annotated[str, Path()],
    token: Annotated[str, Query(description="JWT — <img> nao manda header")],
    db: DbSession,
) -> FileResponse:
    payload = decodificar_token(token)
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido ou expirado")

    usuario = db.get(Usuario, int(payload["sub"]))
    if usuario is None or not usuario.ativo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario invalido")

    obj_tenant = db.scalar(select(Tenant).where(Tenant.slug == tenant))
    if obj_tenant is None or obj_tenant.id != usuario.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acesso negado a este tenant")

    if nome not in ARQUIVOS_CONFIG:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Arquivo desconhecido")

    caminho = dir_config(tenant) / ARQUIVOS_CONFIG[nome]
    if not caminho.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Arquivo nao encontrado")

    return FileResponse(caminho, media_type="image/png")

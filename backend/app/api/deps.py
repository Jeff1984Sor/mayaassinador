"""Dependencies compartilhadas: usuario autenticado e escopo de tenant."""

from typing import Annotated

from fastapi import Depends, HTTPException, Path, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decodificar_token
from app.db.session import get_db
from app.models import Tenant, Usuario

bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_usuario_atual(
    db: DbSession,
    cred: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Usuario:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nao autenticado")

    payload = decodificar_token(cred.credentials)
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido ou expirado")

    usuario = db.get(Usuario, int(payload["sub"]))
    if usuario is None or not usuario.ativo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario inativo ou inexistente")

    return usuario


UsuarioAtual = Annotated[Usuario, Depends(get_usuario_atual)]


def get_usuario_flex(
    db: DbSession,
    cred: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    token: Annotated[str | None, Query(description="JWT alternativo ao header")] = None,
) -> Usuario:
    """Aceita o token pelo header OU pela query string.

    Existe por um limite do navegador: <iframe> e <img> nao enviam header
    Authorization. Usado apenas para VISUALIZAR arquivos — nunca para
    escrita.
    """
    bruto = cred.credentials if cred else token
    if not bruto:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nao autenticado")

    payload = decodificar_token(bruto)
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido ou expirado")

    usuario = db.get(Usuario, int(payload["sub"]))
    if usuario is None or not usuario.ativo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario inativo ou inexistente")

    return usuario


UsuarioFlex = Annotated[Usuario, Depends(get_usuario_flex)]


def get_tenant_flex(
    tenant: Annotated[str, Path(description="Slug do tenant na URL")],
    usuario: UsuarioFlex,
    db: DbSession,
) -> Tenant:
    obj = db.scalar(select(Tenant).where(Tenant.slug == tenant))
    if obj is None or not obj.ativo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant nao encontrado")
    if obj.id != usuario.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acesso negado a este tenant")
    return obj


TenantFlex = Annotated[Tenant, Depends(get_tenant_flex)]


def get_tenant_atual(
    tenant: Annotated[str, Path(description="Slug do tenant na URL")],
    usuario: UsuarioAtual,
    db: DbSession,
) -> Tenant:
    """Valida que o slug da URL corresponde ao tenant do usuario logado.

    E aqui que o isolamento multi-tenant e garantido: nenhuma rota deve
    consultar dados sem passar por esta dependency.
    """
    obj = db.scalar(select(Tenant).where(Tenant.slug == tenant))
    if obj is None or not obj.ativo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant nao encontrado")

    if obj.id != usuario.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acesso negado a este tenant")

    return obj


TenantAtual = Annotated[Tenant, Depends(get_tenant_atual)]

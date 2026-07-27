"""Rotas de autenticacao."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession, UsuarioAtual
from app.core.config import settings
from app.core.security import criar_access_token, verificar_senha
from app.models import Usuario
from app.schemas.auth import LoginRequest, MeResponse, TokenResponse, UsuarioOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(dados: LoginRequest, db: DbSession) -> TokenResponse:
    usuario = db.scalar(select(Usuario).where(Usuario.email == dados.email.lower()))

    # mensagem generica de proposito: nao revela se o email existe
    if usuario is None or not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email ou senha invalidos")

    if not usuario.ativo:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Usuario inativo")

    token = criar_access_token(usuario.id, usuario.tenant.slug)
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        usuario=UsuarioOut.model_validate(usuario),
    )


@router.get("/me", response_model=MeResponse)
def me(usuario: UsuarioAtual) -> MeResponse:
    return MeResponse(
        id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        tenant_id=usuario.tenant_id,
        tenant_slug=usuario.tenant.slug,
        tenant_nome=usuario.tenant.nome,
    )

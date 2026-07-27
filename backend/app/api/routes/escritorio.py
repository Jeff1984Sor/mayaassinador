"""Dados do Escritorio (aba 1 das configuracoes) + upload do logo."""

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import select

from app.api.deps import DbSession, TenantAtual, UsuarioAtual
from app.core.storage import dir_config, para_relativo, remover
from app.models import Escritorio
from app.schemas.configuracao import UploadOut
from app.schemas.escritorio import EscritorioOut, EscritorioUpdate
from app.services import imagens

router = APIRouter(prefix="/{tenant}/escritorio", tags=["escritorio"])

MAX_IMAGEM_MB = 5


def _buscar(db: DbSession, tenant_id: int) -> Escritorio:
    obj = db.scalar(select(Escritorio).where(Escritorio.tenant_id == tenant_id))
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Escritorio nao cadastrado")
    return obj


def _saida(obj: Escritorio, slug: str) -> EscritorioOut:
    out = EscritorioOut.model_validate(obj)
    out.logo_url = f"/api/{slug}/arquivos/logo" if obj.logo_path else None
    return out


@router.get("", response_model=EscritorioOut)
def obter(tenant: TenantAtual, db: DbSession) -> EscritorioOut:
    return _saida(_buscar(db, tenant.id), tenant.slug)


@router.put("", response_model=EscritorioOut)
def atualizar(
    dados: EscritorioUpdate, tenant: TenantAtual, db: DbSession, _: UsuarioAtual
) -> EscritorioOut:
    obj = _buscar(db, tenant.id)
    for campo, valor in dados.model_dump().items():
        setattr(obj, campo, valor)
    db.commit()
    db.refresh(obj)
    return _saida(obj, tenant.slug)


@router.post("/logo", response_model=UploadOut, status_code=status.HTTP_201_CREATED)
async def enviar_logo(
    tenant: TenantAtual,
    db: DbSession,
    _: UsuarioAtual,
    arquivo: Annotated[UploadFile, File()],
) -> UploadOut:
    conteudo = await arquivo.read()
    if len(conteudo) > MAX_IMAGEM_MB * 1024 * 1024:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Imagem maior que {MAX_IMAGEM_MB}MB",
        )

    destino = dir_config(tenant.slug) / "logo.png"
    try:
        # o logo nao passa por remocao de fundo: pode ter cores proprias
        imagens.salvar_original(conteudo, destino)
    except imagens.ImagemInvalida as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    obj = _buscar(db, tenant.id)
    obj.logo_path = para_relativo(destino)
    db.commit()

    largura, altura = imagens.dimensoes(destino)
    return UploadOut(
        url=f"/api/{tenant.slug}/arquivos/logo", largura=largura, altura=altura
    )


@router.delete("/logo", status_code=status.HTTP_204_NO_CONTENT)
def remover_logo(tenant: TenantAtual, db: DbSession, _: UsuarioAtual) -> None:
    obj = _buscar(db, tenant.id)
    remover(obj.logo_path)
    obj.logo_path = None
    db.commit()

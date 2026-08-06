"""Dados do Escritorio (aba 1 das configuracoes) + upload do logo."""

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import select

from app.api.deps import DbSession, TenantAtual, UsuarioAtual
from app.core.storage import dir_config, para_relativo, remover
from app.models import ConfiguracaoTenant, Escritorio
from app.schemas.configuracao import EdicaoImagem, UploadOut
from app.schemas.escritorio import EscritorioOut, EscritorioUpdate
from app.services import imagens

router = APIRouter(prefix="/{tenant}/escritorio", tags=["escritorio"])

MAX_IMAGEM_MB = 5


def _buscar(db: DbSession, tenant_id: int) -> Escritorio:
    obj = db.scalar(select(Escritorio).where(Escritorio.tenant_id == tenant_id))
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Escritorio nao cadastrado")
    return obj


def _configuracao(db: DbSession, tenant_id: int) -> ConfiguracaoTenant | None:
    """A preferencia de tratar o logo mora na configuracao, junto com a
    posicao e a altura dele — mas o arquivo pertence ao escritorio."""
    return db.scalar(
        select(ConfiguracaoTenant).where(ConfiguracaoTenant.tenant_id == tenant_id)
    )


def _saida(obj: Escritorio, slug: str) -> EscritorioOut:
    out = EscritorioOut.model_validate(obj)
    if obj.logo_path:
        out.logo_url = f"/api/{slug}/arquivos/logo"
        out.logo_original_url = f"/api/{slug}/arquivos/logo_original"
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

    pasta = dir_config(tenant.slug)
    original = pasta / "logo_original.png"
    destino = pasta / "logo.png"

    # o logo so e tratado quando o escritorio pede: um fundo colorido
    # intencional seria comido pela remocao
    config = _configuracao(db, tenant.id)
    tratar = bool(config and config.logo_remover_fundo)
    tolerancia = config.logo_tolerancia if config else imagens.TOLERANCIA_PADRAO

    try:
        imagens.salvar_original(conteudo, original)
        if tratar:
            imagens.remover_fundo(conteudo, destino, tolerancia)
        else:
            imagens.salvar_original(conteudo, destino)
    except imagens.ImagemInvalida as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    obj = _buscar(db, tenant.id)
    obj.logo_path = para_relativo(destino)
    if config:
        # recorte e rotacao eram coordenadas do logo anterior
        config.logo_rotacao = 0
        config.logo_recorte = None
    db.commit()

    largura, altura = imagens.dimensoes(destino)
    base = f"/api/{tenant.slug}/arquivos"
    return UploadOut(
        url=f"{base}/logo",
        url_original=f"{base}/logo_original",
        largura=largura,
        altura=altura,
    )


@router.post("/logo/reprocessar", response_model=UploadOut)
def reprocessar_logo(
    edicao: EdicaoImagem, tenant: TenantAtual, db: DbSession, _: UsuarioAtual
) -> UploadOut:
    """Reaplica recorte, rotacao e tratamento do logo, a partir do original."""
    obj = _buscar(db, tenant.id)
    if not obj.logo_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nenhum logo enviado")

    pasta = dir_config(tenant.slug)
    original = pasta / "logo_original.png"
    destino = pasta / "logo.png"

    try:
        imagens.reprocessar(
            original, destino, imagens.ajustes_de_dict(edicao.model_dump())
        )
    except imagens.ImagemInvalida as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    config = _configuracao(db, tenant.id)
    if config:
        config.logo_remover_fundo = edicao.remover_fundo
        config.logo_tolerancia = edicao.tolerancia
        config.logo_rotacao = edicao.rotacao
        config.logo_recorte = (
            edicao.recorte.model_dump() if edicao.recorte else None
        )
    obj.logo_path = para_relativo(destino)
    db.commit()

    largura, altura = imagens.dimensoes(destino)
    base = f"/api/{tenant.slug}/arquivos"
    return UploadOut(
        url=f"{base}/logo",
        url_original=f"{base}/logo_original",
        largura=largura,
        altura=altura,
    )


@router.delete("/logo", status_code=status.HTTP_204_NO_CONTENT)
def remover_logo(tenant: TenantAtual, db: DbSession, _: UsuarioAtual) -> None:
    obj = _buscar(db, tenant.id)
    remover(obj.logo_path)
    remover(f"{tenant.slug}/config/logo_original.png")
    obj.logo_path = None
    db.commit()

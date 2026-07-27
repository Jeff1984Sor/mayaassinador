"""Configuracoes do tenant: cabecalho, rodape, imagens e SMTP."""

from typing import Annotated, Literal

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.api.deps import DbSession, TenantAtual, UsuarioAtual
from app.core.crypto import criptografar
from app.core.storage import dir_config, para_relativo, remover
from app.models import ConfiguracaoTenant, Escritorio
from app.models.configuracao import FONTES_DISPONIVEIS
from app.schemas.configuracao import (
    ConfiguracaoOut,
    ConfiguracaoUpdate,
    EmailTesteRequest,
    FonteOut,
    UploadOut,
)
from app.services import conversao, pdf_teste
from app.services import email as servico_email
from app.services import imagens
from app.services.templates_email import email_teste

router = APIRouter(prefix="/{tenant}/configuracoes", tags=["configuracoes"])

MAX_IMAGEM_MB = 5
TipoImagem = Literal["rubrica", "assinatura"]


def _buscar(db: DbSession, tenant_id: int) -> ConfiguracaoTenant:
    obj = db.scalar(
        select(ConfiguracaoTenant).where(ConfiguracaoTenant.tenant_id == tenant_id)
    )
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Configuracao nao encontrada")
    return obj


def _saida(obj: ConfiguracaoTenant, slug: str) -> ConfiguracaoOut:
    out = ConfiguracaoOut.model_validate(obj)
    base = f"/api/{slug}/arquivos"
    if obj.rubrica_path:
        out.rubrica_url = f"{base}/rubrica"
        out.rubrica_original_url = f"{base}/rubrica_original"
    if obj.assinatura_path:
        out.assinatura_url = f"{base}/assinatura"
        out.assinatura_original_url = f"{base}/assinatura_original"
    out.smtp_senha_definida = bool(obj.smtp_senha_cripto)
    return out


@router.get("/fontes", response_model=list[FonteOut])
def listar_fontes() -> list[FonteOut]:
    """Fontes realmente instaladas no servidor — alimenta os dropdowns."""
    return [FonteOut(valor=v, rotulo=r) for v, r in FONTES_DISPONIVEIS.items()]


@router.get("", response_model=ConfiguracaoOut)
def obter(tenant: TenantAtual, db: DbSession) -> ConfiguracaoOut:
    return _saida(_buscar(db, tenant.id), tenant.slug)


@router.put("", response_model=ConfiguracaoOut)
def atualizar(
    dados: ConfiguracaoUpdate, tenant: TenantAtual, db: DbSession, _: UsuarioAtual
) -> ConfiguracaoOut:
    obj = _buscar(db, tenant.id)
    valores = dados.model_dump()

    # a senha SMTP e tratada a parte: None significa "manter a atual"
    senha = valores.pop("smtp_senha", None)
    if senha:
        obj.smtp_senha_cripto = criptografar(senha)

    for campo in (
        "cabecalho_campos",
        "cabecalho_tipografia",
        "rodape_campos",
        "rodape_tipografia",
    ):
        valores[campo] = dict(valores[campo])

    for campo, valor in valores.items():
        setattr(obj, campo, valor)

    db.commit()
    db.refresh(obj)
    return _saida(obj, tenant.slug)


@router.post(
    "/imagens/{tipo}", response_model=UploadOut, status_code=status.HTTP_201_CREATED
)
async def enviar_imagem(
    tipo: TipoImagem,
    tenant: TenantAtual,
    db: DbSession,
    _: UsuarioAtual,
    arquivo: Annotated[UploadFile, File()],
) -> UploadOut:
    """Sobe rubrica ou assinatura.

    Guarda duas versoes: o original (o 'antes') e a tratada com fundo
    transparente (o 'depois'), que e a usada no PDF.
    """
    conteudo = await arquivo.read()
    if len(conteudo) > MAX_IMAGEM_MB * 1024 * 1024:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Imagem maior que {MAX_IMAGEM_MB}MB",
        )

    pasta = dir_config(tenant.slug)
    original = pasta / f"{tipo}_original.png"
    tratada = pasta / f"{tipo}.png"

    try:
        imagens.salvar_original(conteudo, original)
        imagens.remover_fundo(conteudo, tratada)
    except imagens.ImagemInvalida as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    obj = _buscar(db, tenant.id)
    setattr(obj, f"{tipo}_path", para_relativo(tratada))
    db.commit()

    largura, altura = imagens.dimensoes(tratada)
    base = f"/api/{tenant.slug}/arquivos"
    return UploadOut(
        url=f"{base}/{tipo}",
        url_original=f"{base}/{tipo}_original",
        largura=largura,
        altura=altura,
    )


@router.delete("/imagens/{tipo}", status_code=status.HTTP_204_NO_CONTENT)
def remover_imagem(
    tipo: TipoImagem, tenant: TenantAtual, db: DbSession, _: UsuarioAtual
) -> None:
    obj = _buscar(db, tenant.id)
    remover(getattr(obj, f"{tipo}_path"))
    remover(f"{tenant.slug}/config/{tipo}_original.png")
    setattr(obj, f"{tipo}_path", None)
    db.commit()


@router.post("/pdf-teste")
def gerar_pdf_teste(
    tenant: TenantAtual, db: DbSession, _: UsuarioAtual
) -> FileResponse:
    """Roda o pipeline real sobre uma peticao de exemplo.

    E a prova final de que o preview da tela e o PDF gerado batem: mesma
    montagem de cabecalho, mesma tipografia, mesmo LibreOffice.
    """
    config = _buscar(db, tenant.id)
    escritorio = db.scalar(select(Escritorio).where(Escritorio.tenant_id == tenant.id))

    try:
        caminho = pdf_teste.gerar(config, escritorio, tenant.slug)
    except conversao.FalhaConversao as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"Falha ao gerar o PDF de teste: {exc}",
        ) from exc

    return FileResponse(
        caminho, media_type="application/pdf", filename="mayaassinador-teste.pdf"
    )


@router.post("/email-teste", status_code=status.HTTP_200_OK)
def enviar_email_teste(
    dados: EmailTesteRequest, tenant: TenantAtual, db: DbSession, _: UsuarioAtual
) -> dict[str, str]:
    config = _buscar(db, tenant.id)
    escritorio = db.scalar(select(Escritorio).where(Escritorio.tenant_id == tenant.id))

    assunto, html, texto = email_teste(escritorio)
    try:
        servico_email.enviar(config, [dados.destinatario], assunto, html, texto)
    except servico_email.EmailNaoConfigurado as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except servico_email.FalhaEnvio as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    return {"mensagem": f"Email de teste enviado para {dados.destinatario}"}

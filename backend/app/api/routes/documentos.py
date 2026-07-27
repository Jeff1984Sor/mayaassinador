"""Upload e acompanhamento dos documentos.

O CRUD completo (busca, filtros, downloads, reprocessar, soft delete) chega
na F4. Aqui esta o que a F3 precisa: subir o .docx, enfileirar e acompanhar.
"""

from datetime import date, datetime, time, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, TenantAtual, TenantFlex, UsuarioAtual
from app.core.config import settings
from app.core.storage import caminho_absoluto, dir_documento, para_relativo
from app.models import ConfiguracaoTenant, Documento, StatusDocumento, TipoEvento
from app.schemas.documento import (
    DocumentoDetalhe,
    DocumentoOut,
    ListaDocumentos,
    RenomearRequest,
    ResumoDocumentos,
)
from app.services.pipeline import registrar_evento

router = APIRouter(prefix="/{tenant}/documentos", tags=["documentos"])

EXTENSAO = ".docx"
MIME_DOCX = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


@router.post("", response_model=DocumentoOut, status_code=status.HTTP_201_CREATED)
async def enviar(
    tenant: TenantAtual,
    db: DbSession,
    usuario: UsuarioAtual,
    arquivo: Annotated[UploadFile, File()],
    rubricar: Annotated[bool | None, Form()] = None,
) -> DocumentoOut:
    """Recebe o .docx, guarda o original e devolve na hora.

    O pipeline roda no worker; o frontend acompanha por polling. Nao
    processamos aqui para nao segurar o request por dezenas de segundos.
    """
    nome = (arquivo.filename or "").strip()
    if not nome.lower().endswith(EXTENSAO):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Envie um arquivo .docx. Formatos .doc, .pdf ou .odt nao sao aceitos.",
        )

    conteudo = await arquivo.read()
    if not conteudo:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Arquivo vazio")
    if len(conteudo) > settings.max_upload_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Arquivo maior que {settings.MAX_UPLOAD_MB}MB",
        )
    # .docx e um zip: os dois primeiros bytes sao sempre "PK"
    if conteudo[:2] != b"PK":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "O arquivo nao parece ser um .docx valido",
        )

    if rubricar is None:
        config = db.scalar(
            select(ConfiguracaoTenant).where(ConfiguracaoTenant.tenant_id == tenant.id)
        )
        rubricar = bool(config and config.rubricar_por_padrao)

    documento = Documento(
        tenant_id=tenant.id,
        usuario_id=usuario.id,
        nome_original=nome,
        status=StatusDocumento.ENVIADO,
        rubricado=bool(rubricar),
        tamanho=len(conteudo),
    )
    db.add(documento)
    db.flush()  # precisa do id para montar a pasta

    destino = dir_documento(tenant.slug, documento.id) / "original.docx"
    destino.write_bytes(conteudo)
    documento.caminho_original = para_relativo(destino)

    registrar_evento(db, documento.id, TipoEvento.CRIADO, nome)
    db.commit()
    db.refresh(documento)

    return DocumentoOut.model_validate(documento)


@router.get("", response_model=ListaDocumentos)
def listar(
    tenant: TenantAtual,
    db: DbSession,
    _: UsuarioAtual,
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=100)] = 20,
    busca: Annotated[str | None, Query(description="Trecho do nome do arquivo")] = None,
    status_: Annotated[StatusDocumento | None, Query(alias="status")] = None,
    de: Annotated[date | None, Query(description="Data inicial (inclusive)")] = None,
    ate: Annotated[date | None, Query(description="Data final (inclusive)")] = None,
) -> ListaDocumentos:
    base = select(Documento).where(
        Documento.tenant_id == tenant.id, Documento.deleted_at.is_(None)
    )

    if busca:
        base = base.where(Documento.nome_original.ilike(f"%{busca.strip()}%"))
    if status_:
        base = base.where(Documento.status == status_)
    if de:
        base = base.where(Documento.criado_em >= datetime.combine(de, time.min))
    if ate:
        # ate o fim do dia — senao "ate hoje" excluiria tudo de hoje
        base = base.where(Documento.criado_em <= datetime.combine(ate, time.max))

    total = db.scalar(
        select(func.count()).select_from(base.subquery())
    ) or 0

    itens = db.scalars(
        base.order_by(Documento.criado_em.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
    ).all()

    return ListaDocumentos(
        itens=[DocumentoOut.model_validate(d) for d in itens],
        total=total,
        pagina=pagina,
        paginas=max(1, -(-total // por_pagina)),
    )


@router.get("/resumo", response_model=ResumoDocumentos)
def resumo(tenant: TenantAtual, db: DbSession, _: UsuarioAtual) -> ResumoDocumentos:
    """Cards do topo da tela 4.2."""
    linhas = db.execute(
        select(Documento.status, func.count())
        .where(Documento.tenant_id == tenant.id, Documento.deleted_at.is_(None))
        .group_by(Documento.status)
    ).all()
    contagem = {status_: qtd for status_, qtd in linhas}

    return ResumoDocumentos(
        total=sum(contagem.values()),
        prontos=contagem.get(StatusDocumento.PRONTO, 0),
        enviados_email=contagem.get(StatusDocumento.ENVIADO_EMAIL, 0),
        com_erro=contagem.get(StatusDocumento.ERRO, 0),
        processando=contagem.get(StatusDocumento.ENVIADO, 0)
        + contagem.get(StatusDocumento.PROCESSANDO, 0),
    )


@router.get("/{documento_id}", response_model=DocumentoDetalhe)
def obter(
    documento_id: int, tenant: TenantAtual, db: DbSession, _: UsuarioAtual
) -> DocumentoDetalhe:
    documento = db.scalar(
        select(Documento)
        .options(selectinload(Documento.eventos))
        .where(
            Documento.id == documento_id,
            Documento.tenant_id == tenant.id,
            Documento.deleted_at.is_(None),
        )
    )
    if documento is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento nao encontrado")

    return DocumentoDetalhe.model_validate(documento)


def _buscar(db: DbSession, tenant_id: int, documento_id: int) -> Documento:
    documento = db.scalar(
        select(Documento).where(
            Documento.id == documento_id,
            Documento.tenant_id == tenant_id,
            Documento.deleted_at.is_(None),
        )
    )
    if documento is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento nao encontrado")
    return documento


@router.get("/{documento_id}/arquivo/{tipo}")
def baixar(
    documento_id: int,
    tipo: Literal["final", "original"],
    tenant: TenantFlex,
    db: DbSession,
    inline: Annotated[bool, Query(description="Exibir no navegador")] = False,
) -> FileResponse:
    """Download do PDF final ou do .docx original.

    Usa TenantFlex porque o preview inline roda dentro de um <iframe>, que
    nao envia header Authorization.
    """
    documento = _buscar(db, tenant.id, documento_id)

    if tipo == "final":
        relativo = documento.caminho_final
        if not relativo:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "O PDF final ainda nao foi gerado para este documento",
            )
        midia = "application/pdf"
        nome = f"{documento.nome_original.rsplit('.', 1)[0]}.pdf"
    else:
        relativo = documento.caminho_original
        if not relativo:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Arquivo original ausente")
        midia = MIME_DOCX
        nome = documento.nome_original

    caminho = caminho_absoluto(relativo)
    if not caminho.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Arquivo nao encontrado no storage")

    if not inline:
        registrar_evento(db, documento.id, TipoEvento.DOWNLOAD, tipo)
        db.commit()

    return FileResponse(
        caminho,
        media_type=midia,
        # inline abre no visualizador do navegador; attachment forca download
        headers={
            "Content-Disposition": f'{"inline" if inline else "attachment"}; filename="{nome}"'
        },
    )


@router.post("/{documento_id}/reprocessar", response_model=DocumentoOut)
def reprocessar(
    documento_id: int, tenant: TenantAtual, db: DbSession, _: UsuarioAtual
) -> DocumentoOut:
    """Devolve o documento para a fila.

    Util depois de mudar cabecalho, rodape ou assinatura: o original esta
    intacto no storage, entao o pipeline roda de novo do zero.
    """
    documento = _buscar(db, tenant.id, documento_id)

    if documento.status in (StatusDocumento.ENVIADO, StatusDocumento.PROCESSANDO):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "O documento ja esta na fila de processamento"
        )
    if not documento.caminho_original:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Documento sem arquivo original para reprocessar"
        )

    documento.status = StatusDocumento.ENVIADO
    documento.tentativas = 0  # nova ordem: o contador de falhas recomeca
    documento.erro_msg = None
    documento.processando_desde = None
    documento.processado_em = None

    registrar_evento(db, documento.id, TipoEvento.REPROCESSADO)
    db.commit()
    db.refresh(documento)

    return DocumentoOut.model_validate(documento)


@router.patch("/{documento_id}", response_model=DocumentoOut)
def renomear(
    documento_id: int,
    dados: RenomearRequest,
    tenant: TenantAtual,
    db: DbSession,
    _: UsuarioAtual,
) -> DocumentoOut:
    """Renomeia o documento na listagem.

    Muda apenas o rotulo no banco — o arquivo no storage continua sendo o
    que o cliente enviou, com o mesmo hash.
    """
    documento = _buscar(db, tenant.id, documento_id)
    nome = dados.nome_original.strip()
    if not nome.lower().endswith(EXTENSAO):
        nome = f"{nome}{EXTENSAO}"

    documento.nome_original = nome
    db.commit()
    db.refresh(documento)

    return DocumentoOut.model_validate(documento)


@router.delete("/{documento_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(
    documento_id: int, tenant: TenantAtual, db: DbSession, _: UsuarioAtual
) -> None:
    """Soft delete.

    Os arquivos permanecem no storage: o anexo original do cliente e
    sagrado e a trilha de auditoria precisa continuar verificavel.
    """
    documento = _buscar(db, tenant.id, documento_id)
    documento.deleted_at = datetime.now(timezone.utc)
    registrar_evento(db, documento.id, TipoEvento.EXCLUIDO)
    db.commit()

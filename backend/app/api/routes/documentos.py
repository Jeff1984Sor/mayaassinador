"""Upload e acompanhamento dos documentos.

O CRUD completo (busca, filtros, downloads, reprocessar, soft delete) chega
na F4. Aqui esta o que a F3 precisa: subir o .docx, enfileirar e acompanhar.
"""

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, TenantAtual, UsuarioAtual
from app.core.config import settings
from app.core.storage import dir_documento, para_relativo
from app.models import ConfiguracaoTenant, Documento, StatusDocumento, TipoEvento
from app.schemas.documento import (
    DocumentoDetalhe,
    DocumentoOut,
    ListaDocumentos,
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
) -> ListaDocumentos:
    base = select(Documento).where(
        Documento.tenant_id == tenant.id, Documento.deleted_at.is_(None)
    )

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

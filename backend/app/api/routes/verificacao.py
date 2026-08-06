"""Pagina publica de verificacao — o destino do QR carimbado no PDF.

Sem autenticacao e sem tenant na URL, de proposito: quem recebe o
documento nao tem login no sistema e nao sabe de que escritorio ele veio.
O codigo de 8 hex e a unica chave.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.models import Documento, Escritorio, StatusDocumento
from app.schemas.verificacao import VerificacaoOut

router = APIRouter(prefix="/verificar", tags=["verificacao"])

# o codigo e gerado com secrets.token_hex(4).upper() e ditado por telefone
# como AAAA-BBBB; aceitamos com ou sem o hifen, em qualquer caixa
TAMANHO_CODIGO = 8


def _normalizar(codigo: str) -> str:
    return codigo.replace("-", "").replace(" ", "").strip().upper()


@router.get("/{codigo}", response_model=VerificacaoOut)
def verificar(
    codigo: Annotated[str, Path(max_length=20)], db: DbSession
) -> VerificacaoOut:
    """Confirma a autenticidade de um documento a partir do codigo do QR."""
    limpo = _normalizar(codigo)

    # a mesma resposta para codigo malformado, inexistente e apagado: uma
    # mensagem diferente para cada caso contaria a quem estivesse varrendo
    # codigos quais existem
    nao_encontrado = HTTPException(
        status.HTTP_404_NOT_FOUND,
        "Documento nao encontrado. Confira o codigo impresso no rodape.",
    )
    if len(limpo) != TAMANHO_CODIGO or not all(c in "0123456789ABCDEF" for c in limpo):
        raise nao_encontrado

    documento = db.scalar(
        select(Documento).where(Documento.codigo_verificacao == limpo)
    )
    if (
        documento is None
        or documento.deleted_at is not None
        or documento.status
        not in (StatusDocumento.PRONTO, StatusDocumento.ENVIADO_EMAIL)
    ):
        raise nao_encontrado

    escritorio = db.scalar(
        select(Escritorio).where(Escritorio.tenant_id == documento.tenant_id)
    )

    return VerificacaoOut(
        codigo=f"{limpo[:4]}-{limpo[4:]}",
        escritorio=escritorio.razao_social if escritorio else "—",
        signatario=escritorio.signatario_nome if escritorio else None,
        signatario_oab=escritorio.signatario_oab if escritorio else None,
        nome_arquivo=documento.nome_original,
        paginas=documento.paginas,
        assinado_em=documento.processado_em,
        hash_sha256=documento.hash_sha256,
    )

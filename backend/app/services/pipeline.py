"""Orquestracao do pipeline de documentos (passos 3 a 8 do fluxo).

    original.docx -> cabecalho/rodape -> PDF -> rubrica -> assinatura
                  -> hash + QR -> final.pdf

Cada etapa registra um evento na trilha de auditoria. Se algo falha, o
documento vai para status ERRO com a mensagem visivel para o usuario — o
advogado precisa saber o que deu errado, nao ver "erro interno".
"""

import hashlib
import secrets
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.storage import caminho_absoluto, dir_config, dir_documento, para_relativo
from app.models import (
    ConfiguracaoTenant,
    Documento,
    Escritorio,
    EventoDocumento,
    StatusDocumento,
    Tenant,
    TipoEvento,
)
from app.services import conversao, docx_timbre, pdf_carimbo


class FalhaPipeline(Exception):
    pass


def registrar_evento(
    db: Session, documento_id: int, tipo: TipoEvento, detalhe: str | None = None
) -> None:
    db.add(EventoDocumento(documento_id=documento_id, tipo=tipo, detalhe=detalhe))
    db.flush()


def gerar_codigo_verificacao(db: Session) -> str:
    """Codigo curto e unico. 8 hex = 4 bilhoes de combinacoes; colisao e
    improvavel, mas conferimos mesmo assim."""
    for _ in range(10):
        codigo = secrets.token_hex(4).upper()
        existe = db.scalar(
            select(Documento.id).where(Documento.codigo_verificacao == codigo)
        )
        if existe is None:
            return codigo
    raise FalhaPipeline("Nao foi possivel gerar codigo de verificacao")


def formatar_codigo(codigo: str) -> str:
    """8 caracteres viram AAAA-BBBB, mais facil de ditar por telefone."""
    return f"{codigo[:4]}-{codigo[4:]}"


def calcular_hash(caminho: Path) -> str:
    sha = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(bloco)
    return sha.hexdigest()


def _imagem(config: ConfiguracaoTenant, campo: str) -> Path | None:
    relativo = getattr(config, campo, None)
    if not relativo:
        return None
    try:
        caminho = caminho_absoluto(relativo)
    except ValueError:
        return None
    return caminho if caminho.exists() else None


def processar(db: Session, documento: Documento) -> None:
    """Executa o pipeline inteiro. Levanta FalhaPipeline em caso de erro."""
    tenant = db.get(Tenant, documento.tenant_id)
    if tenant is None:
        raise FalhaPipeline("Tenant do documento nao encontrado")

    config = db.scalar(
        select(ConfiguracaoTenant).where(ConfiguracaoTenant.tenant_id == tenant.id)
    )
    if config is None:
        raise FalhaPipeline("Configuracao do tenant nao encontrada")

    escritorio = db.scalar(select(Escritorio).where(Escritorio.tenant_id == tenant.id))

    if not documento.caminho_original:
        raise FalhaPipeline("Documento sem arquivo original")

    original = caminho_absoluto(documento.caminho_original)
    if not original.exists():
        raise FalhaPipeline("Arquivo original nao encontrado no storage")

    pasta = dir_documento(tenant.slug, documento.id)
    timbrado = pasta / "timbrado.docx"
    convertido = pasta / "convertido.pdf"
    final = pasta / "final.pdf"

    logo = dir_config(tenant.slug) / "logo.png"

    # ---- 3 e 4: cabecalho e rodape ----
    try:
        docx_timbre.aplicar(
            origem=original,
            destino=timbrado,
            config=config,
            escritorio=escritorio,
            logo=logo if logo.exists() else None,
        )
    except Exception as exc:  # noqa: BLE001 — python-docx levanta varios tipos
        raise FalhaPipeline(f"Falha ao aplicar cabecalho/rodape: {exc}") from exc

    registrar_evento(db, documento.id, TipoEvento.CABECALHO_APLICADO)
    registrar_evento(db, documento.id, TipoEvento.RODAPE_APLICADO)

    # ---- 5: conversao ----
    try:
        conversao.docx_para_pdf(timbrado, convertido)
    except conversao.FalhaConversao as exc:
        raise FalhaPipeline(str(exc)) from exc

    registrar_evento(db, documento.id, TipoEvento.CONVERTIDO_PDF)

    # ---- 6, 7 e 8: rubrica, assinatura, QR ----
    codigo = documento.codigo_verificacao or gerar_codigo_verificacao(db)
    documento.codigo_verificacao = codigo
    url_verificacao = f"{settings.PUBLIC_BASE_URL}/verificar/{codigo}"

    rubrica = _imagem(config, "rubrica_path") if documento.rubricado else None
    assinatura = _imagem(config, "assinatura_path")

    try:
        paginas = pdf_carimbo.carimbar(
            origem=convertido,
            destino=final,
            rubrica=rubrica,
            assinatura=assinatura,
            url_verificacao=url_verificacao,
            codigo=formatar_codigo(codigo),
        )
    except pdf_carimbo.FalhaCarimbo as exc:
        raise FalhaPipeline(str(exc)) from exc

    if rubrica:
        registrar_evento(db, documento.id, TipoEvento.RUBRICA_APLICADA, f"{paginas} paginas")
    if assinatura:
        registrar_evento(db, documento.id, TipoEvento.ASSINATURA_APLICADA)

    # ---- hash do arquivo final ----
    documento.hash_sha256 = calcular_hash(final)
    registrar_evento(db, documento.id, TipoEvento.HASH_GERADO, documento.hash_sha256[:16])

    documento.caminho_final = para_relativo(final)
    documento.paginas = paginas
    documento.tamanho = final.stat().st_size
    documento.status = StatusDocumento.PRONTO
    documento.processado_em = datetime.now(timezone.utc)
    documento.erro_msg = None

    registrar_evento(db, documento.id, TipoEvento.PRONTO)

    # os intermediarios nao interessam a ninguem depois do PDF pronto
    timbrado.unlink(missing_ok=True)
    convertido.unlink(missing_ok=True)

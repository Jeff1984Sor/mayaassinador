"""Worker do pipeline — fila na propria tabela `documentos`.

Decisao da F0: nao usamos Redis (o unico do prod2 pertence ao container do
Evolution API). `FOR UPDATE SKIP LOCKED` da exclusao mutua entre processos
sem infra extra, e o indice parcial ix_documentos_fila evita varrer a tabela.

Concorrencia 1: cada LibreOffice headless consome ~400MB e a VM nao tem
swap. Rodar varios em paralelo derrubaria os outros servicos por OOM.

Roda como servico separado da API, para que uma conversao longa nunca
segure um worker HTTP.
"""

import logging
import signal
import time
from datetime import datetime, timezone
from types import FrameType

from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import Documento, StatusDocumento, TipoEvento
from app.services.pipeline import FalhaPipeline, processar, registrar_evento

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [worker] %(message)s",
)
log = logging.getLogger(__name__)

MAX_TENTATIVAS = 3
_rodando = True


def _parar(signum: int, _frame: FrameType | None) -> None:
    global _rodando
    log.info("sinal %s recebido, encerrando apos o documento atual", signum)
    _rodando = False


def _proximo() -> int | None:
    """Reserva um documento da fila e devolve o id.

    A transacao e curta de proposito: pega o lock, marca PROCESSANDO e
    solta. O processamento pesado acontece fora dela, senao a conexao
    ficaria aberta por minutos segurando o lock.
    """
    db = SessionLocal()
    try:
        documento = db.scalar(
            select(Documento)
            .where(
                Documento.status == StatusDocumento.ENVIADO,
                Documento.deleted_at.is_(None),
                Documento.tentativas < MAX_TENTATIVAS,
            )
            .order_by(Documento.criado_em)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if documento is None:
            return None

        documento.status = StatusDocumento.PROCESSANDO
        documento.processando_desde = datetime.now(timezone.utc)
        documento.tentativas += 1
        registrar_evento(db, documento.id, TipoEvento.PROCESSAMENTO_INICIADO)
        db.commit()
        return documento.id
    finally:
        db.close()


def _processar(documento_id: int) -> None:
    db = SessionLocal()
    try:
        documento = db.get(Documento, documento_id)
        if documento is None:
            return

        log.info("processando documento %s (%s)", documento.id, documento.nome_original)
        try:
            processar(db, documento)
            db.commit()
            log.info("documento %s pronto", documento.id)
        except FalhaPipeline as exc:
            db.rollback()
            _marcar_erro(db, documento_id, str(exc))
        except Exception as exc:  # noqa: BLE001 — o worker nao pode morrer
            db.rollback()
            log.exception("erro inesperado no documento %s", documento_id)
            _marcar_erro(db, documento_id, f"Erro inesperado: {exc}")
    finally:
        db.close()


def _marcar_erro(db, documento_id: int, mensagem: str) -> None:
    documento = db.get(Documento, documento_id)
    if documento is None:
        return

    if documento.tentativas >= MAX_TENTATIVAS:
        documento.status = StatusDocumento.ERRO
        documento.erro_msg = mensagem
        registrar_evento(db, documento.id, TipoEvento.ERRO, mensagem[:500])
        log.error("documento %s falhou definitivamente: %s", documento_id, mensagem)
    else:
        # volta para a fila: erros de conversao costumam ser transitorios
        documento.status = StatusDocumento.ENVIADO
        documento.erro_msg = mensagem
        log.warning(
            "documento %s falhou (tentativa %s/%s): %s",
            documento_id,
            documento.tentativas,
            MAX_TENTATIVAS,
            mensagem,
        )
    db.commit()


def main() -> None:
    signal.signal(signal.SIGTERM, _parar)
    signal.signal(signal.SIGINT, _parar)

    log.info(
        "worker iniciado — poll %ss, soffice em %s",
        settings.WORKER_POLL_SECONDS,
        settings.SOFFICE_BIN,
    )

    while _rodando:
        try:
            documento_id = _proximo()
        except Exception:  # noqa: BLE001 — banco fora do ar nao mata o worker
            log.exception("falha ao consultar a fila")
            time.sleep(settings.WORKER_POLL_SECONDS)
            continue

        if documento_id is None:
            time.sleep(settings.WORKER_POLL_SECONDS)
            continue

        _processar(documento_id)

    log.info("worker encerrado")


if __name__ == "__main__":
    main()

"""Schema da pagina publica de verificacao.

Esta e a UNICA resposta do sistema que sai sem autenticacao — qualquer um
com o codigo do QR pode le-la. Por isso ela carrega so o que prova a
autenticidade do documento, e nada sobre o cliente: nem destinatario, nem
email, nem historico de envios, nem link para baixar o arquivo. Quem
verifica ja tem o PDF em maos; o que falta e saber se ele e legitimo.
"""

from datetime import datetime

from pydantic import BaseModel


class VerificacaoOut(BaseModel):
    codigo: str
    autentico: bool = True

    # quem assinou
    escritorio: str
    signatario: str | None = None
    signatario_oab: str | None = None

    # o que assinou
    nome_arquivo: str
    paginas: int | None = None
    assinado_em: datetime | None = None

    # a prova: quem tem o PDF pode conferir o sha256 por conta propria
    hash_sha256: str | None = None

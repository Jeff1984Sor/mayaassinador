"""Criptografia simetrica (Fernet) para segredos guardados no banco.

Usado na F2 para a senha SMTP: ela precisa ser recuperada em texto puro
na hora de enviar o email, entao hash nao serve — tem que ser cifra
reversivel com a chave vivendo apenas no .env.
"""

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

_fernet = Fernet(settings.FERNET_KEY.encode())


def criptografar(valor: str) -> str:
    return _fernet.encrypt(valor.encode()).decode()


def descriptografar(valor_cripto: str) -> str | None:
    """Retorna None se o valor nao puder ser decifrado (ex: FERNET_KEY trocada)."""
    try:
        return _fernet.decrypt(valor_cripto.encode()).decode()
    except (InvalidToken, ValueError):
        return None

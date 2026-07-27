"""Helpers de storage em disco.

Layout dentro de STORAGE_ROOT:
    {tenant}/config/            -> logo, rubrica e assinatura do escritorio
    {tenant}/documentos/{id}/   -> original.docx e final.pdf (F3)

Os caminhos guardados no banco sao SEMPRE relativos ao STORAGE_ROOT, para
que mover o storage nao exija migration.
"""

from pathlib import Path

from app.core.config import settings


def raiz_tenant(slug: str) -> Path:
    return settings.STORAGE_ROOT / slug


def dir_config(slug: str) -> Path:
    caminho = raiz_tenant(slug) / "config"
    caminho.mkdir(parents=True, exist_ok=True)
    return caminho


def dir_documento(slug: str, documento_id: int) -> Path:
    caminho = raiz_tenant(slug) / "documentos" / str(documento_id)
    caminho.mkdir(parents=True, exist_ok=True)
    return caminho


def caminho_absoluto(relativo: str) -> Path:
    """Converte o caminho relativo do banco em caminho absoluto.

    Barreira contra path traversal: o resultado tem que continuar dentro
    do STORAGE_ROOT, senao um valor adulterado no banco poderia servir
    /etc/passwd por um endpoint de download.
    """
    destino = (settings.STORAGE_ROOT / relativo).resolve()
    raiz = settings.STORAGE_ROOT.resolve()
    if not destino.is_relative_to(raiz):
        raise ValueError("Caminho fora do storage")
    return destino


def para_relativo(absoluto: Path) -> str:
    return str(absoluto.resolve().relative_to(settings.STORAGE_ROOT.resolve()))


def remover(relativo: str | None) -> None:
    """Apaga um arquivo do storage, ignorando se ja nao existe."""
    if not relativo:
        return
    try:
        caminho_absoluto(relativo).unlink(missing_ok=True)
    except ValueError:
        pass

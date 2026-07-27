"""Conversao DOCX -> PDF via LibreOffice headless."""

import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from app.core.config import settings


class FalhaConversao(Exception):
    pass


def docx_para_pdf(origem: Path, destino: Path) -> Path:
    """Converte e move o resultado para `destino`.

    Cada chamada usa um perfil proprio (-env:UserInstallation). Sem isso, uma
    segunda conversao simultanea encontra o profile travado e falha em
    silencio, devolvendo exit 0 sem gerar PDF.
    """
    if not origem.exists():
        raise FalhaConversao("Arquivo de origem nao encontrado")

    with tempfile.TemporaryDirectory(prefix="mayaassinador_") as tmp:
        tmp_path = Path(tmp)
        perfil = tmp_path / f"perfil_{uuid.uuid4().hex}"

        comando = [
            settings.SOFFICE_BIN,
            "--headless",
            "--norestore",
            "--nolockcheck",
            f"-env:UserInstallation=file://{perfil}",
            "--convert-to",
            "pdf:writer_pdf_Export",
            "--outdir",
            str(tmp_path),
            str(origem),
        ]

        try:
            resultado = subprocess.run(
                comando,
                capture_output=True,
                text=True,
                timeout=settings.SOFFICE_TIMEOUT,
                # HOME valido: o soffice aborta se nao puder escrever em ~
                cwd=str(tmp_path),
            )
        except subprocess.TimeoutExpired as exc:
            raise FalhaConversao(
                f"LibreOffice excedeu {settings.SOFFICE_TIMEOUT}s na conversao"
            ) from exc
        except FileNotFoundError as exc:
            raise FalhaConversao(
                f"LibreOffice nao encontrado em {settings.SOFFICE_BIN}"
            ) from exc

        gerado = tmp_path / f"{origem.stem}.pdf"
        if not gerado.exists():
            detalhe = (resultado.stderr or resultado.stdout or "").strip()[:500]
            raise FalhaConversao(
                f"Conversao nao produziu PDF (exit {resultado.returncode}). {detalhe}"
            )

        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(gerado), str(destino))

    return destino

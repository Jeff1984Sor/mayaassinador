"""Envio de email via SMTP do tenant."""

import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from app.core.crypto import descriptografar
from app.models import ConfiguracaoTenant


class EmailNaoConfigurado(Exception):
    pass


class FalhaEnvio(Exception):
    pass


def _credenciais(config: ConfiguracaoTenant) -> tuple[str, int, str, str]:
    if not config.smtp_host or not config.smtp_porta or not config.smtp_usuario:
        raise EmailNaoConfigurado("Configure host, porta e usuario do SMTP")
    if not config.smtp_senha_cripto:
        raise EmailNaoConfigurado("Senha SMTP nao cadastrada")

    senha = descriptografar(config.smtp_senha_cripto)
    if senha is None:
        raise EmailNaoConfigurado(
            "Nao foi possivel decifrar a senha SMTP. Cadastre-a novamente."
        )
    return config.smtp_host, config.smtp_porta, config.smtp_usuario, senha


def enviar(
    config: ConfiguracaoTenant,
    destinatarios: list[str],
    assunto: str,
    corpo_html: str,
    corpo_texto: str | None = None,
    anexos: list[Path] | None = None,
    remetente_nome: str | None = None,
    remetente_email: str | None = None,
) -> None:
    """Envia o email. Levanta FalhaEnvio com mensagem legivel em caso de erro.

    remetente_email troca o endereco do From. Cuidado: Gmail e Microsoft 365
    recusam enviar em nome de um endereco que nao seja o autenticado (ou um
    alias verificado). Por isso o padrao continua sendo o usuario do SMTP.
    """
    host, porta, usuario, senha = _credenciais(config)

    msg = EmailMessage()
    msg["Subject"] = assunto
    nome = remetente_nome or config.email_remetente_nome or usuario
    endereco = remetente_email or usuario
    msg["From"] = f"{nome} <{endereco}>"
    msg["To"] = ", ".join(destinatarios)
    if endereco != usuario:
        # se o provedor reescrever o From, a resposta ainda volta pro lugar certo
        msg["Reply-To"] = endereco

    msg.set_content(corpo_texto or "Seu leitor de email nao suporta HTML.")
    msg.add_alternative(corpo_html, subtype="html")

    for anexo in anexos or []:
        msg.add_attachment(
            anexo.read_bytes(),
            maintype="application",
            subtype="pdf",
            filename=anexo.name,
        )

    contexto = ssl.create_default_context()
    try:
        if porta == 465:
            with smtplib.SMTP_SSL(host, porta, context=contexto, timeout=30) as s:
                s.login(usuario, senha)
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, porta, timeout=30) as s:
                if config.smtp_tls:
                    s.starttls(context=contexto)
                s.login(usuario, senha)
                s.send_message(msg)
    except smtplib.SMTPAuthenticationError as exc:
        raise FalhaEnvio(
            "Usuario ou senha do SMTP recusados. Se for Gmail, use uma "
            "senha de app, nao a senha da conta."
        ) from exc
    except smtplib.SMTPException as exc:
        raise FalhaEnvio(f"Erro do servidor SMTP: {exc}") from exc
    except (OSError, ssl.SSLError) as exc:
        raise FalhaEnvio(f"Nao foi possivel conectar em {host}:{porta} — {exc}") from exc

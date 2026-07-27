"""Templates HTML dos emails, com a identidade do escritorio.

Email nao suporta CSS externo nem flexbox de forma confiavel: e tudo
inline e baseado em tabelas, de proposito.
"""

from html import escape

from app.models import Escritorio

NAVY = "#1E2D6B"
CINZA = "#F7F8FC"
TEXTO = "#0F1729"


def _rodape(escritorio: Escritorio | None) -> str:
    if escritorio is None:
        return ""
    linhas = [escape(escritorio.razao_social)]
    if escritorio.oab_numero:
        seccional = f"/{escape(escritorio.oab_seccional)}" if escritorio.oab_seccional else ""
        linhas.append(f"OAB {escape(escritorio.oab_numero)}{seccional}")
    if escritorio.telefone:
        linhas.append(escape(escritorio.telefone))
    if escritorio.email:
        linhas.append(escape(escritorio.email))
    return " · ".join(linhas)


def envelope(escritorio: Escritorio | None, titulo: str, corpo_html: str) -> str:
    """Monta o email completo em volta do conteudo."""
    nome = escape(escritorio.razao_social) if escritorio else "MayaAssinador"
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width"></head>
<body style="margin:0;padding:0;background:{CINZA};font-family:Arial,Helvetica,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{CINZA};padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
             style="max-width:560px;background:#fff;border-radius:12px;overflow:hidden;
                    box-shadow:0 1px 3px rgba(15,23,41,.08);">
        <tr><td style="background:{NAVY};padding:20px 28px;">
          <span style="color:#fff;font-size:16px;font-weight:bold;">{nome}</span>
        </td></tr>
        <tr><td style="padding:28px;color:{TEXTO};font-size:15px;line-height:1.6;">
          <h1 style="margin:0 0 16px;font-size:18px;color:{NAVY};">{escape(titulo)}</h1>
          {corpo_html}
        </td></tr>
        <tr><td style="padding:16px 28px;border-top:1px solid #eef0f6;
                       color:#8a90a3;font-size:12px;line-height:1.5;">
          {_rodape(escritorio)}
        </td></tr>
      </table>
      <p style="margin:16px 0 0;color:#a0a6b8;font-size:11px;">
        Enviado por MayaAssinador
      </p>
    </td></tr>
  </table>
</body>
</html>"""


def email_teste(escritorio: Escritorio | None) -> tuple[str, str, str]:
    """Retorna (assunto, html, texto) do email de teste da tela de configuracoes."""
    assunto = "MayaAssinador — email de teste"
    html = envelope(
        escritorio,
        "Configuracao de email validada",
        "<p>Se voce esta lendo isto, o SMTP do escritorio esta funcionando "
        "e os documentos assinados poderao ser enviados por aqui.</p>"
        "<p style='margin-bottom:0;color:#8a90a3;font-size:13px;'>"
        "Esta e uma mensagem automatica de teste.</p>",
    )
    texto = (
        "Configuracao de email validada.\n\n"
        "Se voce esta lendo isto, o SMTP do escritorio esta funcionando."
    )
    return assunto, html, texto

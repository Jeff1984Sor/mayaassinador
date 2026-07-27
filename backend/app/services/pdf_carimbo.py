"""Carimba rubrica, assinatura e QR de verificacao no PDF.

Estrategia: gerar um overlay transparente com reportlab, do tamanho exato
de cada pagina, e mesclar com pypdf. Assim o conteudo original nunca e
redesenhado — nenhum risco de perder formatacao.
"""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import qrcode
from pypdf import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.services import ancora_pdf

# medidas em pontos (1pt = 1/72")
MARGEM = 28
RUBRICA_ALTURA = 26
RUBRICA_LARGURA_MAX = 90
ASSINATURA_ALTURA = 58
ASSINATURA_LARGURA_MAX = 200
QR_LADO = 42


class FalhaCarimbo(Exception):
    pass


def _dimensoes_proporcionais(
    caminho: Path, altura_alvo: float, largura_max: float
) -> tuple[float, float]:
    imagem = ImageReader(str(caminho))
    largura, altura = imagem.getSize()
    escala = altura_alvo / altura
    if largura * escala > largura_max:
        escala = largura_max / largura
    return largura * escala, altura * escala


def _gerar_qr(conteudo: str) -> BytesIO:
    qr = qrcode.QRCode(box_size=10, border=1)
    qr.add_data(conteudo)
    qr.make(fit=True)
    imagem = qr.make_image(fill_color="#0F1729", back_color="white")
    buffer = BytesIO()
    imagem.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


@dataclass(frozen=True)
class PosicaoAssinatura:
    """Onde carimbar a assinatura.

    modo "ancora": procura `texto` no PDF e posiciona `relativa` (acima ou
    abaixo) da linha encontrada, com `deslocamento` de folga. Se o texto nao
    for encontrado, cai na posicao fixa — nunca sai documento sem assinatura.
    """

    modo: str = "fixa"
    texto: str | None = None
    relativa: str = "abaixo"
    deslocamento: int = 6


def _coordenada_assinatura(
    pagina,
    posicao: PosicaoAssinatura,
    largura_pagina: float,
    largura_img: float,
    altura_img: float,
) -> tuple[float, float, bool]:
    """Devolve (x, y, ancorou)."""
    if posicao.modo == "ancora" and posicao.texto:
        ancora = ancora_pdf.localizar(pagina, posicao.texto)
        if ancora is not None:
            if posicao.relativa == "acima":
                y = ancora.y + ancora.altura + posicao.deslocamento
            else:
                y = ancora.y - posicao.deslocamento - altura_img

            # alinha o centro da imagem com o inicio da linha encontrada,
            # que e onde o nome comeca a ser escrito
            x = ancora.x
            # nao deixa vazar da pagina
            x = max(MARGEM, min(x, largura_pagina - MARGEM - largura_img))
            y = max(MARGEM, y)
            return x, y, True

    return (largura_pagina - largura_img) / 2, MARGEM + 46, False


def _overlay(
    largura: float,
    altura: float,
    rubrica: Path | None,
    assinatura: Path | None,
    qr_buffer: BytesIO | None,
    codigo: str | None,
    coordenada_assinatura: tuple[float, float] | None = None,
) -> BytesIO:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(largura, altura))

    if rubrica:
        w, h = _dimensoes_proporcionais(rubrica, RUBRICA_ALTURA, RUBRICA_LARGURA_MAX)
        c.drawImage(
            ImageReader(str(rubrica)),
            largura - MARGEM - w,
            MARGEM,
            width=w,
            height=h,
            mask="auto",  # respeita o alpha gerado pelo Pillow
        )

    if assinatura:
        w, h = _dimensoes_proporcionais(
            assinatura, ASSINATURA_ALTURA, ASSINATURA_LARGURA_MAX
        )
        x, y = coordenada_assinatura or ((largura - w) / 2, MARGEM + 46)
        c.drawImage(
            ImageReader(str(assinatura)), x, y, width=w, height=h, mask="auto"
        )

    if qr_buffer and codigo:
        c.drawImage(
            ImageReader(qr_buffer), MARGEM, MARGEM, width=QR_LADO, height=QR_LADO
        )
        c.setFont("Helvetica", 5.5)
        c.setFillColorRGB(0.35, 0.37, 0.44)
        c.drawString(MARGEM + QR_LADO + 5, MARGEM + QR_LADO - 8, "Verifique a autenticidade")
        c.setFont("Courier", 6)
        c.drawString(MARGEM + QR_LADO + 5, MARGEM + QR_LADO - 17, codigo)

    c.save()
    buffer.seek(0)
    return buffer


def carimbar(
    origem: Path,
    destino: Path,
    rubrica: Path | None,
    assinatura: Path | None,
    url_verificacao: str | None,
    codigo: str | None,
    posicao: PosicaoAssinatura | None = None,
) -> tuple[int, bool]:
    """Aplica os carimbos e devolve (numero de paginas, assinatura ancorada).

    - rubrica: em TODAS as paginas (quando informada)
    - assinatura + QR: apenas na ultima
    """
    try:
        leitor = PdfReader(str(origem))
    except Exception as exc:  # noqa: BLE001 — pypdf levanta varios tipos
        raise FalhaCarimbo(f"Nao foi possivel ler o PDF: {exc}") from exc

    total = len(leitor.pages)
    if total == 0:
        raise FalhaCarimbo("PDF sem paginas")

    qr_buffer = _gerar_qr(url_verificacao) if url_verificacao and codigo else None
    escritor = PdfWriter()
    ancorou = False

    for indice, pagina in enumerate(leitor.pages):
        ultima = indice == total - 1
        largura = float(pagina.mediabox.width)
        altura = float(pagina.mediabox.height)

        coordenada = None
        if ultima and assinatura and posicao:
            w, h = _dimensoes_proporcionais(
                assinatura, ASSINATURA_ALTURA, ASSINATURA_LARGURA_MAX
            )
            # a busca da ancora acontece ANTES do merge: depois o overlay ja
            # teria alterado o conteudo de texto da pagina
            x, y, ancorou = _coordenada_assinatura(pagina, posicao, largura, w, h)
            coordenada = (x, y)

        precisa_overlay = bool(rubrica) or (ultima and (assinatura or qr_buffer))
        if precisa_overlay:
            if qr_buffer:
                qr_buffer.seek(0)
            camada = _overlay(
                largura,
                altura,
                rubrica,
                assinatura if ultima else None,
                qr_buffer if ultima else None,
                codigo if ultima else None,
                coordenada,
            )
            pagina.merge_page(PdfReader(camada).pages[0])

        escritor.add_page(pagina)

    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("wb") as f:
        escritor.write(f)

    return total, ancorou

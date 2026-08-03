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
ASSINATURA_ALTURA = 84
ASSINATURA_LARGURA_MAX = 290
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


def _coordenada_da_ancora(
    ancora: ancora_pdf.Ancora,
    posicao: PosicaoAssinatura,
    largura_pagina: float,
    largura_img: float,
    altura_img: float,
) -> tuple[float, float]:
    if posicao.relativa == "acima":
        y = ancora.y + ancora.altura + posicao.deslocamento
    else:
        y = ancora.y - posicao.deslocamento - altura_img

    # alinha o inicio da imagem com o inicio da linha encontrada, que e
    # onde o nome comeca a ser escrito
    x = ancora.x
    # nao deixa vazar da pagina
    x = max(MARGEM, min(x, largura_pagina - MARGEM - largura_img))
    y = max(MARGEM, y)
    return x, y


def _localizar_pagina_assinatura(
    leitor: PdfReader,
    posicao: PosicaoAssinatura | None,
    largura_img: float,
    altura_img: float,
) -> tuple[int, tuple[float, float] | None, bool]:
    """Descobre em que pagina a assinatura entra e onde, nessa pagina.

    Varre de tras para frente porque o fecho da peca esta no fim do
    documento — mas a ultima pagina nem sempre e a do fecho: uma quebra de
    pagina ou um paragrafo orfao pode deixar uma pagina depois dele, e a
    assinatura nao pode ficar sozinha nessa pagina, longe do nome.

    Devolve (indice da pagina, coordenada ou None, ancorou).
    """
    total = len(leitor.pages)

    if posicao and posicao.modo == "ancora" and posicao.texto:
        for indice in range(total - 1, -1, -1):
            pagina = leitor.pages[indice]
            ancora = ancora_pdf.localizar(pagina, posicao.texto)
            if ancora is not None:
                coordenada = _coordenada_da_ancora(
                    ancora,
                    posicao,
                    float(pagina.mediabox.width),
                    largura_img,
                    altura_img,
                )
                return indice, coordenada, True

    # sem ancora (ou texto nao encontrado): posicao fixa na ultima pagina —
    # nunca sai documento sem assinatura
    ultima = leitor.pages[total - 1]
    largura = float(ultima.mediabox.width)
    return total - 1, ((largura - largura_img) / 2, MARGEM + 46), False


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

    - assinatura: na pagina onde a ancora foi encontrada (procurada de tras
      para frente). Sem ancora, na ultima pagina, em posicao fixa.
    - rubrica: em todas as paginas MENOS a da assinatura. Num documento de
      uma pagina so, nenhuma pagina e rubricada — vale a assinatura.
    - QR: sempre e apenas na ultima pagina.
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
    indice_assinatura = total - 1
    coordenada = None

    # A busca da ancora acontece ANTES de qualquer merge: depois o overlay
    # ja teria alterado o conteudo de texto das paginas.
    if assinatura:
        w, h = _dimensoes_proporcionais(
            assinatura, ASSINATURA_ALTURA, ASSINATURA_LARGURA_MAX
        )
        indice_assinatura, coordenada, ancorou = _localizar_pagina_assinatura(
            leitor, posicao, w, h
        )

    for indice, pagina in enumerate(leitor.pages):
        ultima = indice == total - 1
        assina_aqui = bool(assinatura) and indice == indice_assinatura
        largura = float(pagina.mediabox.width)
        altura = float(pagina.mediabox.height)

        # A rubrica vale para as paginas SEM assinatura. Documento de uma
        # pagina so tem assinatura — nao existe pagina intermediaria.
        sem_assinatura = not assinatura and ultima
        rubrica_aqui = rubrica if (rubrica and not assina_aqui and not sem_assinatura) else None

        precisa_overlay = bool(rubrica_aqui) or assina_aqui or (ultima and qr_buffer)
        if precisa_overlay:
            if qr_buffer:
                qr_buffer.seek(0)
            camada = _overlay(
                largura,
                altura,
                rubrica_aqui,
                assinatura if assina_aqui else None,
                qr_buffer if ultima else None,
                codigo if ultima else None,
                coordenada if assina_aqui else None,
            )
            pagina.merge_page(PdfReader(camada).pages[0])

        escritor.add_page(pagina)

    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("wb") as f:
        escritor.write(f)

    return total, ancorou

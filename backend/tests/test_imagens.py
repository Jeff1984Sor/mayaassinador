"""Remocao de fundo: os dois modos e o que cada um garante.

O modo "branco" nasceu para papel escaneado claro. Quando o cliente subiu
uma assinatura sobre fundo cinza, ele nao tinha o que fazer: aumentar a
forca comeca a comer o traco antes de alcancar o cinza. Dai o modo "auto".
"""

from io import BytesIO

import pytest
from PIL import Image, ImageDraw

from app.services.imagens import Ajustes, processar


def imagem(fundo: tuple[int, int, int], tinta=(25, 25, 25)) -> bytes:  # noqa: ANN001
    """Um rabisco escuro sobre um fundo de cor controlada."""
    img = Image.new("RGB", (300, 150), fundo)
    ImageDraw.Draw(img).line(
        [(40, 110), (90, 40), (140, 110), (190, 40), (240, 100)],
        fill=tinta,
        width=6,
    )
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def opacidade(caminho) -> float:  # noqa: ANN001
    """Fracao da imagem que sobrou opaca."""
    with Image.open(caminho) as img:
        pixels = list(img.convert("RGBA").getdata())
    return sum(1 for p in pixels if p[3] > 128) / len(pixels)


@pytest.mark.parametrize(
    ("fundo", "descricao"),
    [
        ((250, 250, 250), "papel branco"),
        ((150, 150, 150), "cinza medio — scanner que puxa cinza"),
        ((110, 110, 110), "cinza escuro — foto com sombra"),
        ((205, 190, 150), "amarelado — papel velho ou luz quente"),
    ],
)
def test_auto_limpa_qualquer_fundo(tmp_path, fundo, descricao):  # noqa: ANN001
    destino = tmp_path / "saida.png"
    processar(imagem(fundo), destino, Ajustes(modo_fundo="auto"))

    # sobra so o traco: a moldura de papel foi aparada e quase tudo e transparente
    with Image.open(destino) as img:
        assert img.size < (300, 150), descricao
    assert opacidade(destino) < 0.25, descricao


def test_branco_nao_da_conta_de_fundo_cinza(tmp_path):  # noqa: ANN001
    """Documenta o limite do modo antigo — e por que o automatico existe."""
    destino = tmp_path / "saida.png"
    processar(imagem((150, 150, 150)), destino, Ajustes(modo_fundo="branco"))

    with Image.open(destino) as img:
        assert img.size == (300, 150), "nada foi aparado: o fundo cinza sobreviveu"
    assert opacidade(destino) > 0.9


def test_auto_preserva_o_traco(tmp_path):  # noqa: ANN001
    """Limpar o fundo nao pode significar apagar a assinatura junto."""
    destino = tmp_path / "saida.png"
    processar(imagem((150, 150, 150)), destino, Ajustes(modo_fundo="auto"))
    assert opacidade(destino) > 0.05, "o traco sumiu junto com o fundo"


@pytest.mark.parametrize("graus", [15, 45, 90, -90])
def test_auto_nao_pinta_os_cantos_da_rotacao(tmp_path, graus):  # noqa: ANN001
    """Girar deixa cantos vazios; eles nao podem virar preto opaco.

    O vazio da rotacao e (0,0,0,0) — preto. Como preto fica longe da cor do
    fundo, a rampa do modo automatico o promoveria a "traco" se a mascara
    nao respeitasse a transparencia que ja existia.
    """
    destino = tmp_path / "saida.png"
    processar(imagem((150, 150, 150)), destino, Ajustes(modo_fundo="auto", rotacao=graus))

    with Image.open(destino) as img:
        rgba = img.convert("RGBA")
        largura, altura = rgba.size
        cantos = [
            rgba.getpixel((0, 0)),
            rgba.getpixel((largura - 1, 0)),
            rgba.getpixel((0, altura - 1)),
            rgba.getpixel((largura - 1, altura - 1)),
        ]
    assert all(p[3] == 0 for p in cantos), f"canto opaco apos girar {graus}"

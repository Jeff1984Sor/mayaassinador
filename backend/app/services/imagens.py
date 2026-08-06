"""Tratamento das imagens de logo, rubrica e assinatura (Pillow).

O caso de uso real: o advogado escaneia a assinatura numa folha branca. Se
carimbarmos essa imagem no PDF, ela cobre o texto com um retangulo branco.
Aqui o fundo claro vira transparente, com tolerancia — papel escaneado
quase nunca e #FFFFFF puro.
"""

from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError

FORMATOS_ACEITOS = {"PNG", "JPEG", "WEBP"}
LADO_MAXIMO = 1600  # px — acima disso e desperdicio no PDF

TOLERANCIA_PADRAO = 40
TOLERANCIA_MAXIMA = 120  # acima disso comeca a comer o traco da assinatura


class ImagemInvalida(Exception):
    pass


def _abrir(conteudo: bytes) -> Image.Image:
    try:
        img = Image.open(BytesIO(conteudo))
        img.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ImagemInvalida("Arquivo nao e uma imagem valida") from exc

    if img.format not in FORMATOS_ACEITOS:
        raise ImagemInvalida(
            f"Formato {img.format or 'desconhecido'} nao suportado. Use PNG, JPG ou WEBP."
        )
    return img


def _redimensionar(img: Image.Image) -> Image.Image:
    if max(img.size) <= LADO_MAXIMO:
        return img
    escala = LADO_MAXIMO / max(img.size)
    novo = (int(img.width * escala), int(img.height * escala))
    return img.resize(novo, Image.Resampling.LANCZOS)


def salvar_original(conteudo: bytes, destino: Path) -> None:
    """Guarda a imagem como veio, so normalizando para PNG e redimensionando.

    Serve o 'antes' da comparacao antes/depois na tela de configuracoes.
    """
    img = _redimensionar(_abrir(conteudo).convert("RGBA"))
    img.save(destino, format="PNG", optimize=True)


def remover_fundo(
    conteudo: bytes, destino: Path, tolerancia: int = TOLERANCIA_PADRAO
) -> None:
    """Deixa transparente todo pixel proximo do branco e corta as bordas vazias.

    tolerancia: 0 remove so o branco puro; valores maiores pegam o cinza do
    papel escaneado. 40 e um meio-termo que funciona bem na pratica.
    """
    img = _redimensionar(_abrir(conteudo).convert("RGBA"))
    limite = 255 - tolerancia

    pixels = img.getdata()
    novos = [
        (r, g, b, 0) if (r >= limite and g >= limite and b >= limite) else (r, g, b, a)
        for r, g, b, a in pixels
    ]
    img.putdata(novos)

    # corta o excesso de area transparente: sem isso a assinatura fica
    # minuscula no meio de uma folha vazia ao ser posicionada no PDF
    caixa = img.getbbox()
    if caixa:
        img = img.crop(caixa)

    img.save(destino, format="PNG", optimize=True)


def reprocessar(original: Path, destino: Path, tolerancia: int) -> None:
    """Refaz a remocao de fundo a partir do original, com outra tolerancia.

    E por isso que o original e guardado: cada ajuste parte sempre da imagem
    intacta. Reprocessar em cima da tratada acumularia perda a cada passada —
    o que ja foi apagado nao volta.
    """
    if not original.exists():
        raise ImagemInvalida(
            "Imagem original nao encontrada. Envie o arquivo novamente."
        )
    remover_fundo(original.read_bytes(), destino, tolerancia)


def dimensoes(caminho: Path) -> tuple[int, int]:
    with Image.open(caminho) as img:
        return img.size

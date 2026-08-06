"""Tratamento das imagens de logo, rubrica e assinatura (Pillow).

O caso de uso real: o advogado escaneia a assinatura numa folha branca. Se
carimbarmos essa imagem no PDF, ela cobre o texto com um retangulo branco.
Aqui o fundo claro vira transparente, com tolerancia — papel escaneado
quase nunca e #FFFFFF puro.
"""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError

FORMATOS_ACEITOS = {"PNG", "JPEG", "WEBP"}
LADO_MAXIMO = 1600  # px — acima disso e desperdicio no PDF

TOLERANCIA_PADRAO = 40
TOLERANCIA_MAXIMA = 120  # acima disso comeca a comer o traco da assinatura


class ImagemInvalida(Exception):
    pass


@dataclass(frozen=True)
class Ajustes:
    """O que o usuario escolheu na tela, aplicado sempre sobre o original.

    O recorte vem em fracao (0..1) do lado da imagem, nao em pixels: assim a
    caixa desenhada sobre um preview de 300px continua valendo para o arquivo
    guardado, que pode ter 1600px. Pixels obrigariam a tela a conhecer o
    tamanho real — e a errar sempre que ele mudasse.
    """

    remover_fundo: bool = True
    tolerancia: int = TOLERANCIA_PADRAO
    # graus no sentido horario; o usuario pensa "girar para a direita"
    rotacao: float = 0.0
    # (x, y, largura, altura) em fracao; None = imagem inteira
    recorte: tuple[float, float, float, float] | None = None


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


def ajustes_de_dict(dados: dict) -> Ajustes:
    """Monta os Ajustes a partir do dicionario que vem da API ou do banco.

    Os dois lados falam o mesmo formato — `{x, y, largura, altura}` para o
    recorte —, entao a traducao mora aqui e nao em cada rota.
    """
    recorte = dados.get("recorte")
    return Ajustes(
        remover_fundo=dados.get("remover_fundo", True),
        tolerancia=dados.get("tolerancia", TOLERANCIA_PADRAO),
        rotacao=dados.get("rotacao", 0),
        recorte=(
            (recorte["x"], recorte["y"], recorte["largura"], recorte["altura"])
            if recorte
            else None
        ),
    )


def _recortar(img: Image.Image, caixa: tuple[float, float, float, float]) -> Image.Image:
    x, y, largura, altura = caixa
    esquerda = int(x * img.width)
    topo = int(y * img.height)
    direita = int((x + largura) * img.width)
    base = int((y + altura) * img.height)

    # a caixa vem da tela; um arraste torto nao pode gerar recorte vazio
    esquerda, topo = max(0, esquerda), max(0, topo)
    direita = min(img.width, max(direita, esquerda + 1))
    base = min(img.height, max(base, topo + 1))
    return img.crop((esquerda, topo, direita, base))


def _girar(img: Image.Image, graus: float) -> Image.Image:
    """Gira no sentido horario, expandindo a tela para nao cortar os cantos.

    O Pillow gira no anti-horario, dai o sinal invertido. `expand` evita o
    caso classico de girar 90 graus e perder metade da assinatura; o vazio
    que sobra nos cantos ja nasce transparente.
    """
    if not graus % 360:
        return img
    return img.rotate(
        -graus,
        resample=Image.Resampling.BICUBIC,
        expand=True,
        fillcolor=(0, 0, 0, 0),
    )


def _remover_fundo(img: Image.Image, tolerancia: int) -> Image.Image:
    """Deixa transparente todo pixel proximo do branco.

    tolerancia: 0 remove so o branco puro; valores maiores pegam o cinza do
    papel escaneado. 40 e um meio-termo que funciona bem na pratica.
    """
    limite = 255 - tolerancia
    novos = [
        (r, g, b, 0) if (r >= limite and g >= limite and b >= limite) else (r, g, b, a)
        for r, g, b, a in img.getdata()
    ]
    img.putdata(novos)
    return img


def _aparar(img: Image.Image) -> Image.Image:
    """Corta o excesso transparente das bordas.

    Sem isso a assinatura fica minuscula no meio de uma folha vazia ao ser
    posicionada no PDF — a altura configurada valeria para o papel, nao para
    o traco.
    """
    caixa = img.getbbox()
    return img.crop(caixa) if caixa else img


def processar(conteudo: bytes, destino: Path, ajustes: Ajustes) -> None:
    """Aplica recorte, rotacao e remocao de fundo, nesta ordem.

    A ordem importa: recortar antes de girar deixa a caixa desenhada na tela
    corresponder ao que o usuario viu, e remover o fundo depois de girar
    apaga tambem o branco que a interpolacao da rotacao criou nas bordas.
    """
    img = _redimensionar(_abrir(conteudo).convert("RGBA"))

    if ajustes.recorte:
        img = _recortar(img, ajustes.recorte)
    img = _girar(img, ajustes.rotacao)
    if ajustes.remover_fundo:
        img = _aparar(_remover_fundo(img, ajustes.tolerancia))

    img.save(destino, format="PNG", optimize=True)


def remover_fundo(
    conteudo: bytes, destino: Path, tolerancia: int = TOLERANCIA_PADRAO
) -> None:
    processar(conteudo, destino, Ajustes(tolerancia=tolerancia))


def reprocessar(original: Path, destino: Path, ajustes: Ajustes) -> None:
    """Reaplica os ajustes a partir do original.

    E por isso que o original e guardado: cada ajuste parte sempre da imagem
    intacta. Reprocessar em cima da tratada acumularia perda a cada passada —
    o que ja foi apagado nao volta, e girar duas vezes borraria o traco.
    """
    if not original.exists():
        raise ImagemInvalida(
            "Imagem original nao encontrada. Envie o arquivo novamente."
        )
    processar(original.read_bytes(), destino, ajustes)


def dimensoes(caminho: Path) -> tuple[int, int]:
    with Image.open(caminho) as img:
        return img.size

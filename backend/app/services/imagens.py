"""Tratamento das imagens de logo, rubrica e assinatura (Pillow).

O caso de uso real: o advogado escaneia a assinatura numa folha branca. Se
carimbarmos essa imagem no PDF, ela cobre o texto com um retangulo branco.
Aqui o fundo claro vira transparente, com tolerancia — papel escaneado
quase nunca e #FFFFFF puro.
"""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Literal

from PIL import Image, ImageChops, UnidentifiedImageError

FORMATOS_ACEITOS = {"PNG", "JPEG", "WEBP"}
LADO_MAXIMO = 1600  # px — acima disso e desperdicio no PDF

TOLERANCIA_PADRAO = 40
TOLERANCIA_MAXIMA = 120  # acima disso comeca a comer o traco da assinatura

# "branco": apaga o que esta perto do branco. Rapido e previsivel, mas so
#   serve para papel claro — fundo cinza ou colorido sobrevive.
# "auto": descobre a cor do fundo pelas bordas e apaga tudo que se parece com
#   ela, seja qual for. E o modo para foto de celular, scanner que puxa
#   cinza e assinatura sobre fundo colorido.
ModoFundo = Literal["branco", "auto"]

# largura da faixa de borda usada para estimar a cor do fundo, em fracao do
# lado: 4% pega papel suficiente sem alcancar o traco, que fica no meio
FAIXA_BORDA = 0.04


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
    modo_fundo: ModoFundo = "branco"
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
        modo_fundo=dados.get("modo_fundo", "branco"),
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


def _cor_do_fundo(img: Image.Image) -> tuple[int, int, int]:
    """Estima a cor do fundo pela moldura da imagem.

    A assinatura ocupa o miolo; a borda e papel puro em praticamente todo
    scan e foto. Usamos a mediana, e nao a media, para que um dedo no canto
    ou uma sombra forte nao puxem a estimativa.
    """
    rgba = img.convert("RGBA")
    largura, altura = rgba.size
    faixa_x = max(1, int(largura * FAIXA_BORDA))
    faixa_y = max(1, int(altura * FAIXA_BORDA))

    bordas = [
        rgba.crop((0, 0, largura, faixa_y)),  # topo
        rgba.crop((0, altura - faixa_y, largura, altura)),  # base
        rgba.crop((0, 0, faixa_x, altura)),  # esquerda
        rgba.crop((largura - faixa_x, 0, largura, altura)),  # direita
    ]

    # pixels ja transparentes nao contam: depois de girar, os cantos vazios
    # sao (0,0,0,0) e puxariam a estimativa para preto
    pixels = [
        (p[0], p[1], p[2])
        for pedaco in bordas
        for p in pedaco.getdata()
        if p[3] > 0
    ]
    if not pixels:
        return (255, 255, 255)

    def mediana(canal: int) -> int:
        valores = sorted(p[canal] for p in pixels)
        return valores[len(valores) // 2]

    return (mediana(0), mediana(1), mediana(2))


def _limiar_otsu(histograma: list[int]) -> int:
    """Separa 'fundo' de 'traco' no histograma de distancias (metodo de Otsu).

    Em vez de o usuario adivinhar um numero, procuramos o corte que melhor
    separa os dois grupos de pixels da propria imagem. E o que faz o modo
    automatico funcionar tanto num scan lavado quanto numa foto escura.
    """
    total = sum(histograma)
    if not total:
        return 128

    soma_total = sum(i * n for i, n in enumerate(histograma))
    soma_fundo = 0.0
    peso_fundo = 0.0
    melhor_variancia = -1.0
    melhor_limiar = 128

    for limiar, quantidade in enumerate(histograma):
        peso_fundo += quantidade
        if peso_fundo == 0:
            continue
        peso_frente = total - peso_fundo
        if peso_frente == 0:
            break

        soma_fundo += limiar * quantidade
        media_fundo = soma_fundo / peso_fundo
        media_frente = (soma_total - soma_fundo) / peso_frente

        # variancia entre as duas classes: quanto maior, melhor a separacao
        variancia = peso_fundo * peso_frente * (media_fundo - media_frente) ** 2
        if variancia > melhor_variancia:
            melhor_variancia = variancia
            melhor_limiar = limiar

    return melhor_limiar


def _remover_fundo_auto(img: Image.Image, tolerancia: int) -> Image.Image:
    """Apaga o fundo seja qual for a cor dele — cinza, colorido ou branco.

    Como funciona: descobre a cor do fundo pelas bordas, mede a distancia de
    cada pixel ate ela e usa Otsu para achar o corte entre fundo e traco.
    Em torno desse corte a transparencia e gradual, o que preserva a borda
    suave do traco em vez de deixar o serrilhado de um corte seco.

    Feito com operacoes de banda do Pillow (`ImageChops` e `point`), que
    rodam em C: um laco por pixel em Python levaria segundos numa imagem de
    1600px e o worker do prod2 tem um nucleo so.
    """
    fundo = _cor_do_fundo(img)
    rgb = img.convert("RGB")

    # distancia ate a cor do fundo, canal a canal; ficamos com a maior delas,
    # que e o que separa um cinza neutro de um traco azul de caneta
    solido = Image.new("RGB", rgb.size, fundo)
    diferenca = ImageChops.difference(rgb, solido)
    r, g, b = diferenca.split()
    distancia = ImageChops.lighter(ImageChops.lighter(r, g), b)

    corte = _limiar_otsu(distancia.histogram())

    # a tolerancia da tela vira a largura da rampa: mais tolerancia, transicao
    # mais larga e apagando mais perto do traco
    margem = max(4, int(tolerancia * 0.6))
    inicio = max(0, corte - margem)
    fim = min(255, corte + margem)

    def alfa(valor: int) -> int:
        if valor <= inicio:
            return 0
        if valor >= fim:
            return 255
        return int(255 * (valor - inicio) / (fim - inicio))

    mascara = distancia.point([alfa(v) for v in range(256)])

    saida = img.convert("RGBA")
    # o que ja era transparente continua transparente: sem este `darker`, os
    # cantos vazios deixados pela rotacao voltariam opacos e pretos, porque
    # preto esta longe da cor do fundo e a rampa os promoveria a traco
    mascara = ImageChops.darker(mascara, saida.getchannel("A"))
    saida.putalpha(mascara)
    return saida


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
        sem_fundo = (
            _remover_fundo_auto(img, ajustes.tolerancia)
            if ajustes.modo_fundo == "auto"
            else _remover_fundo(img, ajustes.tolerancia)
        )
        img = _aparar(sem_fundo)

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

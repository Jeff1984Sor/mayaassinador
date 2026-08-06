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

# Os tres modos formam uma escada, do mais conservador ao mais agressivo:
#
# "branco": apaga o que esta perto do branco. Previsivel, mas so serve para
#   papel claro — fundo cinza ou colorido sobrevive.
# "auto": descobre a COR do fundo pelas bordas e apaga o que se parece com
#   ela. Resolve fundo cinza ou colorido uniforme. Falha quando a imagem tem
#   mais de um fundo (o caso classico: rubrica recortada de um print, com um
#   retangulo cinza no meio de uma area branca) — as bordas so contam sobre
#   um deles, e o outro sobrevive.
# "traco": ignora a cor do fundo. Mantem so o que e escuro o bastante para
#   ser tinta e apaga TODO o resto, quantos fundos existam. E a opcao para
#   quem quer o fundo removido a qualquer custo.
ModoFundo = Literal["branco", "auto", "traco"]

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
    mascara = _rampa(distancia, corte, tolerancia)

    saida = img.convert("RGBA")
    # o que ja era transparente continua transparente: sem este `darker`, os
    # cantos vazios deixados pela rotacao voltariam opacos e pretos, porque
    # preto esta longe da cor do fundo e a rampa os promoveria a traco
    mascara = ImageChops.darker(mascara, saida.getchannel("A"))
    saida.putalpha(mascara)
    return saida


def _limiar_otsu_tres_classes(histograma: list[int]) -> int:
    """Corte que isola a tinta quando a imagem tem TRES niveis, nao dois.

    O Otsu comum separa em dois grupos. Numa rubrica recortada de um print —
    papel branco, retangulo cinza e traco — ele poe a divisa entre o branco e
    "todo o resto", e o cinza fica do lado da tinta: exatamente o bloco que
    sobrava na tela. Procurando dois cortes de uma vez, o cinza ganha a
    propria classe e so a tinta fica acima do segundo corte.

    Devolve o segundo corte. Sao ~32 mil combinacoes com somas acumuladas,
    barato o bastante para rodar a cada ajuste do slider.
    """
    total = sum(histograma)
    if not total:
        return 128

    # somas acumuladas: contagem e soma ponderada ate cada nivel
    contagem = [0] * 257
    ponderada = [0.0] * 257
    for i, n in enumerate(histograma):
        contagem[i + 1] = contagem[i] + n
        ponderada[i + 1] = ponderada[i] + i * n

    def classe(inicio: int, fim: int) -> tuple[float, float]:
        """(peso, media) do intervalo [inicio, fim]."""
        peso = contagem[fim + 1] - contagem[inicio]
        if peso == 0:
            return 0.0, 0.0
        return peso, (ponderada[fim + 1] - ponderada[inicio]) / peso

    media_geral = ponderada[256] / total
    melhor = (-1.0, 128)

    for t1 in range(0, 254):
        peso_a, media_a = classe(0, t1)
        if peso_a == 0:
            continue
        for t2 in range(t1 + 1, 255):
            peso_b, media_b = classe(t1 + 1, t2)
            peso_c, media_c = classe(t2 + 1, 255)
            if peso_b == 0 or peso_c == 0:
                continue
            variancia = (
                peso_a * (media_a - media_geral) ** 2
                + peso_b * (media_b - media_geral) ** 2
                + peso_c * (media_c - media_geral) ** 2
            )
            if variancia > melhor[0]:
                melhor = (variancia, t2)

    return melhor[1]


def _rampa(
    distancia: Image.Image,
    corte: int,
    tolerancia: int,
    a_partir_do_corte: bool = False,
) -> Image.Image:
    """Converte 'distancia ate o fundo' em canal alfa, com transicao suave.

    O corte seco deixaria o traco serrilhado; a rampa em torno dele preserva
    a borda macia da caneta. A tolerancia da tela regula a largura dela.

    `a_partir_do_corte` sobe a rampa so acima do corte, em vez de centra-la
    nele. E o que o modo "traco" precisa: centrada, a rampa alcanca a classe
    do meio (o retangulo cinza) e devolve um alfa parcial — o fundo fica
    translucido em vez de sumir, que na tela parece "nao removeu tudo".
    """
    margem = max(4, int(tolerancia * 0.6))
    inicio = corte if a_partir_do_corte else max(0, corte - margem)
    fim = min(255, inicio + (2 * margem if a_partir_do_corte else margem * 2))
    fim = max(fim, inicio + 1)

    def alfa(valor: int) -> int:
        if valor <= inicio:
            return 0
        if valor >= fim:
            return 255
        return int(255 * (valor - inicio) / (fim - inicio))

    return distancia.point([alfa(v) for v in range(256)])


def _remover_fundo_traco(img: Image.Image, tolerancia: int) -> Image.Image:
    """Mantem so o traco. Apaga o fundo inteiro, tenha ele quantas cores tiver.

    A diferenca para o modo "auto" e nao perguntar QUAL e a cor do fundo:
    aqui vale o brilho. Assinatura e tinta escura sobre algo mais claro, e
    tudo que nao for escuro o bastante vai embora — o papel branco, o
    retangulo cinza do print e a sombra da foto, todos de uma vez.

    O limiar sai de Otsu sobre a propria imagem, entao nao ha numero para o
    usuario adivinhar: funciona no scan lavado e na foto escura.
    """
    luminancia = img.convert("L")

    # Papel claro e o caso normal, mas existe o inverso (giz branco em quadro
    # escuro, assinatura digitalizada em negativo). A borda diz qual e qual.
    fundo_claro = sum(_cor_do_fundo(img)) / 3 >= 128
    # a distancia precisa crescer na direcao da tinta, para a rampa funcionar
    # igual nos dois casos
    distancia = ImageChops.invert(luminancia) if fundo_claro else luminancia

    corte = _limiar_otsu_tres_classes(distancia.histogram())
    mascara = _rampa(distancia, corte, tolerancia, a_partir_do_corte=True)

    saida = img.convert("RGBA")
    mascara = ImageChops.darker(mascara, saida.getchannel("A"))
    saida.putalpha(mascara)
    return saida


# alfa abaixo disto e invisivel na pratica; serve so para nao contar como
# conteudo na hora de aparar
ALFA_MINIMO = 8


def _aparar(img: Image.Image) -> Image.Image:
    """Corta o excesso transparente das bordas.

    Sem isso a assinatura fica minuscula no meio de uma folha vazia ao ser
    posicionada no PDF — a altura configurada valeria para o papel, nao para
    o traco.

    O `getbbox` cru nao serve: a rampa deixa o fundo com um alfa residual de
    1 ou 2, invisivel a olho nu mas suficiente para ele considerar a folha
    inteira como conteudo e nao cortar nada. Medimos a caixa sobre um alfa
    limpo e recortamos a imagem original, que mantem as bordas suaves.
    """
    alfa = img.getchannel("A").point(lambda a: 255 if a > ALFA_MINIMO else 0)
    caixa = alfa.getbbox()
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
        limpeza = {
            "auto": _remover_fundo_auto,
            "traco": _remover_fundo_traco,
        }.get(ajustes.modo_fundo, _remover_fundo)
        img = _aparar(limpeza(img, ajustes.tolerancia))

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

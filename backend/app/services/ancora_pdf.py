"""Localiza um trecho de texto dentro de uma pagina do PDF.

Usado para ancorar a assinatura no nome do advogado em vez de carimbar
numa posicao fixa. Funciona porque o PDF sai do nosso proprio pipeline
(DOCX -> LibreOffice), entao o texto e sempre texto de verdade — nunca
imagem escaneada.

Implementado com o visitor do pypdf: nao precisamos de pdfplumber nem de
nenhuma dependencia nova so para descobrir coordenadas.
"""

import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Ancora:
    """Posicao encontrada, em pontos, com origem no canto inferior esquerdo."""

    x: float
    y: float
    altura: float
    texto: str


def normalizar(valor: str) -> str:
    """Remove acentos, baixa a caixa e colapsa espacos.

    O nome pode estar em caixa alta no documento e com acento na
    configuracao — a comparacao precisa ignorar as duas coisas.
    """
    sem_acento = "".join(
        c
        for c in unicodedata.normalize("NFD", valor)
        if unicodedata.category(c) != "Mn"
    )
    return " ".join(sem_acento.lower().split())


def _agrupar_linhas(fragmentos: list[tuple[str, float, float, float]], tolerancia: float = 2.0):
    """Junta fragmentos que estao na mesma altura numa unica linha.

    O PDF quebra o texto em varios pedacos (mudanca de fonte, kerning), entao
    procurar o nome fragmento a fragmento falharia em quase todo caso real.
    """
    linhas: list[dict] = []
    for texto, x, y, altura in sorted(fragmentos, key=lambda f: (-f[2], f[1])):
        for linha in linhas:
            if abs(linha["y"] - y) <= tolerancia:
                linha["partes"].append((x, texto))
                linha["x"] = min(linha["x"], x)
                linha["altura"] = max(linha["altura"], altura)
                break
        else:
            linhas.append({"y": y, "x": x, "altura": altura, "partes": [(x, texto)]})

    for linha in linhas:
        linha["texto"] = "".join(t for _, t in sorted(linha["partes"]))
    return linhas


def localizar(pagina, termo: str) -> Ancora | None:
    """Procura `termo` na pagina e devolve a posicao da linha que o contem.

    Retorna a ULTIMA ocorrencia: se o nome do advogado aparecer no cabecalho
    e de novo no fecho da peca, queremos o fecho.
    """
    alvo = normalizar(termo)
    if not alvo:
        return None

    fragmentos: list[tuple[str, float, float, float]] = []

    def visitor(texto, _cm, tm, _fonte, tamanho):  # noqa: ANN001
        if texto and texto.strip():
            # tm[4] e tm[5] sao a translacao da matriz de texto: x e y
            fragmentos.append((texto, float(tm[4]), float(tm[5]), float(tamanho or 10)))

    try:
        pagina.extract_text(visitor_text=visitor)
    except Exception:  # noqa: BLE001 — PDF estranho nao pode quebrar o pipeline
        return None

    encontradas = [
        linha for linha in _agrupar_linhas(fragmentos) if alvo in normalizar(linha["texto"])
    ]
    if not encontradas:
        return None

    # menor y = mais embaixo na pagina = mais perto do fecho do documento
    escolhida = min(encontradas, key=lambda linha: linha["y"])
    return Ancora(
        x=escolhida["x"],
        y=escolhida["y"],
        altura=escolhida["altura"],
        texto=escolhida["texto"].strip(),
    )

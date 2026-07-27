"""Aplica cabecalho e rodape no .docx com python-docx.

Regra que nao pode ser quebrada: as linhas do cabecalho montadas aqui
precisam ser IDENTICAS as do preview do frontend
(`linhasCabecalho` em preview-a4.tsx). Se as duas logicas divergirem, o
preview passa a mentir — e o preview e o argumento de venda da tela 4.4.
"""

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from docx.text.paragraph import Paragraph

from app.models import ConfiguracaoTenant, Escritorio

ALINHAMENTOS = {
    "esquerda": WD_ALIGN_PARAGRAPH.LEFT,
    "centro": WD_ALIGN_PARAGRAPH.CENTER,
    "direita": WD_ALIGN_PARAGRAPH.RIGHT,
}


def linhas_cabecalho(escritorio: Escritorio | None, campos: dict) -> list[str]:
    """Espelho de `linhasCabecalho` do frontend. Manter as duas em sincronia."""
    if escritorio is None:
        return []

    linhas: list[str] = []

    if campos.get("razao_social"):
        linhas.append(escritorio.razao_social)

    identidade: list[str] = []
    if campos.get("cnpj") and escritorio.cnpj:
        identidade.append(f"CNPJ {escritorio.cnpj}")
    if campos.get("oab") and escritorio.oab_numero:
        seccional = f"/{escritorio.oab_seccional}" if escritorio.oab_seccional else ""
        identidade.append(f"OAB {escritorio.oab_numero}{seccional}")
    if identidade:
        linhas.append(" · ".join(identidade))

    if campos.get("endereco"):
        rua = ", ".join(p for p in (escritorio.logradouro, escritorio.numero) if p)
        local = " - ".join(
            p for p in (escritorio.bairro, escritorio.cidade, escritorio.uf) if p
        )
        endereco = " · ".join(p for p in (rua, local, escritorio.cep) if p)
        if endereco:
            linhas.append(endereco)

    contato: list[str] = []
    if campos.get("telefone") and escritorio.telefone:
        contato.append(escritorio.telefone)
    if campos.get("whatsapp") and escritorio.whatsapp:
        contato.append(f"WhatsApp {escritorio.whatsapp}")
    if campos.get("email") and escritorio.email:
        contato.append(escritorio.email)
    if campos.get("site") and escritorio.site:
        contato.append(escritorio.site)
    if contato:
        linhas.append(" · ".join(contato))

    return linhas


def _aplicar_fonte(run, tipografia: dict, negrito_forcado: bool | None = None) -> None:
    fonte = tipografia.get("fonte", "Arial")
    run.font.size = Pt(tipografia.get("tamanho", 10))
    run.font.bold = tipografia.get("negrito", False) if negrito_forcado is None else negrito_forcado
    run.font.italic = tipografia.get("italico", False)

    cor = tipografia.get("cor", "#1E2D6B").lstrip("#")
    run.font.color.rgb = RGBColor.from_string(cor.upper())

    # python-docx so escreve o nome em w:ascii. Sem preencher hAnsi/cs/eastAsia
    # o Word e o LibreOffice caem na fonte do tema em parte do texto.
    run.font.name = fonte
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for atributo in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(atributo), fonte)


def _campo(paragrafo: Paragraph, instrucao: str, tipografia: dict) -> None:
    """Insere um campo do Word (PAGE / NUMPAGES).

    python-docx nao expoe campos: e preciso montar o XML na mao, senao a
    numeracao ficaria congelada no numero da primeira pagina.
    """
    run = paragrafo.add_run()
    _aplicar_fonte(run, tipografia)

    inicio = OxmlElement("w:fldChar")
    inicio.set(qn("w:fldCharType"), "begin")

    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f" {instrucao} "

    fim = OxmlElement("w:fldChar")
    fim.set(qn("w:fldCharType"), "end")

    run._element.append(inicio)
    run._element.append(instr)
    run._element.append(fim)


def _texto(paragrafo: Paragraph, texto: str, tipografia: dict, negrito: bool | None = None) -> None:
    run = paragrafo.add_run(texto)
    _aplicar_fonte(run, tipografia, negrito)


def _limpar(container) -> None:
    """Remove o conteudo pre-existente do cabecalho/rodape do template."""
    for paragrafo in list(container.paragraphs):
        p = paragrafo._element
        p.getparent().remove(p)
    for tabela in list(container.tables):
        t = tabela._element
        t.getparent().remove(t)


def _sem_bordas(tabela) -> None:
    tbl_pr = tabela._element.tblPr
    borders = OxmlElement("w:tblBorders")
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{lado}")
        el.set(qn("w:val"), "none")
        borders.append(el)
    tbl_pr.append(borders)


def aplicar(
    origem: Path,
    destino: Path,
    config: ConfiguracaoTenant,
    escritorio: Escritorio | None,
    logo: Path | None,
) -> None:
    """Le o .docx original, injeta cabecalho e rodape, salva em `destino`.

    O arquivo de origem NUNCA e modificado — e o anexo do cliente.
    """
    doc = Document(str(origem))

    tip_cab = dict(config.cabecalho_tipografia or {})
    tip_rod = dict(config.rodape_tipografia or {})
    linhas = linhas_cabecalho(escritorio, dict(config.cabecalho_campos or {}))
    posicao_logo = config.logo_posicao or "esquerda"
    usar_logo = logo is not None and logo.exists() and posicao_logo != "sem_logo"

    for secao in doc.sections:
        # ---------------- cabecalho ----------------
        cabecalho = secao.header
        cabecalho.is_linked_to_previous = False
        _limpar(cabecalho)

        if usar_logo and posicao_logo in ("esquerda", "direita"):
            tabela = cabecalho.add_table(rows=1, cols=2, width=secao.page_width)
            tabela.alignment = WD_TABLE_ALIGNMENT.CENTER
            _sem_bordas(tabela)

            celula_logo, celula_texto = (
                (tabela.cell(0, 0), tabela.cell(0, 1))
                if posicao_logo == "esquerda"
                else (tabela.cell(0, 1), tabela.cell(0, 0))
            )

            p_logo = celula_logo.paragraphs[0]
            p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_logo.add_run().add_picture(str(logo), height=Pt(34))

            primeiro = True
            alvo = celula_texto.paragraphs[0]
            for linha in linhas:
                p = alvo if primeiro else celula_texto.add_paragraph()
                p.alignment = ALINHAMENTOS.get(tip_cab.get("alinhamento", "centro"))
                _texto(p, linha, tip_cab, negrito=True if primeiro else None)
                primeiro = False
        else:
            if usar_logo and posicao_logo == "acima":
                p = cabecalho.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.add_run().add_picture(str(logo), height=Pt(34))

            for i, linha in enumerate(linhas):
                p = cabecalho.add_paragraph()
                p.alignment = ALINHAMENTOS.get(tip_cab.get("alinhamento", "centro"))
                _texto(p, linha, tip_cab, negrito=True if i == 0 else None)

        # ---------------- rodape ----------------
        rodape = secao.footer
        rodape.is_linked_to_previous = False
        _limpar(rodape)

        texto_rodape = (config.rodape_texto or "").strip()
        numerar = bool(config.rodape_numeracao)
        lado = config.rodape_numeracao_alinhamento or "direita"

        if numerar and lado in ("esquerda", "direita") and texto_rodape:
            # texto e numeracao em lados opostos: tabela de 2 colunas
            tabela = rodape.add_table(rows=1, cols=2, width=secao.page_width)
            _sem_bordas(tabela)
            celula_num, celula_txt = (
                (tabela.cell(0, 0), tabela.cell(0, 1))
                if lado == "esquerda"
                else (tabela.cell(0, 1), tabela.cell(0, 0))
            )

            p_txt = celula_txt.paragraphs[0]
            p_txt.alignment = ALINHAMENTOS.get(tip_rod.get("alinhamento", "centro"))
            _texto(p_txt, texto_rodape, tip_rod)

            p_num = celula_num.paragraphs[0]
            p_num.alignment = ALINHAMENTOS.get(lado)
            _numeracao(p_num, tip_rod)
        else:
            if texto_rodape:
                p = rodape.add_paragraph()
                p.alignment = ALINHAMENTOS.get(tip_rod.get("alinhamento", "centro"))
                _texto(p, texto_rodape, tip_rod)
            if numerar:
                p = rodape.add_paragraph()
                p.alignment = ALINHAMENTOS.get(lado)
                _numeracao(p, tip_rod)

    doc.save(str(destino))


def _numeracao(paragrafo: Paragraph, tipografia: dict) -> None:
    _texto(paragrafo, "Pagina ", tipografia)
    _campo(paragrafo, "PAGE", tipografia)
    _texto(paragrafo, " de ", tipografia)
    _campo(paragrafo, "NUMPAGES", tipografia)

"""Schemas da configuracao do tenant: cabecalho, rodape, imagens e SMTP."""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.configuracao import FONTES_DISPONIVEIS

Alinhamento = Literal["esquerda", "centro", "direita"]
# "acima": logo centralizado, texto mantem o alinhamento da tipografia
# "centro": logo e texto centralizados juntos (papel timbrado classico)
PosicaoLogo = Literal["esquerda", "direita", "acima", "centro", "sem_logo"]


class Tipografia(BaseModel):
    """As opcoes de fonte sao limitadas ao que esta instalado no prod2.

    Aceitar uma fonte fora dessa lista faria o LibreOffice substituir na
    conversao, e o PDF sairia diferente do preview da tela.
    """

    fonte: str = "Arial"
    tamanho: int = Field(default=10, ge=6, le=72)
    alinhamento: Alinhamento = "centro"
    negrito: bool = False
    italico: bool = False
    cor: str = "#1E2D6B"

    @field_validator("fonte")
    @classmethod
    def valida_fonte(cls, v: str) -> str:
        if v not in FONTES_DISPONIVEIS:
            disponiveis = ", ".join(FONTES_DISPONIVEIS)
            raise ValueError(f"Fonte nao instalada no servidor. Use uma de: {disponiveis}")
        return v

    @field_validator("cor")
    @classmethod
    def valida_cor(cls, v: str) -> str:
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", v):
            raise ValueError("Cor deve estar no formato #RRGGBB")
        return v.upper()


class CabecalhoCampos(BaseModel):
    """Quais dados do escritorio aparecem no cabecalho (checkboxes da tela)."""

    razao_social: bool = True
    cnpj: bool = False
    oab: bool = True
    endereco: bool = True
    telefone: bool = True
    whatsapp: bool = False
    email: bool = True
    site: bool = False


class RodapeCampos(BaseModel):
    """Mesmos campos do cabecalho, escolhidos de forma independente.

    Padrao tudo desligado: quem ja usava so o texto livre nao ve mudanca.
    """

    razao_social: bool = False
    cnpj: bool = False
    oab: bool = False
    endereco: bool = False
    telefone: bool = False
    whatsapp: bool = False
    email: bool = False
    site: bool = False


class ConfiguracaoUpdate(BaseModel):
    cabecalho_campos: CabecalhoCampos
    cabecalho_tipografia: Tipografia
    logo_posicao: PosicaoLogo = "esquerda"
    logo_altura: int = Field(default=34, ge=10, le=120)
    logo_remover_fundo: bool = False
    logo_tolerancia: int = Field(default=40, ge=0, le=120)

    rodape_campos: RodapeCampos = RodapeCampos()
    rodape_texto: str | None = Field(default=None, max_length=2000)
    rodape_tipografia: Tipografia
    rodape_numeracao: bool = True
    rodape_numeracao_alinhamento: Alinhamento = "direita"
    numeracao_local: Literal["rodape", "cabecalho"] = "rodape"

    rubricar_por_padrao: bool = False
    qrcode_ativo: bool = True

    # ---- Tamanho dos carimbos, em pontos ----
    # Os tetos existem para que uma imagem enorme nao cubra o texto da peca.
    rubrica_altura: int = Field(default=26, ge=10, le=80)
    assinatura_altura: int = Field(default=84, ge=20, le=200)
    # a tolerancia tambem chega pelo endpoint de reprocessar, que e quem
    # regrava a imagem; aqui ela viaja so para o formulario nao perder o valor
    rubrica_tolerancia: int = Field(default=40, ge=0, le=120)
    assinatura_tolerancia: int = Field(default=40, ge=0, le=120)

    # ---- Posicao da assinatura ----
    assinatura_modo: Literal["fixa", "ancora"] = "fixa"
    assinatura_ancora: str | None = Field(default=None, max_length=200)
    assinatura_relativa: Literal["acima", "abaixo"] = "abaixo"
    assinatura_deslocamento: int = Field(default=6, ge=0, le=200)

    # ---- SMTP ----
    smtp_host: str | None = Field(default=None, max_length=255)
    smtp_porta: int | None = Field(default=None, ge=1, le=65535)
    smtp_usuario: str | None = Field(default=None, max_length=255)
    # enviada apenas quando o usuario digita uma nova senha; None mantem a atual
    smtp_senha: str | None = Field(default=None, max_length=255)
    smtp_tls: bool = True
    email_remetente_nome: str | None = Field(default=None, max_length=200)
    email_assunto_padrao: str | None = Field(default=None, max_length=255)
    email_mensagem_padrao: str | None = Field(default=None, max_length=5000)


class ConfiguracaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cabecalho_campos: CabecalhoCampos
    cabecalho_tipografia: Tipografia
    logo_posicao: PosicaoLogo
    logo_altura: int
    logo_remover_fundo: bool
    logo_tolerancia: int

    rodape_campos: RodapeCampos
    rodape_texto: str | None
    rodape_tipografia: Tipografia
    rodape_numeracao: bool
    rodape_numeracao_alinhamento: Alinhamento
    numeracao_local: Literal["rodape", "cabecalho"]

    rubricar_por_padrao: bool
    qrcode_ativo: bool
    rubrica_altura: int
    assinatura_altura: int
    rubrica_tolerancia: int
    assinatura_tolerancia: int
    assinatura_modo: Literal["fixa", "ancora"]
    assinatura_ancora: str | None
    assinatura_relativa: Literal["acima", "abaixo"]
    assinatura_deslocamento: int
    rubrica_url: str | None = None
    assinatura_url: str | None = None
    # 'antes' da comparacao antes/depois do tratamento com Pillow
    rubrica_original_url: str | None = None
    assinatura_original_url: str | None = None

    smtp_host: str | None
    smtp_porta: int | None
    smtp_usuario: str | None
    smtp_tls: bool
    # a senha nunca volta para o frontend, so a informacao de que existe
    smtp_senha_definida: bool = False
    email_remetente_nome: str | None
    email_assunto_padrao: str | None
    email_mensagem_padrao: str | None


class FonteOut(BaseModel):
    valor: str
    rotulo: str


class EmailTesteRequest(BaseModel):
    destinatario: EmailStr


class UploadOut(BaseModel):
    url: str
    url_original: str | None = None
    largura: int
    altura: int

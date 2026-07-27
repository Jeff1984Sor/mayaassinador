"""Schemas da configuracao do tenant: cabecalho, rodape, imagens e SMTP."""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.configuracao import FONTES_DISPONIVEIS

Alinhamento = Literal["esquerda", "centro", "direita"]
PosicaoLogo = Literal["esquerda", "direita", "acima", "sem_logo"]


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


class ConfiguracaoUpdate(BaseModel):
    cabecalho_campos: CabecalhoCampos
    cabecalho_tipografia: Tipografia
    logo_posicao: PosicaoLogo = "esquerda"

    rodape_texto: str | None = Field(default=None, max_length=2000)
    rodape_tipografia: Tipografia
    rodape_numeracao: bool = True
    rodape_numeracao_alinhamento: Alinhamento = "direita"

    rubricar_por_padrao: bool = False

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

    rodape_texto: str | None
    rodape_tipografia: Tipografia
    rodape_numeracao: bool
    rodape_numeracao_alinhamento: Alinhamento

    rubricar_por_padrao: bool
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

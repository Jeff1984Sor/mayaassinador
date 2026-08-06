"""Schemas dos Dados do Escritorio — a fonte unica da verdade."""

import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}


class EscritorioBase(BaseModel):
    razao_social: str = Field(min_length=2, max_length=255)
    nome_fantasia: str | None = Field(default=None, max_length=255)
    cnpj: str | None = Field(default=None, max_length=18)

    oab_numero: str | None = Field(default=None, max_length=30)
    oab_seccional: str | None = Field(default=None, max_length=2)

    # quem assina — e o nome que o pipeline procura no PDF para ancorar a
    # imagem da assinatura
    signatario_nome: str | None = Field(default=None, max_length=200)
    signatario_oab: str | None = Field(default=None, max_length=30)

    logradouro: str | None = Field(default=None, max_length=255)
    numero: str | None = Field(default=None, max_length=20)
    complemento: str | None = Field(default=None, max_length=100)
    bairro: str | None = Field(default=None, max_length=100)
    cidade: str | None = Field(default=None, max_length=100)
    uf: str | None = Field(default=None, max_length=2)
    cep: str | None = Field(default=None, max_length=9)

    telefone: str | None = Field(default=None, max_length=20)
    whatsapp: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None
    site: str | None = Field(default=None, max_length=255)

    @field_validator("uf", "oab_seccional")
    @classmethod
    def valida_uf(cls, v: str | None) -> str | None:
        if not v:
            return None
        v = v.strip().upper()
        if v not in UFS:
            raise ValueError("UF invalida")
        return v

    @field_validator("cnpj")
    @classmethod
    def valida_cnpj(cls, v: str | None) -> str | None:
        if not v:
            return None
        digitos = re.sub(r"\D", "", v)
        if len(digitos) != 14:
            raise ValueError("CNPJ deve ter 14 digitos")
        return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}"

    @field_validator("cep")
    @classmethod
    def valida_cep(cls, v: str | None) -> str | None:
        if not v:
            return None
        digitos = re.sub(r"\D", "", v)
        if len(digitos) != 8:
            raise ValueError("CEP deve ter 8 digitos")
        return f"{digitos[:5]}-{digitos[5:]}"


class EscritorioUpdate(EscritorioBase):
    pass


class EscritorioOut(EscritorioBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    logo_path: str | None = None
    # URL para o frontend exibir o logo (endpoint autenticado)
    logo_url: str | None = None
    # 'antes' da comparacao, quando o logo passa por remocao de fundo
    logo_original_url: str | None = None

"""A pagina publica de verificacao — o destino do QR carimbado no PDF.

E a unica rota que responde sem autenticacao, entao os dois riscos que
importam sao: aceitar o que nao deveria (documento apagado, ainda em
processamento) e devolver mais do que deveria (qualquer dado do cliente).
"""

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.api.routes import verificacao
from app.models import Documento, Escritorio, StatusDocumento, Tenant

CODIGO = "AB12CD34"


@pytest.fixture
def cliente(db) -> TestClient:  # noqa: ANN001
    tenant = Tenant(nome="Escritorio Teste", slug="teste", ativo=True)
    db.add(tenant)
    db.flush()
    db.add(
        Escritorio(
            tenant_id=tenant.id,
            razao_social="Silveira Advogados",
            signatario_nome="Antonio Jose Silveira",
            signatario_oab="123456/SP",
        )
    )

    def documento(codigo: str, **extra) -> Documento:  # noqa: ANN003
        campos = {
            "tenant_id": tenant.id,
            "usuario_id": 1,
            "nome_original": "peticao.docx",
            "status": StatusDocumento.PRONTO,
            "codigo_verificacao": codigo,
            "paginas": 4,
            "hash_sha256": "a" * 64,
            "processado_em": datetime.now(timezone.utc),
        }
        return Documento(**{**campos, **extra})

    db.add_all(
        [
            documento(CODIGO),
            documento("DEADBEEF", status=StatusDocumento.PROCESSANDO),
            documento("FEEDFACE", deleted_at=datetime.now(timezone.utc)),
        ]
    )
    db.commit()

    app = FastAPI()
    app.include_router(verificacao.router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


@pytest.mark.parametrize(
    "codigo",
    [
        CODIGO,
        CODIGO.lower(),  # o QR abre em minusculas em alguns leitores
        "AB12-CD34",  # como aparece impresso no rodape
        " AB12CD34 ",  # copiado e colado com sobra
    ],
)
def test_aceita_o_codigo_em_qualquer_formato(cliente, codigo):  # noqa: ANN001
    resposta = cliente.get(f"/api/verificar/{codigo}")
    assert resposta.status_code == 200
    # sempre devolvido no formato ditavel por telefone
    assert resposta.json()["codigo"] == "AB12-CD34"


def test_mostra_quem_assinou(cliente):  # noqa: ANN001
    dados = cliente.get(f"/api/verificar/{CODIGO}").json()
    assert dados["autentico"] is True
    assert dados["escritorio"] == "Silveira Advogados"
    assert dados["signatario"] == "Antonio Jose Silveira"
    assert dados["hash_sha256"] == "a" * 64


@pytest.mark.parametrize(
    ("codigo", "porque"),
    [
        ("DEADBEEF", "documento ainda em processamento nao esta assinado"),
        ("FEEDFACE", "documento apagado nao pode ser confirmado"),
        ("00000000", "codigo inexistente"),
        ("ZZZZZZZZ", "fora do alfabeto hexadecimal"),
        ("AB12", "curto demais"),
    ],
)
def test_recusa(cliente, codigo, porque):  # noqa: ANN001
    assert cliente.get(f"/api/verificar/{codigo}").status_code == 404, porque


def test_nao_vaza_dado_do_cliente(cliente):  # noqa: ANN001
    """A resposta e publica: nada de destinatario, caminho de arquivo ou ids.

    Quem verifica ja tem o PDF em maos; o que falta e saber se e legitimo.
    """
    dados = cliente.get(f"/api/verificar/{CODIGO}").json()
    proibidos = {
        "id",
        "tenant_id",
        "usuario_id",
        "caminho_final",
        "caminho_original",
        "envios",
        "destinatario",
        "email",
        "erro_msg",
    }
    assert not (proibidos & set(dados))

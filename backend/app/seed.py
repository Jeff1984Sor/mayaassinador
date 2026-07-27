"""Seed inicial: tenant, escritorio, configuracao padrao e usuario admin.

Idempotente — pode rodar quantas vezes quiser, nao duplica nada.

Uso no prod2:
    cd ~/mayaassinador/backend
    source .venv/bin/activate
    SEED_EMAIL=jeff@mayacorp.com.br SEED_SENHA='umaSenhaForte' python -m app.seed
"""

import os
import sys

from sqlalchemy import select

from app.core.security import hash_senha
from app.db.session import SessionLocal
from app.models import ConfiguracaoTenant, Escritorio, Tenant, Usuario

TENANT_SLUG = os.getenv("SEED_TENANT_SLUG", "escritorio")
TENANT_NOME = os.getenv("SEED_TENANT_NOME", "Escritorio Modelo")
ADMIN_NOME = os.getenv("SEED_NOME", "Jeff")
ADMIN_EMAIL = os.getenv("SEED_EMAIL", "").strip().lower()
ADMIN_SENHA = os.getenv("SEED_SENHA", "")


def main() -> int:
    if not ADMIN_EMAIL or not ADMIN_SENHA:
        print("ERRO: defina SEED_EMAIL e SEED_SENHA.", file=sys.stderr)
        return 1
    if len(ADMIN_SENHA) < 8:
        print("ERRO: SEED_SENHA precisa de ao menos 8 caracteres.", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == TENANT_SLUG))
        if tenant is None:
            tenant = Tenant(nome=TENANT_NOME, slug=TENANT_SLUG, ativo=True)
            db.add(tenant)
            db.flush()
            print(f"[+] tenant criado: {tenant.slug}")
        else:
            print(f"[=] tenant ja existe: {tenant.slug}")

        # Dados do escritorio: placeholder, preenchido de verdade na tela da F2
        if db.scalar(select(Escritorio).where(Escritorio.tenant_id == tenant.id)) is None:
            db.add(Escritorio(tenant_id=tenant.id, razao_social=TENANT_NOME))
            print("[+] escritorio (placeholder) criado")
        else:
            print("[=] escritorio ja existe")

        if db.scalar(
            select(ConfiguracaoTenant).where(ConfiguracaoTenant.tenant_id == tenant.id)
        ) is None:
            db.add(ConfiguracaoTenant(tenant_id=tenant.id))
            print("[+] configuracao padrao criada")
        else:
            print("[=] configuracao ja existe")

        usuario = db.scalar(
            select(Usuario).where(
                Usuario.tenant_id == tenant.id, Usuario.email == ADMIN_EMAIL
            )
        )
        if usuario is None:
            db.add(
                Usuario(
                    tenant_id=tenant.id,
                    nome=ADMIN_NOME,
                    email=ADMIN_EMAIL,
                    senha_hash=hash_senha(ADMIN_SENHA),
                    ativo=True,
                )
            )
            print(f"[+] usuario criado: {ADMIN_EMAIL}")
        else:
            usuario.senha_hash = hash_senha(ADMIN_SENHA)
            print(f"[=] usuario ja existe — senha atualizada: {ADMIN_EMAIL}")

        db.commit()
        print(f"\nSeed concluido. Login em /{TENANT_SLUG} com {ADMIN_EMAIL}")
        return 0
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        print(f"ERRO no seed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

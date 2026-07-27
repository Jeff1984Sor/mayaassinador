"""Importa todos os models para que o Alembic os enxergue no metadata."""

from app.models.configuracao import ConfiguracaoTenant
from app.models.documento import Documento, StatusDocumento
from app.models.envio_email import EnvioEmail, StatusEnvio
from app.models.escritorio import Escritorio
from app.models.evento import EventoDocumento, TipoEvento
from app.models.tenant import Tenant
from app.models.usuario import Usuario

__all__ = [
    "ConfiguracaoTenant",
    "Documento",
    "StatusDocumento",
    "EnvioEmail",
    "StatusEnvio",
    "Escritorio",
    "EventoDocumento",
    "TipoEvento",
    "Tenant",
    "Usuario",
]

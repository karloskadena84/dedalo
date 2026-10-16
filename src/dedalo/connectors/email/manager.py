"""Gestor de conectores de correo. Controla cuál está activo."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from dedalo.connectors.base import BaseConnector
from dedalo.connectors.email.gmail import GmailConnector
from dedalo.connectors.email.imap import IMAPConnector
from dedalo.utils.config import settings


class EmailConnectorManager:
    """Gestiona los conectores de correo disponibles y el activo."""

    AVAILABLE = {
        "gmail": GmailConnector,
        "imap": IMAPConnector,
        # "outlook": OutlookConnector,  # se añadirá después
    }

    def __init__(self):
        settings.ensure_data_dir()
        self._active_file = settings.data_dir / "connectors" / "active_email.json"

    def list_available(self) -> list[str]:
        return list(self.AVAILABLE.keys())

    def get_connector(self, provider: str, account: str = "default") -> BaseConnector:
        if provider not in self.AVAILABLE:
            raise ValueError(
                f"Proveedor '{provider}' no soportado. Disponibles: {self.list_available()}"
            )
        return self.AVAILABLE[provider](account=account)

    def set_active(self, provider: str, account: str = "default") -> None:
        data = {"provider": provider, "account": account}
        self._active_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get_active(self) -> Optional[BaseConnector]:
        if not self._active_file.exists():
            return None
        data = json.loads(self._active_file.read_text(encoding="utf-8"))
        provider = data.get("provider")
        account = data.get("account", "default")
        if not provider:
            return None
        connector = self.get_connector(provider, account)
        if not connector.is_configured():
            return None
        return connector

    def has_active_connector(self) -> bool:
        connector = self.get_active()
        return connector is not None and connector.is_configured()

    def require_active(self) -> BaseConnector:
        """Devuelve el conector activo o lanza error claro."""
        connector = self.get_active()
        if connector is None:
            raise RuntimeError(
                "No hay ningún conector de correo configurado.\n"
                "Ejecuta: dedalo connectors add gmail   (o imap)"
            )
        return connector

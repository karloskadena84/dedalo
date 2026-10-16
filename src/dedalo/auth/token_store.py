"""Almacenamiento seguro de tokens de autenticación."""

from __future__ import annotations

import json
import keyring
from typing import Any, Optional

SERVICE_NAME = "dedalo"


class TokenStore:
    """Guarda y recupera tokens usando el keyring del sistema."""

    def save(self, provider: str, account: str, data: dict[str, Any]) -> None:
        key = f"{provider}:{account}"
        keyring.set_password(SERVICE_NAME, key, json.dumps(data))

    def load(self, provider: str, account: str) -> Optional[dict[str, Any]]:
        key = f"{provider}:{account}"
        raw = keyring.get_password(SERVICE_NAME, key)
        if raw is None:
            return None
        return json.loads(raw)

    def delete(self, provider: str, account: str) -> None:
        key = f"{provider}:{account}"
        try:
            keyring.delete_password(SERVICE_NAME, key)
        except keyring.errors.PasswordDeleteError:
            pass

    def list_accounts(self, provider: str) -> list[str]:
        # keyring no tiene listado nativo portable; se mantiene un índice simple
        index_key = f"{provider}:__index__"
        raw = keyring.get_password(SERVICE_NAME, index_key)
        if raw is None:
            return []
        return json.loads(raw)

    def add_to_index(self, provider: str, account: str) -> None:
        accounts = self.list_accounts(provider)
        if account not in accounts:
            accounts.append(account)
            index_key = f"{provider}:__index__"
            keyring.set_password(SERVICE_NAME, index_key, json.dumps(accounts))

"""Interfaz base para todos los conectores de Dédalo."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseConnector(ABC):
    """Contrato que debe cumplir cualquier conector."""

    name: str = "base"
    provider: str = "base"

    @abstractmethod
    def is_configured(self) -> bool:
        """Devuelve True si el conector tiene credenciales válidas."""
        ...

    @abstractmethod
    def configure(self, **kwargs: Any) -> None:
        """Inicia el flujo de configuración (OAuth o credenciales)."""
        ...

    @abstractmethod
    def test_connection(self) -> bool:
        """Verifica que la conexión funciona."""
        ...

    def get_status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "provider": self.provider,
            "configured": self.is_configured(),
        }

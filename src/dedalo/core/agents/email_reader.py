"""Agente lector y priorizador de correos — lógica real."""

from __future__ import annotations

import re
from typing import Any

from dedalo.connectors.base import BaseConnector
from dedalo.connectors.email.gmail import GmailConnector
from dedalo.connectors.email.imap import IMAPConnector
from dedalo.connectors.email.manager import EmailConnectorManager


class EmailReaderAgent:
    """
    Lee correos del conector activo y aplica reglas de prioridad e ignorados.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.priorities: list[str] = self.config.get("priorities", [])
        self.high_priority_rules: list[str] = self.config.get("high_priority_rules", [])
        self.ignore_rules: list[str] = self.config.get("ignore_rules", [])
        self.max_results: int = int(self.config.get("max_results", 20))

    def run(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = context or {}
        manager = EmailConnectorManager()
        connector = manager.require_active()

        raw_emails = self._fetch(connector)
        prioritized = []
        ignored = []
        normal = []

        for mail in raw_emails:
            if self._should_ignore(mail):
                ignored.append(mail)
                continue
            score, reason = self._score(mail)
            enriched = {
                **mail,
                "priority_score": score,
                "priority_reason": reason,
                "is_priority": score > 0,
            }
            if score > 0:
                prioritized.append(enriched)
            else:
                normal.append(enriched)

        # Ordenar prioritarios de mayor a menor score
        prioritized.sort(key=lambda m: m["priority_score"], reverse=True)

        return {
            "status": "ok",
            "agent": "GmailReaderAgent",
            "total_fetched": len(raw_emails),
            "prioritized": prioritized,
            "normal": normal,
            "ignored_count": len(ignored),
            "priorities_config": self.priorities,
            "ignore_rules": self.ignore_rules,
            "message": (
                f"Leídos {len(raw_emails)} correos → "
                f"{len(prioritized)} prioritarios, "
                f"{len(normal)} normales, "
                f"{len(ignored)} ignorados"
            ),
        }

    def _fetch(self, connector: BaseConnector) -> list[dict[str, Any]]:
        if isinstance(connector, GmailConnector):
            return connector.fetch_emails(
                max_results=self.max_results,
                query="is:unread OR newer_than:7d",
                include_body=True,
            )
        if isinstance(connector, IMAPConnector):
            return connector.fetch_emails(
                max_results=self.max_results,
                query="UNSEEN",
                include_body=True,
            )
        raise RuntimeError(f"Conector no soportado para lectura: {type(connector)}")

    def _should_ignore(self, mail: dict[str, Any]) -> bool:
        text = f"{mail.get('from', '')} {mail.get('subject', '')} {mail.get('snippet', '')}".lower()
        for rule in self.ignore_rules:
            rule_l = rule.lower().strip()
            if rule_l and rule_l in text:
                return True
        return False

    def _score(self, mail: dict[str, Any]) -> tuple[int, str]:
        """Devuelve (score, razón). Score > 0 = prioritario."""
        text = f"{mail.get('from', '')} {mail.get('subject', '')} {mail.get('snippet', '')} {mail.get('body', '')[:500]}".lower()
        score = 0
        reasons: list[str] = []

        # Reglas de alta prioridad explícitas
        for rule in self.high_priority_rules:
            rule_l = rule.lower().strip()
            if rule_l and rule_l in text:
                score += 10
                reasons.append(f"regla alta: '{rule}'")

        # Categorías de prioridad definidas por el usuario
        for cat in self.priorities:
            cat_l = cat.lower().strip()
            if not cat_l:
                continue
            # Coincidencia simple por palabra/frase
            if cat_l in text:
                score += 5
                reasons.append(f"categoría: '{cat}'")
            else:
                # Variantes comunes
                variants = self._variants(cat_l)
                for v in variants:
                    if v in text:
                        score += 4
                        reasons.append(f"categoría (variante): '{cat}'")
                        break

        # Señales genéricas de urgencia
        urgency = ["urgente", "urgent", "asap", "inmediato", "importante", "priority", "acción requerida"]
        for u in urgency:
            if u in text:
                score += 3
                reasons.append(f"urgencia: '{u}'")
                break

        reason = "; ".join(reasons) if reasons else "sin coincidencias"
        return score, reason

    @staticmethod
    def _variants(term: str) -> list[str]:
        """Genera variantes simples en español/inglés."""
        mapping = {
            "clientes": ["cliente", "customer", "client"],
            "facturas": ["factura", "invoice", "billing", "pago"],
            "oportunidades": ["oportunidad", "lead", "prospecto", "deal"],
            "soporte": ["support", "ticket", "ayuda", "help"],
            "internos": ["interno", "internal", "equipo", "team"],
        }
        return mapping.get(term, [term])

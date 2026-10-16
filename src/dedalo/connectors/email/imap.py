"""Conector IMAP genérico con lectura real de correos."""

from __future__ import annotations

import email
import imaplib
import re
from datetime import timezone
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Any, Optional

from dedalo.auth.token_store import TokenStore
from dedalo.connectors.base import BaseConnector


class IMAPConnector(BaseConnector):
    name = "imap"
    provider = "imap"

    def __init__(self, account: str = "default"):
        self.account = account
        self.token_store = TokenStore()

    def is_configured(self) -> bool:
        data = self.token_store.load(self.provider, self.account)
        return data is not None and all(
            k in data for k in ("host", "port", "email", "password")
        )

    def configure(
        self,
        host: Optional[str] = None,
        port: int = 993,
        email: Optional[str] = None,
        password: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        if not all([host, email, password]):
            raise ValueError(
                "Se requieren host, email y password (o contraseña de aplicación)."
            )
        data = {
            "host": host,
            "port": port,
            "email": email,
            "password": password,
            "use_ssl": kwargs.get("use_ssl", True),
        }
        self.token_store.save(self.provider, self.account, data)
        self.token_store.add_to_index(self.provider, self.account)

    def test_connection(self) -> bool:
        try:
            mail = self._connect()
            mail.logout()
            return True
        except Exception:
            return False

    def _connect(self) -> imaplib.IMAP4:
        data = self.token_store.load(self.provider, self.account)
        if not data:
            raise RuntimeError("IMAP no está configurado.")
        if data.get("use_ssl", True):
            mail = imaplib.IMAP4_SSL(data["host"], data["port"])
        else:
            mail = imaplib.IMAP4(data["host"], data["port"])
        mail.login(data["email"], data["password"])
        return mail

    def get_connection(self):
        return self._connect()

    def fetch_emails(
        self,
        max_results: int = 20,
        query: str = "UNSEEN",
        include_body: bool = True,
        mailbox: str = "INBOX",
    ) -> list[dict[str, Any]]:
        """Obtiene correos vía IMAP. query: criterio IMAP (UNSEEN, ALL, etc.)."""
        mail = self._connect()
        try:
            mail.select(mailbox)
            status, data = mail.search(None, query)
            if status != "OK" or not data or not data[0]:
                return []

            msg_ids = data[0].split()
            msg_ids = list(reversed(msg_ids))[:max_results]
            emails: list[dict[str, Any]] = []

            for mid in msg_ids:
                status, msg_data = mail.fetch(mid, "(RFC822)")
                if status != "OK" or not msg_data or not msg_data[0]:
                    continue
                raw = msg_data[0][1]
                if not isinstance(raw, bytes):
                    continue
                msg = email.message_from_bytes(raw)
                emails.append(self._parse_message(msg, mid.decode(), include_body))

            return emails
        finally:
            try:
                mail.logout()
            except Exception:
                pass

    def _parse_message(
        self, msg: email.message.Message, msg_id: str, include_body: bool
    ) -> dict[str, Any]:
        subject = self._decode_header_value(msg.get("Subject", "(sin asunto)"))
        from_ = self._decode_header_value(msg.get("From", ""))
        to = self._decode_header_value(msg.get("To", ""))
        date_str = msg.get("Date", "")
        try:
            dt = parsedate_to_datetime(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            date_iso = dt.isoformat()
        except Exception:
            date_iso = date_str

        body = ""
        if include_body:
            body = self._extract_body(msg)

        return {
            "id": msg_id,
            "thread_id": msg.get("Message-ID", msg_id),
            "from": from_,
            "to": to,
            "subject": subject,
            "date": date_iso,
            "snippet": body[:200].replace("\n", " ") if body else "",
            "body": body,
            "labels": [],
            "provider": "imap",
        }

    def _decode_header_value(self, value: str) -> str:
        if not value:
            return ""
        parts = decode_header(value)
        result = []
        for part, charset in parts:
            if isinstance(part, bytes):
                result.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                result.append(part)
        return " ".join(result)

    def _extract_body(self, msg: email.message.Message) -> str:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        return payload.decode(charset, errors="replace")
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        text = payload.decode(charset, errors="replace")
                        return re.sub(r"<[^>]+>", " ", text)
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
        return ""

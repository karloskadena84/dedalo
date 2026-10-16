"""Conector de Gmail con OAuth 2.0 y lectura real de correos."""

from __future__ import annotations

import base64
import re
from datetime import timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Optional

from dedalo.auth.token_store import TokenStore
from dedalo.connectors.base import BaseConnector
from dedalo.utils.config import settings

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]


class GmailConnector(BaseConnector):
    name = "gmail"
    provider = "gmail"

    def __init__(self, account: str = "default"):
        self.account = account
        self.token_store = TokenStore()
        self._credentials = None
        self._service = None

    def is_configured(self) -> bool:
        data = self.token_store.load(self.provider, self.account)
        return data is not None and "token" in data

    def configure(self, client_secrets_file: Optional[str] = None, **kwargs: Any) -> None:
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError as e:
            raise ImportError(
                "Faltan dependencias de Google. "
                "Instala: pip install google-auth-oauthlib google-api-python-client"
            ) from e

        secrets_path = client_secrets_file or kwargs.get("secrets_file")
        if not secrets_path:
            candidates = [
                settings.data_dir / "connectors" / "gmail_client_secrets.json",
                Path.cwd() / "client_secrets.json",
            ]
            for c in candidates:
                if c.exists():
                    secrets_path = str(c)
                    break

        if not secrets_path or not Path(secrets_path).exists():
            raise FileNotFoundError(
                "No se encontró client_secrets.json.\n"
                "1. Ve a https://console.cloud.google.com/\n"
                "2. Crea un proyecto → APIs & Services → Credentials\n"
                "3. Crea OAuth 2.0 Client ID (Desktop app)\n"
                "4. Descarga el JSON y guárdalo como:\n"
                f"   {settings.data_dir / 'connectors' / 'gmail_client_secrets.json'}"
            )

        flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
        creds = flow.run_local_server(port=0)

        data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes) if creds.scopes else SCOPES,
        }
        self.token_store.save(self.provider, self.account, data)
        self.token_store.add_to_index(self.provider, self.account)
        self._credentials = creds
        self._service = None

    def _load_credentials(self):
        if self._credentials is not None:
            return self._credentials

        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        data = self.token_store.load(self.provider, self.account)
        if not data:
            raise RuntimeError(
                "Gmail no está configurado. Ejecuta: dedalo connectors add gmail"
            )

        creds = Credentials(
            token=data.get("token"),
            refresh_token=data.get("refresh_token"),
            token_uri=data.get("token_uri"),
            client_id=data.get("client_id"),
            client_secret=data.get("client_secret"),
            scopes=data.get("scopes"),
        )

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            data["token"] = creds.token
            self.token_store.save(self.provider, self.account, data)

        self._credentials = creds
        return creds

    def get_service(self):
        if self._service is not None:
            return self._service
        from googleapiclient.discovery import build

        creds = self._load_credentials()
        self._service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        return self._service

    def test_connection(self) -> bool:
        try:
            service = self.get_service()
            profile = service.users().getProfile(userId="me").execute()
            return "emailAddress" in profile
        except Exception:
            return False

    def get_profile_email(self) -> Optional[str]:
        try:
            service = self.get_service()
            profile = service.users().getProfile(userId="me").execute()
            return profile.get("emailAddress")
        except Exception:
            return None

    def fetch_emails(
        self,
        max_results: int = 20,
        query: str = "is:unread",
        include_body: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Obtiene correos de Gmail.

        Returns:
            Lista de dicts con: id, thread_id, from, to, subject, date, snippet, body, labels
        """
        service = self.get_service()
        results = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )
        messages = results.get("messages", [])
        emails: list[dict[str, Any]] = []

        for msg_ref in messages:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_ref["id"], format="full")
                .execute()
            )
            emails.append(self._parse_message(msg, include_body=include_body))

        return emails

    def _parse_message(self, msg: dict, include_body: bool = True) -> dict[str, Any]:
        headers = {
            h["name"].lower(): h["value"]
            for h in msg.get("payload", {}).get("headers", [])
        }
        body = ""
        if include_body:
            body = self._extract_body(msg.get("payload", {}))

        date_str = headers.get("date", "")
        try:
            dt = parsedate_to_datetime(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            date_iso = dt.isoformat()
        except Exception:
            date_iso = date_str

        return {
            "id": msg["id"],
            "thread_id": msg.get("threadId"),
            "from": headers.get("from", ""),
            "to": headers.get("to", ""),
            "subject": headers.get("subject", "(sin asunto)"),
            "date": date_iso,
            "snippet": msg.get("snippet", ""),
            "body": body,
            "labels": msg.get("labelIds", []),
            "provider": "gmail",
        }

    def _extract_body(self, payload: dict) -> str:
        if "body" in payload and payload["body"].get("data"):
            return self._decode(payload["body"]["data"])

        parts = payload.get("parts", [])
        text_plain = None
        text_html = None

        for part in parts:
            mime = part.get("mimeType", "")
            if mime == "text/plain" and part.get("body", {}).get("data"):
                text_plain = self._decode(part["body"]["data"])
            elif mime == "text/html" and part.get("body", {}).get("data"):
                text_html = self._decode(part["body"]["data"])
            elif mime.startswith("multipart/"):
                nested = self._extract_body(part)
                if nested:
                    return nested

        if text_plain:
            return text_plain
        if text_html:
            return re.sub(r"<[^>]+>", " ", text_html)
        return ""

    @staticmethod
    def _decode(data: str) -> str:
        try:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        except Exception:
            return ""

    def mark_as_read(self, message_id: str) -> bool:
        try:
            service = self.get_service()
            service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["UNREAD"]},
            ).execute()
            return True
        except Exception:
            return False

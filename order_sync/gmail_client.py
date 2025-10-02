from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


@dataclass
class GmailConfig:
    credentials_file: Path = Path("credentials.json")
    token_file: Path = Path("token.json")
    scopes: tuple[str, ...] = ("https://www.googleapis.com/auth/gmail.readonly",)


class GmailClient:
    def __init__(self, config: GmailConfig | None = None):
        self.config = config or GmailConfig()
        self._service = None

    def _load_credentials(self) -> Credentials:
        creds: Optional[Credentials] = None
        if self.config.token_file.exists():
            creds = Credentials.from_authorized_user_file(str(self.config.token_file), list(self.config.scopes))

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.config.credentials_file), list(self.config.scopes)
                )
                creds = flow.run_local_server(port=0)
            with self.config.token_file.open("w", encoding="utf-8") as token:
                token.write(creds.to_json())
        return creds

    @property
    def service(self):
        if self._service is None:
            creds = self._load_credentials()
            self._service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        return self._service

    def search_messages(self, query: str, max_results: int = 10) -> Iterable[dict]:
        response = (
            self.service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )
        for message in response.get("messages", []):
            yield message

    def get_message(self, message_id: str) -> dict:
        return self.service.users().messages().get(userId="me", id=message_id, format="full").execute()

    @staticmethod
    def _get_subject(message: dict) -> str:
        headers = message.get("payload", {}).get("headers", [])
        for header in headers:
            if header.get("name", "").lower() == "subject":
                return header.get("value", "")
        return ""

    @staticmethod
    def _decode_body(message: dict) -> str:
        payload = message.get("payload", {})
        body_data = ""
        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain":
                    body_data = part.get("body", {}).get("data", "")
                    if body_data:
                        break
        else:
            body_data = payload.get("body", {}).get("data", "")

        if not body_data:
            return ""

        return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")

    def find_status(self, order_number: str, detector: "StatusDetector") -> Tuple[str, Optional[str], Optional[str]]:
        for message_meta in self.search_messages(f'"{order_number}"', max_results=5):
            message = self.get_message(message_meta["id"])
            subject = self._get_subject(message)
            body = self._decode_body(message)
            status, box, pin = detector.detect(subject, body)
            if status:
                return status, box, pin
        return "", None, None


class StatusDetector:
    def __init__(self):
        self.status_keywords: dict[str, tuple[str, ...]] = {
            "キャンセル": ("ご注文のキャンセル",),
            "注文済": ("注文済み:",),
            "配達中": ("発送済み",),
            "返金": ("返金", "返金の確認"),
            "宅配ボックス": ("宅配ボックスに配達しました",),
        }

    def detect(self, subject: str, body: str) -> Tuple[str, Optional[str], Optional[str]]:
        text = f"{subject}\n{body}"
        for status, keywords in self.status_keywords.items():
            if any(keyword in text for keyword in keywords):
                if status == "宅配ボックス":
                    box, pin = self._extract_locker_info(body)
                    return status, box, pin
                return status, None, None

        if "到着" in text and ("お届け済" in text or "配達済" in text):
            return "到着済", None, None

        return "", None, None

    @staticmethod
    def _extract_locker_info(body: str) -> Tuple[Optional[str], Optional[str]]:
        box = None
        pin = None
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        for index, line in enumerate(lines):
            if "ボックス番号" in line and index + 1 < len(lines):
                box = lines[index + 1]
            if "暗証番号" in line and index + 1 < len(lines):
                pin = lines[index + 1]
        return box, pin

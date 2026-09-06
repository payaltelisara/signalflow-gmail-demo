import base64
import hashlib
import secrets
from email.message import EmailMessage
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken

from .config import Settings

GMAIL_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]
TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"


class GmailConfigurationError(ValueError):
    pass


def credential_cipher(settings: Settings) -> Fernet:
    if not settings.credential_encryption_key:
        raise GmailConfigurationError("CREDENTIAL_ENCRYPTION_KEY is required before connecting Gmail")
    try:
        return Fernet(settings.credential_encryption_key.encode())
    except (ValueError, TypeError) as exc:
        raise GmailConfigurationError("CREDENTIAL_ENCRYPTION_KEY must be a valid Fernet key") from exc


def encrypt_refresh_token(token: str, settings: Settings) -> str:
    return credential_cipher(settings).encrypt(token.encode()).decode()


def decrypt_refresh_token(token: str, settings: Settings) -> str:
    try:
        return credential_cipher(settings).decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise GmailConfigurationError("Stored Gmail credentials cannot be decrypted. Reconnect the mailbox.") from exc


def code_verifier() -> str:
    return secrets.token_urlsafe(64)


def code_challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()


def oauth_url(settings: Settings, state: str, verifier: str) -> str:
    if not settings.gmail_client_id or not settings.gmail_client_secret:
        raise GmailConfigurationError("Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET before connecting Gmail")
    query = urlencode({"client_id": settings.gmail_client_id, "redirect_uri": settings.gmail_redirect_uri, "response_type": "code", "scope": " ".join(GMAIL_SCOPES), "access_type": "offline", "prompt": "consent", "state": state, "code_challenge": code_challenge(verifier), "code_challenge_method": "S256"})
    return f"{AUTH_URL}?{query}"


def exchange_code(settings: Settings, code: str, verifier: str) -> dict:
    response = httpx.post(TOKEN_URL, data={"code": code, "client_id": settings.gmail_client_id, "client_secret": settings.gmail_client_secret, "redirect_uri": settings.gmail_redirect_uri, "grant_type": "authorization_code", "code_verifier": verifier}, timeout=20)
    response.raise_for_status()
    payload = response.json()
    if not payload.get("refresh_token"):
        raise GmailConfigurationError("Google did not return a refresh token. Reconnect and approve access again.")
    return payload


def access_token(settings: Settings, refresh_token: str) -> str:
    response = httpx.post(TOKEN_URL, data={"client_id": settings.gmail_client_id, "client_secret": settings.gmail_client_secret, "refresh_token": refresh_token, "grant_type": "refresh_token"}, timeout=20)
    response.raise_for_status()
    return response.json()["access_token"]


def gmail_request(method: str, path: str, token: str, **kwargs) -> httpx.Response:
    response = httpx.request(method, f"{GMAIL_API}{path}", headers={"Authorization": f"Bearer {token}"}, timeout=25, **kwargs)
    response.raise_for_status()
    return response


def mailbox_profile(token: str) -> dict:
    return gmail_request("GET", "/profile", token).json()


def google_email(token: str) -> str:
    response = httpx.get("https://openidconnect.googleapis.com/v1/userinfo", headers={"Authorization": f"Bearer {token}"}, timeout=20)
    response.raise_for_status()
    email = response.json().get("email")
    if not email:
        raise GmailConfigurationError("Google did not return the mailbox email")
    return str(email).lower()


def send_message(token: str, *, to_email: str, subject: str, body: str, thread_id: str | None = None, in_reply_to: str | None = None) -> dict:
    message = EmailMessage()
    message["To"] = to_email
    message["Subject"] = subject
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
        message["References"] = in_reply_to
    message.set_content(body)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    payload = {"raw": raw}
    if thread_id:
        payload["threadId"] = thread_id
    return gmail_request("POST", "/messages/send", token, json=payload).json()


def history(token: str, start_history_id: str) -> dict:
    return gmail_request("GET", "/history", token, params={"startHistoryId": start_history_id, "historyTypes": "messageAdded"}).json()


def message(token: str, message_id: str) -> dict:
    return gmail_request("GET", f"/messages/{message_id}", token, params={"format": "full"}).json()


def header(payload: dict, name: str) -> str | None:
    for item in payload.get("headers", []):
        if item.get("name", "").lower() == name.lower():
            return item.get("value")
    return None


def decode_body(data: str) -> str:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding).decode(errors="replace")


def message_text(payload: dict) -> str:
    body = payload.get("body", {}).get("data")
    if body:
        return decode_body(body)
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data")
            if data:
                return decode_body(data)
    return ""

from __future__ import annotations

import os
import secrets
import smtplib
import ssl
from collections import deque
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator


ROOT = Path(__file__).parent
MAX_RECIPIENTS = 20
activity: deque[dict[str, str | int]] = deque(maxlen=12)

app = FastAPI(title="SignalFlow Gmail campaign demo")


class CampaignRequest(BaseModel):
    recipients: list[str] = Field(min_length=1, max_length=MAX_RECIPIENTS)
    subject: str = Field(min_length=1, max_length=180)
    body: str = Field(min_length=1, max_length=10_000)

    @field_validator("recipients")
    @classmethod
    def clean_recipients(cls, recipients: list[str]) -> list[str]:
        cleaned = []
        for recipient in recipients:
            address = recipient.strip()
            if "@" not in address or address.startswith("@") or address.endswith("@"):
                raise ValueError(f"Invalid email address: {recipient}")
            cleaned.append(address)
        return list(dict.fromkeys(cleaned))


def setting(name: str) -> str:
    return os.getenv(name, "").strip()


def configured() -> bool:
    return all(setting(name) for name in ("SHOWCASE_ADMIN_TOKEN", "SMTP_USERNAME", "SMTP_PASSWORD"))


@app.get("/")
def home() -> FileResponse:
    return FileResponse(ROOT / "index.html")


@app.get("/api/status")
def status() -> dict[str, object]:
    return {
        "configured": configured(),
        "sender": setting("SMTP_USERNAME") if configured() else None,
        "dry_run": setting("SMTP_DRY_RUN").lower() == "true",
        "activity": list(activity),
    }


@app.post("/api/send")
def send_campaign(payload: CampaignRequest, x_admin_token: str | None = Header(default=None)) -> dict[str, object]:
    admin_token = setting("SHOWCASE_ADMIN_TOKEN")
    if not admin_token or not x_admin_token or not secrets.compare_digest(admin_token, x_admin_token):
        raise HTTPException(status_code=401, detail="Enter the campaign owner token to send email.")
    if not configured():
        raise HTTPException(status_code=503, detail="Gmail SMTP is not configured on this deployment.")

    event = {
        "timestamp": datetime.now(timezone.utc).strftime("%d %b, %H:%M UTC"),
        "recipients": len(payload.recipients),
        "subject": payload.subject,
        "status": "dry run" if setting("SMTP_DRY_RUN").lower() == "true" else "sent",
    }
    if event["status"] == "dry run":
        activity.appendleft(event)
        return {"message": "Dry run complete. No email was sent.", "event": event}

    message = EmailMessage()
    message["From"] = setting("SMTP_USERNAME")
    message["To"] = ", ".join(payload.recipients)
    message["Subject"] = payload.subject
    message.set_content(payload.body)

    try:
        with smtplib.SMTP(setting("SMTP_HOST") or "smtp.gmail.com", int(setting("SMTP_PORT") or "587"), timeout=20) as server:
            server.ehlo()
            if setting("SMTP_USE_SSL").lower() != "true":
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
            server.login(setting("SMTP_USERNAME"), setting("SMTP_PASSWORD"))
            server.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        raise HTTPException(status_code=502, detail=f"Gmail could not accept the message: {error}") from error

    activity.appendleft(event)
    return {"message": f"Gmail accepted delivery to {len(payload.recipients)} recipient(s).", "event": event}

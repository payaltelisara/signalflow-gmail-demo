import imaplib
import smtplib
import ssl
from email import message_from_bytes
from email.message import EmailMessage
from email.utils import make_msgid, parseaddr

from .config import Settings


class SmtpImapConfigurationError(ValueError):
    pass


def configured(settings: Settings) -> bool:
    return bool(settings.credential_encryption_key and settings.smtp_host and settings.smtp_username and settings.smtp_password and settings.imap_host and settings.imap_username and settings.imap_password)


def setup_required(settings: Settings) -> list[str]:
    required = ("CREDENTIAL_ENCRYPTION_KEY", "SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "IMAP_HOST", "IMAP_USERNAME", "IMAP_PASSWORD")
    return [item for item in required if not getattr(settings, item.lower())]


def _smtp(settings: Settings):
    if not settings.smtp_host or not settings.smtp_username or not settings.smtp_password:
        raise SmtpImapConfigurationError("Set SMTP_HOST, SMTP_USERNAME, and SMTP_PASSWORD before connecting the local mailbox")
    if settings.smtp_use_ssl:
        client = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=ssl.create_default_context(), timeout=20)
    else:
        client = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20)
        client.starttls(context=ssl.create_default_context())
    client.login(settings.smtp_username, settings.smtp_password)
    return client


def verify(settings: Settings) -> str:
    if not configured(settings):
        raise SmtpImapConfigurationError(f"Mailbox setup is incomplete: {', '.join(setup_required(settings))}")
    with _smtp(settings) as client:
        client.noop()
    with imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port) as client:
        client.login(settings.imap_username, settings.imap_password)
        status, _ = client.select(settings.imap_folder, readonly=True)
        if status != "OK":
            raise SmtpImapConfigurationError(f"Cannot open IMAP folder {settings.imap_folder}")
    return settings.smtp_username.lower()


def send(settings: Settings, *, to_email: str, subject: str, body: str, in_reply_to: str | None = None) -> dict:
    message = EmailMessage()
    message["From"] = settings.smtp_username
    message["To"] = to_email
    message["Subject"] = subject
    message_id = make_msgid(domain=settings.smtp_username.split("@")[-1])
    message["Message-ID"] = message_id
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
        message["References"] = in_reply_to
    message.set_content(body)
    with _smtp(settings) as client:
        client.send_message(message)
    return {"id": message_id, "threadId": in_reply_to or message_id, "rfc_message_id": message_id}


def messages_since(settings: Settings, after_uid: str | None = None) -> list[dict]:
    if not settings.imap_host or not settings.imap_username or not settings.imap_password:
        raise SmtpImapConfigurationError("Set IMAP_HOST, IMAP_USERNAME, and IMAP_PASSWORD before synchronizing replies")
    records: list[dict] = []
    with imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port) as client:
        client.login(settings.imap_username, settings.imap_password)
        status, _ = client.select(settings.imap_folder, readonly=True)
        if status != "OK":
            raise SmtpImapConfigurationError(f"Cannot open IMAP folder {settings.imap_folder}")
        criteria = "ALL"
        if after_uid and after_uid.isdigit():
            criteria = f"UID {int(after_uid) + 1}:*"
        status, ids = client.uid("search", None, criteria)
        if status != "OK":
            return records
        for uid in ids[0].split():
            status, payload = client.uid("fetch", uid, "(RFC822)")
            if status != "OK" or not payload or not payload[0]:
                continue
            raw = payload[0][1]
            parsed = message_from_bytes(raw)
            sender = parseaddr(parsed.get("From", ""))[1].lower()
            body = ""
            if parsed.is_multipart():
                for part in parsed.walk():
                    if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition", "")).lower():
                        body = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="replace")
                        break
            else:
                body = parsed.get_payload(decode=True).decode(parsed.get_content_charset() or "utf-8", errors="replace")
            records.append({"uid": uid.decode(), "message_id": parsed.get("Message-ID", ""), "in_reply_to": parsed.get("In-Reply-To", ""), "references": parsed.get("References", ""), "from": sender, "subject": parsed.get("Subject", "No subject"), "body": body})
    return records

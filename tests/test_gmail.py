import base64
from unittest.mock import MagicMock, patch

from app.config import Settings
from app.gmail import code_challenge, decode_body, decrypt_refresh_token, encrypt_refresh_token
from app.smtp_imap import configured, send, setup_required


def settings_with_key() -> Settings:
    return Settings(credential_encryption_key="MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=")


def test_refresh_token_round_trip_is_encrypted() -> None:
    settings = settings_with_key()
    encrypted = encrypt_refresh_token("local-test-refresh-token", settings)
    assert "local-test-refresh-token" not in encrypted
    assert decrypt_refresh_token(encrypted, settings) == "local-test-refresh-token"


def test_pkce_challenge_is_stable_and_unpadded() -> None:
    challenge = code_challenge("test-verifier")
    assert challenge == code_challenge("test-verifier")
    assert "=" not in challenge


def test_decode_body_handles_missing_base64_padding() -> None:
    encoded = base64.urlsafe_b64encode(b"hello from Gmail").decode().rstrip("=")
    assert decode_body(encoded) == "hello from Gmail"


def test_smtp_imap_configuration_requires_only_local_settings() -> None:
    settings = Settings(credential_encryption_key="MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=", smtp_host="smtp.gmail.com", smtp_username="sender@example.com", smtp_password="app-password", imap_host="imap.gmail.com", imap_username="sender@example.com", imap_password="app-password")
    assert configured(settings)
    assert setup_required(settings) == []


@patch("app.smtp_imap._smtp")
def test_smtp_message_has_a_stable_rfc_thread_anchor(mock_smtp: MagicMock) -> None:
    settings = Settings(smtp_host="smtp.local", smtp_username="sender@example.com", smtp_password="secret")
    result = send(settings, to_email="recipient@example.com", subject="Hello", body="Test")
    assert result["id"] == result["rfc_message_id"]
    assert result["threadId"] == result["id"]
    mock_smtp.return_value.__enter__.return_value.send_message.assert_called_once()

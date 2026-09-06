"""Provider-neutral integration contracts for the P0 foundation.

This module deliberately contains no vendor SDK calls. Concrete Apollo,
HubSpot, n8n, verification, and sending adapters can be added independently
without leaking provider details into lead or campaign workflows.
"""

import csv
import io
import json
from dataclasses import dataclass
from typing import Protocol

import httpx

from .gmail import GmailConfigurationError, decrypt_refresh_token

APOLLO_API_BASE = "https://api.apollo.io/api/v1"
DISPOSABLE_EMAIL_DOMAINS = {"mailinator.com", "guerrillamail.com", "tempmail.com", "yopmail.com"}
PUBLIC_EMAIL_DOMAINS = {"gmail.com", "googlemail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "proton.me", "protonmail.com"}


@dataclass(frozen=True)
class ProviderDefinition:
    key: str
    label: str
    capabilities: tuple[str, ...]
    credential_fields: tuple[str, ...]
    pricing_mode: str = "optional"


@dataclass(frozen=True)
class ConnectionTestResult:
    status: str
    ready: bool
    detail: str


class ProviderAdapter(Protocol):
    definition: ProviderDefinition

    def test_connection(self, *, has_credentials: bool, configuration: dict) -> ConnectionTestResult: ...


class DeferredProviderAdapter:
    """Safe local adapter used until a provider-specific adapter is installed."""

    def __init__(self, definition: ProviderDefinition):
        self.definition = definition

    def test_connection(self, *, has_credentials: bool, configuration: dict) -> ConnectionTestResult:
        if not has_credentials:
            return ConnectionTestResult("needs_credentials", False, f"{self.definition.label} credentials have not been configured.")
        if not isinstance(configuration, dict):
            return ConnectionTestResult("invalid_configuration", False, "Integration configuration must be an object.")
        return ConnectionTestResult("adapter_pending", False, f"{self.definition.label} is configured. Its live adapter will be enabled in a later P0 batch.")


class IntegrationRegistry:
    def __init__(self, definitions: tuple[ProviderDefinition, ...]):
        self._adapters = {item.key: DeferredProviderAdapter(item) for item in definitions}

    def get(self, provider: str) -> ProviderAdapter | None:
        return self._adapters.get(provider.lower().strip())

    def definitions(self) -> list[ProviderDefinition]:
        return [adapter.definition for adapter in self._adapters.values()]


registry = IntegrationRegistry((
    ProviderDefinition("apollo", "Apollo", ("search_accounts", "search_contacts", "import", "enrich"), ("api_key",)),
    ProviderDefinition("hubspot", "HubSpot", ("upsert_contacts", "upsert_companies", "sync"), ("access_token",)),
    ProviderDefinition("n8n", "n8n", ("emit_webhook", "receive_webhook", "sync"), ("webhook_secret",), "self_hosted"),
    ProviderDefinition("email", "Email provider", ("send", "receive_events", "reply_sync"), ("api_key",)),
    ProviderDefinition("verification", "Email verification", ("verify_email",), ("api_key",)),
))


class ApolloConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class EmailVerificationResult:
    """A provider-neutral verification result.

    The built-in verifier deliberately makes no deliverability claim: it only
    detects clearly unsafe addresses and marks otherwise syntactically valid
    contacts as risky until a human or a configured provider confirms them.
    """

    status: str
    provider: str
    reason: str


def verify_email_locally(email: str | None) -> EmailVerificationResult:
    value = str(email or "").strip().lower()
    if not value or "@" not in value:
        return EmailVerificationResult("not_available", "local_syntax", "No normalized recipient email is available.")
    domain = value.rsplit("@", 1)[1]
    if domain in DISPOSABLE_EMAIL_DOMAINS or domain.endswith(".example"):
        return EmailVerificationResult("invalid", "local_syntax", "Disposable or reserved email domain.")
    if domain in PUBLIC_EMAIL_DOMAINS:
        return EmailVerificationResult("risky", "local_syntax", "Public mailbox domain; require a human verification decision.")
    return EmailVerificationResult("risky", "local_syntax", "Syntax is valid, but live deliverability has not been verified.")


def apollo_api_key(connection: object, settings: object) -> str:
    """Read an Apollo key only in the server process, never in an API response."""
    try:
        credentials = json.loads(decrypt_refresh_token(connection.encrypted_credentials, settings))
    except (GmailConfigurationError, json.JSONDecodeError) as exc:
        raise ApolloConfigurationError("Stored Apollo credentials cannot be used. Reconfigure the integration.") from exc
    key = str(credentials.get("api_key") or "").strip()
    if not key:
        raise ApolloConfigurationError("Apollo API key is required before importing prospects.")
    return key


def apollo_people_search(connection: object, settings: object, *, filters: dict, page: int, per_page: int) -> list[dict]:
    """Search net-new Apollo people and normalize only fields SignalFlow owns.

    Apollo does not return emails from people search, so records may enter the
    canonical pipeline as research-required until a later enrichment batch.
    """
    key = apollo_api_key(connection, settings)
    payload = {**filters, "page": page, "per_page": per_page}
    try:
        response = httpx.post(
            f"{APOLLO_API_BASE}/mixed_people/api_search",
            headers={"x-api-key": key, "Content-Type": "application/json"},
            json=payload,
            timeout=25,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500] or exc.response.reason_phrase
        raise ApolloConfigurationError(f"Apollo search failed ({exc.response.status_code}): {detail}") from exc
    except httpx.HTTPError as exc:
        raise ApolloConfigurationError("Apollo is unavailable. No prospects were imported.") from exc
    data = response.json()
    people = data.get("people") or []
    if not isinstance(people, list):
        raise ApolloConfigurationError("Apollo returned an unexpected people-search response.")
    return [item for item in people if isinstance(item, dict)]


def apollo_people_csv(people: list[dict]) -> bytes:
    """Convert a provider response into the existing, auditable CSV pipeline."""
    rows: list[dict[str, str]] = []
    for person in people:
        organization = person.get("organization") or {}
        rows.append({
            "First Name": str(person.get("first_name") or ""),
            "Last Name": str(person.get("last_name") or ""),
            "Full Name": str(person.get("name") or ""),
            "Email": str(person.get("email") or ""),
            "Job Title": str(person.get("title") or ""),
            "Company": str(organization.get("name") or ""),
            "Company Domain": str(organization.get("primary_domain") or organization.get("website_url") or ""),
            "Country": str(person.get("country") or ""),
            "Source": "apollo",
            "Apollo Person ID": str(person.get("id") or person.get("person_id") or ""),
            "Apollo Organization ID": str(organization.get("id") or ""),
        })
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=["First Name", "Last Name", "Full Name", "Email", "Job Title", "Company", "Company Domain", "Country", "Source", "Apollo Person ID", "Apollo Organization ID"])
    writer.writeheader(); writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def public_connection(connection: object | None, definition: ProviderDefinition) -> dict:
    """Return browser-safe connection data without configuration secrets."""
    if not connection:
        return {
            "provider": definition.key,
            "label": definition.label,
            "status": "not_configured",
            "capabilities": list(definition.capabilities),
            "credential_fields": list(definition.credential_fields),
            "pricing_mode": definition.pricing_mode,
            "configured": False,
            "sync_status": "idle",
            "retry_state": {},
            "last_test_at": None,
            "last_sync_at": None,
            "last_error": None,
        }
    return {
        "id": connection.id,
        "provider": definition.key,
        "label": definition.label,
        "status": connection.status,
        "capabilities": list(definition.capabilities),
        "credential_fields": list(definition.credential_fields),
        "pricing_mode": definition.pricing_mode,
        "configured": bool(connection.encrypted_credentials),
        "configuration": connection.configuration or {},
        "sync_status": connection.sync_status,
        "retry_state": connection.retry_state or {},
        "last_test_at": connection.last_test_at,
        "last_sync_at": connection.last_sync_at,
        "last_error": connection.last_error,
    }

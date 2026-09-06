from types import SimpleNamespace

from app.integrations import apollo_people_csv, registry, public_connection, verify_email_locally


def test_registry_exposes_only_supported_provider_capabilities() -> None:
    apollo = registry.get("apollo")
    assert apollo is not None
    assert "search_contacts" in apollo.definition.capabilities
    assert registry.get("unknown-provider") is None


def test_deferred_adapter_never_claims_a_live_connection() -> None:
    result = registry.get("apollo").test_connection(has_credentials=True, configuration={"region": "us"})
    assert result.status == "adapter_pending"
    assert result.ready is False


def test_public_connection_omits_encrypted_credentials() -> None:
    connection = SimpleNamespace(
        id="integration-1", status="configured", encrypted_credentials="ciphertext", configuration={"region": "us"},
        sync_status="idle", retry_state={}, last_test_at=None, last_sync_at=None, last_error=None,
    )
    data = public_connection(connection, registry.get("apollo").definition)
    assert data["configured"] is True
    assert "encrypted_credentials" not in data
    assert "ciphertext" not in str(data)


def test_apollo_people_are_converted_to_the_canonical_import_shape() -> None:
    content = apollo_people_csv([{
        "id": "apollo-person-1", "first_name": "Maya", "last_name": "Chen", "title": "VP Revenue",
        "organization": {"id": "apollo-org-1", "name": "Lumen Health", "primary_domain": "lumenhealth.example"},
    }]).decode()
    assert "Apollo Person ID" in content
    assert "apollo-person-1" in content
    assert "lumenhealth.example" in content


def test_apollo_rows_keep_a_stable_person_identifier_for_repeat_import_dedupe() -> None:
    content = apollo_people_csv([{"person_id": "apollo-person-2", "name": "Maya Chen"}]).decode()
    assert "apollo-person-2" in content


def test_local_verification_never_claims_live_deliverability() -> None:
    assert verify_email_locally("maya@company.test").status == "risky"
    assert verify_email_locally("maya@mailinator.com").status == "invalid"
    assert verify_email_locally(None).status == "not_available"

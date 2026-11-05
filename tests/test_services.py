from types import SimpleNamespace

from app.services import can_transition_lead_stage, derive_account_enrichment, enrich_from_account, map_headers, next_account_action, next_action, normalize_account, normalize_domain, normalize_row, score_account, score_company_inbox, score_lead


def test_normalize_domain_removes_protocol_and_path():
    assert normalize_domain("https://Example.COM/pricing") == "example.com"


def test_mapping_and_identity_validation():
    mapping = map_headers(["Email", "Company Domain", "Job Title"])
    normalized = normalize_row({"Email": "  MAYA@EXAMPLE.COM ", "Company Domain": "example.com", "Job Title": "VP Sales"}, mapping)
    assert normalized.data["email"] == "maya@example.com"
    assert normalized.data["seniority"] == "vp"
    assert not normalized.errors


def test_missing_identity_is_rejected():
    normalized = normalize_row({"First Name": "Maya"}, {"first_name": "First Name"})
    assert normalized.errors[0]["code"] == "missing_identity"


def test_scoring_and_suppression_are_deterministic():
    data = {"email": "maya@example.com", "company_domain": "example.com", "industry": "SaaS", "employee_band": "51-200", "seniority": "vp", "territory": "NA", "source": "referral", "engagement": "demo"}
    score, qualification, contributions = score_lead(data)
    assert score == 100
    assert qualification == "qualified"
    assert contributions
    suppressed_score, suppressed_qualification, _ = score_lead(data, suppressed=True)
    assert (suppressed_score, suppressed_qualification) == (0, "suppressed")


def test_next_action_follows_qualification():
    assert next_action("qualified", True) == "ready_for_follow_up"
    assert next_action("qualified", False) == "manual_routing_review"
    assert next_action("suppressed", False) == "do_not_contact"


def test_lead_lifecycle_only_allows_forward_transitions():
    assert can_transition_lead_stage("new", "normalized")
    assert can_transition_lead_stage("imported", "normalized")
    assert can_transition_lead_stage("replied", "unsubscribe")
    assert not can_transition_lead_stage("imported", "approved")
    assert not can_transition_lead_stage("qualified", "contacted")


def test_account_export_headers_map_to_company_profile():
    headers = ["Company Name", "Headcount", "Industry", "Website", "Domain URL", "Company Country"]
    mapping = map_headers(headers)
    assert mapping == {"company": "Company Name", "employee_count": "Headcount", "industry": "Industry", "company_domain": "Website", "country": "Company Country"}
    account = normalize_account({"Company Name": "Lumen Health", "Headcount": "180", "Industry": "Healthcare SaaS", "Website": "https://lumenhealth.io", "Company Country": "United States"}, mapping)
    assert not account.errors
    assert account.data["company_domain"] == "lumenhealth.io"
    assert account.data["employee_band"] == "51-200"
    assert account.data["territory"] == "NA"


def test_account_enrichment_fills_missing_values_without_overwriting_contact_data():
    company = SimpleNamespace(id="company-1", domain="northstar-demo.com", name="Northstar Demo", industry="Software", employee_band="51-200", profile_data={"Company Country": "United States"})
    enriched, evidence = enrich_from_account({"company_domain": "northstar-demo.com", "industry": "Fintech", "country": None, "territory": None}, company)
    assert enriched["industry"] == "Fintech"
    assert enriched["company"] == "Northstar Demo"
    assert enriched["employee_band"] == "51-200"
    assert enriched["territory"] == "NA"
    assert evidence["provider"] == "local_account_profile"
    assert evidence["fields_filled"] == ["company", "employee_band", "country", "territory"]


def test_account_export_can_be_qualified_for_contact_sourcing():
    score, qualification, contributions = score_account({"company_domain": "northstar-demo.com", "industry": "Software", "employee_band": "51-200", "territory": "NA"}, {"Total headcount growth (12 months)": "18%", "Total Funding": "$2m", "Description": "Workflow software"})
    assert score == 70
    assert qualification == "qualified"
    assert next_account_action(qualification, True) == "source_contacts"
    assert contributions


def test_account_enrichment_derives_growth_completeness_and_provenance():
    enrichment = derive_account_enrichment({"company_domain": "northstar-demo.com", "industry": "Software", "employee_band": "51-200", "country": "United States"}, {"Total headcount growth (12 months)": "18%", "Founding Year": "2018", "Total Funding": "$2m", "Description": "Workflow software", "Last Updated": "2026-08-01"})
    assert enrichment["version"] == "account-enrichment-v2"
    assert enrichment["derived"]["growth_status"] == "positive"
    assert enrichment["derived"]["company_age_years"] >= 1
    assert enrichment["derived"]["profile_completeness"] > 0


def test_account_import_accepts_a_real_company_email_but_not_a_company_name_as_one():
    mapping = map_headers(["Company Name", "Company Email", "Domain URL"])
    account = normalize_account({"Company Name": "Northstar", "Company Email": "team@northstar-demo.com", "Domain URL": "northstar-demo.com"}, mapping)
    assert account.data["recipient_email"] == "team@northstar-demo.com"
    assert not account.errors
    name_mapping = map_headers(["Company Name for Emails"])
    assert "email" not in name_mapping


def test_company_inbox_requires_an_email_and_qualified_account():
    score, qualification, contributions = score_company_inbox(70, "qualified", "team@northstar-demo.com")
    assert score == 85
    assert qualification == "qualified"
    assert contributions[-1]["name"] == "supplied_company_email"
    assert score_company_inbox(70, "qualified", None)[1] != "qualified"

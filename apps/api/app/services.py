import csv
import io
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse

from email_validator import EmailNotValidError, validate_email

PUBLIC_EMAIL_DOMAINS = {"gmail.com", "googlemail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "proton.me", "protonmail.com"}
COUNTRY_TERRITORY = {
    "united states": ("United States", "NA"), "usa": ("United States", "NA"), "us": ("United States", "NA"),
    "canada": ("Canada", "NA"), "united kingdom": ("United Kingdom", "EMEA"), "uk": ("United Kingdom", "EMEA"),
    "india": ("India", "APAC"), "australia": ("Australia", "APAC"), "germany": ("Germany", "EMEA"),
}
SENIORITY_PATTERNS = [("c_suite", r"\b(ceo|cto|cfo|coo|cmo|chief)\b"), ("vp", r"\b(vp|vice president)\b"), ("director", r"\bdirector\b"), ("manager", r"\b(manager|head of)\b"), ("individual_contributor", r"\b(engineer|analyst|specialist|coordinator)\b")]

# A lead may only move forward through this lifecycle. The legacy "new" value
# is treated as "imported" so existing workspaces can adopt the flow safely.
LEAD_LIFECYCLE_TRANSITIONS = {
    "imported": {"normalized"},
    "normalized": {"enriching", "disqualified"},
    "enriching": {"enriched", "disqualified"},
    "enriched": {"verifying", "researching", "disqualified"},
    "verifying": {"verified", "invalid"},
    "verified": {"researching", "disqualified"},
    "invalid": {"disqualified"},
    "researching": {"qualified", "disqualified"},
    "qualified": {"awaiting_approval", "disqualified"},
    "awaiting_approval": {"approved", "disqualified"},
    "approved": {"queued"},
    "queued": {"contacted"},
    "contacted": {"replied"},
    "replied": {"positive", "question", "not_now", "not_interested", "unsubscribe", "ooo", "wrong_person", "referral", "unknown"},
}


@dataclass
class NormalizedRow:
    data: dict
    errors: list[dict]


def clean(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_domain(value: object | None) -> str | None:
    text = clean(value)
    if not text:
        return None
    candidate = text.lower()
    if "://" not in candidate:
        candidate = "https://" + candidate
    parsed = urlparse(candidate)
    domain = (parsed.hostname or "").lower().strip(".")
    return domain or None


def normalize_email(value: object | None) -> tuple[str | None, str | None]:
    text = clean(value)
    if not text:
        return None, None
    try:
        result = validate_email(text, check_deliverability=False)
        return result.normalized.lower(), None
    except EmailNotValidError as exc:
        return None, str(exc)


def employee_band(value: object | None) -> str | None:
    text = clean(value)
    if not text:
        return None
    digits = re.findall(r"\d+", text.replace(",", ""))
    if not digits:
        return text.lower()
    number = int(digits[0])
    if number < 11: return "1-10"
    if number < 51: return "11-50"
    if number < 201: return "51-200"
    if number < 501: return "201-500"
    if number < 1001: return "501-1000"
    return "1001+"


def seniority(value: object | None) -> str | None:
    text = (clean(value) or "").lower()
    for label, pattern in SENIORITY_PATTERNS:
        if re.search(pattern, text):
            return label
    return "unknown" if text else None


def normalize_country(value: object | None) -> tuple[str | None, str | None]:
    text = clean(value)
    if not text:
        return None, None
    return COUNTRY_TERRITORY.get(text.lower(), (text.title(), "Other"))


def map_headers(headers: list[str]) -> dict[str, str]:
    aliases = {
        "first_name": {"first name", "firstname", "first"}, "last_name": {"last name", "lastname", "last"},
        "full_name": {"full name", "name", "contact name"}, "email": {"email", "email address", "work email", "company email", "company email address", "general email"},
        "company": {"company", "company name", "company name for emails", "account"}, "company_domain": {"company domain", "domain", "domain url", "website"},
        "job_title": {"job title", "title", "role"}, "country": {"country", "company country", "location"}, "territory": {"territory", "region"},
        "industry": {"industry", "vertical"}, "employee_count": {"employee count", "employees", "headcount", "employee size"},
        "source": {"source", "lead source"}, "owner": {"owner", "rep"}, "notes": {"notes", "note"},
        "engagement": {"engagement", "engagement signal"}, "intent": {"intent", "intent signal"},
    }
    result: dict[str, str] = {}
    for header in headers:
        key = header.strip().lower().replace("_", " ")
        for field, candidates in aliases.items():
            if key in candidates and field not in result:
                result[field] = header
    return result


def normalize_row(raw: dict, mapping: dict[str, str]) -> NormalizedRow:
    pick = lambda field: raw.get(mapping.get(field, ""))
    email, email_error = normalize_email(pick("email"))
    full_name = clean(pick("full_name"))
    first_name, last_name = clean(pick("first_name")), clean(pick("last_name"))
    if not full_name:
        full_name = " ".join(part for part in [first_name, last_name] if part) or None
    company_domain = normalize_domain(pick("company_domain"))
    if not company_domain and email and email.split("@", 1)[1] not in PUBLIC_EMAIL_DOMAINS:
        company_domain = email.split("@", 1)[1]
    country, derived_territory = normalize_country(pick("country"))
    data = {
        "email": email, "first_name": first_name, "last_name": last_name, "full_name": full_name,
        "company": clean(pick("company")), "company_domain": company_domain, "job_title": clean(pick("job_title")),
        "seniority": seniority(pick("job_title")), "country": country, "territory": clean(pick("territory")) or derived_territory,
        "industry": clean(pick("industry")), "employee_band": employee_band(pick("employee_count")),
        "source": (clean(pick("source")) or "csv_import").lower(), "owner": clean(pick("owner")),
        "notes": clean(pick("notes")), "engagement": clean(pick("engagement")), "intent": clean(pick("intent")),
    }
    errors: list[dict] = []
    if email_error:
        errors.append({"field": "email", "code": "invalid_email", "message": email_error})
    if not email and not (full_name and company_domain):
        errors.append({"field": "identity", "code": "missing_identity", "message": "Provide a valid email or full name plus company domain."})
    return NormalizedRow(data=data, errors=errors)


def normalize_account(raw: dict, mapping: dict[str, str]) -> NormalizedRow:
    pick = lambda field: raw.get(mapping.get(field, ""))
    name = clean(pick("company"))
    domain = normalize_domain(pick("company_domain"))
    recipient_email, email_error = normalize_email(pick("email"))
    country, territory = normalize_country(pick("country"))
    data = {
        "company": name,
        "company_domain": domain,
        "industry": clean(pick("industry")),
        "employee_band": employee_band(pick("employee_count")),
        "country": country,
        "territory": territory,
        "recipient_email": recipient_email,
    }
    errors = [] if name or domain else [{"field": "company", "code": "missing_company_identity", "message": "Provide a company name or company domain."}]
    if email_error:
        errors.append({"field": "email", "code": "invalid_company_email", "message": email_error})
    return NormalizedRow(data=data, errors=errors)


def enrich_from_account(contact: dict, company: object | None) -> tuple[dict, dict]:
    """Fill only missing contact attributes from an imported, domain-matched account.

    This is deliberately a local enrichment adapter: it makes imported account
    attributes usable downstream without representing a third-party lookup.
    """
    enriched = dict(contact)
    if not company:
        return enriched, {"provider": "local_account_profile", "status": "unmatched", "fields_filled": [], "fields_missing": ["company", "industry", "employee_band", "country", "territory"]}
    profile = getattr(company, "profile_data", {}) or {}
    candidates = {
        "company": clean(getattr(company, "name", None)),
        "industry": clean(getattr(company, "industry", None)),
        "employee_band": clean(getattr(company, "employee_band", None)),
        "country": clean(profile.get("Company Country")) or clean(profile.get("Country")),
    }
    fields_filled: list[str] = []
    for field, value in candidates.items():
        if value and not enriched.get(field):
            enriched[field] = value
            fields_filled.append(field)
    if enriched.get("country") and not enriched.get("territory"):
        normalized_country, territory = normalize_country(enriched["country"])
        enriched["country"] = normalized_country
        if territory:
            enriched["territory"] = territory
            fields_filled.append("territory")
    account_enrichment = getattr(company, "enrichment_data", {}) or {}
    derived = account_enrichment.get("derived", {})
    for field in ("growth_status", "funding_signal", "data_freshness", "profile_completeness"):
        if derived.get(field) is not None:
            enriched[f"account_{field}"] = derived[field]
    return enriched, {
        "provider": "local_account_profile",
        "status": "matched",
        "company_id": getattr(company, "id", None),
        "company_domain": getattr(company, "domain", None),
        "fields_filled": fields_filled,
        "fields_missing": [field for field in ("company", "industry", "employee_band", "country", "territory") if not enriched.get(field)],
    }


def parse_number(value: object | None) -> float | None:
    text = clean(value)
    if not text:
        return None
    match = re.search(r"-?\d+(?:[,.]\d+)?", text.replace(",", ""))
    return float(match.group(0)) if match else None


def parse_year(value: object | None) -> int | None:
    number = parse_number(value)
    year = int(number) if number else None
    return year if year and 1800 <= year <= datetime.now(UTC).year else None


def freshness_status(value: object | None) -> str:
    text = clean(value)
    if not text:
        return "unknown"
    for pattern in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y"):
        try:
            parsed = datetime.strptime(text[:19], pattern).replace(tzinfo=UTC)
            age = (datetime.now(UTC).date() - parsed.date()).days
            return "fresh" if age <= 180 else "stale" if age > 365 else "aging"
        except ValueError:
            continue
    return "provided_unparsed"


def derive_account_enrichment(data: dict, profile: dict | None = None) -> dict:
    profile = profile or {}
    growth = parse_number(profile.get("Total headcount growth (12 months)"))
    followers = parse_number(profile.get("LinkedIn Followers"))
    founding_year = parse_year(profile.get("Founding Year"))
    completeness_fields = [data.get("company_domain"), data.get("industry"), data.get("employee_band"), data.get("country"), profile.get("Description"), profile.get("Product and Services"), profile.get("Annual Revenue"), profile.get("Total Funding"), profile.get("LinkedIn")]
    completeness = round(sum(bool(clean(item)) for item in completeness_fields) / len(completeness_fields), 2)
    return {
        "version": "account-enrichment-v2",
        "derived": {
            "growth_status": "positive" if growth is not None and growth > 0 else "negative" if growth is not None and growth < 0 else "flat_or_unknown",
            "growth_percent": growth,
            "company_age_years": datetime.now(UTC).year - founding_year if founding_year else None,
            "funding_signal": "present" if clean(profile.get("Total Funding")) or clean(profile.get("Last Funding Amount")) else "missing",
            "funding_type": clean(profile.get("Last Funding Type")),
            "follower_band": "10000+" if followers and followers >= 10000 else "1000-9999" if followers and followers >= 1000 else "1-999" if followers else "unknown",
            "data_freshness": freshness_status(profile.get("Last Updated")),
            "profile_completeness": completeness,
            "industry_tags": [item.strip() for item in (clean(profile.get("Industry Tags")) or "").split(",") if item.strip()][:10],
            "product_context_available": bool(clean(profile.get("Product and Services")) or clean(profile.get("Description")) or clean(profile.get("SEO Description"))),
        },
        "provenance": {"source": "imported_account_profile", "derived_at": datetime.now(UTC).isoformat()},
    }


def score_account(data: dict, profile: dict | None = None, enrichment: dict | None = None) -> tuple[int, str, list[dict]]:
    """Score imported companies using only supplied account-export attributes."""
    profile = profile or {}
    contributions: list[dict] = []
    def add(name: str, points: int, reason: str):
        contributions.append({"name": name, "points": points, "reason": reason})
    derived = (enrichment or derive_account_enrichment(data, profile)).get("derived", {})
    if data.get("company_domain"): add("company_domain", 10, "Company domain available")
    if (data.get("industry") or "").lower() in {"saas", "software", "fintech", "technology"}: add("industry_fit", 20, "Target industry")
    if data.get("employee_band") in {"11-50", "51-200", "201-500"}: add("company_size", 15, "Target employee band")
    if data.get("territory") in {"NA", "EMEA", "APAC"}: add("territory", 5, "Supported territory")
    if derived.get("growth_status") == "positive": add("headcount_growth", 10, "Positive 12-month headcount growth supplied")
    elif derived.get("growth_status") == "negative": add("headcount_decline", -5, "Negative 12-month headcount growth supplied")
    if clean(profile.get("Total Funding")) or clean(profile.get("Last Funding Amount")):
        add("funding_signal", 5, "Funding data supplied")
    if derived.get("product_context_available"):
        add("company_context", 5, "Company description or product context supplied")
    if derived.get("data_freshness") == "fresh": add("data_freshness", 5, "Account data was updated recently")
    if (derived.get("profile_completeness") or 0) >= 0.7: add("profile_completeness", 5, "Sufficient profile context for prioritization")
    total = max(0, min(100, sum(item["points"] for item in contributions)))
    qualification = "qualified" if total >= 40 else "nurture" if total >= 25 else "unqualified"
    return total, qualification, contributions


def next_account_action(qualification: str, has_owner: bool) -> str:
    if qualification == "qualified" and has_owner:
        return "source_contacts"
    if qualification == "qualified":
        return "manual_routing_review"
    if qualification == "nurture":
        return "monitor_account"
    return "research_required"


def score_lead(data: dict, suppressed: bool = False) -> tuple[int, str, list[dict]]:
    contributions: list[dict] = []
    def add(name: str, points: int, reason: str):
        contributions.append({"name": name, "points": points, "reason": reason})
    if data.get("email"): add("valid_email", 15, "Valid normalized email")
    if data.get("company_domain"): add("company_domain", 10, "Company domain available")
    if data.get("industry", "").lower() in {"saas", "software", "fintech", "technology"}: add("industry_fit", 20, "Target industry")
    if data.get("employee_band") in {"11-50", "51-200", "201-500"}: add("company_size", 15, "Target employee band")
    if data.get("seniority") in {"c_suite", "vp", "director"}: add("seniority", 15, "Decision-maker seniority")
    if data.get("territory") in {"NA", "EMEA", "APAC"}: add("territory", 5, "Supported territory")
    if data.get("source") in {"referral", "reply", "website_form"}: add("high_intent_source", 20, "High-intent source")
    if data.get("engagement") or data.get("intent"): add("intent_signal", 10, "Engagement or intent signal present")
    if data.get("account_growth_status") == "positive": add("account_growth", 5, "Matched account has positive headcount growth")
    if (data.get("account_profile_completeness") or 0) >= 0.7: add("account_profile", 5, "Matched account profile is sufficiently complete")
    if not data.get("email"): add("missing_email", -15, "No valid email")
    if suppressed:
        return 0, "suppressed", contributions + [{"name": "suppression", "points": 0, "reason": "Suppression record matched"}]
    total = max(0, min(100, sum(item["points"] for item in contributions)))
    qualification = "qualified" if total >= 75 else "nurture" if total >= 45 else "unqualified"
    return total, qualification, contributions


def score_company_inbox(account_score: int, account_qualification: str, email: str | None) -> tuple[int, str, list[dict]]:
    """Score a supplied shared company inbox without pretending it is a person.

    The account fit remains the primary signal. A valid imported mailbox makes
    the record eligible for a human-reviewed draft, but does not prove a named
    decision maker or deliverability.
    """
    contributions: list[dict] = [
        {"name": "account_fit", "points": account_score, "reason": "Inherited from the deterministic account score"},
    ]
    if email:
        contributions.append({"name": "supplied_company_email", "points": 15, "reason": "A valid company mailbox was supplied in the import"})
    total = max(0, min(100, sum(item["points"] for item in contributions)))
    qualification = "qualified" if email and account_qualification == "qualified" else "nurture" if total >= 45 else "unqualified"
    return total, qualification, contributions


def next_action(qualification: str, has_owner: bool, has_identity_conflict: bool = False) -> str:
    if qualification == "suppressed": return "do_not_contact"
    if has_identity_conflict: return "duplicate_review"
    if qualification == "qualified" and has_owner: return "ready_for_follow_up"
    if qualification == "qualified": return "manual_routing_review"
    if qualification == "nurture": return "nurture"
    return "research_required"


def can_transition_lead_stage(current_stage: str | None, target_stage: str) -> bool:
    """Return whether a lifecycle transition is a permitted forward move."""
    current = "imported" if current_stage in {None, "", "new"} else current_stage
    return target_stage in LEAD_LIFECYCLE_TRANSITIONS.get(current, set())


def safe_csv(rows: list[dict], headers: list[str]) -> bytes:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: "'" + str(value) if isinstance(value, str) and value[:1] in "=+-@" else value for key, value in row.items()})
    return output.getvalue().encode("utf-8")

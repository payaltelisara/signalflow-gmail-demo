from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from .models import AiSuggestion, Campaign, CampaignAudienceMember, CampaignEnrollment, CampaignStep, Lead, OutreachDraft, ScheduledMessage, Suppression


def campaign_data(db: Session, campaign: Campaign) -> dict:
    steps = db.query(CampaignStep).filter(CampaignStep.campaign_id == campaign.id).order_by(CampaignStep.position).all()
    enrollments = db.query(CampaignEnrollment).filter(CampaignEnrollment.campaign_id == campaign.id).all()
    status_counts: dict[str, int] = {}
    for enrollment in enrollments:
        status_counts[enrollment.status] = status_counts.get(enrollment.status, 0) + 1
    return {"id": campaign.id, "name": campaign.name, "status": campaign.status, "mailbox_id": campaign.mailbox_id, "audience_filter": campaign.audience_filter or {}, "timezone": campaign.timezone, "business_hours": campaign.business_hours or {}, "daily_limit": campaign.daily_limit, "per_domain_limit": campaign.per_domain_limit, "test_sent_at": campaign.test_sent_at, "approved_at": campaign.approved_at, "activated_at": campaign.activated_at, "created_at": campaign.created_at, "updated_at": campaign.updated_at, "steps": [{"id": step.id, "position": step.position, "delay_hours": step.delay_hours, "subject": step.subject, "body": step.body, "facts_used": step.facts_used or []} for step in steps], "enrollment_counts": status_counts, "enrollment_total": len(enrollments)}


def audience_leads(db: Session, campaign: Campaign) -> list[Lead]:
    filters = campaign.audience_filter or {}
    member_ids = [item.lead_id for item in db.query(CampaignAudienceMember).filter(CampaignAudienceMember.campaign_id == campaign.id, CampaignAudienceMember.selected.is_(True), CampaignAudienceMember.lead_id.is_not(None)).all()]
    query = db.query(Lead).filter(Lead.workspace_id == campaign.workspace_id, Lead.email.is_not(None), Lead.qualification == "qualified")
    # New campaign-first workspaces only ever send to explicitly selected
    # audience members. Legacy campaigns keep their filter-based behaviour.
    if filters.get("campaign_first"):
        if not member_ids:
            return []
        query = query.filter(Lead.id.in_(member_ids))
    elif member_ids:
        query = query.filter(Lead.id.in_(member_ids))
    if filters.get("source"):
        query = query.filter(Lead.source == filters["source"])
    if filters.get("territory"):
        query = query.filter(Lead.territory == filters["territory"])
    ids = filters.get("lead_ids") or []
    if ids:
        query = query.filter(Lead.id.in_(ids))
    suppressed = {row.normalized_email for row in db.query(Suppression).filter(Suppression.workspace_id == campaign.workspace_id).all()}
    eligible: list[Lead] = []
    for lead in query.order_by(Lead.score.desc()).all():
        if lead.normalized_email in suppressed:
            continue
        completed_analysis = db.query(AiSuggestion).filter(AiSuggestion.lead_id == lead.id, AiSuggestion.status == "completed").first()
        if completed_analysis:
            eligible.append(lead)
    return eligible


def next_business_time(value: datetime, timezone_name: str, business_hours: dict) -> datetime:
    try:
        zone = ZoneInfo(timezone_name)
    except Exception:
        zone = UTC
    local = value.astimezone(zone)
    start = int(business_hours.get("start", 9)); end = int(business_hours.get("end", 17)); weekdays = set(business_hours.get("weekdays", [0, 1, 2, 3, 4]))
    while local.weekday() not in weekdays or local.hour >= end:
        local = (local + timedelta(days=1)).replace(hour=start, minute=0, second=0, microsecond=0)
    if local.hour < start:
        local = local.replace(hour=start, minute=0, second=0, microsecond=0)
    return local.astimezone(UTC)


def schedule_enrollment(db: Session, campaign: Campaign, enrollment: CampaignEnrollment, position: int, base_time: datetime | None = None) -> ScheduledMessage | None:
    step = db.query(CampaignStep).filter(CampaignStep.campaign_id == campaign.id, CampaignStep.position == position).first()
    if not step:
        return None
    send_at = next_business_time((base_time or datetime.now(UTC)) + timedelta(hours=step.delay_hours), campaign.timezone, campaign.business_hours or {})
    key = f"{campaign.id}:{enrollment.id}:{position}"
    existing = db.query(ScheduledMessage).filter(ScheduledMessage.idempotency_key == key).first()
    if existing:
        return existing
    record = ScheduledMessage(workspace_id=campaign.workspace_id, campaign_id=campaign.id, enrollment_id=enrollment.id, step_position=position, send_at=send_at, idempotency_key=key)
    db.add(record)
    enrollment.status = "scheduled"; enrollment.next_step = position; enrollment.next_send_at = send_at
    return record


def classify_reply(subject: str, body: str) -> str:
    text = f"{subject} {body}".lower()
    if any(term in text for term in ("delivery status notification", "undeliverable", "address not found", "mailbox unavailable", "message blocked")):
        return "hard_bounce"
    if any(term in text for term in ("unsubscribe", "remove me", "stop emailing", "opt out")):
        return "unsubscribe"
    if any(term in text for term in ("out of office", "automatic reply", "away until")):
        return "out_of_office"
    if any(term in text for term in ("wrong person", "not the right person", "contact instead")):
        return "wrong_person"
    if any(term in text for term in ("not interested", "no thanks", "not a fit")):
        return "objection"
    if any(term in text for term in ("not now", "later", "next quarter", "circle back")):
        return "not_now"
    if any(term in text for term in ("yes", "interested", "let's talk", "book", "calendar", "meeting")):
        return "interested"
    if any(term in text for term in ("referral", "speak with", "contact my")):
        return "referral"
    return "unknown"

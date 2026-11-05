import pytest
from pydantic import ValidationError

from app.ai_contracts import AccountAiOutput, LeadAiOutput


def valid_output() -> dict:
    return {
        "classification": "qualified",
        "summary": "A qualified revenue-operations contact at a software company.",
        "rationale": "The deterministic score and supplied account context support a reviewable outreach draft.",
        "suggested_next_action": "Review the generated sequence before manual use.",
        "company_summary": "A software company with supplied firmographic and growth context.",
        "signals": ["Positive headcount growth supplied"],
        "personalization_angles": ["Revenue-operations ownership"],
        "warnings": ["Review claims against the imported profile."],
        "confidence": 0.72,
        "cold_email_sequence": [
            {"step": 1, "timing": "Initial", "subject": "A question for your team", "body": "Hi Maya, I am reaching out with a brief question about how your team handles lead follow-up. Would a short conversation next week be useful?", "cta": "Would 15 minutes next week be useful?", "facts_used": ["VP Revenue Operations"]},
            {"step": 2, "timing": "Three business days later", "subject": "Following up", "body": "Hi Maya, I wanted to follow up on my question about lead follow-up processes. Is a short conversation useful this week?", "cta": "Is there a suitable time this week?", "facts_used": ["VP Revenue Operations"]},
            {"step": 3, "timing": "Seven business days later", "subject": "Closing the loop", "body": "Hi Maya, I will close the loop after this note. If lead follow-up is a current priority, I would be glad to compare notes.", "cta": "Would a brief call be useful?", "facts_used": ["VP Revenue Operations"]},
        ],
    }


def test_ai_contract_requires_a_three_step_sequence():
    output = LeadAiOutput.model_validate(valid_output())
    assert [item.step for item in output.ordered_sequence()] == [1, 2, 3]


def test_ai_contract_rejects_missing_sequence_step():
    data = valid_output()
    data["cold_email_sequence"] = data["cold_email_sequence"][:2]
    with pytest.raises(ValidationError):
        LeadAiOutput.model_validate(data)


def test_account_contract_normalizes_human_percentage_confidence():
    output = AccountAiOutput.model_validate({
        "company_summary": "A company with imported profile context available.",
        "icp_assessment": "The deterministic account score supports research review.",
        "why_now": ["Positive headcount growth was supplied."],
        "personalization_angles": ["Use the imported product description."],
        "recommended_roles": ["Revenue operations leader"],
        "data_gaps": ["No verified contact or email was supplied."],
        "suggested_next_action": "Source a relevant contact before outreach.",
        "confidence": 55,
    })
    assert output.confidence == 0.55

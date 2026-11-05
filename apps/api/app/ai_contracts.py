from typing import Literal

from pydantic import BaseModel, Field, field_validator


def normalize_confidence(value: object) -> float:
    """Accept either a probability (0.55) or a human percentage (55)."""
    numeric = float(value)
    if 1 < numeric <= 100:
        numeric /= 100
    return numeric


class ColdEmailStep(BaseModel):
    step: Literal[1, 2, 3]
    timing: str = Field(min_length=3, max_length=80)
    subject: str = Field(min_length=3, max_length=90)
    body: str = Field(min_length=20, max_length=1000)
    cta: str = Field(min_length=3, max_length=180)
    facts_used: list[str] = Field(default_factory=list, max_length=8)


class LeadAiOutput(BaseModel):
    classification: Literal["qualified", "nurture", "research_required"]
    summary: str = Field(min_length=10, max_length=700)
    rationale: str = Field(min_length=10, max_length=900)
    suggested_next_action: str = Field(min_length=3, max_length=120)
    company_summary: str = Field(min_length=10, max_length=700)
    signals: list[str] = Field(default_factory=list, max_length=10)
    personalization_angles: list[str] = Field(default_factory=list, max_length=6)
    warnings: list[str] = Field(default_factory=list, max_length=8)
    confidence: float = Field(ge=0, le=1)
    cold_email_sequence: list[ColdEmailStep] = Field(min_length=3, max_length=3)

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence_value(cls, value: object) -> float:
        return normalize_confidence(value)

    def ordered_sequence(self) -> list[ColdEmailStep]:
        sequence = sorted(self.cold_email_sequence, key=lambda item: item.step)
        if [item.step for item in sequence] != [1, 2, 3]:
            raise ValueError("cold_email_sequence must contain steps 1, 2, and 3 exactly once")
        return sequence


class AccountAiOutput(BaseModel):
    """Structured account research for exports that do not include contacts."""

    company_summary: str = Field(min_length=10, max_length=700)
    icp_assessment: str = Field(min_length=10, max_length=700)
    why_now: list[str] = Field(default_factory=list, max_length=6)
    personalization_angles: list[str] = Field(default_factory=list, max_length=6)
    recommended_roles: list[str] = Field(default_factory=list, max_length=6)
    data_gaps: list[str] = Field(default_factory=list, max_length=8)
    suggested_next_action: str = Field(min_length=3, max_length=160)
    confidence: float = Field(ge=0, le=1)

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence_value(cls, value: object) -> float:
        return normalize_confidence(value)

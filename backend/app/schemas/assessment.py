"""Assessment of one land case: risk level, Bangla texts, coverage, review list and actions."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.land_case import SourceRef
from app.services.rules.base import RuleResult


class SkippedCheck(BaseModel):
    rule_id: str
    reason_bn: str


class Coverage(BaseModel):
    """What could be checked. Never changes the risk level."""

    complete: bool
    checks_run: int
    checks_skipped: list[SkippedCheck] = Field(default_factory=list)
    documents_missing: list[str] = Field(default_factory=list)  # CaseRole values
    documents_missing_bn: list[str] = Field(default_factory=list)


class ReviewItem(BaseModel):
    """An extraction field flagged low/medium confidence that a rule used."""

    source_id: str
    document_label_bn: str
    field_path: str
    label_bn: str
    printed_text: str | None
    flags: list[str]


class Action(BaseModel):
    id: str
    text_bn: str
    priority: int  # 1 high ... 3 low
    who: str  # buyer | seller | amin | lawyer | land_office
    from_codes: list[str] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)


class Assessment(BaseModel):
    engine_version: str
    risk_level: str  # high | medium | low (findings.md)
    headline_bn: str
    summary_bn: str
    coverage: Coverage
    review_needed: list[ReviewItem] = Field(default_factory=list)
    findings: list[RuleResult] = Field(default_factory=list)
    passed: list[RuleResult] = Field(default_factory=list)
    actions: list[Action] = Field(default_factory=list)
    disclaimer_bn: str


class AssessmentOut(Assessment):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    land_id: uuid.UUID
    created_at: datetime

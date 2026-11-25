"""The buyer's journey for one plot (services/journey.py): 8 steps in 3 phases, gated in order."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

StepStatus = Literal["done", "action", "waiting", "locked", "todo"]


class JourneyStep(BaseModel):
    n: int  # 1..8
    key: str  # location | documents | paper | ground | report | seller | escrow | guardian
    phase: Literal["before", "during", "after"]
    status: StepStatus
    note_bn: str = ""  # what is missing or what to do; empty when done


class Journey(BaseModel):
    steps: list[JourneyStep]
    progress_done: int  # done steps among the 5 "before buying" steps
    progress_total: int = 5
    # paper check could not cover everything: unread/pending documents, stale assessment,
    # skipped checks, missing documents. Non-empty -> never show a no-mismatch headline.
    incomplete_reasons_bn: list[str] = Field(default_factory=list)
    next_action_bn: str | None = None
    escrow_deal_id: str | None = None


class CaseSummary(BaseModel):
    """One dashboard card: same journey logic as the case page."""

    risk_level: str | None = None  # high | medium | low; None before the first assessment
    complete: bool  # False when incomplete_reasons_bn is non-empty
    progress_done: int
    progress_total: int = 5
    updated_at: datetime
    next_action_bn: str | None = None
    # False for leftover test cases (no district/dag, no Bangla mouza, "??" names): the
    # dashboard hides them; nothing is deleted
    listed: bool = True

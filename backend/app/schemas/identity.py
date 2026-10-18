import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class IdentityVerificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    land_id: uuid.UUID | None
    party: Literal["buyer", "seller"]
    seller_name_on_deed: str | None = None
    status: Literal["pending", "verified", "failed"]
    name_bn_as_per_nid: str | None = None
    father_name_as_per_nid: str | None = None
    provider: str
    provider_ref: str
    verified_at: datetime | None
    created_at: datetime


class SellerLinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seller_name_on_deed: str = Field(min_length=1, max_length=200)


class SellerLinkCreated(BaseModel):
    url: str
    expires_at: datetime


class ConsentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consent: Literal[True]


class VerificationCompleteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    father_name: str = Field(min_length=1, max_length=200)
    outcome: Literal["verified", "failed", "pending"]


class BuyerVerificationIn(VerificationCompleteIn):
    consent: Literal[True]

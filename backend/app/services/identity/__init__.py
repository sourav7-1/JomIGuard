"""Result-only identity provider interface and local mock."""

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, Protocol

from app.core.config import settings

Outcome = Literal["verified", "failed", "pending"]


@dataclass(frozen=True)
class IdentityResult:
    status: Outcome
    name_bn_as_per_nid: str | None
    father_name_as_per_nid: str | None
    provider: str
    provider_ref: str
    verified_at: datetime | None


class IdentityProvider(Protocol):
    name: str

    def verify(self, name: str, father_name: str, outcome: Outcome) -> IdentityResult: ...


class MockProvider:
    name = "mock"

    def verify(self, name: str, father_name: str, outcome: Outcome) -> IdentityResult:
        return IdentityResult(
            status=outcome,
            name_bn_as_per_nid=name if outcome == "verified" else None,
            father_name_as_per_nid=father_name if outcome == "verified" else None,
            provider=self.name,
            provider_ref=secrets.token_urlsafe(18),
            verified_at=datetime.now(UTC) if outcome == "verified" else None,
        )


def get_provider() -> IdentityProvider:
    if settings.identity_provider != "mock":
        raise RuntimeError("Unsupported IDENTITY_PROVIDER")
    return MockProvider()

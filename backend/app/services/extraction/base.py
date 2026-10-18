"""Extractor protocol: document image -> schema-valid extracted data (or an error)."""

from dataclasses import dataclass, field
from typing import Protocol

from app.schemas.extracted import (
    DeedData,
    ExtractedDocument,
    HeirCertData,
    KhatianData,
    MutationData,
)

MODELS = {"khatian": KhatianData, "deed": DeedData, "dcr": MutationData, "heir_cert": HeirCertData}


@dataclass
class ExtractionMeta:
    model: str | None = None
    latency_s: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    cached: bool = False
    prompt_version: str | None = None


@dataclass
class ExtractionResult:
    document: ExtractedDocument | None = None
    error: str | None = None  # set when no valid document came back; never both
    meta: ExtractionMeta = field(default_factory=ExtractionMeta)
    handwritten: bool = False


class Extractor(Protocol):
    def extract(self, image_bytes: bytes, doc_type: str) -> ExtractionResult: ...

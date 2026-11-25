"""Read ONLY the name fields from an NID photo, in memory, for name matching.

Owner decision 2026-11-26 (CLAUDE.md, docs/specs/identity.md): from an NID image JomiGuard may
read the name in Bangla and English and the father's/husband's name. Nothing else: no NID
number, date of birth, address, blood group, signature, photo or mother's name.

- The image bytes stay in memory: never written to MinIO, disk or the extraction cache.
- Chain: a paid Anthropic model (only when its key is set), then local Tesseract. Never Gemini:
  its free tier may use inputs for training and a real NID is never sent there.
- NidNames keeps only the three allowed fields; anything else the model returns is dropped
  while parsing, so it can never reach the database, the API or the log.
"""

import base64
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal

import anthropic
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.services.extraction.budget import BudgetExceeded, cost_usd
from app.services.extraction.llm import (
    API_IMAGE_PIXELS,
    TOKENS_PER_PIXEL,
    AnthropicExtractor,
    ProviderError,
    prepare_image,
)
from app.services.ocr import ocr
from app.services.preprocess import PreprocessError, preprocess

log = logging.getLogger(__name__)

ALLOWED = ("name_bn", "name_en", "father_or_husband_name")
TOOL_NAME = "record_nid_names"
MAX_IMAGE_BYTES = 5 * 1024 * 1024

SYSTEM = """\
You read a photo of a Bangladeshi national ID card ONLY to copy the person's names, by calling
the record_nid_names tool exactly once.

Return only:
- name_bn: the name after "নাম" in Bangla, exactly as printed (keep honorifics like মোঃ).
- name_en: the name after "Name" in English, exactly as printed.
- father_or_husband_name: the name after "পিতা" (father) or "স্বামী" (husband), as printed.
Return null for a field that is not printed or not readable. Never guess.

Never return, in any field, the NID number, date of birth, address, blood group, mother's
name, signature, photo description or any other text from the card. There are no fields for
them. Ignore the "নমুনা / SAMPLE" watermark.
"""


class NidNames(BaseModel):
    """The only data ever kept from an NID photo. Extra keys are dropped, never stored."""

    model_config = ConfigDict(extra="ignore")

    name_bn: str | None = Field(default=None, max_length=200)
    name_en: str | None = Field(default=None, max_length=200)
    father_or_husband_name: str | None = Field(default=None, max_length=200)

    def any_name(self) -> bool:
        return bool(self.name_bn or self.name_en)


@dataclass
class NidRead:
    names: NidNames = field(default_factory=NidNames)
    source: str | None = None  # "ai" | "ocr"; None when nothing could read it


def parse_names(raw: dict | None) -> NidNames:
    """Model answer -> the three allowed fields, cleaned; everything else is dropped."""
    if not isinstance(raw, dict):
        return NidNames()
    kept = {k: raw.get(k) for k in ALLOWED}
    kept = {k: v.strip() or None if isinstance(v, str) else None for k, v in kept.items()}
    try:
        return NidNames.model_validate(kept)
    except ValidationError:
        return NidNames()


# --- AI step (Anthropic, paid; no cache) ---


class AnthropicNidReader(AnthropicExtractor):
    """Reuses the Anthropic client, model, prices and daily budget; never the disk cache."""

    def read(self, image_bytes: bytes) -> NidNames:
        data, media_type, size = prepare_image(image_bytes, "gray")
        tokens_in = int(min(size[0] * size[1], API_IMAGE_PIXELS) * TOKENS_PER_PIXEL)
        tokens_in += len(SYSTEM) // 2
        self.budget.check(cost_usd(tokens_in, 300, self.price_in, self.price_out))
        schema = {
            "type": "object",
            "properties": {k: {"type": ["string", "null"]} for k in ALLOWED},
            "required": list(ALLOWED),
        }
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                system=SYSTEM,
                tools=[{"name": TOOL_NAME, "description": "Record the names on one NID card.",
                        "input_schema": schema}],
                tool_choice={"type": "tool", "name": TOOL_NAME},
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type,
                                                 "data": base64.b64encode(data).decode()}},
                    {"type": "text", "text": f"Record the names with the {TOOL_NAME} tool."},
                ]}],
            )  # fmt: skip
        except anthropic.APIError as e:
            raise ProviderError(type(e).__name__) from e
        usage = response.usage
        self.budget.add(
            cost_usd(usage.input_tokens, usage.output_tokens, self.price_in, self.price_out)
        )
        if response.stop_reason == "max_tokens":
            return NidNames()
        calls = [b for b in response.content if getattr(b, "type", None) == "tool_use"]
        raw = next((b.input for b in calls if b.name == TOOL_NAME), None)
        return parse_names(dict(raw) if raw is not None else None)


# --- OCR step (local Tesseract): only the name lines, the rest of the text is discarded ---

# OCR often puts noise before a label ("। ঢা । পিতা: ..."): a label after a space or line start,
# always followed by ":" so words like "নামজারি" never count
_LINE = {
    "name_bn": re.compile(r"(?:^|\s)নাম\s*[:ঃ]\s*(.+)$"),
    "name_en": re.compile(r"(?:^|\s)Name\s*[:;]\s*([A-Za-z][A-Za-z0-9.\s]*?)\s*$"),
    "father_or_husband_name": re.compile(r"(?:^|\s)(?:পিতা|স্বামী)\s*[:ঃ]\s*(.+)$"),
}


def names_from_text(text: str) -> NidNames:
    found: dict[str, str] = {}
    for line in text.splitlines():
        for key, pattern in _LINE.items():
            if key not in found and (m := pattern.search(line)):
                found[key] = m.group(1).strip()
    return parse_names(found)


def ocr_read(image_bytes: bytes) -> NidNames:
    try:
        gray = preprocess(image_bytes).gray
    except PreprocessError:
        return NidNames()
    return names_from_text(ocr(gray, psm=6).text)


# --- chain ---


def nid_steps() -> list[tuple[str, Callable[[bytes], NidNames]]]:
    """AI (Anthropic, when configured) then OCR. Gemini is never a step (CLAUDE.md)."""
    return [("ai", lambda img: AnthropicNidReader().read(img)), ("ocr", ocr_read)]


def read_nid(image_bytes: bytes, steps=None) -> NidRead:
    for source, step in steps if steps is not None else nid_steps():
        try:
            names = step(image_bytes)
        except (ValueError, BudgetExceeded, ProviderError) as e:  # not configured / failed
            log.warning("nid reader %s skipped: %s", source, type(e).__name__)
            continue
        except Exception as e:  # noqa: BLE001  a broken step must not stop the chain
            log.warning("nid reader %s crashed: %s", source, type(e).__name__)  # no content
            continue
        if names.any_name():
            return NidRead(names=names, source=source)
    return NidRead()


def confidence(score: float, source: str | None) -> float:
    """Name-match score, lowered for an OCR read (limited)."""
    return float(round(Decimal(str(score)) * (Decimal("0.6") if source == "ocr" else 1), 2))

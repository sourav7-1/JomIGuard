"""Extraction that does not give up on the first provider error.

Steps, tried in order until one returns a document:
  1. the LLM_PROVIDER extractor (it already retried 429/5xx/timeouts with backoff),
  2. GEMINI_FALLBACK_MODEL, when set and a Gemini key exists,
  3. the other provider (Anthropic <-> Gemini), when its key is set,
  4. Tesseract + regex (local, free): a limited read, marked "tesseract_regex".
A step that cannot be built (missing key/model) or raises is skipped and logged; only the log
holds technical errors. ExtractionResult.extractor names the step that produced the result.

Note (CLAUDE.md): Gemini's free tier may use inputs for training, so with LLM_PROVIDER=anthropic
and a GEMINI_API_KEY set, real documents could reach Gemini through step 3. Leave
GEMINI_API_KEY unset on a deployment that reads real documents.
"""

import logging
from collections.abc import Callable

from app.core.config import settings
from app.services.extraction.base import ExtractionResult, Extractor
from app.services.extraction.budget import BudgetExceeded

log = logging.getLogger(__name__)

TESSERACT = "tesseract_regex"


class FallbackExtractor:
    name = "llm"

    def __init__(self, steps: list[tuple[str, Callable[[], Extractor]]]):
        self.steps = steps  # (name, factory); built lazily, so a missing key only skips a step
        self._built: dict[str, Extractor] = {}

    def _get(self, name: str, factory: Callable[[], Extractor]) -> Extractor:
        if name not in self._built:
            self._built[name] = factory()
        return self._built[name]

    def extract(self, image_bytes: bytes, doc_type: str) -> ExtractionResult:
        last = ExtractionResult(error="no extractor could run")
        for name, factory in self.steps:
            try:
                result = self._get(name, factory).extract(image_bytes, doc_type)
            except (ValueError, BudgetExceeded) as e:  # not configured, or over today's budget
                log.warning("extractor %s skipped: %s", name, e)
                continue
            except Exception:  # noqa: BLE001  a broken step must not stop the chain
                log.exception("extractor %s crashed", name)
                continue
            result.extractor = name
            if result.document is not None:
                return result
            log.warning("extractor %s failed for %s: %s", name, doc_type, result.error)
            last = result
        return last


def make_fallback_extractor() -> FallbackExtractor:
    """The chain for EXTRACTOR=llm, from the settings (see the module docstring)."""
    from app.services.extraction.gemini import GeminiExtractor
    from app.services.extraction.llm import AnthropicExtractor, make_llm_extractor
    from app.services.extraction.tesseract_regex import TesseractRegexExtractor

    primary = settings.llm_provider
    steps: list[tuple[str, Callable[[], Extractor]]] = [(primary, make_llm_extractor)]
    fallback_model = settings.gemini_fallback_model.strip()
    if fallback_model and settings.gemini_api_key is not None:
        if not (primary == "gemini" and fallback_model == settings.gemini_model):
            steps.append(
                (f"gemini:{fallback_model}", lambda: GeminiExtractor(model=fallback_model))
            )
    if primary == "gemini" and settings.anthropic_api_key is not None:
        steps.append(("anthropic", AnthropicExtractor))
    if primary == "anthropic" and settings.gemini_api_key is not None:
        steps.append(("gemini", GeminiExtractor))
    steps.append((TESSERACT, TesseractRegexExtractor))
    return FallbackExtractor(steps)

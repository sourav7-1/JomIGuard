"""Vision-LLM extractor (Anthropic): document image -> schema-valid extracted data.

Structured output through a forced tool call whose input_schema is the extractor-only schema
(the Pydantic model without the fields normalize.py fills). The answer is validated with the real
model; a bad answer becomes ExtractionResult.error, never an exception. BudgetExceeded is raised
before a call that would go over the daily limit. Results are cached on disk by
sha256(image + model + PROMPT_VERSION + doc_type + image mode); a hit costs 0.
"""

import base64
import copy
import hashlib
import json
from decimal import Decimal
from functools import cache
from pathlib import Path
from time import perf_counter

import anthropic
import cv2
from pydantic import ValidationError

from app.core.config import settings
from app.services.extraction.base import MODELS, ExtractionMeta, ExtractionResult
from app.services.extraction.budget import Budget, cost_usd
from app.services.extraction.prompts import DOC_NOTES, PROMPT_VERSION, SYSTEM, TOOL_NAME, user_text
from app.services.preprocess import PreprocessError, decode, limit_size, preprocess

IMAGE_MODES = ("gray", "original")
API_IMAGE_PIXELS = 1_150_000  # the API scales larger images down to about this many pixels
TOKENS_PER_PIXEL = Decimal(1) / 750


def is_normalize_field(name: str) -> bool:
    """Fields filled by normalize.py (fields.md, filled_by = normalize)."""
    return name == "name_normalized" or name.endswith(("_shatangsho", "_fraction"))


@cache
def _extractor_schema(doc_type: str) -> dict:
    schema = MODELS[doc_type].model_json_schema()

    def strip(node):
        if isinstance(node, dict):
            props = node.get("properties")
            if isinstance(props, dict):
                for name in [n for n in props if is_normalize_field(n)]:
                    del props[name]
                if "required" in node:
                    node["required"] = [r for r in node["required"] if not is_normalize_field(r)]
            for v in node.values():
                strip(v)
        elif isinstance(node, list):
            for v in node:
                strip(v)

    strip(schema)
    return schema


def extractor_schema(doc_type: str) -> dict:
    """JSON schema of what the extractor may return for doc_type (no normalize fields)."""
    return copy.deepcopy(_extractor_schema(doc_type))


def prepare_image(image_bytes: bytes, mode: str) -> tuple[bytes, str, tuple[int, int]]:
    """-> (encoded image, media type, (width, height)); long side <= 2000 px."""
    if mode == "gray":
        img = preprocess(image_bytes).gray  # already limited to 2000 px
        ext, media = ".png", "image/png"  # lossless for text
    elif mode == "original":
        img = limit_size(decode(image_bytes)[0])
        ext, media = ".jpg", "image/jpeg"  # color photos as PNG can pass the API size limit
    else:
        raise ValueError(f"image mode must be one of {IMAGE_MODES}")
    params = [cv2.IMWRITE_JPEG_QUALITY, 92] if ext == ".jpg" else []
    ok, buf = cv2.imencode(ext, img, params)
    if not ok:
        raise PreprocessError("could not encode the image")
    return buf.tobytes(), media, (img.shape[1], img.shape[0])


class ProviderError(RuntimeError):
    """The provider call failed (network, auth, rate limit after retries): not cached."""


class LLMExtractor:
    """Shared by every vision-LLM provider: extractor-only schema, image preparation, cache,
    budget guard and validation. A provider implements _default_model, _make_client and _call."""

    provider = "llm"
    model_setting = "LLM_MODEL"

    def __init__(
        self,
        *,
        client=None,
        model: str | None = None,
        image: str = "gray",
        price_input_per_mtok: Decimal | None = None,
        price_output_per_mtok: Decimal | None = None,
        max_tokens: int | None = None,
        cache_dir: Path | None = None,
        budget: Budget | None = None,
    ) -> None:
        self.model = model or self._default_model()
        self.price_in = _first(price_input_per_mtok, settings.llm_price_input_per_mtok)
        self.price_out = _first(price_output_per_mtok, settings.llm_price_output_per_mtok)
        missing = [
            name
            for name, value in (
                (self.model_setting, self.model),
                ("LLM_PRICE_INPUT_PER_MTOK", self.price_in),
                ("LLM_PRICE_OUTPUT_PER_MTOK", self.price_out),
                ("LLM_DAILY_BUDGET_USD", budget or settings.llm_daily_budget_usd),
            )
            if value is None
        ]
        if missing:
            raise ValueError(f"LLM settings missing: {', '.join(missing)}")
        if image not in IMAGE_MODES:
            raise ValueError(f"image mode must be one of {IMAGE_MODES}")
        self.image = image
        self.max_tokens = max_tokens or settings.llm_max_tokens
        self.cache_dir = Path(cache_dir or settings.llm_cache_dir)
        self.budget = budget or Budget(
            Path(settings.llm_budget_file), settings.llm_daily_budget_usd
        )
        self._client = client

    # --- provider hooks ---

    def _default_model(self) -> str | None:
        raise NotImplementedError

    def _make_client(self):
        raise NotImplementedError

    def _call(self, data: bytes, media_type: str, doc_type: str):
        """-> (tool_input | None, error | None, input_tokens, output_tokens).
        Raises ProviderError when the call itself failed."""
        raise NotImplementedError

    @property
    def client(self):
        if self._client is None:  # created lazily: cache hits need no API key
            self._client = self._make_client()
        return self._client

    # --- cache ---

    def cache_key(self, image_bytes: bytes, doc_type: str) -> str:
        h = hashlib.sha256(image_bytes)
        for part in (self.provider, self.model, PROMPT_VERSION, doc_type, self.image):
            h.update(b"\0" + part.encode())
        return h.hexdigest()

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def _cache_get(self, key: str) -> dict | None:
        path = self._cache_path(key)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def _cache_put(self, key: str, value: dict) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_path(key).write_text(
            json.dumps(value, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n"
        )

    # --- call ---

    def estimate_usd(self, size: tuple[int, int], doc_type: str) -> Decimal:
        """Upper bound for the budget check: image + prompt tokens in, max_tokens out."""
        image_tokens = min(size[0] * size[1], API_IMAGE_PIXELS) * TOKENS_PER_PIXEL
        text = SYSTEM + DOC_NOTES[doc_type] + json.dumps(extractor_schema(doc_type))
        input_tokens = int(image_tokens) + len(text) // 2  # Bangla text: ~2 chars per token
        return cost_usd(input_tokens, self.max_tokens, self.price_in, self.price_out)

    def extract(self, image_bytes: bytes, doc_type: str) -> ExtractionResult:
        start = perf_counter()
        meta = ExtractionMeta(model=self.model, prompt_version=PROMPT_VERSION)

        def done(tool_input: dict | None, error: str | None) -> ExtractionResult:
            meta.latency_s = round(perf_counter() - start, 3)
            return _result(doc_type, tool_input, error, meta)

        if doc_type not in MODELS:
            return done(None, f"unknown doc_type {doc_type!r}")
        key = self.cache_key(image_bytes, doc_type)
        if (hit := self._cache_get(key)) is not None:
            meta.cached = True
            meta.input_tokens = hit["meta"]["input_tokens"]
            meta.output_tokens = hit["meta"]["output_tokens"]
            return done(hit["tool_input"], hit["error"])

        try:
            data, media_type, size = prepare_image(image_bytes, self.image)
        except PreprocessError as e:
            return done(None, f"image: {e}")
        self.budget.check(self.estimate_usd(size, doc_type))  # raises BudgetExceeded

        try:
            tool_input, error, tokens_in, tokens_out = self._call(data, media_type, doc_type)
        except ProviderError as e:  # not cached: a later run may succeed
            return done(None, f"api: {e}")

        meta.input_tokens, meta.output_tokens = tokens_in, tokens_out
        cost = cost_usd(tokens_in, tokens_out, self.price_in, self.price_out)
        self.budget.add(cost)
        meta.cost_usd = float(cost)
        self._cache_put(
            key,
            {
                "tool_input": tool_input,
                "error": error,
                "meta": {
                    "provider": self.provider,
                    "model": self.model,
                    "prompt_version": PROMPT_VERSION,
                    "input_tokens": tokens_in,
                    "output_tokens": tokens_out,
                    "cost_usd": meta.cost_usd,
                },
            },
        )
        return done(tool_input, error)


class AnthropicExtractor(LLMExtractor):
    """Structured output through a forced tool call (input_schema = extractor-only schema)."""

    provider = "anthropic"

    def _default_model(self) -> str | None:
        return settings.llm_model

    def _make_client(self):
        key = settings.anthropic_api_key
        if key is None:
            raise ValueError("ANTHROPIC_API_KEY is not set")
        return anthropic.Anthropic(api_key=key.get_secret_value())

    def _call(self, data: bytes, media_type: str, doc_type: str):
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=SYSTEM,
                tools=[
                    {
                        "name": TOOL_NAME,
                        "description": f"Record the printed fields of one {doc_type} document.",
                        "input_schema": extractor_schema(doc_type),
                    }
                ],
                tool_choice={"type": "tool", "name": TOOL_NAME},
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": base64.b64encode(data).decode(),
                                },
                            },
                            {"type": "text", "text": user_text(doc_type)},
                        ],
                    }
                ],
            )
        except anthropic.APIError as e:
            raise ProviderError(type(e).__name__) from e
        tool_input, error = _tool_input(response)
        return tool_input, error, response.usage.input_tokens, response.usage.output_tokens


def make_llm_extractor(**kwargs) -> LLMExtractor:
    """The vision-LLM extractor for LLM_PROVIDER (anthropic | gemini)."""
    if settings.llm_provider == "gemini":
        from app.services.extraction.gemini import GeminiExtractor

        return GeminiExtractor(**kwargs)
    if settings.llm_provider == "anthropic":
        return AnthropicExtractor(**kwargs)
    raise ValueError(f"LLM_PROVIDER must be anthropic or gemini, not {settings.llm_provider!r}")


def _first(value, default):
    return default if value is None else value


def _tool_input(response) -> tuple[dict | None, str | None]:
    if response.stop_reason == "max_tokens":
        return None, "output truncated at max_tokens"
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == TOOL_NAME:
            return dict(block.input), None
    return None, "no tool call in the answer"


def _result(doc_type, tool_input, error, meta) -> ExtractionResult:
    if error is not None or tool_input is None:
        return ExtractionResult(error=error or "empty answer", meta=meta)
    try:
        document = MODELS[doc_type].model_validate({**tool_input, "doc_type": doc_type})
    except ValidationError as e:
        where = ", ".join(".".join(map(str, err["loc"])) for err in e.errors()[:5])
        return ExtractionResult(
            error=f"invalid output: {e.error_count()} errors ({where})", meta=meta
        )
    return ExtractionResult(document=document, meta=meta)

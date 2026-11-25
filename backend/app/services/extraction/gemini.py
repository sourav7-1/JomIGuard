"""Gemini vision extractor (Google Gen AI SDK), selected with LLM_PROVIDER=gemini.

Same behaviour as AnthropicExtractor (LLMExtractor: cache with the provider in the key, budget
guard, validation, error results instead of exceptions). Structured output through
response_schema, built from the same extractor-only schema; Gemini's schema subset has no $ref,
anyOf or const, so to_gemini_schema inlines and simplifies it. On HTTP 429/500/503/504 or a
timeout the call backs off (4 s, 8 s; a longer Retry-After wins) and retries; after that
FallbackExtractor (fallback.py) tries the next extractor.

Gemini's free tier may use inputs to improve Google's models: synthetic documents only
(CLAUDE.md).
"""

import json
import time
from functools import cache

import httpx
from google import genai
from google.genai import errors, types

from app.core.config import settings
from app.services.extraction.llm import LLMExtractor, ProviderError, extractor_response_schema
from app.services.extraction.prompts import DOC_NOTES, SYSTEM

RETRY_STATUS = {429, 500, 503, 504}
BACKOFF_S = 4.0  # first wait; doubles each retry (default 2 retries: 4 s + 8 s)
MAX_BACKOFF_S = 30.0  # a longer Retry-After is cut to this; the fallback chain takes over
KEEP = ("type", "description", "enum", "nullable", "required", "properties", "items")
# the shared prompt asks for a tool call; Gemini answers with JSON instead
JSON_NOTE = (
    "\n\nThere is no tool here: return the record as one JSON object that follows the response "
    "schema."
)
sleep = time.sleep  # patched in tests


def to_gemini_schema(schema: dict) -> dict:
    """Pydantic JSON schema -> Gemini response schema: $ref inlined, anyOf resolved (null ->
    nullable; Decimal's number|string -> string, exact), const -> enum, other keywords
    (title, default, format, pattern, additionalProperties, $defs) dropped."""
    defs = schema.get("$defs", {})

    def convert(node: dict) -> dict:
        if "$ref" in node:
            target = defs[node["$ref"].rsplit("/", 1)[-1]]
            return convert({**target, **{k: v for k, v in node.items() if k != "$ref"}})
        if "anyOf" in node:
            options = [o for o in node["anyOf"] if o.get("type") != "null"]
            chosen = next((o for o in options if o.get("type") == "string"), options[0])
            extra = {k: v for k, v in node.items() if k != "anyOf"}
            out = convert({**chosen, **extra})
            if len(options) < len(node["anyOf"]):
                out["nullable"] = True
            return out
        out: dict = {}
        if "const" in node:
            out["enum"] = [node["const"]]
        for key in KEEP:
            if key not in node or key in out:
                continue
            value = node[key]
            if key == "properties":
                value = {name: convert(sub) for name, sub in value.items()}
            elif key == "items":
                value = convert(value)
            out[key] = value
        if "enum" in out:
            out.setdefault("type", "string")
        return out

    return convert(schema)


def retry_after_s(e: errors.APIError) -> float | None:
    """Seconds the provider asked us to wait: the Retry-After header, or Gemini's RetryInfo
    retryDelay ("17s") in the error body. None when absent or not a number."""
    headers = getattr(getattr(e, "response", None), "headers", None)
    value = headers.get("retry-after") if headers is not None else None
    if value is None and isinstance(e.details, dict):
        for d in e.details.get("error", {}).get("details") or []:
            if isinstance(d, dict) and str(d.get("@type", "")).endswith("RetryInfo"):
                value = str(d.get("retryDelay", "")).removesuffix("s")
    try:
        return float(value) if value is not None else None
    except ValueError:  # an HTTP date: use our own backoff
        return None


@cache
def gemini_schema(doc_type: str) -> dict:
    return to_gemini_schema(extractor_response_schema(doc_type))


class GeminiExtractor(LLMExtractor):
    provider = "gemini"
    model_setting = "GEMINI_MODEL"

    def _default_model(self) -> str | None:
        return settings.gemini_model

    def _make_client(self):
        key = settings.gemini_api_key
        if key is None:
            raise ValueError("GEMINI_API_KEY is not set")
        return genai.Client(
            api_key=key.get_secret_value(),
            http_options=types.HttpOptions(timeout=int(settings.llm_timeout_s * 1000)),  # ms
        )

    def _generate(self, contents, config):
        retries = settings.gemini_max_retries
        for attempt in range(retries + 1):
            try:
                return self.client.models.generate_content(
                    model=self.model, contents=contents, config=config
                )
            except (errors.APIError, httpx.TimeoutException) as e:
                code = getattr(e, "code", None) if isinstance(e, errors.APIError) else "timeout"
                if (code in RETRY_STATUS or code == "timeout") and attempt < retries:
                    wait = BACKOFF_S * 2**attempt
                    if isinstance(e, errors.APIError):
                        wait = max(wait, retry_after_s(e) or 0)
                    sleep(min(wait, MAX_BACKOFF_S))
                    continue
                raise ProviderError(f"{type(e).__name__} {code or ''}".strip()) from e
        raise ProviderError("no response")  # not reached

    def _call(self, data: bytes, media_type: str, doc_type: str):
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM + JSON_NOTE,
            response_mime_type="application/json",
            response_schema=gemini_schema(doc_type),
            max_output_tokens=self.max_tokens,
            temperature=0,
        )
        contents = [
            types.Part.from_bytes(data=data, mime_type=media_type),
            f"{DOC_NOTES[doc_type]}\n\nReturn the JSON record for this document.",
        ]
        response = self._generate(contents, config)
        usage = response.usage_metadata
        tokens_in = (usage.prompt_token_count or 0) if usage else 0
        tokens_out = (
            (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0) if usage else 0
        )
        finish = response.candidates[0].finish_reason if response.candidates else None
        if finish == types.FinishReason.MAX_TOKENS:
            return None, "output truncated at max_tokens", tokens_in, tokens_out
        try:
            answer = json.loads(response.text or "")
        except json.JSONDecodeError:
            return None, "answer is not JSON", tokens_in, tokens_out
        if not isinstance(answer, dict):
            return None, "answer is not a JSON object", tokens_in, tokens_out
        return answer, None, tokens_in, tokens_out

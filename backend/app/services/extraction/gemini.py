"""Gemini vision extractor (Google Gen AI SDK), selected with LLM_PROVIDER=gemini.

Same behaviour as AnthropicExtractor (LLMExtractor: cache with the provider in the key, budget
guard, validation, error results instead of exceptions). Structured output through
response_schema, built from the same extractor-only schema; Gemini's schema subset has no $ref,
anyOf or const, so to_gemini_schema inlines and simplifies it. On HTTP 429 (free-tier rate limit)
or 503 the call backs off and retries.

Gemini's free tier may use inputs to improve Google's models: synthetic documents only
(CLAUDE.md).
"""

import json
import time
from functools import cache

from google import genai
from google.genai import errors, types

from app.core.config import settings
from app.services.extraction.llm import LLMExtractor, ProviderError, extractor_schema
from app.services.extraction.prompts import DOC_NOTES, SYSTEM

RETRY_STATUS = {429, 503}
BACKOFF_S = 2.0  # first wait; doubles each retry, at most MAX_BACKOFF_S
MAX_BACKOFF_S = 60.0
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


@cache
def gemini_schema(doc_type: str) -> dict:
    return to_gemini_schema(extractor_schema(doc_type))


class GeminiExtractor(LLMExtractor):
    provider = "gemini"
    model_setting = "GEMINI_MODEL"

    def _default_model(self) -> str | None:
        return settings.gemini_model

    def _make_client(self):
        key = settings.gemini_api_key
        if key is None:
            raise ValueError("GEMINI_API_KEY is not set")
        return genai.Client(api_key=key.get_secret_value())

    def _generate(self, contents, config):
        retries = settings.gemini_max_retries
        for attempt in range(retries + 1):
            try:
                return self.client.models.generate_content(
                    model=self.model, contents=contents, config=config
                )
            except errors.APIError as e:
                code = getattr(e, "code", None)
                if code in RETRY_STATUS and attempt < retries:
                    sleep(min(BACKOFF_S * 2**attempt, MAX_BACKOFF_S))
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

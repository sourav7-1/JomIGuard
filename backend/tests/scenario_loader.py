"""Load a scenario folder (tests/scenarios/NN_name/) as a LandCase plus its answer key."""

import json
from pathlib import Path

from pydantic import TypeAdapter

from app.schemas.extracted import ExtractedDocument
from app.schemas.land_case import CaseDocumentInput, LandCase
from app.services.land_case import build_land_case
from app.services.normalize import normalize_document

_documents = TypeAdapter(ExtractedDocument)


def load_scenario(folder: Path) -> tuple[LandCase, dict]:
    """Every *.json except expected.json is a document; its file name is the source_id.
    Documents go through normalize like an extraction would (status, field flags)."""
    inputs = []
    for path in sorted(folder.glob("*.json")):
        if path.name == "expected.json":
            continue
        result = normalize_document(_documents.validate_json(path.read_bytes()))
        flags: dict[str, list[str]] = {}
        for w in result.warnings:
            flags.setdefault(w.field_path, []).append(w.code)
        inputs.append(
            CaseDocumentInput(
                source_id=path.name,
                data=result.doc,
                extraction_status="needs_review" if result.warnings else "ok",
                field_flags=flags,
            )
        )
    expected = json.loads((folder / "expected.json").read_text(encoding="utf-8"))
    return build_land_case(inputs), expected

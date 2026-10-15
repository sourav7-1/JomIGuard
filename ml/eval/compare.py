"""Field-level comparison of extracted documents (pure functions; used by eval.extraction).

Both sides are normalized first (normalize_document), then compared as dicts:
- identifiers (*_no, deed_year): exact after normalize_identifier ("৩০৫" == "305")
- name_normalized: exact; printed `name`: CER only; other *_name fields: exact on
  normalize_name plus CER
- numbers (Decimal), dates, enums, bools: exact; other strings: exact after NFC/space cleanup
- *_text: CER only (not counted in accuracy)
- lists: Hungarian matching (people by name_normalized similarity, plots by dag_no), then
  field-by-field inside pairs; unmatched items are missed / wrong predicted fields
- a wrong doc_type makes every field of the document wrong
Critical = the field's rule column in docs/specs/fields.md has identity, area, heirs or chain.
"""

import re
import typing
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import numpy as np
from app.schemas.extracted import (
    DeedData,
    ExtractedDocument,
    HeirCertData,
    KhatianData,
    MutationData,
)
from app.services.normalize import clean, normalize_document, normalize_identifier, normalize_name
from pydantic import BaseModel, TypeAdapter, ValidationError
from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein
from scipy.optimize import linear_sum_assignment

MODELS: dict[str, type[BaseModel]] = {
    "khatian": KhatianData,
    "deed": DeedData,
    "dcr": MutationData,
    "heir_cert": HeirCertData,
}
CRITICAL_RULES = {"identity", "area", "heirs", "chain"}
FIELDS_MD = Path(__file__).resolve().parents[2] / "docs/specs/fields.md"
_documents = TypeAdapter(ExtractedDocument)


def _rules_from_fields_md(text: str) -> dict[str, dict[str, set[str]]]:
    """{model name: {field: rules}} from the field tables (rule = 6th column)."""
    rules: dict[str, dict[str, set[str]]] = {}
    model = None
    for line in text.splitlines():
        if line.startswith("#"):
            names = re.findall(r"`(\w+)`", line)
            model = names[-1] if names else None
        elif model and line.startswith("| ") and not line.startswith("| field_name"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 6 and not set(cells[0]) <= {"-"}:
                rules.setdefault(model, {})[cells[0]] = {r.strip() for r in cells[5].split(",")}
    return rules


RULES = _rules_from_fields_md(FIELDS_MD.read_text(encoding="utf-8"))


def is_critical(model: type[BaseModel], field: str) -> bool:
    return bool(RULES.get(model.__name__, {}).get(field, set()) & CRITICAL_RULES)


@dataclass
class FieldResult:
    doc_type: str
    path: str  # "owners[1].share_fraction" (ground-truth index; predicted index if unmatched)
    generic: str  # "khatian.owners[].share_fraction": aggregation key
    critical: bool
    expected: object
    predicted: object
    gt_present: bool
    pred_present: bool
    correct: bool | None  # None: not counted in accuracy (CER-only field)
    cer: float | None  # None: no CER for this field or no ground truth


@dataclass
class ListCount:
    doc_type: str
    generic: str
    expected: int
    predicted: int


@dataclass
class Comparison:
    fields: list[FieldResult]
    lists: list[ListCount]


# --- normalization ---


def normalized(doc: BaseModel) -> dict:
    return normalize_document(doc).doc.model_dump()


def prepare_prediction(raw: dict | None) -> tuple[dict | None, str | None]:
    """Prediction JSON -> (normalized dict, error). {"error": ...} or invalid -> (None, error)."""
    if raw is None:
        return None, "missing"
    if "error" in raw:
        return None, str(raw["error"])
    body = {k: v for k, v in raw.items() if k != "meta"}
    try:
        return normalized(_documents.validate_python(body)), None
    except ValidationError as e:
        return None, f"invalid: {e.error_count()} validation errors"


# --- values ---


def cer(expected: str, predicted: str | None) -> float:
    """Character error rate: edit distance / ground-truth length, capped at 1."""
    e, p = clean(expected), clean(predicted or "")
    if not e:
        return 0.0 if not p else 1.0
    return min(1.0, Levenshtein.distance(e, p) / len(e))


def _text(v) -> str:
    return " ".join(clean(str(v)).split())


def _key(field: str, v):
    """Comparable form of a value for exact matching."""
    if v is None:
        return None
    if field.endswith("_no") or field == "deed_year":
        return normalize_identifier(str(v))
    if field.endswith("_name"):
        return normalize_name(str(v))
    if isinstance(v, Decimal):
        return v
    if isinstance(v, str):
        return _text(v)
    return v


def _present(v) -> bool:
    return v is not None and v != ""


# --- structure ---


def _nested_model(model: type[BaseModel], field: str) -> type[BaseModel] | None:
    ann = model.model_fields[field].annotation
    stack = [ann]
    while stack:
        t = stack.pop()
        if isinstance(t, type) and issubclass(t, BaseModel):
            return t
        stack.extend(typing.get_args(t))
    return None


def _similarity(model: type[BaseModel], a: dict, b: dict) -> float:
    """0-1 similarity of two list items, for matching."""
    if "name_normalized" in model.model_fields or "name" in model.model_fields:
        an = a.get("name_normalized") or normalize_name(a.get("name") or "")
        bn = b.get("name_normalized") or normalize_name(b.get("name") or "")
        return fuzz.ratio(an, bn) / 100
    if "dag_no" in model.model_fields:
        return float(_key("dag_no", a.get("dag_no")) == _key("dag_no", b.get("dag_no")))
    keys = [f for f in model.model_fields if f.endswith("_no") or f == "survey_type"]
    same = [_key(f, a.get(f)) == _key(f, b.get(f)) for f in keys]
    return sum(same) / len(same) if same else 0.0


def _compare(model, gt: dict, pred: dict, path: str, generic: str, doc_type: str, out):
    for field in model.model_fields:
        g, p = gt.get(field), pred.get(field)
        fpath = f"{path}.{field}" if path else field
        fgen = f"{generic}.{field}"
        nested = _nested_model(model, field)
        if nested is not None and (isinstance(g, list) or isinstance(p, list)):
            _compare_list(nested, g or [], p or [], fpath, fgen, doc_type, out)
        elif nested is not None:
            _compare(nested, g or {}, p or {}, fpath, fgen, doc_type, out)
        else:
            out.fields.append(_leaf(model, field, g, p, fpath, fgen, doc_type))


def _leaf(model, field, g, p, path, generic, doc_type) -> FieldResult:
    cer_only = field == "name" or field.endswith("_text")
    with_cer = cer_only or field.endswith("_name")
    gp, pp = _present(g), _present(p)
    correct = None if cer_only else (gp and pp and _key(field, g) == _key(field, p))
    return FieldResult(
        doc_type=doc_type,
        path=path,
        generic=generic,
        critical=is_critical(model, field),
        expected=g,
        predicted=p,
        gt_present=gp,
        pred_present=pp,
        correct=correct,
        cer=cer(str(g), str(p) if pp else None) if with_cer and gp else None,
    )


def _compare_list(model, gt: list, pred: list, path, generic, doc_type, out):
    out.lists.append(ListCount(doc_type, f"{generic}[]", len(gt), len(pred)))
    pairs: list[tuple[int, int]] = []
    if gt and pred:
        cost = np.array([[1 - _similarity(model, g, p) for p in pred] for g in gt])
        rows, cols = linear_sum_assignment(cost)
        pairs = list(zip(rows.tolist(), cols.tolist(), strict=True))
    for gi, pi in pairs:
        _compare(model, gt[gi], pred[pi], f"{path}[{gi}]", f"{generic}[]", doc_type, out)
    matched_g, matched_p = {g for g, _ in pairs}, {p for _, p in pairs}
    for gi in sorted(set(range(len(gt))) - matched_g):
        _compare(model, gt[gi], {}, f"{path}[{gi}]", f"{generic}[]", doc_type, out)
    for pi in sorted(set(range(len(pred))) - matched_p):
        _compare(model, {}, pred[pi], f"{path}[+{pi}]", f"{generic}[]", doc_type, out)


def compare_documents(gt: dict, pred: dict | None) -> Comparison:
    """Compare two normalized document dicts (pred None = nothing predicted)."""
    out = Comparison([], [])
    doc_type = gt["doc_type"]
    pred = pred or {}
    if pred and pred.get("doc_type") != doc_type:
        # wrong document type: every ground-truth field missed, every predicted field wrong
        _compare(MODELS[doc_type], gt, {}, "", doc_type, doc_type, out)
        if pred.get("doc_type") in MODELS:
            wrong = Comparison([], [])
            other = pred["doc_type"]
            _compare(MODELS[other], {}, pred, "", other, doc_type, wrong)
            out.fields += [f for f in wrong.fields if f.pred_present]
        return out
    _compare(MODELS[doc_type], gt, pred, "", doc_type, doc_type, out)
    return out


# --- metrics ---


def metrics(fields: list[FieldResult], lists: list[ListCount] = ()) -> dict:
    counted = [f for f in fields if f.correct is not None]
    gt_n = sum(f.gt_present for f in counted)
    pred_n = sum(f.pred_present for f in counted)
    ok = sum(bool(f.correct) for f in counted)
    crit = [f for f in counted if f.critical]
    crit_gt = sum(f.gt_present for f in crit)
    cers = [f.cer for f in fields if f.cer is not None]
    return {
        "accuracy": ok / gt_n if gt_n else None,  # = recall
        "precision": ok / pred_n if pred_n else None,
        "recall": ok / gt_n if gt_n else None,
        "critical_accuracy": sum(bool(f.correct) for f in crit) / crit_gt if crit_gt else None,
        "mean_cer": sum(cers) / len(cers) if cers else None,
        "list_count_accuracy": (
            sum(lc.expected == lc.predicted for lc in lists) / len(lists) if lists else None
        ),
        "fields_gt": gt_n,
        "fields_pred": pred_n,
        "fields_correct": ok,
        "critical_gt": crit_gt,
    }

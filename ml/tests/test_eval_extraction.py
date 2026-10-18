import copy
import json
from pathlib import Path

import pytest
from app.schemas.extracted import DeedData, KhatianData, Owner, Plot

from eval.compare import (
    cer,
    compare_documents,
    is_critical,
    metrics,
    normalized,
    prepare_prediction,
)
from eval.extraction import baseline, evaluate, load_handwritten_items, load_items
from synth.deed import generate_cases

SAMPLES = Path(__file__).resolve().parents[2] / "backend/tests/fixtures/samples"


def test_handwritten_loader_pairs_synthetic_deed_and_ground_truth(tmp_path):
    (tmp_path / "demo.png").write_bytes(b"synthetic image")
    (tmp_path / "demo.json").write_text('{"doc_type":"deed"}', encoding="utf-8")
    (tmp_path / "orphan.json").write_text('{"doc_type":"deed"}', encoding="utf-8")
    [item] = load_handwritten_items(tmp_path)
    assert item.image_id == "demo" and item.doc_type == "deed"
    assert item.image_path == tmp_path / "demo.png"


def test_handwritten_loader_rejects_non_deed_pair(tmp_path):
    (tmp_path / "demo.png").write_bytes(b"synthetic image")
    (tmp_path / "demo.json").write_text('{"doc_type":"khatian"}', encoding="utf-8")
    with pytest.raises(ValueError, match="must be a deed"):
        load_handwritten_items(tmp_path)


def sample(name: str, model):
    return model.model_validate_json((SAMPLES / f"{name}.json").read_bytes())


@pytest.fixture
def khatian() -> KhatianData:
    return sample("khatian", KhatianData)


def score(gt, pred) -> dict:
    c = compare_documents(normalized(gt), None if pred is None else normalized(pred))
    return metrics(c.fields, c.lists)


def owner_fields(gt) -> int:
    """Counted ground-truth fields of owners[2] (name_normalized, father, marker, shares)."""
    c = compare_documents(normalized(gt), normalized(gt))
    return sum(
        f.gt_present and f.correct is not None for f in c.fields if f.path.startswith("owners[2].")
    )


def test_identical_prediction_is_perfect(khatian):
    m = score(khatian, khatian.model_copy(deep=True))
    assert m["accuracy"] == m["precision"] == m["recall"] == m["critical_accuracy"] == 1
    assert m["mean_cer"] == 0 and m["list_count_accuracy"] == 1


def test_bangla_digits_count_as_correct(khatian):
    pred = khatian.model_copy(deep=True)
    pred.khatian_no = "৮৮২"
    pred.plots[0].dag_no = "৩০৫"
    pred.location.jl_no = "৪৫"
    assert score(khatian, pred)["accuracy"] == 1


def test_owner_order_does_not_matter(khatian):
    pred = khatian.model_copy(deep=True)
    pred.owners.reverse()
    m = score(khatian, pred)
    assert m["accuracy"] == m["precision"] == 1


def test_missing_owner_lowers_recall_only(khatian):
    full = score(khatian, khatian)
    pred = khatian.model_copy(deep=True)
    pred.owners.pop(2)
    m = score(khatian, pred)
    n = owner_fields(khatian)
    assert n == 5  # name_normalized, father, relation_marker, share_fraction, share_shatangsho
    assert m["fields_gt"] == full["fields_gt"]
    assert m["fields_correct"] == full["fields_correct"] - n
    assert m["recall"] == pytest.approx((full["fields_correct"] - n) / full["fields_gt"])
    assert m["precision"] == 1
    assert m["list_count_accuracy"] < 1


def test_hallucinated_owner_lowers_precision_only(khatian):
    pred = khatian.model_copy(deep=True)
    pred.owners.append(Owner(name="মোঃ জলিল মিয়া", father_or_husband_name="করিম", share_text=".১০০"))
    m = score(khatian, pred)
    assert m["recall"] == 1
    assert m["precision"] < 1
    assert m["fields_pred"] > m["fields_correct"]


def test_wrong_doc_type_makes_everything_wrong(khatian):
    deed = sample("deed", DeedData)
    m = score(khatian, deed)
    assert m["fields_correct"] == 0 and m["accuracy"] == 0
    assert m["fields_pred"] > 0 and m["precision"] == 0  # every predicted field counts wrong


def test_error_prediction_counts_as_all_missed(khatian, tmp_path):
    doc, err = prepare_prediction({"error": "timeout", "meta": {"latency_s": 3.0}})
    assert doc is None and err == "timeout"
    m = score(khatian, None)
    assert m["accuracy"] == 0 and m["precision"] is None and m["fields_gt"] > 0
    invalid, err = prepare_prediction({"doc_type": "khatian"})  # misses required fields
    assert invalid is None and err.startswith("invalid")


def test_cer_small_value():
    gt, pred = "রহিম উদ্দিন", "রহিম উদ্দীন"  # one vowel sign differs (ি vs ী)
    assert cer(gt, pred) == pytest.approx(1 / len(gt))
    assert cer(gt, gt) == 0 and cer(gt, None) == 1


def test_critical_accuracy_uses_only_critical_fields(khatian):
    assert is_critical(Owner, "share_fraction") and is_critical(KhatianData, "khatian_no")
    assert not is_critical(Plot, "land_class") and not is_critical(KhatianData, "doc_type")
    pred = khatian.model_copy(deep=True)
    pred.plots[0].land_class = "ভিটি"  # rule "none yet"
    m = score(khatian, pred)
    assert m["accuracy"] < 1 and m["critical_accuracy"] == 1
    pred.khatian_no = "883"  # identity, chain
    assert score(khatian, pred)["critical_accuracy"] < 1


def tiny_dataset(root: Path) -> dict:
    files = []
    for c in generate_cases(3, seed=5):
        docs = [c.khatian, c.deed, c.mutation] + ([c.heir_cert] if c.family else [])
        for doc in docs:
            name = "mutation" if doc.doc_type == "dcr" else doc.doc_type
            rel = f"synthetic/cases/{c.id}/{name}"
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / f"{rel}.json").write_text(doc.model_dump_json(), encoding="utf-8")
            (root / f"{rel}.png").write_bytes(b"png")  # images are not read by the eval
            for ext in ("json", "png"):
                files.append({"path": f"{rel}.{ext}", "doc_type": name, "split": "test"})
    return {"files": files}


def test_oracle_and_empty_baselines(tmp_path):
    items = load_items(tiny_dataset(tmp_path), tmp_path, "test", None)
    assert len(items) >= 9 and {it.preset for it in items} == {"clean"}
    oracle, _ = evaluate(items, baseline(items, "oracle"))
    o = oracle["overall"]
    assert o["accuracy"] == o["precision"] == o["critical_accuracy"] == 1
    assert o["mean_cer"] == 0
    empty, rows = evaluate(items, baseline(items, "empty"))
    assert empty["overall"]["accuracy"] < 0.05
    assert rows and empty["error_predictions"] == 0 and empty["missing_predictions"] == 0


def test_missing_prediction_file_is_counted(tmp_path):
    items = load_items(tiny_dataset(tmp_path), tmp_path, "test", "deed")
    assert {it.doc_type for it in items} == {"deed"}
    preds = baseline(items, "oracle")
    first = items[0].image_id
    del preds[first]
    preds[items[1].image_id] = (None, "boom", {"latency_s": 2.0, "cost_usd": 0.01})
    report, _ = evaluate(items, preds)
    assert report["missing_predictions"] == 1 and report["error_predictions"] == 1
    assert report["mean_latency_s"] == 2.0
    assert report["overall"]["precision"] == 1 and report["overall"]["recall"] < 1


def test_inputs_not_mutated(khatian):
    gt = normalized(khatian)
    before = copy.deepcopy(gt)
    compare_documents(gt, gt)
    assert gt == before
    json.dumps(before, default=str)  # stays serialisable for report.json

"""Identity rules on small cases built from the scenario 02 documents (everything matches)."""

from pathlib import Path

import pytest
from scenario_loader import load_scenario

from app.services.rules import Status, run_rules

BASE = Path(__file__).parents[1] / "scenarios/02_sells_within_share"


@pytest.fixture
def case():
    c, _ = load_scenario(BASE)
    return c


def edit(doc, **changes):
    doc.data = doc.data.model_copy(update=changes)


def results(case, rule_id):
    return run_rules(case, [rule_id]).results


def statuses(case, rule_id):
    return [r.status for r in results(case, rule_id)]


# --- plots_on_khatian ---


def test_dag_on_khatian_passes(case):
    [r] = results(case, "plots_on_khatian")
    assert r.status == Status.passed and "৩০৫" in r.message_bn


def test_dag_not_on_khatian_is_bad(case):
    deed = case.proposed_deed
    plot = deed.data.schedule_plots[0].model_copy(update={"dag_no": "৩০৬"})
    edit(deed, schedule_plots=[plot])
    [r] = results(case, "plots_on_khatian")
    assert (r.code, r.status) == ("dag_mismatch", Status.bad)
    assert "দলিলে দাগ ৩০৬, কিন্তু বর্তমান খতিয়ান (BS ৮৮২)-এ দাগ ৩০৫" in r.message_bn
    assert {s.source_id for s in r.sources} == {"deed.json", "khatian_bs.json"}
    assert r.values["deed_dag"] == "306"  # identifiers compared after normalizing digits


def test_dag_written_in_bangla_digits_still_matches(case):
    deed = case.proposed_deed
    edit(deed, schedule_plots=[deed.data.schedule_plots[0].model_copy(update={"dag_no": "৩০৫"})])
    assert statuses(case, "plots_on_khatian") == [Status.passed]


# --- khatian_refs ---


def test_khatian_refs_pass_and_ignore_surveys_not_in_case(case):
    # deed lists BS 882 and SA 214; the case has only the BS khatian: SA is ignored
    assert statuses(case, "khatian_refs") == [Status.passed]


def test_wrong_khatian_number_is_bad(case):
    deed = case.proposed_deed
    refs = [r.model_copy(update={"khatian_no": "883"}) if r.survey_type == "BS" else r
            for r in deed.data.schedule_khatians]  # fmt: skip
    edit(deed, schedule_khatians=refs)
    [r] = results(case, "khatian_refs")
    assert (r.code, r.status) == ("khatian_mismatch", Status.bad)
    assert "৮৮৩" in r.message_bn and "৮৮২" in r.message_bn


def test_no_comparable_khatian_is_skipped(case):
    deed = case.proposed_deed
    edit(deed, schedule_khatians=[r for r in deed.data.schedule_khatians if r.survey_type == "SA"])
    assert statuses(case, "khatian_refs") == [Status.skipped]


# --- mouza_match ---


def test_mouza_pass_with_small_spelling_difference(case):
    loc = case.proposed_deed.data.schedule_location
    edit(case.proposed_deed, schedule_location=loc.model_copy(update={"mouza": "চাঁদশি"}))
    assert statuses(case, "mouza_match") == [Status.passed]


def test_other_mouza_is_bad(case):
    loc = case.proposed_deed.data.schedule_location
    edit(case.proposed_deed, schedule_location=loc.model_copy(update={"mouza": "বাটাজোর"}))
    [r] = results(case, "mouza_match")
    assert (r.code, r.status) == ("mouza_mismatch", Status.bad)
    assert "বাটাজোর" in r.message_bn and "চাঁদশী" in r.message_bn


def test_same_mouza_other_jl_is_bad(case):
    loc = case.proposed_deed.data.schedule_location
    edit(case.proposed_deed, schedule_location=loc.model_copy(update={"jl_no": "46"}))
    [r] = results(case, "mouza_match")
    assert r.code == "mouza_mismatch" and "৪৬" in r.message_bn


# --- seller_is_owner and seller_father ---


def seller(case, **changes):
    deed = case.proposed_deed
    edit(deed, sellers=[deed.data.sellers[0].model_copy(update=changes)])


def test_seller_with_honorific_and_spelling_variant_is_owner(case):
    seller(case, name="মোঃ রহিম উদ্দীন", name_normalized="রহিম উদ্দীন")
    [r] = results(case, "seller_is_owner")
    assert r.status == Status.passed and r.values["owner"] == "রহিম উদ্দিন"


def test_brother_with_similar_name_is_not_owner(case):
    owners = case.current_khatian.data.owners
    edit(case.current_khatian, owners=[o for o in owners if o.name_normalized != "রহিম উদ্দিন"])
    [r] = results(case, "seller_is_owner")  # "করিম উদ্দিন" is still an owner
    assert (r.code, r.status) == ("seller_not_owner", Status.bad)
    assert "রহিম উদ্দিন" in r.message_bn and "করিম উদ্দিন" in r.message_bn


def test_one_result_per_seller(case):
    deed = case.proposed_deed
    stranger = deed.data.sellers[0].model_copy(update={"name": "জলিল", "name_normalized": "জলিল"})
    edit(deed, sellers=[deed.data.sellers[0], stranger])
    assert statuses(case, "seller_is_owner") == [Status.passed, Status.bad]


def test_father_matches(case):
    [r] = results(case, "seller_father")
    assert r.status == Status.passed


def test_father_differs_is_warn(case):
    seller(case, father_or_husband_name="কাশেম")
    [r] = results(case, "seller_father")
    assert (r.code, r.status) == ("seller_father_mismatch", Status.warn)
    assert "কাশেম" in r.message_bn and "রহমান" in r.message_bn


def test_missing_father_is_skipped(case):
    seller(case, father_or_husband_name=None)
    assert statuses(case, "seller_father") == [Status.skipped]


def two_rahims(case, father_b: str):
    owners = case.current_khatian.data.owners
    other = owners[0].model_copy(update={"father_or_husband_name": father_b})
    edit(case.current_khatian, owners=[*owners, other])


def test_same_name_owners_father_chooses(case):
    two_rahims(case, "ইউসুফ আলী")  # second রহিম উদ্দিন, son of ইউসুফ আলী
    [r] = results(case, "seller_father")  # seller's father is রহমান: picks the first owner
    assert r.status == Status.passed and r.values["khatian_father"] == "রহমান"
    assert statuses(case, "seller_is_owner") == [Status.passed]


def test_same_name_owners_still_ambiguous_warns(case):
    two_rahims(case, "রহমান")  # same name, same father
    [r] = results(case, "seller_father")
    assert (r.code, r.status) == ("seller_father_mismatch", Status.warn)
    assert "একাধিক মালিক" in r.message_bn


def test_rules_skip_without_a_current_khatian(case):
    case.documents = [d for d in case.documents if d.source_id != "khatian_bs.json"]
    run = run_rules(case, ["plots_on_khatian", "seller_is_owner"])
    assert [r.status for r in run.results] == [Status.skipped, Status.skipped]

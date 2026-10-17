"""Area rules on small cases built from scenario documents."""

from decimal import Decimal
from pathlib import Path

import pytest
from scenario_loader import load_scenario

from app.services.normalize import parse_share, to_bangla_digits
from app.services.rules import Status, run_rules

SCENARIOS = Path(__file__).parents[1] / "scenarios"


def case_of(name: str):
    case, _ = load_scenario(SCENARIOS / name)
    return case


def edit(doc, **changes):
    doc.data = doc.data.model_copy(update=changes)


def sell(case, shatangsho: str | None, dag: str = "305", per_dag: bool = True):
    """Set the deed's sold area (one schedule plot); None = area could not be read."""
    deed = case.proposed_deed
    text = f"{to_bangla_digits(shatangsho)} শতাংশ" if shatangsho else "অস্পষ্ট"
    value = Decimal(shatangsho) if shatangsho else None
    plot = deed.data.schedule_plots[0].model_copy(
        update={"dag_no": dag, "area_text": text, "area_shatangsho": value if per_dag else None}
    )
    edit(deed, schedule_plots=[plot], transferred_area_text=text,
         transferred_area_shatangsho=value)  # fmt: skip


def result(case, rule_id="sold_within_share"):
    [r] = run_rules(case, [rule_id]).results
    return r


# --- sold_within_share ---


@pytest.mark.parametrize(
    ("sold", "status"),
    [("5", Status.passed), ("6", Status.passed), ("10", Status.bad), ("6.01", Status.bad)],
)
def test_sold_against_share(sold, status):
    case = case_of("02_sells_within_share")  # রহিম: .৪০০ of dag 305 (15 শতাংশ) = 6
    sell(case, sold)
    r = result(case)
    assert r.status == status
    assert r.values["available_shatangsho"] == Decimal("6") and r.values["method"] == "per_dag"
    assert r.values["sold_shatangsho"] == Decimal(sold)


def test_demo_message_and_sources():
    case = case_of("01_demo_area_exceeds")
    r = result(case)
    assert (r.code, r.status) == ("area_exceeds_share", Status.bad)
    assert "খতিয়ানে দাগ ৩০৫-এ রহিম উদ্দিন-এর অংশ ৬ শতাংশ, কিন্তু দলিলে ১০ শতাংশ" in r.message_bn
    assert "অতিরিক্ত ৪ শতাংশ" in r.message_bn
    printed = {(s.source_id, s.printed_text) for s in r.sources}
    assert ("khatian_bs.json", ".৪০০") in printed  # owner share_text
    assert ("khatian_bs.json", ".১৫০০") in printed  # plot area
    assert ("deed.json", "১০ শতাংশ") in printed  # deed area
    assert r.values["sellers"] == ["রহিম উদ্দিন"] and r.values["dags"] == ["305"]


def test_no_transferred_area_is_skipped():
    case = case_of("02_sells_within_share")
    sell(case, None)
    r = result(case)
    assert r.status == Status.skipped and "হস্তান্তরিত" in r.skip_reason


def test_two_sellers_combined_share_covers_the_sale():
    case = case_of("06_two_heirs_sell_jointly")  # রহিম + করিম: 6 + 6
    sell(case, "12")
    r = result(case)
    assert r.status == Status.passed and r.values["available_shatangsho"] == Decimal("12")
    assert "রহিম উদ্দিন ও করিম উদ্দিন-এর মোট অংশ ১২ শতাংশ" in r.message_bn
    sell(case, "12.5")
    assert result(case).status == Status.bad


def test_seller_not_on_khatian_is_skipped_not_bad():
    case = case_of("07_seller_not_owner")
    r = result(case)
    assert r.status == Status.skipped and "মেলেনি" in r.skip_reason


def test_three_dag_khatian_compares_the_sold_dag_only():
    case = case_of("17_multi_dag_within_share")  # রহিম: 12 on the khatian, 6 in dag 305
    sell(case, "5")
    assert result(case).status == Status.passed
    sell(case, "8")
    r = result(case)
    assert r.status == Status.bad and r.values["available_shatangsho"] == Decimal("6")


def test_deed_with_only_a_total_compares_the_listed_dags():
    case = case_of("17_multi_dag_within_share")
    sell(case, "6", per_dag=False)
    r = result(case)
    assert r.values["method"] == "total_over_listed_dags" and r.status == Status.passed


def test_dag_not_on_khatian_falls_back_to_the_whole_khatian():
    case = case_of("02_sells_within_share")
    sell(case, "5", dag="399")
    r = result(case)
    assert r.values["method"] == "whole_khatian" and r.status == Status.passed
    sell(case, "7", dag="399")
    assert result(case).status == Status.bad


# --- shares_add_up ---


def set_shares(case, texts: list[str]):
    k = case.current_khatian
    owners = [
        o.model_copy(update={"share_text": t, "share_fraction": parse_share(t)[0]})
        for o, t in zip(k.data.owners, texts, strict=True)
    ]
    edit(k, owners=owners)


def share_results(case):
    return run_rules(case, ["shares_add_up"]).results


def test_shares_summing_to_900_warn():
    case = case_of("02_sells_within_share")
    set_shares(case, [".৪০০", ".৪০০", ".১০০"])
    [k, m] = share_results(case)  # khatian and mutation: one result each
    assert (k.code, k.status) == ("area_sum_mismatch", Status.warn)
    assert "০.৯" in k.message_bn and m.status == Status.passed


def test_shares_summing_to_one_pass():
    case = case_of("02_sells_within_share")
    set_shares(case, [".৪০০", ".৪০০", ".২০০"])
    assert all(r.status == Status.passed for r in share_results(case))


def test_thirds_within_tolerance_pass():
    case = case_of("02_sells_within_share")
    set_shares(case, [".৩৩৪", ".৩৩৩", ".৩৩৩"])
    assert share_results(case)[0].status == Status.passed


def test_unparseable_share_is_skipped():
    case = case_of("02_sells_within_share")
    k = case.current_khatian
    bad = k.data.owners[0].model_copy(update={"share_text": "।০ আনা", "share_fraction": None})
    edit(k, owners=[bad, *k.data.owners[1:]])
    assert share_results(case)[0].status == Status.skipped


# --- units ---


def unit_findings(case):
    return [r for r in run_rules(case, ["units"]).results if r.code]


def test_katha_is_unsupported_unit():
    case = case_of("15_unsupported_unit_katha")
    [r] = unit_findings(case)
    assert (r.code, r.status) == ("unsupported_unit", Status.warn)
    assert "২ কাঠা" in r.message_bn
    assert r.values["fields"] == ["schedule_plots[0].area_text", "transferred_area_text"]
    assert {s.source_id for s in r.sources} == {"deed.json"}


def test_no_unit_and_no_header_is_missing_unit():
    case = case_of("16_missing_unit_khatian")
    [r] = unit_findings(case)
    assert (r.code, r.status) == ("missing_unit", Status.warn)
    assert {s.source_id for s in r.sources} == {"khatian_bs.json"}
    assert "plots[0].area_text" in r.values["fields"]


def test_clean_case_passes_units():
    [r] = run_rules(case_of("02_sells_within_share"), ["units"]).results
    assert r.status == Status.passed

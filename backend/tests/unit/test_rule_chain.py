"""ownership_chain on cases built from the scenario documents."""

from datetime import date
from pathlib import Path

from scenario_loader import load_scenario

from app.schemas.land_case import CaseRole
from app.services.rules import Status, run_rules

SCENARIOS = Path(__file__).parents[1] / "scenarios"


def case_of(name: str):
    case, _ = load_scenario(SCENARIOS / name)
    return case


def edit(doc, **changes):
    doc.data = doc.data.model_copy(update=changes)


def doc(case, source_id):
    return next(d for d in case.documents if d.source_id == source_id)


def chain(case):
    return run_rules(case, ["ownership_chain"]).results


def test_consistent_cs_sa_bs_chain_passes():
    [r] = chain(case_of("19_full_chain_cs_sa_bs"))
    assert r.status == Status.passed
    assert "মালিকানার ধারা ১৯৮৫ থেকে বর্তমান পর্যন্ত ভাঙেনি" in r.message_bn
    links = r.values["links"]
    assert links.index("পুরোনো খতিয়ান (CS ৫৭)") < links.index("পুরোনো খতিয়ান (SA ২১৪)")
    assert links.index("বায়া দলিল (১৯৮৫)") < links.index("ওয়ারিশ সনদ")
    assert links.endswith("বর্তমান খতিয়ান (BS ৮৮২)")


def test_prior_deed_seller_not_on_sa_khatian_breaks():
    [r] = chain(case_of("13_chain_break_sa_owner"))
    assert (r.code, r.status) == ("chain_break", Status.bad)
    assert {s.source_id for s in r.sources} == {"khatian_sa.json", "deed_prior_1985.json"}
    assert "আব্দুল করিম" in r.message_bn and "নূর মোহাম্মদ" in r.message_bn


def test_sa_owner_changed_in_full_chain_breaks():
    case = case_of("19_full_chain_cs_sa_bs")
    sa = doc(case, "khatian_sa.json")
    owner = sa.data.owners[0].model_copy(
        update={"name": "নূর মোহাম্মদ", "name_normalized": "নূর মোহাম্মদ"}
    )
    edit(sa, owners=[owner])
    # the 1985 seller still owns the CS khatian, which is older than SA: that link holds
    assert chain(case)[0].status == Status.passed
    edit(doc(case, "khatian_cs.json"), owners=[owner])
    [r] = chain(case)
    assert r.code == "chain_break" and "deed_prior_1985.json" in {s.source_id for s in r.sources}


def test_no_older_khatian_is_skipped():
    [r] = chain(case_of("02_sells_within_share"))
    assert r.status == Status.skipped and "পুরোনো খতিয়ান" in r.skip_reason


def test_no_predecessor_is_skipped():
    case = case_of("19_full_chain_cs_sa_bs")
    case.documents = [
        d for d in case.documents if d.role not in (CaseRole.heir_cert, CaseRole.prior_deed)
    ]
    assert chain(case)[0].status == Status.skipped


def test_deceased_neither_owner_nor_buyer_breaks():
    case = case_of("19_full_chain_cs_sa_bs")
    case.documents = [d for d in case.documents if d.role != CaseRole.prior_deed]
    edit(case.heir_certs[0], deceased_name="জব্বার আলী")
    [r] = chain(case)
    assert r.code == "chain_break"
    assert {s.source_id for s in r.sources} == {"khatian_sa.json", "heir_cert.json"}
    assert "জব্বার আলী" in r.message_bn


def test_purchase_before_the_khatian_record_date_does_not_connect():
    case = case_of("19_full_chain_cs_sa_bs")
    edit(doc(case, "khatian_sa.json"), record_date=date(1990, 1, 1))  # deed is from 1985
    [r] = chain(case)
    assert r.code == "chain_break" and r.values["person"] == "রহমান"


def test_source_khatian_follows_the_mutation_old_khatian_no():
    case = case_of("19_full_chain_cs_sa_bs")
    edit(case.mutations[0], old_khatian_no="57")  # the CS khatian becomes the source
    [r] = chain(case)
    assert r.status == Status.passed
    assert "পুরোনো খতিয়ান (SA ২১৪)" not in r.values["links"]

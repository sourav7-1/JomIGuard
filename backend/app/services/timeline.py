"""Build a document-backed ownership timeline without persisting derived events."""

import re

from app.schemas.assessment import Assessment
from app.schemas.land_case import CaseDocument, CaseRole, LandCase, ref
from app.services.normalize import to_bangla_digits
from app.services.rules.names import match_key

_SURVEY_ORDER = {"CS": 0, "SA": 1, "RS": 2, "BS": 3, "CITY": 4}


def _year(value) -> int | None:
    if value is None:
        return None
    match = re.search(r"\d{4}", str(value))
    return int(match.group()) if match else None


def _owners(items, prefix: str) -> list[dict]:
    return [
        {
            "name": owner.name,
            "share_text": owner.share_text,
            "share_fraction": owner.share_fraction,
            "source_field": f"{prefix}[{i}].name",
        }
        for i, owner in enumerate(items or [])
    ]


def _source(doc: CaseDocument, path: str) -> dict:
    return ref(doc, path).model_dump(mode="json")


def _event(doc, kind, year, title, detail, from_owners, to_owners, area, paths):
    refs = [_source(doc, path) for path in paths if path]
    return {
        "year": year,
        "kind": kind,
        "title_bn": title,
        "detail_bn": detail,
        "from_owners": from_owners,
        "to_owners": to_owners,
        "area": area,
        "sources": refs,
        "source_ids": [doc.source_id],
        "status": "ok",
        "finding_codes": [],
        "_survey_rank": _SURVEY_ORDER.get(getattr(doc.data, "survey_type", ""), 99),
    }


def build_timeline(case: LandCase, assessment: Assessment) -> dict:
    """Make events from case documents; inherit shares only when printed in mutation/khatian."""
    events = []
    for doc in case.documents:
        d = doc.data
        if doc.doc_type == "khatian":
            current = doc.role == CaseRole.current_khatian
            label = "বর্তমান খতিয়ান" if current else "পুরোনো খতিয়ান"
            record_year = _year(d.record_date or d.record_date_text)
            paths = ["khatian_no"] + [
                f"owners[{i}].{field}"
                for i in range(len(d.owners))
                for field in ("name", "share_text")
            ]
            paths += [f"plots[{i}].area_text" for i in range(len(d.plots))]
            events.append(
                _event(
                    doc,
                    "record",
                    record_year,
                    f"{label} ({d.survey_type} {to_bangla_digits(d.khatian_no)})",
                    "মালিকানা নথিভুক্ত",
                    [],
                    _owners(d.owners, "owners"),
                    d.total_area_text,
                    paths,
                )
            )
        elif doc.role in (CaseRole.prior_deed, CaseRole.proposed_deed):
            proposed = doc.role == CaseRole.proposed_deed
            date = d.registration_date or d.registration_date_text or d.deed_year
            kind = "proposed_sale" if proposed else "sale"
            title = "প্রস্তাবিত বিক্রয়" if proposed else "পূর্বের বিক্রয়"
            paths = ["deed_no"] + [
                f"{role}[{i}].name"
                for role, owners in (("sellers", d.sellers), ("buyers", d.buyers))
                for i in range(len(owners))
            ]
            paths += [f"schedule_plots[{i}].area_text" for i in range(len(d.schedule_plots))]
            events.append(
                _event(
                    doc,
                    kind,
                    _year(date),
                    title,
                    d.transferred_area_text,
                    _owners(d.sellers, "sellers"),
                    _owners(d.buyers, "buyers"),
                    d.transferred_area_text,
                    paths,
                )
            )
        elif doc.role == CaseRole.mutation:
            year = _year(d.order_date or d.order_date_text)
            paths = ["case_no", "new_khatian_no"] + [
                f"owners[{i}].{field}"
                for i in range(len(d.owners))
                for field in ("name", "share_text")
            ]
            events.append(
                _event(
                    doc,
                    "mutation",
                    year,
                    f"নামজারি ({to_bangla_digits(d.new_khatian_no)})",
                    d.basis_text or "নামজারি নথি",
                    [],
                    _owners(d.owners, "owners"),
                    d.total_area_text,
                    paths,
                )
            )
        elif doc.role == CaseRole.heir_cert:
            year = _year(d.date_of_death or d.date_of_death_text)
            share_owners = [o for m in case.mutations for o in m.data.owners]
            if not share_owners and case.current_khatian:
                share_owners = case.current_khatian.data.owners
            share_by_name = {match_key(o.name_normalized or o.name): o for o in share_owners}
            heirs = []
            for i, heir in enumerate(d.heirs):
                recorded = share_by_name.get(match_key(heir.name_normalized or heir.name))
                heirs.append(
                    {
                        "name": heir.name,
                        "relation": heir.relation_text,
                        "share_text": recorded.share_text if recorded else None,
                        "share_fraction": recorded.share_fraction if recorded else None,
                        "source_field": f"heirs[{i}].name",
                    }
                )
            paths = ["deceased_name", "date_of_death"] + [
                f"heirs[{i}].name" for i in range(len(d.heirs))
            ]
            death_date = d.date_of_death_text or (
                d.date_of_death.isoformat() if d.date_of_death else "তথ্য নেই"
            )
            events.append(
                _event(
                    doc,
                    "inheritance",
                    year,
                    f"ওয়ারিশ সনদ: {d.deceased_name}",
                    f"মৃত্যুর তারিখ: {death_date}",
                    [{"name": d.deceased_name, "share_text": None, "share_fraction": None}],
                    heirs,
                    None,
                    paths,
                )
            )

    findings = assessment.findings
    for event in events:
        sources = set(event["source_ids"])
        relevant = [f for f in findings if any(s.source_id in sources for s in f.sources)]
        event["finding_codes"] = list(dict.fromkeys(f.code for f in relevant if f.code))
        event["status"] = (
            "bad"
            if any(f.status.value == "bad" for f in relevant)
            else "warn"
            if relevant
            else "ok"
        )
    events.sort(key=lambda e: (0, e["_survey_rank"]) if e["year"] is None else (1, e["year"]))
    for event in events:
        event.pop("_survey_rank")
    years = [e["year"] for e in events if e["year"] is not None]
    dag = next(
        (
            p.dag_no
            for doc in case.documents
            for p in getattr(doc.data, "plots", getattr(doc.data, "schedule_plots", []))
        ),
        "",
    )
    span = max(years) - min(years) if len(years) > 1 else None
    title = (
        f"দাগ {to_bangla_digits(dag)}-এর {to_bangla_digits(str(span))} বছরের ইতিহাস"
        if dag and span
        else f"দাগ {to_bangla_digits(dag)}-এর জমির ইতিহাস"
        if dag
        else "জমির মালিকানার ইতিহাস"
    )
    return {"title_bn": title, "events": events}

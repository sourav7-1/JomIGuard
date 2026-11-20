"""Paper vs ground findings from a sentinel result (synthetic results, scenario khatians)."""

from pathlib import Path

import pytest
from scenario_loader import load_scenario

from app.services.risk import assess, forbidden_words_in
from app.services.rules import run_rules
from app.services.rules.base import Status
from app.services.satellite_findings import (
    GROUP,
    is_agricultural,
    is_orchard,
    land_classes,
    satellite_findings,
)

SCENARIOS = Path(__file__).parents[1] / "scenarios"
YEARS = list(range(2019, 2026))


def result(
    water=None,
    heavy=(),
    spikes=(),
    outliers=(),
    low=(),
    tree_persistent=False,
    tree_change=0.0,
    water_persistent=False,
    water_change=0.0,
):
    water = water or [0.2] * 7
    years = [
        {"year": y, "status": "ok", "low_confidence": y in low, "metrics": {"water_pct": w}}
        for y, w in zip(YEARS, water, strict=True)
    ]
    return {
        "buffer_m": 200.0,
        "years": years,
        "trends": {
            "tree_cover_pct": {
                "from": 40.0,
                "to": 40.0 + tree_change,
                "change": tree_change,
                "from_year": 2019,
                "to_year": 2025,
                "persistent_change": tree_persistent,
            },
            "water_pct": {
                "from": 30.1,
                "to": 30.1 + water_change,
                "change": water_change,
                "from_year": 2019,
                "to_year": 2025,
                "slope_per_year": water_change / 6,
                "persistent_change": water_persistent,
            },
        },
        "signals": {
            "water_heavy_years": list(heavy),
            "water_spike_years": list(spikes),
            "outlier_years": list(outliers),
            "low_confidence_years": list(low),
        },
    }


@pytest.fixture(scope="module")
def nal_case():
    case, _ = load_scenario(SCENARIOS / "01_demo_area_exceeds")
    return case


def with_land_class(case, land_class):
    case = case.model_copy(deep=True)
    for plot in case.current_khatian.data.plots:
        plot.land_class = land_class
    return case


def ids(findings):
    return [f.rule_id for f in findings]


def test_quiet_area_with_enough_years_gives_no_findings_and_no_pass(nal_case):
    findings = satellite_findings(result(), nal_case)
    assert findings == []  # nothing seen is not a pass: there is simply nothing to report


def test_water_heavy_year_warns_and_mismatches_cropland(nal_case):
    findings = satellite_findings(result(heavy=[2022], spikes=[2022]), nal_case)
    assert ids(findings) == [
        "satellite_water_dry_season",
        "satellite_water_spike",
        "satellite_class_water_mismatch",
    ]
    assert all(f.status == Status.warn for f in findings)
    assert "শুকনো মৌসুমেও আশেপাশে পানি" == findings[0].title_bn
    assert "২০২২" in findings[0].message_bn
    assert findings[2].values["land_class"] == "নাল"


def test_spike_alone_is_flood_or_waterlogging_warning(nal_case):
    findings = satellite_findings(result(spikes=[2021]), nal_case)
    assert ids(findings) == ["satellite_water_spike"]
    assert "বন্যা" in findings[0].message_bn and "২০২১" in findings[0].message_bn


def test_persistent_tree_drop_is_tree_loss(nal_case):
    findings = satellite_findings(result(tree_persistent=True, tree_change=-15.0), nal_case)
    assert ids(findings) == ["satellite_tree_loss"]
    assert "গাছ" in findings[0].title_bn


def test_tree_rise_or_non_persistent_drop_is_not_loss(nal_case):
    assert satellite_findings(result(tree_persistent=True, tree_change=12.0), nal_case) == []
    assert satellite_findings(result(tree_change=-15.0), nal_case) == []


def test_orchard_with_tree_drop_is_mismatch(nal_case):
    case = with_land_class(nal_case, "আম বাগান")
    findings = satellite_findings(result(tree_persistent=True, tree_change=-15.0), case)
    assert ids(findings) == ["satellite_tree_loss", "satellite_class_tree_mismatch"]
    assert findings[1].values["land_class"] == "আম বাগান"


def test_orchard_with_water_is_not_cropland_mismatch(nal_case):
    case = with_land_class(nal_case, "বাগান")
    assert "satellite_class_water_mismatch" not in ids(
        satellite_findings(result(heavy=[2020]), case)
    )


def test_few_good_years_is_insufficient_info_not_pass(nal_case):
    r = result(outliers=[2021], low=[2022, 2024, 2020], tree_persistent=True, tree_change=-20.0)
    findings = satellite_findings(r, nal_case)
    assert ids(findings) == ["satellite_insufficient_evidence"]  # tree loss needs enough years
    f = findings[0]
    assert f.status == Status.skipped and f.code is None
    assert f.skip_reason and "পাস নয়" in f.message_bn


def test_insufficient_still_reports_water(nal_case):
    r = result(heavy=[2022], low=[2019, 2020, 2021, 2023])
    assert ids(satellite_findings(r, nal_case))[0] == "satellite_water_dry_season"
    assert "satellite_insufficient_evidence" in ids(satellite_findings(r, nal_case))


@pytest.mark.parametrize(
    "land_class, agri, orchard",
    [
        ("নাল", True, False),
        ("নাল জমি", True, False),
        ("ধানী", True, False),
        ("ধানি", True, False),
        ("কৃষি", True, False),
        ("কৃষি জমি", True, False),
        ("ফসলি", True, False),
        ("নাল (দো-ফসলি)", True, False),
        ("নালা", False, False),  # a drain, not cropland
        ("বাগান", False, True),
        ("আম বাগান", False, True),
        ("আমবাগান", False, True),
        ("বাগিচা", False, True),
        ("বাড়ি", False, False),
        ("ভিটি", False, False),
        ("", False, False),
    ],
)
def test_land_class_variants(land_class, agri, orchard):
    assert is_agricultural(land_class) is agri
    assert is_orchard(land_class) is orchard


def test_land_classes_from_current_khatian(nal_case):
    assert land_classes(nal_case) == ["নাল"]


def test_every_finding_says_surroundings_has_next_action_and_no_forbidden_words(nal_case):
    case = with_land_class(nal_case, "নাল")
    everything = satellite_findings(
        result(
            heavy=[2022],
            spikes=[2022],
            tree_persistent=True,
            tree_change=-15.0,
            water_persistent=True,
            water_change=28.6,
        ),
        case,
    ) + satellite_findings(result(low=[2019, 2020, 2021, 2022]), case)
    orchard = satellite_findings(
        result(tree_persistent=True, tree_change=-15.0), with_land_class(nal_case, "বাগান")
    )
    everything += orchard
    assert {f.rule_id for f in everything} >= {
        "satellite_water_dry_season",
        "satellite_water_spike",
        "satellite_water_rising",
        "satellite_tree_loss",
        "satellite_class_water_mismatch",
        "satellite_class_tree_mismatch",
        "satellite_insufficient_evidence",
    }
    for f in everything:
        assert f.group == GROUP
        assert "২০০ মিটার" in f.message_bn and "সীমানার ভেতরের হিসাব নয়" in f.message_bn
        assert f.values["next_action_bn"] and f.values["scope"] == "surroundings"
        assert f.status != Status.passed
        text = f"{f.title_bn} {f.message_bn} {f.values['next_action_bn']}"
        assert forbidden_words_in(text) == []


def test_buffer_is_taken_from_the_result(nal_case):
    r = result(heavy=[2022])
    r["buffer_m"] = 350
    assert "৩৫০ মিটার" in satellite_findings(r, nal_case)[0].message_bn


def test_satellite_findings_do_not_change_rule_outcomes(nal_case):
    run = run_rules(nal_case)
    before = assess(nal_case, run)
    after = assess(nal_case, run)
    after.satellite_findings = satellite_findings(result(heavy=[2022]), nal_case)
    assert after.risk_level == before.risk_level
    assert after.findings == before.findings and after.summary_bn == before.summary_bn


def test_report_has_satellite_section_without_forbidden_words(nal_case):
    from datetime import UTC, datetime

    from app.services.report import render_report_html

    assessment = assess(nal_case, run_rules(nal_case))
    assessment.satellite_findings = satellite_findings(
        result(heavy=[2022], low=[2019, 2020, 2021, 2023]), nal_case
    )
    html = render_report_html(nal_case, assessment, datetime(2026, 11, 20, tzinfo=UTC))
    assert "স্যাটেলাইট যাচাই" in html and "শুকনো মৌসুমেও আশেপাশে পানি" in html
    assert "এরপর:" in html
    assert forbidden_words_in(html) == []


def test_persistent_water_rise_shows_values_slope_and_erosion_action(nal_case):
    r = result(heavy=YEARS, water_persistent=True, water_change=28.65)
    r["trends"]["water_pct"].update(to=58.75, slope_per_year=5.1)
    findings = satellite_findings(r, nal_case)
    assert ids(findings) == [
        "satellite_water_dry_season",
        "satellite_water_rising",
        "satellite_class_water_mismatch",
    ]
    f = findings[1]
    assert f.status == Status.warn and f.title_bn == "আশেপাশে পানি বছর বছর বাড়ছে"
    assert "৩০.১%" in f.message_bn and "৫৮.৮%" in f.message_bn and "৫.১" in f.message_bn
    assert "২০১৯" in f.message_bn and "২০২৫" in f.message_bn
    assert "নদীভাঙন" in f.message_bn and "২০০ মিটার" in f.message_bn
    action = f.values["next_action_bn"]
    assert "ইউনিয়ন পরিষদ" in action and "মৌজা ম্যাপ" in action and "আমিন" in action


def test_water_fall_or_non_persistent_rise_is_not_rising(nal_case):
    assert satellite_findings(result(water_persistent=True, water_change=-12.0), nal_case) == []
    assert satellite_findings(result(water_change=20.0), nal_case) == []


def test_water_rise_needs_enough_good_years(nal_case):
    r = result(low=[2019, 2020, 2021, 2022], water_persistent=True, water_change=20.0)
    assert ids(satellite_findings(r, nal_case)) == ["satellite_insufficient_evidence"]

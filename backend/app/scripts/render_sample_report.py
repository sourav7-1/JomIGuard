"""Render the sample report for scenario 01 (synthetic data, with the "নমুনা" watermark).

Usage (Docker): docker compose exec backend uv run python -m app.scripts.render_sample_report \
    --out /app/report-scenario-01.pdf
then move the file to docs/samples/ (/docs is mounted read-only in the container).
"""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
SCENARIO = BACKEND / "tests/scenarios/01_demo_area_exceeds"
DEFAULT_OUT = BACKEND.parent / "docs/samples/report-scenario-01.pdf"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    sys.path.insert(0, str(BACKEND / "tests"))  # scenario_loader is a test helper
    from scenario_loader import load_scenario

    from app.services.actions import next_actions
    from app.services.report import render_report_html, render_report_pdf
    from app.services.risk import assess
    from app.services.rules import run_rules

    case, _ = load_scenario(SCENARIO)
    run = run_rules(case)
    assessment = assess(case, run)
    assessment.actions = next_actions(case, run, assessment)
    html = render_report_html(case, assessment, datetime.now(UTC), sample=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(render_report_pdf(html))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()

"""Judge demo packs: five small synthetic document sets, watermarked "নমুনা / SAMPLE".

    PYTHONPATH=../backend uv run python -m synth.demo_packs --out ../backend/app/scripts/demo_data/packs

Each pack folder holds PNG pages and pack.json (location for the new case and the doc type of
every file). The expected result shown in the app is recorded separately, by uploading the pack
through the app (see frontend/src/lib/demo-packs.ts).
"""

import argparse
import json
from pathlib import Path

from synth.common import Renderer
from synth.deed import Case, generate_cases

WATERMARK_JS = """
() => {
  const w = document.createElement('div');
  w.style.cssText = 'position:absolute;inset:0;overflow:hidden;pointer-events:none;z-index:9999';
  const h = document.documentElement.scrollHeight;
  w.style.height = h + 'px';
  for (let y = 60; y < h; y += 260) for (let x = -80; x < 1200; x += 420) {
    const s = document.createElement('span');
    s.textContent = 'নমুনা / SAMPLE';
    s.style.cssText = `position:absolute;left:${x}px;top:${y}px;transform:rotate(-24deg);font-size:46px;` +
      'font-weight:700;color:rgba(170,30,30,.16);white-space:nowrap;font-family:Synth';
    w.appendChild(s);
  }
  document.body.style.position = 'relative';
  document.body.appendChild(w);
}
"""

# Handwritten style: slanted ink-blue text, each line slightly tilted and shifted.
HANDWRITTEN_JS = """
() => {
  document.body.style.color = '#1f2f78';
  document.body.style.fontStyle = 'italic';
  let i = 0;
  for (const el of document.querySelectorAll('p, td, li, h1, h2, h3, div > span')) {
    i += 1;
    const r = Math.sin(i * 12.9898) * 43758.5453; const f = r - Math.floor(r);
    el.style.display = el.tagName === 'SPAN' ? 'inline-block' : el.style.display;
    el.style.transform = `rotate(${(f - 0.5) * 1.6}deg) translateX(${(f - 0.5) * 6}px)`;
  }
}
"""


class PackRenderer(Renderer):
    def render(self, template, font, context, path, handwritten=False):
        from synth.common import _TEMPLATES, font_faces

        html = _TEMPLATES.get_template(template).render(font_faces=font_faces(font), **context)
        self._page.set_content(html)
        self._page.evaluate("Promise.all([...document.fonts].map(f => f.load())).then(() => true)")
        if handwritten:
            self._page.evaluate(HANDWRITTEN_JS)
        self._page.evaluate(WATERMARK_JS)
        self._page.screenshot(path=path, full_page=True)


SCENARIOS = {
    "A": ("all_match", lambda c: not c.mismatches and not c.family),
    "B": ("area_exceeds_share", lambda c: c.mismatches and c.mismatches[0]["type"] == "area_exceeds_share" and not c.family),
    "C": ("dag_mismatch", lambda c: c.mismatches and c.mismatches[0]["type"] == "dag_mismatch" and not c.family),
    "D": ("heir_missing", lambda c: not c.mismatches and c.family and len(c.mutation.owners) >= 3),
    "E": ("handwritten_deed", lambda c: not c.mismatches and not c.family),
}


def drop_last_owner(c: Case) -> str:
    """Scenario D: the mutation forgets one heir (data and printed copy)."""
    dropped = c.mutation_printed["owners"][-1]
    c.mutation_printed = {**c.mutation_printed, "owners": c.mutation_printed["owners"][:-1]}
    c.mutation = c.mutation.model_copy(update={"owners": c.mutation.owners[:-1]})
    return str(dropped.get("name") or dropped)


def pick(cases: list[Case]) -> dict[str, Case]:
    chosen: dict[str, Case] = {}
    for key, (_, match) in SCENARIOS.items():
        chosen[key] = next(c for c in cases if c not in chosen.values() and match(c))
    return chosen


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    cases = generate_cases(300, args.seed, 0.7)
    chosen = pick(cases)
    with PackRenderer() as r:
        for key, c in chosen.items():
            name, _ = SCENARIOS[key]
            d = args.out / key
            d.mkdir(parents=True, exist_ok=True)
            for old in d.glob("*.png"):
                old.unlink()
            note = drop_last_owner(c) if key == "D" else None
            files = [("1-khatian.png", "khatian", "khatian.html", c.khatian_font, c.khatian_printed),
                     ("2-deed.png", "deed", "deed.html", c.deed_font, c.deed_printed),
                     ("3-mutation.png", "dcr", "mutation.html", c.mutation_font, c.mutation_printed)]
            if c.heir_cert:
                files.append(("4-heir-certificate.png", "heir_cert", "heir_cert.html", c.heir_cert_font, c.heir_cert_printed))
            for fname, _, template, font, printed in files:
                r.render(template, font, printed, d / fname, handwritten=(key == "E" and fname == "2-deed.png"))
            loc = c.khatian.location
            pack = {
                "id": key, "scenario": name, "seed": c.seed,
                "land": {"district": loc.district, "upazila": loc.upazila, "mouza": loc.mouza,
                         "dag_no": c.khatian.plots[0].dag_no, "khatian_no": c.khatian.khatian_no},
                "files": [{"name": f, "doc_type": t} for f, t, *_ in files],
                "mismatch": c.mismatches[0] if c.mismatches else None,
                "dropped_heir": note,
            }
            (d / "pack.json").write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
            print(key, name, [f for f, *_ in files])


if __name__ == "__main__":
    main()

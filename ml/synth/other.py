"""Synthetic "other" pages (not land documents) for the document-type classifier.

Usage (from ml/):
    uv run python -m synth.other --n 20 --seed 45 --out ../data/other
Renders n clean pages (kinds cycle: blank, Bangla shopping list or notice, English letter,
table of numbers) with the dataset fonts, plus one augmented copy of each (same presets as
synth.augment): 2n images. Writes {id}.png and manifest.csv (output, source_id, kind, preset,
seed). Kept outside dataset v2. All text is invented; no real names or numbers.
"""

import argparse
import csv
import html
import random
from pathlib import Path

from synth.augment import PRESET_WEIGHTS, augment_image, derive_seed, read_rgb, write_rgb
from synth.common import WIDTH, Renderer, choose_font, font_faces, item_seeds, to_bn

KINDS = ("blank", "bangla_text", "english_letter", "number_table")
FOOTER = "নমুনা / SAMPLE কৃত্রিম তথ্য"

ITEMS = ["চাল", "ডাল", "সয়াবিন তেল", "পেঁয়াজ", "আলু", "লবণ", "চিনি", "ডিম", "আটা", "রসুন", "আদা", "মরিচ"]
UNITS = ["কেজি", "লিটার", "হালি", "প্যাকেট", "গ্রাম"]
NOTICE_LINES = [
    "আগামী শুক্রবার বিকাল চারটায় পাঠাগারের বার্ষিক সভা অনুষ্ঠিত হইবে।",
    "সকল সদস্যকে যথাসময়ে উপস্থিত থাকিবার জন্য অনুরোধ করা যাইতেছে।",
    "সভায় নতুন বই কেনা ও পাঠকক্ষ সংস্কার নিয়ে আলোচনা হইবে।",
    "বৃষ্টির কারণে খেলার মাঠের অনুশীলন আগামী সপ্তাহে স্থগিত থাকিবে।",
    "বিদ্যালয়ের বিজ্ঞান মেলায় অংশগ্রহণের শেষ সময় মাসের শেষ দিন।",
    "পরিচ্ছন্নতা অভিযানে আগ্রহী স্বেচ্ছাসেবকগণ অফিসে নাম লিখাইবেন।",
]
LETTER_LINES = [
    "Thank you for your letter about the community garden project.",
    "The committee met last week and agreed to extend the opening hours.",
    "Volunteers are welcome every Saturday morning from nine to twelve.",
    "Please bring gloves and a water bottle; tools will be provided.",
    "We will share the new schedule on the notice board next month.",
    "If you have questions, reply to this letter or visit the office.",
]
NAMES_EN = ["A. Rahman", "S. Akter", "M. Hossain", "R. Karim", "T. Begum"]


def page(font: str, body: str) -> str:
    faces = "".join(
        f'@font-face {{ font-family: "Synth"; src: url("{f["uri"]}"); '
        f"font-weight: {f['weight']}; }}"
        for f in font_faces(font)
    )
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{faces}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: #fff; color: #111; font-family: "Synth"; font-size: 20px;
         line-height: 1.7; }}
  .page {{ width: {WIDTH}px; min-height: 1600px; padding: 56px 80px 32px; position: relative; }}
  h1 {{ text-align: center; font-size: 28px; }}
  table {{ border-collapse: collapse; margin: 16px auto; }}
  td, th {{ border: 1px solid #222; padding: 6px 14px; text-align: right; }}
  .foot {{ position: absolute; bottom: 24px; left: 80px; font-size: 16px; color: #444; }}
</style></head><body><div class="page">{body}<div class="foot">{FOOTER}</div></div></body></html>"""


def body(kind: str, rng: random.Random) -> str:
    e = html.escape
    if kind == "blank":
        return ""
    if kind == "bangla_text":
        if rng.random() < 0.5:
            rows = "".join(
                f"<tr><td>{to_bn(str(i))}</td><td style='text-align:left'>{e(item)}</td>"
                f"<td>{to_bn(str(rng.randint(1, 5)))} {e(rng.choice(UNITS))}</td>"
                f"<td>{to_bn(str(rng.randint(2, 40) * 10))} টাকা</td></tr>"
                for i, item in enumerate(rng.sample(ITEMS, rng.randint(5, 9)), 1)
            )
            return f"<h1>বাজারের তালিকা</h1><table>{rows}</table>"
        lines = "".join(f"<p>{e(x)}</p>" for x in rng.sample(NOTICE_LINES, 4))
        return f"<h1>বিজ্ঞপ্তি</h1>{lines}<p>সম্পাদক, পাঠাগার কমিটি</p>"
    if kind == "english_letter":
        lines = "".join(f"<p>{e(x)}</p>" for x in rng.sample(LETTER_LINES, 4))
        return (
            f"<p>Dear {e(rng.choice(NAMES_EN))},</p>{lines}"
            f"<p>Sincerely,<br>{e(rng.choice(NAMES_EN))}<br>Garden Committee</p>"
        )
    cols = rng.randint(4, 6)
    head = "".join(f"<th>{c}</th>" for c in "ABCDEF"[:cols])
    rows = "".join(
        "<tr>" + "".join(f"<td>{rng.randint(0, 99999)}</td>" for _ in range(cols)) + "</tr>"
        for _ in range(rng.randint(10, 18))
    )
    return f"<table><tr>{head}</tr>{rows}</table>"


def generate(n: int, seed: int, out: Path) -> list[dict]:
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    with Renderer() as r:
        for i, item_seed in enumerate(item_seeds(seed, n), 1):
            rng = random.Random(item_seed)
            kind = KINDS[(i - 1) % len(KINDS)]
            source_id = f"other_{i:05d}"
            clean_png = out / f"{source_id}.png"
            # same Chromium page as synth.common.Renderer, with inline HTML instead of a template
            r._page.set_content(page(choose_font(rng), body(kind, rng)))
            r._page.evaluate("Promise.all([...document.fonts].map(f => f.load())).then(() => 1)")
            r._page.screenshot(path=clean_png, full_page=True)
            rows.append(
                {"output": clean_png.name, "source_id": source_id, "kind": kind,
                 "preset": "clean", "seed": item_seed}
            )  # fmt: skip
            img_seed = derive_seed(seed, source_id, "other", 0)
            preset = random.Random(img_seed).choices(
                list(PRESET_WEIGHTS), weights=list(PRESET_WEIGHTS.values())
            )[0]
            photo, _ = augment_image(read_rgb(clean_png), preset, img_seed)
            write_rgb(out / f"{source_id}_0.png", photo)
            rows.append(
                {"output": f"{source_id}_0.png", "source_id": source_id, "kind": kind,
                 "preset": preset, "seed": img_seed}
            )  # fmt: skip
    with (out / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=20, help="clean pages; 2n images in total")
    ap.add_argument("--seed", type=int, default=45)
    ap.add_argument("--out", type=Path, default=Path("../data/other"))
    a = ap.parse_args()
    rows = generate(a.n, a.seed, a.out)
    print(f"wrote {len(rows)} images to {a.out}")


if __name__ == "__main__":
    main()

"""Shared helpers for the synthetic document generators."""

import base64
import json
import random
from collections.abc import Iterator
from decimal import Decimal
from functools import cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
WIDTH = 1240

# family -> [(file under fonts/, css font-weight)]; each folder carries its OFL.txt
FONTS = {
    "Hind Siliguri": [
        ("hindsiliguri/HindSiliguri-Regular.ttf", "400"),
        ("hindsiliguri/HindSiliguri-Bold.ttf", "700"),
    ],
    "Noto Sans Bengali": [("notosansbengali/NotoSansBengali.ttf", "100 900")],
    "Noto Serif Bengali": [("notoserifbengali/NotoSerifBengali.ttf", "100 900")],
    "Tiro Bangla": [("tirobangla/TiroBangla-Regular.ttf", "400")],
}

_TO_BN = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
_TO_ASCII = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def to_bn(s: str) -> str:
    return s.translate(_TO_BN)


def to_ascii(s: str) -> str:
    return s.translate(_TO_ASCII)


def load(name: str) -> dict:
    return json.loads((HERE / "data" / name).read_text(encoding="utf-8"))


NAMES = load("names.json")
PLACES = load("places.json")


def item_seeds(seed: int, n: int) -> Iterator[int]:
    """Per-item seeds from one master seed; each item gets its own Random(item_seed)."""
    master = random.Random(seed)
    for _ in range(n):
        yield master.getrandbits(32)


def choose_font(rng: random.Random) -> str:
    return rng.choice(sorted(FONTS))


def acres_text(acres: Decimal) -> str:
    s = f"{acres:.4f}"
    return to_bn(s[1:] if s.startswith("0.") else s)  # ".১৫০০" style


def is_female(name_normalized: str) -> bool:
    return name_normalized.split()[-1] in NAMES["female_last"]


def person(rng: random.Random) -> tuple[str, str, str, str]:
    """-> (printed name, name_normalized, father_or_husband_name, relation_marker)."""
    female = rng.random() < 0.35
    sex = "female" if female else "male"
    plain = f"{rng.choice(NAMES[f'{sex}_first'])} {rng.choice(NAMES[f'{sex}_last'])}"
    name = f"{rng.choice(NAMES[f'{sex}_honorifics'])} {plain}" if rng.random() < 0.6 else plain
    marker = "husband" if female and rng.random() < 0.5 else "father"
    guardian = f"{rng.choice(NAMES['male_first'])} {rng.choice(NAMES['male_last'])}"
    return name, plain, guardian, marker


# --- rendering ---


@cache
def font_faces(family: str) -> list[dict]:
    return [
        {
            "uri": "data:font/ttf;base64,"
            + base64.b64encode((HERE / "fonts" / f).read_bytes()).decode(),
            "weight": weight,
        }
        for f, weight in FONTS[family]
    ]


_TEMPLATES = Environment(
    loader=FileSystemLoader(HERE / "templates"), autoescape=select_autoescape(["html"])
)


class Renderer:
    """One Chromium page reused for every render: `with Renderer() as r: r.render(...)`."""

    def __enter__(self):
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch()
        self._page = self._browser.new_page(viewport={"width": WIDTH, "height": 800})
        return self

    def __exit__(self, *exc):
        self._browser.close()
        self._pw.stop()

    def render(self, template: str, font: str, context: dict, path: Path) -> None:
        html = _TEMPLATES.get_template(template).render(font_faces=font_faces(font), **context)
        self._page.set_content(html)
        # load every face; rejects (raises) if a font fails instead of silently falling back
        self._page.evaluate("Promise.all([...document.fonts].map(f => f.load())).then(() => true)")
        self._page.screenshot(path=path, full_page=True)

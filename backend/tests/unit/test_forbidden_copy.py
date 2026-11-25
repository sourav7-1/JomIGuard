"""No user-facing backend string says land is safe (CLAUDE.md hard rule). Every string literal in
app/ (code, templates, prompts) is scanned; only the FORBIDDEN_WORDS list itself may hold the
words, because the checks need them."""

import ast
from pathlib import Path

from app.services.rules.messages import FORBIDDEN_WORDS

APP = Path(__file__).parents[2] / "app"
BANNED = "নিরাপদ"


def _forbidden_list_lines(tree: ast.AST) -> set[int]:
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "FORBIDDEN_WORDS" for t in node.targets
        ):
            lines.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    return lines


def test_no_banned_word_in_any_backend_string():
    hits = []
    for path in APP.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        allowed = _forbidden_list_lines(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if BANNED in node.value and node.lineno not in allowed:
                    hits.append(f"{path.relative_to(APP)}:{node.lineno}")
    for path in [*APP.rglob("*.html"), *APP.rglob("*.j2"), *APP.rglob("*.md"), *APP.rglob("*.txt")]:
        if BANNED in path.read_text(encoding="utf-8"):
            hits.append(str(path.relative_to(APP)))
    assert hits == [], f"'{BANNED}' in user-facing text: {hits}"
    assert BANNED in FORBIDDEN_WORDS  # the runtime check still knows the word

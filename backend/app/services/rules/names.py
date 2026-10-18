"""Matching people's names across documents, token by token (pure functions).

Never a single whole-string fuzzy score: "রহিম উদ্দিন" and "করিম উদ্দিন" share 9 of 11 characters
and would look "similar", yet they are different people (brothers in the demo family).
"""

from rapidfuzz import fuzz

from app.services.normalize import clean, normalize_name

# Each token: one spelling or OCR slip in a typical 4-7 letter Bangla name part (e.g. "উদ্দিন" vs
# "উদ্দিন্") stays at or above 85; two different words almost never do.
TOKEN_MIN = 85
# The first token is the given name and tells people apart within a family: stricter.
# "রহিম" vs "করিম" scores 75, "রহিম" vs "রহীম" (after folding) 100.
FIRST_TOKEN_MIN = 90
# Names may differ by one token, and only in the middle ("মোহাম্মদ আব্দুল করিম" vs
# "মোহাম্মদ করিম"). A missing first or last token is not allowed: "রহিম" alone could be anyone.
MAX_TOKEN_DIFF = 1

# long/short vowel signs are used interchangeably in names: fold to the short form
_FOLD = str.maketrans({"ী": "ি", "ূ": "ু"})


def match_key(name: str | None) -> str:
    """name_normalized -> comparison key: NFC, no zero-width characters, ী→ি, ূ→ু, single spaces."""
    return " ".join(clean(name or "").translate(_FOLD).replace("য়", "য").replace("য়", "য").split())


def _ratio(a: str, b: str) -> float:
    return fuzz.ratio(a, b)


def _pairwise(short: list[str], long: list[str]) -> list[float] | None:
    """Ratios of aligned tokens, or None if any is below its threshold."""
    ratios = [_ratio(a, b) for a, b in zip(short, long, strict=True)]
    if ratios[0] < FIRST_TOKEN_MIN or any(r < TOKEN_MIN for r in ratios):
        return None
    return ratios


def names_match(a: str | None, b: str | None) -> tuple[bool, float, str]:
    """-> (match, score 0-100, reason). Inputs are name_normalized values."""
    ta, tb = match_key(a).split(), match_key(b).split()
    if not ta or not tb:
        return False, 0.0, "empty name"
    if abs(len(ta) - len(tb)) > MAX_TOKEN_DIFF:
        return False, 0.0, f"token counts differ: {len(ta)} vs {len(tb)}"
    short, long = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    if len(short) == len(long):
        candidates = [long]
    elif len(short) < 2:
        return False, 0.0, "one-token name against a longer name"
    else:  # drop one middle token of the longer name
        candidates = [long[:i] + long[i + 1 :] for i in range(1, len(long) - 1)]
    best = None
    for cand in candidates:
        ratios = _pairwise(short, cand)
        if ratios and (best is None or sum(ratios) > sum(best)):
            best = ratios
    if best is None:
        first = _ratio(short[0], long[0])
        if first < FIRST_TOKEN_MIN:
            return False, first, f"first name differs ({first:.0f} < {FIRST_TOKEN_MIN})"
        return False, 0.0, "a name part differs"
    score = round(sum(best) / len(best), 1)
    reason = "same tokens" if len(short) == len(long) else "one middle token missing"
    return True, score, reason


def person_key(name: str | None) -> str:
    """Printed name (with honorifics) -> match key; for fields without a normalized copy."""
    return match_key(normalize_name(name or ""))

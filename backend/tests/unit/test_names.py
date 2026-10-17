import pytest
from rapidfuzz import fuzz

from app.services.rules.names import FIRST_TOKEN_MIN, match_key, names_match, person_key


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("রহিম উদ্দিন", "রহিম উদ্দীন"),  # ী / ি
        ("আব্দুল করিম", "আব্দুল করীম"),
        ("মোহাম্মদ আব্দুল করিম", "মোহাম্মদ করিম"),  # missing middle name
        ("সালমা খাতুন", "সালমা  খাতুন"),  # spacing
        ("রহিম উদ্দিন", "রহিম উ‌দ্দিন"),  # zero-width non-joiner
        ("আবুল কালাম আজাদ", "আবুল কালাম আজাদ"),
    ],
)
def test_same_person(a, b):
    ok, score, reason = names_match(a, b)
    assert ok, reason
    assert 85 <= score <= 100
    assert names_match(b, a)[0]  # symmetric


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("রহিম উদ্দিন", "করিম উদ্দিন"),  # brothers: first names differ by one letter
        ("সালমা খাতুন", "সালমা বেগম"),  # last name differs
        ("রহিম", "রহিম উদ্দিন"),  # a missing first or last token is not allowed
        ("রহিম উদ্দিন", "উদ্দিন রহিম"),  # order matters
        ("আবুল কালাম আজাদ খান", "আবুল খান"),  # two tokens missing
        ("জলিল", "রহিম উদ্দিন"),
    ],
)
def test_different_people(a, b):
    ok, _, reason = names_match(a, b)
    assert not ok and reason


@pytest.mark.parametrize(("a", "b"), [("", "রহিম"), ("রহিম", None), (None, None), ("  ", "  ")])
def test_empty_names_never_match(a, b):
    assert names_match(a, b) == (False, 0.0, "empty name")


def test_whole_string_similarity_would_have_matched_brothers():
    # why names_match goes token by token
    assert fuzz.ratio("রহিম উদ্দিন", "করিম উদ্দিন") > 80
    assert fuzz.ratio("রহিম", "করিম") < FIRST_TOKEN_MIN


def test_match_key_and_person_key():
    assert match_key(" রহীম  উদ্দীন ") == "রহিম উদ্দিন"
    assert match_key("আবু‌ল") == "আবুল"
    assert person_key("মোঃ রহিম উদ্দীন") == "রহিম উদ্দিন"

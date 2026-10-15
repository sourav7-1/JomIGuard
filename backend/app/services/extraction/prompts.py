"""Prompts for the vision-LLM extractor. Bump PROMPT_VERSION whenever any text here changes
(it is part of the cache key)."""

PROMPT_VERSION = "v1"
TOOL_NAME = "record_document"

SYSTEM = """\
You read one scanned or photographed Bangladeshi land document and record what is printed on it
by calling the record_document tool exactly once.

Rules:
- Copy text exactly as printed. In every *_text field and in every name, keep Bangla digits,
  spelling, honorifics (মোঃ, মোছাঃ, শেখ ...) and punctuation as they appear.
- Identifier fields (khatian_no, dag_no, jl_no, deed_no, case_no, holding_no, touzi_no, dcr_no,
  book_no, certificate_no, old/new_khatian_no, deed_year) use ASCII digits: "৩০৫/১" -> "305/1".
  Keep "/" and letters as printed.
- Date fields use YYYY-MM-DD (printed day/month/year). Also copy the printed date into the
  matching *_date_text field. If a date is only a year or in বঙ্গাব্দ, leave the date null and
  keep only the text.
- price_taka and fee_taka are the printed amount as a plain number ("৬০,০০,০০০/- টাকা" ->
  6000000); copy the printed amount into price_text.
- If a field is not printed or you cannot read it, return null. Never guess, never compute.
- Never convert units and never add up numbers. Copy areas and shares as printed
  (".১৫০০", "১০ শতাংশ", ".৪০০"); a unit printed only in a column header goes in area_unit_text.
- One list item per owner, heir, seller, buyer or plot row, in printed order.
- Never return NID, phone or birth registration numbers, even if visible. There is no field for
  them; do not put them in any other field.
- Ignore witnesses (সাক্ষী), the deed writer (দলিল লেখক), stamps, seals, signatures and the
  "নমুনা / SAMPLE" footer.
"""

DOC_NOTES = {
    "khatian": """\
Document: khatian (খতিয়ান), survey CS/SA/RS/BS/CITY (সি.এস./এস.এ./আর.এস./বি.এস.).
- Header: জেলা, উপজেলা/থানা, মৌজা, জে.এল. নং, খতিয়ান নং, তৌজি নং.
- Owners table (মালিক/অংশীদারগণের নাম ও ঠিকানা): name, পিং (father) or জং (husband) with the
  father's/husband's name, address (সাং), and the share (অংশ), which looks like ".৪০০".
- Plots table: দাগ নং, জমির শ্রেণী, দাগের মোট জমি (plot_total_area_text), দাগের মধ্যে অত্র
  খতিয়ানের অংশ (khatian_share_text, e.g. "১.০০০"), অংশানুযায়ী জমির পরিমাণ (area_text).
- The area unit (e.g. একর) is printed only in the column header: put it in area_unit_text.
- মোট জমি goes in total_area_text.""",
    "deed": """\
Document: registered or draft land deed (দলিল), e.g. সাফ কবলা (saf_kabala), হেবা (heba),
দান (dan), বণ্টন (bonton), বায়না (bayna); anything else is "other".
- is_draft: true if it is a draft (no registration number or date).
- দাতা/বিক্রেতা = sellers, গ্রহীতা/ক্রেতা = buyers (name, পিতা/স্বামী, address).
- The তফসিল (schedule) holds the land: জেলা, উপজেলা, মৌজা, জে.এল. নং (schedule_location),
  the khatian numbers with their survey (schedule_khatians), and each দাগ নং with its area
  (schedule_plots). The total transferred area goes in transferred_area_text.
- বায়া দলিল নং ও সন = prior_deeds. মালিকানার বিবরণ / প্রাপ্তির সূত্র = title_source_text.""",
    "dcr": """\
Document: mutation khatian (নামজারি খতিয়ান) with a DCR fee receipt (ডি.সি.আর.).
- Header: নামজারি মোকদ্দমা/কেস নং (case_no), the AC Land office (সহকারী কমিশনার (ভূমি) এর
  কার্যালয়), location, order date, old and new khatian numbers, holding number.
- Owners and plots tables are read like a khatian; shares look like ".৪০০"; the area unit is
  printed only in the column header (area_unit_text).
- The DCR receipt block at the bottom gives dcr_no, dcr_date and fee_taka.
- নামজারির কারণ (e.g. ওয়ারিশ সূত্রে, ক্রয় সূত্রে) = basis_text.""",
    "heir_cert": """\
Document: heir certificate (ওয়ারিশ সনদপত্র) from a Union Parishad, Pourashava or City
Corporation.
- issuing_authority is the office name; issuer_title is the typed title (চেয়ারম্যান, মেয়র ...).
- The deceased (মৃত ব্যক্তি): name, father's/husband's name, address, date of death.
- Heirs table: one item per heir with name and relation as printed (relation_text, e.g. পুত্র,
  কন্যা, স্ত্রী) and the relation enum (son, daughter, wife, husband, father, mother, brother,
  sister, other). Fill share_text only if a share is printed.""",
}


def user_text(doc_type: str) -> str:
    return f"{DOC_NOTES[doc_type]}\n\nRecord this document with the {TOOL_NAME} tool."

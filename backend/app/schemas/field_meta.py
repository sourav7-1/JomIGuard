"""Field metadata for extracted document types. Spec: docs/specs/fields.md."""

import types
from typing import Literal, Union, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field

FieldKind = Literal["identifier", "name", "number_text", "date_text", "enum", "text", "list"]
FilledBy = Literal["extractor", "normalize"]


class EnumOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str
    label_bn: str


class FieldMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    label_bn: str
    kind: FieldKind
    filled_by: FilledBy
    editable: bool
    enum_options: list[EnumOption] | None = None


class FieldsMetaResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    khatian: list[FieldMeta] = Field(default_factory=list)
    deed: list[FieldMeta] = Field(default_factory=list)
    dcr: list[FieldMeta] = Field(default_factory=list)
    heir_cert: list[FieldMeta] = Field(default_factory=list)


SURVEY_OPTIONS = [
    EnumOption(value="CS", label_bn="সি.এস."),
    EnumOption(value="SA", label_bn="এস.এ."),
    EnumOption(value="RS", label_bn="আর.এস."),
    EnumOption(value="BS", label_bn="বি.এস."),
    EnumOption(value="CITY", label_bn="সিটি জরিপ"),
]

DEED_TYPE_OPTIONS = [
    EnumOption(value="saf_kabala", label_bn="সাফ কবলা"),
    EnumOption(value="heba", label_bn="হেবা"),
    EnumOption(value="dan", label_bn="দান"),
    EnumOption(value="bonton", label_bn="বণ্টননামা"),
    EnumOption(value="bayna", label_bn="বায়না"),
    EnumOption(value="other", label_bn="অন্যান্য"),
]

RELATION_MARKER_OPTIONS = [
    EnumOption(value="father", label_bn="পিং (পিতা)"),
    EnumOption(value="husband", label_bn="জং (স্বামী)"),
    EnumOption(value="unknown", label_bn="অজানা"),
]

RELATION_OPTIONS = [
    EnumOption(value="son", label_bn="পুত্র"),
    EnumOption(value="daughter", label_bn="কন্যা"),
    EnumOption(value="wife", label_bn="স্ত্রী"),
    EnumOption(value="husband", label_bn="স্বামী"),
    EnumOption(value="father", label_bn="পিতা"),
    EnumOption(value="mother", label_bn="মাতা"),
    EnumOption(value="brother", label_bn="ভাই"),
    EnumOption(value="sister", label_bn="বোন"),
    EnumOption(value="other", label_bn="অন্যান্য"),
]

BOOL_OPTIONS = [
    EnumOption(value="true", label_bn="হ্যাঁ"),
    EnumOption(value="false", label_bn="না"),
]


KHATIAN_FIELDS: list[FieldMeta] = [
    FieldMeta(
        path="doc_type", label_bn="কাগজের ধরন", kind="text", filled_by="extractor", editable=False
    ),
    FieldMeta(
        path="survey_type",
        label_bn="জরিপ (সি.এস. / এস.এ. / আর.এস. / বি.এস.)",
        kind="enum",
        filled_by="extractor",
        editable=True,
        enum_options=SURVEY_OPTIONS,
    ),
    FieldMeta(
        path="location.district", label_bn="জেলা", kind="text", filled_by="extractor", editable=True
    ),
    FieldMeta(
        path="location.upazila",
        label_bn="উপজেলা / থানা",
        kind="text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="location.mouza", label_bn="মৌজা", kind="text", filled_by="extractor", editable=True
    ),
    FieldMeta(
        path="location.jl_no",
        label_bn="জে.এল. নং",
        kind="identifier",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="khatian_no",
        label_bn="খতিয়ান নং",
        kind="identifier",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="touzi_no",
        label_bn="তৌজি নং / রেভিনিউ নং",
        kind="identifier",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="owners",
        label_bn="মালিক / অংশীদারগণের নাম ও ঠিকানা",
        kind="list",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="owners[].name",
        label_bn="মালিকের নাম / নাম",
        kind="name",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="owners[].name_normalized",
        label_bn="স্বাভাবিক নাম",
        kind="name",
        filled_by="normalize",
        editable=False,
    ),
    FieldMeta(
        path="owners[].father_or_husband_name",
        label_bn="পিতা / স্বামী",
        kind="name",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="owners[].relation_marker",
        label_bn="পিং / জং (পিতা বা স্বামী)",
        kind="enum",
        filled_by="extractor",
        editable=True,
        enum_options=RELATION_MARKER_OPTIONS,
    ),
    FieldMeta(
        path="owners[].address_text",
        label_bn="ঠিকানা / সাং",
        kind="text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="owners[].share_text",
        label_bn="অংশ",
        kind="number_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="owners[].share_fraction",
        label_bn="অংশ (ভগ্নাংশ)",
        kind="number_text",
        filled_by="normalize",
        editable=False,
    ),
    FieldMeta(
        path="owners[].share_shatangsho",
        label_bn="অংশের জমি (শতাংশ)",
        kind="number_text",
        filled_by="normalize",
        editable=False,
    ),
    FieldMeta(
        path="plots",
        label_bn="দাগ নং ও জমির বিবরণ",
        kind="list",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="plots[].dag_no",
        label_bn="দাগ নং",
        kind="identifier",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="plots[].land_class",
        label_bn="জমির শ্রেণী",
        kind="text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="plots[].plot_total_area_text",
        label_bn="দাগের মোট জমি",
        kind="number_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="plots[].plot_total_area_shatangsho",
        label_bn="দাগের মোট জমি (শতাংশ)",
        kind="number_text",
        filled_by="normalize",
        editable=False,
    ),
    FieldMeta(
        path="plots[].khatian_share_text",
        label_bn="দাগের মধ্যে অত্র খতিয়ানের অংশ",
        kind="number_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="plots[].khatian_share_fraction",
        label_bn="খতিয়ানের অংশের ভগ্নাংশ",
        kind="number_text",
        filled_by="normalize",
        editable=False,
    ),
    FieldMeta(
        path="plots[].area_text",
        label_bn="অংশানুযায়ী জমির পরিমাণ / জমির পরিমাণ",
        kind="number_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="plots[].area_shatangsho",
        label_bn="জমির পরিমাণ (শতাংশ)",
        kind="number_text",
        filled_by="normalize",
        editable=False,
    ),
    FieldMeta(
        path="area_unit_text",
        label_bn="জমির পরিমাণের একক",
        kind="text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="total_area_text",
        label_bn="মোট জমি",
        kind="number_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="total_area_shatangsho",
        label_bn="মোট জমি (শতাংশ)",
        kind="number_text",
        filled_by="normalize",
        editable=False,
    ),
    FieldMeta(
        path="annual_revenue_text",
        label_bn="বার্ষিক খাজনা / রাজস্ব",
        kind="number_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="landlord_name",
        label_bn="জমিদার / ভূস্বামী (CS only)",
        kind="name",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="mutation_case_ref",
        label_bn="নামজারি / জমাভাগ কেস নং",
        kind="identifier",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="record_date",
        label_bn="প্রস্তুতের / চূড়ান্ত প্রকাশের তারিখ",
        kind="date_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="record_date_text",
        label_bn="প্রস্তুতের তারিখ (মূল লেখা)",
        kind="date_text",
        filled_by="extractor",
        editable=True,
    ),
]

DEED_FIELDS: list[FieldMeta] = [
    FieldMeta(
        path="doc_type", label_bn="কাগজের ধরন", kind="text", filled_by="extractor", editable=False
    ),
    FieldMeta(
        path="deed_type",
        label_bn="দলিলের প্রকৃতি",
        kind="enum",
        filled_by="extractor",
        editable=True,
        enum_options=DEED_TYPE_OPTIONS,
    ),
    FieldMeta(
        path="is_draft",
        label_bn="খসড়া দলিল",
        kind="enum",
        filled_by="extractor",
        editable=True,
        enum_options=BOOL_OPTIONS,
    ),
    FieldMeta(
        path="deed_no", label_bn="দলিল নং", kind="identifier", filled_by="extractor", editable=True
    ),
    FieldMeta(
        path="deed_year", label_bn="সন", kind="identifier", filled_by="extractor", editable=True
    ),
    FieldMeta(
        path="registration_date",
        label_bn="রেজিস্ট্রির তারিখ",
        kind="date_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="registration_date_text",
        label_bn="রেজিস্ট্রির তারিখ (মূল লেখা)",
        kind="date_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="sub_registry_office",
        label_bn="সাব-রেজিস্ট্রি অফিস",
        kind="text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="book_no", label_bn="বহি নং", kind="identifier", filled_by="extractor", editable=True
    ),
    FieldMeta(
        path="sellers", label_bn="দাতা / বিক্রেতা", kind="list", filled_by="extractor", editable=True
    ),
    FieldMeta(
        path="sellers[].name",
        label_bn="বিক্রেতার নাম",
        kind="name",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="sellers[].name_normalized",
        label_bn="স্বাভাবিক নাম",
        kind="name",
        filled_by="normalize",
        editable=False,
    ),
    FieldMeta(
        path="sellers[].father_or_husband_name",
        label_bn="পিতা / স্বামী",
        kind="name",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="sellers[].relation_marker",
        label_bn="পিং / জং (পিতা বা স্বামী)",
        kind="enum",
        filled_by="extractor",
        editable=True,
        enum_options=RELATION_MARKER_OPTIONS,
    ),
    FieldMeta(
        path="sellers[].address_text",
        label_bn="ঠিকানা / সাং",
        kind="text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="sellers[].share_text",
        label_bn="অংশ",
        kind="number_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="sellers[].share_fraction",
        label_bn="অংশ (ভগ্নাংশ)",
        kind="number_text",
        filled_by="normalize",
        editable=False,
    ),
    FieldMeta(
        path="sellers[].share_shatangsho",
        label_bn="অংশের জমি (শতাংশ)",
        kind="number_text",
        filled_by="normalize",
        editable=False,
    ),
    FieldMeta(
        path="buyers", label_bn="গ্রহীতা / ক্রেতা", kind="list", filled_by="extractor", editable=True
    ),
    FieldMeta(
        path="buyers[].name", label_bn="ক্রেতার নাম", kind="name", filled_by="extractor", editable=True
    ),
    FieldMeta(
        path="buyers[].name_normalized",
        label_bn="স্বাভাবিক নাম",
        kind="name",
        filled_by="normalize",
        editable=False,
    ),
    FieldMeta(
        path="buyers[].father_or_husband_name",
        label_bn="পিতা / স্বামী",
        kind="name",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="buyers[].relation_marker",
        label_bn="পিং / জং (পিতা বা স্বামী)",
        kind="enum",
        filled_by="extractor",
        editable=True,
        enum_options=RELATION_MARKER_OPTIONS,
    ),
    FieldMeta(
        path="buyers[].address_text",
        label_bn="ঠিকানা / সাং",
        kind="text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="buyers[].share_text",
        label_bn="অংশ",
        kind="number_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="buyers[].share_fraction",
        label_bn="অংশ (ভগ্নাংশ)",
        kind="number_text",
        filled_by="normalize",
        editable=False,
    ),
    FieldMeta(
        path="buyers[].share_shatangsho",
        label_bn="অংশের জমি (শতাংশ)",
        kind="number_text",
        filled_by="normalize",
        editable=False,
    ),
    FieldMeta(
        path="price_taka",
        label_bn="পণ / মূল্য (টাকা)",
        kind="number_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="price_text",
        label_bn="মূল্য (মূল লেখা)",
        kind="number_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="schedule_location.district",
        label_bn="জেলা",
        kind="text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="schedule_location.upazila",
        label_bn="উপজেলা / থানা",
        kind="text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="schedule_location.mouza",
        label_bn="মৌজা",
        kind="text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="schedule_location.jl_no",
        label_bn="জে.এল. নং",
        kind="identifier",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="schedule_khatians",
        label_bn="তফসিল: খতিয়ান নং (জরিপ সহ)",
        kind="list",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="schedule_khatians[].survey_type",
        label_bn="জরিপ",
        kind="enum",
        filled_by="extractor",
        editable=True,
        enum_options=SURVEY_OPTIONS,
    ),
    FieldMeta(
        path="schedule_khatians[].khatian_no",
        label_bn="খতিয়ান নং",
        kind="identifier",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="schedule_plots",
        label_bn="তফসিল: দাগ নং ও পরিমাণ",
        kind="list",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="schedule_plots[].dag_no",
        label_bn="দাগ নং",
        kind="identifier",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="schedule_plots[].land_class",
        label_bn="জমির শ্রেণী",
        kind="text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="schedule_plots[].plot_total_area_text",
        label_bn="দাগের মোট জমি",
        kind="number_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="schedule_plots[].plot_total_area_shatangsho",
        label_bn="দাগের মোট জমি (শতাংশ)",
        kind="number_text",
        filled_by="normalize",
        editable=False,
    ),
    FieldMeta(
        path="schedule_plots[].khatian_share_text",
        label_bn="দাগের মধ্যে অত্র খতিয়ানের অংশ",
        kind="number_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="schedule_plots[].khatian_share_fraction",
        label_bn="খতিয়ানের অংশের ভগ্নাংশ",
        kind="number_text",
        filled_by="normalize",
        editable=False,
    ),
    FieldMeta(
        path="schedule_plots[].area_text",
        label_bn="অংশানুযায়ী জমির পরিমাণ / জমির পরিমাণ",
        kind="number_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="schedule_plots[].area_shatangsho",
        label_bn="জমির পরিমাণ (শতাংশ)",
        kind="number_text",
        filled_by="normalize",
        editable=False,
    ),
    FieldMeta(
        path="transferred_area_text",
        label_bn="হস্তান্তরিত মোট জমি",
        kind="number_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="transferred_area_shatangsho",
        label_bn="হস্তান্তরিত মোট জমি (শতাংশ)",
        kind="number_text",
        filled_by="normalize",
        editable=False,
    ),
    FieldMeta(
        path="prior_deeds",
        label_bn="বায়া দলিল নং ও সন",
        kind="list",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="prior_deeds[].deed_no",
        label_bn="বায়া দলিল নং",
        kind="identifier",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="prior_deeds[].deed_year",
        label_bn="সন",
        kind="identifier",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="title_source_text",
        label_bn="মালিকানার বিবরণ / প্রাপ্তির সূত্র",
        kind="text",
        filled_by="extractor",
        editable=True,
    ),
]

MUTATION_FIELDS: list[FieldMeta] = [
    FieldMeta(
        path="doc_type", label_bn="কাগজের ধরন", kind="text", filled_by="extractor", editable=False
    ),
    FieldMeta(
        path="case_no",
        label_bn="নামজারি মোকদ্দমা / কেস নং",
        kind="identifier",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="office",
        label_bn="সহকারী কমিশনার (ভূমি) এর কার্যালয়",
        kind="text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="location.district", label_bn="জেলা", kind="text", filled_by="extractor", editable=True
    ),
    FieldMeta(
        path="location.upazila",
        label_bn="উপজেলা / থানা",
        kind="text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="location.mouza", label_bn="মৌজা", kind="text", filled_by="extractor", editable=True
    ),
    FieldMeta(
        path="location.jl_no",
        label_bn="জে.এল. নং",
        kind="identifier",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="order_date",
        label_bn="আদেশের তারিখ",
        kind="date_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="order_date_text",
        label_bn="আদেশের তারিখ (মূল লেখা)",
        kind="date_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="dcr_no",
        label_bn="ডি.সি.আর. নং",
        kind="identifier",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="dcr_date",
        label_bn="ডি.সি.আর. তারিখ",
        kind="date_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="fee_taka",
        label_bn="ফি / আদায়কৃত টাকা",
        kind="number_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="old_khatian_no",
        label_bn="পূর্বের খতিয়ান নং",
        kind="identifier",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="new_khatian_no",
        label_bn="নামজারি / প্রস্তাবিত খতিয়ান নং",
        kind="identifier",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="holding_no",
        label_bn="হোল্ডিং নং",
        kind="identifier",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="owners", label_bn="মালিকের নাম ও অংশ", kind="list", filled_by="extractor", editable=True
    ),
    FieldMeta(
        path="owners[].name",
        label_bn="মালিকের নাম / নাম",
        kind="name",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="owners[].name_normalized",
        label_bn="স্বাভাবিক নাম",
        kind="name",
        filled_by="normalize",
        editable=False,
    ),
    FieldMeta(
        path="owners[].father_or_husband_name",
        label_bn="পিতা / স্বামী",
        kind="name",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="owners[].relation_marker",
        label_bn="পিং / জং (পিতা বা স্বামী)",
        kind="enum",
        filled_by="extractor",
        editable=True,
        enum_options=RELATION_MARKER_OPTIONS,
    ),
    FieldMeta(
        path="owners[].address_text",
        label_bn="ঠিকানা / সাং",
        kind="text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="owners[].share_text",
        label_bn="অংশ",
        kind="number_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="owners[].share_fraction",
        label_bn="অংশ (ভগ্নাংশ)",
        kind="number_text",
        filled_by="normalize",
        editable=False,
    ),
    FieldMeta(
        path="owners[].share_shatangsho",
        label_bn="অংশের জমি (শতাংশ)",
        kind="number_text",
        filled_by="normalize",
        editable=False,
    ),
    FieldMeta(
        path="plots",
        label_bn="দাগ নং ও জমির পরিমাণ",
        kind="list",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="plots[].dag_no",
        label_bn="দাগ নং",
        kind="identifier",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="plots[].land_class",
        label_bn="জমির শ্রেণী",
        kind="text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="plots[].plot_total_area_text",
        label_bn="দাগের মোট জমি",
        kind="number_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="plots[].plot_total_area_shatangsho",
        label_bn="দাগের মোট জমি (শতাংশ)",
        kind="number_text",
        filled_by="normalize",
        editable=False,
    ),
    FieldMeta(
        path="plots[].khatian_share_text",
        label_bn="দাগের মধ্যে অত্র খতিয়ানের অংশ",
        kind="number_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="plots[].khatian_share_fraction",
        label_bn="খতিয়ানের অংশের ভগ্নাংশ",
        kind="number_text",
        filled_by="normalize",
        editable=False,
    ),
    FieldMeta(
        path="plots[].area_text",
        label_bn="অংশানুযায়ী জমির পরিমাণ / জমির পরিমাণ",
        kind="number_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="plots[].area_shatangsho",
        label_bn="জমির পরিমাণ (শতাংশ)",
        kind="number_text",
        filled_by="normalize",
        editable=False,
    ),
    FieldMeta(
        path="area_unit_text",
        label_bn="জমির পরিমাণের একক",
        kind="text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="total_area_text",
        label_bn="মোট জমি",
        kind="number_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="total_area_shatangsho",
        label_bn="মোট জমি (শতাংশ)",
        kind="number_text",
        filled_by="normalize",
        editable=False,
    ),
    FieldMeta(
        path="basis_text",
        label_bn="নামজারির কারণ (ক্রয় / ওয়ারিশ / দান …)",
        kind="text",
        filled_by="extractor",
        editable=True,
    ),
]

HEIR_CERT_FIELDS: list[FieldMeta] = [
    FieldMeta(
        path="doc_type", label_bn="কাগজের ধরন", kind="text", filled_by="extractor", editable=False
    ),
    FieldMeta(
        path="certificate_no",
        label_bn="স্মারক নং / সনদ নং",
        kind="identifier",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="issue_date",
        label_bn="প্রদানের তারিখ",
        kind="date_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="issuing_authority",
        label_bn="ইউনিয়ন পরিষদ / পৌরসভা / সিটি কর্পোরেশন",
        kind="text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="issuer_title",
        label_bn="চেয়ারম্যান / মেয়র / কাউন্সিলর",
        kind="text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="deceased_name",
        label_bn="মৃত ব্যক্তির নাম",
        kind="name",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="deceased_father_or_husband_name",
        label_bn="পিতা / স্বামী",
        kind="name",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="deceased_address.district",
        label_bn="জেলা",
        kind="text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="deceased_address.upazila",
        label_bn="উপজেলা / থানা",
        kind="text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="deceased_address.mouza",
        label_bn="মৌজা",
        kind="text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="deceased_address.jl_no",
        label_bn="জে.এল. নং",
        kind="identifier",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="deceased_address.address_text",
        label_bn="ঠিকানা / গ্রাম",
        kind="text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="date_of_death",
        label_bn="মৃত্যুর তারিখ",
        kind="date_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="date_of_death_text",
        label_bn="মৃত্যুর তারিখ (মূল লেখা)",
        kind="date_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="heirs",
        label_bn="ওয়ারিশগণের নাম ও সম্পর্ক",
        kind="list",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="heirs[].name", label_bn="নাম", kind="name", filled_by="extractor", editable=True
    ),
    FieldMeta(
        path="heirs[].name_normalized",
        label_bn="স্বাভাবিক নাম",
        kind="name",
        filled_by="normalize",
        editable=False,
    ),
    FieldMeta(
        path="heirs[].father_or_husband_name",
        label_bn="পিতা / স্বামী",
        kind="name",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="heirs[].relation",
        label_bn="সম্পর্ক",
        kind="enum",
        filled_by="extractor",
        editable=True,
        enum_options=RELATION_OPTIONS,
    ),
    FieldMeta(
        path="heirs[].relation_text",
        label_bn="সম্পর্ক (মূল লেখা)",
        kind="text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="heirs[].is_deceased",
        label_bn="মৃত",
        kind="enum",
        filled_by="extractor",
        editable=True,
        enum_options=BOOL_OPTIONS,
    ),
    FieldMeta(
        path="heirs[].share_text",
        label_bn="অংশ",
        kind="number_text",
        filled_by="extractor",
        editable=True,
    ),
    FieldMeta(
        path="heirs[].share_fraction",
        label_bn="অংশ (ভগ্নাংশ)",
        kind="number_text",
        filled_by="normalize",
        editable=False,
    ),
]

DOC_TYPE_FIELDS: dict[str, list[FieldMeta]] = {
    "khatian": KHATIAN_FIELDS,
    "deed": DEED_FIELDS,
    "dcr": MUTATION_FIELDS,
    "heir_cert": HEIR_CERT_FIELDS,
}


def get_field_meta_by_doc_type() -> FieldsMetaResponse:
    return FieldsMetaResponse(
        khatian=KHATIAN_FIELDS,
        deed=DEED_FIELDS,
        dcr=MUTATION_FIELDS,
        heir_cert=HEIR_CERT_FIELDS,
    )


def extract_schema_fields(cls: type[BaseModel], prefix: str = "") -> set[str]:
    """Inspect all field paths for a Pydantic model class recursively."""
    paths = set()
    for name, field in cls.model_fields.items():
        ann = field.annotation
        origin = get_origin(ann)
        if origin in (Union, types.UnionType):
            args = [a for a in get_args(ann) if a is not type(None)]
            ann = args[0] if len(args) == 1 else ann
            origin = get_origin(ann)

        path = f"{prefix}{name}"
        if origin is list:
            paths.add(path)
            item_ann = get_args(ann)[0]
            item_origin = get_origin(item_ann)
            if item_origin in (Union, types.UnionType):
                i_args = [a for a in get_args(item_ann) if a is not type(None)]
                item_ann = i_args[0] if len(i_args) == 1 else item_ann
            if isinstance(item_ann, type) and issubclass(item_ann, BaseModel):
                paths.update(extract_schema_fields(item_ann, f"{path}[]."))
        elif isinstance(ann, type) and issubclass(ann, BaseModel):
            paths.update(extract_schema_fields(ann, f"{path}."))
        else:
            paths.add(path)
    return paths

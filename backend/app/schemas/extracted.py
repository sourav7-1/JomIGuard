"""Extracted document data. Field source of truth: docs/specs/fields.md.

Fields that normalize.py derives (*_shatangsho, *_fraction, name_normalized) are
Optional/None so raw extractor output validates. No validator here computes or converts anything.
"""

import enum
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SurveyType(enum.StrEnum):
    CS = "CS"
    SA = "SA"
    RS = "RS"
    BS = "BS"
    CITY = "CITY"


class DeedType(enum.StrEnum):
    saf_kabala = "saf_kabala"
    heba = "heba"
    dan = "dan"
    bonton = "bonton"
    bayna = "bayna"
    other = "other"


class RelationMarker(enum.StrEnum):
    father = "father"
    husband = "husband"
    unknown = "unknown"


class Relation(enum.StrEnum):
    son = "son"
    daughter = "daughter"
    wife = "wife"
    husband = "husband"
    father = "father"
    mother = "mother"
    brother = "brother"
    sister = "sister"
    other = "other"


# --- shared objects ---


class Location(_Model):
    district: str
    upazila: str
    mouza: str
    jl_no: str | None = None


class Address(_Model):
    """Heir certificate address: all optional, a mouza is often not printed."""

    district: str | None = None
    upazila: str | None = None
    mouza: str | None = None
    jl_no: str | None = None
    address_text: str | None = None


class Owner(_Model):
    name: str
    name_normalized: str | None = None  # normalize
    father_or_husband_name: str | None = None
    relation_marker: RelationMarker | None = None
    address_text: str | None = None
    share_text: str | None = None
    share_fraction: Decimal | None = None  # normalize
    share_shatangsho: Decimal | None = None  # normalize


class Plot(_Model):
    dag_no: str
    land_class: str | None = None
    plot_total_area_text: str | None = None
    plot_total_area_shatangsho: Decimal | None = None  # normalize
    khatian_share_text: str | None = None
    khatian_share_fraction: Decimal | None = None  # normalize
    area_text: str
    area_shatangsho: Decimal | None = None  # normalize


class Heir(_Model):
    name: str
    name_normalized: str | None = None  # normalize
    father_or_husband_name: str | None = None
    relation: Relation
    relation_text: str
    is_deceased: bool | None = None
    share_text: str | None = None
    share_fraction: Decimal | None = None  # normalize


class KhatianRef(_Model):
    survey_type: SurveyType
    khatian_no: str


class PriorDeed(_Model):
    deed_no: str
    deed_year: str | None = None


# --- document types ---


class KhatianData(_Model):
    doc_type: Literal["khatian"]
    survey_type: SurveyType
    location: Location
    khatian_no: str
    touzi_no: str | None = None
    owners: list[Owner]
    plots: list[Plot]
    area_unit_text: str | None = None  # unit printed in the area column header, e.g. "একর"
    total_area_text: str | None = None
    total_area_shatangsho: Decimal | None = None  # normalize
    annual_revenue_text: str | None = None
    landlord_name: str | None = None
    mutation_case_ref: str | None = None
    record_date: date | None = None
    record_date_text: str | None = None


class DeedData(_Model):
    doc_type: Literal["deed"]
    deed_type: DeedType
    is_draft: bool
    deed_no: str | None = None
    deed_year: str | None = None
    registration_date: date | None = None
    registration_date_text: str | None = None
    sub_registry_office: str | None = None
    book_no: str | None = None
    sellers: list[Owner]
    buyers: list[Owner]
    price_taka: Decimal | None = None
    price_text: str | None = None
    schedule_location: Location
    schedule_khatians: list[KhatianRef]
    schedule_plots: list[Plot]
    transferred_area_text: str
    transferred_area_shatangsho: Decimal | None = None  # normalize
    prior_deeds: list[PriorDeed] = []
    title_source_text: str | None = None


class MutationData(_Model):
    """Mutation khatian plus DCR receipt; DB doc_type stays "dcr"."""

    doc_type: Literal["dcr"]
    case_no: str
    office: str | None = None
    location: Location
    order_date: date | None = None
    order_date_text: str | None = None
    dcr_no: str | None = None
    dcr_date: date | None = None
    fee_taka: Decimal | None = None
    old_khatian_no: str | None = None
    new_khatian_no: str
    holding_no: str | None = None
    owners: list[Owner]
    plots: list[Plot]
    area_unit_text: str | None = None  # unit printed in the area column header, e.g. "একর"
    total_area_text: str | None = None
    total_area_shatangsho: Decimal | None = None  # normalize
    basis_text: str | None = None


class HeirCertData(_Model):
    doc_type: Literal["heir_cert"]
    certificate_no: str | None = None
    issue_date: date | None = None
    issuing_authority: str
    issuer_title: str | None = None
    deceased_name: str
    deceased_father_or_husband_name: str | None = None
    deceased_address: Address | None = None
    date_of_death: date | None = None
    date_of_death_text: str | None = None
    heirs: list[Heir]


ExtractedDocument = Annotated[
    KhatianData | DeedData | MutationData | HeirCertData,
    Field(discriminator="doc_type"),
]

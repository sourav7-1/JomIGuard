# Field specification: extracted document data

**Status: DRAFT. Every field below is UNVERIFIED** until checked against real document formats.

Pydantic schemas: `backend/app/schemas/extracted.py` → `KhatianData`, `DeedData`, `MutationData`, `HeirCertData`, combined as `ExtractedDocument` (discriminated on `doc_type`).
Consumers: rule engine (`identity`, `area`, `heirs`, `chain`).

Example values follow the team demo (দাগ ৩০৫, খতিয়ান ৮৮২, রহিম/করিম/সালমা). All names and numbers are samples.

## Conventions

- **Identifiers are strings.** `dag_no`, `khatian_no`, `jl_no`, `deed_no`, `case_no`, `holding_no` and similar are always `string` (`"305/1"`, `"১২৪৩/২৬"` normalised to `"1243/26"`). An int is rejected.
- **Digits.** Store identifiers with ASCII digits; keep the printed Bangla form only in `*_text` fields.
- **Area and share: always two values.**
  - `*_text`: the exact text the cell shows (`".১৫০০"`, `"৬ শতাংশ"`, `"।০ আনা"`). No unit is added if the cell has none; a unit printed only in the column header goes in `area_unit_text` (khatian, mutation).
  - `*_shatangsho`: normalised `decimal` in শতাংশ (decimal). 1 একর = 100 শতাংশ.
  - Shares printed as a *fraction of the khatian/plot* (e.g. `.৪০০`) also get `*_fraction` (decimal 0–1). See Decisions.
- **Decimals.** Areas, shares and money are `decimal`, never float.
- **Dates.** `date` fields are ISO `YYYY-MM-DD`. If the document uses বঙ্গাব্দ or only a year, keep `*_text` and leave the date `null`.
- **Unknown fields are rejected** on every model (`extra="forbid"`).
- **Excluded personal data.** NID, phone numbers and birth registration numbers are **never** extracted, even when printed. Same for photos and signatures.
- **filled_by column.** `extractor` = read from the document as printed; `normalize` = derived later by `normalize.py`. Every `normalize` field is optional (default `null`), so raw extractor output validates.
- **Rule column.** `identity` = names/IDs match across documents; `area` = shares and areas add up; `heirs` = who the heirs are; `chain` = ownership history links; `none yet` = stored for display or future use.

## Shared objects

### `Location` (khatian, deed, mutation)

| field_name | Bangla label | type | req | filled_by | rule | example | status |
|---|---|---|---|---|---|---|---|
| district | জেলা | string | required | extractor | identity | `"বরিশাল"` | UNVERIFIED |
| upazila | উপজেলা / থানা | string | required | extractor | identity | `"গৌরনদী"` | UNVERIFIED |
| mouza | মৌজা | string | required | extractor | identity | `"চাঁদশী"` | UNVERIFIED |
| jl_no | জে.এল. নং | string | optional | extractor | identity | `"45"` | UNVERIFIED |

### `Address` (heir certificate: deceased's address)

Same fields as `Location` plus `address_text`, but **every field is optional**: heir certificates often print a village and union, not a mouza.

| field_name | Bangla label | type | req | filled_by | rule | example | status |
|---|---|---|---|---|---|---|---|
| district | জেলা | string | optional | extractor | identity | `"বরিশাল"` | UNVERIFIED |
| upazila | উপজেলা / থানা | string | optional | extractor | identity | `"গৌরনদী"` | UNVERIFIED |
| mouza | মৌজা | string | optional | extractor | identity | `"চাঁদশী"` | UNVERIFIED |
| jl_no | জে.এল. নং | string | optional | extractor | identity | `"45"` | UNVERIFIED |
| address_text | ঠিকানা / গ্রাম | string | optional | extractor | identity | `"গ্রাম চাঁদশী"` | UNVERIFIED |

### `Owner` (khatian, deed, mutation)

| field_name | Bangla label | type | req | filled_by | rule | example | status |
|---|---|---|---|---|---|---|---|
| name | মালিকের নাম / নাম | string | required | extractor | identity | `"মোঃ রহিম উদ্দিন"` | UNVERIFIED |
| name_normalized | — | string | optional | normalize | identity | `"রহিম উদ্দিন"` | UNVERIFIED |
| father_or_husband_name | পিতা / স্বামী | string | optional | extractor | identity | `"রহমান"` | UNVERIFIED |
| relation_marker | পিং / জং (পিতা বা স্বামী) | enum: `father`, `husband`, `unknown` | optional | extractor | identity | `"father"` | UNVERIFIED |
| address_text | ঠিকানা / সাং | string | optional | extractor | none yet | `"সাং চাঁদশী"` | UNVERIFIED |
| share_text | অংশ | string | optional | extractor | area | `".৪০০"` | UNVERIFIED |
| share_fraction | — | decimal | optional | normalize | area, heirs | `0.400` | UNVERIFIED |
| share_shatangsho | — | decimal | optional | normalize | area | `6.0` | UNVERIFIED |

### `Plot` (one row per দাগ)

| field_name | Bangla label | type | req | filled_by | rule | example | status |
|---|---|---|---|---|---|---|---|
| dag_no | দাগ নং | string | required | extractor | identity, chain | `"305"` | UNVERIFIED |
| land_class | জমির শ্রেণী | string | optional | extractor | none yet | `"নাল"` | UNVERIFIED |
| plot_total_area_text | দাগের মোট জমি | string | optional | extractor | area | `".১৫০০"` | UNVERIFIED |
| plot_total_area_shatangsho | — | decimal | optional | normalize | area | `15.0` | UNVERIFIED |
| khatian_share_text | দাগের মধ্যে অত্র খতিয়ানের অংশ | string | optional | extractor | area | `"১.০০০"` | UNVERIFIED |
| khatian_share_fraction | — | decimal | optional | normalize | area | `1.0` | UNVERIFIED |
| area_text | অংশানুযায়ী জমির পরিমাণ / জমির পরিমাণ | string | required | extractor | area | `".১৫০০"` (khatian), `"১০ শতাংশ"` (deed) | UNVERIFIED |
| area_shatangsho | — | decimal | optional | normalize | area | `15.0` | UNVERIFIED |

### `Heir` (heir certificate)

| field_name | Bangla label | type | req | filled_by | rule | example | status |
|---|---|---|---|---|---|---|---|
| name | নাম | string | required | extractor | identity, heirs | `"মোছাঃ সালমা খাতুন"` | UNVERIFIED |
| name_normalized | — | string | optional | normalize | identity, heirs | `"সালমা খাতুন"` | UNVERIFIED |
| father_or_husband_name | পিতা / স্বামী | string | optional | extractor | identity | `"রহমান"` | UNVERIFIED |
| relation | সম্পর্ক | enum: `son`, `daughter`, `wife`, `husband`, `father`, `mother`, `brother`, `sister`, `other` | required | extractor | heirs | `"daughter"` | UNVERIFIED |
| relation_text | সম্পর্ক (as printed) | string | required | extractor | heirs | `"কন্যা"` | UNVERIFIED |
| is_deceased | মৃত (if marked) | bool | optional | extractor | heirs | `false` | UNVERIFIED |
| share_text | অংশ (only if printed) | string | optional | extractor | heirs, area | `null` | UNVERIFIED |
| share_fraction | — (only if printed) | decimal | optional | normalize | heirs, area | `null` | UNVERIFIED |

### `KhatianRef` (deed schedule: one khatian reference)

| field_name | Bangla label | type | req | filled_by | rule | example | status |
|---|---|---|---|---|---|---|---|
| survey_type | জরিপ | enum: `CS`, `SA`, `RS`, `BS`, `CITY` | required | extractor | identity, chain | `"SA"` | UNVERIFIED |
| khatian_no | খতিয়ান নং | string | required | extractor | identity, chain | `"214"` | UNVERIFIED |

### `PriorDeed` (deed: one বায়া দলিল)

| field_name | Bangla label | type | req | filled_by | rule | example | status |
|---|---|---|---|---|---|---|---|
| deed_no | বায়া দলিল নং | string | required | extractor | chain | `"3310"` | UNVERIFIED |
| deed_year | সন | string | optional | extractor | chain | `"1985"` | UNVERIFIED |

## 1. Khatian (খতিয়ান): CS / SA / RS / BS → `KhatianData`

| field_name | Bangla label | type | req | filled_by | rule | example | status |
|---|---|---|---|---|---|---|---|
| doc_type | — | literal `"khatian"` | required | extractor | none yet | `"khatian"` | UNVERIFIED |
| survey_type | জরিপ (সি.এস. / এস.এ. / আর.এস. / বি.এস.) | enum: `CS`, `SA`, `RS`, `BS`, `CITY` | required | extractor | chain | `"BS"` | UNVERIFIED |
| location | — | `Location` | required | extractor | identity | see above | UNVERIFIED |
| khatian_no | খতিয়ান নং | string | required | extractor | identity, chain | `"882"` | UNVERIFIED |
| touzi_no | তৌজি নং / রেভিনিউ নং | string | optional | extractor | none yet | `"1520"` | UNVERIFIED |
| owners | মালিক / অংশীদারগণের নাম ও ঠিকানা | list[`Owner`] | required | extractor | identity, area, heirs | `[{"name": "মোঃ রহিম উদ্দিন", "share_text": ".৪০০", "share_shatangsho": 6.0}, …]` | UNVERIFIED |
| plots | দাগ নং ও জমির বিবরণ | list[`Plot`] | required | extractor | identity, area | `[{"dag_no": "305", "area_shatangsho": 15.0}]` | UNVERIFIED |
| area_unit_text | জমির পরিমাণ (একর): unit in the area column header | string | optional | extractor | area | `"একর"` | UNVERIFIED |
| total_area_text | মোট জমি | string | optional | extractor | area | `".১৫০০"` | UNVERIFIED |
| total_area_shatangsho | — | decimal | optional | normalize | area | `15.0` | UNVERIFIED |
| annual_revenue_text | বার্ষিক খাজনা / রাজস্ব | string | optional | extractor | none yet | `"২ টাকা"` | UNVERIFIED |
| landlord_name | জমিদার / ভূস্বামী (CS only) | string | optional | extractor | none yet | `"…"` | UNVERIFIED |
| mutation_case_ref | নামজারি / জমাভাগ কেস নং (if printed) | string | optional | extractor | chain | `"512/18"` | UNVERIFIED |
| record_date | প্রস্তুতের / চূড়ান্ত প্রকাশের তারিখ | date | optional | extractor | chain | `"2018-03-15"` | UNVERIFIED |
| record_date_text | — | string | optional | extractor | chain | `"১৫/০৩/২০১৮"` | UNVERIFIED |

## 2. Sale deed (সাফ কবলা দলিল) → `DeedData`

| field_name | Bangla label | type | req | filled_by | rule | example | status |
|---|---|---|---|---|---|---|---|
| doc_type | — | literal `"deed"` | required | extractor | none yet | `"deed"` | UNVERIFIED |
| deed_type | দলিলের প্রকৃতি | enum: `saf_kabala`, `heba`, `dan`, `bonton`, `bayna`, `other` | required | extractor | chain | `"saf_kabala"` | UNVERIFIED |
| is_draft | — (draft vs registered copy) | bool | required | extractor | chain | `true` | UNVERIFIED |
| deed_no | দলিল নং | string | optional (empty on drafts) | extractor | identity, chain | `"4521"` | UNVERIFIED |
| deed_year | সন | string | optional | extractor | chain | `"1985"` | UNVERIFIED |
| registration_date | রেজিস্ট্রির তারিখ | date | optional | extractor | chain | `"1985-06-12"` | UNVERIFIED |
| registration_date_text | — | string | optional | extractor | chain | `"১২/০৬/১৯৮৫"` | UNVERIFIED |
| sub_registry_office | সাব-রেজিস্ট্রি অফিস | string | optional | extractor | none yet | `"গৌরনদী"` | UNVERIFIED |
| book_no | বহি নং | string | optional | extractor | none yet | `"1"` | UNVERIFIED |
| sellers | দাতা / বিক্রেতা | list[`Owner`] | required | extractor | identity, area, chain | `[{"name": "মোঃ রহিম উদ্দিন", "father_or_husband_name": "রহমান"}]` | UNVERIFIED |
| buyers | গ্রহীতা / ক্রেতা | list[`Owner`] | required | extractor | identity, chain | `[{"name": "মোঃ রফিক আহমেদ"}]` | UNVERIFIED |
| price_taka | পণ / মূল্য (টাকা) | decimal | optional | extractor | none yet | `6000000` | UNVERIFIED |
| price_text | — | string | optional | extractor | none yet | `"৬০,০০,০০০/- টাকা"` | UNVERIFIED |
| schedule_location | তফসিল: জেলা, উপজেলা, মৌজা, জে.এল. নং | `Location` | required | extractor | identity | see above | UNVERIFIED |
| schedule_khatians | তফসিল: খতিয়ান নং (জরিপ সহ) | list[`KhatianRef`] | required | extractor | identity, chain | `[{"survey_type": "BS", "khatian_no": "882"}, {"survey_type": "SA", "khatian_no": "214"}]` | UNVERIFIED |
| schedule_plots | তফসিল: দাগ নং ও পরিমাণ | list[`Plot`] | required | extractor | identity, area | `[{"dag_no": "305", "area_text": "১০ শতাংশ", "area_shatangsho": 10.0}]` | UNVERIFIED |
| transferred_area_text | হস্তান্তরিত মোট জমি | string | required | extractor | area | `"১০ শতাংশ"` | UNVERIFIED |
| transferred_area_shatangsho | — | decimal | optional | normalize | area | `10.0` | UNVERIFIED |
| prior_deeds | বায়া দলিল নং ও সন | list[`PriorDeed`] | optional (default `[]`) | extractor | chain | `[{"deed_no": "3310", "deed_year": "1985"}]` | UNVERIFIED |
| title_source_text | মালিকানার বিবরণ / প্রাপ্তির সূত্র | string | optional | extractor | chain, heirs | `"পিতা রহমানের মৃত্যুতে ওয়ারিশ সূত্রে প্রাপ্ত"` | UNVERIFIED |

## 3. Mutation (নামজারি খতিয়ান ও ডিসিআর) → `MutationData`

One schema for the mutation khatian plus the DCR fee receipt. All DCR fields (`dcr_no`, `dcr_date`, `fee_taka`) are optional, since the receipt may be missing or uploaded separately. The DB `doc_type` stays `"dcr"`.

| field_name | Bangla label | type | req | filled_by | rule | example | status |
|---|---|---|---|---|---|---|---|
| doc_type | — | literal `"dcr"` | required | extractor | none yet | `"dcr"` | UNVERIFIED |
| case_no | নামজারি মোকদ্দমা / কেস নং | string | required | extractor | identity, chain | `"512/18"` | UNVERIFIED |
| office | সহকারী কমিশনার (ভূমি) এর কার্যালয় | string | optional | extractor | none yet | `"গৌরনদী, বরিশাল"` | UNVERIFIED |
| location | — | `Location` | required | extractor | identity | see above | UNVERIFIED |
| order_date | আদেশের তারিখ | date | optional | extractor | chain | `"2018-02-01"` | UNVERIFIED |
| order_date_text | — | string | optional | extractor | chain | `"০১/০২/২০১৮"` | UNVERIFIED |
| dcr_no | ডি.সি.আর. নং | string | optional | extractor | none yet | `"778812"` | UNVERIFIED |
| dcr_date | ডি.সি.আর. তারিখ | date | optional | extractor | chain | `"2018-02-05"` | UNVERIFIED |
| fee_taka | ফি / আদায়কৃত টাকা | decimal | optional | extractor | none yet | `1150` | UNVERIFIED |
| old_khatian_no | পূর্বের খতিয়ান নং | string | optional | extractor | chain | `"214"` | UNVERIFIED |
| new_khatian_no | নামজারি / প্রস্তাবিত খতিয়ান নং | string | required | extractor | identity, chain | `"882"` | UNVERIFIED |
| holding_no | হোল্ডিং নং | string | optional | extractor | identity | `"312"` | UNVERIFIED |
| owners | মালিকের নাম ও অংশ | list[`Owner`] | required | extractor | identity, area, heirs | `[{"name": "মোঃ রহিম উদ্দিন", "share_text": ".৪০০", "share_shatangsho": 6.0}, …]` | UNVERIFIED |
| plots | দাগ নং ও জমির পরিমাণ | list[`Plot`] | required | extractor | identity, area | `[{"dag_no": "305", "area_shatangsho": 15.0}]` | UNVERIFIED |
| area_unit_text | জমির পরিমাণ (একর): unit in the area column header | string | optional | extractor | area | `"একর"` | UNVERIFIED |
| total_area_text | মোট জমি | string | optional | extractor | area | `".১৫০০"` | UNVERIFIED |
| total_area_shatangsho | — | decimal | optional | normalize | area | `15.0` | UNVERIFIED |
| basis_text | নামজারির কারণ (ক্রয় / ওয়ারিশ / দান …) | string | optional | extractor | chain, heirs | `"ওয়ারিশ সূত্রে"` | UNVERIFIED |

## 4. Heir certificate (ওয়ারিশ সনদ) → `HeirCertData`

| field_name | Bangla label | type | req | filled_by | rule | example | status |
|---|---|---|---|---|---|---|---|
| doc_type | — | literal `"heir_cert"` | required | extractor | none yet | `"heir_cert"` | UNVERIFIED |
| certificate_no | স্মারক নং / সনদ নং | string | optional | extractor | none yet | `"ইউপি/২০১৮/৫৫"` | UNVERIFIED |
| issue_date | প্রদানের তারিখ | date | optional | extractor | chain | `"2018-01-10"` | UNVERIFIED |
| issuing_authority | ইউনিয়ন পরিষদ / পৌরসভা / সিটি কর্পোরেশন | string | required | extractor | none yet | `"৫ নং চাঁদশী ইউনিয়ন পরিষদ"` | UNVERIFIED |
| issuer_title | চেয়ারম্যান / মেয়র / কাউন্সিলর | string | optional | extractor | none yet | `"চেয়ারম্যান"` | UNVERIFIED |
| deceased_name | মৃত ব্যক্তির নাম | string | required | extractor | identity, heirs, chain | `"রহমান"` | UNVERIFIED |
| deceased_father_or_husband_name | পিতা / স্বামী | string | optional | extractor | identity | `"ইউসুফ আলী"` | UNVERIFIED |
| deceased_address | — | `Address` | optional | extractor | identity | `{"upazila": "গৌরনদী", "address_text": "গ্রাম চাঁদশী"}` | UNVERIFIED |
| date_of_death | মৃত্যুর তারিখ | date | optional | extractor | heirs, chain | `"2009-08-20"` | UNVERIFIED |
| date_of_death_text | — | string | optional | extractor | heirs, chain | `"২০/০৮/২০০৯"` | UNVERIFIED |
| heirs | ওয়ারিশগণের নাম ও সম্পর্ক | list[`Heir`] | required | extractor | identity, heirs | see `Heir` above | UNVERIFIED |

## Decisions (MVP)

1. **Shares.** The extractor gives `share_text` as printed. `normalize.py` fills `share_fraction` and `share_shatangsho`.
2. **Units.** Only একর, শতাংশ and decimal fractions are converted. বিঘা, কাঠা, আনা and any other unit stay as text and produce an `unsupported_unit` warning, never a guessed conversion.
3. **One owner share per khatian.** An owner's area in a plot = `share_fraction` × plot area. *(Needs expert check.)*
4. **City survey** khatians keep the `CITY` survey type.
5. **No inheritance-share calculation.** Heir shares come from the mutation / BS khatian. *(Needs expert check.)* The heir certificate only tells who all the heirs are. No religion field.
6. **বঙ্গাব্দ dates.** Keep the text; the `date` field stays `null`.
7. **Witnesses and deed writer** (সাক্ষী, দলিল লেখক) are not extracted.
8. **Area unit.** normalize reads the unit from `area_text` first; if the cell has no unit, it uses `area_unit_text`; if neither has a unit, it emits a `missing_unit` warning and leaves `*_shatangsho` empty.

from app.services.rules.names import names_match


def escrow_conditions(case, assessment, buyer_verification, deadline, registration=None):
    sellers = case.proposed_deed.data.sellers if case.proposed_deed else []
    seller_rows = case.identity or []
    all_verified = bool(buyer_verification and buyer_verification.status == "verified") and all(
        any(
            row.status == "verified" and names_match(seller.name, row.seller_name_on_deed or "")[0]
            for row in seller_rows
        )
        for seller in sellers
    )
    findings = assessment.findings if assessment else []
    no_bad = not any(getattr(item.status, "value", item.status) == "bad" for item in findings)
    no_consent_gap = not any(item.code == "heir_consent_missing" for item in findings)
    registered = bool(
        registration and registration[0] and registration[1] and registration[1] <= deadline
    )
    return [
        {
            "id": "both_parties_verified",
            "label_bn": "ক্রেতা ও সব বিক্রেতার পরিচয় যাচাই",
            "met": all_verified,
            "detail_bn": "ক্রেতা ও দলিলের প্রত্যেক বিক্রেতার যাচাইয়ের ফল মিলেছে।"
            if all_verified
            else "ক্রেতা ও প্রত্যেক দলিল বিক্রেতার যাচাই সম্পন্ন হওয়া বাকি।",
        },
        {
            "id": "no_bad_findings",
            "label_bn": "সর্বশেষ যাচাইয়ে গুরুতর অমিল নেই",
            "met": no_bad,
            "detail_bn": "সর্বশেষ assessment-এ bad finding নেই।"
            if no_bad
            else "সর্বশেষ assessment-এ bad finding আছে।",
        },
        {
            "id": "co_owner_consent",
            "label_bn": "সহ-মালিকের সম্মতির বাধা নেই",
            "met": no_consent_gap,
            "detail_bn": "heir_consent_missing finding নেই।"
            if no_consent_gap
            else "সহ-মালিকের সম্মতি যাচাই বাকি।",
        },
        {
            "id": "registration_by_deadline",
            "label_bn": "সময়সীমার মধ্যে রেজিস্ট্রি",
            "met": registered,
            "detail_bn": "সময়সীমার মধ্যে deed number-সহ রেজিস্ট্রি নথিভুক্ত।"
            if registered
            else "সময়সীমার মধ্যে deed number-সহ রেজিস্ট্রি নথিভুক্ত হয়নি।",
        },
    ]

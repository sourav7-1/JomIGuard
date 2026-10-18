from app.services.rules.names import names_match


def _owner_map(data):
    result = {}
    for owner in data.get("owners", []):
        key = next(
            (key for key in result if names_match(key, owner.get("name"))[0]), owner.get("name")
        )
        result[key] = owner
    return result


def diff_khatians(old, new, user_verified_name=None, low_confidence_fields=()):
    """Compare normalized khatian dictionaries; return severity and presentation-ready changes."""
    changes = []
    severity = {"info": 0, "warn": 1, "bad": 2}

    def add(field, before, after, level, message):
        changes.append(
            {"field": field, "old": before, "new": after, "severity": level, "message_bn": message}
        )

    old_owners, new_owners = _owner_map(old), _owner_map(new)
    removed = [
        o
        for name, o in old_owners.items()
        if not any(names_match(name, nn)[0] for nn in new_owners)
    ]
    added = [
        o
        for name, o in new_owners.items()
        if not any(names_match(name, on)[0] for on in old_owners)
    ]
    for owner in removed:
        add("owners", owner, None, "bad", "মালিকের নাম বাদ গেছে")
    for owner in added:
        add("owners", None, owner, "bad", "নতুন মালিকের নাম যোগ হয়েছে")
    for name, owner in old_owners.items():
        current = next((o for n, o in new_owners.items() if names_match(name, n)[0]), None)
        if current and any(
            owner.get(k) != current.get(k)
            for k in ("share_text", "share_fraction", "share_shatangsho")
        ):
            add("owners.share", owner, current, "bad", "মালিকের অংশ বদলেছে")
    for field in ("total_area_text", "total_area_shatangsho"):
        if old.get(field) != new.get(field):
            add(field, old.get(field), new.get(field), "bad", "জমির মোট পরিমাণ বদলেছে")
    for field in ("mutation_case_ref", "khatian_no"):
        if old.get(field) != new.get(field):
            add(field, old.get(field), new.get(field), "warn", "তথ্য বদলেছে; যাচাই দরকার")
    same_owners = not removed and not added
    if same_owners:
        for field in ("touzi_no", "annual_revenue_text"):
            if old.get(field) != new.get(field):
                add(field, old.get(field), new.get(field), "info", "খাজনার holding হালনাগাদ, মালিক একই")
    if (
        user_verified_name
        and any(names_match(user_verified_name, o.get("name"))[0] for o in old_owners.values())
        and not any(names_match(user_verified_name, o.get("name"))[0] for o in new_owners.values())
    ):
        add(
            "user_owner",
            user_verified_name,
            None,
            "bad",
            "নতুন খতিয়ানে আপনার নাম নেই। এটা কি আপনি করেছেন? না করে থাকলে এখনই ব্যবস্থা নিন।",
        )
    for field in low_confidence_fields:
        if any(c["field"] == field for c in changes):
            for change in changes:
                if change["field"] == field:
                    change["severity"] = "warn"
                    change["message_bn"] = "যাচাই দরকার"
    level = max((c["severity"] for c in changes), key=severity.get, default="info")
    return {"severity": level, "changes": changes}

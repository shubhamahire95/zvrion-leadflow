"""High-conversion education categories for lead collection searches."""

_RAW_COACHING_CATEGORIES = [
    "Coaching Classes",
    "Tuition Classes",
    "Tutorials",
    "Academy",
    "Computer Institute",
    "Training Institute",
    "NEET Classes",
    "JEE Classes",
    "MHT CET Classes",
    "Competitive Exam Classes",
    "Spoken English",
    "English Speaking Classes",
    "Abacus Classes",
    "Study Center",
]


def _dedupe_categories(categories: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for category in categories:
        normalized = " ".join(category.split()).casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(" ".join(category.split()))
    return deduped


COACHING_CATEGORIES = _dedupe_categories(_RAW_COACHING_CATEGORIES)

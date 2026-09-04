"""
backend/ingestion/normalise.py

Normalises raw scheme records from the 7 schemes_batch_*.json files (all of
which share one flat schema: scheme_id, name, level, state,
sponsoring_department, category, short_description, benefit_description,
benefit_amount_inr, benefit_type, eligibility_structured, eligibility_notes,
required_documents, citizen_charter_deadline_days, application_mode,
application_url, official_source_url, last_scraped_at, data_completeness)
into one NormalisedScheme shape used for embedding and retrieval.

The raw "category" field is a list of free-text tags (e.g.
["social_security", "agriculture", "rural_development"]); NormalisedScheme
needs exactly one enum value, so tags are resolved to a single bucket by
priority: agriculture > education > healthcare > employment_msme >
social_welfare > other. This priority was chosen by inspecting real
records — e.g. PM-KISAN is tagged both "social_security" and "agriculture"
but is fundamentally a farmer income-support scheme, so agriculture must
outrank social_welfare.

target_beneficiaries has no direct source field in the raw data. It is
derived from eligibility_structured.occupation plus a handful of category
tags mapped to human-readable beneficiary phrases (e.g. "women_empowerment"
-> "women"). This is a heuristic, not a sourced field.
"""

import logging
from typing import Optional, TypedDict

logger = logging.getLogger(__name__)


class NormalisedScheme(TypedDict):
    scheme_id: str
    name: str
    description: str
    department: str
    state: str
    category: str
    target_beneficiaries: str
    eligibility_notes: str
    required_documents: list
    citizen_charter_days: Optional[int]
    income_max: Optional[int]
    age_min: Optional[int]
    age_max: Optional[int]
    landholding_max_hectares: Optional[float]
    gender: Optional[str]
    official_source_url: str


_VALID_CATEGORIES = (
    "agriculture",
    "education",
    "social_welfare",
    "healthcare",
    "employment_msme",
    "other",
)

_AGRICULTURE_TAGS = {"agriculture", "farmer_welfare", "fisheries"}
_EDUCATION_TAGS = {"education", "scholarship"}
_HEALTHCARE_TAGS = {"healthcare", "insurance"}
_EMPLOYMENT_MSME_TAGS = {
    "msme",
    "entrepreneurship",
    "employment",
    "skill_development",
    "startups",
    "manufacturing",
    "artisan",
}
_SOCIAL_WELFARE_TAGS = {
    "social_security",
    "women_empowerment",
    "child_welfare",
    "sc_st_welfare",
    "disability_welfare",
    "obc_welfare",
    "elderly_welfare",
    "minority_welfare",
    "social_welfare",
    "pension",
    "tribal_welfare",
    "bc_welfare",
    "differently_abled",
    "housing",
}

_TAG_TO_BENEFICIARY_PHRASE = {
    "women_empowerment": "women",
    "child_welfare": "children",
    "elderly_welfare": "elderly persons",
    "disability_welfare": "persons with disabilities",
    "differently_abled": "persons with disabilities",
    "sc_st_welfare": "SC/ST individuals",
    "obc_welfare": "OBC individuals",
    "bc_welfare": "backward class individuals",
    "minority_welfare": "minority communities",
    "tribal_welfare": "tribal communities",
    "farmer_welfare": "farmers",
}


def _to_int(value) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        logger.warning("Could not coerce value to int: %r", value)
        return None


def _to_float(value) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        logger.warning("Could not coerce value to float: %r", value)
        return None


def _resolve_category(raw_tags: list) -> str:
    tags = set(raw_tags or [])
    if tags & _AGRICULTURE_TAGS:
        category = "agriculture"
    elif tags & _EDUCATION_TAGS:
        category = "education"
    elif tags & _HEALTHCARE_TAGS:
        category = "healthcare"
    elif tags & _EMPLOYMENT_MSME_TAGS:
        category = "employment_msme"
    elif tags & _SOCIAL_WELFARE_TAGS:
        category = "social_welfare"
    else:
        category = "other"
    assert category in _VALID_CATEGORIES
    return category


def _derive_target_beneficiaries(eligibility: dict, raw_tags: list) -> str:
    parts = list((eligibility or {}).get("occupation") or [])
    for tag in raw_tags or []:
        phrase = _TAG_TO_BENEFICIARY_PHRASE.get(tag)
        if phrase and phrase not in parts:
            parts.append(phrase)
    if not parts:
        return "general public"
    return ", ".join(parts)


def normalise_scheme(raw: dict, batch_name: str) -> NormalisedScheme:
    """Converts one raw scheme record into a NormalisedScheme.

    batch_name is the source file's stem (e.g. "schemes_batch_01_central")
    and determines the normalised state: "Central" for batch 01, "Tamil
    Nadu" for batches 02-07, per the ingestion spec.
    """
    eligibility = raw.get("eligibility_structured") or {}
    raw_tags = raw.get("category") or []

    state = "Central" if "01" in batch_name or "central" in batch_name else "Tamil Nadu"

    description = raw.get("short_description") or raw.get("benefit_description") or ""

    required_documents = raw.get("required_documents")
    if not isinstance(required_documents, list):
        required_documents = []

    return NormalisedScheme(
        scheme_id=raw["scheme_id"],
        name=raw.get("name") or "",
        description=description,
        department=raw.get("sponsoring_department") or "",
        state=state,
        category=_resolve_category(raw_tags),
        target_beneficiaries=_derive_target_beneficiaries(eligibility, raw_tags),
        eligibility_notes=raw.get("eligibility_notes") or "",
        required_documents=required_documents,
        citizen_charter_days=_to_int(raw.get("citizen_charter_deadline_days")),
        income_max=_to_int(eligibility.get("max_annual_income_inr")),
        age_min=_to_int(eligibility.get("min_age")),
        age_max=_to_int(eligibility.get("max_age")),
        landholding_max_hectares=_to_float(eligibility.get("max_landholding_hectares")),
        gender=eligibility.get("gender"),
        official_source_url=raw.get("official_source_url") or "",
    )


def build_embedding_text(scheme: NormalisedScheme) -> str:
    """Concatenates the fields most useful for semantic retrieval into one string."""
    return " ".join(
        [
            scheme["name"],
            scheme["description"],
            scheme["target_beneficiaries"],
            scheme["category"],
            scheme["eligibility_notes"],
        ]
    ).strip()

"""Data cleaning, mapping, and legacy conversion."""

import json
import re
from pathlib import Path
from models import Subsidy, generate_slug

MAPPINGS_DIR = Path(__file__).parent / "mappings"

SOURCE_PRIORITY = {"bojokim24": 0, "bizinfo": 1, "gov24": 2, "fallback": 3}


def load_mappings() -> tuple[dict, dict]:
    with open(MAPPINGS_DIR / "categories.json", encoding="utf-8") as f:
        cat_map = json.load(f)
    with open(MAPPINGS_DIR / "regions.json", encoding="utf-8") as f:
        region_map = json.load(f)
    return cat_map, region_map


def normalize_text(value: str | None, default: str = "") -> str:
    if not value or not value.strip():
        return default
    return re.sub(r"\s+", " ", value.strip())


def apply_category_mapping(category: str, cat_map: dict) -> str:
    mapping = cat_map["mapping"]
    default = cat_map["default"]
    if category in mapping:
        return mapping[category]
    if category in mapping.values():
        return category
    return default


def apply_region_mapping(region: str, region_map: dict) -> str:
    mapping = region_map["mapping"]
    if region in mapping:
        return mapping[region]
    return region


def convert_legacy(raw: dict) -> Subsidy:
    gender_raw = raw.get("gender")
    gender = None if gender_raw == "무관" else gender_raw

    return Subsidy(
        id=str(raw["id"]),
        name=raw["name"],
        slug=generate_slug(raw["name"]),
        category=raw["category"],
        description=raw["description"],
        amount=raw["amount"],
        organization=raw["org"],
        region=raw["regions"],
        age_min=raw["min_age"],
        age_max=raw["max_age"],
        gender=gender,
        income_percentile=raw["max_income_percentile"],
        business_types=raw.get("business_types", []),
        deadline=raw.get("deadline"),
        documents=raw.get("required_docs", []),
        url=None,
        source="fallback",
        raw_data=raw,
    )


def _dedup_key(s: Subsidy) -> str:
    name = re.sub(r"[\s\W]", "", s.name).lower()
    org = re.sub(r"[\s\W]", "", s.organization).lower()
    return f"{name}:{org}"


def deduplicate(subsidies: list[Subsidy]) -> list[Subsidy]:
    seen: dict[str, Subsidy] = {}
    for s in subsidies:
        key = _dedup_key(s)
        if key not in seen:
            seen[key] = s
        else:
            existing = seen[key]
            existing_prio = SOURCE_PRIORITY.get(existing.source, 99)
            new_prio = SOURCE_PRIORITY.get(s.source, 99)
            if new_prio < existing_prio:
                seen[key] = s
    return list(seen.values())

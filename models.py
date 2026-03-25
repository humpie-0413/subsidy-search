"""Subsidy data model."""

import re
from dataclasses import dataclass, field, asdict


def generate_slug(name: str) -> str:
    """Generate URL-friendly slug from subsidy name."""
    slug = re.sub(r"[^\w\s가-힣-]", "", name)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    return slug


@dataclass
class Subsidy:
    id: str
    name: str
    slug: str
    category: str
    description: str
    amount: str
    organization: str
    region: list[str]
    age_min: int | None
    age_max: int | None
    gender: str | None
    income_percentile: int | None
    business_types: list[str]
    deadline: str | None
    documents: list[str]
    url: str | None
    source: str
    raw_data: dict = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict:
        """Convert to dict for API responses. Excludes raw_data."""
        d = asdict(self)
        d.pop("raw_data", None)
        return d

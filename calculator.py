"""Income percentile calculation and amount extraction."""

import json
import re
from pathlib import Path

MAPPINGS_DIR = Path(__file__).parent / "mappings"

_THRESHOLDS = None


def _get_thresholds() -> dict:
    global _THRESHOLDS
    if _THRESHOLDS is None:
        with open(MAPPINGS_DIR / "income_thresholds.json", encoding="utf-8") as f:
            _THRESHOLDS = json.load(f)
    return _THRESHOLDS


def calculate_income_percentile(income_monthly: int, household_size: int) -> int:
    if income_monthly <= 0:
        return 0
    thresholds = _get_thresholds()
    key = str(min(household_size, 4))
    median = thresholds["median_income_monthly"][key]
    return round(income_monthly / median * 100)


def extract_amount_number(amount_text: str) -> int | None:
    text = amount_text.replace(",", "")
    m = re.search(r"(\d+)\s*억\s*원?", text)
    if m:
        return int(m.group(1)) * 100000000
    m = re.search(r"(\d+)\s*만\s*원?", text)
    if m:
        return int(m.group(1)) * 10000
    m = re.search(r"(\d{4,})\s*원", text)
    if m:
        return int(m.group(1))
    return None

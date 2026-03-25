# Phase 1: 기반 구축 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the subsidy search service from a Vanilla JS SPA to Jinja2 SSR with public API integration, TTL caching, and basic SEO.

**Architecture:** FastAPI serves Jinja2-rendered HTML pages. Public APIs (보조금24, 기업마당, 정부24) are fetched at server startup and cached in-memory with TTL. Users never wait for API calls — all requests are served from cache. Fallback to hardcoded `data.py` if all sources fail.

**Tech Stack:** FastAPI 0.115.0, Jinja2, aiohttp, python-dotenv, Uvicorn

**Spec:** `docs/superpowers/specs/2026-03-26-subsidy-search-improvement-design.md`

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `models.py` | Subsidy dataclass + slug generation |
| Create | `cache.py` | TTLCache with stale-while-error |
| Create | `data_cleaner.py` | Mapping loader, convert_legacy(), text normalization, dedup |
| Create | `api_client.py` | BaseAPIClient ABC, 3 concrete clients, AggregatedClient |
| Create | `mappings/categories.json` | Category name unification mapping |
| Create | `mappings/regions.json` | Region name unification mapping |
| Create | `templates/base.html` | Shared layout: head (meta/OG), nav, footer, ad slot |
| Create | `templates/index.html` | Main search page extending base |
| Create | `static/css/style.css` | Extracted + cleaned CSS from current index.html |
| Create | `static/js/main.js` | Extracted JS: filters, search, age calc, modal, income guide |
| Create | `seo/sitemap.py` | Dynamic sitemap.xml generation |
| Modify | `main.py` | Jinja2 setup, lifespan, updated routes, SEO endpoints, GZip |
| Modify | `requirements.txt` | Add jinja2, aiohttp, python-dotenv |
| Create | `.env.example` | Document required environment variables |
| Create | `.gitignore` | Exclude __pycache__, .env, etc. |
| Create | `pyproject.toml` | pytest-asyncio config, Python path |
| Create | `tests/test_models.py` | Subsidy model + slug tests |
| Create | `tests/test_cache.py` | TTLCache behavior tests |
| Create | `tests/test_data_cleaner.py` | Mapping, convert_legacy, dedup tests |
| Create | `tests/test_api_client.py` | Normalize + aggregation tests |
| Create | `tests/test_main.py` | Route integration tests |

---

## Task 1: Project Setup & Dependencies

**Files:**
- Modify: `requirements.txt`
- Create: `.env.example`
- Create: `tests/__init__.py`
- Create: `mappings/` directory
- Create: `templates/` directory
- Create: `static/css/` directory
- Create: `static/js/` directory
- Create: `seo/` directory

- [ ] **Step 1: Update requirements.txt**

```
fastapi==0.115.0
uvicorn==0.30.6
jinja2>=3.1.0
aiohttp>=3.9.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx>=0.27.0
```

- [ ] **Step 2: Create .env.example**

```
DATA_GO_KR_API_KEY=your_api_key_here
BIZINFO_API_KEY=your_api_key_here
SITE_DOMAIN=localhost:8000
```

- [ ] **Step 3: Create .gitignore**

```
__pycache__/
*.pyc
.env
*.egg-info/
dist/
build/
.pytest_cache/
```

- [ ] **Step 4: Create pyproject.toml**

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
pythonpath = ["."]
```

- [ ] **Step 5: Create directory structure**

Run:
```bash
mkdir -p mappings templates static/css static/js seo tests
touch tests/__init__.py seo/__init__.py
```

Note: `seo/__init__.py` is an empty file — required for Python package imports.

- [ ] **Step 6: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: All packages install successfully.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .env.example .gitignore pyproject.toml tests/__init__.py seo/__init__.py
git commit -m "chore: add Phase 1 dependencies and directory structure"
```

---

## Task 2: Subsidy Data Model (`models.py`)

**Files:**
- Create: `models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_models.py
from models import Subsidy, generate_slug


def test_generate_slug_basic():
    assert generate_slug("청년 월세 지원") == "청년-월세-지원"


def test_generate_slug_strips_special_chars():
    assert generate_slug("AI/디지털전환 기업 지원금") == "AI디지털전환-기업-지원금"


def test_generate_slug_collapses_dashes():
    assert generate_slug("청년  창업  지원금") == "청년-창업-지원금"


def test_subsidy_creation():
    s = Subsidy(
        id="1",
        name="청년 월세 지원",
        slug="청년-월세-지원",
        category="주거",
        description="월세 지원",
        amount="월 최대 20만원",
        organization="국토교통부",
        region=["서울"],
        age_min=19,
        age_max=34,
        gender=None,
        income_percentile=60,
        business_types=[],
        deadline="2026-08-31",
        documents=["주민등록등본"],
        url=None,
        source="fallback",
        raw_data={},
    )
    assert s.id == "1"
    assert s.name == "청년 월세 지원"
    assert s.gender is None


def test_subsidy_to_dict():
    s = Subsidy(
        id="1", name="테스트", slug="테스트", category="창업",
        description="desc", amount="100만원", organization="org",
        region=["서울"], age_min=19, age_max=39, gender=None,
        income_percentile=100, business_types=[], deadline=None,
        documents=[], url=None, source="fallback", raw_data={},
    )
    d = s.to_dict()
    assert isinstance(d, dict)
    assert d["id"] == "1"
    assert d["name"] == "테스트"
    assert "raw_data" not in d  # raw_data excluded from public dict
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'models'`

- [ ] **Step 3: Implement models.py**

```python
"""Subsidy data model."""

import re
from dataclasses import dataclass, field, asdict


def generate_slug(name: str) -> str:
    """Generate URL-friendly slug from subsidy name.

    Keeps Korean characters, removes special chars, replaces spaces with dashes.
    """
    # Remove special characters except Korean, alphanumeric, spaces, dashes
    slug = re.sub(r"[^\w\s가-힣-]", "", name)
    # Collapse whitespace and replace with dashes
    slug = re.sub(r"\s+", "-", slug.strip())
    # Collapse multiple dashes
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_models.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add models.py tests/test_models.py
git commit -m "feat: add Subsidy dataclass and slug generation"
```

---

## Task 3: TTL Cache (`cache.py`)

**Files:**
- Create: `cache.py`
- Create: `tests/test_cache.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cache.py
import time
from cache import TTLCache


def test_set_and_get():
    cache = TTLCache()
    cache.set("key1", "value1", ttl_seconds=60)
    assert cache.get("key1") == "value1"


def test_get_returns_none_for_missing_key():
    cache = TTLCache()
    assert cache.get("nonexistent") is None


def test_ttl_expiry():
    cache = TTLCache()
    cache.set("key1", "value1", ttl_seconds=1)
    assert cache.get("key1") == "value1"
    time.sleep(1.1)
    assert cache.get("key1") is None


def test_stale_survives_expiry():
    cache = TTLCache()
    cache.set("key1", "value1", ttl_seconds=1)
    time.sleep(1.1)
    assert cache.get("key1") is None
    assert cache.get_stale("key1") == "value1"


def test_stale_updated_on_set():
    cache = TTLCache()
    cache.set("key1", "v1", ttl_seconds=60)
    cache.set("key1", "v2", ttl_seconds=60)
    assert cache.get_stale("key1") == "v2"


def test_clear_expired_removes_from_store_not_stale():
    cache = TTLCache()
    cache.set("key1", "value1", ttl_seconds=1)
    time.sleep(1.1)
    cache.clear_expired()
    assert cache.get("key1") is None
    assert cache.get_stale("key1") == "value1"


def test_invalidate():
    cache = TTLCache()
    cache.set("key1", "value1", ttl_seconds=60)
    cache.invalidate("key1")
    assert cache.get("key1") is None


def test_invalidate_nonexistent_key_no_error():
    cache = TTLCache()
    cache.invalidate("nope")  # should not raise
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cache.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cache'`

- [ ] **Step 3: Implement cache.py**

```python
"""TTL-based in-memory cache with stale-while-error support."""

import time
from typing import Any


class TTLCache:
    def __init__(self):
        self._store: dict[str, tuple[Any, float]] = {}  # key -> (value, expires_at)
        self._stale: dict[str, Any] = {}  # key -> last known value

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            return None
        return value

    def get_stale(self, key: str) -> Any | None:
        return self._stale.get(key)

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        self._store[key] = (value, time.time() + ttl_seconds)
        self._stale[key] = value

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def clear_expired(self) -> None:
        now = time.time()
        expired_keys = [k for k, (_, exp) in self._store.items() if now > exp]
        for k in expired_keys:
            del self._store[k]
        # _stale is NOT cleared — intentional for stale-while-error
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cache.py -v`
Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add cache.py tests/test_cache.py
git commit -m "feat: add TTLCache with stale-while-error support"
```

---

## Task 4: Mapping Files

**Files:**
- Create: `mappings/categories.json`
- Create: `mappings/regions.json`

- [ ] **Step 1: Create mappings/categories.json**

```json
{
  "mapping": {
    "창업지원": "창업",
    "창업육성": "창업",
    "고용촉진": "고용",
    "취업지원": "고용",
    "취업": "고용",
    "주거안정": "주거",
    "전세자금": "주거",
    "농업지원": "농업",
    "경영안정지원": "경영안정",
    "에너지지원": "에너지",
    "수출지원": "수출",
    "기술개발": "기술혁신",
    "복지지원": "복지"
  },
  "default": "기타"
}
```

- [ ] **Step 2: Create mappings/regions.json**

```json
{
  "mapping": {
    "서울특별시": "서울",
    "서울시": "서울",
    "부산광역시": "부산",
    "부산시": "부산",
    "대구광역시": "대구",
    "대구시": "대구",
    "인천광역시": "인천",
    "인천시": "인천",
    "광주광역시": "광주",
    "광주시": "광주",
    "대전광역시": "대전",
    "대전시": "대전",
    "울산광역시": "울산",
    "울산시": "울산",
    "세종특별자치시": "세종",
    "세종시": "세종",
    "경기도": "경기",
    "강원특별자치도": "강원",
    "강원도": "강원",
    "충청북도": "충북",
    "충청남도": "충남",
    "전북특별자치도": "전북",
    "전라북도": "전북",
    "전라남도": "전남",
    "경상북도": "경북",
    "경상남도": "경남",
    "제주특별자치도": "제주",
    "제주도": "제주"
  },
  "default": "전국"
}
```

- [ ] **Step 3: Commit**

```bash
git add mappings/categories.json mappings/regions.json
git commit -m "feat: add category and region mapping files"
```

---

## Task 5: Data Cleaner (`data_cleaner.py`)

**Files:**
- Create: `data_cleaner.py`
- Create: `tests/test_data_cleaner.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_data_cleaner.py
from data_cleaner import (
    load_mappings,
    apply_category_mapping,
    apply_region_mapping,
    normalize_text,
    convert_legacy,
    deduplicate,
)
from models import Subsidy


def test_normalize_text_strips_whitespace():
    assert normalize_text("  hello  world  ") == "hello world"


def test_normalize_text_none_returns_default():
    assert normalize_text(None, default="정보 없음") == "정보 없음"


def test_normalize_text_empty_returns_default():
    assert normalize_text("", default="정보 없음") == "정보 없음"


def test_load_mappings():
    cat_map, region_map = load_mappings()
    assert "창업지원" in cat_map["mapping"]
    assert "서울특별시" in region_map["mapping"]


def test_apply_category_mapping():
    cat_map, _ = load_mappings()
    assert apply_category_mapping("창업지원", cat_map) == "창업"
    assert apply_category_mapping("알수없는카테고리", cat_map) == "기타"
    assert apply_category_mapping("창업", cat_map) == "창업"  # already correct


def test_apply_region_mapping():
    _, region_map = load_mappings()
    assert apply_region_mapping("서울특별시", region_map) == "서울"
    assert apply_region_mapping("서울", region_map) == "서울"  # already short
    assert apply_region_mapping("알수없는지역", region_map) == "알수없는지역"


def test_convert_legacy_basic():
    raw = {
        "id": 1,
        "name": "청년창업지원금",
        "category": "창업",
        "description": "청년 창업 지원",
        "amount": "최대 5,000만원",
        "min_age": 19,
        "max_age": 39,
        "gender": "무관",
        "regions": ["서울", "경기"],
        "max_income_percentile": 100,
        "business_types": ["IT", "제조업"],
        "required_docs": ["사업계획서"],
        "deadline": "2026-06-30",
        "org": "중소벤처기업부",
    }
    s = convert_legacy(raw)
    assert isinstance(s, Subsidy)
    assert s.id == "1"
    assert s.age_min == 19
    assert s.age_max == 39
    assert s.organization == "중소벤처기업부"
    assert s.region == ["서울", "경기"]
    assert s.documents == ["사업계획서"]
    assert s.income_percentile == 100
    assert s.gender is None  # "무관" -> None
    assert s.source == "fallback"
    assert s.slug == "청년창업지원금"
    assert s.business_types == ["IT", "제조업"]


def test_convert_legacy_missing_business_types():
    raw = {
        "id": 2, "name": "테스트", "category": "기타",
        "description": "d", "amount": "a", "min_age": 18,
        "max_age": 65, "gender": "여성", "regions": ["서울"],
        "max_income_percentile": 80, "required_docs": [],
        "deadline": None, "org": "org",
    }
    s = convert_legacy(raw)
    assert s.business_types == []
    assert s.gender == "여성"


def test_deduplicate_keeps_higher_priority():
    s1 = Subsidy(
        id="a1", name="청년 창업 지원금", slug="청년-창업-지원금",
        category="창업", description="d", amount="100만원",
        organization="기관A", region=["서울"], age_min=19, age_max=39,
        gender=None, income_percentile=100, business_types=[],
        deadline=None, documents=[], url=None,
        source="bojokim24", raw_data={},
    )
    s2 = Subsidy(
        id="b2", name="청년 창업 지원금", slug="청년-창업-지원금",
        category="창업", description="d2", amount="200만원",
        organization="기관A", region=["서울"], age_min=19, age_max=39,
        gender=None, income_percentile=100, business_types=[],
        deadline=None, documents=[], url=None,
        source="bizinfo", raw_data={},
    )
    result = deduplicate([s2, s1])  # s1 has higher priority
    assert len(result) == 1
    assert result[0].source == "bojokim24"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_data_cleaner.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'data_cleaner'`

- [ ] **Step 3: Implement data_cleaner.py**

```python
"""Data cleaning, mapping, and legacy conversion."""

import json
import re
from pathlib import Path
from models import Subsidy, generate_slug

MAPPINGS_DIR = Path(__file__).parent / "mappings"

# Source priority for deduplication (lower index = higher priority)
SOURCE_PRIORITY = {"bojokim24": 0, "bizinfo": 1, "gov24": 2, "fallback": 3}


def load_mappings() -> tuple[dict, dict]:
    """Load category and region mapping files. Called once at startup."""
    with open(MAPPINGS_DIR / "categories.json", encoding="utf-8") as f:
        cat_map = json.load(f)
    with open(MAPPINGS_DIR / "regions.json", encoding="utf-8") as f:
        region_map = json.load(f)
    return cat_map, region_map


def normalize_text(value: str | None, default: str = "") -> str:
    """Strip whitespace, collapse spaces. Return default if empty/None."""
    if not value or not value.strip():
        return default
    return re.sub(r"\s+", " ", value.strip())


def apply_category_mapping(category: str, cat_map: dict) -> str:
    """Map API category to unified category. Pass through if already valid."""
    mapping = cat_map["mapping"]
    default = cat_map["default"]
    if category in mapping:
        return mapping[category]
    # Check if already a target value
    if category in mapping.values():
        return category
    return default


def apply_region_mapping(region: str, region_map: dict) -> str:
    """Map API region to short form. Pass through if already short or unknown."""
    mapping = region_map["mapping"]
    if region in mapping:
        return mapping[region]
    # Already short form or unknown — pass through
    return region


def convert_legacy(raw: dict) -> Subsidy:
    """Convert a data.py dict to Subsidy instance. Fallback-only."""
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
    """Normalized key for deduplication: name + organization."""
    name = re.sub(r"[\s\W]", "", s.name).lower()
    org = re.sub(r"[\s\W]", "", s.organization).lower()
    return f"{name}:{org}"


def deduplicate(subsidies: list[Subsidy]) -> list[Subsidy]:
    """Remove duplicates. Higher-priority source wins (Section 5.4)."""
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_data_cleaner.py -v`
Expected: All 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add data_cleaner.py tests/test_data_cleaner.py
git commit -m "feat: add data cleaner with legacy conversion and dedup"
```

---

## Task 6: API Client (`api_client.py`)

**Files:**
- Create: `api_client.py`
- Create: `tests/test_api_client.py`

- [ ] **Step 1: Write failing tests**

Note: These tests mock HTTP calls. We test normalization logic and aggregation, not actual API connectivity.

```python
# tests/test_api_client.py
import pytest
from unittest.mock import AsyncMock, patch
from api_client import (
    BaseAPIClient,
    Bojokim24Client,
    BizinfoClient,
    Gov24Client,
    AggregatedClient,
)
from models import Subsidy


def test_bojokim24_normalize_basic():
    client = Bojokim24Client(api_key="test")
    raw = {
        "BIZ_ID": "B001",
        "BIZ_NM": "청년 창업 지원금",
        "BKCC_NM": "창업지원",
        "BIZ_CN": "청년 대상 창업 지원",
        "SPORT_CN": "최대 5000만원",
        "EXEC_INST": "중소벤처기업부",
        "APPLY_REGION": "서울특별시,부산광역시",
        "AGE_FROM": "19",
        "AGE_TO": "39",
        "GENDER": "",
        "INCOME_LMT": "100",
        "BIZ_TYPE": "IT,제조업",
        "DEADLINE": "2026-06-30",
        "DOCS": "사업계획서,신분증",
        "URL": "https://example.com",
    }
    s = client.normalize(raw)
    assert isinstance(s, Subsidy)
    assert s.id == "B001"
    assert s.source == "bojokim24"
    assert s.organization == "중소벤처기업부"
    assert "서울" in s.region


def test_bizinfo_normalize_basic():
    client = BizinfoClient(api_key="test")
    raw = {
        "pblancId": "BZ001",
        "pblancNm": "소상공인 경영안정자금",
        "jrsdInsttNm": "소상공인시장진흥공단",
        "bsnsSumryCn": "소상공인 대상 융자",
        "sprtAmt": "최대 7000만원",
        "trgtNm": "서울,경기",
        "ageFrom": "",
        "ageTo": "",
        "pblancEndDe": "2026-12-31",
        "detailUrl": "https://bizinfo.go.kr/detail",
    }
    s = client.normalize(raw)
    assert isinstance(s, Subsidy)
    assert s.id == "BZ001"
    assert s.source == "bizinfo"


def test_gov24_normalize_basic():
    client = Gov24Client(api_key="test")
    raw = {
        "서비스ID": "G001",
        "서비스명": "다자녀 양육비 지원",
        "소관기관명": "보건복지부",
        "서비스목적요약": "다자녀 가구 지원",
        "지원내용": "자녀 1인당 연 100만원",
        "선정기준": "",
        "신청기한": "2026-12-31",
        "상세조회URL": "https://gov24.go.kr/detail",
    }
    s = client.normalize(raw)
    assert isinstance(s, Subsidy)
    assert s.id == "G001"
    assert s.source == "gov24"


@pytest.mark.asyncio
async def test_aggregated_client_combines_sources():
    mock_client1 = AsyncMock(spec=BaseAPIClient)
    mock_client2 = AsyncMock(spec=BaseAPIClient)

    s1 = Subsidy(
        id="1", name="보조금A", slug="보조금A", category="창업",
        description="d", amount="a", organization="기관1",
        region=["서울"], age_min=19, age_max=39, gender=None,
        income_percentile=100, business_types=[], deadline=None,
        documents=[], url=None, source="bojokim24", raw_data={},
    )
    s2 = Subsidy(
        id="2", name="보조금B", slug="보조금B", category="고용",
        description="d", amount="a", organization="기관2",
        region=["부산"], age_min=18, age_max=65, gender=None,
        income_percentile=100, business_types=[], deadline=None,
        documents=[], url=None, source="bizinfo", raw_data={},
    )

    mock_client1.fetch_all = AsyncMock(return_value=[{"raw": 1}])
    mock_client1.normalize = lambda raw: s1
    mock_client2.fetch_all = AsyncMock(return_value=[{"raw": 2}])
    mock_client2.normalize = lambda raw: s2

    agg = AggregatedClient(clients=[mock_client1, mock_client2])
    result = await agg.fetch_all_sources()

    assert len(result) == 2
    names = {s.name for s in result}
    assert "보조금A" in names
    assert "보조금B" in names
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_api_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'api_client'`

- [ ] **Step 3: Implement api_client.py**

```python
"""Multi-source public API client for Korean government subsidies."""

import logging
import os
from abc import ABC, abstractmethod

import aiohttp

from data_cleaner import (
    apply_category_mapping,
    apply_region_mapping,
    deduplicate,
    load_mappings,
    normalize_text,
)
from models import Subsidy, generate_slug

logger = logging.getLogger(__name__)

# Lazy-loaded mappings (avoids crash if mapping files are missing at import time)
_CAT_MAP = None
_REGION_MAP = None


def _get_mappings():
    global _CAT_MAP, _REGION_MAP
    if _CAT_MAP is None:
        _CAT_MAP, _REGION_MAP = load_mappings()
    return _CAT_MAP, _REGION_MAP


class BaseAPIClient(ABC):
    """Abstract base for public API clients."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    @abstractmethod
    async def fetch_all(self) -> list[dict]:
        """Fetch all subsidy records (handles pagination)."""
        ...

    @abstractmethod
    def normalize(self, raw: dict) -> Subsidy:
        """Convert raw API dict to Subsidy instance."""
        ...

    async def _fetch_with_retry(
        self, url: str, params: dict, max_retries: int = 3
    ) -> dict | None:
        """HTTP GET with exponential backoff retry."""
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url, params=params, timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp:
                        if resp.status == 200:
                            return await resp.json(content_type=None)
                        logger.warning(
                            "API %s returned %s (attempt %d)",
                            url, resp.status, attempt + 1,
                        )
            except Exception as e:
                logger.warning("API %s error: %s (attempt %d)", url, e, attempt + 1)
            if attempt < max_retries - 1:
                import asyncio
                await asyncio.sleep(2 ** attempt)
        return None


class Bojokim24Client(BaseAPIClient):
    """보조금24 API client (data.go.kr)."""

    BASE_URL = "https://apis.data.go.kr/1210000/BojoGmSvc/getBojoGmList"

    async def fetch_all(self) -> list[dict]:
        records = []
        page = 1
        while True:
            params = {
                "serviceKey": self.api_key,
                "pageNo": page,
                "numOfRows": 100,
                "type": "json",
            }
            data = await self._fetch_with_retry(self.BASE_URL, params)
            if not data:
                break
            try:
                items = data.get("response", {}).get("body", {}).get("items", [])
                if not items:
                    break
                records.extend(items)
                total = int(
                    data.get("response", {}).get("body", {}).get("totalCount", 0)
                )
                if len(records) >= total:
                    break
                page += 1
            except (KeyError, TypeError):
                break
        return records

    def normalize(self, raw: dict) -> Subsidy:
        age_from = raw.get("AGE_FROM", "")
        age_to = raw.get("AGE_TO", "")
        gender_raw = raw.get("GENDER", "")
        regions_raw = raw.get("APPLY_REGION", "")
        biz_types_raw = raw.get("BIZ_TYPE", "")
        docs_raw = raw.get("DOCS", "")
        income_raw = raw.get("INCOME_LMT", "")

        regions = [
            apply_region_mapping(r.strip(), _get_mappings()[1])
            for r in regions_raw.split(",") if r.strip()
        ] if regions_raw else ["전국"]

        return Subsidy(
            id=str(raw.get("BIZ_ID", "")),
            name=normalize_text(raw.get("BIZ_NM", ""), "이름없음"),
            slug=generate_slug(raw.get("BIZ_NM", "")),
            category=apply_category_mapping(
                normalize_text(raw.get("BKCC_NM", ""), "기타"), _get_mappings()[0]
            ),
            description=normalize_text(raw.get("BIZ_CN", ""), "정보 없음"),
            amount=normalize_text(raw.get("SPORT_CN", ""), "정보 없음"),
            organization=normalize_text(raw.get("EXEC_INST", ""), "정보 없음"),
            region=regions,
            age_min=int(age_from) if age_from.isdigit() else None,
            age_max=int(age_to) if age_to.isdigit() else None,
            gender=None if not gender_raw or gender_raw == "무관" else gender_raw,
            income_percentile=int(income_raw) if income_raw.isdigit() else None,
            business_types=[
                b.strip() for b in biz_types_raw.split(",") if b.strip()
            ] if biz_types_raw else [],
            deadline=normalize_text(raw.get("DEADLINE"), None),
            documents=[
                d.strip() for d in docs_raw.split(",") if d.strip()
            ] if docs_raw else [],
            url=raw.get("URL"),
            source="bojokim24",
            raw_data=raw,
        )


class BizinfoClient(BaseAPIClient):
    """기업마당 API client (bizinfo.go.kr)."""

    BASE_URL = "https://www.bizinfo.go.kr/uss/rss/bizApiList.json"

    async def fetch_all(self) -> list[dict]:
        records = []
        page = 1
        while True:
            params = {
                "crtfcKey": self.api_key,
                "pageNo": page,
                "dataRows": 100,
            }
            data = await self._fetch_with_retry(self.BASE_URL, params)
            if not data:
                break
            try:
                items = data.get("jsonArray", [])
                if not items:
                    break
                records.extend(items)
                total = int(data.get("totalCnt", 0))
                if len(records) >= total:
                    break
                page += 1
            except (KeyError, TypeError):
                break
        return records

    def normalize(self, raw: dict) -> Subsidy:
        regions_raw = raw.get("trgtNm", "")
        regions = [
            apply_region_mapping(r.strip(), _get_mappings()[1])
            for r in regions_raw.split(",") if r.strip()
        ] if regions_raw else ["전국"]

        age_from = raw.get("ageFrom", "")
        age_to = raw.get("ageTo", "")

        return Subsidy(
            id=str(raw.get("pblancId", "")),
            name=normalize_text(raw.get("pblancNm", ""), "이름없음"),
            slug=generate_slug(raw.get("pblancNm", "")),
            category=apply_category_mapping("기타", _get_mappings()[0]),
            description=normalize_text(raw.get("bsnsSumryCn", ""), "정보 없음"),
            amount=normalize_text(raw.get("sprtAmt", ""), "정보 없음"),
            organization=normalize_text(raw.get("jrsdInsttNm", ""), "정보 없음"),
            region=regions,
            age_min=int(age_from) if str(age_from).isdigit() else None,
            age_max=int(age_to) if str(age_to).isdigit() else None,
            gender=None,
            income_percentile=None,
            business_types=[],
            deadline=normalize_text(raw.get("pblancEndDe"), None),
            documents=[],
            url=raw.get("detailUrl"),
            source="bizinfo",
            raw_data=raw,
        )


class Gov24Client(BaseAPIClient):
    """정부24 API client (data.go.kr)."""

    BASE_URL = "https://apis.data.go.kr/1741000/publicSvc/getPublicSvcList"

    async def fetch_all(self) -> list[dict]:
        records = []
        page = 1
        while True:
            params = {
                "serviceKey": self.api_key,
                "pageNo": page,
                "numOfRows": 100,
                "type": "json",
            }
            data = await self._fetch_with_retry(self.BASE_URL, params)
            if not data:
                break
            try:
                items = data.get("response", {}).get("body", {}).get("items", [])
                if not items:
                    break
                records.extend(items)
                total = int(
                    data.get("response", {}).get("body", {}).get("totalCount", 0)
                )
                if len(records) >= total:
                    break
                page += 1
            except (KeyError, TypeError):
                break
        return records

    def normalize(self, raw: dict) -> Subsidy:
        return Subsidy(
            id=str(raw.get("서비스ID", "")),
            name=normalize_text(raw.get("서비스명", ""), "이름없음"),
            slug=generate_slug(raw.get("서비스명", "")),
            category=apply_category_mapping("기타", _get_mappings()[0]),
            description=normalize_text(raw.get("서비스목적요약", ""), "정보 없음"),
            amount=normalize_text(raw.get("지원내용", ""), "정보 없음"),
            organization=normalize_text(raw.get("소관기관명", ""), "정보 없음"),
            region=["전국"],
            age_min=None,
            age_max=None,
            gender=None,
            income_percentile=None,
            business_types=[],
            deadline=normalize_text(raw.get("신청기한"), None),
            documents=[],
            url=raw.get("상세조회URL"),
            source="gov24",
            raw_data=raw,
        )


class AggregatedClient:
    """Aggregates multiple API sources with deduplication."""

    def __init__(self, clients: list[BaseAPIClient]):
        self.clients = clients

    async def fetch_all_sources(self) -> list[Subsidy]:
        all_subsidies: list[Subsidy] = []
        for client in self.clients:
            try:
                raw_list = await client.fetch_all()
                for raw in raw_list:
                    try:
                        s = client.normalize(raw)
                        all_subsidies.append(s)
                    except Exception as e:
                        logger.warning("Normalize error in %s: %s", type(client).__name__, e)
            except Exception as e:
                logger.warning("Fetch error in %s: %s", type(client).__name__, e)
        return deduplicate(all_subsidies)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_api_client.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add api_client.py tests/test_api_client.py
git commit -m "feat: add multi-source API client with normalization"
```

---

## Task 7: Static Files — CSS/JS Extraction

**Files:**
- Create: `static/css/style.css`
- Create: `static/js/main.js`

Extract CSS and JS from the current `static/index.html` into separate files. This is a pure extraction — no logic changes.

- [ ] **Step 1: Create static/css/style.css**

Copy all content from the `<style>` block in `static/index.html` (lines 8-126) into `static/css/style.css`. Then add the following `@font-face` at the top of the file for font optimization (spec Section 9):

```css
@font-face {
  font-family: 'Pretendard';
  font-display: swap;
  src: local('Pretendard');
}
```

This ensures the page renders immediately with fallback fonts while Pretendard loads.

- [ ] **Step 2: Create static/js/main.js**

Copy all content from the `<script>` block in `static/index.html` (lines 216-388) into `static/js/main.js`. This is the exact JS from the current file, unchanged.

- [ ] **Step 3: Verify files are accessible**

Run: `python -c "import os; assert os.path.exists('static/css/style.css'); assert os.path.exists('static/js/main.js'); print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add static/css/style.css static/js/main.js
git commit -m "feat: extract CSS and JS into separate static files"
```

---

## Task 8: Jinja2 Templates

**Files:**
- Create: `templates/base.html`
- Create: `templates/index.html`

- [ ] **Step 1: Create templates/base.html**

```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ page_title | default("보조금 조건 검색 서비스") }} | 보조금 검색</title>
<meta name="description" content="{{ page_description | default('나이, 지역, 소득 조건에 맞는 정부 보조금을 검색하세요') }}">
<meta name="robots" content="index, follow">
{% if canonical_url %}<link rel="canonical" href="{{ canonical_url }}">{% endif %}

<!-- Open Graph -->
<meta property="og:title" content="{{ page_title | default('보조금 조건 검색 서비스') }}">
<meta property="og:description" content="{{ page_description | default('나이, 지역, 소득 조건에 맞는 정부 보조금을 검색하세요') }}">
<meta property="og:type" content="{{ og_type | default('website') }}">
{% if canonical_url %}<meta property="og:url" content="{{ canonical_url }}">{% endif %}
<meta property="og:locale" content="ko_KR">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{{ page_title | default('보조금 조건 검색 서비스') }}">
<meta name="twitter:description" content="{{ page_description | default('나이, 지역, 소득 조건에 맞는 정부 보조금을 검색하세요') }}">

<link rel="stylesheet" href="/static/css/style.css">
{% block head_extra %}{% endblock %}
</head>
<body>

<div class="header">
  <h1><a href="/" style="color:inherit;text-decoration:none">보조금 조건 검색 서비스</a></h1>
  <p>나에게 맞는 정부 보조금을 빠르게 찾아보세요</p>
</div>

{% block content %}{% endblock %}

<!-- AdSense slot (activated in Phase 4) -->
{% block adsense %}{% endblock %}

{% block json_ld %}{% endblock %}

<script src="/static/js/main.js"></script>
{% block scripts_extra %}{% endblock %}
</body>
</html>
```

- [ ] **Step 2: Create templates/index.html**

```html
{% extends "base.html" %}

{% block head_extra %}
{% endblock %}

{% block json_ld %}
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "보조금 조건 검색 서비스",
  "url": "{{ canonical_url or '/' }}",
  "potentialAction": {
    "@type": "SearchAction",
    "target": "{{ canonical_url or '/' }}?keyword={search_term_string}",
    "query-input": "required name=search_term_string"
  }
}
</script>
{% endblock %}

{% block content %}
<div class="container">
  <!-- 필터 -->
  <div class="filter-panel">
    <div class="filter-grid">
      <div class="filter-group">
        <label>만 나이
          <span class="label-hint">
            <a href="javascript:void(0)" id="ageToggle" onclick="toggleAgeInput()" style="color:#3b82f6;text-decoration:underline;cursor:pointer">생년월일로 입력</a>
          </span>
        </label>
        <div id="ageDirectWrap">
          <input type="number" id="age" placeholder="예: 30" min="1" max="120">
        </div>
        <div id="ageBirthWrap" style="display:none">
          <input type="date" id="birthDate" onchange="calcAge()" style="width:100%">
          <div id="ageResult" style="font-size:.8rem;color:#3b82f6;margin-top:.3rem"></div>
        </div>
      </div>
      <div class="filter-group">
        <label for="gender">성별</label>
        <select id="gender">
          <option value="">전체</option>
          <option value="남성">남성</option>
          <option value="여성">여성</option>
        </select>
      </div>
      <div class="filter-group">
        <label for="region">지역</label>
        <select id="region"><option value="">전체</option></select>
      </div>
      <div class="filter-group">
        <label for="category">분류</label>
        <select id="category"><option value="">전체</option></select>
      </div>
      <div class="filter-group">
        <label for="businessType">업종</label>
        <select id="businessType"><option value="">전체</option></select>
      </div>
      <div class="filter-group">
        <label for="income">소득분위 <span class="label-hint">(%)</span></label>
        <input type="number" id="income" placeholder="1~100" min="1" max="100">
      </div>
      <div class="filter-group">
        <label for="keyword">키워드</label>
        <input type="text" id="keyword" placeholder="보조금명, 기관명 등">
      </div>
    </div>
    <div class="btn-row">
      <button class="btn btn-primary" onclick="search()">검색</button>
      <button class="btn btn-secondary" onclick="resetFilters()">초기화</button>
      <button class="btn btn-help" onclick="toggleIncomeGuide()">내 소득분위 확인하기</button>
    </div>

    <!-- 소득분위 간이 가이드 -->
    <div class="income-guide" id="incomeGuide">
      <h4>소득분위 간편 확인 가이드</h4>
      <p>소득분위는 전체 가구를 소득 순으로 나눈 비율(%)입니다. 숫자가 낮을수록 소득이 낮습니다.</p>
      <table>
        <tr><th>소득분위</th><th>1인 가구 (월소득)</th><th>4인 가구 (월소득)</th><th>해당 계층</th></tr>
        <tr><td>~30%</td><td>약 130만원 이하</td><td>약 340만원 이하</td><td>기초~차상위</td></tr>
        <tr><td>~50%</td><td>약 220만원 이하</td><td>약 570만원 이하</td><td>중위소득 이하</td></tr>
        <tr><td>~60%</td><td>약 260만원 이하</td><td>약 680만원 이하</td><td>청년 주거 기준</td></tr>
        <tr><td>~70%</td><td>약 310만원 이하</td><td>약 800만원 이하</td><td>복지 확대 기준</td></tr>
        <tr><td>~80%</td><td>약 350만원 이하</td><td>약 910만원 이하</td><td>일반 지원 기준</td></tr>
        <tr><td>~100%</td><td>제한 없음</td><td>제한 없음</td><td>소득 무관</td></tr>
      </table>
      <p class="tip">* 2026년 기준 중위소득 기준 추정치입니다. 정확한 확인은 <strong>복지로(bokjiro.go.kr)</strong> 또는 <strong>건강보험료 조회</strong>로 가능합니다.</p>
    </div>
  </div>

  <!-- 결과 -->
  <div class="result-count" id="resultCount"></div>
  <div id="results"></div>
</div>

<!-- 상세 모달 (Phase 1: retained, replaced in Phase 2 by detail pages) -->
<div class="modal-overlay" id="modal" onclick="closeModal(event)">
  <div class="modal" id="modalContent"></div>
</div>
{% endblock %}
```

- [ ] **Step 3: Commit**

```bash
git add templates/base.html templates/index.html
git commit -m "feat: add Jinja2 base and index templates with SEO meta tags"
```

---

## Task 9: SEO — Sitemap & Robots.txt

**Files:**
- Create: `seo/__init__.py`
- Create: `seo/sitemap.py`
- Create: `tests/test_sitemap.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_sitemap.py
from seo.sitemap import generate_sitemap_xml


def test_sitemap_contains_homepage():
    xml = generate_sitemap_xml(domain="example.com", subsidies=[])
    assert '<?xml version="1.0"' in xml
    assert "<loc>https://example.com/</loc>" in xml


def test_sitemap_is_valid_xml():
    xml = generate_sitemap_xml(domain="example.com", subsidies=[])
    assert "</urlset>" in xml
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_sitemap.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement seo/sitemap.py**

```python
"""Dynamic sitemap.xml generator."""

from datetime import datetime, timezone


def generate_sitemap_xml(domain: str, subsidies: list = None) -> str:
    """Generate sitemap XML string. Subsidies list used for detail page URLs (Phase 2)."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    scheme_domain = f"https://{domain}" if not domain.startswith("http") else domain

    urls = [
        {"loc": f"{scheme_domain}/", "changefreq": "daily", "priority": "1.0"},
        # Phase 2: add /calculator, detail pages
        # Phase 3: add category/region list pages
    ]

    entries = []
    for u in urls:
        entries.append(
            f"  <url>\n"
            f"    <loc>{u['loc']}</loc>\n"
            f"    <lastmod>{now}</lastmod>\n"
            f"    <changefreq>{u['changefreq']}</changefreq>\n"
            f"    <priority>{u['priority']}</priority>\n"
            f"  </url>"
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>"
    )
```

Also create `seo/__init__.py`:
```python
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_sitemap.py -v`
Expected: All 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add seo/__init__.py seo/sitemap.py tests/test_sitemap.py
git commit -m "feat: add dynamic sitemap.xml generator"
```

---

## Task 10: Main.py Rewrite — Integration

**Files:**
- Modify: `main.py`
- Create: `tests/test_main.py`

This is the integration task. Rewrite `main.py` to use Jinja2, lifespan events, cache, and the API client.

- [ ] **Step 1: Write integration tests**

```python
# tests/test_main.py
import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.mark.asyncio
async def test_index_returns_html():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    assert "보조금 조건 검색 서비스" in resp.text
    assert "<title>" in resp.text


@pytest.mark.asyncio
async def test_api_filters():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/filters")
    assert resp.status_code == 200
    data = resp.json()
    assert "regions" in data
    assert "categories" in data


@pytest.mark.asyncio
async def test_api_subsidies():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/subsidies")
    assert resp.status_code == 200
    data = resp.json()
    assert "count" in data
    assert "results" in data
    assert data["count"] > 0


@pytest.mark.asyncio
async def test_api_subsidies_filter_by_age():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/subsidies?age=25")
    assert resp.status_code == 200
    data = resp.json()
    for s in data["results"]:
        assert s["age_min"] <= 25 <= s["age_max"]


@pytest.mark.asyncio
async def test_api_subsidy_detail():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/subsidies/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "1"


@pytest.mark.asyncio
async def test_api_subsidy_detail_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/subsidies/99999")
    assert resp.status_code == 200
    assert "error" in resp.json()


@pytest.mark.asyncio
async def test_robots_txt():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/robots.txt")
    assert resp.status_code == 200
    assert "User-agent" in resp.text
    assert "Disallow: /api/" in resp.text


@pytest.mark.asyncio
async def test_sitemap_xml():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "<?xml" in resp.text
    assert "<urlset" in resp.text


@pytest.mark.asyncio
async def test_static_css_accessible():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/static/css/style.css")
    assert resp.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_main.py -v`
Expected: Multiple failures (old main.py doesn't serve Jinja2, no robots.txt route, etc.)

- [ ] **Step 3: Rewrite main.py**

```python
"""보조금 조건 검색 서비스 — FastAPI 백엔드 (Phase 1)"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional

from api_client import AggregatedClient, Bojokim24Client, BizinfoClient, Gov24Client
from cache import TTLCache
from data import SUBSIDIES as LEGACY_SUBSIDIES
from data_cleaner import convert_legacy
from models import Subsidy
from seo.sitemap import generate_sitemap_xml

load_dotenv()
logger = logging.getLogger(__name__)

# Global state
cache = TTLCache()
templates = Jinja2Templates(directory="templates")


def _get_subsidies() -> list[Subsidy]:
    """Get subsidies from cache, stale cache, or fallback."""
    cached = cache.get("subsidies:list")
    if cached is not None:
        return cached
    stale = cache.get_stale("subsidies:list")
    if stale is not None:
        return stale
    # Fallback to legacy data
    return [convert_legacy(s) for s in LEGACY_SUBSIDIES]


def _build_filters(subsidies: list[Subsidy]) -> dict:
    """Derive filter options from current subsidies list."""
    regions = sorted(set(r for s in subsidies for r in s.region))
    categories = sorted(set(s.category for s in subsidies))
    business_types = sorted(set(b for s in subsidies for b in s.business_types))
    return {
        "regions": regions,
        "categories": categories,
        "business_types": business_types,
        "genders": ["남성", "여성"],
    }


async def _initial_fetch(agg_client: AggregatedClient):
    """Fetch data from all API sources on startup."""
    try:
        subsidies = await agg_client.fetch_all_sources()
        if subsidies:
            cache.set("subsidies:list", subsidies, ttl_seconds=86400)
            logger.info("Loaded %d subsidies from APIs", len(subsidies))
            return
    except Exception as e:
        logger.warning("Initial API fetch failed: %s", e)
    # Fallback
    fallback = [convert_legacy(s) for s in LEGACY_SUBSIDIES]
    cache.set("subsidies:list", fallback, ttl_seconds=86400)
    logger.info("Using %d fallback subsidies", len(fallback))


async def _data_refresh_loop(agg_client: AggregatedClient):
    """24-hour refresh loop (Section 5.3)."""
    while True:
        await asyncio.sleep(86400)
        try:
            subsidies = await agg_client.fetch_all_sources()
            if subsidies:
                cache.set("subsidies:list", subsidies, ttl_seconds=86400)
                logger.info("Refreshed %d subsidies", len(subsidies))
        except Exception as e:
            logger.warning("Refresh failed (stale-while-error active): %s", e)


async def _cache_cleanup_loop():
    """5-minute cache cleanup loop (Section 8.3)."""
    while True:
        await asyncio.sleep(300)
        cache.clear_expired()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: fetch data + launch background loops."""
    data_go_kr_key = os.getenv("DATA_GO_KR_API_KEY", "")
    bizinfo_key = os.getenv("BIZINFO_API_KEY", "")

    clients = []
    if data_go_kr_key:
        clients.append(Bojokim24Client(api_key=data_go_kr_key))
        clients.append(Gov24Client(api_key=data_go_kr_key))
    if bizinfo_key:
        clients.append(BizinfoClient(api_key=bizinfo_key))

    agg_client = AggregatedClient(clients=clients)

    await _initial_fetch(agg_client)

    refresh_task = asyncio.create_task(_data_refresh_loop(agg_client))
    cleanup_task = asyncio.create_task(_cache_cleanup_loop())

    yield

    refresh_task.cancel()
    cleanup_task.cancel()


app = FastAPI(title="보조금 조건 검색 서비스", lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=500)


# --- HTML Routes ---

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    site_domain = os.getenv("SITE_DOMAIN", "")
    canonical = f"https://{site_domain}/" if site_domain else None
    return templates.TemplateResponse("index.html", {
        "request": request,
        "page_title": "보조금 조건 검색 서비스",
        "page_description": "나이, 지역, 소득 조건에 맞는 정부 보조금을 검색하세요",
        "canonical_url": canonical,
        "og_type": "website",
    })


# --- API Routes ---

@app.get("/api/filters")
def get_filters():
    subsidies = _get_subsidies()
    return _build_filters(subsidies)


@app.get("/api/subsidies")
def search_subsidies(
    age: Optional[int] = Query(None),
    gender: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    business_type: Optional[str] = Query(None),
    income_percentile: Optional[int] = Query(None),
    keyword: Optional[str] = Query(None),
):
    results = _get_subsidies()

    if age is not None:
        results = [
            s for s in results
            if (s.age_min is None or s.age_min <= age)
            and (s.age_max is None or age <= s.age_max)
        ]

    if gender:
        results = [s for s in results if s.gender is None or s.gender == gender]

    if region:
        results = [s for s in results if region in s.region]

    if category:
        results = [s for s in results if s.category == category]

    if business_type:
        results = [
            s for s in results
            if not s.business_types or business_type in s.business_types
        ]

    if income_percentile is not None:
        results = [
            s for s in results
            if s.income_percentile is None or income_percentile <= s.income_percentile
        ]

    if keyword:
        kw = keyword.lower()
        results = [
            s for s in results
            if kw in s.name.lower()
            or kw in s.description.lower()
            or kw in s.organization.lower()
        ]

    return {"count": len(results), "results": [s.to_dict() for s in results]}


@app.get("/api/subsidies/{subsidy_id}")
def get_subsidy(subsidy_id: str):
    for s in _get_subsidies():
        if s.id == subsidy_id:
            return s.to_dict()
    return {"error": "보조금을 찾을 수 없습니다"}


# --- SEO Routes ---

@app.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt():
    domain = os.getenv("SITE_DOMAIN", "localhost:8000")
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        f"Sitemap: https://{domain}/sitemap.xml\n"
    )


@app.get("/sitemap.xml")
def sitemap_xml():
    cached = cache.get("seo:sitemap")
    if cached:
        return Response(content=cached, media_type="application/xml")

    domain = os.getenv("SITE_DOMAIN", "localhost:8000")
    subsidies = _get_subsidies()
    xml = generate_sitemap_xml(domain=domain, subsidies=subsidies)
    cache.set("seo:sitemap", xml, ttl_seconds=86400)
    return Response(content=xml, media_type="application/xml")


# --- Static Files (with cache headers per spec Section 9) ---


class CachedStaticFiles(StaticFiles):
    """StaticFiles with Cache-Control header for 7 days."""

    async def __call__(self, scope, receive, send):
        async def send_with_cache(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                headers[b"cache-control"] = b"public, max-age=604800"
                message["headers"] = list(headers.items())
            await send(message)
        await super().__call__(scope, receive, send_with_cache)


app.mount("/static", CachedStaticFiles(directory="static"), name="static")
```

- [ ] **Step 4: Update main.js for new API response format**

The new API changes field names AND `gender` semantics (`"무관"` → `null` in JSON). Apply these changes to `static/js/main.js`:

**In `renderResults` function:**
- `s.org` → `s.organization`
- `s.min_age` → `s.age_min`
- `s.max_age` → `s.age_max`
- `s.regions` → `s.region`

**In `showDetail` function:**
- `s.org` → `s.organization`
- `s.min_age` → `s.age_min`
- `s.max_age` → `s.age_max`
- `s.regions` → `s.region`
- `s.required_docs` → `s.documents`
- `s.max_income_percentile` → `s.income_percentile`
- **CRITICAL: `s.gender === '무관'`** → `!s.gender` (gender is now `null` for unrestricted, not `"무관"`)
- `s.max_income_percentile === 100` → `!s.income_percentile || s.income_percentile >= 100`

**In `genderBadge` function:**
- No changes needed (it checks `"여성"` and `"남성"` which remain the same; `null` falls through to return `""`)

**In `renderResults` card onclick:**
- `showDetail(${s.id})` → `showDetail('${s.id}')` (IDs are now strings, not integers)

- [ ] **Step 5: Run integration tests**

Run: `pytest tests/test_main.py -v`
Expected: All 10 tests PASS.

- [ ] **Step 6: Manual smoke test**

Run: `uvicorn main:app --reload`

Verify in browser:
1. `http://localhost:8000/` — main page renders with filter panel
2. Click "검색" — results load via API
3. Click a card — modal shows detail
4. `http://localhost:8000/robots.txt` — shows robots.txt
5. `http://localhost:8000/sitemap.xml` — shows XML sitemap
6. View page source — meta tags, OG tags, JSON-LD present

- [ ] **Step 7: Commit**

```bash
git add main.py static/js/main.js
git commit -m "feat: rewrite main.py with Jinja2 SSR, caching, lifespan, and SEO routes"
```

---

## Task 11: Cleanup & Full Test Suite

- [ ] **Step 1: Remove old static/index.html**

The old `static/index.html` is now dead code (replaced by Jinja2 templates + separated CSS/JS). Delete it:

Run: `rm static/index.html`

- [ ] **Step 2: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests pass (models: 4, cache: 8, data_cleaner: 9, api_client: 4, sitemap: 2, main: 10 = ~37 tests).

- [ ] **Step 3: Verify no import errors**

Run: `python -c "from main import app; print('Import OK')"`
Expected: `Import OK`

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: cleanup old index.html, finalize Phase 1"
```

---

## Summary

| Task | Component | Tests | Key Files |
|------|-----------|-------|-----------|
| 1 | Project setup | — | requirements.txt, .env.example |
| 2 | Subsidy model | 4 | models.py |
| 3 | TTL cache | 8 | cache.py |
| 4 | Mapping files | — | mappings/*.json |
| 5 | Data cleaner | 9 | data_cleaner.py |
| 6 | API client | 4 | api_client.py |
| 7 | CSS/JS extraction | — | static/css/, static/js/ |
| 8 | Jinja2 templates | — | templates/ |
| 9 | SEO (sitemap) | 2 | seo/sitemap.py |
| 10 | Main.py rewrite | 10 | main.py |
| 11 | Cleanup & full test suite | all | — |

---

## Known Deviations from Spec

1. **`BaseAPIClient.fetch_detail()` omitted** — Spec Section 5.2 defines it, but detail pages are Phase 2. Will be added in Phase 2 plan.
2. **`/calculator` not in sitemap yet** — Calculator is Phase 2. Sitemap URL will be added in Phase 2.
3. **Static file cache headers** use a simple `CachedStaticFiles` wrapper. Phase 3 may replace this with a reverse proxy (Nginx) for production.

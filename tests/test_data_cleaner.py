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
    assert apply_category_mapping("창업", cat_map) == "창업"


def test_apply_region_mapping():
    _, region_map = load_mappings()
    assert apply_region_mapping("서울특별시", region_map) == "서울"
    assert apply_region_mapping("서울", region_map) == "서울"
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
    assert s.gender is None
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
    result = deduplicate([s2, s1])
    assert len(result) == 1
    assert result[0].source == "bojokim24"

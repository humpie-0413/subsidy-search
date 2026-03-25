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
    assert "raw_data" not in d

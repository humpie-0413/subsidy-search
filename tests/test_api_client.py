import pytest
from unittest.mock import AsyncMock
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

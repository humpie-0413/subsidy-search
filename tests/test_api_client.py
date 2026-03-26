import pytest
from unittest.mock import AsyncMock
from api_client import (
    BaseAPIClient,
    Gov24OdcloudClient,
    BizinfoClient,
    AggregatedClient,
)
from models import Subsidy


def test_gov24_odcloud_normalize_basic():
    client = Gov24OdcloudClient(api_key="test")
    raw = {
        "서비스ID": "000000465790",
        "서비스명": "유아학비 (누리과정) 지원",
        "서비스분야": "보육·교육",
        "서비스목적요약": "유치원에 다니는 3~5세 아동에게 유아학비 지원",
        "지원내용": "3~5세에 대해 교육비 지급. 국공립 100,000원, 사립 280,000원",
        "소관기관명": "교육부",
        "신청기한": "상시신청",
        "상세조회URL": "https://www.gov.kr/portal/rcvfvrSvc/dtlEx/000000465790",
    }
    s = client.normalize(raw)
    assert isinstance(s, Subsidy)
    assert s.id == "000000465790"
    assert s.source == "gov24"
    assert s.organization == "교육부"
    assert s.url == "https://www.gov.kr/portal/rcvfvrSvc/dtlEx/000000465790"


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


@pytest.mark.asyncio
async def test_aggregated_client_combines_sources():
    mock_client1 = AsyncMock(spec=BaseAPIClient)
    mock_client2 = AsyncMock(spec=BaseAPIClient)

    s1 = Subsidy(
        id="1", name="보조금A", slug="보조금A", category="창업",
        description="d", amount="a", organization="기관1",
        region=["서울"], age_min=19, age_max=39, gender=None,
        income_percentile=100, business_types=[], deadline=None,
        documents=[], url=None, source="gov24", raw_data={},
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

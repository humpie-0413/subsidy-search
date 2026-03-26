import pytest
from unittest.mock import AsyncMock
from api_client import (
    BaseAPIClient,
    Gov24OdcloudClient,
    BizinfoClient,
    AggregatedClient,
)
from models import Contest, Subsidy


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
        "pldirSportRealmLclasCodeNm": "경영",
        "hashTags": "소상공인,경영,서울,경기,융자",
        "reqstBeginEndDe": "2026-01-01 ~ 2026-12-31",
        "pblancUrl": "https://bizinfo.go.kr/detail",
    }
    s = client.normalize(raw)
    assert isinstance(s, Subsidy)
    assert s.id == "BZ001"
    assert s.source == "bizinfo"
    assert s.name == "소상공인 경영안정자금"
    assert s.category == "경영"
    assert "서울" in s.region
    assert "경기" in s.region
    assert s.deadline == "2026-12-31"
    assert s.url == "https://bizinfo.go.kr/detail"


def test_bizinfo_region_extraction():
    client = BizinfoClient(api_key="test")
    assert client._extract_regions("창업,경영,강원,기업") == ["강원"]
    assert client._extract_regions("서울,부산,대구") == ["서울", "부산", "대구"]
    assert client._extract_regions("") == ["전국"]
    assert client._extract_regions("일반,기타") == ["전국"]


def test_bizinfo_category_mapping():
    client = BizinfoClient(api_key="test")
    assert client._map_category("금융") == "금융"
    assert client._map_category("인력") == "고용"
    assert client._map_category("") == "기타"
    assert client._map_category("알수없는분야") == "기타"


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
    subsidies, contests = await agg.fetch_all_sources()

    assert len(subsidies) == 2
    names = {s.name for s in subsidies}
    assert "보조금A" in names
    assert "보조금B" in names
    assert isinstance(contests, list)


def test_bizinfo_is_contest():
    client = BizinfoClient(api_key="test")
    assert client.is_contest({"pblancNm": "2026 해커톤 대회"}) == "해커톤"
    assert client.is_contest({"pblancNm": "창업 공모전 참가자 모집"}) == "공모"
    assert client.is_contest({"pblancNm": "소상공인 경영안정자금"}) is None
    assert client.is_contest({"pblancNm": "기업교육 프로그램"}) == "교육"


def test_bizinfo_normalize_contest():
    client = BizinfoClient(api_key="test")
    raw = {
        "pblancId": "CONTEST001",
        "pblancNm": "2026 창업 해커톤",
        "jrsdInsttNm": "중소벤처기업부",
        "bsnsSumryCn": "창업 아이디어 경진",
        "hashTags": "창업,서울,해커톤",
        "reqstBeginEndDe": "2026-04-01 ~ 2026-04-30",
        "pblancUrl": "https://example.com/contest",
        "trgetNm": "청년",
    }
    c = client.normalize_contest(raw, "해커톤")
    assert isinstance(c, Contest)
    assert c.id == "CONTEST001"
    assert c.category == "해커톤"
    assert c.source == "bizinfo"
    assert "서울" in c.region
    assert c.target == "청년"
    assert c.deadline == "2026-04-30"

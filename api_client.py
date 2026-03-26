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
from models import Contest, Subsidy, generate_slug

logger = logging.getLogger(__name__)

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
        import asyncio

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
                await asyncio.sleep(2 ** attempt)
        return None


class Gov24OdcloudClient(BaseAPIClient):
    """정부24 보조금 API client (api.odcloud.kr)."""

    BASE_URL = "https://api.odcloud.kr/api/gov24/v3/serviceList"
    MAX_RECORDS = 500

    async def fetch_all(self) -> list[dict]:
        records = []
        page = 1
        per_page = 100
        while True:
            params = {
                "serviceKey": self.api_key,
                "page": page,
                "perPage": per_page,
            }
            data = await self._fetch_with_retry(self.BASE_URL, params)
            if not data:
                break
            try:
                items = data.get("data", [])
                if not items:
                    break
                records.extend(items)
                total = min(int(data.get("totalCount", 0)), self.MAX_RECORDS)
                if len(records) >= total:
                    break
                page += 1
            except (KeyError, TypeError):
                break
        return records[:self.MAX_RECORDS]

    def normalize(self, raw: dict) -> Subsidy:
        cat_map, region_map = _get_mappings()
        raw_category = normalize_text(raw.get("서비스분야", ""), "기타")
        deadline_raw = normalize_text(raw.get("신청기한"), None)

        return Subsidy(
            id=str(raw.get("서비스ID", "")),
            name=normalize_text(raw.get("서비스명", ""), "이름없음"),
            slug=generate_slug(raw.get("서비스명", "")),
            category=apply_category_mapping(raw_category, cat_map),
            description=normalize_text(raw.get("서비스목적요약", ""), "정보 없음"),
            amount=normalize_text(raw.get("지원내용", ""), "정보 없음"),
            organization=normalize_text(raw.get("소관기관명", ""), "정보 없음"),
            region=["전국"],
            age_min=None,
            age_max=None,
            gender=None,
            income_percentile=None,
            business_types=[],
            deadline=deadline_raw,
            documents=[],
            url=raw.get("상세조회URL"),
            source="gov24",
            raw_data=raw,
        )


class BizinfoClient(BaseAPIClient):
    """기업마당 API client (bizinfo.go.kr)."""

    BASE_URL = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"

    # 17 시도 names for hashtag region extraction
    KNOWN_REGIONS = {
        "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
        "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
    }

    # 기업마당 분야 → 서비스 카테고리
    CATEGORY_MAP = {
        "금융": "금융",
        "기술": "기술",
        "인력": "고용",
        "수출": "수출",
        "내수": "내수",
        "창업": "창업",
        "경영": "경영",
        "기타": "기타",
    }

    # Keywords to classify an item as a contest/event
    CONTEST_KEYWORDS = [
        "공모", "해커톤", "경진대회", "챌린지", "대회",
        "세미나", "컨퍼런스", "포럼", "워크숍",
        "교육", "강좌", "특강", "아카데미", "캠프",
        "멘토링",
    ]

    # Contest keyword → category mapping
    CONTEST_CATEGORY_MAP = {
        "공모": "공모전", "해커톤": "해커톤", "경진대회": "공모전",
        "챌린지": "공모전", "대회": "공모전",
        "세미나": "세미나", "컨퍼런스": "세미나", "포럼": "세미나",
        "워크숍": "세미나",
        "교육": "교육", "강좌": "교육", "특강": "교육",
        "아카데미": "교육", "캠프": "교육",
        "멘토링": "멘토링",
    }

    async def fetch_all(self) -> list[dict]:
        params = {
            "crtfcKey": self.api_key,
            "dataType": "json",
            "searchCnt": 0,
        }
        data = await self._fetch_with_retry(self.BASE_URL, params)
        if not data:
            return []
        try:
            items = data.get("jsonArray", [])
            return items if items else []
        except (KeyError, TypeError):
            return []

    def _extract_regions(self, hashtags: str) -> list[str]:
        """Extract known region names from comma-separated hashtags."""
        if not hashtags:
            return ["전국"]
        parts = [p.strip() for p in hashtags.split(",")]
        regions = [p for p in parts if p in self.KNOWN_REGIONS]
        return regions if regions else ["전국"]

    def _map_category(self, raw_category: str) -> str:
        """Map 기업마당 category to service category."""
        if not raw_category:
            return "기타"
        for key, val in self.CATEGORY_MAP.items():
            if key in raw_category:
                return val
        return "기타"

    def _extract_deadline(self, raw: dict) -> str | None:
        """Extract deadline from reqstBeginEndDe or pblancEndDe."""
        date_str = raw.get("reqstBeginEndDe") or raw.get("pblancEndDe") or ""
        if not date_str or not date_str.strip():
            return None
        parts = date_str.strip().split("~")
        return parts[-1].strip() if parts[-1].strip() else None

    def is_contest(self, raw: dict) -> str | None:
        """Check if item is a contest/event. Returns matched keyword or None."""
        name = raw.get("pblancNm") or raw.get("title", "")
        sub_cat = raw.get("pldirSportRealmMlsfcCodeNm", "")
        hashtags = raw.get("hashTags") or raw.get("hashtags", "")
        combined = f"{name} {sub_cat} {hashtags}"
        for kw in self.CONTEST_KEYWORDS:
            if kw in combined:
                return kw
        return None

    def normalize(self, raw: dict) -> Subsidy:
        name = normalize_text(
            raw.get("pblancNm") or raw.get("title", ""), "이름없음"
        )
        description = normalize_text(
            raw.get("bsnsSumryCn") or raw.get("description", ""), "정보 없음"
        )
        organization = normalize_text(
            raw.get("jrsdInsttNm") or raw.get("author", ""), "정보 없음"
        )
        raw_category = raw.get("pldirSportRealmLclasCodeNm") or raw.get("lcategory", "")
        hashtags = raw.get("hashTags") or raw.get("hashtags", "")
        url = raw.get("pblancUrl") or raw.get("link")

        return Subsidy(
            id=str(raw.get("pblancId", "")),
            name=name,
            slug=generate_slug(name),
            category=self._map_category(raw_category),
            description=description,
            amount="정보 없음",
            organization=organization,
            region=self._extract_regions(hashtags),
            age_min=None,
            age_max=None,
            gender=None,
            income_percentile=None,
            business_types=[],
            deadline=self._extract_deadline(raw),
            documents=[],
            url=url,
            source="bizinfo",
            raw_data=raw,
        )

    def normalize_contest(self, raw: dict, matched_keyword: str) -> Contest:
        """Convert raw API dict to Contest instance."""
        name = normalize_text(
            raw.get("pblancNm") or raw.get("title", ""), "이름없음"
        )
        description = normalize_text(
            raw.get("bsnsSumryCn") or raw.get("description", ""), "정보 없음"
        )
        organization = normalize_text(
            raw.get("jrsdInsttNm") or raw.get("author", ""), "정보 없음"
        )
        hashtags = raw.get("hashTags") or raw.get("hashtags", "")
        url = raw.get("pblancUrl") or raw.get("link")
        target = normalize_text(raw.get("trgetNm"), None)
        category = self.CONTEST_CATEGORY_MAP.get(matched_keyword, "기타")

        return Contest(
            id=str(raw.get("pblancId", "")),
            name=name,
            slug=generate_slug(name),
            category=category,
            description=description,
            organization=organization,
            region=self._extract_regions(hashtags),
            deadline=self._extract_deadline(raw),
            url=url,
            target=target,
            source="bizinfo",
            raw_data=raw,
        )


class AggregatedClient:
    """Aggregates multiple API sources with deduplication."""

    def __init__(self, clients: list[BaseAPIClient]):
        self.clients = clients

    async def fetch_all_sources(self) -> tuple[list[Subsidy], list[Contest]]:
        all_subsidies: list[Subsidy] = []
        all_contests: list[Contest] = []
        for client in self.clients:
            try:
                raw_list = await client.fetch_all()
                for raw in raw_list:
                    try:
                        # BizinfoClient can distinguish contests from subsidies
                        if isinstance(client, BizinfoClient):
                            kw = client.is_contest(raw)
                            if kw:
                                c = client.normalize_contest(raw, kw)
                                all_contests.append(c)
                                continue
                        s = client.normalize(raw)
                        all_subsidies.append(s)
                    except Exception as e:
                        logger.warning("Normalize error in %s: %s", type(client).__name__, e)
            except Exception as e:
                logger.warning("Fetch error in %s: %s", type(client).__name__, e)
        return deduplicate(all_subsidies), all_contests

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

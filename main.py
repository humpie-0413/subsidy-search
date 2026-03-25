"""보조금 조건 검색 서비스 — FastAPI 백엔드 (Phase 1)"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
    fallback = [convert_legacy(s) for s in LEGACY_SUBSIDIES]
    cache.set("subsidies:list", fallback, ttl_seconds=86400)
    logger.info("Using %d fallback subsidies", len(fallback))


async def _data_refresh_loop(agg_client: AggregatedClient):
    """24-hour refresh loop."""
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
    """5-minute cache cleanup loop."""
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
    return templates.TemplateResponse(request, "index.html", {
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


# --- Static Files ---

app.mount("/static", StaticFiles(directory="static"), name="static")

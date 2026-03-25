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

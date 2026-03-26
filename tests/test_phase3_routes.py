import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.mark.asyncio
async def test_category_page_renders():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/category/창업")
    assert resp.status_code == 200
    assert "창업" in resp.text
    assert "<title>" in resp.text


@pytest.mark.asyncio
async def test_category_page_has_itemlist_schema():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/category/창업")
    assert "ItemList" in resp.text


@pytest.mark.asyncio
async def test_category_page_has_subsidy_links():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/category/창업")
    assert "/subsidies/" in resp.text
    assert 'class="list-card"' in resp.text


@pytest.mark.asyncio
async def test_category_page_empty():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/category/존재하지않는카테고리")
    assert resp.status_code == 200
    assert "0건" in resp.text


@pytest.mark.asyncio
async def test_region_page_renders():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/region/서울")
    assert resp.status_code == 200
    assert "서울" in resp.text
    assert "<title>" in resp.text


@pytest.mark.asyncio
async def test_region_page_has_itemlist_schema():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/region/서울")
    assert "ItemList" in resp.text


@pytest.mark.asyncio
async def test_region_page_has_subsidy_links():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/region/서울")
    assert "/subsidies/" in resp.text
    assert 'class="list-card"' in resp.text


@pytest.mark.asyncio
async def test_region_page_empty():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/region/존재하지않는지역")
    assert resp.status_code == 200
    assert "0건" in resp.text

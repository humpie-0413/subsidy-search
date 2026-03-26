import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.mark.asyncio
async def test_detail_page_renders():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/subsidies/1/청년창업지원금")
    assert resp.status_code == 200
    assert "청년창업지원금" in resp.text
    assert "<title>" in resp.text


@pytest.mark.asyncio
async def test_detail_page_wrong_slug_redirects():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
        resp = await client.get("/subsidies/1/wrong-slug")
    assert resp.status_code == 301


@pytest.mark.asyncio
async def test_detail_page_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/subsidies/99999/없는보조금")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_detail_page_has_faq_schema():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/subsidies/1/청년창업지원금")
    assert "FAQPage" in resp.text
    assert "GovernmentService" in resp.text


@pytest.mark.asyncio
async def test_detail_page_has_internal_links():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/subsidies/1/청년창업지원금")
    assert 'class="related-card"' in resp.text

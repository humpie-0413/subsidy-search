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


@pytest.mark.asyncio
async def test_calculator_page_renders():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/calculator")
    assert resp.status_code == 200
    assert "계산기" in resp.text
    assert "WebApplication" in resp.text


@pytest.mark.asyncio
async def test_calculator_with_params_shows_results():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/calculator?age=25&region=서울&income=200&household=1")
    assert resp.status_code == 200
    assert "결과" in resp.text or "매칭" in resp.text


@pytest.mark.asyncio
async def test_calculator_no_params_shows_form():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/calculator")
    assert resp.status_code == 200
    assert "나이" in resp.text

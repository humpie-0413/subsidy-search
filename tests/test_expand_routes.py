"""Tests for expanded routes: contests, youth, midlife pages."""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_contests_page_renders():
    resp = client.get("/contests")
    assert resp.status_code == 200
    assert "공모전" in resp.text


def test_contests_page_with_category_filter():
    resp = client.get("/contests?category=교육")
    assert resp.status_code == 200


def test_contests_page_with_region_filter():
    resp = client.get("/contests?region=서울")
    assert resp.status_code == 200


def test_contest_detail_not_found():
    resp = client.get("/contests/nonexistent/slug")
    assert resp.status_code == 404


def test_contest_category_page():
    resp = client.get("/contests/category/교육")
    assert resp.status_code == 200


def test_youth_page_renders():
    resp = client.get("/youth")
    assert resp.status_code == 200
    assert "청년" in resp.text


def test_youth_page_has_calculator_link():
    resp = client.get("/youth")
    assert "/calculator" in resp.text


def test_midlife_page_renders():
    resp = client.get("/midlife")
    assert resp.status_code == 200
    assert "중장년" in resp.text


def test_midlife_page_has_calculator_link():
    resp = client.get("/midlife")
    assert "/calculator" in resp.text


def test_api_contests():
    resp = client.get("/api/contests")
    assert resp.status_code == 200
    data = resp.json()
    assert "count" in data
    assert "results" in data


def test_api_contests_with_keyword():
    resp = client.get("/api/contests?keyword=교육")
    assert resp.status_code == 200


def test_nav_has_all_links():
    resp = client.get("/")
    assert "/contests" in resp.text
    assert "/youth" in resp.text
    assert "/midlife" in resp.text
    assert "/calculator" in resp.text


def test_branding_updated():
    resp = client.get("/")
    assert "기회 검색" in resp.text


def test_sitemap_includes_new_pages():
    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "/contests" in resp.text
    assert "/youth" in resp.text
    assert "/midlife" in resp.text

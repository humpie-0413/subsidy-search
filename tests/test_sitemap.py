from seo.sitemap import generate_sitemap_xml
from models import Subsidy


def test_sitemap_contains_homepage():
    xml = generate_sitemap_xml(domain="example.com", subsidies=[])
    assert '<?xml version="1.0"' in xml
    assert "<loc>https://example.com/</loc>" in xml


def test_sitemap_is_valid_xml():
    xml = generate_sitemap_xml(domain="example.com", subsidies=[])
    assert "</urlset>" in xml


def test_sitemap_includes_detail_pages():
    subsidies = [
        Subsidy(
            id="1", name="테스트 보조금", slug="테스트-보조금", category="창업",
            description="d", amount="a", organization="org", region=["서울"],
            age_min=19, age_max=39, gender=None, income_percentile=100,
            business_types=[], deadline=None, documents=[], url=None,
            source="fallback", raw_data={},
        ),
    ]
    xml = generate_sitemap_xml(domain="example.com", subsidies=subsidies)
    assert "/subsidies/1/" in xml


def test_sitemap_includes_calculator():
    xml = generate_sitemap_xml(domain="example.com", subsidies=[])
    assert "/calculator" in xml

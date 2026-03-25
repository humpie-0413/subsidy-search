from seo.sitemap import generate_sitemap_xml


def test_sitemap_contains_homepage():
    xml = generate_sitemap_xml(domain="example.com", subsidies=[])
    assert '<?xml version="1.0"' in xml
    assert "<loc>https://example.com/</loc>" in xml


def test_sitemap_is_valid_xml():
    xml = generate_sitemap_xml(domain="example.com", subsidies=[])
    assert "</urlset>" in xml

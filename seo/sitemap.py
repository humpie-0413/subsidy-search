"""Dynamic sitemap.xml generator."""

from datetime import datetime, timezone


def generate_sitemap_xml(domain: str, subsidies: list = None) -> str:
    """Generate sitemap XML string. Subsidies list used for detail page URLs (Phase 2)."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    scheme_domain = f"https://{domain}" if not domain.startswith("http") else domain

    urls = [
        {"loc": f"{scheme_domain}/", "changefreq": "daily", "priority": "1.0"},
    ]

    entries = []
    for u in urls:
        entries.append(
            f"  <url>\n"
            f"    <loc>{u['loc']}</loc>\n"
            f"    <lastmod>{now}</lastmod>\n"
            f"    <changefreq>{u['changefreq']}</changefreq>\n"
            f"    <priority>{u['priority']}</priority>\n"
            f"  </url>"
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>"
    )

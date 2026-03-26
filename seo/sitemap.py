"""Dynamic sitemap.xml generator."""

from datetime import datetime, timezone


def generate_sitemap_xml(domain: str, subsidies: list = None) -> str:
    """Generate sitemap XML with homepage, calculator, listings, and detail pages."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    scheme_domain = f"https://{domain}" if not domain.startswith("http") else domain

    urls = [
        {"loc": f"{scheme_domain}/", "changefreq": "daily", "priority": "1.0"},
        {"loc": f"{scheme_domain}/calculator", "changefreq": "weekly", "priority": "0.9"},
    ]

    if subsidies:
        # Category and region listing pages
        categories = sorted(set(s.category for s in subsidies))
        regions = sorted(set(r for s in subsidies for r in s.region))

        for cat in categories:
            urls.append({
                "loc": f"{scheme_domain}/category/{cat}",
                "changefreq": "weekly",
                "priority": "0.8",
            })
        for reg in regions:
            urls.append({
                "loc": f"{scheme_domain}/region/{reg}",
                "changefreq": "weekly",
                "priority": "0.8",
            })

        # Detail pages
        for s in subsidies:
            urls.append({
                "loc": f"{scheme_domain}/subsidies/{s.id}/{s.slug}",
                "changefreq": "weekly",
                "priority": "0.7",
            })

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

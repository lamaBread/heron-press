"""sitemap.xml generator (sitemaps.org 0.9 schema; static XML, no client side).

Included URLs:
  - home (`/`)
  - top-level category indexes (`/{cat-slug}/`)
  - subcategory indexes (`/{top-slug}/{sub-slug}/`)
  - articles (`/{slug}/`) — every article without `noindex: true`

Excluded:
  - `search.php` (noindex,follow), `404.html`, `/assets/` (not content),
    and any article with `noindex: true`.

lastmod rules:
  - article: `updated` if present, else `date`.
  - category (top or sub): max lastmod over its subtree's non-noindex articles.
  - home: max lastmod over articles actually shown on the home page (i.e.
    non-noindex articles not under Articles/meta.yaml's excludes_categories).

`changefreq` / `priority` are intentionally omitted — Google ignores both, and
an inaccurate priority only hurts trust.
"""
from xml.sax.saxutils import escape as _xml_escape


def _article_lastmod(article) -> str:
    return article.meta.updated or article.meta.date


def _collect_indexable(cat) -> list:
    """All non-noindex articles in a category subtree."""
    result = [a for a in cat.articles if not a.meta.noindex]
    for child in cat.children:
        result.extend(_collect_indexable(child))
    return result


def build_sitemap(articles, categories, site, home_meta) -> str:
    """Return the sitemap.xml body (utf-8).

    Arguments map to Builder.articles / .categories / .site / .home_meta.
    home_meta is the single source for the home-excluded category list.
    """
    base_url = site.base_url.rstrip('/')
    exclude_top = set(home_meta.excludes_categories)

    indexable = [a for a in articles if not a.meta.noindex]

    entries = []  # [(loc, lastmod_or_None)]

    home_visible = [
        a for a in indexable
        if not (a.category_path and a.category_path[0] in exclude_top)
    ]
    home_lastmod = max(
        (_article_lastmod(a) for a in home_visible), default=None,
    )
    entries.append((f'{base_url}/', home_lastmod))

    # Top-level and subcategories alike, sorted by slug_path lexicographically.
    all_cats = sorted(
        categories.values(),
        key=lambda c: (len(c.slug_path), c.slug_path),
    )
    for cat in all_cats:
        subtree = _collect_indexable(cat)
        if not subtree:
            continue
        lastmod = max(_article_lastmod(a) for a in subtree)
        cat_url = base_url + '/' + '/'.join(cat.slug_path) + '/'
        entries.append((cat_url, lastmod))

    for article in sorted(indexable, key=lambda a: a.meta.slug):
        entries.append((
            f'{base_url}/{article.meta.slug}/',
            _article_lastmod(article),
        ))

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc, lastmod in entries:
        lines.append('  <url>')
        lines.append(f'    <loc>{_xml_escape(loc)}</loc>')
        if lastmod:
            lines.append(f'    <lastmod>{lastmod}</lastmod>')
        lines.append('  </url>')
    lines.append('</urlset>')
    return '\n'.join(lines) + '\n'

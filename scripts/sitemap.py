"""sitemap.xml 생성기 (v0.4.4 신설; v0.4.5 에서 서브카테고리 URL 포함).

sitemaps.org 0.9 스키마. 클라이언트 측 처리 없는 정적 XML 파일.

포함되는 URL:
  - 홈 (`/`)
  - 톱레벨 카테고리 인덱스 (`/{cat-slug}/`)
  - 서브카테고리 인덱스 (`/{top-slug}/{sub-slug}/`) — v0.4.5 부터 포함.
    v0.4.4 까지는 서브카테고리에 인덱스 페이지가 없었기 때문에 sitemap 에서도
    제외했지만, v0.4.5 에서 서브카테고리 인덱스 페이지를 신설하면서 sitemap
    에도 추가한다.
  - 글 (`/{slug}/`) — meta.yaml 의 `noindex: true` 가 아닌 모든 글.

제외되는 페이지:
  - `search.php` — v0.4.2 부터 noindex,follow 정책 (`?q=…` 노이즈 차단).
  - `404.html` — 에러 페이지.
  - `/assets/` — 사이트 공용 자원 디렉터리 (콘텐츠가 아님). v0.5.2 부터
    글 자산이 `/{slug}/` 안에 들어가지만, sitemap 은 글 인덱스 페이지
    (`/{slug}/`) 만 등록하고 자산 파일은 등록 대상이 아님.
  - meta.yaml 에 `noindex: true` 가 있는 글.

lastmod 결정 규칙:
  - 글: `updated` 가 있으면 그 값, 없으면 `date`.
  - 카테고리 (톱레벨 또는 서브): 그 서브트리의 (non-noindex) 글 lastmod 중 최댓값.
  - 홈: 홈 페이지에 실제로 노출되는 글 (즉 Articles/meta.yaml 의
        excludes_categories 에 들지 않은 non-noindex 글) 의 lastmod 중 최댓값.

v0.4.6 변경:
  - 홈 제외 카테고리 목록의 출처가 site.home_excludes_categories →
    home_meta.excludes_categories (= Articles/meta.yaml) 로 이전.
    build_sitemap 시그니처에 home_meta 매개변수 추가.

`changefreq` / `priority` 는 일부러 비움 — Google 은 두 필드를 무시한다고
공식적으로 밝혔고, 부정확한 priority 는 오히려 신뢰도를 떨어뜨림.
"""
from xml.sax.saxutils import escape as _xml_escape


def _article_lastmod(article) -> str:
    return article.meta.updated or article.meta.date


def _collect_indexable(cat) -> list:
    """카테고리 서브트리의 non-noindex 글 모두 수집."""
    result = [a for a in cat.articles if not a.meta.noindex]
    for child in cat.children:
        result.extend(_collect_indexable(child))
    return result


def build_sitemap(articles, categories, site, home_meta) -> str:
    """sitemap.xml 본문 문자열 (utf-8) 반환.

    매개변수는 builder.Builder 의 self.articles / self.categories / self.site
    / self.home_meta 를 그대로 받는다. v0.4.6 부터 home_meta 가 필수 인자
    (홈 제외 카테고리 목록의 단일 진실 source).
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

    # v0.4.5: 톱레벨 + 서브카테고리 모두 포함. 정렬은 slug_path 사전식.
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

"""SEO meta 태그 빌더 (§ 5).

v0.4.0 변경:
  - seo_keywords 필드 제거. <meta name="keywords"> 는 검색엔진 가중치에
    실효가 없어 1990년대 흔적이라 판단.
  - 글마다 noindex 를 meta.yaml 에서 켤 수 있음 (article 템플릿이
    ROBOTS_META placeholder 를 표시).
"""
from .models import RenderResult, SiteConfig


def _truncate(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[:max_len].rstrip() + '…'


def build_meta_tags(article, rr: RenderResult, site: SiteConfig) -> tuple:
    """Returns (meta_tags_html, full_title_str)."""
    m = article.meta

    prefix = m.seo_title_prefix if m.seo_title_prefix is not None else site.default_title_prefix
    suffix = m.seo_title_suffix if m.seo_title_suffix is not None else site.default_title_suffix
    full_title = f'{prefix}{m.title}{suffix}'

    desc = m.seo_description
    if not desc and rr.first_paragraph:
        desc = _truncate(rr.first_paragraph, site.description_truncate)

    canonical = m.seo_canonical or f'{site.base_url}/{m.slug}/'

    og_image_raw = m.seo_og_image
    if not og_image_raw and rr.first_image:
        og_image_raw = rr.first_image
    og_image = og_image_raw or site.default_og_image
    if og_image and not og_image.startswith('http'):
        og_image = site.base_url + og_image

    og_title = m.seo_og_title or full_title
    og_desc = m.seo_og_description or desc or ''
    og_image_alt = m.seo_og_image_alt or m.title
    tw_image = m.seo_twitter_image or og_image

    def e(s):
        return (s or '').replace('&', '&amp;').replace('"', '&quot;')

    tags = []

    if desc:
        tags.append(f'<meta name="description" content="{e(desc)}">')

    author = m.seo_author or site.default_author
    if author:
        tags.append(f'<meta name="author" content="{e(author)}">')

    tags.append(f'<link rel="canonical" href="{e(canonical)}">')

    tags.append(f'<meta property="og:title" content="{e(og_title)}">')
    if og_desc:
        tags.append(f'<meta property="og:description" content="{e(og_desc)}">')
    if og_image:
        tags.append(f'<meta property="og:image" content="{e(og_image)}">')
        tags.append(f'<meta property="og:image:alt" content="{e(og_image_alt)}">')
    og_type = m.seo_og_type or 'article'
    tags.append(f'<meta property="og:type" content="{e(og_type)}">')
    tags.append(f'<meta property="og:url" content="{e(canonical)}">')
    tags.append(f'<meta property="og:site_name" content="{e(site.name)}">')
    tags.append(f'<meta property="article:published_time" content="{e(m.date)}">')
    modified = m.updated or m.date
    tags.append(f'<meta property="article:modified_time" content="{e(modified)}">')

    tw_card = m.seo_twitter_card or 'summary_large_image'
    tags.append(f'<meta name="twitter:card" content="{e(tw_card)}">')
    tags.append(f'<meta name="twitter:title" content="{e(og_title)}">')
    if og_desc:
        tags.append(f'<meta name="twitter:description" content="{e(og_desc)}">')
    if tw_image:
        tags.append(f'<meta name="twitter:image" content="{e(tw_image)}">')

    return '\n    '.join(tags), full_title

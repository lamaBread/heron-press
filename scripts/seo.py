"""SEO meta 태그 빌더 (§ 5).

v0.5.4 변경:
  - `truncate_description` (구 `_truncate`) 가 영문 단어 경계를 존중. 절단
    지점이 ASCII alphanumeric/하이픈/언더스코어 시퀀스 한가운데 (= 양쪽 모두
    Latin 단어 글자) 이면 직전 공백까지 backup. 한국어/한자/일본어 등 CJK
    는 글자 단위가 의미 단위라 영향 없음 (`isascii()` 통과 못함). 빌더의
    article_render_meta 캐시 (gallery / feed 가 참조) 도 같은 함수를 import 해서
    중복 로직 제거.

v0.4.3 변경:
  - meta.yaml 의 평면 seo_* 필드 → SeoMeta dataclass (`m.seo.*`).
  - <title> 에 들어가는 full_title 을 builder 가 정상 사용 (이전엔
    site.name 으로 덮어쓰던 quirk 제거).

v0.4.0 변경:
  - seo_keywords 필드 제거. <meta name="keywords"> 는 검색엔진 가중치에
    실효가 없어 1990년대 흔적이라 판단.
  - 글마다 noindex 를 meta.yaml 에서 켤 수 있음 (article 템플릿이
    ROBOTS_META placeholder 를 표시).
"""
import re

from .models import RenderResult, SiteConfig


def _is_latin_word_char(c: str) -> bool:
    """ASCII 영문/숫자/'-'/'_' 인지. 한글·한자·일본어 등 CJK 글자는 False."""
    return bool(c) and c.isascii() and (c.isalnum() or c in '-_')


def truncate_description(s: str, max_len: int) -> str:
    """`s` 를 `max_len` 글자로 절단. 영문 단어를 한가운데 자르지 않는다.

    절단 지점이 ASCII Latin 단어 (영문/숫자/하이픈/언더스코어 시퀀스) 한가운데
    이면 직전 공백까지 backup. 한국어 등 CJK 글자는 글자 단위가 의미 단위라
    그대로 절단 가능 (Latin 단어 검사를 통과하지 못한다).

    백업해도 공백을 찾지 못하면 (예: max_len 안이 단일 영문 단어 하나뿐인
    극단적 케이스) 그냥 원래 절단 지점에서 자른다 — 무한 폴백을 만들지 않기 위함.

    절단이 일어난 경우 우측의 trailing whitespace 를 제거하고 '…' 를 붙인다.
    """
    if len(s) <= max_len:
        return s
    cut = s[:max_len]
    c_before = cut[-1] if cut else ''
    c_after = s[max_len] if max_len < len(s) else ''
    if _is_latin_word_char(c_before) and _is_latin_word_char(c_after):
        m = re.search(r'^(.*\s)\S+$', cut, re.DOTALL)
        if m:
            cut = m.group(1)
    return cut.rstrip() + '…'


# v0.5.4 이전과 호환되는 내부 이름. seo.py 내부 호출용.
_truncate = truncate_description


def build_meta_tags(article, rr: RenderResult, site: SiteConfig) -> tuple:
    """Returns (meta_tags_html, full_title_str)."""
    m = article.meta
    s = m.seo

    prefix = s.title_prefix if s.title_prefix is not None else site.default_title_prefix
    suffix = s.title_suffix if s.title_suffix is not None else site.default_title_suffix
    full_title = f'{prefix}{m.title}{suffix}'

    desc = s.description
    if not desc and rr.first_paragraph:
        desc = _truncate(rr.first_paragraph, site.description_truncate)

    canonical = s.canonical or f'{site.base_url}/{m.slug}/'

    og_image_raw = s.og_image
    if not og_image_raw and rr.first_image:
        og_image_raw = rr.first_image
    og_image = og_image_raw or site.default_og_image
    if og_image and not og_image.startswith('http'):
        og_image = site.base_url + og_image

    og_title = s.og_title or full_title
    og_desc = s.og_description or desc or ''
    og_image_alt = s.og_image_alt or m.title
    tw_image = s.twitter_image or og_image

    def e(val):
        return (val or '').replace('&', '&amp;').replace('"', '&quot;')

    tags = []

    if desc:
        tags.append(f'<meta name="description" content="{e(desc)}">')

    author = s.author or site.default_author
    if author:
        tags.append(f'<meta name="author" content="{e(author)}">')

    tags.append(f'<link rel="canonical" href="{e(canonical)}">')

    tags.append(f'<meta property="og:title" content="{e(og_title)}">')
    if og_desc:
        tags.append(f'<meta property="og:description" content="{e(og_desc)}">')
    if og_image:
        tags.append(f'<meta property="og:image" content="{e(og_image)}">')
        tags.append(f'<meta property="og:image:alt" content="{e(og_image_alt)}">')
    og_type = s.og_type or 'article'
    tags.append(f'<meta property="og:type" content="{e(og_type)}">')
    tags.append(f'<meta property="og:url" content="{e(canonical)}">')
    tags.append(f'<meta property="og:site_name" content="{e(site.name)}">')
    tags.append(f'<meta property="article:published_time" content="{e(m.date)}">')
    modified = m.updated or m.date
    tags.append(f'<meta property="article:modified_time" content="{e(modified)}">')

    tw_card = s.twitter_card or 'summary_large_image'
    tags.append(f'<meta name="twitter:card" content="{e(tw_card)}">')
    tags.append(f'<meta name="twitter:title" content="{e(og_title)}">')
    if og_desc:
        tags.append(f'<meta name="twitter:description" content="{e(og_desc)}">')
    if tw_image:
        tags.append(f'<meta name="twitter:image" content="{e(tw_image)}">')

    return '\n    '.join(tags), full_title

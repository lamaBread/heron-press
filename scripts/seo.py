"""SEO meta 태그 빌더 (§ 5).

본문 ↔ 메타데이터 분리 원칙 (v0.5.5):
  description / og_description / twitter_description / og_image 같이 외부에
  노출되는 메타데이터는 본문이 아니라 author 가 `meta.yaml` 의 `seo:` 블록에
  명시적으로 작성한 값에서만 가져온다. v0.5.4 까지 있었던 "본문 첫 `<p>` 를
  description 으로 / 본문 첫 `<img src>` 를 og_image 로" 류의 폴백은 모두 제거.

필드 상태 처리 (모든 Optional[str] 필드 공통):
  - None      = 키 부재 또는 값 부재 → 해당 메타 태그를 출력하지 않는다.
  - ''        = 빈 문자열 → 메타 태그 미출력 + Builder 가 BuildReport 에 기록.
                (seo.py 자체는 빈 문자열을 None 과 동등하게 처리 — 산출물엔
                노이즈를 보내지 않는다. 리포트는 builder 단에서 채운다.)
  - 'text'    = 정상값 → 메타 태그 출력.

폴백 정책:
  - description: author 가 직접 쓴 값만. 본문 폴백 없음.
  - og_description / twitter_description: 부재 시 description 폴백 (author 가
    직접 쓴 값을 재사용하므로 본문 추출이 아니다 — author-authored fallback).
  - og_image: meta.seo.og_image > site.default_og_image. 본문 폴백 없음.
              SNS / 메신저 미리보기가 og:image 없을 때 본문 첫 이미지를
              임의로 긁어가는 행동을 SSG 가 빌드 시점에 자동화하는 건 동일
              하게 무례한 일이라는 판단.
  - twitter_image: meta.seo.twitter_image > og_image (동일 규칙).
  - og_title: meta.seo.og_title > full_title.
  - og_image_alt: meta.seo.og_image_alt > meta.title.
  - author: meta.seo.author > site.default_author.

빈 태그 정책:
  속성 값이 비어 있으면 (`<meta name="description" content="">` 같이) 태그
  자체를 출력하지 않는다. SERP / 카드에 무의미한 노이즈를 보내지 않기 위함.

v0.5.4 잔존 기능:
  - `truncate_description` (구 `_truncate`) 가 영문 단어 경계를 존중. 절단
    지점이 ASCII alphanumeric/하이픈/언더스코어 시퀀스 한가운데이면 직전
    공백까지 backup. 한국어/한자/일본어 등 CJK 글자는 글자 단위가 의미 단위
    이므로 영향 없음 (Latin 단어 검사를 통과 못한다).
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


def _present(val) -> bool:
    """필드가 '실제 노출할 값을 가진다' 인지. None / 빈 문자열은 False."""
    return val is not None and val != ''


def build_meta_tags(article, rr: RenderResult, site: SiteConfig) -> tuple:
    """글의 `<head>` 에 들어갈 메타 태그 HTML 과 full_title 을 반환.

    Returns (meta_tags_html, full_title_str).

    v0.5.5: 본문 폴백 모두 제거. author-authored 값만 사용.
      - description: m.seo.description (없거나 빈 문자열이면 태그 누락).
      - og_description / twitter_description: 자기 필드 > description.
      - og_image: m.seo.og_image > site.default_og_image (둘 다 비면 태그 누락).
      - og_title: m.seo.og_title > full_title.
      - twitter_image: m.seo.twitter_image > og_image.
    """
    m = article.meta
    s = m.seo

    prefix = s.title_prefix if s.title_prefix is not None else site.default_title_prefix
    suffix = s.title_suffix if s.title_suffix is not None else site.default_title_suffix
    full_title = f'{prefix}{m.title}{suffix}'

    # description — 본문 폴백 없음. None/빈 문자열이면 태그 누락.
    desc = s.description if _present(s.description) else None

    canonical = s.canonical if _present(s.canonical) else f'{site.base_url}/{m.slug}/'

    # og_image — 본문 폴백 없음. seo.og_image > site.default_og_image.
    og_image = s.og_image if _present(s.og_image) else None
    if og_image is None and _present(site.default_og_image):
        og_image = site.default_og_image
    if og_image and not og_image.startswith('http'):
        og_image = site.base_url + og_image

    og_title = s.og_title if _present(s.og_title) else full_title

    # og_desc — seo.og_description > seo.description. 둘 다 부재면 태그 누락.
    og_desc = s.og_description if _present(s.og_description) else desc

    og_image_alt = s.og_image_alt if _present(s.og_image_alt) else m.title

    tw_image = s.twitter_image if _present(s.twitter_image) else og_image

    def e(val):
        return (val or '').replace('&', '&amp;').replace('"', '&quot;')

    tags = []

    if _present(desc):
        tags.append(f'<meta name="description" content="{e(desc)}">')

    author = s.author if _present(s.author) else site.default_author
    if _present(author):
        tags.append(f'<meta name="author" content="{e(author)}">')

    tags.append(f'<link rel="canonical" href="{e(canonical)}">')

    tags.append(f'<meta property="og:title" content="{e(og_title)}">')
    if _present(og_desc):
        tags.append(f'<meta property="og:description" content="{e(og_desc)}">')
    if _present(og_image):
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
    if _present(og_desc):
        tags.append(f'<meta name="twitter:description" content="{e(og_desc)}">')
    if _present(tw_image):
        tags.append(f'<meta name="twitter:image" content="{e(tw_image)}">')

    return '\n    '.join(tags), full_title

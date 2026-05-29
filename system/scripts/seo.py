"""SEO meta 태그 + JSON-LD 구조화 데이터 빌더 (§ 5).

v0.8.3 — JSON-LD (schema.org) 추가:
  글 페이지 `<head>` 에 `<script type="application/ld+json">` 한 줄을
  추가하는 `build_jsonld()` 와 사이트/글 토글을 판정하는 `jsonld_enabled()`
  를 신설. 기존 메타 태그를 *대체하지 않고 보강* (additive) 한다 — OG/
  Twitter/canonical/robots 와 JSON-LD 는 기계 소비자가 서로 다르다 (SNS
  언퍼ler=OG, SERP 스니펫=meta description, 색인 제어=robots meta, 검색
  엔진 리치 결과=JSON-LD). 두 산출물이 어긋나지 않도록 canonical/og_image/
  author 해석을 `resolve_canonical` / `resolve_og_image` / `resolve_author`
  헬퍼로 추출해 build_meta_tags 와 공유한다 (추출은 순수 리팩터 — v0.8.2
  까지 build_meta_tags 인라인이던 로직과 1:1, 메타 태그 산출물 byte 불변).

본문 ↔ 메타데이터 분리 원칙 (v0.5.5):
  description / og_description / twitter_description / og_image 같이 외부에
  노출되는 메타데이터는 본문이 아니라 author 가 `meta.yaml` 의 `seo:` 블록에
  명시적으로 작성한 값에서만 가져온다. v0.5.4 까지 있었던 "본문 첫 `<p>` 를
  description 으로 / 본문 첫 `<img src>` 를 og_image 로" 류의 폴백은 모두 제거.

페이지 종류 일반화 (v0.6.2):
  글 / 홈 / 카테고리가 같은 함수 `build_meta_tags` 를 사용한다. v0.5.4 까지
  글 페이지에만 출력되던 description / og_* / twitter_* 메타 태그가 홈과
  카테고리 페이지에도 동일한 폴백 규칙으로 출력된다. v0.5.4 의 한계 표
  "홈/카테고리 페이지의 SEO 메타 태그 출력" 항목을 해소.

  시그니처는 keyword-only — `title`, `seo`, `site`, `canonical_path`,
  `page_kind` 다섯이 필수, `published`/`updated` 는 글에만 의미가 있어 옵션.

  페이지 종류별 차이는 두 군데뿐:
  - `og:type` 디폴트: 글=`article` / 홈·카테고리=`website` (OGP 표준 권장).
    seo.og_type 으로 명시 override 가능.
  - `article:published_time` / `article:modified_time`: 글일 때만 (= published
    인자가 전달됐을 때만) 출력. 홈/카테고리는 두 인자 모두 None 이라 누락.

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
  - og_image: seo.og_image > site.default_og_image. 본문 폴백 없음.
              SNS / 메신저 미리보기가 og:image 없을 때 본문 첫 이미지를
              임의로 긁어가는 행동을 SSG 가 빌드 시점에 자동화하는 건 동일
              하게 무례한 일이라는 판단.
  - twitter_image: seo.twitter_image > og_image (동일 규칙).
  - og_title: seo.og_title > full_title.
  - og_image_alt: seo.og_image_alt > title (페이지 본문 title — 글 제목 /
                  홈 home_meta.title or site.name / 카테고리 cat.meta.title
                  or folder_name).
  - author: seo.author > site.default_author.

빈 태그 정책:
  속성 값이 비어 있으면 (`<meta name="description" content="">` 같이) 태그
  자체를 출력하지 않는다. SERP / 카드에 무의미한 노이즈를 보내지 않기 위함.

v0.5.4 잔존 기능:
  - `truncate_description` (구 `_truncate`) 가 영문 단어 경계를 존중. 절단
    지점이 ASCII alphanumeric/하이픈/언더스코어 시퀀스 한가운데이면 직전
    공백까지 backup. 한국어/한자/일본어 등 CJK 글자는 글자 단위가 의미 단위
    이므로 영향 없음 (Latin 단어 검사를 통과 못한다).
"""
import json
import re
from typing import Optional

from .models import SeoMeta, SiteConfig


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


# ════════════════════════════════════════════════════════════════
# 공용 해석 헬퍼 (v0.8.3) — build_meta_tags 와 build_jsonld 가 같은
# canonical / og_image / author 를 보도록 추출. 동작은 v0.8.2 까지
# build_meta_tags 인라인이던 것과 1:1 (순수 리팩터, 산출물 불변).
# ════════════════════════════════════════════════════════════════

def resolve_canonical(seo: SeoMeta, site: SiteConfig,
                      canonical_path: str) -> str:
    """canonical URL — seo.canonical (author 명시) > base_url+canonical_path."""
    return (
        seo.canonical if _present(seo.canonical)
        else f'{site.base_url}{canonical_path}'
    )


def resolve_og_image(seo: SeoMeta, site: SiteConfig) -> Optional[str]:
    """og:image — seo.og_image > site.default_og_image, 절대 URL 정규화.

    본문 폴백 없음 (v0.5.5 본문↔메타데이터 분리). 'http' 로 시작하지 않으면
    site.base_url 접두. 둘 다 부재면 None.
    """
    img = seo.og_image if _present(seo.og_image) else None
    if img is None and _present(site.default_og_image):
        img = site.default_og_image
    if img and not img.startswith('http'):
        img = site.base_url + img
    return img


def resolve_author(seo: SeoMeta, site: SiteConfig) -> Optional[str]:
    """author — seo.author (author 명시) > site.default_author."""
    return seo.author if _present(seo.author) else site.default_author


def build_meta_tags(
    *,
    title: str,
    seo: SeoMeta,
    site: SiteConfig,
    canonical_path: str,
    page_kind: str,
    published: Optional[str] = None,
    updated: Optional[str] = None,
) -> tuple:
    """페이지의 `<head>` 에 들어갈 메타 태그 HTML 과 full_title 을 반환.

    Returns (meta_tags_html, full_title_str).

    v0.6.2: 글/홈/카테고리 공용. 페이지 종류별 차이는 og:type 디폴트 + article:*
    time 태그 출력 여부 두 군데.

    인자 (모두 keyword-only):
      title          — 페이지의 본문 title. 글=m.title / 홈=home_meta.title or
                       site.name / 카테고리=cat.meta.title or cat.folder_name.
                       `{prefix}{title}{suffix}` 로 감싸 full_title 을 만든다.
      seo            — 페이지의 SeoMeta. title_prefix/suffix/description/og_*/
                       twitter_*/author/canonical/og_type 등.
      site           — SiteConfig. default_title_prefix/suffix, default_og_image,
                       default_author, base_url, name 등의 폴백 소스.
      canonical_path — canonical URL 의 경로 부분. 글='/{slug}/' / 홈='/' /
                       카테고리='/{top}/{sub}/'. seo.canonical 이 있으면 무시
                       되고 그 값이 우선.
      page_kind      — 'article' | 'home' | 'category'. og:type 디폴트 결정에
                       사용 (article→article, home/category→website). 다른 값이
                       오면 'website' 로 폴백.
      published      — 글의 date (ISO 8601). 홈/카테고리는 None. 값이 있을
                       때만 article:published_time 태그 출력.
      updated        — 글의 updated or date. 홈/카테고리는 None. 값이 있을
                       때만 article:modified_time 태그 출력.
    """
    prefix = seo.title_prefix if seo.title_prefix is not None else site.default_title_prefix
    suffix = seo.title_suffix if seo.title_suffix is not None else site.default_title_suffix
    full_title = f'{prefix}{title}{suffix}'

    # description — 본문 폴백 없음. None/빈 문자열이면 태그 누락.
    desc = seo.description if _present(seo.description) else None

    canonical = resolve_canonical(seo, site, canonical_path)

    # og_image — 본문 폴백 없음. seo.og_image > site.default_og_image.
    # v0.8.3: 해석을 resolve_og_image 로 추출 (build_jsonld 와 공용·동작 불변).
    og_image = resolve_og_image(seo, site)

    og_title = seo.og_title if _present(seo.og_title) else full_title

    # og_desc — seo.og_description > seo.description. 둘 다 부재면 태그 누락.
    og_desc = seo.og_description if _present(seo.og_description) else desc

    og_image_alt = seo.og_image_alt if _present(seo.og_image_alt) else title

    tw_image = seo.twitter_image if _present(seo.twitter_image) else og_image

    # og:type 디폴트는 page_kind 따라. seo.og_type 으로 명시 override 가능.
    # v0.6.1 까지 SeoMeta.og_type 의 default 가 'article' 이었으나, 홈/카테고리에
    # 그대로 적용되면 OGP 표준상 부정확. v0.6.2 부터 SeoMeta.og_type 은 None
    # 이 디폴트이고 (= "author 가 명시하지 않음"), 빌더가 page_kind 로 결정.
    if _present(seo.og_type):
        og_type = seo.og_type
    elif page_kind == 'article':
        og_type = 'article'
    else:
        og_type = 'website'

    def e(val):
        return (val or '').replace('&', '&amp;').replace('"', '&quot;')

    tags = []

    if _present(desc):
        tags.append(f'<meta name="description" content="{e(desc)}">')

    author = resolve_author(seo, site)
    if _present(author):
        tags.append(f'<meta name="author" content="{e(author)}">')

    tags.append(f'<link rel="canonical" href="{e(canonical)}">')

    tags.append(f'<meta property="og:title" content="{e(og_title)}">')
    if _present(og_desc):
        tags.append(f'<meta property="og:description" content="{e(og_desc)}">')
    if _present(og_image):
        tags.append(f'<meta property="og:image" content="{e(og_image)}">')
        tags.append(f'<meta property="og:image:alt" content="{e(og_image_alt)}">')
    tags.append(f'<meta property="og:type" content="{e(og_type)}">')
    tags.append(f'<meta property="og:url" content="{e(canonical)}">')
    tags.append(f'<meta property="og:site_name" content="{e(site.name)}">')
    # article:* 시간 태그는 글일 때만 (= published 인자가 전달됐을 때만).
    # 홈/카테고리는 두 인자 모두 None 으로 호출되어 자동 누락.
    if _present(published):
        tags.append(f'<meta property="article:published_time" content="{e(published)}">')
    if _present(updated):
        tags.append(f'<meta property="article:modified_time" content="{e(updated)}">')

    tw_card = seo.twitter_card or 'summary_large_image'
    tags.append(f'<meta name="twitter:card" content="{e(tw_card)}">')
    tags.append(f'<meta name="twitter:title" content="{e(og_title)}">')
    if _present(og_desc):
        tags.append(f'<meta name="twitter:description" content="{e(og_desc)}">')
    if _present(tw_image):
        tags.append(f'<meta name="twitter:image" content="{e(tw_image)}">')

    return '\n    '.join(tags), full_title


# ════════════════════════════════════════════════════════════════
# JSON-LD 구조화 데이터 (schema.org) — v0.8.3
# ════════════════════════════════════════════════════════════════

def jsonld_enabled(site: SiteConfig, seo: SeoMeta) -> bool:
    """이 페이지에 JSON-LD 를 출력할지 판정. 사이트 토글이 마스터.

    - site.jsonld.enabled 가 False → 무조건 False (글 단위 seo.jsonld=True
      로도 강제 켜지지 않는다).
    - 사이트가 켜져 있고 seo.jsonld 가 False → 이 글만 opt-out → False.
    - 그 외 (seo.jsonld 가 None/True) → True.
    """
    if not site.jsonld.enabled:
        return False
    if seo.jsonld is False:
        return False
    return True


def build_jsonld(
    *,
    title: str,
    seo: SeoMeta,
    site: SiteConfig,
    canonical_path: str,
    page_lang: str,
    published: Optional[str] = None,
    updated: Optional[str] = None,
    tags: Optional[list] = None,
    breadcrumb: Optional[list] = None,
) -> str:
    """글 페이지 `<head>` 에 들어갈 schema.org JSON-LD `<script>` 한 줄 반환.

    v0.8.3 신설. build_meta_tags 와 *부가적* (additive) — OG/Twitter/
    canonical/robots 메타 태그를 대체하지 않는다 (소비자가 다름: SNS
    언퍼ler=OG, SERP 스니펫=meta description, 색인 제어=robots meta,
    검색 엔진 리치 결과=JSON-LD). 본문↔메타데이터 분리 원칙을 동일하게
    따른다 — description/og_image/author 는 author 가 직접 쓴 값(또는
    site 디폴트)만, 본문 추출 폴백 없음. canonical/og_image/author 해석은
    build_meta_tags 와 같은 resolve_* 헬퍼를 공유해 두 산출물이 어긋나지
    않는다.

    @graph 로 두 노드:
      - Article  — headline / datePublished / dateModified / description /
        author(Person) / publisher(Organization) / image / keywords /
        inLanguage / url / mainEntityOfPage. 부재한 선택 필드는 키 자체를
        넣지 않는다 (빈 값 노이즈 금지 — 메타 태그 정책과 동형).
      - BreadcrumbList — breadcrumb 인자(빌더의 crumb_parts, 사이트의
        nav-tracker 와 같은 라벨)를 1-기반 ListItem 배열로. 마지막(현재
        페이지, url=None)은 schema.org 권장대로 `item` 을 생략. 항목이
        2개 미만(톱레벨 글의 단일 crumb 등)이면 의미 있는 경로가 아니라
        BreadcrumbList 노드 자체를 생략한다.

    결정성: json.dumps(ensure_ascii=False, sort_keys=True,
    separators=(',', ':')) — 객체 키가 삽입 순서와 무관하게 정렬되어
    입력이 같으면 byte 동일. 배열(@graph / itemListElement / keywords)
    순서는 의미가 있어 보존된다 (sort_keys 는 객체 키만 정렬).

    `<script>` 안전: raw-text 요소라 `</script` / `<!--` 가 HTML 파서를
    깨뜨릴 수 있어 직렬화 결과의 `<` `>` `&` 를 각각 `\\u003c` `\\u003e`
    `\\u0026` 로 치환한다. 셋 다 유효한 JSON 이스케이프라 소비자는 원문
    으로 복원하고, 치환 결과에는 다시 `<>&` 가 없어 순서 무관.
    """
    canonical = resolve_canonical(seo, site, canonical_path)

    article = {
        '@type': 'Article',
        'headline': title,
        'url': canonical,
        'mainEntityOfPage': {'@type': 'WebPage', '@id': canonical},
        'publisher': {
            '@type': 'Organization',
            'name': site.name,
            'url': site.base_url,
        },
    }
    if _present(published):
        article['datePublished'] = published
    if _present(updated):
        article['dateModified'] = updated
    if _present(seo.description):
        article['description'] = seo.description
    author = resolve_author(seo, site)
    if _present(author):
        article['author'] = {'@type': 'Person', 'name': author}
    img = resolve_og_image(seo, site)
    if img:
        article['image'] = img
    if tags:
        article['keywords'] = list(tags)
    if _present(page_lang):
        article['inLanguage'] = page_lang

    graph = [article]

    items = []
    for i, (name, url) in enumerate(breadcrumb or [], start=1):
        el = {'@type': 'ListItem', 'position': i, 'name': name}
        if url:
            el['item'] = (
                url if url.startswith('http') else site.base_url + url
            )
        items.append(el)
    if len(items) >= 2:
        graph.append({
            '@type': 'BreadcrumbList',
            'itemListElement': items,
        })

    doc = {'@context': 'https://schema.org', '@graph': graph}
    payload = json.dumps(
        doc, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
    )
    payload = (
        payload.replace('<', '\\u003c')
               .replace('>', '\\u003e')
               .replace('&', '\\u0026')
    )
    return f'<script type="application/ld+json">{payload}</script>'

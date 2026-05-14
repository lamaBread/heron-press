"""빌드 파이프라인 전체에서 공유되는 데이터 모델.

dataclasses 만 모아둔다. 모든 동작 로직은 다른 모듈에 있다.

v0.5.5 변경:
  - RenderResult 에서 `first_paragraph` / `first_image` 필드 제거. v0.5.4
    까지 SEO description / og_image / 갤러리 썸네일 / 피드 summary 의 폴백
    소스로 본문에서 휴리스틱 추출된 값이었으나, "본문 ↔ 메타데이터 분리
    원칙" (README § 5-1 참조) 도입과 함께 폐기. 모든 외부 노출 메타데이터는
    `meta.yaml` 의 명시적 author-authored 값만 사용한다.
  - SeoMeta.description 등 Optional[str] 필드의 의미가 *세 상태* 로 확장:
    `None` = 키 부재 또는 값 부재 (opt-out, 메타 태그 누락), `''` = 작성자
    실수 (메타 태그 누락 + BuildReport 에 기록), 비어있지 않은 str = 정상값
    (메타 태그 출력). 빈 문자열을 None 으로 강제하지 않는다 — Builder 의
    frontmatter 파서가 둘을 보존해서 넘긴다.

v0.5.4 변경:
  - CategoryMeta 에 `title` (Optional[str]) 과 `seo` (SeoMeta) 추가. 홈/카테고리
    페이지의 `<title>` 폴백 체인을 글과 동일하게 작동시키기 위함 (v0.4.3 에서
    글에만 적용되던 한계 해소). 카테고리는 `title` 없으면 폴더명, 홈은
    site.name 이 폴백. 두 페이지 모두 `seo.title_prefix` / `seo.title_suffix`
    가 site.default_title_prefix / default_title_suffix 를 오버라이드.
  - ArticleMeta + CategoryMeta 에 `nav_priority` (int) 추가. 톱레벨 nav 의
    항목 정렬 키 — `priority` (부모 카테고리 page 안에서의 sibling section
    정렬) 와 별개 축. 값이 클수록 먼저, 같은 값끼리는 폴더명 알파벳 순.
    이전 버전의 'About 최상단 하드코딩' 폐기.
  - SiteConfig 에 `error_404_title` / `search_title`. 404·search 페이지는
    meta.yaml 을 두지 않으므로 (콘텐츠 페이지가 아님) site.yaml 에서 직접
    설정. 두 페이지 모두 default_title_prefix / default_title_suffix 폴백
    체인 적용 (글·홈·카테고리와 동일).

v0.5.3 변경:
  - ArticleMeta 에 `tags` 필드 (list[str]) 추가. 글 작성자가 직접 적는 주제어
    목록. v0.5.3 시점에는 feed.atom / feed.rss 의 `<category>` 엔트리에만
    쓰였고, v0.6.0 부터 검색 인덱스의 세 번째 BM25 필드로 합류 (`w_tags=2.0`,
    정확매치 시 phrase boost ×2.5). 카테고리 meta.yaml (CategoryMeta) 에는
    의도적으로 `tags` 를 두지 않음 — 카테고리가 그 자체로 분류 축이라
    tags 와 개념이 중복된다는 판단.

v0.5.1 변경:
  - SiteConfig 에 `images` 필드 (ImageConfig). site.yaml 의 `images:` 블록을
    파싱한 결과. 빌드 시 raster 이미지의 WebP 변환 + 다중 해상도 + lazy
    loading 정책을 보유. 자세한 의미는 scripts/images.py 의 ImageConfig
    docstring 참조. site.yaml 에 `images:` 블록이 없으면 기본값으로 채워짐.

v0.4.6 변경:
  - 메인페이지(홈) 전용 설정을 site.yaml 에서 분리 → Articles/meta.yaml
    로 일원화. SiteConfig 에서 home_per_page / home_excludes_categories /
    home_sort 필드 제거. 그 자리는 CategoryMeta 가 흡수
    (excludes_categories 추가). home_sort 는 빌더가 사용한 적 없는 dead
    field 였으므로 그대로 폐기. site.yaml 은 이제 카테고리류의 전역 디폴트
    (category_per_page / category_preview_per_page / lang 등) 만 보유.
  - CategoryMeta 에 excludes_categories 필드 추가. 카테고리 자기 자신에는
    의미가 없고 Articles/meta.yaml (홈) 에서만 사용됨.

v0.4.5 변경:
  - CategoryMeta dataclass 신설. 카테고리 폴더의 meta.yaml 을 파싱한 결과.
    per_page / preview_per_page / layout / styles / lang.
  - SiteConfig 에 lang / home_per_page / category_per_page /
    category_preview_per_page 필드 추가.
  - ArticleMeta 에 lang 필드 추가 (전역 lang override).
  - Category 에 meta 필드 (CategoryMeta).

v0.4.3 변경:
  - SeoMeta dataclass 신설. ArticleMeta 의 평면적 seo_* 필드들을 모두
    SeoMeta 로 옮김 (meta.yaml 도 `seo:` 하위 블록으로 변경).
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .images import ImageConfig


@dataclass
class SiteConfig:
    domain: str
    base_url: str
    name: str
    main_title: str
    default_author: str
    default_og_image: str
    default_title_prefix: str
    default_title_suffix: str
    copyright_holder: str
    copyright_year_start: int
    reserved_slugs: list
    warn_on_underscore_ref: bool
    warn_on_missing_asset: bool
    warn_on_stale_updated: bool
    description_truncate: int
    robots_txt_main: str
    robots_txt_legacy: str
    # v0.4.5: i18n + 카테고리 페이지네이션 디폴트.
    # v0.4.6: home_* 류 필드는 Articles/meta.yaml 로 이전됨 — site.yaml 에는
    # 진짜 '전역' (= 카테고리 류 전반에 적용되는 디폴트, 또는 사이트 메타) 만 남김.
    lang: str = 'ko'
    category_per_page: int = 20
    category_preview_per_page: int = 5
    # v0.5.4: meta.yaml 을 두지 않는 시스템 페이지(404 / search)의 `<title>`
    # 본문 텍스트. default_title_prefix / default_title_suffix 폴백 체인은
    # 글·홈·카테고리와 동일하게 적용된다. site.yaml 의 키는 같은 이름.
    error_404_title: str = 'Not Found'
    search_title: str = 'Search'
    # v0.5.1: 이미지 자동 최적화 정책 (WebP + 다중 해상도 + lazy loading).
    images: ImageConfig = field(default_factory=ImageConfig)


@dataclass
class SeoMeta:
    """meta.yaml 의 `seo:` 하위 블록.

    v0.5.5: 모든 Optional[str] 필드가 세 상태를 가진다.
      - None      = 키 부재 또는 값 부재. opt-out → 메타 태그 누락.
      - ''        = 빈 문자열. 작성자 실수로 간주 → 메타 태그 누락 +
                    BuildReport 에 기록.
      - 'text'    = 정상값. 메타 태그 출력.

    Builder 의 frontmatter 파서 (`_parse_frontmatter` / `_parse_category_meta_file`)
    가 yaml_load 의 결과를 그대로 보존해야 한다 — 빈 문자열을 None 으로
    강제 변환하면 위 구분이 무너진다.

    v0.5.4 까지 있었던 본문 폴백 (first_paragraph → description, first_image
    → og_image) 은 v0.5.5 에서 폐기. 모든 외부 노출 메타데이터는 author 가
    명시한 값만 사용. og_description / twitter_description 의 description
    폴백, og_title 의 full_title 폴백 같은 *author-authored fallback* 은
    유지 (다른 필드도 author 가 직접 쓴 값을 재사용하는 것이라 본문 추출이
    아니다).
    """
    title_prefix: Optional[str] = None
    title_suffix: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    canonical: Optional[str] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    og_image: Optional[str] = None
    og_image_alt: Optional[str] = None
    og_type: str = 'article'
    twitter_card: str = 'summary_large_image'
    twitter_image: Optional[str] = None


@dataclass
class ArticleMeta:
    slug: str
    title: str
    date: str
    updated: Optional[str] = None
    noindex: bool = False
    # v0.4.5: 글 단위 lang override. 비우면 site.lang.
    lang: Optional[str] = None
    seo: SeoMeta = field(default_factory=SeoMeta)
    # 본문 태그 (p, h3, ul, blockquote, a, ...) 의 기본 속성을 글 단위로 override.
    # 결과는 head 의 <style> 에 inject 되어 `section TAG` 선택자로 적용된다.
    styles: dict = field(default_factory=dict)
    # v0.5.3: 글 작성자가 직접 적는 주제어 목록. 산출물에서 두 곳에 쓰임 —
    # (1) feed.atom / feed.rss 의 <category>, (2) v0.6.0 부터 검색 인덱스의
    # 세 번째 BM25 필드 (w_tags=2.0, 정확매치 phrase boost ×2.5). meta.yaml
    # 파싱 단계에서 검증되고 정규화 (trim + dedup, 순서 보존) 된다.
    tags: list = field(default_factory=list)
    # v0.5.4: 톱레벨 nav 의 항목 정렬 키. 글이 톱레벨 (Articles/ 직속) 일 때만
    # 의미가 있다 (예: About). priority 와 별개 축 — priority 는 부모 카테고리
    # page 안에서의 sibling section 정렬, nav_priority 는 사이트 전역 nav 정렬.
    # 값이 클수록 먼저, 같은 값끼리는 폴더명 알파벳 순. 기본 0.
    nav_priority: int = 0


@dataclass
class CategoryMeta:
    """카테고리 폴더 (`Articles/<path>/meta.yaml`) 와 사이트 루트
    (`Articles/meta.yaml` = 메인페이지) 의 설정을 함께 담는 dataclass.

    v0.4.5 에 카테고리용으로 신설. v0.4.6 에서 메인페이지 (홈) 도 같은
    스키마로 파싱되도록 확장 — 단 필드별로 적용 대상이 다르다 (아래 분류).

    ── 공통 (홈 + 카테고리) ────────────────────────────────────────────
    per_page          — 이 페이지의 페이지당 글 수.
                        비우면 카테고리는 site.category_per_page (기본 20),
                        홈은 빌더의 코드 디폴트 (= 5).
    layout            — 'list' (기본) / 'gallery' (v0.5.3). 'gallery' 는 글
                        목록을 텍스트 한 줄이 아니라 이미지 타일 그리드로
                        렌더 (CSS Grid + 4:3 강제 크롭). 둘 외의 값이 오면
                        빌드는 통과하되 'list' 로 폴백한다.
    lang              — 이 페이지의 <html lang> 오버라이드. 비우면 site.lang.
    styles            — 이 페이지 head 에 inject 되는 CSS 규칙 매핑
                        (글 단위 styles 와 동일 포맷).

    ── 카테고리 전용 (루트 = 홈 에서는 무의미) ─────────────────────────
    preview_per_page  — 이 카테고리가 *상위* 카테고리 인덱스 페이지에
                        section 으로 임베드될 때 한 페이지가 보여 줄 글 개수.
                        비우면 site.category_preview_per_page (기본 5).
                        "소분류 색인 페이지는 대분류보다 더 많은 항목" 정책의
                        의도가 per_page > preview_per_page 라는 형태로 구현됨.
    priority          — v0.4.6 신설. 이 카테고리가 다른 카테고리들과 한
                        페이지에 함께 표시될 때 (부모 카테고리의 인덱스
                        페이지의 section 들, 또는 톱레벨 nav 링크 등) 의
                        등장 순서를 결정. 0 을 포함한 정수. **값이 클수록
                        먼저** 표시된다 (priority 100 → priority 1 → priority 0).
                        같은 priority 끼리는 폴더명 알파벳 순. 기본값 0.

    ── 홈 전용 (실제 카테고리에서는 무의미) ────────────────────────────
    excludes_categories — v0.4.6 신설 (이전 버전의 site.home_excludes_categories
                          이 이리로 이전됨). 메인페이지 Recent posts 에서
                          제외할 톱레벨 카테고리 폴더명 목록. 기본값 [].
                          예: [About] 이면 About 카테고리의 글은 홈 목록과
                          sitemap.xml 의 홈 lastmod 계산에서 제외된다.

    ── 공통, v0.5.4 신설 ────────────────────────────────────────────────
    title             — 이 페이지의 `<title>` 본문. 비우면 폴백:
                        카테고리는 folder_name, 홈은 site.name. 글의
                        ArticleMeta.title 과 같은 자리 (페이지 = 글/홈/카테고리
                        통일 관점). 양옆은 seo.title_prefix / seo.title_suffix
                        (없으면 site.default_title_prefix / suffix) 로 감싸진다.
    seo               — 페이지의 SEO 메타. SeoMeta 와 같은 dataclass. 현재
                        실제 사용처는 `<title>` 폴백 체인의 prefix/suffix 뿐이며,
                        나머지 필드 (description / og_* / twitter_*) 는 파싱만
                        되고 사용되지 않음 (forward compat). 글 (ArticleMeta) 의
                        seo 와 동일 의미.
    nav_priority      — 톱레벨 nav 의 정렬 키. 글의 nav_priority 와 같은 의미.
                        톱레벨 카테고리에서만 의미가 있다 — 서브카테고리/홈에서는
                        파싱만 되고 사용되지 않음. 값이 클수록 먼저, 같은 값끼리는
                        폴더명 알파벳 순. 기본 0.
    """
    per_page: Optional[int] = None
    preview_per_page: Optional[int] = None
    layout: str = 'list'
    lang: Optional[str] = None
    styles: dict = field(default_factory=dict)
    priority: int = 0
    excludes_categories: list = field(default_factory=list)
    # v0.5.4: `<title>` 폴백 체인을 글과 동일하게 작동시키기 위한 필드들.
    title: Optional[str] = None
    seo: SeoMeta = field(default_factory=SeoMeta)
    nav_priority: int = 0


@dataclass
class RenderResult:
    """본문 렌더 결과.

    v0.5.5 에서 슬림화 — 이전의 `first_paragraph` / `first_image` 필드가
    제거되었다. 두 필드는 SEO description / og_image / 갤러리 썸네일 / 피드
    summary 의 폴백 소스였으나, "본문 ↔ 메타데이터 분리 원칙" 도입과 함께
    폐기. 외부 노출 메타데이터는 author 가 meta.yaml 에 직접 쓴 값만 사용.
    """
    html: str


@dataclass
class Article:
    meta: ArticleMeta
    source_dir: Path
    content_file: Path
    category_path: list  # [folder_name, ...] from Articles/ to article folder


@dataclass
class Category:
    folder_name: str
    slug: str
    path: list          # [folder_name, ...] path from Articles/
    slug_path: list     # [slug, ...] built from path
    children: list = field(default_factory=list)
    articles: list = field(default_factory=list)
    # v0.4.5: 카테고리 폴더의 meta.yaml 파싱 결과 (없으면 기본 CategoryMeta).
    meta: CategoryMeta = field(default_factory=CategoryMeta)

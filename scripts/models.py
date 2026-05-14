"""빌드 파이프라인 전체에서 공유되는 데이터 모델.

dataclasses 만 모아둔다. 모든 동작 로직은 다른 모듈에 있다.

v0.5.3 변경:
  - ArticleMeta 에 `tags` 필드 (list[str]) 추가. 글 작성자가 직접 적는 주제어
    목록. 현재는 파싱만 되고 구체적인 사용처는 없음 (검색·필터·관련 글 등
    미래 기능을 위한 토대). 카테고리 meta.yaml (CategoryMeta) 에는 의도적으로
    `tags` 를 두지 않음 — 카테고리가 그 자체로 분류 축이라 tags 와 개념이
    중복된다는 판단.

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
    # v0.5.1: 이미지 자동 최적화 정책 (WebP + 다중 해상도 + lazy loading).
    images: ImageConfig = field(default_factory=ImageConfig)


@dataclass
class SeoMeta:
    """meta.yaml 의 `seo:` 하위 블록.

    모든 필드는 None 이 기본값 — 비어 있으면 site.yaml 의 default_* 또는
    seo.py 의 폴백 체인 (first_paragraph, first_image 등) 으로 채워진다.
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
    # v0.5.3: 글 작성자가 직접 적는 주제어 목록. 검색·필터·관련 글 등 미래 기능을
    # 위한 토대. 현재 빌드 산출물에서 직접 쓰이지는 않지만, meta.yaml 파싱
    # 단계에서 검증되고 정규화 (trim + dedup, 순서 보존) 된다.
    tags: list = field(default_factory=list)


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
    layout            — 'list' (기본) / 'gallery' / ... 미래 확장용. 현재는
                        'list' 만 구현. 다른 값이 와도 빌드는 통과하되 'list'
                        로 폴백한다.
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
    """
    per_page: Optional[int] = None
    preview_per_page: Optional[int] = None
    layout: str = 'list'
    lang: Optional[str] = None
    styles: dict = field(default_factory=dict)
    priority: int = 0
    excludes_categories: list = field(default_factory=list)


@dataclass
class RenderResult:
    html: str
    first_paragraph: str
    first_image: Optional[str]


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

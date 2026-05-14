"""빌드 파이프라인 전체에서 공유되는 데이터 모델.

dataclasses 만 모아둔다. 모든 동작 로직은 다른 모듈에 있다.

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
    home_excludes_categories: list
    home_sort: str
    description_truncate: int
    robots_txt_main: str
    robots_txt_legacy: str
    # v0.4.5: i18n + 페이지네이션 디폴트
    lang: str = 'ko'
    home_per_page: int = 5
    category_per_page: int = 20
    category_preview_per_page: int = 5


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


@dataclass
class CategoryMeta:
    """카테고리 폴더(`Articles/<path>/meta.yaml`) 의 설정. v0.4.5 신설.

    per_page          — 이 카테고리의 *자신* 의 인덱스 페이지에서 한 페이지가
                        보여 줄 글 개수. 비우면 site.category_per_page (기본 20).
    preview_per_page  — 이 카테고리가 *상위* 카테고리의 인덱스 페이지에
                        section 으로 임베드될 때 한 페이지가 보여 줄 글 개수.
                        비우면 site.category_preview_per_page (기본 5).
                        "소분류 색인 페이지는 대분류보다 더 많은 항목" 정책의
                        의도가 per_page > preview_per_page 라는 형태로 구현됨.
    layout            — 'list' (기본) / 'gallery' / ... 미래 확장용. 현재는
                        'list' 만 구현. 다른 값이 와도 빌드는 통과하되 'list' 로
                        폴백한다.
    styles            — 이 카테고리 인덱스 페이지 head 에 inject 되는 CSS
                        규칙 매핑. (글 단위 styles 와 동일 포맷.)
    lang              — 이 카테고리 인덱스 페이지의 <html lang> 오버라이드.
    """
    per_page: Optional[int] = None
    preview_per_page: Optional[int] = None
    layout: str = 'list'
    lang: Optional[str] = None
    styles: dict = field(default_factory=dict)


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

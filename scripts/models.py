"""빌드 파이프라인 전체에서 공유되는 데이터 모델.

dataclasses 만 모아둔다. 모든 동작 로직은 다른 모듈에 있다.
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


@dataclass
class ArticleMeta:
    slug: str
    title: str
    date: str
    updated: Optional[str] = None
    noindex: bool = False
    seo_title_prefix: Optional[str] = None
    seo_title_suffix: Optional[str] = None
    seo_description: Optional[str] = None
    seo_author: Optional[str] = None
    seo_canonical: Optional[str] = None
    seo_og_title: Optional[str] = None
    seo_og_description: Optional[str] = None
    seo_og_image: Optional[str] = None
    seo_og_image_alt: Optional[str] = None
    seo_og_type: str = 'article'
    seo_twitter_card: str = 'summary_large_image'
    seo_twitter_image: Optional[str] = None
    # 본문 태그 (p, h3, ul, blockquote, a, ...) 의 기본 속성을 글 단위로 override.
    # 결과는 head 의 <style> 에 inject 되어 `section TAG` 선택자로 적용된다.
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

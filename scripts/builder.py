"""빌드 파이프라인 (Builder 클래스).

15단계 파이프라인:
  [1] _load_config           — site.yaml + legacy-map.yaml + 토크나이저 패리티 검증
  [2] _scan_articles         — Articles/ 트리 순회, _ 접두 제외
  [3] _parse_frontmatter     — meta.yaml 파싱 → ArticleMeta 채움 (seo: 블록 포함)
  [4] _validate              — slug 검증, 카테고리 트리 구축 (한글 폴더 워닝),
                                카테고리 meta.yaml 파싱 (v0.4.5)
  [5] _render_articles       — 본문 렌더 + 섹션 마커 처리 + nav/SEO/styles
                                → dist/{slug}/
  [6] _sync_assets           — 본문 외 자원 → dist/src/{slug}/
  [7] _build_categories      — 톱레벨 + 서브카테고리 인덱스 페이지 (v0.4.5)
  [8] _build_home            — 루트 페이지 (Recent + 페이지네이션, v0.4.5)
  [9] _copy_site_assets      — assets/ → dist/assets/
  [10] _build_404            — 404 페이지
  [11] _build_robots         — robots.txt (main + legacy)
  [12] _build_sitemap        — dist/sitemap.xml (v0.4.4 신설, v0.4.5 에서
                                서브카테고리 URL 도 포함)
  [13] _build_dispatcher     — dist-legacy/redirect.php (301 매핑)
  [14] _build_search         — search-index.json + search.php (+ tokenize lib)
  [15] _prune_orphans        — 삭제된 슬러그/카테고리의 dist 잔재 정리

v0.4.7 변경:
  - _build_home 의 카테고리 path 분기 dead branch 정리 (출력 동일).
  - docstring 의 v0.4.x 버전 표기 일괄 갱신. 동작 변경 없음.

v0.4.6 변경:
  - 페이지네이션 nav 의 상/하단 여백 축소 (assets/common_template.css).
  - SSR 단계에서 페이지네이션 첫 페이지 상태를 정적으로 출력 — 비활성 페이지
    항목은 inline `style='display:none'` 으로 미리 숨김 → FOUC 제거.
    pagination.js 는 그 후에 첫 페이지 항목의 inline style 을 비워 정상 표시.
  - Articles/meta.yaml 신설 (메인페이지 = 홈의 카테고리-격 설정).
  - 모든 카테고리/홈 meta.yaml 에 priority 필드 (정수, 값이 클수록 먼저).
  - **설정 일원화**: 홈 (메인페이지) 전용 설정은 site.yaml 에서 Articles/
    meta.yaml 로 전부 이전. site.yaml 은 진짜 '전역' (카테고리류 디폴트, lang
    디폴트, SEO 폴백 등) 만 보유. 옛 home_per_page / home_excludes_categories
    는 각각 Articles/meta.yaml 의 per_page / excludes_categories 로 이동.
    home_sort 는 빌더가 사용한 적 없는 dead field 라 폐기.

v0.4.5 변경:
  - 카테고리 폴더의 meta.yaml 파싱 (CategoryMeta). per_page /
    preview_per_page / layout / styles / lang.
  - 서브카테고리도 자기 인덱스 페이지를 가짐 (`/{top}/{sub}/`). 톱레벨
    페이지는 그대로 유지 (서브카테고리들의 section 들이 임베드).
  - 메인페이지 Recent / 카테고리 인덱스 (대분류·소분류) / 상위 카테고리에
    임베드된 서브카테고리 section 마다 독립적인 페이지 컨트롤.
    JS DOM hide/show 로 구현 — 모든 항목은 SSR.
  - 다국어: 템플릿의 `<html lang>` 가 더 이상 'ko' 하드코딩이 아님.
    site.lang 디폴트, 글/카테고리 meta.yaml 의 `lang:` 으로 오버라이드.
  - 한국어 폴더명 워닝의 메시지 보강 (어떤 폴더가 어떤 hex slug 로
    변환되었는지 빌드 로그에서 한눈에).

v0.4.4 변경:
  - sitemap.xml 자동 생성 (scripts/sitemap.py). 글·카테고리·홈 URL 을 포함.
    noindex 글과 서브카테고리는 제외. lastmod 는 updated 우선, 없으면 date.
  - robots.txt 의 `Sitemap:` 디렉티브가 더 이상 주석 처리되지 않음.

v0.4.3 변경:
  - <title> 에 글 제목 사용 (이전엔 항상 site.name 으로 덮어쓰던 quirk 제거).
    `{seo.title_prefix}{title}{seo.title_suffix}` 형태.
  - meta.yaml 의 평면 seo_* 필드 → `seo:` 하위 블록 (SeoMeta 로 파싱).
  - 마크다운 본문 안에서 섹션 마커 (===제목===, ======) 사용 가능.
    body 조립을 markdown.resolve_section_markers 에 위임.

v0.4.0 변경:
  - _meta.yaml 슬러그 오버라이드 코드 경로 완전 제거.
  - 한국어 폴더명 자동 경고 + ASCII 코드포인트 폴백 (slugs.py).
  - ROBOTS_META placeholder 로 article 단위 noindex.
  - search 인덱스 빌드 직전 토크나이저 패리티 검증.
  - 본문 길이 절단 제거 (search.build_search_index).
"""
import datetime
import json
import os
import re
import shutil
import sys
from datetime import date as Date
from pathlib import Path

from .yaml_parser import yaml_load
from .models import (
    SiteConfig, ArticleMeta, SeoMeta, CategoryMeta, Article, Category,
)
from .slugs import category_slug_from_name, is_underscore_path, has_non_ascii
from .markdown import (
    escape_html,
    render_article_md,
    render_article_styles,
    normalize_styles,
    process_html,
    has_live_php,
    resolve_section_markers,
)


# ════════════════════════════════════════════════════════════════
# 페이지네이션 helper (v0.4.5)
#
# 모든 페이지네이션은 JS DOM hide/show. 서버는 한 페이지에 모든 항목을
# 렌더하고 (SEO 친화), data-per-page 와 함께 pagination_nav HTML 을 같이
# 출력한다. pagination.js 가 `.paginated` 섹션과 그 직후의 `.pagination-nav`
# 를 짝지어 클라이언트에서 hide/show.
#
# 한 페이지에 *여러* 페이지네이션 컨트롤이 있을 수 있으므로
# (예: 톱레벨 카테고리 인덱스의 서브카테고리 섹션들), 각 짝을 명확히
# 묶기 위해 data-pagination-group="<key>" 속성을 사용한다.
# ════════════════════════════════════════════════════════════════


def _pagination_section_attrs(group_key: str, per_page: int) -> str:
    """`.paginated` section 의 data 속성 모음 (group_key, per_page)."""
    safe = escape_html(group_key)
    return f'class="paginated" data-pagination-group="{safe}" data-per-page="{per_page}"'


def _pagination_nav_html(group_key: str, total_items: int, per_page: int) -> str:
    """페이지 컨트롤 HTML.

    items 가 per_page 이하면 빈 문자열 (컨트롤 자체 미출력).
    """
    if per_page <= 0:
        per_page = 1
    pages = (total_items + per_page - 1) // per_page
    if pages <= 1:
        return ''
    safe = escape_html(group_key)
    return (
        f'<nav class="pagination-nav" data-pagination-group="{safe}" '
        f'data-total-pages="{pages}" aria-label="pagination">'
        f'<button type="button" class="pagi-btn pagi-prev" '
        f'aria-label="Previous page" disabled>‹</button>'
        f'<span class="pagi-info"><span class="pagi-current">1</span>'
        f' / <span class="pagi-total">{pages}</span></span>'
        f'<button type="button" class="pagi-btn pagi-next" '
        f'aria-label="Next page">›</button>'
        f'</nav>'
    )
from .seo import build_meta_tags
from .search import (
    html_to_plain,
    build_search_index,
    run_parity_test,
)
from .sitemap import build_sitemap


# ════════════════════════════════════════════════════════════════
# Build / Error helpers
# ════════════════════════════════════════════════════════════════

_warnings = []


def warn(msg: str):
    print(f'[WARN] {msg}', file=sys.stderr)
    _warnings.append(msg)


def die(msg: str):
    print(f'[FAIL] {msg}', file=sys.stderr)
    print('빌드 중단.', file=sys.stderr)
    sys.exit(1)


def warning_count() -> int:
    return len(_warnings)


def _copy_if_newer(src: Path, dst: Path):
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _remove_empty_dirs(root: Path):
    for dirpath, _dirnames, _filenames in os.walk(root, topdown=False):
        p = Path(dirpath)
        if p == root:
            continue
        try:
            p.rmdir()
        except OSError:
            pass


def _load_template(templates_dir: Path, name: str) -> str:
    path = templates_dir / name
    if not path.exists():
        die(f'Template not found: {path}')
    return path.read_text(encoding='utf-8')


def _render_template(template: str, vars: dict) -> str:
    for k, v in vars.items():
        template = template.replace('{{' + k + '}}', str(v) if v is not None else '')
    return template


# ════════════════════════════════════════════════════════════════
# Builder
# ════════════════════════════════════════════════════════════════

class Builder:
    SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$')
    DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')

    def __init__(self, base_dir: Path):
        self.base = base_dir
        self.articles_dir = base_dir / 'Articles'
        self.assets_dir = base_dir / 'assets'
        self.templates_dir = base_dir / 'templates'
        self.dist = base_dir / 'dist'
        self.dist_legacy = base_dir / 'dist-legacy'

        self.site: SiteConfig = None
        self.legacy_map: dict = {}
        self.articles: list = []
        self.slug_to_article: dict = {}
        self.categories: dict = {}      # path_tuple → Category
        self.rendered_bodies: dict = {} # slug → plain text body (검색용)
        # v0.4.6: Articles/meta.yaml — 메인페이지 (루트) 의 카테고리-격 설정.
        # 없으면 기본 CategoryMeta (모든 필드 None / 0).
        self.home_meta: CategoryMeta = CategoryMeta()

    # ── [1] Config load ──────────────────────────────────────

    def _load_config(self):
        site_yaml = self.base / 'site.yaml'
        if not site_yaml.exists():
            die(f'site.yaml not found at {site_yaml}')
        raw = yaml_load(site_yaml.read_text(encoding='utf-8'))

        def get(key, default=None):
            return raw.get(key, default)

        self.site = SiteConfig(
            domain=get('domain', 'siheonlee.com'),
            base_url=get('base_url', 'https://siheonlee.com'),
            name=get('name', 'siheonlee.com'),
            main_title=get('main_title') or get('name', 'siheonlee.com'),
            default_author=get('default_author', ''),
            default_og_image=get('default_og_image', '/assets/default-og.png'),
            default_title_prefix=get('default_title_prefix') or '',
            default_title_suffix=get('default_title_suffix') or '',
            copyright_holder=get('copyright_holder', ''),
            copyright_year_start=get('copyright_year_start', 2025),
            reserved_slugs=get('reserved_slugs') or [],
            warn_on_underscore_ref=bool(get('warn_on_underscore_ref', True)),
            warn_on_missing_asset=bool(get('warn_on_missing_asset', True)),
            warn_on_stale_updated=bool(get('warn_on_stale_updated', True)),
            description_truncate=int(get('description_truncate') or 150),
            robots_txt_main=get('robots_txt_main') or 'User-agent: *\nAllow: /\n',
            robots_txt_legacy=get('robots_txt_legacy') or 'User-agent: *\nAllow: /\n',
            # v0.4.5: i18n + 카테고리 페이지네이션 디폴트.
            # v0.4.6: home_* 류 (home_per_page / home_excludes_categories /
            # home_sort) 는 Articles/meta.yaml 로 이전됨 — 더 이상 site.yaml
            # 에서 읽지 않는다. 옛 site.yaml 에 잔존하더라도 조용히 무시.
            lang=str(get('lang') or 'ko'),
            category_per_page=int(get('category_per_page') or 20),
            category_preview_per_page=int(get('category_preview_per_page') or 5),
        )

        # v0.4.6: 사용자가 옛 home_* 키를 site.yaml 에 그대로 두면 알아채지
        # 못한 채 무시될 수 있으므로 한 번 경고 — 마이그레이션 가이드 역할.
        for legacy_key in ('home_per_page', 'home_excludes_categories', 'home_sort'):
            if legacy_key in raw:
                warn(f"site.yaml: '{legacy_key}' 는 v0.4.6 부터 Articles/meta.yaml "
                     f"로 이전되었습니다. site.yaml 에서 제거하고 Articles/meta.yaml "
                     f"의 해당 필드를 사용하세요.")

        legacy_yaml = self.base / 'legacy-map.yaml'
        if legacy_yaml.exists():
            self.legacy_map = yaml_load(legacy_yaml.read_text(encoding='utf-8'))

        # 토크나이저 패리티 검증 (PHP 없으면 워닝만)
        run_parity_test(self.templates_dir, php_bin='php',
                        warn_fn=warn, die_fn=die)

    # ── [2] Content scan ──────────────────────────────────────

    def _scan_articles(self):
        if not self.articles_dir.is_dir():
            die(f'Articles/ directory not found at {self.articles_dir}')

        for root, dirs, files in os.walk(self.articles_dir):
            root_path = Path(root)

            if is_underscore_path(root_path, self.articles_dir):
                dirs.clear()
                continue

            dirs[:] = [d for d in dirs if not d.startswith('_')]

            if 'meta.yaml' not in files:
                continue

            # v0.4.5: meta.yaml 이 있는 폴더가 '글' 인지 '카테고리' 인지 구분.
            # 글 폴더: content.md / content.html 중 하나가 존재.
            # 카테고리 폴더: 둘 다 없음 (이 경우 meta.yaml 은 카테고리 설정).
            # 카테고리 폴더의 meta.yaml 은 _build_category_tree 에서 처리.
            content_md = root_path / 'content.md'
            content_html = root_path / 'content.html'
            if not content_md.exists() and not content_html.exists():
                continue

            rel = root_path.relative_to(self.articles_dir)
            category_path = list(rel.parts[:-1])
            article_folder = rel.parts[-1]

            if content_md.exists() and content_html.exists():
                die(f'content.md and content.html both exist\n'
                    f'       at {root_path}')

            content_file = content_md if content_md.exists() else content_html

            article = Article(
                meta=None,
                source_dir=root_path,
                content_file=content_file,
                category_path=category_path + [article_folder],
            )
            self.articles.append(article)

    # ── [3] Frontmatter parse ────────────────────────────────

    def _parse_frontmatter(self):
        for article in self.articles:
            meta_file = article.source_dir / 'meta.yaml'
            try:
                raw = yaml_load(meta_file.read_text(encoding='utf-8'))
            except Exception as e:
                die(f'meta.yaml parse error: {e}\n       at {meta_file}')

            slug = raw.get('slug')
            title = raw.get('title')
            date_str = raw.get('date')

            if not slug:
                die(f'slug is empty\n       at {meta_file}')
            if not title:
                die(f'title is empty\n       at {meta_file}')
            if not date_str:
                die(f'date is missing\n       at {meta_file}')

            date_str = str(date_str)
            updated = str(raw.get('updated')) if raw.get('updated') else None
            noindex_raw = raw.get('noindex')
            noindex = bool(noindex_raw) if noindex_raw is not None else False
            # v0.4.5: 글 단위 lang override. 비우면 site.lang.
            lang_val = raw.get('lang')
            lang = str(lang_val) if lang_val else None

            seo_raw = raw.get('seo') or {}
            if not isinstance(seo_raw, dict):
                die(f"meta.yaml: 'seo' 는 매핑이어야 합니다\n       at {meta_file}")

            def _seo_str(key):
                v = seo_raw.get(key)
                return v if v else None

            seo = SeoMeta(
                title_prefix=seo_raw.get('title_prefix'),
                title_suffix=seo_raw.get('title_suffix'),
                description=_seo_str('description'),
                author=_seo_str('author'),
                canonical=_seo_str('canonical'),
                og_title=_seo_str('og_title'),
                og_description=_seo_str('og_description'),
                og_image=_seo_str('og_image'),
                og_image_alt=_seo_str('og_image_alt'),
                og_type=seo_raw.get('og_type') or 'article',
                twitter_card=seo_raw.get('twitter_card') or 'summary_large_image',
                twitter_image=_seo_str('twitter_image'),
            )

            article.meta = ArticleMeta(
                slug=slug,
                title=title,
                date=date_str,
                updated=updated,
                noindex=noindex,
                lang=lang,
                seo=seo,
                styles=normalize_styles(raw.get('styles')),
            )

    # ── [4] Validation + category tree ───────────────────────

    def _validate(self):
        seen_slugs = {}

        for article in self.articles:
            m = article.meta
            meta_path = article.source_dir / 'meta.yaml'

            if not self.SLUG_RE.match(m.slug):
                die(f'slug 정규식 불일치: {repr(m.slug)}\n       at {meta_path}')

            if m.slug in self.site.reserved_slugs:
                die(f'slug 예약어: {repr(m.slug)}\n       at {meta_path}')

            if m.slug in seen_slugs:
                other = seen_slugs[m.slug]
                die(f"slug 충돌: '{m.slug}'\n"
                    f"       at {meta_path}\n"
                    f"          {other / 'meta.yaml'}")
            seen_slugs[m.slug] = article.source_dir

            if not self.DATE_RE.match(m.date):
                die(f'date 형식 오류: {repr(m.date)}\n       at {meta_path}')

            if m.updated:
                if not self.DATE_RE.match(m.updated):
                    die(f'updated 형식 오류: {repr(m.updated)}\n       at {meta_path}')
                if m.updated < m.date:
                    die(f'updated < date\n       at {meta_path}')

        for url_path, slug in self.legacy_map.items():
            if slug is not None and slug not in seen_slugs:
                die(f"legacy-map.yaml: slug '{slug}' 미존재\n"
                    f"       ('{url_path}' 항목)")

        self.slug_to_article = {a.meta.slug: a for a in self.articles}

        # v0.4.6: Articles/meta.yaml (메인페이지 카테고리-격 설정) 파싱.
        self._load_home_meta()

        self._build_category_tree()

        # 글 slug ↔ 톱레벨 카테고리 slug 충돌 검증 (v0.4.2).
        # 둘 다 dist/{slug}/index.html 자리에 떨어지므로, _prune_orphans 의
        # 사후 정리에 맡기지 말고 검증 단계에서 차단한다.
        cat_slugs = {
            cat.slug: cat
            for cat in self.categories.values()
            if len(cat.path) == 1
        }
        for article in self.articles:
            if article.meta.slug in cat_slugs:
                cat = cat_slugs[article.meta.slug]
                die(f"slug 충돌 (글 ↔ 카테고리): {repr(article.meta.slug)}\n"
                    f"       at {article.source_dir / 'meta.yaml'}\n"
                    f"          (카테고리 폴더: Articles/{'/'.join(cat.path)})")

        for cat in self.categories.values():
            all_articles = self._collect_articles(cat)
            if not all_articles:
                warn(f'empty category: {"/".join(cat.path)}')

        if self.site.warn_on_stale_updated:
            for article in self.articles:
                if article.meta.updated and article.content_file:
                    try:
                        mtime = Date.fromtimestamp(
                            article.content_file.stat().st_mtime
                        ).isoformat()
                        if mtime > article.meta.updated:
                            warn(f'{article.meta.slug}: meta updated may be stale '
                                 f'(file mtime {mtime} > updated {article.meta.updated})')
                    except Exception:
                        pass

    def _build_category_tree(self):
        """v0.4.5: 카테고리 폴더의 meta.yaml 도 파싱한다.

        v0.4.0: _meta.yaml 오버라이드 코드 경로 제거.
        한국어 등 비ASCII 폴더명은 slugs.category_slug_from_name 이
        결정론적으로 ASCII 코드포인트 hex 로 변환한다. 경고는 한 번만 (폴더당).
        v0.4.5 에서 워닝 메시지를 보강해, 어떤 폴더명이 어떤 hex slug 로
        변환되었는지 빌드 로그에서 한눈에 보이도록 한다.
        """
        cat_paths = set()
        for article in self.articles:
            cat = article.category_path[:-1]
            for depth in range(1, len(cat) + 1):
                cat_paths.add(tuple(cat[:depth]))

        warned_folders = set()

        def to_slug(folder_name: str, full_path_for_warn) -> str:
            s = category_slug_from_name(folder_name)
            if not s:
                die(f'카테고리 slug 빈 문자열: {folder_name}\n'
                    f"       (Articles/{'/'.join(full_path_for_warn)})")
            if has_non_ascii(folder_name) and folder_name not in warned_folders:
                warn(
                    f"URL slug 에 비ASCII 문자 포함: '{folder_name}' → '{s}'\n"
                    f"       (Articles/{'/'.join(full_path_for_warn)})\n"
                    f"       빌드는 정상 진행되었으나, URL 가독성/공유성을 위해 "
                    f"폴더명을 ASCII (영문/숫자/하이픈) 로 바꾸는 것을 권장합니다."
                )
                warned_folders.add(folder_name)
            return s

        for path_tuple in sorted(cat_paths, key=lambda p: (len(p), p)):
            folder_name = path_tuple[-1]
            slug = to_slug(folder_name, list(path_tuple))

            slug_path = [
                to_slug(part, list(path_tuple[:i + 1]))
                for i, part in enumerate(path_tuple)
            ]

            cat = Category(
                folder_name=folder_name,
                slug=slug,
                path=list(path_tuple),
                slug_path=slug_path,
                meta=self._parse_category_meta(path_tuple),
            )
            self.categories[path_tuple] = cat

        for path_tuple, cat in self.categories.items():
            if len(path_tuple) > 1:
                parent_path = path_tuple[:-1]
                if parent_path in self.categories:
                    parent = self.categories[parent_path]
                    if cat not in parent.children:
                        parent.children.append(cat)

        for article in self.articles:
            cat_path = tuple(article.category_path[:-1])
            if cat_path in self.categories:
                cat = self.categories[cat_path]
                if article not in cat.articles:
                    cat.articles.append(article)

    def _parse_category_meta(self, path_tuple) -> CategoryMeta:
        """`Articles/<카테고리경로>/meta.yaml` 파일 (있으면) 파싱.

        없으면 모든 필드가 None 인 기본 CategoryMeta.
        per_page / preview_per_page 가 None 이면 사이트 디폴트가 적용됨.
        """
        cat_dir = self.articles_dir.joinpath(*path_tuple)
        return self._parse_category_meta_file(cat_dir / 'meta.yaml')

    def _parse_category_meta_file(self, meta_file: Path) -> CategoryMeta:
        """임의 경로의 meta.yaml 을 CategoryMeta 로 파싱 (v0.4.6 helper).

        `Articles/meta.yaml` (루트 = 메인페이지) 와 카테고리 폴더의 meta.yaml
        둘 다에 동일한 파싱 로직 적용. 글 폴더의 meta.yaml 과 헷갈리지 않도록
        slug/title/date 가 있으면 카테고리 meta.yaml 로 취급하지 않는다.
        """
        if not meta_file.exists():
            return CategoryMeta()

        try:
            raw = yaml_load(meta_file.read_text(encoding='utf-8'))
        except Exception as e:
            die(f'카테고리 meta.yaml parse error: {e}\n'
                f"       at {meta_file}")

        if raw is None:
            raw = {}
        if 'slug' in raw or 'title' in raw or 'date' in raw:
            # 글 폴더의 meta.yaml 이 우연히 카테고리처럼 잡힌 경우 — 카테고리
            # meta.yaml 로 취급하지 않는다 (실제로는 _scan_articles 가 글로
            # 분류했을 것이므로, path_tuple 이 카테고리이면 이 경우는 발생하지
            # 않아야 정상).
            return CategoryMeta()

        per_page = raw.get('per_page')
        preview = raw.get('preview_per_page')
        layout = raw.get('layout') or 'list'
        lang_val = raw.get('lang')
        styles_raw = raw.get('styles')
        # v0.4.6: priority. 빈값/누락이면 0. 정수만 허용.
        priority_raw = raw.get('priority')
        if priority_raw is None:
            priority = 0
        else:
            try:
                priority = int(priority_raw)
            except (TypeError, ValueError):
                die(f"meta.yaml: 'priority' 는 정수여야 합니다 (받은 값: "
                    f"{priority_raw!r})\n       at {meta_file}")

        # v0.4.6: excludes_categories. 홈 (Articles/meta.yaml) 에서만 의미를
        # 가진다 — 카테고리 meta.yaml 에 들어있어도 파싱만 되고 사용되지 않음.
        excludes_raw = raw.get('excludes_categories')
        if excludes_raw is None:
            excludes = []
        elif isinstance(excludes_raw, list):
            excludes = [str(x) for x in excludes_raw]
        else:
            die(f"meta.yaml: 'excludes_categories' 는 리스트여야 합니다 (받은 값: "
                f"{excludes_raw!r})\n       at {meta_file}")

        return CategoryMeta(
            per_page=int(per_page) if per_page is not None else None,
            preview_per_page=int(preview) if preview is not None else None,
            layout=str(layout),
            lang=str(lang_val) if lang_val else None,
            styles=normalize_styles(styles_raw),
            priority=priority,
            excludes_categories=excludes,
        )

    def _load_home_meta(self):
        """v0.4.6: Articles/meta.yaml 파싱 (메인페이지의 카테고리-격 설정).

        없으면 모든 필드가 기본값인 CategoryMeta. _build_category_tree 와
        독립적으로 동작 — Articles/ 루트는 self.categories 의 path_tuple ()
        로 들어가지 않는다 (루트는 카테고리가 아니라 사이트 자체).
        """
        self.home_meta = self._parse_category_meta_file(
            self.articles_dir / 'meta.yaml'
        )

    # v0.4.6: Articles/meta.yaml 이 통째로 없거나 per_page 가 비어 있을 때
    # 적용되는 코드 디폴트. site.yaml 에서 home_per_page 가 제거된 자리.
    HOME_PER_PAGE_DEFAULT = 5

    def _home_per_page(self) -> int:
        """메인페이지 Recent posts 의 페이지당 글 수.

        Articles/meta.yaml 의 per_page 가 있으면 그 값, 없으면 코드 디폴트
        (Builder.HOME_PER_PAGE_DEFAULT).
        """
        if self.home_meta.per_page is not None:
            return self.home_meta.per_page
        return self.HOME_PER_PAGE_DEFAULT

    def _category_per_page(self, cat: Category) -> int:
        """카테고리 자기 인덱스 페이지의 페이지당 글 수."""
        if cat.meta.per_page is not None:
            return cat.meta.per_page
        return self.site.category_per_page

    def _category_preview_per_page(self, cat: Category) -> int:
        """카테고리가 상위 인덱스 페이지의 section 으로 임베드될 때의 페이지당 글 수."""
        if cat.meta.preview_per_page is not None:
            return cat.meta.preview_per_page
        return self.site.category_preview_per_page

    def _collect_articles(self, cat: Category) -> list:
        result = list(cat.articles)
        for child in cat.children:
            result.extend(self._collect_articles(child))
        return result

    # ── [5] Article render + output ──────────────────────────

    def _copyright_year(self) -> str:
        return str(datetime.date.today().year)

    def _top_level_entries(self) -> list:
        """Articles/ 직속 항목을 [(folder_name, slug, is_article), ...] 로 반환.

        v0.4.5: 카테고리 폴더에도 meta.yaml 이 있을 수 있으므로, meta.yaml
        존재만으로 '글' 인지 판단하지 않는다. _scan_articles 에서 이미
        분류한 self.articles 리스트와 source_dir 매칭으로 결정.
        """
        if not self.articles_dir.is_dir():
            return []

        entries = []
        for child in self.articles_dir.iterdir():
            if not child.is_dir():
                continue
            if child.name.startswith('_'):
                continue
            article = next(
                (a for a in self.articles if a.source_dir == child),
                None,
            )
            if article is not None:
                entries.append((child.name, article.meta.slug, True))
            else:
                key = (child.name,)
                cat = self.categories.get(key)
                slug = cat.slug if cat else category_slug_from_name(child.name)
                entries.append((child.name, slug, False))

        # v0.4.6: About 은 그대로 최상단 고정. 나머지는 (priority desc,
        # folder_name asc) 로 정렬. priority 는 카테고리 meta.yaml 에서 옴 —
        # 글 항목은 priority 가 없으므로 0 으로 간주.
        def _entry_priority(name: str) -> int:
            key = (name,)
            cat = self.categories.get(key)
            return cat.meta.priority if cat else 0

        about = [e for e in entries if e[0] == 'About']
        others = sorted(
            (e for e in entries if e[0] != 'About'),
            key=lambda e: (-_entry_priority(e[0]), e[0]),
        )
        return about + others

    def _nav_links_html(self) -> str:
        entries = self._top_level_entries()
        if not entries:
            return ''
        parts = []
        for folder, slug, _is_article in entries:
            parts.append(f"<a href='/{slug}/'>{escape_html(folder)}</a>")
        return '<span>|</span> '.join(parts)

    def _nav_tracker_for_path(self, breadcrumb_parts: list) -> str:
        html = "<a href='/'>Home</a>"
        for label, url in breadcrumb_parts:
            label_safe = escape_html(label)
            if url is None:
                html += (f"<a onClick='window.location.reload()' "
                         f"style='cursor: pointer;'> / {label_safe} </a>")
            else:
                html += f"<a href='{url}'> / {label_safe}</a>"
        return html

    def _top_category_for_article(self, article: 'Article'):
        if not article.category_path or len(article.category_path) < 2:
            return None
        top = (article.category_path[0],)
        return self.categories.get(top)

    def _render_articles(self):
        tpl = _load_template(self.templates_dir, 'article.html')
        nav_links = self._nav_links_html()

        for article in self.articles:
            m = article.meta
            content_path = article.content_file

            if not content_path or not content_path.exists():
                warn(f'{m.slug}: content file not found, skipping')
                continue

            content_text = content_path.read_text(encoding='utf-8')

            if content_path.suffix == '.md':
                rr = render_article_md(
                    content_text, m.slug, article.source_dir,
                )
                # v0.4.3: 본문 자동 첫 갭 + 섹션 마커 (===제목===, ======) 처리.
                body_html = resolve_section_markers(rr.html, m.title)
            else:
                rr = process_html(content_text, m.slug, article.source_dir)
                body_html = rr.html

            self.rendered_bodies[m.slug] = html_to_plain(rr.html)

            article_styles = render_article_styles(m.styles)

            if self.site.warn_on_underscore_ref:
                for pattern in [r'src="([^"]+)"', r'href="([^"]+)"']:
                    for url_match in re.finditer(pattern, rr.html):
                        ref = url_match.group(1)
                        if '/_' in ref or ref.startswith('_'):
                            warn(f'{m.slug}: referenced excluded asset {ref}')

            meta_tags, full_title = build_meta_tags(article, rr, self.site)

            crumb_parts = []
            top_cat = self._top_category_for_article(article)
            if top_cat:
                top_url = f"/{top_cat.slug}/"
                crumb_parts.append((top_cat.folder_name, top_url))
                middle_folders = article.category_path[1:-1]
                for folder in middle_folders:
                    crumb_parts.append((folder, top_url))
            crumb_parts.append((article.category_path[-1], None))
            nav_tracker = self._nav_tracker_for_path(crumb_parts)

            # noindex 가 켜진 글은 robots meta 한 줄을 넣고, 꺼진 글은
            # placeholder 가 자리한 라인 자체를 통째로 제거 — 빈 줄 잔존 방지.
            # v0.4.2: 들여쓰기에 무관하게 라인 단위로 제거 (이전 버전은
            # '    {{ROBOTS_META}}\n' 4공백 하드코딩).
            if m.noindex:
                tpl_local = tpl.replace(
                    '{{ROBOTS_META}}',
                    "<meta name='robots' content='noindex'>",
                )
            else:
                tpl_local = re.sub(
                    r'^[ \t]*\{\{ROBOTS_META\}\}[ \t]*\r?\n',
                    '',
                    tpl,
                    flags=re.MULTILINE,
                )

            # v0.4.3: <title> 에 글 제목 사용. full_title 은
            # build_meta_tags 가 만든 `{prefix}{title}{suffix}` 문자열.
            page_title = full_title or self.site.name

            # v0.4.5: 글 단위 lang override (없으면 site.lang).
            page_lang = m.lang or self.site.lang

            vars_ = {
                'LANG': escape_html(page_lang),
                'META_TAGS': meta_tags,
                'ARTICLE_STYLES': article_styles,
                'PAGE_TITLE': escape_html(page_title),
                'MAIN_TITLE': escape_html(self.site.main_title),
                'NAV_TRACKER': nav_tracker,
                'NAV_LINKS': nav_links,
                'BODY': body_html,
                'COPYRIGHT_YEAR': self._copyright_year(),
                'COPYRIGHT_HOLDER': escape_html(self.site.copyright_holder),
            }
            page_html = _render_template(tpl_local, vars_)

            ext = 'php' if has_live_php(page_html) else 'html'

            out_dir = self.dist / m.slug
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f'index.{ext}'
            out_file.write_text(page_html, encoding='utf-8')

    # ── [6] Asset sync ────────────────────────────────────────

    def _sync_assets(self):
        for article in self.articles:
            m = article.meta
            src_root = article.source_dir
            dst_root = self.dist / 'src' / m.slug

            for src_file in src_root.rglob('*'):
                if not src_file.is_file():
                    continue
                if is_underscore_path(src_file, src_root):
                    continue
                if src_file.name in ('meta.yaml', 'content.md', 'content.html'):
                    continue
                rel = src_file.relative_to(src_root)
                dst_file = dst_root / rel
                _copy_if_newer(src_file, dst_file)

            self._prune_article_assets(article)

    def _prune_article_assets(self, article: Article):
        m = article.meta
        src_root = article.source_dir
        dst_root = self.dist / 'src' / m.slug
        if not dst_root.exists():
            return

        expected = set()
        for src_file in src_root.rglob('*'):
            if not src_file.is_file():
                continue
            if is_underscore_path(src_file, src_root):
                continue
            if src_file.name in ('meta.yaml', 'content.md', 'content.html'):
                continue
            rel = src_file.relative_to(src_root)
            expected.add(dst_root / rel)

        for existing in list(dst_root.rglob('*')):
            if existing.is_file() and existing not in expected:
                existing.unlink()

        _remove_empty_dirs(dst_root)

    # ── [7] Category indexes ──────────────────────────────────

    def _listup_module_html(self, article: 'Article', hidden: bool = False) -> str:
        """글 한 줄의 listup HTML.

        v0.4.6: hidden=True 면 `style='display:none'` 를 inline 으로 부착.
        SSR 시점에 페이지네이션의 비활성 페이지 항목을 미리 숨겨 FOUC 를 방지.
        pagination.js 는 그 후에 첫 페이지 항목의 inline style 을 비워
        (`style.display=''`) 정상 표시한다.
        """
        link_text = article.meta.title
        style_attr = " style='display:none'" if hidden else ""
        return (f"<div class='listup_module_div'{style_attr}>"
                f"<span class='listup_module_title'>"
                f"<a href='/{article.meta.slug}/'> "
                f"{escape_html(link_text)} </a>"
                f"</span>"
                f"<span class='listup_module_date'> &nbsp;&nbsp; "
                f"{article.meta.date}</span>"
                f"</div>")

    def _listup_items_html(self, articles, per_page: int) -> str:
        """v0.4.6: 페이지네이션이 부착된 항목 목록 HTML.

        per_page 가 0 이하면 모든 항목을 그대로 출력. 그 외에는 per_page 초과
        인덱스의 항목에 `style='display:none'` 을 미리 부착하여 FOUC 방지.
        """
        parts = []
        for i, a in enumerate(articles):
            hidden = per_page > 0 and i >= per_page
            parts.append(self._listup_module_html(a, hidden=hidden))
        return '\n'.join(parts)

    def _render_section(self, label: str, articles: list, group_key: str,
                        per_page: int, more_url: str = None) -> str:
        """페이지네이션이 부착된 한 개의 section HTML 을 반환.

        articles 는 이미 정렬되어 있어야 한다.
        group_key 는 같은 페이지 내에서 unique 해야 한다 (페이지 컨트롤 짝짓기).
        more_url 이 주어지면 section 우측 상단에 → 링크가 표시된다.
        """
        if not articles:
            inner = "<p>No articles found</p>"
            attrs = "class='paginated-empty'"
            nav_html = ''
        else:
            attrs = _pagination_section_attrs(group_key, per_page)
            # v0.4.6: per_page 를 넘는 항목은 SSR 단계에서 inline style 로
            # 미리 숨겨 FOUC 를 방지.
            inner = self._listup_items_html(articles, per_page)
            nav_html = _pagination_nav_html(group_key, len(articles), per_page)

        if more_url:
            label_html = (
                f"{escape_html(label)} "
                f"<a class='more-link' href='{more_url}'>→</a>"
            )
        else:
            label_html = escape_html(label)

        return (
            f"<div class='gap'><p>{label_html}</p></div>\n"
            f"<section {attrs}>\n{inner}\n</section>\n"
            f"{nav_html}"
        )

    def _category_styles_html(self, cat: Category) -> str:
        """카테고리 meta.yaml 의 styles → <style> 블록.

        section TAG 선택자로 글 styles 와 동일한 우선순위 정책 적용.
        """
        return render_article_styles(cat.meta.styles)

    def _build_category_page(self, cat: Category):
        """톱레벨/서브카테고리 공용 인덱스 페이지 빌더 (v0.4.5).

        - 톱레벨 카테고리: 자식 서브카테고리마다 section 한 개씩.
                          자식이 없으면 (이 카테고리의 직속 articles 만 있는 경우)
                          자기 자신을 한 section 으로.
        - 서브카테고리: 자기 자신을 한 section 으로. 만약 더 깊은 자식이
                       있다면 (3+ depth) 자식별 section 도 추가로.
        - 페이지네이션: section 마다 독립 (data-pagination-group 으로 짝지음).
        - styles: 이 카테고리의 meta.yaml 의 styles 가 head 의 <style> 로.
        - lang: 카테고리 meta.yaml 의 lang 우선, 없으면 site.lang.
        """
        tpl = _load_template(self.templates_dir, 'category.html')
        nav_links = self._nav_links_html()

        is_top = len(cat.path) == 1

        # URL prefix — 톱레벨이면 "/{slug}/", 서브이면 "/{top}/{sub}/"
        url_prefix = '/' + '/'.join(cat.slug_path) + '/'

        sections = []
        # v0.4.6: 자식 카테고리 정렬은 priority 내림차순 (큰 값 먼저), 같은
        # priority 끼리는 folder_name 알파벳 오름차순.
        sorted_children = sorted(
            cat.children,
            key=lambda c: (-c.meta.priority, c.folder_name),
        )

        # 자식 서브카테고리가 있는 경우 — 자식별로 section 생성.
        # 톱레벨이면 "더 보기" 링크가 자식의 자기 페이지 (`/top/sub/`) 로.
        for child in sorted_children:
            articles = self._collect_articles(child)
            articles.sort(key=lambda a: a.meta.date, reverse=True)
            child_url = '/' + '/'.join(child.slug_path) + '/'
            group_key = f"cat-{'-'.join(child.slug_path)}"
            sections.append(
                self._render_section(
                    label=child.folder_name,
                    articles=articles,
                    group_key=group_key,
                    per_page=self._category_preview_per_page(child),
                    more_url=child_url,
                )
            )

        # 이 카테고리 직속 글들이 있는 경우 또는 자식이 없는 경우 — 자신을 section 으로.
        # (자식이 있어도 직속 글이 있을 수 있다 — 그러면 둘 다 표시.)
        own_articles = sorted(cat.articles, key=lambda a: a.meta.date, reverse=True)
        if own_articles or not sorted_children:
            if not is_top and not sorted_children:
                # 서브카테고리의 자기 페이지에서, 자식이 없는 경우 — 큰 per_page 사용.
                section_per_page = self._category_per_page(cat)
            elif is_top and not sorted_children:
                # 톱레벨인데 자식이 없는 경우 — 자기 자신이 글 목록의 본진.
                # (예: Blog 직속 글들만 있는 현 상태)
                section_per_page = self._category_per_page(cat)
            else:
                # 자식이 있는데 직속 글도 있는 경우 — 톱레벨이면 preview,
                # 서브이면 per_page.
                section_per_page = (
                    self._category_preview_per_page(cat) if is_top
                    else self._category_per_page(cat)
                )

            group_key = f"cat-{'-'.join(cat.slug_path)}-own"
            sections.append(
                self._render_section(
                    label=cat.folder_name,
                    articles=own_articles,
                    group_key=group_key,
                    per_page=section_per_page,
                )
            )

        subcategory_sections = '\n'.join(sections) if sections else (
            f"<div class='gap'><p>{escape_html(cat.folder_name)}</p></div>\n"
            f"<section><p>No articles found</p></section>"
        )

        # breadcrumb: 톱레벨이면 [(folder, url)], 서브면 [(top, top_url), (sub, None)]
        if is_top:
            crumb_parts = [(cat.folder_name, url_prefix)]
        else:
            top_cat = self.categories.get((cat.path[0],))
            crumb_parts = []
            if top_cat is not None:
                crumb_parts.append((top_cat.folder_name, f"/{top_cat.slug}/"))
            # 중간 폴더들 (3+ depth) → 가장 가까운 톱레벨로 링크 (원본 quirk 와 일치).
            for mid_folder in cat.path[1:-1]:
                crumb_parts.append(
                    (mid_folder,
                     f"/{top_cat.slug}/" if top_cat else None)
                )
            crumb_parts.append((cat.folder_name, None))
        nav_tracker = self._nav_tracker_for_path(crumb_parts)

        page_title = self.site.name
        page_lang = cat.meta.lang or self.site.lang

        # 검색 스코프: 톱레벨이면 자기 slug, 서브이면 톱레벨 slug 로 한정.
        # (search-index 의 category_slug 가 톱레벨 slug 만 갖기 때문.)
        search_cat = cat.slug_path[0]

        vars_ = {
            'LANG': escape_html(page_lang),
            'PAGE_TITLE': escape_html(page_title),
            'MAIN_TITLE': escape_html(self.site.main_title),
            'NAV_TRACKER': nav_tracker,
            'NAV_LINKS': nav_links,
            'NAV_SEARCH_CAT': escape_html(search_cat),
            'SUBCATEGORY_SECTIONS': subcategory_sections,
            'CATEGORY_STYLES': self._category_styles_html(cat),
            'COPYRIGHT_YEAR': self._copyright_year(),
            'COPYRIGHT_HOLDER': escape_html(self.site.copyright_holder),
        }
        page_html = _render_template(tpl, vars_)

        out_dir = self.dist.joinpath(*cat.slug_path)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / 'index.html').write_text(page_html, encoding='utf-8')

    def _build_categories(self):
        """v0.4.5: 톱레벨 + 모든 서브카테고리에 대해 인덱스 페이지 생성.

        v0.4.4 까지는 톱레벨만 인덱스가 있었음 (원본 lama.pe.kr quirk 보존).
        v0.4.5 에서 이 quirk 를 해제 — 서브카테고리도 자기 인덱스 페이지를 가짐.
        """
        # 빈 카테고리 (글이 한 편도 없는 카테고리 트리) 는 인덱스 페이지를
        # 만들지 않는다. _validate 가 이미 워닝을 띄웠음.
        for path_tuple, cat in self.categories.items():
            subtree = self._collect_articles(cat)
            if not subtree:
                continue
            self._build_category_page(cat)

    # ── [8] Home page ─────────────────────────────────────────

    def _build_home(self):
        tpl = _load_template(self.templates_dir, 'home.html')

        # v0.4.6: 홈 전용 설정은 site.yaml 이 아니라 Articles/meta.yaml 에서.
        exclude_top = set(self.home_meta.excludes_categories)

        # category_path 는 _scan_articles 가 [..., article_folder] 형태로 채우므로
        # 항상 1+ 요소이며, [0] 은 (a) 톱레벨 카테고리 폴더명 (글이 카테고리 안에
        # 있을 때) 또는 (b) 톱레벨 글 폴더명 자체 (About 처럼). 두 경우 모두 같은
        # 검사 한 번으로 처리 — v0.4.7 에서 중복 검사 분기를 정리.
        home_articles = [
            a for a in self.articles
            if not (a.category_path and a.category_path[0] in exclude_top)
        ]

        home_articles.sort(key=lambda a: a.meta.date, reverse=True)

        # v0.4.6: Articles/meta.yaml 의 per_page 가 site 디폴트를 오버라이드.
        per_page = self._home_per_page()
        # v0.4.6: per_page 초과 항목은 SSR 단계에서 미리 hide (FOUC 방지).
        article_items = self._listup_items_html(home_articles, per_page)

        # v0.4.6: 메인페이지 lang — Articles/meta.yaml 의 lang 우선, 없으면 site.lang.
        page_lang = self.home_meta.lang or self.site.lang
        page_title = self.site.name
        pagination_nav = _pagination_nav_html(
            'home-recent', len(home_articles), per_page,
        )

        vars_ = {
            'LANG': escape_html(page_lang),
            'PAGE_TITLE': escape_html(page_title),
            'MAIN_TITLE': escape_html(self.site.main_title),
            'NAV_LINKS': self._nav_links_html(),
            'HOME_PER_PAGE': str(per_page),
            'ARTICLE_LIST': article_items,
            'PAGINATION_NAV': pagination_nav,
            'COPYRIGHT_YEAR': self._copyright_year(),
            'COPYRIGHT_HOLDER': escape_html(self.site.copyright_holder),
        }
        page_html = _render_template(tpl, vars_)
        self.dist.mkdir(parents=True, exist_ok=True)
        (self.dist / 'index.html').write_text(page_html, encoding='utf-8')

    # ── [9] Site assets ───────────────────────────────────────

    def _copy_site_assets(self):
        if not self.assets_dir.is_dir():
            return
        dst_assets = self.dist / 'assets'
        dst_assets.mkdir(parents=True, exist_ok=True)
        for src_file in self.assets_dir.rglob('*'):
            if src_file.is_file():
                rel = src_file.relative_to(self.assets_dir)
                _copy_if_newer(src_file, dst_assets / rel)

    # ── [10] 404 page ─────────────────────────────────────────

    def _build_404(self):
        tpl = _load_template(self.templates_dir, '404.html')
        page_title = 'Error 404'
        vars_ = {
            'LANG': escape_html(self.site.lang),
            'PAGE_TITLE': escape_html(page_title),
            'MAIN_TITLE': escape_html(self.site.main_title),
            'NAV_LINKS': self._nav_links_html(),
            'COPYRIGHT_YEAR': self._copyright_year(),
            'COPYRIGHT_HOLDER': escape_html(self.site.copyright_holder),
        }
        page_html = _render_template(tpl, vars_)
        self.dist.mkdir(parents=True, exist_ok=True)
        (self.dist / '404.html').write_text(page_html, encoding='utf-8')

    # ── [11] robots.txt ───────────────────────────────────────

    def _build_robots(self):
        self.dist.mkdir(parents=True, exist_ok=True)
        (self.dist / 'robots.txt').write_text(
            self.site.robots_txt_main, encoding='utf-8'
        )
        self.dist_legacy.mkdir(parents=True, exist_ok=True)
        (self.dist_legacy / 'robots.txt').write_text(
            self.site.robots_txt_legacy, encoding='utf-8'
        )

    # ── [12] sitemap.xml ──────────────────────────────────────

    def _build_sitemap(self):
        # v0.4.6: home_excludes_categories 가 site.yaml 에서 Articles/meta.yaml
        # 로 이전됨. sitemap.py 가 홈 lastmod 계산용으로 그 값을 필요로 하므로
        # home_meta 를 함께 넘긴다.
        xml = build_sitemap(
            self.articles, self.categories, self.site, self.home_meta,
        )
        self.dist.mkdir(parents=True, exist_ok=True)
        (self.dist / 'sitemap.xml').write_text(xml, encoding='utf-8')

    # ── [13] Legacy dispatcher ────────────────────────────────

    def _build_dispatcher(self):
        # v0.4.2: site.yaml 의 base_url 을 사용 (이전 버전은 도메인 하드코딩).
        base_url = self.site.base_url.rstrip('/')
        base_url_php = base_url.replace("'", "\\'")

        lines = ["<?php"]
        lines.append(f"$BASE_URL = '{base_url_php}';")
        lines.append("$map = [")
        for url_path, slug in self.legacy_map.items():
            key_escaped = url_path.replace("'", "\\'")
            if slug is None:
                lines.append(f"    '{key_escaped}' => null,")
            else:
                lines.append(f"    '{key_escaped}' => '{slug}',")
        lines.append("];")
        lines.append("")
        lines.append("$path = urldecode(parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH));")
        lines.append("$path = rtrim($path, '/') . '/';")
        lines.append("")
        lines.append("if (array_key_exists($path, $map)) {")
        lines.append("    $slug = $map[$path];")
        lines.append("    if ($slug === null) {")
        lines.append("        http_response_code(410);")
        lines.append("        echo '410 Gone';")
        lines.append("        exit;")
        lines.append("    }")
        lines.append("    header(\"Location: {$BASE_URL}/{$slug}/\", true, 301);")
        lines.append("    exit;")
        lines.append("}")
        lines.append("")
        lines.append("http_response_code(404);")
        lines.append("header(\"Location: {$BASE_URL}/404.html\", true, 302);")
        lines.append("exit;")

        self.dist_legacy.mkdir(parents=True, exist_ok=True)
        (self.dist_legacy / 'redirect.php').write_text(
            '\n'.join(lines), encoding='utf-8'
        )

    # ── [14] Search index + search.php + tokenizer lib ──────

    def _build_search(self):
        index_data = build_search_index(
            self.articles,
            self.rendered_bodies,
            self.categories,
            self._top_category_for_article,
        )

        self.dist.mkdir(parents=True, exist_ok=True)
        (self.dist / 'search-index.json').write_text(
            json.dumps(index_data, ensure_ascii=False, separators=(',', ':')),
            encoding='utf-8',
        )

        # search_tokenize.php 를 dist 에 복사 (search.php 가 require_once)
        tok_src = self.templates_dir / 'search_tokenize.php'
        if not tok_src.exists():
            die(f'templates/search_tokenize.php not found')
        (self.dist / 'search_tokenize.php').write_text(
            tok_src.read_text(encoding='utf-8'),
            encoding='utf-8',
        )

        tpl_path = self.templates_dir / 'search.php'
        if not tpl_path.exists():
            warn('templates/search.php not found, skipping search page build')
            return
        tpl = tpl_path.read_text(encoding='utf-8')
        vars_ = {
            'LANG': escape_html(self.site.lang),
            'PAGE_TITLE': escape_html(self.site.name),
            'MAIN_TITLE': escape_html(self.site.main_title),
            'NAV_LINKS': self._nav_links_html(),
            'COPYRIGHT_YEAR': self._copyright_year(),
            'COPYRIGHT_HOLDER': escape_html(self.site.copyright_holder),
        }
        page = _render_template(tpl, vars_)
        (self.dist / 'search.php').write_text(page, encoding='utf-8')

    # ── [15] Global orphan pruning ────────────────────────────

    def _prune_orphans(self):
        current_slugs = {a.meta.slug for a in self.articles}
        current_cat_slug_paths = {tuple(c.slug_path) for c in self.categories.values()}

        if self.dist.is_dir():
            for d in self.dist.iterdir():
                if not d.is_dir():
                    continue
                name = d.name
                if name in ('src', 'assets'):
                    continue
                if (d / 'index.html').exists() or (d / 'index.php').exists():
                    if name not in current_slugs:
                        is_cat = any(sp[0] == name for sp in current_cat_slug_paths
                                     if sp)
                        if not is_cat:
                            shutil.rmtree(d)

        # v0.4.5: 서브카테고리 인덱스 페이지가 신설되면서, 서브카테고리 폴더의
        # 잔재도 정리할 필요가 생김. 톱레벨 카테고리 dir 안쪽을 재귀적으로
        # 확인해 현재 self.categories 에 없는 slug_path 의 서브카테고리 인덱스
        # 폴더를 삭제한다.
        for sp in list(current_cat_slug_paths):
            if len(sp) < 1:
                continue
            top_dir = self.dist / sp[0]
            if not top_dir.is_dir():
                continue
            # top_dir 의 직속 자식 폴더 중, 인덱스가 있고 sub_slug_path 에 없으면 삭제.
            for sub in top_dir.iterdir():
                if not sub.is_dir():
                    continue
                expected = (sp[0], sub.name)
                if any(tuple(c.slug_path) == expected
                       for c in self.categories.values()):
                    continue
                # 폴더 안에 index.html 하나만 남아 있는 경우에만 stale 로 간주.
                # (다른 콘텐츠가 있으면 함부로 삭제하지 않음.)
                try:
                    items = list(sub.iterdir())
                except OSError:
                    continue
                if len(items) == 1 and items[0].name == 'index.html':
                    shutil.rmtree(sub)

        src_dir = self.dist / 'src'
        if src_dir.is_dir():
            for d in src_dir.iterdir():
                if d.is_dir() and d.name not in current_slugs:
                    shutil.rmtree(d)

    # ── Build entry point ─────────────────────────────────────

    def build(self):
        print('빌드 시작...', flush=True)

        self._load_config()                    # [1]
        self._scan_articles()                  # [2]
        self._parse_frontmatter()              # [3]
        self._validate()                       # [4]
        self._render_articles()                # [5]
        self._sync_assets()                    # [6]
        self._build_categories()               # [7]
        self._build_home()                     # [8]
        self._copy_site_assets()               # [9]
        self._build_404()                      # [10]
        self._build_robots()                   # [11]
        self._build_sitemap()                  # [12]
        self._build_dispatcher()               # [13]
        self._build_search()                   # [14]
        self._prune_orphans()                  # [15]

        warn_count = warning_count()
        art_count = len(self.articles)
        cat_count = len(self.categories)
        print(f'\n빌드 완료: {art_count} 글, {cat_count} 카테고리, {warn_count} 경고.')
        print(f'산출물: dist/ (siheonlee.com), dist-legacy/ (lama.pe.kr).')

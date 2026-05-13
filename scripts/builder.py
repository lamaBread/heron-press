"""빌드 파이프라인 (Builder 클래스).

14단계 파이프라인 (v0.4.0):
  [1] _load_config           — site.yaml + legacy-map.yaml + 토크나이저 패리티 검증
  [2] _scan_articles         — Articles/ 트리 순회, _ 접두 제외
  [3] _parse_frontmatter     — meta.yaml 파싱 → ArticleMeta 채움
  [4] _validate              — slug 검증, 카테고리 트리 구축 (한글 폴더 워닝)
  [5] _render_articles       — 본문 렌더 + nav/SEO/styles 적용 → dist/{slug}/
  [6] _sync_assets           — 본문 외 자원 → dist/src/{slug}/
  [7] _build_categories      — 톱레벨 카테고리 인덱스 페이지
  [8] _build_home            — 루트 페이지
  [9] _copy_site_assets      — assets/ → dist/assets/
  [10] _build_404            — 404 페이지
  [11] _build_robots         — robots.txt (main + legacy)
  [12] _build_dispatcher     — dist-legacy/redirect.php (301 매핑)
  [13] _build_search         — search-index.json + search.php (+ tokenize lib)
  [14] _prune_orphans        — 삭제된 슬러그/카테고리의 dist 잔재 정리

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
from .models import SiteConfig, ArticleMeta, Article, Category
from .slugs import category_slug_from_name, is_underscore_path, has_non_ascii
from .markdown import (
    escape_html,
    render_article_md,
    render_article_styles,
    normalize_styles,
    process_html,
    has_live_php,
)
from .seo import build_meta_tags
from .search import (
    html_to_plain,
    build_search_index,
    run_parity_test,
)


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
            home_excludes_categories=get('home_excludes_categories') or [],
            home_sort=get('home_sort', 'date_desc'),
            description_truncate=int(get('description_truncate') or 150),
            robots_txt_main=get('robots_txt_main') or 'User-agent: *\nAllow: /\n',
            robots_txt_legacy=get('robots_txt_legacy') or 'User-agent: *\nAllow: /\n',
        )

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

            rel = root_path.relative_to(self.articles_dir)
            category_path = list(rel.parts[:-1])
            article_folder = rel.parts[-1]

            content_md = root_path / 'content.md'
            content_html = root_path / 'content.html'

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

            article.meta = ArticleMeta(
                slug=slug,
                title=title,
                date=date_str,
                updated=updated,
                noindex=noindex,
                seo_title_prefix=raw.get('seo_title_prefix'),
                seo_title_suffix=raw.get('seo_title_suffix'),
                seo_description=raw.get('seo_description') or None,
                seo_author=raw.get('seo_author') or None,
                seo_canonical=raw.get('seo_canonical') or None,
                seo_og_title=raw.get('seo_og_title') or None,
                seo_og_description=raw.get('seo_og_description') or None,
                seo_og_image=raw.get('seo_og_image') or None,
                seo_og_image_alt=raw.get('seo_og_image_alt') or None,
                seo_og_type=raw.get('seo_og_type') or 'article',
                seo_twitter_card=raw.get('seo_twitter_card') or 'summary_large_image',
                seo_twitter_image=raw.get('seo_twitter_image') or None,
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
        """v0.4.0: _meta.yaml 오버라이드 코드 경로 제거.

        한국어 등 비ASCII 폴더명은 slugs.category_slug_from_name 이
        결정론적으로 ASCII 코드포인트 hex 로 변환한다. 경고는 한 번만 (폴더당).
        """
        cat_paths = set()
        for article in self.articles:
            cat = article.category_path[:-1]
            for depth in range(1, len(cat) + 1):
                cat_paths.add(tuple(cat[:depth]))

        warned_folders = set()

        def to_slug(folder_name: str, full_path_for_warn) -> str:
            if has_non_ascii(folder_name) and folder_name not in warned_folders:
                warn(
                    f"non-ASCII folder name '{folder_name}' "
                    f"(Articles/{'/'.join(full_path_for_warn)}) — "
                    f"가급적 ASCII 로 작성하세요. 자동으로 hex 코드포인트 slug 로 변환됩니다."
                )
                warned_folders.add(folder_name)
            s = category_slug_from_name(folder_name)
            if not s:
                die(f'카테고리 slug 빈 문자열: {folder_name}\n'
                    f"       (Articles/{'/'.join(full_path_for_warn)})")
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

    def _collect_articles(self, cat: Category) -> list:
        result = list(cat.articles)
        for child in cat.children:
            result.extend(self._collect_articles(child))
        return result

    # ── [5] Article render + output ──────────────────────────

    def _copyright_year(self) -> str:
        return str(datetime.date.today().year)

    def _top_level_entries(self) -> list:
        """Articles/ 직속 항목을 [(folder_name, slug, is_article), ...] 로 반환."""
        if not self.articles_dir.is_dir():
            return []

        entries = []
        for child in self.articles_dir.iterdir():
            if not child.is_dir():
                continue
            if child.name.startswith('_'):
                continue
            meta_file = child / 'meta.yaml'
            if meta_file.exists():
                article = next(
                    (a for a in self.articles if a.source_dir == child),
                    None,
                )
                slug = article.meta.slug if article else child.name.lower()
                entries.append((child.name, slug, True))
            else:
                key = (child.name,)
                cat = self.categories.get(key)
                slug = cat.slug if cat else category_slug_from_name(child.name)
                entries.append((child.name, slug, False))

        about = [e for e in entries if e[0] == 'About']
        others = sorted(
            (e for e in entries if e[0] != 'About'),
            key=lambda e: e[0],
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
                body_html = (f"<div class='gap'>\n"
                             f"    <p>{escape_html(m.title)}</p>\n"
                             f"</div>\n"
                             f"<section>\n{rr.html}\n</section>")
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

            meta_tags, _full_title = build_meta_tags(article, rr, self.site)

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

            page_title = self.site.name

            vars_ = {
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

    def _listup_module_html(self, article: 'Article') -> str:
        link_text = article.meta.title
        return (f"<div class='listup_module_div'>"
                f"<span class='listup_module_title'>"
                f"<a href='/{article.meta.slug}/'> "
                f"{escape_html(link_text)} </a>"
                f"</span>"
                f"<span class='listup_module_date'> &nbsp;&nbsp; "
                f"{article.meta.date}</span>"
                f"</div>")

    def _build_categories(self):
        tpl = _load_template(self.templates_dir, 'category.html')
        nav_links = self._nav_links_html()

        for path_tuple, cat in self.categories.items():
            if len(cat.path) != 1:
                continue

            sections = []
            sorted_children = sorted(cat.children, key=lambda c: c.folder_name)
            for child in sorted_children:
                articles = self._collect_articles(child)
                articles.sort(key=lambda a: a.meta.date, reverse=True)

                if not articles:
                    inner = "<p>No articles found in this subcategory</p>"
                else:
                    inner = '\n'.join(
                        self._listup_module_html(a) for a in articles
                    )

                sections.append(
                    f"<div class='gap'><p>{escape_html(child.folder_name)}</p></div>\n"
                    f"<section>\n{inner}\n</section>"
                )

            if cat.articles and not sorted_children:
                articles = sorted(cat.articles, key=lambda a: a.meta.date, reverse=True)
                inner = '\n'.join(self._listup_module_html(a) for a in articles)
                sections.append(
                    f"<div class='gap'><p>{escape_html(cat.folder_name)}</p></div>\n"
                    f"<section>\n{inner}\n</section>"
                )

            subcategory_sections = '\n'.join(sections) if sections else (
                f"<div class='gap'><p>{escape_html(cat.folder_name)}</p></div>\n"
                f"<section><p>No articles found</p></section>"
            )

            crumb_parts = [(cat.folder_name, f"/{cat.slug}/")]
            nav_tracker = self._nav_tracker_for_path(crumb_parts)

            page_title = self.site.name

            vars_ = {
                'PAGE_TITLE': escape_html(page_title),
                'MAIN_TITLE': escape_html(self.site.main_title),
                'NAV_TRACKER': nav_tracker,
                'NAV_LINKS': nav_links,
                'NAV_SEARCH_CAT': escape_html(cat.slug),
                'SUBCATEGORY_SECTIONS': subcategory_sections,
                'COPYRIGHT_YEAR': self._copyright_year(),
                'COPYRIGHT_HOLDER': escape_html(self.site.copyright_holder),
            }
            page_html = _render_template(tpl, vars_)

            out_dir = self.dist / cat.slug
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / 'index.html').write_text(page_html, encoding='utf-8')

    # ── [8] Home page ─────────────────────────────────────────

    def _build_home(self):
        tpl = _load_template(self.templates_dir, 'home.html')

        exclude_top = set(self.site.home_excludes_categories)

        home_articles = []
        for article in self.articles:
            if article.category_path:
                top_cat = article.category_path[0]
                if top_cat in exclude_top:
                    continue
            if (len(article.category_path) == 1
                    and article.category_path[0] in exclude_top):
                continue
            home_articles.append(article)

        home_articles.sort(key=lambda a: a.meta.date, reverse=True)

        article_items = '\n'.join(
            self._listup_module_html(a) for a in home_articles
        )

        page_title = self.site.name

        vars_ = {
            'PAGE_TITLE': escape_html(page_title),
            'MAIN_TITLE': escape_html(self.site.main_title),
            'NAV_LINKS': self._nav_links_html(),
            'ARTICLE_LIST': article_items,
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

    # ── [12] Legacy dispatcher ────────────────────────────────

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

    # ── [13] Search index + search.php + tokenizer lib ──────

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
            'PAGE_TITLE': escape_html(self.site.name),
            'MAIN_TITLE': escape_html(self.site.main_title),
            'NAV_LINKS': self._nav_links_html(),
            'COPYRIGHT_YEAR': self._copyright_year(),
            'COPYRIGHT_HOLDER': escape_html(self.site.copyright_holder),
        }
        page = _render_template(tpl, vars_)
        (self.dist / 'search.php').write_text(page, encoding='utf-8')

    # ── [14] Global orphan pruning ────────────────────────────

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
        self._build_dispatcher()               # [12]
        self._build_search()                   # [13]
        self._prune_orphans()                  # [14]

        warn_count = warning_count()
        art_count = len(self.articles)
        cat_count = len(self.categories)
        print(f'\n빌드 완료: {art_count} 글, {cat_count} 카테고리, {warn_count} 경고.')
        print(f'산출물: dist/ (siheonlee.com), dist-legacy/ (lama.pe.kr).')

"""v1.4.0 신설 — 묶음 기능·정리 회귀 가드 테스트.

검증 항목 (README §16 v1.4.0 행 매핑):
  - A. 이전/다음 글 nav (sibling 인덱스 + 렌더 + 토글)
  - B. 글 끝 발행/수정 메타 한 줄
  - D. 다크 모드 CSS (raw 문자열 존재 + 핵심 선택자)
  - E. 내부 링크 검증 (helper + valid set 수집)
  - F+G+I. SiteConfig 슬림화 (다섯 필드 제거) + Builder 상수
  - J. BuildReport PHP 빌드 글 카테고리

통합 빌드 회귀는 test_cache 의 시나리오 / run_diagnostics 가 커버.
여기는 *단위/계약* 만 잠근다 — 외부 IO 없이 (또는 최소한으로) 빠르게.
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from scripts.builder import Builder  # noqa: E402
from scripts.models import (  # noqa: E402
    SiteConfig, SeoMeta, ArticleMeta, Article, CategoryMeta,
)
from scripts.report import BuildReport  # noqa: E402
from scripts import i18n  # noqa: E402


def _site(**overrides) -> SiteConfig:
    """v1.4.0 슬림 SiteConfig — 옛 다섯 필드 (reserved_slugs / warn_on_* /
    error_404_title / search_title) 가 더 이상 인자 목록에 없다.
    """
    defaults = dict(
        domain='x.com', base_url='https://x.com',
        name='X', main_title='X',
        default_author='A', default_og_image='/og.png',
        default_title_prefix='', default_title_suffix='',
        copyright_holder='A', copyright_year_start=2020,
        description_truncate=150,
        robots_txt_main='',
    )
    defaults.update(overrides)
    return SiteConfig(**defaults)


def _article(slug: str, date: str, *, category_path=None,
             noindex: bool = False, updated: str = None,
             title: str = None) -> Article:
    cp = list(category_path) if category_path else [slug]
    return Article(
        meta=ArticleMeta(
            slug=slug,
            title=title or slug.upper(),
            date=date,
            updated=updated,
            noindex=noindex,
            seo=SeoMeta(description='x'),
        ),
        source_dir=Path('.'),
        content_file=Path('content.md'),
        category_path=cp,
    )


def _builder(site: SiteConfig = None) -> Builder:
    """_render_articles 직접 호출 없이 헬퍼만 쓰는 minimal Builder."""
    b = Builder.__new__(Builder)
    b.site = site or _site()
    b.articles = []
    b.report = BuildReport()
    return b


# ════════════════════════════════════════════════════════════════
# F+G+I — SiteConfig 슬림화 + Builder 상수
# ════════════════════════════════════════════════════════════════

class SlimSiteConfigTests(unittest.TestCase):

    def test_no_legacy_fields(self):
        """삭제된 다섯 필드가 SiteConfig 의 dataclass 정의에 없다."""
        names = {f.name for f in SiteConfig.__dataclass_fields__.values()}
        for legacy in (
            'reserved_slugs',
            'warn_on_underscore_ref',
            'warn_on_missing_asset',
            'error_404_title',
            'search_title',
        ):
            self.assertNotIn(
                legacy, names,
                msg=f'{legacy} 가 SiteConfig 에 남아 있음 (v1.4.0 폐기 대상)')

    def test_prev_next_enabled_default_true(self):
        sc = _site()
        self.assertTrue(sc.prev_next_enabled)

    def test_prev_next_enabled_override(self):
        sc = _site(prev_next_enabled=False)
        self.assertFalse(sc.prev_next_enabled)


class BuilderConstantsTests(unittest.TestCase):

    def test_reserved_slugs_frozen(self):
        self.assertIn('assets', Builder.RESERVED_SLUGS)
        self.assertIn('search', Builder.RESERVED_SLUGS)
        # 운영자가 못 바꾸는 상수임을 frozenset 으로 보장
        self.assertIsInstance(Builder.RESERVED_SLUGS, frozenset)

    def test_default_titles(self):
        self.assertEqual(Builder.DEFAULT_ERROR_404_TITLE, 'Not Found')
        self.assertEqual(Builder.DEFAULT_SEARCH_TITLE, 'Search')


# ════════════════════════════════════════════════════════════════
# A — Prev/Next sibling navigation
# ════════════════════════════════════════════════════════════════

class PrevNextSiblingIndexTests(unittest.TestCase):

    def test_same_parent_sorted_by_date(self):
        b = _builder()
        b.articles = [
            _article('c', '2026-03-01', category_path=['Blog', 'c']),
            _article('a', '2026-01-01', category_path=['Blog', 'a']),
            _article('b', '2026-02-01', category_path=['Blog', 'b']),
        ]
        idx = b._build_sibling_index()
        sibs = idx[('Blog',)]
        self.assertEqual([a.meta.slug for a in sibs], ['a', 'b', 'c'])

    def test_noindex_excluded_from_pool(self):
        b = _builder()
        b.articles = [
            _article('a', '2026-01-01', category_path=['Blog', 'a']),
            _article('hidden', '2026-02-01', category_path=['Blog', 'hidden'],
                     noindex=True),
            _article('b', '2026-03-01', category_path=['Blog', 'b']),
        ]
        idx = b._build_sibling_index()
        slugs = [a.meta.slug for a in idx[('Blog',)]]
        self.assertEqual(slugs, ['a', 'b'])
        # noindex 글은 풀에 없으므로 자기 자신을 lookup 해도 (None, None)
        hidden = next(a for a in b.articles if a.meta.slug == 'hidden')
        self.assertEqual(b._prev_next_for(hidden, idx), (None, None))

    def test_different_parents_independent(self):
        b = _builder()
        b.articles = [
            _article('a', '2026-01-01', category_path=['Blog', 'a']),
            _article('p', '2026-01-15', category_path=['Project', 'p']),
            _article('b', '2026-02-01', category_path=['Blog', 'b']),
        ]
        idx = b._build_sibling_index()
        self.assertEqual([a.meta.slug for a in idx[('Blog',)]], ['a', 'b'])
        self.assertEqual([a.meta.slug for a in idx[('Project',)]], ['p'])

    def test_date_tiebreak_by_slug(self):
        b = _builder()
        b.articles = [
            _article('z', '2026-01-01', category_path=['Blog', 'z']),
            _article('a', '2026-01-01', category_path=['Blog', 'a']),
        ]
        idx = b._build_sibling_index()
        self.assertEqual([a.meta.slug for a in idx[('Blog',)]], ['a', 'z'])


class PrevNextLookupTests(unittest.TestCase):

    def setUp(self):
        self.b = _builder()
        self.b.articles = [
            _article('first', '2026-01-01', category_path=['Blog', 'first']),
            _article('middle', '2026-02-01', category_path=['Blog', 'middle']),
            _article('last', '2026-03-01', category_path=['Blog', 'last']),
        ]
        self.idx = self.b._build_sibling_index()

    def test_first_has_no_prev(self):
        a = self.b.slug = next(a for a in self.b.articles
                                if a.meta.slug == 'first')
        p, n = self.b._prev_next_for(a, self.idx)
        self.assertIsNone(p)
        self.assertEqual(n.meta.slug, 'middle')

    def test_middle_has_both(self):
        a = next(a for a in self.b.articles if a.meta.slug == 'middle')
        p, n = self.b._prev_next_for(a, self.idx)
        self.assertEqual(p.meta.slug, 'first')
        self.assertEqual(n.meta.slug, 'last')

    def test_last_has_no_next(self):
        a = next(a for a in self.b.articles if a.meta.slug == 'last')
        p, n = self.b._prev_next_for(a, self.idx)
        self.assertEqual(p.meta.slug, 'middle')
        self.assertIsNone(n)


class PrevNextRenderTests(unittest.TestCase):

    def _setup_trio(self, **site_overrides):
        b = _builder(_site(**site_overrides))
        b.articles = [
            _article('first', '2026-01-01', title='First',
                     category_path=['Blog', 'first']),
            _article('middle', '2026-02-01', title='Middle',
                     category_path=['Blog', 'middle']),
            _article('last', '2026-03-01', title='Last',
                     category_path=['Blog', 'last']),
        ]
        return b, b._build_sibling_index()

    def test_middle_renders_both_cards(self):
        b, idx = self._setup_trio()
        a = next(a for a in b.articles if a.meta.slug == 'middle')
        html = b._render_prev_next_nav(a, idx)
        self.assertIn('<nav class="prev-next-nav"', html)
        self.assertIn('href="/first/"', html)
        self.assertIn('rel="prev"', html)
        self.assertIn('href="/last/"', html)
        self.assertIn('rel="next"', html)
        self.assertIn('First', html)
        self.assertIn('Last', html)

    def test_first_uses_placeholder_for_prev(self):
        b, idx = self._setup_trio()
        a = next(a for a in b.articles if a.meta.slug == 'first')
        html = b._render_prev_next_nav(a, idx)
        # prev 자리는 placeholder span
        self.assertIn('prev-next-placeholder', html)
        self.assertIn('href="/middle/"', html)
        self.assertNotIn('rel="prev"', html)

    def test_last_uses_placeholder_for_next(self):
        b, idx = self._setup_trio()
        a = next(a for a in b.articles if a.meta.slug == 'last')
        html = b._render_prev_next_nav(a, idx)
        self.assertIn('prev-next-placeholder', html)
        self.assertIn('href="/middle/"', html)
        self.assertNotIn('rel="next"', html)

    def test_disabled_yields_empty(self):
        b, idx = self._setup_trio(prev_next_enabled=False)
        a = next(a for a in b.articles if a.meta.slug == 'middle')
        self.assertEqual(b._render_prev_next_nav(a, idx), '')

    def test_solo_article_yields_empty(self):
        b = _builder()
        b.articles = [
            _article('alone', '2026-01-01', category_path=['Blog', 'alone']),
        ]
        idx = b._build_sibling_index()
        html = b._render_prev_next_nav(b.articles[0], idx)
        self.assertEqual(html, '')

    def test_title_escapes_html(self):
        b = _builder()
        b.articles = [
            _article('a', '2026-01-01', title='A & <B>',
                     category_path=['Blog', 'a']),
            _article('b', '2026-02-01', title='Safe',
                     category_path=['Blog', 'b']),
        ]
        idx = b._build_sibling_index()
        html = b._render_prev_next_nav(b.articles[1], idx)
        self.assertIn('A &amp; &lt;B&gt;', html)


# ════════════════════════════════════════════════════════════════
# B — Article-end published/updated meta
# ════════════════════════════════════════════════════════════════

class ArticleEndMetaTests(unittest.TestCase):

    def test_published_only_when_no_updated(self):
        b = _builder()
        m = ArticleMeta(slug='x', title='X', date='2026-01-01')
        html = b._render_article_end_meta(m)
        self.assertIn('class="article-end-meta"', html)
        self.assertIn('2026-01-01 발행', html)
        self.assertNotIn('수정', html)
        self.assertNotIn('article-end-meta-sep', html)

    def test_published_only_when_updated_equals_date(self):
        b = _builder()
        m = ArticleMeta(slug='x', title='X', date='2026-01-01',
                        updated='2026-01-01')
        html = b._render_article_end_meta(m)
        self.assertNotIn('수정', html)

    def test_both_when_updated_differs(self):
        b = _builder()
        m = ArticleMeta(slug='x', title='X', date='2026-01-01',
                        updated='2026-02-15')
        html = b._render_article_end_meta(m)
        self.assertIn('2026-01-01 발행', html)
        self.assertIn('2026-02-15 수정', html)
        self.assertIn('article-end-meta-sep', html)
        # datetime 속성도 부착돼야 함 (semantic HTML)
        self.assertIn('datetime="2026-01-01"', html)
        self.assertIn('datetime="2026-02-15"', html)

    def test_empty_date_yields_empty(self):
        b = _builder()
        m = ArticleMeta(slug='x', title='X', date='')
        self.assertEqual(b._render_article_end_meta(m), '')


# ════════════════════════════════════════════════════════════════
# D — Dark mode CSS
# ════════════════════════════════════════════════════════════════

class DarkModeCssTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.css = (_SRC.parent / 'user' / 'styles' / 'common_template.css').read_text(
            encoding='utf-8')

    def test_prefers_color_scheme_dark_block_present(self):
        self.assertIn('@media (prefers-color-scheme: dark)', self.css)

    def test_no_toggle_ui_class(self):
        """토글 UI 없음 — 시스템 기본을 그대로 신뢰 (사용자 결정)."""
        # 가짜 토글 클래스가 들어오면 회귀로 잡힌다 — 자주 쓰이는 이름들 가드.
        for ban in ('.dark-mode-toggle', '#dark-toggle', '.theme-toggle'):
            self.assertNotIn(
                ban, self.css,
                msg=f'다크 모드는 토글 UI 없음 정책 — {ban} 발견')

    def test_key_dark_overrides(self):
        """필수 표면 (body / section / footer / 링크 / prev-next / end-meta)
        이 다크 블록 안에서 색 override 를 받는지 — raw 문자열 존재 검사."""
        m = re.search(
            r'@media \(prefers-color-scheme: dark\)\s*\{(.*)$',
            self.css, re.DOTALL,
        )
        self.assertIsNotNone(m)
        dark = m.group(1)
        for needed in (
            'body',
            'section',
            'footer',
            '.prev-next-link',
            '.article-end-meta',
            '#TITLE',
        ):
            self.assertIn(
                needed, dark,
                msg=f'다크 블록에 {needed} override 가 없음')


# ════════════════════════════════════════════════════════════════
# E — Internal link validation
# ════════════════════════════════════════════════════════════════

class InternalLinkValidationTests(unittest.TestCase):

    def test_is_internal_link_skips_external(self):
        f = Builder._is_internal_link
        for ext in (
            'https://example.com/',
            'http://example.com/',
            '//cdn.example.com/x.js',
            'mailto:x@y.com',
            'tel:+8210',
            'javascript:void(0)',
            'data:image/png;base64,xxx',
            '#anchor',
            '?q=foo',
            '',
            'relative/path',
        ):
            self.assertFalse(f(ext), msg=f'{ext!r} 는 internal 이 아니어야')

    def test_is_internal_link_accepts_site_relative(self):
        f = Builder._is_internal_link
        for href in ('/', '/foo/', '/foo/bar.html', '/feed.atom', '/404.html'):
            self.assertTrue(f(href), msg=f'{href!r} 는 internal 이어야')

    def test_normalize_link_path_unquote_and_nfc(self):
        """URL-decode + NFC 정규화 — 디스크 literal 경로와 비교 정합."""
        n = Builder._normalize_link_path
        # 공백 URL-encoded
        self.assertEqual(n('/foo/bar%20baz.pdf'), '/foo/bar baz.pdf')
        # 비-ASCII 그대로 (NFC 보존)
        self.assertEqual(n('/blog/한글.html'), '/blog/한글.html')
        # NFD Korean Jamo → NFC 합성 (디스크 literal 과 매칭하기 위해)
        nfd = '/blog/한글.pdf'
        self.assertEqual(n(nfd), '/blog/한글.pdf')
        # URL-encoded 비ASCII (UTF-8 byte) 도 정상 decode
        self.assertEqual(n('/blog/%ED%95%9C%EA%B8%80.pdf'),
                         '/blog/한글.pdf')

    def test_collect_dist_urls_includes_dir_index(self):
        """dist 안의 디렉터리에 index.html 이 있으면 '/dir/' URL 도 set 에."""
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            dist = base / 'dist'
            (dist / 'foo').mkdir(parents=True)
            (dist / 'foo' / 'index.html').write_text('x', encoding='utf-8')
            (dist / 'bar').mkdir()
            (dist / 'bar' / 'index.php').write_text('x', encoding='utf-8')
            (dist / 'sitemap.xml').write_text('x', encoding='utf-8')
            (dist / 'index.html').write_text('x', encoding='utf-8')

            b = Builder.__new__(Builder)
            b.dist = dist
            urls = b._collect_dist_urls()

            self.assertIn('/foo/', urls)
            self.assertIn('/foo/index.html', urls)
            self.assertIn('/bar/', urls)
            self.assertIn('/bar/index.php', urls)
            self.assertIn('/sitemap.xml', urls)
            self.assertIn('/', urls)

    def test_validate_internal_links_flags_broken(self):
        """글 페이지 본문의 깨진 site-relative 링크를 글 단위 issue 로 보고."""
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            dist = base / 'dist'
            (dist / 'realtarget').mkdir(parents=True)
            (dist / 'realtarget' / 'index.html').write_text(
                'x', encoding='utf-8')
            (dist / 'srcart').mkdir()
            (dist / 'srcart' / 'index.html').write_text(
                '<html><body>'
                '<a href="/realtarget/">good</a>'
                '<a href="/missing-target/">broken</a>'
                '<a href="https://x.com/">external</a>'
                '<a href="#sect">anchor</a>'
                '<a href="/realtarget/?q=foo">good w/ query</a>'
                '</body></html>',
                encoding='utf-8',
            )

            b = Builder.__new__(Builder)
            b.dist = dist
            b.report = BuildReport()
            b.tool_tr = i18n.load('ko')   # v1.9.2: _emit 가 build.console.* 를 조회
            b.articles = [
                _article('srcart', '2026-01-01',
                         category_path=['Blog', 'srcart']),
            ]
            b._console = []
            b._live_pending = False
            b._live_lastlen = 0
            b._live_cols = 78
            b._stdout_isatty = False
            b._validate_internal_links()

            msgs = [e.message for e in b.report.entries
                    if 'srcart' in (e.target or '')]
            self.assertTrue(
                any('/missing-target/' in m for m in msgs),
                msg=f'깨진 링크가 issue 로 보고되지 않음: {msgs}')
            # 양호한 링크는 noise 가 되지 않아야
            self.assertFalse(
                any('/realtarget/' in m for m in msgs),
                msg=f'정상 링크가 잘못 보고됨: {msgs}')

    # ── v1.4.1: 정규식 회귀 가드 (data-href / 진짜 href 만 추출) ──

    def test_href_regex_ignores_data_href_only(self):
        """`<a data-href="...">` 만 있을 때 진짜 href 가 없으므로 추출 0건.

        v1.4.0 `\\bhref=` 가 `-` ~ `h` 사이도 워드 경계로 인식해 data-href 를
        href 로 오매칭하던 회귀. v1.4.1 `\\s+href=` 로 속성 경계 정확화.
        """
        rx = Builder._LINK_HREF_RE
        self.assertEqual(rx.findall('<a data-href="/foo">x</a>'), [])

    def test_href_regex_picks_real_href_when_both_present(self):
        """`href` 와 `data-href` 가 같이 있어도 진짜 href 만 추출."""
        rx = Builder._LINK_HREF_RE
        # 진짜 href 가 먼저
        self.assertEqual(
            rx.findall('<a href="/real" data-href="/fake">x</a>'),
            ['/real'],
        )
        # data-href 가 먼저 (v1.4.0 greedy 가 마지막 hit 를 가져가던 케이스)
        self.assertEqual(
            rx.findall('<a data-href="/fake" href="/real">x</a>'),
            ['/real'],
        )

    def test_href_regex_handles_newline_and_uppercase(self):
        """줄바꿈 공백 + 대문자 태그/속성도 매칭 (HTML 관용)."""
        rx = Builder._LINK_HREF_RE
        self.assertEqual(rx.findall('<a\nhref="/x">y</a>'), ['/x'])
        self.assertEqual(rx.findall('<A HREF="/upper">y</A>'), ['/upper'])

    def test_validate_internal_links_does_not_flag_data_href(self):
        """`<a data-href="/no-such-page">` 만 있는 경우 false-positive 금지.

        v1.4.0 의 `\\bhref=` 가 data-href 의 값을 잘못 추출해 깨진 링크로
        보고하던 회귀. 진짜 href 가 아예 없으므로 issue 0건이어야 한다.
        """
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            dist = base / 'dist'
            (dist / 'srcart').mkdir(parents=True)
            (dist / 'srcart' / 'index.html').write_text(
                '<html><body>'
                '<a data-href="/no-such-page/">data only</a>'
                '<a href="/real/" data-href="/whatever/">real href</a>'
                '</body></html>',
                encoding='utf-8',
            )
            (dist / 'real').mkdir()
            (dist / 'real' / 'index.html').write_text('x', encoding='utf-8')

            b = Builder.__new__(Builder)
            b.dist = dist
            b.report = BuildReport()
            b.tool_tr = i18n.load('ko')   # v1.9.2: _emit 가 build.console.* 를 조회
            b.articles = [
                _article('srcart', '2026-01-01',
                         category_path=['Blog', 'srcart']),
            ]
            b._console = []
            b._live_pending = False
            b._live_lastlen = 0
            b._live_cols = 78
            b._stdout_isatty = False
            b._validate_internal_links()

            msgs = [e.message for e in b.report.entries
                    if 'srcart' in (e.target or '')]
            # data-href 의 값(/no-such-page/) 은 절대 깨진 링크로 잡혀선 안 됨.
            self.assertFalse(
                any('/no-such-page/' in m or '/whatever/' in m for m in msgs),
                msg=f'data-href 값이 잘못 보고됨: {msgs}')


# ════════════════════════════════════════════════════════════════
# J — BuildReport PHP-built articles category
# ════════════════════════════════════════════════════════════════

class BuildReportPhpBuiltTests(unittest.TestCase):

    def setUp(self):
        # v1.9.2: render_markdown()/render() 의 헤딩·요약이 전역 i18n.t() 를
        # 거치므로 ko(정본)로 고정 — 실행 순서 무관히 한국어 단언이 성립.
        i18n.init('ko')

    def tearDown(self):
        # v1.9.7: 기본값이 en 이므로 한국어 단언용으로 바꾼 전역을 복원.
        i18n.init(i18n.CANONICAL)

    def test_note_php_built_dedupes(self):
        r = BuildReport()
        r.note_php_built('a')
        r.note_php_built('b')
        r.note_php_built('a')  # 중복
        self.assertEqual(r.php_built, ['a', 'b'])
        self.assertEqual(r.php_built_count(), 2)

    def test_render_markdown_sorts_and_labels(self):
        r = BuildReport()
        r.note_php_built('zz')
        r.note_php_built('aa')
        md = r.render_markdown()
        self.assertIn('## PHP 로 빌드된 글', md)
        self.assertIn('의도된 출력', md)
        # 알파벳 순 정렬 — aa 가 zz 보다 먼저
        self.assertLess(md.index('/aa/'), md.index('/zz/'))

    def test_summary_includes_php_count_when_present(self):
        r = BuildReport()
        r.note_php_built('alpha')
        md = r.render_markdown()
        # 요약에 'PHP 빌드 1건' 노출
        self.assertIn('PHP 빌드 1건', md)

    def test_summary_omits_php_when_zero(self):
        r = BuildReport()
        r.issue('site', '', 'just an issue')
        md = r.render_markdown()
        self.assertNotIn('PHP 빌드', md)

    def test_render_console_php_section(self):
        import io
        r = BuildReport()
        r.note_php_built('demo')
        out = io.StringIO()
        r.render(out=out)
        text = out.getvalue()
        self.assertIn('PHP 로 빌드된 글', text)
        self.assertIn('/demo/', text)


if __name__ == '__main__':
    unittest.main()

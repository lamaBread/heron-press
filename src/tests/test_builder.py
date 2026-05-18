"""scripts/builder Builder 의 *순수 헬퍼* 단위 테스트 (v0.6.0~).

전체 파이프라인 (빌드 / 자산 sync / orphan prune) 은 통합 테스트 / 진단
스크립트가 커버한다. 본 테스트는 외부 IO 없이 검증 가능한 함수만 다룬다:

  - Builder._inline_php_body  : v0.6.0 신설. search_*.php → search.php 인라인
                                 시 헤더/CLI 블록 정리.
  - Builder._wrap_page_title  : v0.5.4 의 페이지 제목 폴백 체인.
  - v0.6.3 신규: 글 단위 외부 CSS (`styles:` 정수 키) + use_common_css 토글의
                 frontmatter 파싱 동작을 통합 빌드로 검증.
  - v0.6.4 신규: 카테고리/홈도 같은 styles 두 채널 + use_common_css 지원,
                 + meta.yaml 의 template 키 (페이지 단위 템플릿 선택).
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.builder import Builder  # noqa: E402
from scripts.models import (  # noqa: E402
    SiteConfig, SeoMeta, Category,
)


class InlinePhpBodyTests(unittest.TestCase):

    def test_strips_php_open(self):
        src = '<?php\nfunction foo() {}'
        out = Builder._inline_php_body(src, strip_cli_block=False)
        self.assertNotIn('<?php', out)
        self.assertIn('function foo()', out)

    def test_strips_declare(self):
        src = '<?php\ndeclare(strict_types=1);\n\nfunction foo() {}'
        out = Builder._inline_php_body(src, strip_cli_block=False)
        self.assertNotIn('declare(strict_types', out)

    def test_strips_php_close(self):
        src = '<?php\nfunction foo() {}\n?>'
        out = Builder._inline_php_body(src, strip_cli_block=False)
        self.assertNotIn('?>', out)

    def test_strips_cli_block(self):
        # search_tokenize.php 끝의 CLI 모드 블록 패턴
        src = (
            "<?php\n"
            "function search_tokenize($x) { return []; }\n\n"
            "// CLI 모드 — 패리티 검증용. argv[1] 을 토큰화해 JSON 으로 출력.\n"
            "if (PHP_SAPI === 'cli' && isset($argv[0])\n"
            "        && realpath($argv[0]) === realpath(__FILE__)) {\n"
            "    $input = $argv[1] ?? '';\n"
            "    echo json_encode(search_tokenize($input), JSON_UNESCAPED_UNICODE);\n"
            "}\n"
        )
        out = Builder._inline_php_body(src, strip_cli_block=True)
        self.assertIn('function search_tokenize', out)
        self.assertNotIn('PHP_SAPI', out)
        self.assertNotIn('echo json_encode', out)

    def test_does_not_strip_cli_block_when_disabled(self):
        src = (
            "<?php\n"
            "function foo() {}\n"
            "// CLI 모드 \n"
            "if (PHP_SAPI === 'cli') { echo 'x'; }\n"
        )
        out = Builder._inline_php_body(src, strip_cli_block=False)
        self.assertIn('PHP_SAPI', out)

    def test_ends_with_newline(self):
        out = Builder._inline_php_body('<?php\nfoo();', strip_cli_block=False)
        self.assertTrue(out.endswith('\n'))


class WrapPageTitleTests(unittest.TestCase):

    def _builder(self, **site_overrides):
        # 최소 인스턴스 — _wrap_page_title 만 호출하므로 다른 필드는 무시.
        b = Builder.__new__(Builder)
        defaults = dict(
            domain='x.com', base_url='https://x.com',
            name='X', main_title='X',
            default_author='A', default_og_image='/og.png',
            default_title_prefix='', default_title_suffix=' | X',
            copyright_holder='A', copyright_year_start=2020,
            reserved_slugs=[],
            warn_on_underscore_ref=False, warn_on_missing_asset=False,
            warn_on_stale_updated=False, description_truncate=160,
            robots_txt_main='',
        )
        defaults.update(site_overrides)
        b.site = SiteConfig(**defaults)
        return b

    def test_default_prefix_suffix(self):
        b = self._builder()
        self.assertEqual(b._wrap_page_title('Hello'), 'Hello | X')

    def test_seo_override_prefix(self):
        b = self._builder()
        seo = SeoMeta(title_prefix='»', title_suffix=None)
        # title_suffix=None → site 디폴트 ' | X'
        self.assertEqual(b._wrap_page_title('Hello', seo), '»Hello | X')

    def test_seo_override_suffix(self):
        b = self._builder()
        seo = SeoMeta(title_prefix=None, title_suffix='«')
        self.assertEqual(b._wrap_page_title('Hello', seo), 'Hello«')

    def test_seo_empty_string_overrides(self):
        # 빈 문자열은 None 과 구분 — empty 면 site 디폴트 무시.
        b = self._builder()
        seo = SeoMeta(title_prefix='', title_suffix='')
        self.assertEqual(b._wrap_page_title('Hello', seo), 'Hello')


# ════════════════════════════════════════════════════════════════
# v0.6.3 — frontmatter 의 styles 분리 + use_common_css 토글
# ════════════════════════════════════════════════════════════════

# v0.8.1: 테스트는 src/tests/ 로 이동 → REPO_ROOT = src/ (templates/ ·
# assets/ 의 실제 위치). Builder(base_dir=tmp) 는 tmp/src/templates ·
# tmp/src/assets 를 읽으므로 아래 하네스들이 거기로 복사한다.
REPO_ROOT = Path(__file__).resolve().parent.parent


class StylesFrontmatterTests(unittest.TestCase):
    """글 meta.yaml 의 styles 키와 use_common_css 토글을 *통합 빌드* 로 검증.

    임시 디렉터리에 최소 사이트를 만들고 Builder().build() 를 돌린 뒤
    dist 산출물을 확인. _parse_frontmatter → _render_articles 의 전체
    경로가 의도대로 연결되는지 본다 (외부 IO 없이는 styles 의 파일 존재
    검증 동작을 단위 테스트하기 어려움).
    """

    SITE_YAML = (
        "domain: example.com\n"
        "base_url: https://example.com\n"
        "name: Example\n"
        "main_title: Example\n"
        "default_author: A\n"
        "default_og_image: /og.png\n"
        "default_title_prefix: ''\n"
        "default_title_suffix: ' | E'\n"
        "copyright_holder: A\n"
        "copyright_year_start: 2020\n"
        "lang: en\n"
        "images:\n"
        "  enabled: false\n"
        "  lazy_loading: false\n"
        "reserved_slugs: [assets, search]\n"
    )

    META_BASE = (
        "slug: demo\n"
        "title: Demo\n"
        "date: 2026-01-01\n"
        "seo:\n"
        "  description: A demo article.\n"
    )

    def _scaffold(self, meta_extra: str, *, files: dict = None):
        """임시 사이트 트리를 만들고 Builder 를 돌려 dist Path 반환."""
        tmp = Path(tempfile.mkdtemp(prefix='ssg-v063-'))
        (tmp / 'site.yaml').write_text(self.SITE_YAML, encoding='utf-8')
        # templates/ + assets/ 의 실 파일을 임시 디렉터리로 복사
        # (v0.8.1: Builder 가 base/src/templates · base/src/assets 를 읽음).
        shutil.copytree(REPO_ROOT / 'templates', tmp / 'src' / 'templates')
        shutil.copytree(REPO_ROOT / 'assets', tmp / 'src' / 'assets')

        # Articles/<slug>/ 글 한 개.
        article_dir = tmp / 'Articles' / 'Demo'
        article_dir.mkdir(parents=True)
        (article_dir / 'meta.yaml').write_text(
            self.META_BASE + (meta_extra or ''),
            encoding='utf-8',
        )
        (article_dir / 'content.md').write_text('# Demo body\n', encoding='utf-8')
        if files:
            for rel, content in files.items():
                p = article_dir / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding='utf-8')

        # 다른 테스트와 격리 — 전역 _report 초기화.
        # v0.8.2: per-Builder 리포트 — 모듈 전역 reset_report() 폐지.
        # 인스턴스를 self 에 보관해 테스트가 self._builder.report 로 검사.
        b = Builder(base_dir=tmp)
        b.build()
        self._builder = b
        return tmp, tmp / 'dist'

    def test_no_stylesheets_keeps_v062_output(self):
        """외부 CSS 없는 글: PAGE_STYLESHEETS placeholder 줄이 통째로 제거되어
        head 가 공통 CSS → atom/rss → (인라인) → title 순으로 깔끔."""
        _, dist = self._scaffold('')
        html = (dist / 'demo' / 'index.html').read_text(encoding='utf-8')
        self.assertIn(
            "<link href='/assets/common_template.css'",
            html,
        )
        self.assertNotIn('{{PAGE_STYLESHEETS}}', html)
        self.assertNotIn('{{COMMON_CSS}}', html)

    def test_external_css_emits_link_in_head(self):
        """외부 CSS 파일이 존재하면 `<link>` 가 head 에 추가됨."""
        _, dist = self._scaffold(
            'styles:\n  1: extra.css\n',
            files={'extra.css': 'body { background: #eee; }\n'},
        )
        html = (dist / 'demo' / 'index.html').read_text(encoding='utf-8')
        self.assertIn(
            "<link href='/demo/extra.css' rel='stylesheet' type='text/css'>",
            html,
        )
        # _sync_assets 가 글 폴더의 css 를 dist/{slug}/ 로 복사.
        self.assertTrue((dist / 'demo' / 'extra.css').is_file())

    def test_external_css_multiple_order(self):
        """정수 키 오름차순 = head 의 link 출력 순서."""
        _, dist = self._scaffold(
            'styles:\n  2: b.css\n  1: a.css\n',
            files={'a.css': '/* a */', 'b.css': '/* b */'},
        )
        html = (dist / 'demo' / 'index.html').read_text(encoding='utf-8')
        pos_a = html.find('/demo/a.css')
        pos_b = html.find('/demo/b.css')
        self.assertGreater(pos_a, 0)
        self.assertGreater(pos_b, pos_a)

    def test_external_and_inline_both_emit_inline_last(self):
        """외부 CSS + 인라인 룰 공존 → 둘 다 head 에 출력되며 인라인이 *나중*."""
        _, dist = self._scaffold(
            "styles:\n"
            "  1: extra.css\n"
            "  p:\n"
            "    color: red\n",
            files={'extra.css': '/* extra */'},
        )
        html = (dist / 'demo' / 'index.html').read_text(encoding='utf-8')
        pos_link = html.find("/demo/extra.css")
        pos_inline = html.find('<style>')
        self.assertGreater(pos_link, 0)
        self.assertGreater(pos_inline, pos_link,
                           '인라인 <style> 이 외부 link 보다 뒤에 나와야 함')

    def test_missing_css_file_routes_issue_no_link(self):
        """meta.yaml 에 적었지만 글 폴더에 파일이 없으면 issue + link 미출력."""
        _, dist = self._scaffold('styles:\n  1: ghost.css\n')
        html = (dist / 'demo' / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('ghost.css', html)
        entries = self._builder.report.entries
        joined = '\n'.join(e.message for e in entries if e.severity == 'issue')
        self.assertIn('ghost.css', joined)

    def test_path_escape_rejected(self):
        """'../foo.css' 같은 글 폴더 이탈 경로는 거부."""
        _, dist = self._scaffold(
            'styles:\n  1: ../escape.css\n',
            files={},
        )
        html = (dist / 'demo' / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('escape.css', html)

    def test_absolute_path_rejected(self):
        """'/foo.css' 같은 절대 경로는 거부."""
        _, dist = self._scaffold('styles:\n  1: /etc/passwd\n')
        html = (dist / 'demo' / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('passwd', html)

    def test_use_common_css_false_omits_common_link(self):
        """use_common_css: false → common_template.css link 자체 미출력."""
        _, dist = self._scaffold('use_common_css: false\n')
        html = (dist / 'demo' / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('/assets/common_template.css', html)
        self.assertNotIn('{{COMMON_CSS}}', html)

    def test_use_common_css_true_default(self):
        """use_common_css 미지정 → 기본 True → common_template.css link 출력."""
        _, dist = self._scaffold('')
        html = (dist / 'demo' / 'index.html').read_text(encoding='utf-8')
        self.assertIn("href='/assets/common_template.css'", html)

    def test_use_common_css_false_with_external(self):
        """use_common_css=false + 외부 CSS — 외부만 출력되고 공통은 없음."""
        _, dist = self._scaffold(
            "use_common_css: false\nstyles:\n  1: only.css\n",
            files={'only.css': '/* only */'},
        )
        html = (dist / 'demo' / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('/assets/common_template.css', html)
        self.assertIn("/demo/only.css", html)


# ════════════════════════════════════════════════════════════════
# v0.6.4 — 카테고리/홈 일원화 + template: 키
# ════════════════════════════════════════════════════════════════


class PageCssUnificationTests(unittest.TestCase):
    """v0.6.4 — 홈 (Articles/meta.yaml) 과 카테고리 (Articles/<cat>/meta.yaml) 도
    글과 같은 styles 두 채널 + use_common_css 토글을 지원하는지 검증.
    """

    SITE_YAML = StylesFrontmatterTests.SITE_YAML

    def _scaffold(self, *, home_meta='', category_meta=None, category_files=None,
                  home_files=None):
        """홈 + 1 개 카테고리 + 그 카테고리 안에 글 1 개. 카테고리 / 홈의
        meta.yaml 본문을 호출자가 주입할 수 있도록 한다.
        """
        tmp = Path(tempfile.mkdtemp(prefix='ssg-v064-'))
        (tmp / 'site.yaml').write_text(self.SITE_YAML, encoding='utf-8')
        shutil.copytree(REPO_ROOT / 'templates', tmp / 'src' / 'templates')
        shutil.copytree(REPO_ROOT / 'assets', tmp / 'src' / 'assets')

        # Articles/meta.yaml (홈)
        articles_dir = tmp / 'Articles'
        articles_dir.mkdir(parents=True)
        (articles_dir / 'meta.yaml').write_text(
            "seo:\n  description: Site root description.\n" + (home_meta or ''),
            encoding='utf-8',
        )
        if home_files:
            for rel, content in home_files.items():
                p = articles_dir / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding='utf-8')

        # Articles/Blog/meta.yaml (카테고리)
        cat_dir = articles_dir / 'Blog'
        cat_dir.mkdir(parents=True)
        (cat_dir / 'meta.yaml').write_text(
            "seo:\n  description: Blog category.\n" + (category_meta or ''),
            encoding='utf-8',
        )
        if category_files:
            for rel, content in category_files.items():
                p = cat_dir / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding='utf-8')

        # Articles/Blog/Hello/ — 글 1 개 (홈/카테고리 페이지가 비어있지 않도록).
        art_dir = cat_dir / 'Hello'
        art_dir.mkdir(parents=True)
        (art_dir / 'meta.yaml').write_text(
            "slug: hello\ntitle: Hello\ndate: 2026-01-01\n"
            "seo:\n  description: Hello article.\n",
            encoding='utf-8',
        )
        (art_dir / 'content.md').write_text('# Hello\n', encoding='utf-8')

        # v0.8.2: per-Builder 리포트 — 모듈 전역 reset_report() 폐지.
        # 인스턴스를 self 에 보관해 테스트가 self._builder.report 로 검사.
        b = Builder(base_dir=tmp)
        b.build()
        self._builder = b
        return tmp, tmp / 'dist'

    # ── 홈 ────────────────────────────────────────────────────────

    def test_home_external_css_emits_link_and_copies_file(self):
        """홈의 styles: 1: theme.css → link 가 dist/index.html head 에 출력
        + 파일이 dist 루트에 복사."""
        _, dist = self._scaffold(
            home_meta="styles:\n  1: theme.css\n",
            home_files={'theme.css': '/* home theme */'},
        )
        html = (dist / 'index.html').read_text(encoding='utf-8')
        self.assertIn(
            "<link href='/theme.css' rel='stylesheet' type='text/css'>",
            html,
        )
        self.assertTrue((dist / 'theme.css').is_file())

    def test_home_use_common_css_false_omits_common_link(self):
        _, dist = self._scaffold(home_meta="use_common_css: false\n")
        html = (dist / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('/assets/common_template.css', html)

    def test_home_inline_styles_render(self):
        """홈의 styles: p: { color: red } 인라인 룰이 <style> 로 출력."""
        _, dist = self._scaffold(
            home_meta="styles:\n  p:\n    color: red\n",
        )
        html = (dist / 'index.html').read_text(encoding='utf-8')
        self.assertIn('<style>', html)
        self.assertIn('section p', html)
        self.assertIn('color: red', html)

    def test_home_missing_css_routes_issue(self):
        """홈의 styles 에 존재하지 않는 CSS 를 적으면 issue + link 미출력."""
        _, dist = self._scaffold(home_meta="styles:\n  1: missing.css\n")
        html = (dist / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('missing.css', html)
        joined = '\n'.join(
            e.message for e in self._builder.report.entries
            if e.severity == 'issue'
        )
        self.assertIn('missing.css', joined)

    # ── 카테고리 ──────────────────────────────────────────────────

    def test_category_external_css_emits_link_and_copies_file(self):
        """카테고리의 styles: 1: cat.css → link 가 dist/blog/index.html 에 출력
        + 파일이 dist/blog/ 로 복사."""
        _, dist = self._scaffold(
            category_meta="styles:\n  1: cat.css\n",
            category_files={'cat.css': '/* cat */'},
        )
        html = (dist / 'blog' / 'index.html').read_text(encoding='utf-8')
        self.assertIn(
            "<link href='/blog/cat.css' rel='stylesheet' type='text/css'>",
            html,
        )
        self.assertTrue((dist / 'blog' / 'cat.css').is_file())

    def test_category_use_common_css_false_omits_common_link(self):
        _, dist = self._scaffold(category_meta="use_common_css: false\n")
        html = (dist / 'blog' / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('/assets/common_template.css', html)

    def test_category_inline_styles_render(self):
        _, dist = self._scaffold(
            category_meta="styles:\n  p:\n    color: blue\n",
        )
        html = (dist / 'blog' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('<style>', html)
        self.assertIn('section p', html)
        self.assertIn('color: blue', html)


class TemplateRefTests(unittest.TestCase):
    """v0.6.4 — meta.yaml 의 template 키로 페이지 단위 템플릿 선택."""

    SITE_YAML = StylesFrontmatterTests.SITE_YAML

    def _scaffold(self, *, article_meta='', article_files=None,
                  templates_extra=None):
        tmp = Path(tempfile.mkdtemp(prefix='ssg-v064-tpl-'))
        (tmp / 'site.yaml').write_text(self.SITE_YAML, encoding='utf-8')
        shutil.copytree(REPO_ROOT / 'templates', tmp / 'src' / 'templates')
        shutil.copytree(REPO_ROOT / 'assets', tmp / 'src' / 'assets')

        if templates_extra:
            for rel, content in templates_extra.items():
                p = tmp / 'src' / 'templates' / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding='utf-8')

        articles_dir = tmp / 'Articles'
        articles_dir.mkdir(parents=True)
        (articles_dir / 'meta.yaml').write_text(
            "seo:\n  description: site.\n", encoding='utf-8',
        )
        art_dir = articles_dir / 'Demo'
        art_dir.mkdir(parents=True)
        meta_body = (
            "slug: demo\ntitle: Demo\ndate: 2026-01-01\n"
            "seo:\n  description: Demo article.\n"
        ) + (article_meta or '')
        (art_dir / 'meta.yaml').write_text(meta_body, encoding='utf-8')
        (art_dir / 'content.md').write_text('# Demo\n', encoding='utf-8')
        if article_files:
            for rel, content in article_files.items():
                p = art_dir / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding='utf-8')

        # v0.8.2: per-Builder 리포트 — 모듈 전역 reset_report() 폐지.
        # 인스턴스를 self 에 보관해 테스트가 self._builder.report 로 검사.
        b = Builder(base_dir=tmp)
        b.build()
        self._builder = b
        return tmp, tmp / 'dist'

    def test_no_template_key_uses_default(self):
        """template 키 없음 → 기본 article.html."""
        _, dist = self._scaffold()
        html = (dist / 'demo' / 'index.html').read_text(encoding='utf-8')
        # 기본 article.html 에는 imgslidebox.js 가 포함됨 (식별 단서).
        self.assertIn('imgslidebox.js', html)

    def test_template_key_from_templates_dir(self):
        """template: 'name.html' → templates/ 에서 로드."""
        _, dist = self._scaffold(
            article_meta="template: tiny.html\n",
            templates_extra={
                'tiny.html':
                    '<html><head><title>{{PAGE_TITLE}}</title></head>'
                    '<body>{{BODY}}</body></html>',
            },
        )
        html = (dist / 'demo' / 'index.html').read_text(encoding='utf-8')
        # tiny.html 은 header/nav/footer 가 없어 imgslidebox.js 도 없음.
        self.assertNotIn('imgslidebox.js', html)
        self.assertIn('<title>Demo | E</title>', html)
        # 본문 markdown 의 `# Demo` 가 <h1>Demo</h1> 로 렌더되어 BODY 자리에.
        self.assertIn('<h1>Demo</h1>', html)

    def test_template_key_dot_slash_from_article_folder(self):
        """template: './local.html' → 글 폴더에서 로드."""
        _, dist = self._scaffold(
            article_meta="template: ./local.html\n",
            article_files={
                'local.html':
                    '<html><body><h1>LOCAL {{PAGE_TITLE}}</h1>{{BODY}}</body></html>',
            },
        )
        html = (dist / 'demo' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('LOCAL Demo | E', html)

    def test_template_key_missing_file_falls_back_to_default(self):
        """존재하지 않는 템플릿 → issue + 기본 article.html 폴백."""
        _, dist = self._scaffold(
            article_meta="template: ghost.html\n",
        )
        html = (dist / 'demo' / 'index.html').read_text(encoding='utf-8')
        # 기본으로 폴백 → header/footer 등 정상.
        self.assertIn('imgslidebox.js', html)
        joined = '\n'.join(
            e.message for e in self._builder.report.entries
            if e.severity == 'issue'
        )
        self.assertIn('ghost.html', joined)

    def test_template_key_path_escape_rejected(self):
        """절대경로 / '..' 포함 → issue + 기본 폴백."""
        _, dist = self._scaffold(
            article_meta="template: ../escape.html\n",
        )
        html = (dist / 'demo' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('imgslidebox.js', html)  # 기본 폴백
        joined = '\n'.join(
            e.message for e in self._builder.report.entries
            if e.severity == 'issue'
        )
        self.assertIn("'template'", joined)

    def test_unfilled_placeholder_strip_and_warn(self):
        """페이지 종류 가로지르기 → 미치환 placeholder strip + warning."""
        _, dist = self._scaffold(
            article_meta="template: weird.html\n",
            templates_extra={
                # SUBCATEGORY_SECTIONS 는 카테고리에서만 채워지므로 글이
                # 이 템플릿을 골랐을 때 남는다 → strip + warning.
                'weird.html':
                    '<html><body>{{BODY}}<x>{{SUBCATEGORY_SECTIONS}}</x>'
                    '</body></html>',
            },
        )
        html = (dist / 'demo' / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('{{SUBCATEGORY_SECTIONS}}', html)
        self.assertIn('<x></x>', html)  # strip 후 빈 문자열.
        warnings = [
            e.message for e in self._builder.report.entries
            if e.severity == 'warning'
        ]
        joined = '\n'.join(warnings)
        self.assertIn('SUBCATEGORY_SECTIONS', joined)


class BodyPlaceholderPreservationTests(unittest.TestCase):
    """v0.6.5: 사용자 본문 (BODY) 에 들어 있는 `{{XXX}}` 대문자 placeholder 가
    silent 으로 strip 되지 않아야 한다 (v0.6.4 회귀).

    예: 사용자가 템플릿 엔진 튜토리얼을 쓰면서 코드 블록에 `{{NAV_LINKS}}` 같은
    문자열을 넣었을 때, v0.6.4 의 leftover strip 이 BODY 안에 든 패턴까지 잡아
    사용자 텍스트를 잃었다. v0.6.5 의 3-pass _render_template 가 BODY 치환을
    leftover strip 이후로 미뤄 사용자 본문을 보존한다.
    """

    SITE_YAML = StylesFrontmatterTests.SITE_YAML

    def _scaffold(self, *, content_md: str):
        tmp = Path(tempfile.mkdtemp(prefix='ssg-v065-body-'))
        (tmp / 'site.yaml').write_text(self.SITE_YAML, encoding='utf-8')
        shutil.copytree(REPO_ROOT / 'templates', tmp / 'src' / 'templates')
        shutil.copytree(REPO_ROOT / 'assets', tmp / 'src' / 'assets')

        articles_dir = tmp / 'Articles'
        articles_dir.mkdir(parents=True)
        (articles_dir / 'meta.yaml').write_text(
            "seo:\n  description: site.\n", encoding='utf-8',
        )
        art_dir = articles_dir / 'Demo'
        art_dir.mkdir(parents=True)
        (art_dir / 'meta.yaml').write_text(
            "slug: demo\ntitle: Demo\ndate: 2026-01-01\n"
            "seo:\n  description: Demo article.\n",
            encoding='utf-8',
        )
        (art_dir / 'content.md').write_text(content_md, encoding='utf-8')

        # v0.8.2: per-Builder 리포트 — 모듈 전역 reset_report() 폐지.
        # 인스턴스를 self 에 보관해 테스트가 self._builder.report 로 검사.
        b = Builder(base_dir=tmp)
        b.build()
        self._builder = b
        return tmp, tmp / 'dist'

    def test_body_preserves_unknown_uppercase_placeholder(self):
        """본문 안의 vars 에 없는 `{{FOO_BAR}}` 는 그대로 보존되어야 한다."""
        _, dist = self._scaffold(content_md='# Demo\n\nLiteral `{{FOO_BAR}}` text.\n')
        html = (dist / 'demo' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('{{FOO_BAR}}', html)

    def test_body_preserves_known_uppercase_placeholder(self):
        """본문 안의 vars 에 있는 `{{NAV_LINKS}}` 도 보존되어야 한다.

        v0.6.5: content_vars 의 substitute 는 frame vars 와 leftover strip 이
        끝난 뒤에 일어나므로, BODY 가 substitute 되는 시점에는 더 이상 다른
        `.replace()` 가 돌지 않아 BODY 안의 패턴이 안전하다.
        """
        _, dist = self._scaffold(
            content_md='# Demo\n\nThe `{{NAV_LINKS}}` slot.\n',
        )
        html = (dist / 'demo' / 'index.html').read_text(encoding='utf-8')
        # BODY 안의 `{{NAV_LINKS}}` 는 그대로. (head 의 nav 영역은 template
        # 측에서 이미 substitute 되었지만, BODY 자리에는 사용자 문자가 들어감.)
        # parsedown 이 `code` 를 <code> 로 감싸므로 escape 후에도 텍스트 보존.
        self.assertIn('{{NAV_LINKS}}', html)

    def test_body_preserves_placeholder_in_code_block(self):
        """코드 블록 안의 placeholder 패턴 보존."""
        md = '# Demo\n\n```\n{{COPYRIGHT_YEAR}}\n```\n'
        _, dist = self._scaffold(content_md=md)
        html = (dist / 'demo' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('{{COPYRIGHT_YEAR}}', html)


class BuildReportResetTests(unittest.TestCase):
    """v0.6.5→v0.8.2: build() 가 self.report 를 새로 교체해, 한 인스턴스를
    재사용해 여러 번 빌드를 돌려도 issue/warning 이 누적되지 않는다.

    v0.6.5 ~ v0.8.1 은 모듈 전역 `_report` + build() 진입 시 reset_report()
    였다. v0.8.2 부터 리포트가 per-Builder 라 (a) 같은 인스턴스 재사용 시
    build() 의 self.report 재생성으로 누적 방지, (b) 서로 다른 인스턴스는
    리포트를 공유하지 않는다 (동시 빌드의 전제 — 본 클래스가 두 성질을
    각각 가드).
    """

    SITE_YAML = StylesFrontmatterTests.SITE_YAML

    def _make_site(self):
        tmp = Path(tempfile.mkdtemp(prefix='ssg-v065-reset-'))
        (tmp / 'site.yaml').write_text(self.SITE_YAML, encoding='utf-8')
        shutil.copytree(REPO_ROOT / 'templates', tmp / 'src' / 'templates')
        shutil.copytree(REPO_ROOT / 'assets', tmp / 'src' / 'assets')
        articles_dir = tmp / 'Articles'
        articles_dir.mkdir(parents=True)
        # 홈에 description 없음 → 1 issue.
        (articles_dir / 'meta.yaml').write_text('', encoding='utf-8')
        art_dir = articles_dir / 'Demo'
        art_dir.mkdir(parents=True)
        # 글에도 description 없음 → 1 issue.
        (art_dir / 'meta.yaml').write_text(
            "slug: demo\ntitle: Demo\ndate: 2026-01-01\n",
            encoding='utf-8',
        )
        (art_dir / 'content.md').write_text('# Demo\n', encoding='utf-8')
        return tmp

    def test_same_instance_reuse_does_not_accumulate_issues(self):
        """같은 Builder 인스턴스로 build() 를 두 번 — build() 가 self.report
        를 새로 교체하므로 issue 카운트가 누적되지 않아야 한다 (v0.6.5
        자동 reset 의 per-Builder 판)."""
        tmp = self._make_site()
        b = Builder(base_dir=tmp)
        b.build()
        count_after_first = b.report.issue_count()
        b.build()  # 같은 인스턴스 재사용 — reset 은 build() 가 자동.
        count_after_second = b.report.issue_count()
        self.assertEqual(count_after_first, count_after_second,
                         '두 번째 빌드 후 issue 카운트가 같아야 한다 '
                         '(누적되면 안 됨)')

    def test_distinct_instances_have_independent_reports(self):
        """v0.8.2 핵심: 서로 다른 Builder 인스턴스는 리포트를 공유하지
        않는다 (모듈 전역 폐지 → 동시 빌드 봉쇄 해제의 전제). 두 인스턴스를
        각각 빌드해도 한쪽의 issue 가 다른 쪽 리포트에 새지 않는다."""
        tmp = self._make_site()
        b1 = Builder(base_dir=tmp)
        b1.build()
        b2 = Builder(base_dir=tmp)
        b2.build()
        # 두 리포트는 별개 객체.
        self.assertIsNot(b1.report, b2.report)
        # 같은 사이트라 카운트는 같지만, 누적이 아니라 각자 독립 집계.
        self.assertEqual(b1.report.issue_count(), b2.report.issue_count())
        # b2 빌드가 b1.report 항목 수를 바꾸지 않았다.
        self.assertEqual(
            len(b1.report.entries),
            b1.report.issue_count() + b1.report.warning_count(),
        )


class CrumbPartsForTests(unittest.TestCase):
    """빵부스러기/nav-tracker 단일 공유 소스의 빌더 레벨 검증.
    `_crumb_parts_for` 는 조상을 자기 *중첩* 카테고리 URL 로 링크하고
    (Bug A 교정), 글 호출자는 말단에 글 제목을 넘긴다(Bug B 교정).
    `_ancestor_categories` 는 접두 경로를 등록 Category 로 해석한다."""

    def _b(self):
        b = Builder.__new__(Builder)
        # Articles/Top/Mid/<글폴더> 를 모사하는 최소 카테고리 트리.
        top = Category(folder_name='Top', slug='top',
                       path=['Top'], slug_path=['top'])
        mid = Category(folder_name='Mid', slug='mid',
                       path=['Top', 'Mid'], slug_path=['top', 'mid'])
        b.categories = {('Top',): top, ('Top', 'Mid'): mid}
        return b, top, mid

    def test_ancestor_categories_resolution_and_skip(self):
        b, top, mid = self._b()
        self.assertEqual(b._ancestor_categories(['Top', 'Mid']), [top, mid])
        self.assertEqual(b._ancestor_categories(['Top']), [top])
        self.assertEqual(b._ancestor_categories([]), [])
        # 미등록 깊이는 건너뛴다 (('Top','Ghost') 미등록).
        self.assertEqual(b._ancestor_categories(['Top', 'Ghost']), [top])

    def test_three_level_article_nested_urls_and_title_leaf(self):
        b, _, _ = self._b()
        # 글 category_path = ['Top','Mid','<글폴더>'] → 조상 = [:-1].
        ancestors = b._ancestor_categories(['Top', 'Mid', 'Leaf_Folder'][:-1])
        crumb = b._crumb_parts_for(ancestors=ancestors,
                                   leaf=('글 제목', None))
        self.assertEqual(crumb, [
            ('Top', '/top/'),
            ('Mid', '/top/mid/'),     # 중간 = 자기 중첩 URL (Bug A 교정)
            ('글 제목', None),         # 말단 = 글 제목, item 없음 (Bug B)
        ])
        # 중간은 부모(top)와 distinct — v0.8.3 은 둘 다 '/top/' 이었다.
        self.assertNotEqual(crumb[0][1], crumb[1][1])
        # 말단 url=None → JSON-LD item 생략 / nav-tracker reload 앵커.
        self.assertIsNone(crumb[-1][1])

    def test_top_level_article_single_crumb_is_title(self):
        b, _, _ = self._b()
        ancestors = b._ancestor_categories(['About'][:-1])  # == []
        crumb = b._crumb_parts_for(ancestors=ancestors,
                                   leaf=('글 제목', None))
        # 단일 crumb → downstream(build_jsonld)에서 BreadcrumbList 생략,
        # nav-tracker 는 한 줄 + 말단 텍스트 = 글 제목.
        self.assertEqual(crumb, [('글 제목', None)])

    def test_top_category_page_single_crumb_keeps_folder_name(self):
        b, _, _ = self._b()
        # 톱 카테고리 페이지: 조상 0 + 자기 url_prefix, 말단 이름은
        # K2(폴더명 유지)에 따라 폴더명 그대로 (글 제목 개념 없음).
        crumb = b._crumb_parts_for(ancestors=[],
                                   leaf=('Top', '/top/'))
        self.assertEqual(crumb, [('Top', '/top/')])

    def test_subcategory_page_nested_middle_and_folder_leaf(self):
        b, _, _ = self._b()
        # 서브 카테고리 페이지 cat.path=['Top','Mid'] → 조상 = [:-1]=
        # ['Top'], 말단 = (cat.folder_name, None).
        ancestors = b._ancestor_categories(['Top', 'Mid'][:-1])
        crumb = b._crumb_parts_for(ancestors=ancestors,
                                   leaf=('Mid', None))
        self.assertEqual(crumb, [('Top', '/top/'), ('Mid', None)])


if __name__ == '__main__':
    unittest.main()

"""scripts/builder Builder 의 *순수 헬퍼* 단위 테스트 (v0.6.0~).

전체 파이프라인 (빌드 / 자산 sync / orphan prune) 은 통합 테스트 / 진단
스크립트가 커버한다. 본 테스트는 외부 IO 없이 검증 가능한 함수만 다룬다:

  - Builder._inline_php_body  : v0.6.0 신설. search_*.php → search.php 인라인
                                 시 헤더/CLI 블록 정리.
  - Builder._wrap_page_title  : v0.5.4 의 페이지 제목 폴백 체인.
  - v0.6.3 신규: 글 단위 외부 CSS (`styles:` 정수 키) + use_common_css 토글의
                 frontmatter 파싱 동작을 통합 빌드로 검증.
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import builder as builder_module  # noqa: E402
from scripts.builder import Builder  # noqa: E402
from scripts.models import (  # noqa: E402
    SiteConfig, SeoMeta,
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
            robots_txt_main='', robots_txt_legacy='',
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
        # templates/ + assets/ 는 v0.6.3 폴더의 실 파일을 임시 디렉터리로 복사
        # (Builder 가 base/templates, base/assets 만 받기 때문).
        shutil.copytree(REPO_ROOT / 'templates', tmp / 'templates')
        shutil.copytree(REPO_ROOT / 'assets', tmp / 'assets')
        # legacy-map.yaml 은 빈 dict 로.
        (tmp / 'legacy-map.yaml').write_text('legacy_map: {}\n', encoding='utf-8')

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
        builder_module.reset_report()
        b = Builder(base_dir=tmp)
        b.build()
        return tmp, tmp / 'dist'

    def test_no_stylesheets_keeps_v062_output(self):
        """외부 CSS 없는 글: ARTICLE_STYLESHEETS placeholder 줄이 통째로 제거되어
        head 가 공통 CSS → atom/rss → (인라인) → title 순으로 깔끔."""
        _, dist = self._scaffold('')
        html = (dist / 'demo' / 'index.html').read_text(encoding='utf-8')
        self.assertIn(
            "<link href='/assets/common_template.css'",
            html,
        )
        self.assertNotIn('{{ARTICLE_STYLESHEETS}}', html)
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
        entries = builder_module.report().entries
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


if __name__ == '__main__':
    unittest.main()

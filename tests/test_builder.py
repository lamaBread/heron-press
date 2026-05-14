"""scripts/builder Builder 의 *순수 헬퍼* 단위 테스트 (v0.6.0).

전체 파이프라인 (빌드 / 자산 sync / orphan prune) 은 통합 테스트 / 진단
스크립트가 커버한다. 본 테스트는 외부 IO 없이 검증 가능한 함수만 다룬다:

  - Builder._inline_php_body  : v0.6.0 신설. search_*.php → search.php 인라인
                                 시 헤더/CLI 블록 정리.
  - Builder._wrap_page_title  : v0.5.4 의 페이지 제목 폴백 체인.
  - Builder._top_level_entries / _nav_links_html : nav_priority 정렬 (통합).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

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


if __name__ == '__main__':
    unittest.main()

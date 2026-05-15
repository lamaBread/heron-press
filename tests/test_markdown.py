"""scripts/markdown 단위 테스트 (v0.6.0).

이미지 path 재작성 / imgBox / 섹션 마커 / 본문 fallback 제거 검증.
Parsedown 자체는 scripts/parsedown.py (포트) 가 검증하므로 여기서는
markdown.py 의 후처리 단계만 다룬다.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.markdown import (  # noqa: E402
    escape_html,
    rewrite_asset_path,
    rewrite_asset_paths_in_html,
    preprocess_md_custom_syntax,
    resolve_section_markers,
    finalize_md_html,
    normalize_styles,
    render_inline_styles,
    render_stylesheet_links,
    has_live_php,
)


class EscapeTests(unittest.TestCase):

    def test_basic(self):
        self.assertEqual(escape_html('<b>&amp;</b>'),
                         '&lt;b&gt;&amp;amp;&lt;/b&gt;')


class RewriteAssetPathTests(unittest.TestCase):

    def test_relative_path(self):
        # v0.5.2: /src/ 가 아니라 /{slug}/ 로
        self.assertEqual(rewrite_asset_path('./img.jpg', 's'), '/s/img.jpg')

    def test_no_dot_prefix(self):
        self.assertEqual(rewrite_asset_path('img.jpg', 's'), '/s/img.jpg')

    def test_absolute_url_preserved(self):
        self.assertEqual(rewrite_asset_path('https://x.com/a.jpg', 's'),
                         'https://x.com/a.jpg')
        self.assertEqual(rewrite_asset_path('http://x.com/a.jpg', 's'),
                         'http://x.com/a.jpg')
        self.assertEqual(rewrite_asset_path('//x.com/a.jpg', 's'),
                         '//x.com/a.jpg')

    def test_root_relative_preserved(self):
        self.assertEqual(rewrite_asset_path('/abs.jpg', 's'), '/abs.jpg')

    def test_subdir(self):
        self.assertEqual(rewrite_asset_path('imgs/x.png', 's'), '/s/imgs/x.png')


class RewriteAssetPathsInHtmlTests(unittest.TestCase):

    def test_img_src(self):
        html = '<img src="./pic.png">'
        out = rewrite_asset_paths_in_html(html, 'slug')
        self.assertIn('src="/slug/pic.png"', out)

    def test_a_href(self):
        html = '<a href="./doc.pdf">d</a>'
        out = rewrite_asset_paths_in_html(html, 's')
        self.assertIn('href="/s/doc.pdf"', out)

    def test_external_href_preserved(self):
        html = '<a href="https://example.com/page">x</a>'
        out = rewrite_asset_paths_in_html(html, 's')
        self.assertIn('href="https://example.com/page"', out)


class PreprocessImgBoxTests(unittest.TestCase):

    def test_imgbox_inline(self):
        md = '![[alt]](pic.png) {caption}'
        out = preprocess_md_custom_syntax(md)
        self.assertIn('<div class="imgBox">', out)
        self.assertIn('<img src="pic.png" alt="alt">', out)
        self.assertIn('<p class="caption">caption</p>', out)

    def test_imgbox_no_caption(self):
        md = '![[alt]](pic.png)'
        out = preprocess_md_custom_syntax(md)
        self.assertIn('<div class="imgBox">', out)
        self.assertNotIn('class="caption"', out)


class SectionMarkerTests(unittest.TestCase):

    def test_section_open_close(self):
        # ===title=== 와 ====== 라인을 sentinel 로 변환
        md = '===hello===\nbody\n======\nafter'
        out = preprocess_md_custom_syntax(md)
        self.assertIn('<!--SBR-OPEN:hello-->', out)
        self.assertIn('<!--SBR-CLOSE-->', out)

    def test_section_marker_inside_code_fence_ignored(self):
        md = '```\n===keep===\n```\n===real===\n'
        out = preprocess_md_custom_syntax(md)
        # 코드 펜스 안의 ===keep=== 는 sentinel 로 변환되지 않아야 함
        self.assertNotIn('SBR-OPEN:keep', out)
        self.assertIn('<!--SBR-OPEN:real-->', out)

    def test_resolve_wraps_in_gap_section(self):
        # 본문이 sentinel 없이도 첫 갭 + section 으로 감싸짐
        html = 'plain body'
        out = resolve_section_markers(html, 'My Title')
        self.assertIn('<div class=\'gap\'>', out)
        self.assertIn('<p>My Title</p>', out)
        self.assertIn('<section>', out)
        self.assertIn('plain body', out)

    def test_resolve_handles_open_close(self):
        html = (
            'intro<!--SBR-OPEN:sec1-->section1<!--SBR-CLOSE-->'
            'outside<!--SBR-OPEN:sec2-->section2'
        )
        out = resolve_section_markers(html, 'Top')
        self.assertIn('<p>sec1</p>', out)
        self.assertIn('<p>sec2</p>', out)
        self.assertEqual(out.count('<section>'), 3)
        self.assertEqual(out.count('</section>'), 3)


class FinalizeMdTests(unittest.TestCase):

    def test_render_result_html_only(self):
        # v0.5.5: RenderResult 는 html 한 필드만. first_paragraph / first_image
        # 필드가 더 이상 존재하지 않음.
        rr = finalize_md_html('<p>x</p>', 'slug', Path('.'))
        self.assertEqual(rr.html, '<p>x</p>')
        self.assertFalse(hasattr(rr, 'first_paragraph'))
        self.assertFalse(hasattr(rr, 'first_image'))


class StyleTests(unittest.TestCase):

    def test_normalize_strips_none(self):
        # v0.6.3: 반환이 (sheets, rules) 튜플로 변경.
        raw = {'p': {'color': 'red', 'margin': None}}
        sheets, rules = normalize_styles(raw)
        self.assertEqual(sheets, [])
        self.assertEqual(rules, {'p': {'color': 'red'}})

    def test_normalize_empty_dict_to_dict(self):
        self.assertEqual(normalize_styles({}), ([], {}))
        self.assertEqual(normalize_styles(None), ([], {}))
        self.assertEqual(normalize_styles('not a dict'), ([], {}))

    def test_render_section_scoped_tag(self):
        out = render_inline_styles({'p': {'color': 'red'}})
        self.assertIn('section p', out)
        self.assertIn('color: red', out)

    def test_render_complex_selector_unchanged(self):
        # 공백 / 콤마 등 'CSS selector 같은' 입력은 section prefix 안 붙음
        out = render_inline_styles({'.foo > p': {'color': 'red'}})
        self.assertIn('.foo > p', out)
        self.assertNotIn('section .foo', out)

    # v0.6.3 신규 케이스 ─────────────────────────────────────────────

    def test_normalize_separates_int_and_str_keys(self):
        """정수 키 = 외부 CSS 파일 / 문자열 키 = 인라인 룰."""
        raw = {
            2: 'theme.css',
            'p': {'color': 'red'},
            1: 'layout.css',
        }
        sheets, rules = normalize_styles(raw)
        self.assertEqual(sheets, ['layout.css', 'theme.css'])
        self.assertEqual(rules, {'p': {'color': 'red'}})

    def test_normalize_int_keys_sort_ascending(self):
        """정수 키는 오름차순으로 정렬 — 1 → 2 → 3."""
        sheets, _ = normalize_styles({10: 'c.css', 1: 'a.css', 5: 'b.css'})
        self.assertEqual(sheets, ['a.css', 'b.css', 'c.css'])

    def test_normalize_int_keys_allow_gaps(self):
        """빠진 번호 (1, 3) 도 허용."""
        sheets, _ = normalize_styles({1: 'a.css', 3: 'b.css'})
        self.assertEqual(sheets, ['a.css', 'b.css'])

    def test_normalize_skips_non_string_int_value(self):
        """정수 키의 값이 문자열이 아니면 무시 (silent — Builder 가 issue)."""
        sheets, _ = normalize_styles({1: ['not', 'a', 'str']})
        self.assertEqual(sheets, [])

    def test_normalize_skips_empty_int_value(self):
        """빈 문자열 / 공백만 있는 값 무시."""
        sheets, _ = normalize_styles({1: '', 2: '   ', 3: 'real.css'})
        self.assertEqual(sheets, ['real.css'])

    def test_normalize_skips_bool_key(self):
        """YAML 의 `true:` 같은 bool 키는 정수로 등록되지 않음."""
        sheets, rules = normalize_styles({True: 'x.css', False: 'y.css'})
        self.assertEqual(sheets, [])
        self.assertEqual(rules, {})

    def test_render_stylesheet_links_empty(self):
        self.assertEqual(render_stylesheet_links([], 'slug'), '')
        self.assertEqual(render_stylesheet_links(['a.css'], ''), '')

    def test_render_stylesheet_links_basic(self):
        out = render_stylesheet_links(['style.css'], 'about')
        self.assertIn("href='/about/style.css'", out)
        self.assertIn("rel='stylesheet'", out)
        self.assertEqual(out.count('<link'), 1)

    def test_render_stylesheet_links_multiple_order_preserved(self):
        out = render_stylesheet_links(['a.css', 'b.css'], 'slug')
        pos_a = out.find('a.css')
        pos_b = out.find('b.css')
        self.assertGreater(pos_a, -1)
        self.assertGreater(pos_b, pos_a)

    def test_render_stylesheet_links_normalizes_dot_slash(self):
        out = render_stylesheet_links(['./theme.css'], 'slug')
        self.assertIn("href='/slug/theme.css'", out)
        self.assertNotIn('./theme.css', out)

    def test_render_stylesheet_links_subdir(self):
        out = render_stylesheet_links(['css/main.css'], 'slug')
        self.assertIn("href='/slug/css/main.css'", out)

    def test_render_stylesheet_links_backslash_to_slash(self):
        # Windows 경로 호환.
        out = render_stylesheet_links(['css\\theme.css'], 'slug')
        self.assertIn("href='/slug/css/theme.css'", out)


class HasLivePhpTests(unittest.TestCase):

    def test_detects_php_open(self):
        self.assertTrue(has_live_php('<?php echo "x"; ?>'))
        self.assertTrue(has_live_php('<?= $x ?>'))

    def test_negative(self):
        self.assertFalse(has_live_php('<p>no php here</p>'))


if __name__ == '__main__':
    unittest.main()

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
    simulate_php_in_html,
    parse_php_globals,
    process_html,
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

    # ── v1.14.1 견고화 회귀 (자기 구분자를 본문에 품은 입력) ──────────
    def test_imgbox_url_with_parens(self):
        # B1: 파일명에 `)` (예: `dog(1).png`, `fig(final).png`) 가 있어도
        # 첫 `)` 에서 끊기지 않고 한 줄 imgBox 로 인식.
        out = preprocess_md_custom_syntax('![[d]](fig(final).png) {Figure 1}')
        self.assertIn('<div class="imgBox">', out)
        self.assertIn('<img src="fig(final).png" alt="d">', out)
        self.assertIn('<p class="caption">Figure 1</p>', out)

    def test_imgbox_caption_with_parens_not_eaten_by_url(self):
        # B1 역방향: 캡션 속 `(좌)` 의 `)` 를 URL 이 삼키면 안 됨.
        out = preprocess_md_custom_syntax('![[a]](dog(1).png) {see (left)}')
        self.assertIn('<img src="dog(1).png" alt="a">', out)
        self.assertIn('<p class="caption">see (left)</p>', out)

    def test_imgbox_alt_with_single_brackets(self):
        # B2: alt 안의 단일 `[`/`]` 가 `]]` 구분자보다 먼저 끊지 않게.
        out = preprocess_md_custom_syntax('![[my [cat] pic]](dog.png) {c}')
        self.assertIn('<img src="dog.png" alt="my [cat] pic">', out)
        self.assertIn('<p class="caption">c</p>', out)

    def test_imgbox_leading_indent(self):
        # B3: 탭/공백 들여쓰기된 imgBox 도 인식하고, 결과 div 는 컬럼0.
        for indent in ('\t', '  ', '    '):
            out = preprocess_md_custom_syntax(indent + '![[cat]](dog.png) {cap}')
            self.assertIn('<div class="imgBox">', out)
            # 치환 결과는 줄 맨 앞(컬럼0)에서 시작해야 코드블록으로 안 떨어진다.
            self.assertTrue(out.lstrip().startswith('<div class="imgBox">'))

    def test_imgbox_caption_with_braces(self):
        # B10: 캡션 안의 `{`/`}` (집합·중괄호 표기) 허용.
        out = preprocess_md_custom_syntax('![[a]](d.png) {a {nested} cap}')
        self.assertIn('<p class="caption">a {nested} cap</p>', out)

    def test_imgbox_caption_raw_html_not_escaped(self):
        # B9: 캡션 raw HTML(`<br>`·`<a>`)은 PHP 형과 동일하게 그대로 보존.
        out = preprocess_md_custom_syntax('![[c]](d.png) {line1<br>line2}')
        self.assertIn('<p class="caption">line1<br>line2</p>', out)
        self.assertNotIn('&lt;br&gt;', out)
        # alt 는 속성값이라 이스케이프 유지.
        out2 = preprocess_md_custom_syntax('![[a<b]](d.png)')
        self.assertIn('alt="a&lt;b"', out2)


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
        self.assertEqual(render_stylesheet_links([], '/slug/'), '')
        self.assertEqual(render_stylesheet_links(['a.css'], None), '')

    def test_render_stylesheet_links_basic(self):
        out = render_stylesheet_links(['style.css'], '/about/')
        self.assertIn("href='/about/style.css'", out)
        self.assertIn("rel='stylesheet'", out)
        self.assertEqual(out.count('<link'), 1)

    def test_render_stylesheet_links_multiple_order_preserved(self):
        out = render_stylesheet_links(['a.css', 'b.css'], '/slug/')
        pos_a = out.find('a.css')
        pos_b = out.find('b.css')
        self.assertGreater(pos_a, -1)
        self.assertGreater(pos_b, pos_a)

    def test_render_stylesheet_links_normalizes_dot_slash(self):
        out = render_stylesheet_links(['./theme.css'], '/slug/')
        self.assertIn("href='/slug/theme.css'", out)
        self.assertNotIn('./theme.css', out)

    def test_render_stylesheet_links_subdir(self):
        out = render_stylesheet_links(['css/main.css'], '/slug/')
        self.assertIn("href='/slug/css/main.css'", out)

    def test_render_stylesheet_links_backslash_to_slash(self):
        # Windows 경로 호환.
        out = render_stylesheet_links(['css\\theme.css'], '/slug/')
        self.assertIn("href='/slug/css/theme.css'", out)

    # v0.6.4: url_prefix 시그니처 일반화 — 카테고리/홈도 같은 함수 사용.
    def test_render_stylesheet_links_home_root_prefix(self):
        """홈의 외부 CSS — url_prefix='/' → URL=/<rel>."""
        out = render_stylesheet_links(['theme.css'], '/')
        self.assertIn("href='/theme.css'", out)

    def test_render_stylesheet_links_category_prefix(self):
        """카테고리 (서브 포함) — url_prefix='/blog/tutorials/' → URL 도 동일 접두."""
        out = render_stylesheet_links(['style.css'], '/blog/tutorials/')
        self.assertIn("href='/blog/tutorials/style.css'", out)

    def test_render_stylesheet_links_prefix_without_trailing_slash(self):
        """url_prefix 가 trailing '/' 없이 주어져도 자동 보정."""
        out = render_stylesheet_links(['x.css'], '/blog')
        self.assertIn("href='/blog/x.css'", out)

    def test_render_stylesheet_links_prefix_without_leading_slash(self):
        """url_prefix 가 leading '/' 없이 주어져도 자동 보정."""
        out = render_stylesheet_links(['x.css'], 'blog/')
        self.assertIn("href='/blog/x.css'", out)


class HasLivePhpTests(unittest.TestCase):

    def test_detects_php_open(self):
        self.assertTrue(has_live_php('<?php echo "x"; ?>'))
        self.assertTrue(has_live_php('<?= $x ?>'))

    def test_detects_uppercase_php_open(self):
        # v1.14.1 (B7): PHP 렉서는 여는 태그를 대소문자 무시로 받는다 —
        # `<?PHP`/`<?Php` 도 라이브 PHP 로 잡혀야 빌더가 .php 로 떨군다
        # (안 그러면 대문자 태그가 .html 페이지에 평문으로 샌다).
        self.assertTrue(has_live_php('<?PHP echo "x"; ?>'))
        self.assertTrue(has_live_php('<?Php $x ?>'))

    def test_negative(self):
        self.assertFalse(has_live_php('<p>no php here</p>'))


class ParsePhpGlobalsTests(unittest.TestCase):

    def test_basic_and_dollar_strip(self):
        self.assertEqual(
            parse_php_globals({'$a': 'x', 'b': 'y'}),
            {'a': 'x', 'b': 'y'})

    def test_non_dict_and_none(self):
        self.assertEqual(parse_php_globals(None), {})
        self.assertEqual(parse_php_globals('nope'), {})
        self.assertEqual(parse_php_globals(['a']), {})

    def test_none_value_becomes_empty_str(self):
        self.assertEqual(parse_php_globals({'a': None}), {'a': ''})

    def test_non_str_value_coerced(self):
        self.assertEqual(parse_php_globals({'a': 7}), {'a': '7'})


class SimulatePhpTests(unittest.TestCase):
    """v1.1.1 — 다중 구문 `<?php … ?>` 블록 정적 시뮬레이션 회귀."""

    DIR = Path('.')

    def sim(self, text, g=None):
        return simulate_php_in_html(text, 'slug', self.DIR, g or {})

    # ── 단일 호출 한 줄 형태 (v1.1.1 이전부터 동작 — 회귀 가드) ──
    def test_single_call_oneliner_unchanged(self):
        out = self.sim('<p>x</p>\n<?php imgBox("a.png", "cap") ?>\n')
        self.assertNotIn('<?php', out)
        self.assertIn('<div class="imgBox">', out)
        self.assertIn('<img src="/slug/a.png" alt="">', out)
        self.assertIn('<p class="caption">cap</p>', out)
        # 앞뒤 텍스트·개행은 그대로 보존
        self.assertTrue(out.startswith('<p>x</p>\n'))
        self.assertTrue(out.endswith('</div>\n'))

    # ── 핵심 버그: 다중 imgBox 블록 (배포 시 truncate 되던 형태) ──
    def test_multi_call_block_all_expanded_no_leak(self):
        src = ('<h4>img</h4>\n<?php\n'
               '    imgBox("./1.png", "A");\n'
               '    imgBox("./2.png", "B");\n?>\n<hr>\n')
        out = self.sim(src)
        self.assertNotIn('<?php', out)            # truncate 원인 제거
        self.assertEqual(out.count('<div class="imgBox">'), 2)
        self.assertIn('<p class="caption">A</p>', out)
        self.assertIn('<p class="caption">B</p>', out)
        self.assertIn('<hr>', out)                # 블록 뒤 HTML 살아남음

    def test_two_calls_on_one_line(self):
        out = self.sim('<?php imgBox("a.png","A");imgBox("b.png","B"); ?>')
        self.assertEqual(out.count('<div class="imgBox">'), 2)
        self.assertNotIn('<?php', out)

    # ── global 선언 제거 + {$var}/$var 보간 (u-hof / radish 케이스) ──
    def test_global_stripped_and_braced_interpolation(self):
        src = ('<?php\n'
               '    global $sig;  // GlobalVariable.php\n'
               '    imgBox("./x.png", "Cap.<br>&nbsp;{$sig}");\n?>')
        out = self.sim(src, {'sig': 'by An Illustrator'})
        self.assertNotIn('<?php', out)
        self.assertNotIn('global', out)
        # 캡션은 이스케이프되지 않는다 — <br> 가 살아 있어야 함
        self.assertIn('<p class="caption">Cap.<br>&nbsp;by An Illustrator</p>', out)

    def test_bare_dollar_interpolation_double_quoted(self):
        out = self.sim('<?php imgBox("a.png", "x $v y") ?>', {'v': 'Z'})
        self.assertIn('<p class="caption">x Z y</p>', out)

    def test_undefined_var_becomes_empty(self):
        out = self.sim('<?php imgBox("a.png", "[{$missing}]") ?>', {})
        self.assertIn('<p class="caption">[]</p>', out)

    def test_single_quoted_arg_not_interpolated(self):
        out = self.sim("<?php imgBox('a.png', '$v {$v}') ?>", {'v': 'Z'})
        self.assertIn('<p class="caption">$v {$v}</p>', out)

    # ── 주석 처리 ──
    def test_fully_commented_block_disappears(self):
        out = self.sim('<a>x</a>\n<?php // imgBox("a.png","c") ?>\n<b>y</b>')
        self.assertNotIn('<?php', out)
        self.assertNotIn('imgBox', out)
        self.assertNotIn('class="imgBox"', out)
        self.assertIn('<a>x</a>', out)
        self.assertIn('<b>y</b>', out)

    def test_hash_and_block_comments_skipped(self):
        src = ('<?php\n  # a hash comment\n  /* block\n  comment */\n'
               '  imgBox("a.png","C");\n?>')
        out = self.sim(src)
        self.assertNotIn('<?php', out)
        self.assertEqual(out.count('<div class="imgBox">'), 1)
        self.assertIn('<p class="caption">C</p>', out)

    # ── 보수성: 알 수 없는 동적 구문은 블록 원문 보존 ──
    def test_unknown_dynamic_php_left_verbatim(self):
        src = '<?php echo strtoupper($x); imgBox("a.png","c"); ?>'
        out = self.sim(src)
        self.assertEqual(out, src)            # 원문 그대로
        self.assertTrue(has_live_php(out))

    def test_unknown_function_call_left_verbatim(self):
        src = '<?php mystery("a"); ?>'
        self.assertEqual(self.sim(src), src)

    # ── 인자 파싱 견고성 ──
    def test_nested_parens_and_inner_quotes_in_args(self):
        src = ('<?php imgBox("a(b).png", '
               '"Cap (paren) and <a href=\'http://x/y?z=1\'>L</a>") ?>')
        out = self.sim(src)
        self.assertIn('<img src="/slug/a(b).png"', out)
        self.assertIn("<a href='http://x/y?z=1'>L</a>", out)
        self.assertNotIn('<?php', out)

    def test_close_tag_inside_string_does_not_end_block(self):
        # 문자열 안 '?>' 가 블록을 조기 종료하면 안 됨
        out = self.sim('<?php imgBox("a.png", "arrow ?> here") ?>X')
        self.assertIn('<p class="caption">arrow ?> here</p>', out)
        self.assertTrue(out.endswith('X'))
        self.assertNotIn('<?php', out)

    def test_no_php_passthrough(self):
        html = '<p>just html</p>'
        self.assertEqual(self.sim(html), html)

    def test_unterminated_block_left_verbatim(self):
        src = '<p>a</p><?php imgBox("a.png","c")'   # 닫는 ?> 없음
        self.assertEqual(self.sim(src), src)

    # ── v1.14.1: 짧은 echo 태그 + 대소문자 변종 여는 태그 ──
    def test_short_echo_tag_imgbox_expanded(self):
        # B5: `<?= imgBox(...) ?>` 는 echo 의미 — 안의 호출을 펼친다.
        out = self.sim('<?= imgBox("a.png","cap","alt") ?>')
        self.assertNotIn('<?=', out)
        self.assertIn('<div class="imgBox">', out)
        self.assertIn('<p class="caption">cap</p>', out)

    def test_short_echo_dynamic_left_verbatim(self):
        # 짧은 태그라도 동적 표현식은 보수적으로 원문 보존.
        self.assertEqual(self.sim('<?= $x ?>'), '<?= $x ?>')
        self.assertEqual(self.sim('<?= strtoupper($x) ?>'),
                         '<?= strtoupper($x) ?>')

    def test_uppercase_php_tag_imgbox_expanded(self):
        # B7: `<?PHP`/`<?Php` 도 PHP 처럼 인식해 펼친다(평문 누수 방지).
        out = self.sim('<?PHP imgBox("a.png","cap","alt") ?>')
        self.assertNotIn('<?PHP', out)
        self.assertNotIn('<?php', out.lower())
        self.assertIn('<div class="imgBox">', out)
        out2 = self.sim('<?Php imgBox("a.png","C") ?>')
        self.assertIn('<p class="caption">C</p>', out2)

    # ── process_html 통합 (asset 재작성과 함께) ──
    def test_process_html_threads_globals(self):
        rr = process_html('<?php imgBox("p.png", "{$c}") ?>',
                          'sl', self.DIR, {'c': 'CR'})
        self.assertIn('<img src="/sl/p.png"', rr.html)
        self.assertIn('<p class="caption">CR</p>', rr.html)
        self.assertFalse(has_live_php(rr.html))


if __name__ == '__main__':
    unittest.main()

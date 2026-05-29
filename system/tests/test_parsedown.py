"""scripts/parsedown.Parsedown 단위 테스트 (v0.6.0).

PHP 원본 (Parsedown 1.7.4) 과의 동등성 비교는 본 테스트 범위 아님 — 사용자가
포팅 시 별도 검증을 거쳤다고 명시. 본 테스트는 *Python 포트의 기본 마크다운
요소* 가 잘 동작하는지 확인하는 회귀 가드 (header / list / code / inline /
emphasis / link / image / paragraph).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.parsedown import Parsedown  # noqa: E402


def md(text: str) -> str:
    return Parsedown().text(text)


class HeaderTests(unittest.TestCase):

    def test_h1(self):
        self.assertIn('<h1>Hello</h1>', md('# Hello'))

    def test_h2_through_h6(self):
        for level in range(2, 7):
            hashes = '#' * level
            out = md(f'{hashes} Title')
            self.assertIn(f'<h{level}>Title</h{level}>', out)

    def test_setext_h1(self):
        # `Title\n===` → h1
        out = md('Hello\n=====')
        self.assertIn('<h1>Hello</h1>', out)


class ParagraphTests(unittest.TestCase):

    def test_simple_paragraph(self):
        self.assertIn('<p>Hello world.</p>', md('Hello world.'))

    def test_paragraph_with_inline_formatting(self):
        out = md('Hello **bold** and *italic*.')
        self.assertIn('<strong>bold</strong>', out)
        self.assertIn('<em>italic</em>', out)


class ListTests(unittest.TestCase):

    def test_unordered_list(self):
        out = md('- a\n- b\n- c')
        self.assertIn('<ul>', out)
        self.assertIn('<li>a</li>', out)
        self.assertIn('<li>b</li>', out)
        self.assertIn('<li>c</li>', out)

    def test_ordered_list(self):
        out = md('1. a\n2. b\n3. c')
        self.assertIn('<ol>', out)
        self.assertIn('<li>a</li>', out)


class CodeTests(unittest.TestCase):

    def test_inline_code(self):
        out = md('Use `foo()` here.')
        self.assertIn('<code>foo()</code>', out)

    def test_fenced_code_block(self):
        out = md('```\nprint("x")\n```')
        self.assertIn('<pre>', out)
        self.assertIn('<code>', out)
        # Parsedown 은 fenced code block 안에서 따옴표를 escape 하지 않음
        self.assertIn('print("x")', out)

    def test_fenced_code_with_language(self):
        out = md('```python\nx = 1\n```')
        self.assertIn('language-python', out)


class LinkTests(unittest.TestCase):

    def test_inline_link(self):
        out = md('[text](https://example.com)')
        self.assertIn('<a href="https://example.com">text</a>', out)

    def test_autolink(self):
        out = md('<https://example.com>')
        self.assertIn('href="https://example.com"', out)


class ImageTests(unittest.TestCase):

    def test_image(self):
        out = md('![alt text](pic.png)')
        self.assertIn('<img', out)
        self.assertIn('src="pic.png"', out)
        self.assertIn('alt="alt text"', out)


class BlockquoteTests(unittest.TestCase):

    def test_blockquote(self):
        out = md('> quote\n> body')
        self.assertIn('<blockquote>', out)
        self.assertIn('quote', out)


class HorizontalRuleTests(unittest.TestCase):

    def test_hr_dashes(self):
        out = md('---')
        self.assertIn('<hr', out)

    def test_hr_asterisks(self):
        out = md('***')
        self.assertIn('<hr', out)


class EscapingTests(unittest.TestCase):

    def test_html_special_chars_in_text(self):
        # markdown 본문의 < > & 는 escape 되어야
        out = md('a < b & c > d')
        self.assertIn('&lt;', out)
        self.assertIn('&amp;', out)
        # `>` 는 blockquote 아닌 inline 위치라 그대로 출력될 수도 있음
        # (Parsedown 동작) — 핵심은 < 와 & 가 escape 되는 것

    def test_html_passes_through(self):
        # 원본 Parsedown 은 HTML 을 그대로 통과시킴
        out = md('<div>inner</div>')
        self.assertIn('<div>inner</div>', out)


class CombinedTests(unittest.TestCase):

    def test_mixed_document(self):
        src = (
            '# Title\n\n'
            'Para with **bold**.\n\n'
            '- one\n- two\n\n'
            '```\ncode\n```\n'
        )
        out = md(src)
        self.assertIn('<h1>Title</h1>', out)
        self.assertIn('<strong>bold</strong>', out)
        self.assertIn('<ul>', out)
        self.assertIn('<pre>', out)


if __name__ == '__main__':
    unittest.main()

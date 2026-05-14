"""slugs.category_slug_from_name 단위 테스트 (v0.6.0).

v0.4.0 의 5단계 + 비ASCII pre-escape (scripts/slugs.py docstring 참조).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.slugs import (  # noqa: E402
    category_slug_from_name,
    has_non_ascii,
)


class SlugTests(unittest.TestCase):

    def test_ascii_plain(self):
        self.assertEqual(category_slug_from_name('Blog'), 'blog')

    def test_ascii_with_space(self):
        self.assertEqual(category_slug_from_name('My Posts'), 'my-posts')

    def test_ascii_with_parens(self):
        # 괄호는 제거 (5단계 step 4)
        self.assertEqual(category_slug_from_name('Foo (2026)'), 'foo-2026')

    def test_consecutive_spaces_collapse(self):
        self.assertEqual(category_slug_from_name('Foo   Bar'), 'foo-bar')

    def test_consecutive_hyphens_collapse(self):
        self.assertEqual(category_slug_from_name('foo---bar'), 'foo-bar')

    def test_trailing_hyphen_stripped(self):
        self.assertEqual(category_slug_from_name('foo-'), 'foo')
        self.assertEqual(category_slug_from_name('-foo-'), 'foo')

    def test_lowercase(self):
        self.assertEqual(category_slug_from_name('FOO'), 'foo')

    def test_non_ascii_korean(self):
        # 한글 '블로그' → U+BE14 U+B85C U+ADF8
        result = category_slug_from_name('블로그')
        self.assertEqual(result, 'be14-b85c-adf8')

    def test_non_ascii_with_ascii_prefix(self):
        # ASCII 와 비ASCII 가 섞인 경우
        result = category_slug_from_name('Hello 한')
        # '한' → 'd55c-'. Hello-d55c (마지막 '-' strip).
        self.assertEqual(result, 'hello-d55c')

    def test_numeric_preserved(self):
        self.assertEqual(category_slug_from_name('2026 Posts'), '2026-posts')


class HasNonAsciiTests(unittest.TestCase):

    def test_pure_ascii(self):
        self.assertFalse(has_non_ascii('Hello World 123'))

    def test_has_korean(self):
        self.assertTrue(has_non_ascii('블로그'))

    def test_has_japanese(self):
        self.assertTrue(has_non_ascii('日本語'))

    def test_has_emoji(self):
        self.assertTrue(has_non_ascii('hello 🌍'))


if __name__ == '__main__':
    unittest.main()

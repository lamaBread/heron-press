"""yaml_parser.yaml_load — stdlib-only YAML 부분 구현 단위 테스트 (v0.6.0).

지원 문법 (scripts/yaml_parser.py 의 docstring 참조):
  key: value (string/int/bool/null), quoted key, key: [a, b] (inline list),
  block list, block map (nested), key: | (literal block), 주석.

PyYAML 미사용. 본 모듈은 사이트의 단일 진실원이므로 회귀가 곧 빌드 전반의
재해이다 — 본 테스트는 자주 쓰이는 패턴을 우선 커버한다.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.yaml_parser import yaml_load  # noqa: E402


class ScalarTests(unittest.TestCase):

    def test_plain_string(self):
        self.assertEqual(yaml_load('key: hello'), {'key': 'hello'})

    def test_quoted_string(self):
        self.assertEqual(yaml_load('key: "hello"'), {'key': 'hello'})
        self.assertEqual(yaml_load("key: 'hello'"), {'key': 'hello'})

    def test_integer(self):
        self.assertEqual(yaml_load('count: 42'), {'count': 42})
        self.assertEqual(yaml_load('count: -5'), {'count': -5})

    def test_bool_true_false(self):
        self.assertEqual(yaml_load('flag: true'), {'flag': True})
        self.assertEqual(yaml_load('flag: false'), {'flag': False})
        self.assertEqual(yaml_load('flag: True'), {'flag': True})
        self.assertEqual(yaml_load('flag: FALSE'), {'flag': False})

    def test_null_variants(self):
        for variant in ('null', '~', 'Null', 'NULL'):
            self.assertIsNone(yaml_load(f'k: {variant}')['k'])

    def test_empty_value_is_null(self):
        # `key:` (값 없음) → None.
        self.assertIsNone(yaml_load('k:')['k'])

    def test_empty_string_preserved_as_empty(self):
        # v0.5.5 의 SeoMeta 가 3-상태 (None / '' / 'text') 이므로, 빈 따옴표
        # 문자열이 None 으로 변환되지 않아야 함.
        self.assertEqual(yaml_load('k: ""')['k'], '')
        self.assertEqual(yaml_load("k: ''")['k'], '')


class InlineListTests(unittest.TestCase):

    def test_empty_inline_list(self):
        self.assertEqual(yaml_load('xs: []'), {'xs': []})

    def test_inline_list(self):
        self.assertEqual(yaml_load('xs: [a, b, c]'), {'xs': ['a', 'b', 'c']})

    def test_inline_list_mixed_types(self):
        self.assertEqual(yaml_load('xs: [1, "two", true]'),
                         {'xs': [1, 'two', True]})


class BlockListTests(unittest.TestCase):

    def test_block_list(self):
        src = 'xs:\n  - a\n  - b\n  - c'
        self.assertEqual(yaml_load(src), {'xs': ['a', 'b', 'c']})

    def test_block_list_with_dash_only(self):
        src = 'xs:\n  -\n  - b'
        self.assertEqual(yaml_load(src), {'xs': [None, 'b']})


class BlockMapTests(unittest.TestCase):

    def test_nested_map(self):
        src = 'a:\n  b: 1\n  c: 2'
        self.assertEqual(yaml_load(src), {'a': {'b': 1, 'c': 2}})

    def test_seo_block_typical(self):
        # 사이트의 meta.yaml 패턴
        src = (
            'slug: hello\n'
            'title: Hello, World!\n'
            'date: 2026-01-01\n'
            'seo:\n'
            '  description: Welcome\n'
            '  og_image: /static/og.png\n'
        )
        d = yaml_load(src)
        self.assertEqual(d['slug'], 'hello')
        self.assertEqual(d['title'], 'Hello, World!')
        self.assertEqual(d['seo'], {
            'description': 'Welcome',
            'og_image': '/static/og.png',
        })


class LiteralBlockTests(unittest.TestCase):

    def test_literal_block_preserves_newlines(self):
        src = 'desc: |\n  line one\n  line two\n'
        # literal block 은 끝에 \n 추가 보존
        self.assertEqual(yaml_load(src)['desc'], 'line one\nline two\n')


class CommentTests(unittest.TestCase):

    def test_full_line_comment_skipped(self):
        src = '# leading comment\nk: v\n# trailing'
        self.assertEqual(yaml_load(src), {'k': 'v'})

    def test_blank_lines_skipped(self):
        src = '\n\nk: v\n\n'
        self.assertEqual(yaml_load(src), {'k': 'v'})


class QuotedKeyTests(unittest.TestCase):

    def test_quoted_key_with_slash(self):
        # legacy-map.yaml 의 경로 키 패턴 (예: "old/path/index.php": new)
        src = '"old/path.php": new-slug'
        self.assertEqual(yaml_load(src), {'old/path.php': 'new-slug'})


if __name__ == '__main__':
    unittest.main()

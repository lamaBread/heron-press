"""search.php_array_literal — Python 값 → PHP 배열 리터럴 결정적 직렬화
단위 테스트 (v0.6.0 신규).

빌드 시 인덱스 dict 를 dist/search.php 에 인라인할 때 사용. PHP 가 그대로
파싱 가능해야 하고, 같은 입력 → 같은 텍스트 (결정성) 가 보장되어야 한다.

PHP 가 실제로 파싱 가능한지 확인하려면 별도 PHP 호출 — 이 테스트는
호스트에 PHP 가 있으면 추가로 검증한다 (없으면 skip).
"""
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.search import php_array_literal  # noqa: E402


PHP_BIN = shutil.which('php')


def _php_eval(literal: str) -> object:
    """Compose `<?php echo json_encode(<literal>);` and run via PHP CLI.

    Returns parsed JSON. Raises if PHP fails.
    """
    if not PHP_BIN:
        raise unittest.SkipTest('PHP not available')
    code = f'<?php echo json_encode({literal}, JSON_UNESCAPED_UNICODE);'
    proc = subprocess.run(
        [PHP_BIN, '-r', f'echo json_encode({literal}, JSON_UNESCAPED_UNICODE);'],
        capture_output=True, timeout=15,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f'PHP rejected literal: {proc.stderr.decode("utf-8", errors="replace")}'
        )
    return json.loads(proc.stdout.decode('utf-8'))


class PrimitiveTests(unittest.TestCase):

    def test_none(self):
        self.assertEqual(php_array_literal(None), 'null')

    def test_true(self):
        self.assertEqual(php_array_literal(True), 'true')

    def test_false(self):
        self.assertEqual(php_array_literal(False), 'false')

    def test_int(self):
        self.assertEqual(php_array_literal(42), '42')
        self.assertEqual(php_array_literal(-7), '-7')

    def test_float(self):
        out = php_array_literal(1.5)
        self.assertEqual(out, '1.5')

    def test_str_simple(self):
        self.assertEqual(php_array_literal('hello'), "'hello'")

    def test_str_with_single_quote(self):
        # ' → \'
        self.assertEqual(php_array_literal("it's"), "'it\\'s'")

    def test_str_with_backslash(self):
        # \ → \\
        self.assertEqual(php_array_literal('a\\b'), "'a\\\\b'")

    def test_str_with_utf8(self):
        # UTF-8 그대로 보존
        out = php_array_literal('한글')
        self.assertEqual(out, "'한글'")


class ListTests(unittest.TestCase):

    def test_empty_list(self):
        self.assertEqual(php_array_literal([]), '[]')

    def test_int_list(self):
        self.assertEqual(php_array_literal([1, 2, 3]), '[1,2,3]')

    def test_mixed_list(self):
        self.assertEqual(php_array_literal(['a', 1, True, None]),
                         "['a',1,true,null]")

    def test_nested_list(self):
        self.assertEqual(php_array_literal([[1, 2], [3, 4]]),
                         '[[1,2],[3,4]]')


class AssocTests(unittest.TestCase):

    def test_empty_dict(self):
        self.assertEqual(php_array_literal({}), '[]')

    def test_string_keys(self):
        self.assertEqual(php_array_literal({'a': 1, 'b': 2}),
                         "['a'=>1,'b'=>2]")

    def test_nested_dict(self):
        out = php_array_literal({'k': {'inner': 'v'}})
        self.assertEqual(out, "['k'=>['inner'=>'v']]")

    def test_keys_preserve_order(self):
        # dict 의 insertion order 가 PHP 출력에 보존
        out = php_array_literal({'z': 1, 'a': 2})
        self.assertEqual(out, "['z'=>1,'a'=>2]")


class DeterminismTests(unittest.TestCase):

    def test_same_input_same_output(self):
        value = {
            'version': 4,
            'params': {'k1': 1.2, 'b': 0.5},
            'docs': [{'slug': 'a', 'title': 'A'}, {'slug': 'b', 'title': 'B'}],
            'df_title': {'hello': 1, 'world': 1},
        }
        a = php_array_literal(value)
        b = php_array_literal(value)
        self.assertEqual(a, b)


@unittest.skipUnless(PHP_BIN, 'PHP not available')
class PhpRoundTripTests(unittest.TestCase):
    """PHP CLI 로 직접 파싱해 결과가 의도한 값과 일치하는지 확인."""

    def test_int_roundtrip(self):
        self.assertEqual(_php_eval(php_array_literal(42)), 42)

    def test_str_roundtrip_with_quote(self):
        self.assertEqual(_php_eval(php_array_literal("it's")), "it's")

    def test_str_roundtrip_with_backslash(self):
        self.assertEqual(_php_eval(php_array_literal('a\\b')), 'a\\b')

    def test_utf8_roundtrip(self):
        self.assertEqual(_php_eval(php_array_literal('한글')), '한글')

    def test_nested_assoc(self):
        v = {'k': {'inner': [1, 'two', True]}}
        self.assertEqual(_php_eval(php_array_literal(v)),
                         {'k': {'inner': [1, 'two', True]}})

    def test_full_index_shape(self):
        # 인덱스 구조와 유사한 nested dict.
        v = {
            'version': 4,
            'docs': [
                {'slug': 'a', 'tags': ['x', 'y'], 'dl_title': 2},
                {'slug': 'b', 'tags': [], 'dl_title': 1},
            ],
            'df_title': {'hello': 1, '한글': 1},
            'tf_title': {'hello': [[0, 1]], '한글': [[1, 1]]},
        }
        result = _php_eval(php_array_literal(v))
        self.assertEqual(result['version'], 4)
        self.assertEqual(result['docs'][0]['slug'], 'a')
        self.assertEqual(result['df_title']['한글'], 1)


if __name__ == '__main__':
    unittest.main()

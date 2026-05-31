"""v1.6.0 신설 — 스키마 버전 스탬프 + semver 비교 단위 테스트.

검증:
  - parse_version / compare 의 경계 (선행 v, pre-release 접미, 자리수 패딩).
  - read_schema_version 의 부재→베이스라인, 형식오류→베이스라인.
  - write_schema_version 의 위치(user/.heron/version)·내용·왕복.
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from scripts import version  # noqa: E402


class TestParseCompare(unittest.TestCase):
    def test_parse_version(self):
        self.assertEqual(version.parse_version('1.6.0'), (1, 6, 0))
        self.assertEqual(version.parse_version('v1.5.3'), (1, 5, 3))
        self.assertEqual(version.parse_version('1.6.0-rc1'), (1, 6, 0))
        self.assertEqual(version.parse_version('1.6.0+build'), (1, 6, 0))
        self.assertIsNone(version.parse_version('latest'))
        self.assertIsNone(version.parse_version(''))
        self.assertIsNone(version.parse_version(None))

    def test_compare(self):
        self.assertEqual(version.compare('1.5.3', '1.6.0'), -1)
        self.assertEqual(version.compare('1.6.0', '1.5.3'), 1)
        self.assertEqual(version.compare('1.6.0', '1.6.0'), 0)
        # 자리수 패딩 — 1.6 == 1.6.0
        self.assertEqual(version.compare('1.6', '1.6.0'), 0)
        # 선행 v 무시
        self.assertEqual(version.compare('v1.6.0', '1.6.0'), 0)
        self.assertEqual(version.compare('v1.5.3', 'v1.6.0'), -1)


class TestStamp(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / 'user').mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_missing_is_baseline(self):
        self.assertEqual(version.read_schema_version(self.tmp),
                         version.BASELINE_VERSION)

    def test_write_read_roundtrip(self):
        version.write_schema_version(self.tmp, '1.6.0')
        self.assertEqual(version.read_schema_version(self.tmp), '1.6.0')
        f = version.version_file(self.tmp)
        self.assertTrue(f.is_file())
        self.assertEqual(f.read_text(encoding='utf-8').strip(), '1.6.0')
        # 위치 = user/.heron/version (system/ 교체에도 생존하도록)
        self.assertEqual(f.parent.name, '.heron')
        self.assertEqual(f.parent.parent.name, 'user')

    def test_garbage_is_baseline(self):
        f = version.version_file(self.tmp)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text('not-a-version\n', encoding='utf-8')
        self.assertEqual(version.read_schema_version(self.tmp),
                         version.BASELINE_VERSION)

    def test_leading_v_in_file(self):
        f = version.version_file(self.tmp)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text('v1.6.0\n', encoding='utf-8')
        self.assertEqual(version.read_schema_version(self.tmp), '1.6.0')


if __name__ == '__main__':
    unittest.main()

"""v1.6.0 신설 — 마이그레이션 엔진 단위 테스트.

검증:
  - _yamledit.remove_key: 스칼라/블록리스트/인라인 제거, 주석·타 키 보존,
    중첩 동명 키 미오염, 부재 시 no-op.
  - m_1_6_0: plan/apply 동등성, 멱등성, site.yaml 부재 시 안전.
  - run(): plan_chain 선택, 스탬프 기록, dry_run 무쓰기, 이미-최신 no-op.
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from scripts import migrations, version  # noqa: E402
from scripts.migrations import _yamledit  # noqa: E402
from scripts.migrations.m_1_6_0 import RETIRED_SITE_KEYS  # noqa: E402


class TestYamlEdit(unittest.TestCase):
    def test_top_level_key_detection(self):
        self.assertEqual(_yamledit._top_level_key('domain: x.com'), 'domain')
        self.assertIsNone(_yamledit._top_level_key('  enabled: true'))  # 들여쓰기
        self.assertIsNone(_yamledit._top_level_key('# comment'))
        self.assertIsNone(_yamledit._top_level_key('  - item'))
        self.assertIsNone(_yamledit._top_level_key(''))

    def test_remove_scalar_preserves_neighbours(self):
        text = ('# top\ndomain: x.com\n'
                'warn_on_underscore_ref: true\nname: Site\n# tail\n')
        out, did = _yamledit.remove_key(text, 'warn_on_underscore_ref')
        self.assertTrue(did)
        self.assertNotIn('warn_on_underscore_ref', out)
        self.assertIn('# top', out)
        self.assertIn('domain: x.com', out)
        self.assertIn('name: Site', out)
        self.assertIn('# tail', out)

    def test_remove_block_list(self):
        text = 'a: 1\nreserved_slugs:\n  - foo\n  - bar\nb: 2\n'
        out, did = _yamledit.remove_key(text, 'reserved_slugs')
        self.assertTrue(did)
        self.assertEqual(out, 'a: 1\nb: 2\n')

    def test_remove_inline_list(self):
        text = 'a: 1\nreserved_slugs: [foo, bar]\nb: 2\n'
        out, did = _yamledit.remove_key(text, 'reserved_slugs')
        self.assertTrue(did)
        self.assertEqual(out, 'a: 1\nb: 2\n')

    def test_absent_is_noop(self):
        text = 'domain: x.com\nname: Site\n'
        out, did = _yamledit.remove_key(text, 'reserved_slugs')
        self.assertFalse(did)
        self.assertEqual(out, text)

    def test_nested_same_name_not_removed(self):
        # 톱레벨이 아닌 동명 키(images.enabled 같은)는 건드리지 않는다.
        text = 'images:\n  enabled: true\n  quality: 85\n'
        out, did = _yamledit.remove_key(text, 'enabled')
        self.assertFalse(did)
        self.assertEqual(out, text)


class TestM160(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / 'user').mkdir()
        self.sy = self.tmp / 'user' / 'site.yaml'

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, text):
        self.sy.write_text(text, encoding='utf-8')

    def test_removes_all_retired_keys_idempotent(self):
        self._write(
            '# heading\n'
            'domain: x.com\n'
            'reserved_slugs:\n  - a\n  - b\n'
            'warn_on_underscore_ref: true\n'
            'warn_on_missing_asset: true\n'
            'error_404_title: "Not found"\n'
            'search_title: Search\n'
            'name: Site\n'
        )
        from scripts.migrations.m_1_6_0 import Migration_1_6_0
        m = Migration_1_6_0()
        # plan == apply 의 보고 내용 (적용 전)
        planned = m.plan(self.tmp)
        self.assertEqual(len(planned), 1)
        applied = m.apply(self.tmp)
        self.assertEqual(len(applied), 1)
        result = self.sy.read_text(encoding='utf-8')
        for k in RETIRED_SITE_KEYS:
            self.assertNotIn(k, result)
        self.assertIn('domain: x.com', result)
        self.assertIn('name: Site', result)
        self.assertIn('# heading', result)
        # 멱등: 다시 적용하면 변경 없음
        again = m.apply(self.tmp)
        self.assertEqual(again, [])

    def test_clean_site_is_noop(self):
        self._write('domain: x.com\nname: Site\n')
        from scripts.migrations.m_1_6_0 import Migration_1_6_0
        self.assertEqual(Migration_1_6_0().apply(self.tmp), [])

    def test_missing_site_yaml_safe(self):
        from scripts.migrations.m_1_6_0 import Migration_1_6_0
        self.assertEqual(Migration_1_6_0().apply(self.tmp), [])


class TestRunChain(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / 'user').mkdir()
        (self.tmp / 'user' / 'site.yaml').write_text(
            'domain: x.com\nreserved_slugs: [a, b]\nname: Site\n',
            encoding='utf-8')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_plan_chain_selects_pending(self):
        chain = migrations.plan_chain('1.5.3', '1.6.0')
        self.assertEqual([(m.from_version, m.to_version) for m in chain],
                         [('1.5.3', '1.6.0')])
        # 이미 최신이면 빈 체인
        self.assertEqual(migrations.plan_chain('1.6.0', '1.6.0'), [])

    def test_dry_run_writes_nothing(self):
        before = (self.tmp / 'user' / 'site.yaml').read_text(encoding='utf-8')
        res = migrations.run(self.tmp, target='1.6.0', dry_run=True)
        self.assertFalse(res['stamped'])
        self.assertEqual(version.read_schema_version(self.tmp),
                         version.BASELINE_VERSION)  # 스탬프 미기록
        self.assertEqual(
            (self.tmp / 'user' / 'site.yaml').read_text(encoding='utf-8'),
            before)  # site.yaml 불변
        self.assertTrue(res['changes'])  # 보고는 있음

    def test_apply_migrates_and_stamps(self):
        res = migrations.run(self.tmp, target='1.6.0')
        self.assertTrue(res['stamped'])
        self.assertEqual(version.read_schema_version(self.tmp), '1.6.0')
        self.assertNotIn(
            'reserved_slugs',
            (self.tmp / 'user' / 'site.yaml').read_text(encoding='utf-8'))

    def test_already_current_no_stamp_write_needed(self):
        version.write_schema_version(self.tmp, '1.6.0')
        res = migrations.run(self.tmp, target='1.6.0')
        self.assertFalse(res['stamped'])  # current == target → 재기록 안 함
        self.assertEqual(res['changes'], [])


if __name__ == '__main__':
    unittest.main()

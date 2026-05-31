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


class TestNewlinePreservation(unittest.TestCase):
    """v1.6.1 — 마이그레이션 편집이 원본 개행(LF/CRLF)을 통째로 뒤집지 않는다.

    회귀 방지: read_text + write_text(텍스트 모드)는 Windows 에서 LF↔CRLF 를
    번역해 "건드린 줄만 바뀐다"는 외과적 편집을 깨뜨렸다 (실제 v1.2.2 site.yaml
    마이그레이션에서 전 라인이 CRLF 로 뒤집힘). read_preserving(bytes) +
    atomic_write(bytes) 로 양방향 모두 보존한다.
    """
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / 'user').mkdir()
        self.sy = self.tmp / 'user' / 'site.yaml'

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _apply(self):
        from scripts.migrations.m_1_6_0 import Migration_1_6_0
        Migration_1_6_0().apply(self.tmp)

    def test_lf_original_stays_lf(self):
        self.sy.write_bytes(
            b'domain: x.com\nreserved_slugs:\n  - a\n  - b\nname: Site\n')
        self._apply()
        out = self.sy.read_bytes()
        self.assertNotIn(b'\r', out)            # CRLF 로 뒤집히지 않음
        self.assertNotIn(b'reserved_slugs', out)
        self.assertIn(b'domain: x.com\n', out)
        self.assertIn(b'name: Site\n', out)

    def test_crlf_original_stays_crlf(self):
        self.sy.write_bytes(
            b'domain: x.com\r\nreserved_slugs:\r\n  - a\r\n  - b\r\n'
            b'name: Site\r\n')
        self._apply()
        out = self.sy.read_bytes()
        self.assertNotIn(b'\n', out.replace(b'\r\n', b''))  # 순수 LF 없음
        self.assertIn(b'domain: x.com\r\n', out)
        self.assertIn(b'name: Site\r\n', out)
        self.assertNotIn(b'reserved_slugs', out)

    def test_atomic_write_roundtrip_is_byte_exact(self):
        # 편집이 없을 만큼 무관한 키만 있으면 파일은 한 바이트도 안 변한다.
        raw = b'domain: x.com\nname: Site\nimages:\n  enabled: true\n'
        self.sy.write_bytes(raw)
        self._apply()                            # 폐기 키 없음 → no-op
        self.assertEqual(self.sy.read_bytes(), raw)


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

    # ── v1.6.1: 적용 전 사용자 콘텐츠 백업 ──────────────────────────
    def _backups_root(self):
        return self.tmp / 'user' / '.heron' / 'backups'

    def test_apply_backs_up_original_before_mutating(self):
        res = migrations.run(self.tmp, target='1.6.0')
        # 반환에 백업 경로가 있고, 실제 폴더가 존재한다.
        self.assertIsNotNone(res['backup'])
        self.assertTrue(self._backups_root().is_dir())
        backups = list(self._backups_root().glob('migrate-*'))
        self.assertEqual(len(backups), 1)
        # 백업본은 *원본* — 폐기 키가 아직 들어 있어야 한다.
        saved = (backups[0] / 'user' / 'site.yaml').read_text(encoding='utf-8')
        self.assertIn('reserved_slugs', saved)
        # 현재 파일은 마이그레이션됨 (폐기 키 제거).
        self.assertNotIn(
            'reserved_slugs',
            (self.tmp / 'user' / 'site.yaml').read_text(encoding='utf-8'))

    def test_clean_site_makes_no_backup(self):
        # 바뀔 게 없으면(폐기 키 없음) 백업 폴더도 안 만든다 — 스탬프만 전진.
        (self.tmp / 'user' / 'site.yaml').write_text(
            'domain: x.com\nname: Site\n', encoding='utf-8')
        res = migrations.run(self.tmp, target='1.6.0')
        self.assertIsNone(res['backup'])
        self.assertFalse(self._backups_root().exists())
        self.assertTrue(res['stamped'])  # 콘텐츠 변경 0건이어도 스탬프는 찍힘

    def test_dry_run_makes_no_backup(self):
        migrations.run(self.tmp, target='1.6.0', dry_run=True)
        self.assertFalse(self._backups_root().exists())


if __name__ == '__main__':
    unittest.main()

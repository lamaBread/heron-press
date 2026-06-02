"""v1.9.7 신설 — 로케일 점검·스캐폴딩 도구(locale_tools) 단위 테스트.

실 ``system/locales/`` 를 절대 건드리지 않는다 — setUp 에서 임시 디렉터리에
최소 CANONICAL(en) 팩(admin/cli 조각 몇 줄)을 깔고 check/scaffold 에
``locales_dir=tmp`` 로 격리 주입한다 (i18n._load_pack 의 매개화 경로).

검증:
  - 코드 검증: '../x' 'a/b' '' '1bad' 거부, 'ja' 'zh-Hans' 수용.
  - scaffold: 정본 *.yaml 바이트 복사 + endonym 주입(모든 팩) + 종료 0,
              같은 코드 재실행은 1(기존 거부).
  - check: 스캐폴딩 직후 0 누락/0 잉여 → 0; 키 삭제 → 누락>0 & 1;
           키 추가 → 잉여>0 & 1; 잔존 백슬래시 검출.
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from scripts import i18n, locale_tools  # noqa: E402


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


# 최소 CANONICAL(en) 팩 — 머지하면 6개 키 (admin 3 + cli 3).
_EN_ADMIN = (
    'admin.nav.list: "List"\n'
    'admin.locale.name.en: "English (en)"\n'
    'admin.locale.name.ko: "한국어 (ko)"\n'
)
_EN_CLI = (
    'cli.locale.ok: "{code}: OK ({total} keys)"\n'
    'cli.locale.missing: "  missing {count}: {keys}"\n'
    'cli.sample.greeting: "Hello"\n'
)


class _Base(unittest.TestCase):
    def setUp(self):
        # 격리: 임시 locales_dir + en 팩에 도구 메시지 키도 심어 i18n.t 가
        # 실 팩이 아니라 init() 된 전역(en)에서 해석되도록 한다.
        self.tmp = Path(tempfile.mkdtemp())
        _write(self.tmp / i18n.CANONICAL / 'admin.yaml', _EN_ADMIN)
        _write(self.tmp / i18n.CANONICAL / 'cli.yaml', _EN_CLI)
        # 사람 대면 메시지는 실 i18n 팩(en)으로 해석 — 전역을 en 으로 고정.
        i18n.init(i18n.CANONICAL)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        i18n.init(i18n.CANONICAL)


class CodeValidationTests(unittest.TestCase):
    def test_rejects_bad_codes(self):
        for bad in ('../x', 'a/b', '', '1bad', 'a b', './x'):
            self.assertFalse(locale_tools._is_valid_code(bad),
                             f'should reject {bad!r}')
            self.assertIsNone(locale_tools.LOCALE_CODE_RE.match(bad)
                              if isinstance(bad, str) else None)

    def test_accepts_good_codes(self):
        for good in ('ja', 'zh-Hans', 'en', 'pt-BR', 'x'):
            self.assertTrue(locale_tools._is_valid_code(good),
                            f'should accept {good!r}')


class ScaffoldTests(_Base):
    def test_scaffold_copies_and_injects_and_returns_0(self):
        logs = []
        rc = locale_tools.scaffold('ja', self.tmp, log=logs.append)
        self.assertEqual(rc, 0)

        # cli.yaml 은 정본에서 손대지 않으므로 바이트 동일하게 복사됐다.
        self.assertEqual(
            (self.tmp / 'ja' / 'cli.yaml').read_bytes(),
            (self.tmp / i18n.CANONICAL / 'cli.yaml').read_bytes())
        # admin.yaml 은 정본 내용을 그대로 포함하고 endonym 한 줄이 더 붙는다.
        ja_admin = (self.tmp / 'ja' / 'admin.yaml').read_text(encoding='utf-8')
        self.assertIn('admin.nav.list: "List"', ja_admin)
        self.assertIn('admin.locale.name.ja: "ja"', ja_admin)

        # endonym 키가 en/ja 두 팩 모두에 들어갔다 (fresh _load_pack 로 확인).
        en_pack = i18n._load_pack(i18n.CANONICAL, self.tmp)
        ja_pack = i18n._load_pack('ja', self.tmp)
        self.assertEqual(en_pack.get('admin.locale.name.ja'), 'ja')
        self.assertEqual(ja_pack.get('admin.locale.name.ja'), 'ja')
        # 새 팩이 정본과 키 패리티를 즉시 만족 (값은 영어, 키는 동일).
        self.assertEqual(set(en_pack), set(ja_pack))

    def test_second_scaffold_refuses(self):
        self.assertEqual(locale_tools.scaffold('ja', self.tmp, log=lambda _m: None), 0)
        logs = []
        rc = locale_tools.scaffold('ja', self.tmp, log=logs.append)
        self.assertEqual(rc, 1)
        self.assertTrue(any('ja' in m for m in logs))

    def test_scaffold_rejects_canonical(self):
        self.assertEqual(
            locale_tools.scaffold(i18n.CANONICAL, self.tmp, log=lambda _m: None), 1)

    def test_scaffold_rejects_bad_code(self):
        self.assertEqual(
            locale_tools.scaffold('../evil', self.tmp, log=lambda _m: None), 1)
        self.assertFalse((self.tmp / '..' / 'evil').exists())


class CheckTests(_Base):
    def _scaffold_ja(self):
        self.assertEqual(
            locale_tools.scaffold('ja', self.tmp, log=lambda _m: None), 0)

    def test_check_clean_after_scaffold_returns_0(self):
        self._scaffold_ja()
        logs = []
        rc = locale_tools.check('ja', self.tmp, log=logs.append)
        self.assertEqual(rc, 0)
        self.assertTrue(any('OK' in m for m in logs))

    def test_check_all_excludes_canonical_and_passes(self):
        self._scaffold_ja()
        # code=None → en 제외하고 ja 만 점검, 결함 없으니 0.
        self.assertEqual(locale_tools.check(None, self.tmp, log=lambda _m: None), 0)

    def test_missing_key_detected(self):
        self._scaffold_ja()
        # ja 의 cli.yaml 에서 한 키를 통째로 지운다 → 누락 발생.
        cli = self.tmp / 'ja' / 'cli.yaml'
        text = cli.read_text(encoding='utf-8')
        lines = [ln for ln in text.splitlines()
                 if not ln.startswith('cli.sample.greeting')]
        cli.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        logs = []
        rc = locale_tools.check('ja', self.tmp, log=logs.append)
        self.assertEqual(rc, 1)
        self.assertTrue(any('missing' in m and 'cli.sample.greeting' in m
                            for m in logs))

    def test_extra_key_detected(self):
        self._scaffold_ja()
        cli = self.tmp / 'ja' / 'cli.yaml'
        with cli.open('a', encoding='utf-8') as fh:
            fh.write('cli.extra.bogus: "x"\n')
        logs = []
        rc = locale_tools.check('ja', self.tmp, log=logs.append)
        self.assertEqual(rc, 1)
        self.assertTrue(any('extra' in m and 'cli.extra.bogus' in m
                            for m in logs))

    def test_stray_backslash_detected(self):
        self._scaffold_ja()
        # 큰따옴표 안 알 수 없는 escape \x 는 백슬래시째 보존 → 해석값에 잔존.
        cli = self.tmp / 'ja' / 'cli.yaml'
        text = cli.read_text(encoding='utf-8')
        text = text.replace('cli.sample.greeting: "Hello"',
                            r'cli.sample.greeting: "C:\path"')
        cli.write_text(text, encoding='utf-8')
        logs = []
        rc = locale_tools.check('ja', self.tmp, log=logs.append)
        self.assertEqual(rc, 1)
        self.assertTrue(any('stray' in m or 'backslash' in m for m in logs))

    def test_invalid_code_returns_1(self):
        self.assertEqual(
            locale_tools.check('../x', self.tmp, log=lambda _m: None), 1)


if __name__ == '__main__':
    unittest.main()

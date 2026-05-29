"""build.py CLI 인자 파싱 단위 테스트 (v0.8.2 신설 — argparse 전환).

v0.8.1 까지 build.py 는 raw `'--clean' in sys.argv` 라 오타가 경고 없이
일반 빌드로 흘러가는 silent footgun 이었다. v0.8.2 는 argparse
(allow_abbrev=False) 로 전환 — 미지/오타/약어 인자는 SystemExit(2) 로
거부하고 --help 는 SystemExit(0). 유효 인자의 의미는 v0.8.1 과 1:1
(clean / clean_cache / no_cache 세 플래그).

build.py 는 scripts 패키지가 아니라 프로젝트 루트에 있으므로
importlib 로 파일 경로에서 직접 로드한다 (모듈 레벨은 함수 정의 +
import 뿐 — `if __name__ == '__main__'` 가드라 import 만으로 빌드가
돌지 않는다).
"""
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent       # system/
PROJECT_ROOT = ROOT.parent                          # Heron.py 가 있는 폴더 (<verdir>)
sys.path.insert(0, str(ROOT))                        # Heron.py 가 의존하는 scripts/ (system/scripts)

_spec = importlib.util.spec_from_file_location('heron', PROJECT_ROOT / 'Heron.py')
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)


class ArgParserTests(unittest.TestCase):
    """_build_arg_parser() 의 파싱 동작 — 유효 인자 / 거부 / 도움말."""

    def setUp(self):
        self.parser = build._build_arg_parser()

    def test_no_args_all_false(self):
        a = self.parser.parse_args([])
        self.assertFalse(a.clean)
        self.assertFalse(a.clean_cache)
        self.assertFalse(a.no_cache)

    def test_each_flag_parses(self):
        self.assertTrue(self.parser.parse_args(['--clean']).clean)
        self.assertTrue(self.parser.parse_args(['--clean-cache']).clean_cache)
        self.assertTrue(self.parser.parse_args(['--no-cache']).no_cache)

    def test_flags_combine(self):
        a = self.parser.parse_args(['--clean', '--no-cache'])
        self.assertTrue(a.clean)
        self.assertTrue(a.no_cache)
        self.assertFalse(a.clean_cache)

    def test_unknown_arg_rejected(self):
        # v0.8.1 의 silent footgun: '--clena' 오타가 조용히 무시됐다.
        # v0.8.2 는 SystemExit(2) 로 거부.
        with self.assertRaises(SystemExit) as cm:
            self.parser.parse_args(['--clena'])
        self.assertEqual(cm.exception.code, 2)

    def test_positional_arg_rejected(self):
        with self.assertRaises(SystemExit) as cm:
            self.parser.parse_args(['clean'])
        self.assertEqual(cm.exception.code, 2)

    def test_abbrev_rejected(self):
        # allow_abbrev=False: '--clean' 의 약어로 통과하지 않는다 (오타가
        # 우연히 약어로 흡수되는 것도 차단).
        with self.assertRaises(SystemExit):
            self.parser.parse_args(['--cle'])

    def test_help_exits_zero(self):
        with self.assertRaises(SystemExit) as cm:
            self.parser.parse_args(['--help'])
        self.assertEqual(cm.exception.code, 0)


if __name__ == '__main__':
    unittest.main()

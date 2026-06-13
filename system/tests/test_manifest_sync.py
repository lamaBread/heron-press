"""릴리스 정합성 회귀 게이트 (v1.14.11 신설).

v1.14.8/9 가 코드만 커밋하고 MANIFEST 재생성·버전 참조 갱신을 건너뛰어 self-update
무결성을 깨뜨린 사건의 회귀 방어. 기존 ``python3 -m unittest discover -s
system/tests`` 게이트(RELEASE-HARNESS.md §2)에 올라타, 매니페스트가 디스크와
어긋나거나 README 버전 참조가 __version__ 과 다르면 *커밋 전* 테스트가 실패한다.

이 트리 자신(저장소 루트)을 대상으로 한다 — 합성 픽스처가 아니라 "지금 내보낼 이
릴리스가 정합한가" 를 직접 검증한다. 두 시나리오를 모두 가져야 한다:
  - 실 릴리스 직전: 통과 (clean).
  - 매니페스트 미재생성 상태: 실패 → 이 테스트가 깨진 채로는 커밋이 안 나간다.

또 check_release 의 버전-참조 판정 로직 자체를 합성 입력으로 단위 검증한다.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent       # system/
sys.path.insert(0, str(ROOT))

from scripts import check_release, make_manifest     # noqa: E402

BASE = ROOT.parent                                   # 저장소 루트


class TestShippedReleaseInSync(unittest.TestCase):
    """이 트리의 동봉 MANIFEST·버전 참조가 정합한지 (v1.14.8/9 회귀)."""

    def test_manifest_matches_disk(self):
        problems = check_release.check_manifest(BASE)
        self.assertEqual(problems, [],
                         '동봉 MANIFEST.json 이 디스크와 어긋남 — 소스 편집 후 '
                         '`python3 system/scripts/make_manifest.py` 를 빠뜨렸다:\n'
                         + '\n'.join(problems))

    def test_version_refs_match(self):
        problems = check_release.check_version_refs(BASE)
        self.assertEqual(problems, [],
                         'README 버전 참조가 __version__ 과 불일치:\n'
                         + '\n'.join(problems))

    def test_full_gate_passes(self):
        self.assertEqual(check_release.run(BASE, log=lambda *_: None), 0)


class TestCheckManifestLogic(unittest.TestCase):
    """check_manifest 가 untracked/version 케이스를 잡는지 (verify().ok 의 구멍)."""

    def _tree(self, tmp, version='9.9.9', files=None):
        tmp = Path(tmp)
        (tmp / 'system' / 'scripts').mkdir(parents=True, exist_ok=True)
        (tmp / 'system' / 'scripts' / '__init__.py').write_text(
            f"__version__ = '{version}'\n", encoding='utf-8')
        for name in ('Heron.py', 'Pond.php', 'README.md', 'README.ko.md'):
            (tmp / name).write_text(f'# {name} {version}\n', encoding='utf-8')
        for rel, body in (files or {}).items():
            p = tmp / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body, encoding='utf-8')
        return tmp

    def test_clean_tree_has_no_problems(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            base = self._tree(d)
            make_manifest.write_manifest(base)
            self.assertEqual(check_release.check_manifest(base), [])

    def test_untracked_file_flagged(self):
        """신규 파일을 추가했는데 매니페스트 미재생성 → v1.14.8 의 pagemeta.php."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            base = self._tree(d)
            make_manifest.write_manifest(base)
            (Path(base) / 'system' / 'admin' / 'views').mkdir(
                parents=True, exist_ok=True)
            (Path(base) / 'system' / 'admin' / 'views' / 'pagemeta.php').write_text(
                '<?php // new\n', encoding='utf-8')
            problems = check_release.check_manifest(base)
            self.assertTrue(any('미등록' in p for p in problems), problems)

    def test_stale_version_flagged(self):
        """__version__ 만 올리고 매니페스트 미재생성 → version 불일치."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            base = self._tree(d, version='1.0.0')
            make_manifest.write_manifest(base)
            (Path(base) / 'system' / 'scripts' / '__init__.py').write_text(
                "__version__ = '1.0.1'\n", encoding='utf-8')
            problems = check_release.check_manifest(base)
            self.assertTrue(any('version' in p for p in problems), problems)


class TestCheckVersionRefsLogic(unittest.TestCase):
    """README 파싱: 제목·푸터·changelog 굵게 판정."""

    def _readme(self, tmp, *, version, title_v=None, footer_v=None,
                top_v=None, top_bold=True):
        tmp = Path(tmp)
        (tmp / 'system' / 'scripts').mkdir(parents=True, exist_ok=True)
        (tmp / 'system' / 'scripts' / '__init__.py').write_text(
            f"__version__ = '{version}'\n", encoding='utf-8')
        title_v = title_v or version
        footer_v = footer_v or version
        top_v = top_v or version
        topcell = f'**v{top_v}**' if top_bold else f'v{top_v}'
        body = (
            f'# Heron v{title_v} — User Guide\n\n'
            '| Version | Date | Notes |\n|---|---|---|\n'
            f'| {topcell} | 2026-01-01 | top |\n'
            '| v0.9.0 | 2025-01-01 | old |\n\n'
            f'*Heron v{footer_v} — build with Python*\n')
        for name in ('README.md', 'README.ko.md'):
            (tmp / name).write_text(body, encoding='utf-8')
        return tmp

    def test_all_aligned_passes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            base = self._readme(d, version='2.0.0')
            self.assertEqual(check_release.check_version_refs(base), [])

    def test_footer_mismatch_flagged(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            base = self._readme(d, version='2.0.0', footer_v='1.9.9')
            problems = check_release.check_version_refs(base)
            self.assertTrue(any('푸터' in p for p in problems), problems)

    def test_changelog_not_bold_flagged(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            base = self._readme(d, version='2.0.0', top_bold=False)
            problems = check_release.check_version_refs(base)
            self.assertTrue(any('굵게' in p for p in problems), problems)

    def test_changelog_stale_top_flagged(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            # __version__ 이 최신인데 changelog 최상단은 옛 버전
            base = self._readme(d, version='2.0.0', title_v='2.0.0',
                                footer_v='2.0.0', top_v='1.0.0')
            problems = check_release.check_version_refs(base)
            self.assertTrue(any('changelog' in p for p in problems), problems)


if __name__ == '__main__':
    unittest.main()

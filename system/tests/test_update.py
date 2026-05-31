"""v1.6.0 신설 — 자가 업데이트 엔진 단위 테스트 (네트워크 없이).

검증:
  - select_latest_tag: semver 최대 선택, 파싱불가 태그 무시, 빈 목록.
  - _safe_rel: 프로그램 표면 경로만 허용 (user/·../·절대 거부).
  - overlay: 프로그램 파일 복사 + 사라진 파일 삭제 + user/ 불변.
  - check_update: opener 주입으로 update_available 판정 + 캐시 기록.
  - self_update: opener 주입(태그 JSON + zip 바이트)으로 다운로드→무결성검증
    →오버레이→마이그레이션→스탬프→restart 전체 흐름 (네트워크/실서버 불필요).
"""
import io
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from scripts import update, make_manifest, version  # noqa: E402


# ── 헬퍼 ──────────────────────────────────────────────────────────

def _write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _make_program_tree(root: Path, version_str: str, *, extra=None):
    """최소 프로그램 표면 트리 생성."""
    _write(root / 'Heron.py', f'# Heron entry {version_str}\n')
    _write(root / 'Pond.php', f'<?php // Pond {version_str}\n')
    _write(root / 'README.md', f'# Heron {version_str}\n')
    _write(root / 'README.ko.md', f'# Heron {version_str} (ko)\n')
    _write(root / 'system' / 'scripts' / '__init__.py',
           f"__version__ = '{version_str}'\n")
    _write(root / 'system' / 'runtime' / 'search.php', '<?php // search\n')
    for rel, body in (extra or {}).items():
        _write(root / rel, body)


def _zip_bytes(root: Path, prefix: str) -> bytes:
    """root 트리를 prefix/ 아래로 담은 zip 바이트 (GitHub zipball 모양)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(root.rglob('*')):
            if p.is_file():
                arc = prefix + '/' + p.relative_to(root).as_posix()
                zf.write(p, arc)
    return buf.getvalue()


class _Resp:
    def __init__(self, data: bytes):
        self._data = data

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeOpener:
    """tags URL → tags JSON, 그 외(zip) → zip 바이트."""
    def __init__(self, tags, zip_bytes):
        self._tags = json.dumps(tags).encode('utf-8')
        self._zip = zip_bytes
        self.calls = []

    def __call__(self, req, timeout=None):
        url = getattr(req, 'full_url', str(req))
        self.calls.append(url)
        return _Resp(self._tags if 'tags' in url else self._zip)


# ── 순수 함수 ─────────────────────────────────────────────────────

class TestSelectTag(unittest.TestCase):
    def test_picks_max_semver(self):
        tags = [{'name': 'v1.5.3'}, {'name': 'v1.6.0'},
                {'name': 'v1.4.2'}, {'name': 'nightly'}]
        self.assertEqual(update.select_latest_tag(tags)['name'], 'v1.6.0')

    def test_empty_and_unparseable(self):
        self.assertIsNone(update.select_latest_tag([]))
        self.assertIsNone(update.select_latest_tag([{'name': 'latest'}]))


class TestSafeRel(unittest.TestCase):
    def test_allows_program_paths(self):
        self.assertTrue(update._safe_rel('system/scripts/x.py'))
        self.assertTrue(update._safe_rel('Heron.py'))

    def test_rejects_user_and_traversal(self):
        self.assertFalse(update._safe_rel('user/site.yaml'))
        self.assertFalse(update._safe_rel('../evil'))
        self.assertFalse(update._safe_rel('/abs/path'))
        self.assertFalse(update._safe_rel(''))


class TestOverlay(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.src = self.tmp / 'src'
        self.dst = self.tmp / 'dst'

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_copies_program_deletes_stale_keeps_user(self):
        # 새 릴리스 (src): 새 모듈 포함, old_module 없음.
        _make_program_tree(self.src, '9.9.9',
                           extra={'system/scripts/new_module.py': '# new\n'})
        # 설치본 (dst): 구 프로그램 + old_module + user/ 콘텐츠.
        _make_program_tree(self.dst, '1.6.0',
                           extra={'system/scripts/old_module.py': '# old\n'})
        make_manifest.write_manifest(self.dst)  # old_files 기준
        _write(self.dst / 'user' / 'site.yaml', 'domain: keep.me\n')
        _write(self.dst / 'user' / 'articles' / 'A' / 'meta.yaml', 'slug: a\n')

        update.overlay(self.src, self.dst)

        # 프로그램 갱신
        self.assertIn('9.9.9',
                      (self.dst / 'Heron.py').read_text(encoding='utf-8'))
        self.assertTrue((self.dst / 'system/scripts/new_module.py').is_file())
        # 신 릴리스에서 빠진 프로그램 파일 삭제
        self.assertFalse((self.dst / 'system/scripts/old_module.py').is_file())
        # user/ 불변
        self.assertEqual(
            (self.dst / 'user' / 'site.yaml').read_text(encoding='utf-8'),
            'domain: keep.me\n')
        self.assertTrue((self.dst / 'user/articles/A/meta.yaml').is_file())


# ── 네트워크 액션 (opener 주입) ───────────────────────────────────

class TestCheckUpdateMocked(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        _make_program_tree(self.tmp, '1.6.0')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_update_available_and_cache_written(self):
        opener = _FakeOpener([{'name': 'v1.7.0',
                               'zipball_url': 'http://x/zip'}], b'')
        r = update.check_update(self.tmp, opener=opener)
        self.assertTrue(r['update_available'])
        self.assertEqual(r['latest'], 'v1.7.0')
        self.assertIsNone(r['error'])
        # 캐시 기록 확인
        cache = update.read_cache(self.tmp)
        self.assertTrue(cache['update_available'])

    def test_no_update_when_remote_older(self):
        opener = _FakeOpener([{'name': 'v1.5.3'}], b'')
        r = update.check_update(self.tmp, opener=opener)
        self.assertFalse(r['update_available'])

    def test_network_error_is_captured(self):
        def boom(req, timeout=None):
            raise OSError('no net')
        r = update.check_update(self.tmp, opener=boom)
        self.assertIsNotNone(r['error'])
        self.assertFalse(r['update_available'])


class TestSelfUpdateMocked(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.dst = self.tmp / 'site'
        self.rel = self.tmp / 'release'

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_full_flow(self):
        # 설치본 (1.6.0) — 구 스키마 site.yaml + user/ 콘텐츠.
        _make_program_tree(self.dst, '1.6.0')
        make_manifest.write_manifest(self.dst)
        _write(self.dst / 'user' / 'site.yaml',
               'domain: keep.me\nreserved_slugs: [a, b]\nname: Site\n')
        _write(self.dst / 'user' / 'articles' / 'A' / 'content.md', 'body\n')
        # 스탬프 부재 → 베이스라인. (fresh 설치 상태가 아니라 업그레이드 대상)

        # 새 릴리스 (1.7.0) — MANIFEST 동봉 후 zip.
        _make_program_tree(self.rel, '1.7.0',
                           extra={'system/scripts/feature.py': '# 1.7\n'})
        make_manifest.write_manifest(self.rel)
        zb = _zip_bytes(self.rel, 'lamaBread-heron-press-abc123')

        opener = _FakeOpener([{'name': 'v1.7.0',
                               'zipball_url': 'http://x/zipball'}], zb)
        logs = []

        # 오버레이된 가짜 릴리스의 Heron.py 는 실행 불가하므로, 새 코드의
        # 마이그레이션을 in-process 로 시뮬레이트해 주입한다 (현재 코드의
        # 마이그레이션 체인 == 1.5.3→1.6.0, 목표는 오버레이된 __version__).
        def fake_migrate(base, log):
            from scripts import migrations, make_manifest as mm
            migrations.run(base, target=mm.program_version(base), log=log)
            return True

        r = update.self_update(self.dst, opener=opener, log=logs.append,
                               migrate_fn=fake_migrate)

        self.assertTrue(r['ok'], msg='\n'.join(logs))
        self.assertTrue(r['updated'])
        self.assertTrue(r['restart'])
        self.assertEqual(r['to'], '1.7.0')
        # 프로그램 오버레이됨
        self.assertIn('1.7.0',
                      (self.dst / 'Heron.py').read_text(encoding='utf-8'))
        self.assertTrue((self.dst / 'system/scripts/feature.py').is_file())
        # 마이그레이션 적용 — 폐기 키 제거 + 스탬프 1.7.0
        sy = (self.dst / 'user' / 'site.yaml').read_text(encoding='utf-8')
        self.assertNotIn('reserved_slugs', sy)
        self.assertIn('domain: keep.me', sy)
        self.assertEqual(version.read_schema_version(self.dst), '1.7.0')
        # user/ 콘텐츠 보존
        self.assertTrue((self.dst / 'user/articles/A/content.md').is_file())
        # 백업 생성
        backups = self.dst / 'user' / '.heron' / 'backups'
        self.assertTrue(backups.is_dir() and any(backups.iterdir()))

    def test_no_update_when_current(self):
        _make_program_tree(self.dst, '1.6.0')
        make_manifest.write_manifest(self.dst)
        opener = _FakeOpener([{'name': 'v1.5.3'}], b'')
        r = update.self_update(self.dst, opener=opener, log=lambda _m: None)
        self.assertTrue(r['ok'])
        self.assertFalse(r['updated'])


if __name__ == '__main__':
    unittest.main()

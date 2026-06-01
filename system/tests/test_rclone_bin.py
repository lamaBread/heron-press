"""v1.7.0 신설 — rclone 바이너리 확보 단위 테스트 (네트워크 없이).

검증:
  - platform_key: os/arch 매핑 + 미지원 OS/arch 명확 오류.
  - binary_path: <base>/system/runtime/bin/<os>-<arch>/rclone[.exe].
  - ensure: 멱등 스킵(네트워크 0), SHA256 불일치 거부(파일 미생성),
            다운로드→검증→추출→배치 전 경로(opener 주입), PATH 폴백.
모든 다운로드는 opener 주입/모킹 — 실제 네트워크·실서버 불필요.
"""
import hashlib
import io
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from scripts import rclone_bin  # noqa: E402


class _Resp:
    def __init__(self, data: bytes):
        self._data = data

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _opener_returning(data: bytes):
    def op(req, timeout=None):
        return _Resp(data)
    return op


def _make_archive_bytes(os_key: str, arch_key: str) -> bytes:
    """``rclone-{ver}-{os}-{arch}/rclone[.exe]`` 한 개를 담은 zip 바이트."""
    want = rclone_bin.binary_name(os_key)
    arc_root = f'rclone-{rclone_bin.RCLONE_VERSION}-{os_key}-{arch_key}'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f'{arc_root}/README.txt', 'docs\n')
        zf.writestr(f'{arc_root}/{want}', b'\x00FAKE-RCLONE-BINARY')
    return buf.getvalue()


class TestPlatformKey(unittest.TestCase):
    def _key(self, system, machine):
        with mock.patch.object(rclone_bin.platform, 'system', return_value=system), \
             mock.patch.object(rclone_bin.platform, 'machine', return_value=machine):
            return rclone_bin.platform_key()

    def test_os_arch_mapping(self):
        self.assertEqual(self._key('Windows', 'AMD64'), ('windows', 'amd64'))
        self.assertEqual(self._key('Darwin', 'arm64'), ('osx', 'arm64'))   # mac=osx
        self.assertEqual(self._key('Linux', 'x86_64'), ('linux', 'amd64'))
        self.assertEqual(self._key('Linux', 'aarch64'), ('linux', 'arm64'))

    def test_unsupported_os_raises(self):
        with self.assertRaises(RuntimeError):
            self._key('FreeBSD', 'amd64')

    def test_unsupported_arch_raises(self):
        with self.assertRaises(RuntimeError):
            self._key('Linux', 'i386')

    def test_every_supported_key_has_pin(self):
        # PINS 가 6개 플랫폼을 모두 덮는다.
        for os_key in ('windows', 'osx', 'linux'):
            for arch_key in ('amd64', 'arm64'):
                self.assertIn((os_key, arch_key), rclone_bin.PINS)


class TestBinaryPath(unittest.TestCase):
    def test_path_shape(self):
        with mock.patch.object(rclone_bin.platform, 'system', return_value='Linux'), \
             mock.patch.object(rclone_bin.platform, 'machine', return_value='x86_64'):
            p = rclone_bin.binary_path('/base')
            self.assertEqual(
                p.as_posix(), '/base/system/runtime/bin/linux-amd64/rclone')

    def test_windows_exe_suffix(self):
        with mock.patch.object(rclone_bin.platform, 'system', return_value='Windows'), \
             mock.patch.object(rclone_bin.platform, 'machine', return_value='AMD64'):
            self.assertTrue(rclone_bin.binary_path('/b').name == 'rclone.exe')


class TestEnsure(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.os_key, self.arch_key = rclone_bin.platform_key()  # 실제 플랫폼

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_idempotent_skip_no_network(self):
        # 바이너리가 이미 있고 버전이 맞으면 opener 를 절대 안 부른다.
        dst = rclone_bin.binary_path(self.tmp)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(b'\x00existing')

        def boom(req, timeout=None):
            raise AssertionError('네트워크를 타면 안 됨 (멱등 스킵)')

        with mock.patch.object(rclone_bin, 'installed_version',
                               return_value=rclone_bin.RCLONE_VERSION):
            out = rclone_bin.ensure(self.tmp, opener=boom)
        self.assertEqual(out, dst)

    def test_sha_mismatch_rejected_no_file(self):
        # 핀과 안 맞는 바이트 → 거부, 최종 경로에 파일 미생성, 폴백도 안 함.
        opener = _opener_returning(b'totally-wrong-bytes')
        with mock.patch.object(rclone_bin, 'installed_version', return_value=None):
            with self.assertRaises(RuntimeError) as cm:
                rclone_bin.ensure(self.tmp, opener=opener,
                                  allow_path_fallback=True)
        self.assertIn('SHA256', str(cm.exception))
        self.assertFalse(rclone_bin.binary_path(self.tmp).exists())

    def test_full_download_extract_place(self):
        # 가짜 zip 을 만들고 그 sha 를 현재 플랫폼 핀으로 임시 치환 → 전 경로.
        data = _make_archive_bytes(self.os_key, self.arch_key)
        sha = hashlib.sha256(data).hexdigest()
        patched = dict(rclone_bin.PINS)
        patched[(self.os_key, self.arch_key)] = sha
        opener = _opener_returning(data)
        with mock.patch.object(rclone_bin, 'PINS', patched), \
             mock.patch.object(rclone_bin, 'installed_version',
                               return_value=rclone_bin.RCLONE_VERSION):
            out = rclone_bin.ensure(self.tmp, opener=opener)
        self.assertEqual(out, rclone_bin.binary_path(self.tmp))
        self.assertTrue(out.is_file())
        self.assertEqual(out.read_bytes(), b'\x00FAKE-RCLONE-BINARY')
        # 반쪽 임시파일이 남지 않는다.
        self.assertFalse((out.parent / (out.name + '.heron_tmp')).exists())

    def test_network_failure_falls_back_to_path(self):
        def neterr(req, timeout=None):
            raise OSError('offline')
        with mock.patch.object(rclone_bin.shutil, 'which',
                               return_value='/usr/bin/rclone'), \
             mock.patch.object(rclone_bin, 'installed_version',
                               return_value='v0.0.0'):
            out = rclone_bin.ensure(self.tmp, opener=neterr,
                                    allow_path_fallback=True)
        self.assertEqual(Path(out), Path('/usr/bin/rclone'))

    def test_network_failure_no_fallback_raises(self):
        def neterr(req, timeout=None):
            raise OSError('offline')
        with mock.patch.object(rclone_bin.shutil, 'which', return_value=None):
            with self.assertRaises(RuntimeError):
                rclone_bin.ensure(self.tmp, opener=neterr,
                                  allow_path_fallback=True)


if __name__ == '__main__':
    unittest.main()

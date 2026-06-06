"""v1.7.0 신설 — 배포 오케스트레이션 단위 테스트 (네트워크·실서버 없이).

검증:
  - load_config: 필수키/형식/포트 검증, 키·known_hosts 파일 존재, 명확 오류.
  - build_argv: sync 인자 조립(dry-run 토글, key-file/known-hosts 포함),
                shell 미경유(리스트), known_hosts 기본값 전개.
  - write_example: 멱등 시드(없을 때만 생성), 견본 JSON 유효성.
  - run: ensure→load_config→build_argv→subprocess 배선 + 스트리밍 + exit code
         (subprocess/ensure/load_config 모킹).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from scripts import deploy  # noqa: E402
from scripts import rclone_bin  # noqa: E402


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        # 진짜 키/known_hosts 파일 (존재 검사 통과용).
        self.key = self.tmp / 'keys' / 'id_ed25519'
        self.kh = self.tmp / 'keys' / 'known_hosts'
        _write(self.key, 'PRIVATE KEY\n')
        _write(self.kh, 'host ssh-ed25519 AAAA...\n')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_cfg(self, **over):
        cfg = {
            'host': 'example.com', 'user': 'deploy', 'port': 2222,
            'remote_path': '/var/www/site',
            'ssh_key_path': str(self.key),
            'known_hosts_path': str(self.kh),
        }
        cfg.update(over)
        _write(deploy.config_path(self.tmp), json.dumps(cfg))
        return cfg


class TestLoadConfig(_Base):
    def test_valid(self):
        self._write_cfg()
        cfg = deploy.load_config(self.tmp)
        self.assertEqual(cfg['host'], 'example.com')
        self.assertEqual(cfg['port'], 2222)
        self.assertEqual(cfg['ssh_key_path'], os.path.expanduser(str(self.key)))
        self.assertEqual(cfg['_known_hosts'], str(self.kh))

    def test_missing_file(self):
        with self.assertRaises(deploy.DeployConfigError):
            deploy.load_config(self.tmp)

    def test_bad_json(self):
        _write(deploy.config_path(self.tmp), '{ not json')
        with self.assertRaises(deploy.DeployConfigError):
            deploy.load_config(self.tmp)

    def test_missing_required_key(self):
        self._write_cfg(host='')
        with self.assertRaises(deploy.DeployConfigError) as cm:
            deploy.load_config(self.tmp)
        self.assertIn('host', str(cm.exception))

    def test_default_port_22(self):
        cfg = self._write_cfg()
        del cfg['port']
        _write(deploy.config_path(self.tmp), json.dumps(cfg))
        self.assertEqual(deploy.load_config(self.tmp)['port'], 22)

    def test_noninteger_port(self):
        self._write_cfg(port='abc')
        with self.assertRaises(deploy.DeployConfigError):
            deploy.load_config(self.tmp)

    def test_missing_key_file(self):
        self._write_cfg(ssh_key_path=str(self.tmp / 'nope' / 'id'))
        with self.assertRaises(deploy.DeployConfigError) as cm:
            deploy.load_config(self.tmp)
        self.assertIn('private key', str(cm.exception))   # v1.9.7: 기본값 en

    def test_missing_known_hosts(self):
        self._write_cfg(known_hosts_path=str(self.tmp / 'nope' / 'known_hosts'))
        with self.assertRaises(deploy.DeployConfigError) as cm:
            deploy.load_config(self.tmp)
        self.assertIn('known_hosts', str(cm.exception))

    # ── ssh_alias 위임 모드 (v1.11.4) ─────────────────────────────
    def test_alias_mode_skips_key_and_known_hosts_checks(self):
        # 키·known_hosts 파일이 없어도 alias 모드는 통과 — 그 경로를 안 쓴다.
        _write(deploy.config_path(self.tmp), json.dumps({
            'remote_path': '/var/www/site', 'ssh_alias': 'lama'}))
        cfg = deploy.load_config(self.tmp)
        self.assertEqual(cfg['ssh_alias'], 'lama')
        self.assertEqual(cfg['remote_path'], '/var/www/site')

    def test_alias_mode_requires_only_remote_path(self):
        _write(deploy.config_path(self.tmp), json.dumps({'ssh_alias': 'lama'}))
        with self.assertRaises(deploy.DeployConfigError) as cm:
            deploy.load_config(self.tmp)
        self.assertIn('remote_path', str(cm.exception))

    def test_alias_bad_chars_rejected(self):
        _write(deploy.config_path(self.tmp), json.dumps({
            'remote_path': '/var/www/site', 'ssh_alias': 'bad alias;rm'}))
        with self.assertRaises(deploy.DeployConfigError) as cm:
            deploy.load_config(self.tmp)
        self.assertIn('ssh_alias', str(cm.exception))   # v1.9.7: 기본값 en


class TestBuildArgv(_Base):
    def _cfg(self, **over):
        cfg = {
            'host': 'example.com', 'user': 'deploy', 'port': 2222,
            'remote_path': '/var/www/site',
            'ssh_key_path': str(self.key),
            'known_hosts_path': str(self.kh),
        }
        cfg.update(over)
        return cfg

    def test_shape_and_flags(self):
        argv = deploy.build_argv('/bin/rclone', self.tmp, self._cfg(), False)
        self.assertIsInstance(argv, list)              # shell 미경유
        self.assertEqual(argv[:2], ['/bin/rclone', 'sync'])
        self.assertEqual(argv[2], str(Path(self.tmp) / 'dist'))
        self.assertEqual(argv[3], ':sftp:/var/www/site')
        # 백엔드 플래그가 값과 짝지어 들어간다.
        for flag, val in [('--sftp-host', 'example.com'),
                          ('--sftp-user', 'deploy'),
                          ('--sftp-port', '2222'),
                          ('--sftp-key-file', str(self.key)),
                          ('--sftp-known-hosts-file', str(self.kh))]:
            self.assertIn(flag, argv)
            self.assertEqual(argv[argv.index(flag) + 1], val)
        self.assertNotIn('--dry-run', argv)

    def test_dry_run_toggle(self):
        argv = deploy.build_argv('/bin/rclone', self.tmp, self._cfg(), True)
        self.assertEqual(argv[-1], '--dry-run')

    def test_known_hosts_default_expanded(self):
        cfg = self._cfg()
        del cfg['known_hosts_path']
        argv = deploy.build_argv('/bin/rclone', self.tmp, cfg, False)
        kh = argv[argv.index('--sftp-known-hosts-file') + 1]
        self.assertTrue(kh.endswith(os.path.join('.ssh', 'known_hosts')))
        self.assertNotIn('~', kh)                      # 전개됨 (구분자 무관)

    # ── ssh_alias 위임 모드 (v1.11.4) ─────────────────────────────
    def test_alias_mode_uses_sftp_ssh(self):
        cfg = {'remote_path': '/var/www/site', 'ssh_alias': 'lama'}
        argv = deploy.build_argv('/bin/rclone', self.tmp, cfg, False)
        self.assertEqual(argv[:4], ['/bin/rclone', 'sync',
                                    str(Path(self.tmp) / 'dist'),
                                    ':sftp:/var/www/site'])
        self.assertIn('--sftp-ssh', argv)
        # rclone 이 공백으로 쪼개 ['ssh','lama'] 로 쓰는 두 토큰.
        self.assertEqual(argv[argv.index('--sftp-ssh') + 1], 'ssh lama')
        self.assertIn('--sftp-disable-hashcheck', argv)
        # 키파일 모드 플래그는 전부 빠진다.
        for flag in ('--sftp-host', '--sftp-user', '--sftp-port',
                     '--sftp-key-file', '--sftp-known-hosts-file'):
            self.assertNotIn(flag, argv)
        self.assertIn('--log-level', argv)             # 공통 꼬리 유지
        self.assertNotIn('--dry-run', argv)

    def test_alias_mode_dry_run_toggle(self):
        cfg = {'remote_path': '/var/www/site', 'ssh_alias': 'lama'}
        argv = deploy.build_argv('/bin/rclone', self.tmp, cfg, True)
        self.assertEqual(argv[-1], '--dry-run')


def _find_rclone() -> str:
    """배포에 실제로 쓰이는 rclone 실행파일 경로를 찾는다 (없으면 '').

    우선순위: 핀 버전이 받아져 있으면 그것(``system/runtime/bin/<os>-<arch>/``),
    아니면 PATH 의 rclone. 둘 다 없으면 '' — 호출부가 skip 한다.
    """
    base = Path(__file__).resolve().parents[2]   # heron-press/
    try:
        pinned = rclone_bin.binary_path(base)
    except RuntimeError:                          # 미지원 OS/arch
        pinned = None
    if pinned is not None and pinned.is_file():
        return str(pinned)
    return shutil.which('rclone') or shutil.which('rclone.exe') or ''


def _rclone_long_flags(rclone: str) -> set:
    """``rclone help flags`` 가 보고하는 모든 ``--long-flag`` 이름 집합."""
    out = subprocess.run([rclone, 'help', 'flags'], capture_output=True,
                         text=True, encoding='utf-8', errors='replace',
                         timeout=30)
    return set(re.findall(r'--[A-Za-z0-9][A-Za-z0-9-]*', out.stdout or ''))


class TestArgvFlagsAgainstRealRclone(_Base):
    """회귀 가드 (v1.10.0): build_argv 가 내보내는 모든 ``--flag`` 가 실제
    rclone 바이너리에 존재하는지 대조한다.

    단위 테스트는 build_argv 가 만든 *리스트 형태* 만 검증해, 코드와 테스트가
    같은 오타를 공유하면(예 v1.9.x 의 ``--sftp-known-hosts``) 자기일관적으로
    통과한다 — "코드가 만든 문자열"과 "rclone 이 받아들이는 플래그 표면"의
    불일치는 못 잡는다. 이 테스트가 그 틈을 닫는다. 바이너리가 없으면(다운로드
    전·미지원 플랫폼·CI) skip — 가용한 머신에선 진짜 게이트로 동작한다.
    """
    def test_every_emitted_flag_exists_in_rclone(self):
        rclone = _find_rclone()
        if not rclone:
            self.skipTest('rclone 바이너리 없음 (미다운로드/미지원 플랫폼)')
        known = _rclone_long_flags(rclone)
        self.assertIn('--sftp-host', known,    # 파싱 sanity (표면 비었으면 무의미)
                      'rclone help flags 파싱 실패 — 플래그 표면이 비었다')
        argv = deploy.build_argv(rclone, self.tmp, self._write_cfg(), True)
        emitted = [a for a in argv if a.startswith('--')]
        unknown = [f for f in emitted if f not in known]
        self.assertEqual(unknown, [],
                         f'rclone 가 모르는 플래그: {unknown}')

    def test_alias_emitted_flags_exist_in_rclone(self):
        # v1.11.4: alias 모드가 내보내는 --sftp-ssh·--sftp-disable-hashcheck 가
        # 실제 rclone 바이너리에 존재하는지 (키파일 모드와 같은 회귀 가드).
        rclone = _find_rclone()
        if not rclone:
            self.skipTest('rclone 바이너리 없음 (미다운로드/미지원 플랫폼)')
        known = _rclone_long_flags(rclone)
        self.assertIn('--sftp-host', known,
                      'rclone help flags 파싱 실패 — 플래그 표면이 비었다')
        cfg = {'remote_path': '/var/www/site', 'ssh_alias': 'lama'}
        argv = deploy.build_argv(rclone, self.tmp, cfg, True)
        emitted = [a for a in argv if a.startswith('--')]
        unknown = [f for f in emitted if f not in known]
        self.assertEqual(unknown, [],
                         f'rclone 가 모르는 플래그: {unknown}')


class TestExample(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_example_text_is_valid_json_with_required_keys(self):
        data = json.loads(deploy.example_text())
        for k in deploy.REQUIRED_KEYS:
            self.assertIn(k, data)

    def test_write_example_idempotent(self):
        self.assertTrue(deploy.write_example(self.tmp))     # 첫 호출 = 생성
        p = deploy.example_path(self.tmp)
        self.assertTrue(p.is_file())
        self.assertEqual(p.read_text(encoding='utf-8'), deploy.example_text())
        self.assertFalse(deploy.write_example(self.tmp))    # 둘째 = no-op


class _FakePopen:
    """run() 의 스트리밍 루프를 검증할 가짜 Popen — 줄을 흘리고 코드를 반환."""
    def __init__(self, lines, code):
        self.stdout = iter(lines)
        self.returncode = None
        self._code = code

    def wait(self):
        self.returncode = self._code


class TestRun(_Base):
    def test_run_streams_and_returns_code(self):
        self._write_cfg()
        lines = ['Transferred: 1 / 1\n', 'Deleted: 0\n']
        captured = []

        with mock.patch.object(deploy.rclone_bin, 'ensure',
                               return_value='/bin/rclone'), \
             mock.patch.object(deploy.subprocess, 'Popen',
                               return_value=_FakePopen(lines, 0)), \
             mock.patch.object(deploy.sys, 'stdout') as out:
            out.write.side_effect = lambda s: captured.append(s)
            code = deploy.run(self.tmp, dry_run=True, log=lambda _m: None)

        self.assertEqual(code, 0)
        self.assertIn('Transferred: 1 / 1\n', captured)

    def test_run_propagates_nonzero(self):
        self._write_cfg()
        with mock.patch.object(deploy.rclone_bin, 'ensure',
                               return_value='/bin/rclone'), \
             mock.patch.object(deploy.subprocess, 'Popen',
                               return_value=_FakePopen([], 5)), \
             mock.patch.object(deploy.sys, 'stdout'):
            code = deploy.run(self.tmp, dry_run=False, log=lambda _m: None)
        self.assertEqual(code, 5)

    def test_run_alias_minimal_config_no_keyerror(self):
        # v1.11.4: alias 최소 설정(host/user/key 없음)도 run() 이 sync_line
        # 로깅에서 KeyError 없이 동작 — load_config 통과 후 죽지 않는다.
        _write(deploy.config_path(self.tmp), json.dumps({
            'remote_path': '/var/www/site', 'ssh_alias': 'lama'}))
        with mock.patch.object(deploy.rclone_bin, 'ensure',
                               return_value='/bin/rclone'), \
             mock.patch.object(deploy.subprocess, 'Popen',
                               return_value=_FakePopen([], 0)), \
             mock.patch.object(deploy.sys, 'stdout'):
            code = deploy.run(self.tmp, dry_run=True, log=lambda _m: None)
        self.assertEqual(code, 0)


if __name__ == '__main__':
    unittest.main()

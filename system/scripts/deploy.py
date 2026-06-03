"""dist 서버 배포 오케스트레이션 (v1.7.0 신설).

빌드된 ``dist/`` 를 rclone 의 SFTP 백엔드로 원격 서버에 **증분 동기화**한다
(서버에만 남은 고아 파일 삭제 포함). PHP(Pond)는 얇은 트리거일 뿐, 다운로드·
검증·설정·동기화 로직은 전부 여기에 산다 (Heron.py / 빌더와 같은 단일 진실원).

흐름:
  ensure() (rclone_bin) → load_config() → build_argv() → subprocess(스트리밍).

안전장치:
  - 인증은 **SSH 키파일**(개인키는 저장소 밖 OS 표준 위치, deploy.json 엔 경로만).
  - 호스트키 검증을 강제(``--sftp-known-hosts-file``) — rclone sftp 기본(미검증)은 MITM
    에 취약. 최초 접속은 사용자가 ``ssh user@host`` 1회로 known_hosts 에 등록.
  - argv 리스트 + subprocess(shell 미경유)로 셸 인젝션 차단.
  - ``sync`` 는 원격을 *삭제*하므로 Pond UI 가 2단계(미리보기 dry-run → 적용)
    게이트를 강제한다. 이 모듈은 ``dry_run`` 플래그만 노출.

설정 파일(``user/.heron/deploy.json``)은 gitignore + ``.`` 접두라 빌드/커밋/
dist 어디에도 새지 않는다. 견본(``deploy.example.json``)은 커밋되며, 기존
사용자에겐 ``m_1_7_0`` 마이그레이션이 시드한다 (오버레이는 user/ 미접촉이라).
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, List, Optional

from . import rclone_bin
from . import version as _version
from . import i18n

CONFIG_NAME = 'deploy.json'
EXAMPLE_NAME = 'deploy.example.json'

REQUIRED_KEYS = ('host', 'user', 'remote_path', 'ssh_key_path')

# 견본 — 단일 출처. 커밋되는 deploy.example.json 과 m_1_7_0 시드가 모두 이걸 쓴다.
EXAMPLE_CONFIG = {
    'host': 'your-domain.com',
    'user': 'deployuser',
    'port': 22,
    'remote_path': '/var/www/your-domain.com',
    'ssh_key_path': 'C:/Users/you/.ssh/id_ed25519',
    'known_hosts_path': 'C:/Users/you/.ssh/known_hosts',
}


class DeployConfigError(Exception):
    """deploy.json 부재/형식오류/필수키 누락 — 사람이 읽을 메시지를 담는다."""


# ── 경로 ──────────────────────────────────────────────────────────

def config_path(base) -> Path:
    return _version.heron_dir(base) / CONFIG_NAME


def example_path(base) -> Path:
    return _version.heron_dir(base) / EXAMPLE_NAME


def example_text() -> str:
    """견본 JSON 텍스트 (결정적, 끝 개행 1개)."""
    return json.dumps(EXAMPLE_CONFIG, ensure_ascii=False, indent=2) + '\n'


def write_example(base) -> bool:
    """``user/.heron/deploy.example.json`` 을 *없을 때만* 생성. 만들었으면 True.

    멱등 — 이미 있으면 건드리지 않는다 (m_1_7_0 시드가 이걸 호출).
    """
    p = example_path(base)
    if p.exists():
        return False
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix('.json.heron_tmp')
    tmp.write_text(example_text(), encoding='utf-8')
    tmp.replace(p)
    return True


# ── 설정 ──────────────────────────────────────────────────────────

def known_hosts_path(cfg: dict) -> str:
    """known_hosts 절대경로. 생략 시 ``~/.ssh/known_hosts`` 로 전개.

    rclone 은 ``~`` 를 스스로 안 펴므로 Python 에서 expanduser 로 절대경로화.
    """
    raw = (cfg.get('known_hosts_path') or '').strip()
    if not raw:
        raw = os.path.join('~', '.ssh', 'known_hosts')
    return os.path.expanduser(raw)


def load_config(base) -> dict:
    """``user/.heron/deploy.json`` 읽기·검증. 실패 시 DeployConfigError.

    필수키(host/user/remote_path/ssh_key_path) 검증, port 기본 22, ssh_key_path
    및 known_hosts 파일 존재 확인. 오류엔 deploy.example.json 안내를 포함한다.
    """
    p = config_path(base)
    if not p.is_file():
        raise DeployConfigError(i18n.t(
            'cli.deploy.cfg.absent',
            path=p.as_posix(), example=example_path(base).as_posix()))
    try:
        cfg = json.loads(p.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as e:
        raise DeployConfigError(i18n.t('cli.deploy.cfg.unreadable', error=e))
    if not isinstance(cfg, dict):
        raise DeployConfigError(i18n.t('cli.deploy.cfg.not_object'))

    missing = [k for k in REQUIRED_KEYS
               if not str(cfg.get(k, '')).strip()]
    if missing:
        raise DeployConfigError(i18n.t(
            'cli.deploy.cfg.missing_keys',
            keys=', '.join(missing), example=example_path(base).as_posix()))

    # 포트 정규화 (기본 22).
    port = cfg.get('port', 22)
    try:
        cfg['port'] = int(port)
    except (TypeError, ValueError):
        raise DeployConfigError(i18n.t('cli.deploy.cfg.port_not_int',
                                       port=repr(port)))

    key = os.path.expanduser(str(cfg['ssh_key_path']).strip())
    if not os.path.isfile(key):
        raise DeployConfigError(i18n.t('cli.deploy.cfg.key_not_found',
                                       path=key))
    cfg['ssh_key_path'] = key

    kh = known_hosts_path(cfg)
    if not os.path.isfile(kh):
        raise DeployConfigError(i18n.t('cli.deploy.cfg.known_hosts_missing',
                                       path=kh))
    cfg['_known_hosts'] = kh
    return cfg


# ── argv 조립 ─────────────────────────────────────────────────────

def build_argv(rclone, base, cfg: dict, dry_run: bool) -> List[str]:
    """``rclone sync <base>/dist :sftp:<remote>`` argv (shell 미경유 리스트).

    글로벌 SFTP 백엔드 플래그 + ``:sftp:`` 온더플라이 리모트 — 연결문자열
    이스케이프를 피하고 모든 좌표를 플래그로 명시한다.
    """
    src = str(Path(base) / 'dist')
    argv = [
        str(rclone), 'sync', src, f":sftp:{cfg['remote_path']}",
        '--sftp-host', str(cfg['host']),
        '--sftp-user', str(cfg['user']),
        '--sftp-port', str(cfg.get('port', 22)),
        '--sftp-key-file', str(cfg['ssh_key_path']),
        '--sftp-known-hosts-file', known_hosts_path(cfg),
        '--stats-one-line', '--stats', '1s',
        '--log-level', 'INFO',
    ]
    if dry_run:
        argv.append('--dry-run')
    return argv


# ── 실행 (스트리밍) ───────────────────────────────────────────────

def run(base, dry_run: bool, *,
        log: Optional[Callable[[str], None]] = None,
        opener: Optional[Callable] = None) -> int:
    """ensure → load_config → build_argv → subprocess. 출력은 **실시간 스트리밍**.

    rclone stdout/stderr 를 줄 단위로 즉시 흘려보낸다 (Pond 가 그 파이프를
    브라우저로 패스스루 → 첫 대용량 전송도 진행이 보임). 반환: rclone exit code.
    설정 오류는 DeployConfigError 로 호출부(Heron.py)가 메시지를 표면화한다.
    """
    log = log or (lambda _m: print(_m, flush=True))
    base = Path(base)

    rclone = rclone_bin.ensure(base, opener=opener, log=log)
    cfg = load_config(base)
    argv = build_argv(rclone, base, cfg, dry_run)

    mode = (i18n.t('cli.deploy.mode.preview') if dry_run
            else i18n.t('cli.deploy.mode.apply'))
    log(i18n.t('cli.deploy.sync_line', user=cfg['user'], host=cfg['host'],
               remote=cfg['remote_path'], mode=mode))

    proc = subprocess.Popen(
        argv, cwd=str(base),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding='utf-8', errors='replace', bufsize=1)
    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
    proc.wait()
    code = proc.returncode
    if code == 0:
        log(i18n.t('cli.deploy.preview_done') if dry_run
            else i18n.t('cli.deploy.done'))
    else:
        log(i18n.t('cli.deploy.rclone_exit', code=code))
    return code

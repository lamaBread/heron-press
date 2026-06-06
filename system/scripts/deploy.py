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
import difflib
import json
import os
import re
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

# ssh_alias 위임 모드(v1.11.4): 선택 필드 ``ssh_alias`` 가 있으면 전송을 시스템
# ssh 에 위임(``--sftp-ssh "ssh <alias>"``)하므로 host/user/key·known_hosts 가
# 전부 ~/.ssh/config 에서 온다 → remote_path 만 필수. 별칭은 argv 한 토큰(공백
# 분리로 ['ssh','<alias>'])이라 공백·셸 메타문자를 차단해 단일 토큰만 허용한다.
REQUIRED_KEYS_ALIAS = ('remote_path',)
_ALIAS_RE = re.compile(r'^[A-Za-z0-9._-]+$')

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

    두 모드. (1) 키파일 모드(기본): 필수키(host/user/remote_path/ssh_key_path)
    검증, port 기본 22, ssh_key_path·known_hosts 파일 존재 확인. (2) ssh_alias
    위임 모드(v1.11.4): ``ssh_alias`` 가 있으면 전송을 시스템 ssh 에 위임하므로
    remote_path 만 필수이고 키·known_hosts 파일 검사는 건너뛴다(그 경로를 안 쓴다).
    오류엔 deploy.example.json 안내를 포함한다.
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

    # ssh_alias 위임 모드 판정 — 별칭 형식부터 검증(공백·셸 메타문자 차단).
    alias = str(cfg.get('ssh_alias', '')).strip()
    if alias and not _ALIAS_RE.match(alias):
        raise DeployConfigError(i18n.t('cli.deploy.cfg.bad_alias', alias=alias))

    required = REQUIRED_KEYS_ALIAS if alias else REQUIRED_KEYS
    missing = [k for k in required
               if not str(cfg.get(k, '')).strip()]
    if missing:
        raise DeployConfigError(i18n.t(
            'cli.deploy.cfg.missing_keys',
            keys=', '.join(missing), example=example_path(base).as_posix()))

    # 포트 정규화 (기본 22). 별칭 모드에선 미사용이지만 무해 — 형식만 정상화.
    port = cfg.get('port', 22)
    try:
        cfg['port'] = int(port)
    except (TypeError, ValueError):
        raise DeployConfigError(i18n.t('cli.deploy.cfg.port_not_int',
                                       port=repr(port)))

    if alias:
        # 위임 모드: 인증·검증을 ~/.ssh/config(별칭)·Keychain·agent·known_hosts 가
        # 처리하므로 키/known_hosts 파일 존재 검사를 건너뛰고 조기 반환.
        cfg['ssh_alias'] = alias
        return cfg

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

def _connection_flags(cfg: dict) -> List[str]:
    """SFTP 연결 좌표 플래그(sync·cat 공용). 두 모드 동일 적용.

    ``ssh_alias`` 가 있으면(v1.11.4) 전송을 시스템 ssh 에 위임
    (``--sftp-ssh "ssh <alias>"``)하므로 host/user/port/key/known_hosts 플래그를
    전부 버리고, 파일별 ``md5sum``(=ssh 연결 폭주)을 막는
    ``--sftp-disable-hashcheck`` 만 둔다. ``--sftp-ssh`` 값은 rclone 이 공백으로
    쪼개 argv 로 쓰므로 ``"ssh <alias>"`` 두 토큰이며 alias 는 공백 없는 단일 토큰
    (load_config 가 보장). 아니면 글로벌 SFTP 백엔드 플래그로 모든 좌표를 명시.
    """
    alias = str(cfg.get('ssh_alias', '')).strip()
    if alias:
        return ['--sftp-ssh', f'ssh {alias}', '--sftp-disable-hashcheck']
    return [
        '--sftp-host', str(cfg['host']),
        '--sftp-user', str(cfg['user']),
        '--sftp-port', str(cfg.get('port', 22)),
        '--sftp-key-file', str(cfg['ssh_key_path']),
        '--sftp-known-hosts-file', known_hosts_path(cfg),
    ]


def build_argv(rclone, base, cfg: dict, dry_run: bool) -> List[str]:
    """``rclone sync <base>/dist :sftp:<remote>`` argv (shell 미경유 리스트).

    연결 좌표는 _connection_flags 가 모드별(별칭/키파일)로 조립한다. 여기서는
    sync 전용 옵션(통계 한 줄·로그 레벨·dry-run)만 덧붙인다.
    """
    src = str(Path(base) / 'dist')
    remote = f":sftp:{cfg['remote_path']}"
    argv = [str(rclone), 'sync', src, remote] + _connection_flags(cfg)
    argv += ['--stats-one-line', '--stats', '1s', '--log-level', 'INFO']
    if dry_run:
        argv.append('--dry-run')
    return argv


# ── dry-run 요약 파싱 ─────────────────────────────────────────────
#
# rclone 는 dry-run 에서 객체마다 NOTICE 한 줄(``Skipped …``)을 뱉어 수백 줄이
# 된다 — deploy_run.php 의 <pre> 로그가 그래서 장황하다. 그 줄들을 스트리밍하며
# 집계해(업로드/삭제 건수·용량, 디렉터리 작업, 경고, 상위 디렉터리별 내역) 사람용
# 요약을 **항상** 출력하고, 환경변수 ``HERON_DEPLOY_SUMMARY=json`` 일 때만 기계가
# 읽을 한 줄(JSON)을 sentinel 접두로 덧붙인다 — Pond(admin)가 이를 가로채 카드·
# 표로 시각화한다(CLI 출력엔 안 보인다). 파싱은 여기 단일 출처라 test_deploy 로
# 단위 검증한다.

# rclone 한 줄 형식(--log-level INFO): "YYYY/MM/DD HH:MM:SS LEVEL : <body>".
_RC_LINE = re.compile(
    r'^\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\s+(?P<lvl>\w+)\s*:\s*(?P<body>.*)$')
# 파일 액션: "<obj>: Skipped copy|update|delete as --dry-run is set (size <X>)".
_RC_FILE = re.compile(
    r'^(?P<obj>.*): Skipped (?P<act>copy|update|delete) as --dry-run is set '
    r'\(size (?P<size>[^)]*)\)$')
# 디렉터리 액션(용량 없음): make/remove directory, set directory modification time.
_RC_DIR = re.compile(
    r'^(?P<obj>.*): Skipped (?P<act>set directory modification time|'
    r'make directory|remove directory) as --dry-run is set$')
# 사이즈 토큰: "59", "13.733Ki", "5.089Mi" (rclone 의 IEC 이진 단위).
_SIZE_RE = re.compile(r'^([\d.]+)\s*([KMGTP]i)?B?$')
_SIZE_MULT = {None: 1, 'Ki': 1024, 'Mi': 1024 ** 2,
              'Gi': 1024 ** 3, 'Ti': 1024 ** 4, 'Pi': 1024 ** 5}

# dist 에 섞여 배포되면 안 되는 OS 잡파일 — 업로드 대상에 잡히면 경고로 띄운다.
_JUNK_BASENAMES = {'.DS_Store', 'Thumbs.db', 'desktop.ini', '.localized'}

_WARN_CAP = 12          # 경고 줄 수집 상한 (중복 제외).
_BY_DIR_CAP = 30        # 상위 디렉터리별 표 행 상한 (나머지는 '그 외'로 롤업).
_FILE_CAP = 500         # 추가/수정/삭제 파일별 목록 상한 (나머지는 '+N개 더'로 롤업).

# 파일별 diff(미리보기→클릭 시 그 파일만 서버에서 cat)의 한계. 대용량은 네트워크·
# 메모리·DOM 폭주를 막으려 받지 않고 'too_large'로 끊는다.
_DIFF_CAP = 512 * 1024  # 한쪽이라도 이보다 크면 diff 생략(원격 DoS·메모리 방어).
_DIFF_CONTEXT = 3       # unified hunk 앞뒤 맥락 줄 수.
_DIFF_MAX_LINES = 4000  # hunk 줄 총합 상한(초과 시 truncated). JSON/DOM 폭증 방지.
_LINE_CLIP = 2000       # 한 줄 표시 최대 글자(초과분 절단).

# admin(PHP)이 스트림에서 가로채는 기계용 요약 한 줄의 접두 sentinel. 제어문자
# (RS)라 rclone/Heron 의 어떤 정상 출력과도 충돌하지 않는다.
SUMMARY_SENTINEL = '\x1eHERON_DEPLOY_SUMMARY\x1e'


def parse_size(token: str) -> int:
    """rclone 휴먼 사이즈(``13.733Ki``/``59``)를 바이트(int)로. 실패 시 0."""
    m = _SIZE_RE.match(token.strip())
    if not m:
        return 0
    return int(float(m.group(1)) * _SIZE_MULT[m.group(2)])


def human_size(n: int) -> str:
    """바이트를 사람용 IEC 문자열로 (``86.4 MiB``). 1KiB 미만은 ``N B``."""
    n = int(n)
    units = ('B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB')
    f = float(n)
    i = 0
    while f >= 1024 and i < len(units) - 1:
        f /= 1024
        i += 1
    return f'{n} B' if i == 0 else f'{f:.1f} {units[i]}'


def _top_dir(obj: str) -> str:
    """객체 경로의 최상위 디렉터리. 루트 직속 파일은 '' (표시는 PHP 가 '(루트)')."""
    return obj.split('/', 1)[0] if '/' in obj else ''


class DryRunSummary:
    """dry-run rclone 출력을 줄 단위로 먹으며 집계하는 누산기."""

    def __init__(self, remote_path: str = ''):
        self.remote_path = remote_path
        self.upload_count = 0       # copy+update 합산 — 하위호환(기존 'upload' 키).
        self.upload_bytes = 0
        self.added_count = 0        # copy(신규) — 'added'.
        self.added_bytes = 0
        self.modified_count = 0     # update(변경) — 'modified'.
        self.modified_bytes = 0
        self.delete_count = 0
        self.delete_bytes = 0
        self.dirs = {'make': 0, 'remove': 0, 'touch': 0}
        self.warnings: List[str] = []
        self.junk: List[str] = []
        # 파일별 목록(경로+bytes) — 각 _FILE_CAP 까지만 보관, 초과분은 총계로 롤업.
        self.added_files: List[dict] = []
        self.modified_files: List[dict] = []
        self.deleted_files: List[dict] = []
        self._by_dir = {}   # top-level dir -> [count, bytes]

    def feed(self, line: str) -> None:
        m = _RC_LINE.match(line)
        if not m:                       # Heron 자체 줄 등 — 집계 대상 아님.
            return
        lvl, body = m.group('lvl'), m.group('body')
        if body.startswith(('Transferred:', 'Checks:', 'Elapsed time:')):
            return                      # 한 줄 stats — 집계 제외.

        fm = _RC_FILE.match(body)
        if fm:
            obj, act = fm.group('obj'), fm.group('act')
            size = parse_size(fm.group('size'))
            if act == 'delete':
                self.delete_count += 1
                self.delete_bytes += size
                if len(self.deleted_files) < _FILE_CAP:
                    self.deleted_files.append({'path': obj, 'bytes': size})
            else:                       # copy(신규) + update(변경) = 업로드.
                self.upload_count += 1
                self.upload_bytes += size
                if act == 'copy':       # 신규 파일 → 추가.
                    self.added_count += 1
                    self.added_bytes += size
                    if len(self.added_files) < _FILE_CAP:
                        self.added_files.append({'path': obj, 'bytes': size})
                else:                   # update → 수정(내용·시각 변경).
                    self.modified_count += 1
                    self.modified_bytes += size
                    if len(self.modified_files) < _FILE_CAP:
                        self.modified_files.append({'path': obj, 'bytes': size})
                slot = self._by_dir.setdefault(_top_dir(obj), [0, 0])
                slot[0] += 1
                slot[1] += size
                if obj.rsplit('/', 1)[-1] in _JUNK_BASENAMES \
                        and len(self.junk) < _WARN_CAP:
                    self.junk.append(obj)
            return

        dm = _RC_DIR.match(body)
        if dm:
            act = dm.group('act')
            if act == 'make directory':
                self.dirs['make'] += 1
            elif act == 'remove directory':
                self.dirs['remove'] += 1
            else:
                self.dirs['touch'] += 1
            return

        # 남은 NOTICE/ERROR (호스트키 미검증·config 경고 등) → 경고로 수집.
        if lvl in ('NOTICE', 'ERROR') and body not in self.warnings \
                and len(self.warnings) < _WARN_CAP:
            self.warnings.append(body)

    @staticmethod
    def _list_more(total_count, total_bytes, files):
        """목록 상한 초과분 롤업 {count,bytes} (없으면 None). 총계−보관분."""
        shown = len(files)
        if total_count <= shown:
            return None
        return {'count': total_count - shown,
                'bytes': total_bytes - sum(f['bytes'] for f in files)}

    def to_dict(self) -> dict:
        rows = sorted(self._by_dir.items(), key=lambda kv: (-kv[1][1], kv[0]))
        head, tail = rows[:_BY_DIR_CAP], rows[_BY_DIR_CAP:]
        by_dir = [{'dir': d, 'count': cb[0], 'bytes': cb[1]} for d, cb in head]
        more = None
        if tail:
            more = {'dirs': len(tail),
                    'count': sum(cb[0] for _, cb in tail),
                    'bytes': sum(cb[1] for _, cb in tail)}
        return {
            'dry_run': True,
            'remote_path': self.remote_path,
            # 'upload' = copy+update 합산(하위호환). 'added'/'modified' 가 분리본.
            'upload': {'count': self.upload_count, 'bytes': self.upload_bytes},
            'added': {'count': self.added_count, 'bytes': self.added_bytes},
            'modified': {'count': self.modified_count,
                         'bytes': self.modified_bytes},
            'delete': {'count': self.delete_count, 'bytes': self.delete_bytes},
            'added_files': list(self.added_files),
            'modified_files': list(self.modified_files),
            'deleted_files': list(self.deleted_files),
            'added_more': self._list_more(self.added_count, self.added_bytes,
                                          self.added_files),
            'modified_more': self._list_more(self.modified_count,
                                             self.modified_bytes,
                                             self.modified_files),
            'deleted_more': self._list_more(self.delete_count,
                                            self.delete_bytes,
                                            self.deleted_files),
            'dirs': dict(self.dirs),
            'warnings': list(self.warnings),
            'junk': list(self.junk),
            'by_dir': by_dir,
            'by_dir_more': more,
        }


def build_dry_run_summary(lines) -> dict:
    """줄 이터러블 → 요약 dict (테스트·CLI 공용 순수 함수)."""
    s = DryRunSummary()
    for line in lines:
        s.feed(line)
    return s.to_dict()


def _emit_dry_run_summary(summary: dict, log: Callable[[str], None]) -> None:
    """사람용 요약을 log 로 출력하고, env 가 켜졌으면 기계용 JSON 한 줄도 덧붙인다."""
    up, dl, dirs = summary['upload'], summary['delete'], summary['dirs']
    dir_ops = dirs['make'] + dirs['remove'] + dirs['touch']
    warn = len(summary['warnings']) + len(summary['junk'])
    log(i18n.t('cli.deploy.summary.header'))
    log(i18n.t('cli.deploy.summary.counts',
               uploads=up['count'], up_size=human_size(up['bytes']),
               deletes=dl['count'], del_size=human_size(dl['bytes']),
               dirs=dir_ops, warnings=warn))
    if summary['junk']:
        log(i18n.t('cli.deploy.summary.junk', count=len(summary['junk'])))
    if os.environ.get('HERON_DEPLOY_SUMMARY') == 'json':
        sys.stdout.write(
            SUMMARY_SENTINEL
            + json.dumps(summary, ensure_ascii=False, separators=(',', ':'))
            + '\n')
        sys.stdout.flush()


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
    # alias 모드엔 host/user 가 없을 수 있다(remote_path 만 필수) — 별칭 줄로 분기.
    alias = str(cfg.get('ssh_alias', '')).strip()
    if alias:
        log(i18n.t('cli.deploy.sync_line_alias', alias=alias,
                   remote=cfg['remote_path'], mode=mode))
    else:
        log(i18n.t('cli.deploy.sync_line', user=cfg['user'], host=cfg['host'],
                   remote=cfg['remote_path'], mode=mode))

    proc = subprocess.Popen(
        argv, cwd=str(base),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding='utf-8', errors='replace', bufsize=1)
    assert proc.stdout is not None
    summary = DryRunSummary(cfg['remote_path']) if dry_run else None
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        if summary is not None:
            summary.feed(line.rstrip('\r\n'))
    proc.wait()
    code = proc.returncode
    if code == 0:
        if summary is not None:
            _emit_dry_run_summary(summary.to_dict(), log)
        log(i18n.t('cli.deploy.preview_done') if dry_run
            else i18n.t('cli.deploy.done'))
    else:
        log(i18n.t('cli.deploy.rclone_exit', code=code))
    return code


# ── 파일별 diff (미리보기 → 클릭 시 그 파일만) ─────────────────────
#
# dry-run 은 '무엇이 바뀌는지'만 알려줄 뿐 파일 내용은 안 준다. 수정 파일의 '이전'
# 은 로컬 dist 에 없고 원격에만 있으므로, 사용자가 한 파일을 클릭할 때만 그 파일을
# rclone cat 으로 받아 로컬 dist 본과 unified diff 를 만든다(Python 단일 출처).
# 대용량/바이너리/사라짐 등은 kind 유니온으로 우아하게 끊는다 — Pond 가 렌더만.

def _safe_relpath(rel) -> Optional[str]:
    """dist 기준 상대경로 정규화·검증(admin_safe_rel 과 동형, 심층 방어).

    슬래시/역슬래시 통일, NUL·빈세그·'.'·'..'·드라이브문자·선행 슬래시 거부.
    반환: 정규화된 rel 또는 None(거부). 선행 '-' 도 cat 인자에서 ``:sftp:.../``
    접두 뒤에 붙어 플래그로 오인되지 않으나, 경로 자체의 안전성만 본다.
    """
    if rel is None:
        return None
    rel = str(rel).replace('\\', '/').strip()
    if '\x00' in rel:
        return None
    rel = rel.lstrip('/')
    if not rel or re.match(r'^[A-Za-z]:', rel):
        return None
    parts = rel.split('/')
    for p in parts:
        if p in ('', '.', '..'):
            return None
    return '/'.join(parts)


def cat_remote(base, rel: str, cfg: dict, rclone, *,
               cap: int = _DIFF_CAP, log=None):
    """원격의 한 파일을 ``rclone cat`` 으로 받는다(바이너리, 연결 좌표는 sync 와 공유).

    cap+1 바이트까지만 읽고 초과 시 프로세스를 끊어 대용량·원격 DoS·메모리 폭주를
    막는다. rel 은 호출 전 _safe_relpath 통과 전제. 반환:
    (data:bytes, returncode:int, truncated:bool, stderr_text:str).
    """
    remote = f":sftp:{cfg['remote_path']}/{rel}"
    argv = [str(rclone), 'cat', remote] + _connection_flags(cfg)
    proc = subprocess.Popen(argv, cwd=str(base),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdout is not None and proc.stderr is not None
    data = proc.stdout.read(cap + 1)
    truncated = len(data) > cap
    if truncated:
        proc.kill()
    try:
        err = proc.stderr.read().decode('utf-8', 'replace')
    except OSError:
        err = ''
    proc.wait()
    return data[:cap], proc.returncode, truncated, err


def _clip_line(s: str) -> str:
    """한 줄 표시 상한(초과분은 …로 절단) — DOM/JSON 폭증 방지."""
    return s if len(s) <= _LINE_CLIP else s[:_LINE_CLIP] + '…'


def _build_hunks(old_lines, new_lines, *,
                 context: int = _DIFF_CONTEXT, max_lines: int = _DIFF_MAX_LINES):
    """줄 리스트 두 개 → unified hunk 목록 + truncated 플래그.

    difflib 의 그룹 오프코드(앞뒤 context 줄)로 hunk 를 만들고, 변경 블록은
    삭제(-)를 먼저, 추가(+)를 나중에 낸다(unified 관례). 총 줄수 상한 초과 시 끊는다.
    """
    sm = difflib.SequenceMatcher(a=old_lines, b=new_lines)
    hunks: List[dict] = []
    emitted = 0
    truncated = False
    for group in sm.get_grouped_opcodes(context):
        lines: List[dict] = []
        old_start = group[0][1] + 1
        new_start = group[0][3] + 1
        for tag, i1, i2, j1, j2 in group:
            if tag == 'equal':
                for k in range(i1, i2):
                    lines.append({'tag': ' ', 'old': k + 1,
                                  'new': j1 + (k - i1) + 1,
                                  'text': _clip_line(old_lines[k])})
                    emitted += 1
            else:
                for k in range(i1, i2):
                    lines.append({'tag': '-', 'old': k + 1, 'new': None,
                                  'text': _clip_line(old_lines[k])})
                    emitted += 1
                for k in range(j1, j2):
                    lines.append({'tag': '+', 'old': None, 'new': k + 1,
                                  'text': _clip_line(new_lines[k])})
                    emitted += 1
            if emitted >= max_lines:
                truncated = True
                break
        hunks.append({'old_start': old_start, 'new_start': new_start,
                      'lines': lines})
        if truncated:
            break
    return hunks, truncated


def compute_diff(base, relpath, *, opener=None, log=None) -> dict:
    """수정 파일 한 개의 unified diff (kind 유니온 dict). 네트워크는 이 안에서만.

    kind: 'diff'(hunks) | 'identical'(내용 동일·modtime 만) | 'binary' |
    'too_large' | 'gone'(로컬 dist 부재) | 'error'(잘못된 경로·cat 실패).
    """
    base = Path(base)
    log = log or (lambda _m: None)
    rel = _safe_relpath(relpath)
    if rel is None:
        return {'kind': 'error', 'path': str(relpath),
                'message': i18n.t('cli.deploy.diff.bad_path')}

    local = base / 'dist' / rel
    try:
        if not local.is_file():
            return {'kind': 'gone', 'path': rel}
        new_size = local.stat().st_size
        if new_size > _DIFF_CAP:
            return {'kind': 'too_large', 'path': rel,
                    'old_bytes': None, 'new_bytes': new_size, 'cap': _DIFF_CAP}
        new_bytes = local.read_bytes()
    except OSError as e:
        return {'kind': 'error', 'path': rel, 'message': str(e)}

    rclone = rclone_bin.ensure(base, opener=opener, log=log)
    cfg = load_config(base)
    old_bytes, code, truncated, err = cat_remote(base, rel, cfg, rclone, log=log)
    if truncated:
        return {'kind': 'too_large', 'path': rel,
                'old_bytes': None, 'new_bytes': len(new_bytes), 'cap': _DIFF_CAP}
    if code != 0:
        msg = (err or '').strip()[:500] or i18n.t('cli.deploy.diff.cat_failed')
        return {'kind': 'error', 'path': rel, 'message': msg}

    if b'\x00' in old_bytes or b'\x00' in new_bytes:
        return {'kind': 'binary', 'path': rel,
                'old_bytes': len(old_bytes), 'new_bytes': len(new_bytes)}
    if old_bytes == new_bytes:
        return {'kind': 'identical', 'path': rel, 'new_bytes': len(new_bytes)}

    old_lines = old_bytes.decode('utf-8', 'replace').splitlines()
    new_lines = new_bytes.decode('utf-8', 'replace').splitlines()
    hunks, trunc = _build_hunks(old_lines, new_lines)
    return {'kind': 'diff', 'path': rel,
            'old_bytes': len(old_bytes), 'new_bytes': len(new_bytes),
            'truncated': trunc, 'hunks': hunks}

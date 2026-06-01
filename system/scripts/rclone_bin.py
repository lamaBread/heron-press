"""rclone 실행 바이너리 확보 (v1.7.0 신설).

dist 배포(``deploy.py``)는 rclone 의 SFTP 백엔드로 증분 동기화한다. rclone 은
**플랫폼별 단일 정적 바이너리**(DLL 0, MIT 라이선스)라 저장소에 동봉하지 않고
**필요할 때 핀 버전을 받아** ``system/runtime/bin/<os>-<arch>/`` 에 둔다.

설계 (update.py 의 다운로드 패턴 미러):
  - 버전은 ``RCLONE_VERSION`` 으로 **특정 태그에 핀**한다 ('current' 금지 —
    공급망 안정성). 각 아카이브(.zip)의 SHA256 을 ``PINS`` 에 박아, 다운로드
    바이트가 핀과 일치할 때만 추출한다. 불일치 = 즉시 거부.
  - 네트워크 부분은 ``opener`` 주입이 가능해 테스트가 네트워크 없이 전 경로를
    검증한다 (test_rclone_bin).
  - ``ensure()`` 는 **멱등** — 핀 버전이 이미 자리에 있으면 네트워크 0.
  - 오프라인/네트워크 실패 시 PATH 의 rclone 으로 폴백(버전 무관 허용),
    그래도 없으면 사람이 읽을 수 있는 명확한 오류.

바이너리는 ``system/`` 아래지만 머신 종속물이라 **프로그램 표면이 아니다** —
``make_manifest`` 가 ``system/runtime/bin/`` 를 제외하고 ``.gitignore`` 도
제외하므로 MANIFEST·커밋·오버레이 어디에도 새지 않는다.
"""
import hashlib
import platform
import shutil
import ssl
import stat
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable, Optional, Tuple

# 핀 버전 + 6개 플랫폼 아카이브(.zip) SHA256 — 공식
# https://downloads.rclone.org/{ver}/SHA256SUMS 에서 수집 (v1.74.2).
RCLONE_VERSION = 'v1.74.2'
PINS = {
    # (os, arch): sha256 of rclone-{ver}-{os}-{arch}.zip
    ('windows', 'amd64'): '71f376f47428bd467bf92e8bfe7fb36f4c108a4fc4edd3df30fc74dd409c7eef',
    ('windows', 'arm64'): '464c8abf9eab9dab843906aac90fbd63386eb07576cd8571d03fbd10483c763e',
    ('osx',     'amd64'): 'fc24831eefa3918c278c4a10be4de78288422426e2f7e64509205167f845874d',
    ('osx',     'arm64'): 'e170fc4f225cbe3685695c4761259fe5883115a2b022a2f39b7298f946b8d898',
    ('linux',   'amd64'): '72a806370072015ccbe4d81bcd348cc5eaf3beca6c65ba693fd43fb31fcca5b1',
    ('linux',   'arm64'): 'bc2b2eb8269b743ed7bcea869f3782cfb4931e41efa53fc8befc6dc8308b7a50',
}

BASE_URL = 'https://downloads.rclone.org'
USER_AGENT = 'heron-press-rclone-fetch'
_TIMEOUT = 60  # 아카이브가 수십 MB — update 체크보다 넉넉히.


# ── 플랫폼 매핑 ───────────────────────────────────────────────────

def platform_key() -> Tuple[str, str]:
    """현재 (os, arch) 를 rclone 의 표기로 반환.

    os : Windows→windows, Darwin→osx (**mac 은 osx**), Linux→linux.
    arch: AMD64/x86_64→amd64, arm64/aarch64→arm64.
    그 외(예: 386, armv7)는 명확한 오류 — v1.7.0 은 amd64/arm64 만 지원.
    """
    sysname = platform.system()
    os_map = {'Windows': 'windows', 'Darwin': 'osx', 'Linux': 'linux'}
    os_key = os_map.get(sysname)
    if os_key is None:
        raise RuntimeError(
            f'지원하지 않는 OS: {sysname!r}. rclone 자동 확보는 Windows/macOS/'
            'Linux 만 지원합니다. rclone 을 PATH 에 두거나 '
            'system/runtime/bin/<os>-<arch>/ 에 수동 배치하세요.')
    machine = platform.machine().lower()
    if machine in ('amd64', 'x86_64', 'x64'):
        arch_key = 'amd64'
    elif machine in ('arm64', 'aarch64'):
        arch_key = 'arm64'
    else:
        raise RuntimeError(
            f'지원하지 않는 CPU 아키텍처: {platform.machine()!r}. v1.7.0 은 '
            'amd64/arm64 만 지원합니다. rclone 을 PATH 에 두거나 '
            'system/runtime/bin/<os>-<arch>/ 에 수동 배치하세요.')
    return os_key, arch_key


def binary_name(os_key: str) -> str:
    return 'rclone.exe' if os_key == 'windows' else 'rclone'


def binary_path(base) -> Path:
    """``<base>/system/runtime/bin/<os>-<arch>/rclone[.exe]`` (현재 플랫폼)."""
    os_key, arch_key = platform_key()
    return (Path(base) / 'system' / 'runtime' / 'bin'
            / f'{os_key}-{arch_key}' / binary_name(os_key))


def _archive_name(os_key: str, arch_key: str) -> str:
    return f'rclone-{RCLONE_VERSION}-{os_key}-{arch_key}.zip'


def download_url(os_key: str, arch_key: str) -> str:
    return f'{BASE_URL}/{RCLONE_VERSION}/{_archive_name(os_key, arch_key)}'


# ── 네트워크 (opener 주입 가능) ────────────────────────────────────

def _default_opener(req, timeout=_TIMEOUT):
    # 명시적 기본 SSL 컨텍스트 (인증서 검증 유지 — update.py 와 동일 정책).
    ctx = ssl.create_default_context()
    return urllib.request.urlopen(req, timeout=timeout, context=ctx)


def _download(url: str, opener: Optional[Callable]) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    op = opener or _default_opener
    with op(req) as r:
        return r.read()


# ── 설치된 바이너리 버전 ──────────────────────────────────────────

def installed_version(path: Path) -> Optional[str]:
    """``rclone version`` 첫 줄에서 'v1.74.2' 형태를 뽑는다. 실패면 None."""
    try:
        out = subprocess.run([str(path), 'version'], capture_output=True,
                             text=True, encoding='utf-8', errors='replace',
                             timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    for tok in (out.stdout or '').split():
        if tok.startswith('v') and tok[1:2].isdigit():
            return tok
    return None


# ── 추출 ──────────────────────────────────────────────────────────

def _extract_binary(zip_bytes: bytes, os_key: str, dst: Path) -> None:
    """zip 바이트에서 rclone(.exe) 한 개만 dst 로 원자적 배치.

    rclone 아카이브는 ``rclone-{ver}-{os}-{arch}/rclone[.exe]`` 구조라
    경로 끝이 바이너리명인 엔트리를 찾는다. 임시파일로 추출 후 os.replace —
    반쪽 다운로드/추출이 최종 경로에 절대 남지 않게.
    """
    import io
    want = binary_name(os_key)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        member = None
        for name in zf.namelist():
            # 절대/상위탈출 엔트리 거부 (zip slip 방어).
            if name.startswith('/') or '..' in Path(name).parts:
                raise ValueError(f'안전하지 않은 zip 엔트리: {name}')
            if name.replace('\\', '/').rstrip('/').endswith('/' + want) \
                    or name == want:
                member = name
                break
        if member is None:
            raise RuntimeError(
                f'아카이브에서 {want} 를 찾지 못했습니다 (손상된 다운로드?).')
        payload = zf.read(member)
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.parent / (dst.name + '.heron_tmp')
    tmp.write_bytes(payload)
    if os_key != 'windows':
        mode = tmp.stat().st_mode
        tmp.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    tmp.replace(dst)  # 원자적 교체


# ── 공개 진입점 ───────────────────────────────────────────────────

def ensure(base, *, opener: Optional[Callable] = None,
           log: Optional[Callable[[str], None]] = None,
           allow_path_fallback: bool = True) -> Path:
    """검증된 rclone 실행파일 경로를 보장해 반환.

    1. 핀 버전이 이미 자리에 있으면 그대로 반환 (멱등, 네트워크 0).
    2. 아니면: 핀 URL 다운로드 → 아카이브 SHA256 == PINS 검증 → rclone(.exe)
       추출 → 원자적 배치 → ``rclone version`` 재확인.
    3. 네트워크/검증 실패 + allow_path_fallback → PATH 의 rclone 으로 폴백.
       그래도 없으면 사람이 읽을 명확한 오류.

    SHA256 불일치는 **즉시 중단**(공급망 차단) — 폴백조차 시도하지 않는다.
    """
    log = log or (lambda _m: None)
    base = Path(base)
    os_key, arch_key = platform_key()
    pin = PINS.get((os_key, arch_key))
    if pin is None:
        raise RuntimeError(
            f'핀이 없는 플랫폼: {os_key}-{arch_key}.')

    dst = binary_path(base)

    # 1) 멱등 스킵.
    if dst.is_file():
        have = installed_version(dst)
        if have == RCLONE_VERSION:
            log(f'rclone {RCLONE_VERSION} 확인됨 ({dst}). 다운로드 생략.')
            return dst
        log(f'기존 rclone 버전 불일치(설치={have}, 필요={RCLONE_VERSION}) — 재확보.')

    # 2) 다운로드 + 검증 + 추출.
    url = download_url(os_key, arch_key)
    try:
        log(f'rclone {RCLONE_VERSION} 다운로드: {url}')
        data = _download(url, opener)
    except Exception as e:  # 네트워크/오프라인 — 폴백 시도
        log(f'다운로드 실패: {type(e).__name__}: {e}')
        return _fallback_or_raise(allow_path_fallback, log, str(e))

    digest = hashlib.sha256(data).hexdigest()
    if digest != pin:
        # 공급망 차단 — 폴백 없이 즉시 중단.
        raise RuntimeError(
            'rclone 아카이브 SHA256 불일치 — 다운로드를 거부합니다 (공급망 '
            f'보호). 기대={pin} 실제={digest}. URL={url}')
    log(f'SHA256 검증 통과 ({len(data)} 바이트).')

    _extract_binary(data, os_key, dst)
    log(f'추출·배치 완료: {dst}')

    have = installed_version(dst)
    if have != RCLONE_VERSION:
        raise RuntimeError(
            f'배치 후 버전 재확인 실패 (실행={have!r}, 기대={RCLONE_VERSION}).')
    log(f'rclone {RCLONE_VERSION} 준비 완료.')
    return dst


def _fallback_or_raise(allow: bool, log, why: str) -> Path:
    """PATH 의 rclone 으로 폴백 (버전 무관 허용). 없으면 명확한 오류."""
    if allow:
        found = shutil.which('rclone')
        if found:
            ver = installed_version(Path(found))
            log(f'폴백: PATH 의 rclone 사용 ({found}, 버전={ver}).')
            return Path(found)
    raise RuntimeError(
        'rclone 을 확보하지 못했습니다. 인터넷 연결이 필요하거나, rclone 을 '
        'PATH 에 두거나, system/runtime/bin/<os>-<arch>/ 에 수동 배치하세요. '
        f'(원인: {why})')

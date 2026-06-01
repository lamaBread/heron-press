"""GitHub 릴리스에서 직접 자가 업데이트 (v1.6.0 신설).

공개 저장소(lamaBread/heron-press)의 최신 태그를 인식해 zip 을 받아 프로그램
표면만 오버레이하고 마이그레이션을 돌린다. user/ 는 절대 건드리지 않는다.

설계:
  - 로직은 Python(stdlib: urllib + zipfile)에 둔다. Pond.php 는 이 모듈을
    `python Heron.py --check-update / --update` 로 호출하는 얇은 트리거일 뿐.
  - 네트워크 부분(태그 조회·다운로드)은 opener 주입이 가능해 테스트에서
    네트워크 없이 검증된다. 태그 선택·다운로드 검증·오버레이는 순수 함수.

self-update 의 정직한 처리:
  Pond.php·system/admin/ 이 오버레이로 교체되지만, 실행 중인 PHP 프로세스는
  옛 코드를 메모리에 들고 있다. 그래서 파일 스왑까지만 하고 "재시작 필요" 를
  사용자에게 알린다 (몰래 reload 흉내 내지 않음).

  같은 이유로 **마이그레이션은 새로 띄운 서브프로세스(`python Heron.py
  --migrate`)로 재실행한다** — 오버레이가 디스크의 .py 를 바꿔도 현재 실행
  중인 인터프리터는 옛 `scripts.migrations` 를 sys.modules 에 캐시하고 있어,
  in-process 호출은 *새 릴리스가 추가한* 마이그레이션 스텝을 놓친다. 새
  Heron.py 를 서브프로세스로 띄워야 새 코드의 마이그레이션 체인이 돈다.

안전장치:
  - REPO 상수 고정 — 임의 출처로 못 가리킴.
  - 다운로드 트리가 자기 MANIFEST 와 sha256 일치할 때만 오버레이.
  - 오버레이는 MANIFEST 의 프로그램 경로만 복사/삭제 — user/ 시작 경로는 거부.
  - 오버레이/마이그레이션 직전 프로그램 표면 + 스탬프를 백업.
"""
import json
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable, Optional

from . import make_manifest
from . import version as _version
from . import i18n

# 고정 저장소 (임의 출처 차단).
REPO = 'lamaBread/heron-press'
API_TAGS = f'https://api.github.com/repos/{REPO}/tags'
ZIPBALL = f'https://api.github.com/repos/{REPO}/zipball/{{tag}}'
USER_AGENT = 'heron-press-updater'
_TIMEOUT = 20

CACHE_NAME = 'update.json'
BACKUPS_DIR = 'backups'


# ── 네트워크 (opener 주입 가능) ────────────────────────────────────

def _default_opener(req, timeout=_TIMEOUT):
    # 명시적 기본 SSL 컨텍스트 (인증서 검증 유지). Windows 인증서 이슈는
    # README 에 caveat 로 명시.
    ctx = ssl.create_default_context()
    return urllib.request.urlopen(req, timeout=timeout, context=ctx)


def _http_get(url: str, opener: Optional[Callable], *, binary=False):
    req = urllib.request.Request(url, headers={
        'User-Agent': USER_AGENT,
        'Accept': 'application/vnd.github+json',
    })
    op = opener or _default_opener
    with op(req) as r:
        data = r.read()
    return data if binary else data.decode('utf-8')


# ── 순수 함수 ─────────────────────────────────────────────────────

def select_latest_tag(tags: list, _current=None):
    """태그 목록에서 semver 최대 태그 dict 반환 (파싱 불가 태그 무시). 없으면 None."""
    best, best_v = None, None
    for t in tags or []:
        v = _version.parse_version(t.get('name', '') if isinstance(t, dict) else '')
        if v is None:
            continue
        if best_v is None or v > best_v:
            best, best_v = t, v
    return best


def _safe_rel(rel: str) -> bool:
    """오버레이/삭제가 허용되는 프로그램 표면 상대경로인가."""
    if not rel or rel.startswith('/') or rel.startswith('\\'):
        return False
    parts = rel.replace('\\', '/').split('/')
    if '..' in parts or '.' in parts:
        return False
    # user/ 는 사용자 소유 — 매니페스트엔 없지만 이중 방어.
    if parts[0] == 'user':
        return False
    return True


def overlay(src_base, dst_base, *, log: Optional[Callable[[str], None]] = None) -> dict:
    """src_base 의 프로그램 표면을 dst_base 에 덮어쓴다. 신 매니페스트에서
    사라진(설치본에만 있던) 프로그램 파일은 삭제한다. user/ 는 불변.

    반환: {copied:int, deleted:int}.
    """
    log = log or (lambda _m: None)
    src_base, dst_base = Path(src_base), Path(dst_base)
    new_files = make_manifest.compute_manifest(src_base)['files']
    old_files = (make_manifest.load_manifest(dst_base).get('files') or {})

    copied = 0
    for rel in sorted(new_files):
        if not _safe_rel(rel):
            raise ValueError(i18n.t('cli.update.unsafe_overlay', rel=rel))
        s, d = src_base / rel, dst_base / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s, d)
        copied += 1
    log(i18n.t('cli.update.copied', count=copied))

    deleted = 0
    for rel in sorted(set(old_files) - set(new_files)):
        if not _safe_rel(rel):
            continue
        p = dst_base / rel
        if p.is_file():
            p.unlink()
            deleted += 1
    if deleted:
        log(i18n.t('cli.update.deleted', count=deleted))

    # MANIFEST.json 은 파일 목록에서 자기 자신을 제외하므로 위 복사 루프에
    # 안 잡힌다. 설치본 매니페스트가 새 릴리스를 반영하도록(이후 --check 가
    # 새 표면을 검증) 명시적으로 교체한다.
    src_man = make_manifest.manifest_path(src_base)
    if src_man.is_file():
        dst_man = make_manifest.manifest_path(dst_base)
        dst_man.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_man, dst_man)
    return {'copied': copied, 'deleted': deleted}


# ── 업데이트 캐시 (Pond 배너용) ───────────────────────────────────

def _cache_path(base) -> Path:
    return _version.heron_dir(base) / CACHE_NAME


def read_cache(base) -> dict:
    try:
        return json.loads(_cache_path(base).read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_cache(base, data: dict) -> None:
    _version.heron_dir(base).mkdir(parents=True, exist_ok=True)
    p = _cache_path(base)
    tmp = p.with_suffix('.json.heron_tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                   encoding='utf-8')
    tmp.replace(p)


# ── 액션 ──────────────────────────────────────────────────────────

def check_update(base, *, opener: Optional[Callable] = None,
                 write_cache: bool = True) -> dict:
    """GitHub 태그를 조회해 새 버전 유무를 판단하고 캐시에 기록.

    반환: {current, latest, update_available, zipball_url, checked_at, error}.
    네트워크 실패 시 crash 대신 error 를 채워 반환.
    """
    current = make_manifest.program_version(base)
    result = {
        'current': current, 'latest': None, 'update_available': False,
        'zipball_url': None,
        'checked_at': time.strftime('%Y-%m-%dT%H:%M:%S'), 'error': None,
    }
    try:
        tags = json.loads(_http_get(API_TAGS, opener))
        latest = select_latest_tag(tags, current)
        if latest:
            name = latest.get('name')
            result['latest'] = name
            result['zipball_url'] = latest.get('zipball_url') \
                or ZIPBALL.format(tag=name)
            result['update_available'] = _version.compare(current, name) < 0
    except Exception as e:  # 네트워크/파싱 등 — UI 에 메시지로 표면화
        result['error'] = f'{type(e).__name__}: {e}'
    if write_cache:
        _write_cache(base, result)
    return result


def _find_extract_root(extract_dir: Path) -> Path:
    """zipball 추출 결과의 실제 루트(보통 단일 top-level 디렉터리)를 찾는다."""
    entries = [p for p in extract_dir.iterdir()]
    dirs = [p for p in entries if p.is_dir()]
    if len(entries) == 1 and dirs:
        return dirs[0]
    # system/ 을 직접 품은 디렉터리를 탐색 (안전망).
    if (extract_dir / 'system').is_dir():
        return extract_dir
    for p in dirs:
        if (p / 'system').is_dir():
            return p
    return extract_dir


def _download_zip(url: str, dest: Path, opener: Optional[Callable]) -> None:
    data = _http_get(url, opener, binary=True)
    dest.write_bytes(data)


def _backup_program(base: Path, label: str, log: Callable) -> Path:
    """오버레이 전 프로그램 표면 + 스탬프를 user/.heron/backups/<label>/ 로 복사."""
    dest = _version.heron_dir(base) / BACKUPS_DIR / label
    dest.mkdir(parents=True, exist_ok=True)
    for rel in make_manifest.iter_program_files(base):
        s, d = base / rel, dest / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s, d)
    stamp = _version.version_file(base)
    if stamp.is_file():
        stamp_dst = dest / 'user' / '.heron' / 'version'
        stamp_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(stamp, stamp_dst)
    log(i18n.t('cli.update.backup', path=dest))
    return dest


def _run_migrate(base, log) -> bool:
    """오버레이된 새 코드로 마이그레이션을 서브프로세스 재실행.

    in-process 호출은 옛 `scripts.migrations` 를 쓰므로 새 릴리스가 추가한
    스텝을 놓친다 — 새 Heron.py 를 띄워야 새 체인이 돈다. 새 Heron.py 의
    `--migrate` 는 새 `__version__` 을 목표로 잡는다.
    """
    proc = subprocess.run(
        [sys.executable, str(Path(base) / 'Heron.py'), '--migrate'],
        cwd=str(base), capture_output=True, text=True,
        encoding='utf-8', errors='replace')
    if proc.stdout:
        log(proc.stdout.rstrip())
    if proc.stderr:
        log(proc.stderr.rstrip())
    return proc.returncode == 0


def self_update(base, *, opener: Optional[Callable] = None,
                log: Optional[Callable[[str], None]] = None,
                force: bool = False,
                migrate_fn: Optional[Callable] = None) -> dict:
    """체크 → 다운로드 → 추출 → 무결성 검증 → 백업 → 오버레이 → 마이그레이션.

    마이그레이션은 기본적으로 새 코드를 쓰는 서브프로세스(`_run_migrate`)로
    돈다. migrate_fn 을 주입하면 그 콜러블 ``(base, log) -> bool`` 로 대체된다
    (테스트가 in-process 마이그레이션을 주입할 때 사용).

    반환: {ok, updated, from, to, error, copied, deleted, migrated_to,
           migrate_ok, restart}. restart=True 면 Pond/PHP 재시작 필요.
    """
    base = Path(base)
    log = log or (lambda _m: None)
    migrate_fn = migrate_fn or _run_migrate
    out = {'ok': False, 'updated': False, 'from': None, 'to': None,
           'error': None, 'copied': 0, 'deleted': 0, 'migrated_to': None,
           'migrate_ok': False, 'restart': False}

    info = check_update(base, opener=opener)
    out['from'] = info['current']
    if info['error']:
        out['error'] = i18n.t('cli.checkupdate.failed', error=info['error'])
        log(out['error'])
        return out
    out['to'] = info['latest']
    if not info['update_available'] and not force:
        out['ok'] = True
        log(i18n.t('cli.update.already_latest', current=info['current']))
        return out

    url = info['zipball_url'] or ZIPBALL.format(tag=info['latest'])
    with tempfile.TemporaryDirectory(prefix='heron-update-') as tmp:
        tmp = Path(tmp)
        zip_path = tmp / 'release.zip'
        log(i18n.t('cli.update.downloading', tag=info['latest']))
        try:
            _download_zip(url, zip_path, opener)
        except Exception as e:
            out['error'] = i18n.t('cli.update.download_failed',
                                  error=f'{type(e).__name__}: {e}')
            log(out['error'])
            return out

        extract_dir = tmp / 'x'
        extract_dir.mkdir()
        with zipfile.ZipFile(zip_path) as zf:
            for m in zf.namelist():
                if m.startswith('/') or '..' in Path(m).parts:
                    out['error'] = i18n.t('cli.update.unsafe_zip', entry=m)
                    log(out['error'])
                    return out
            zf.extractall(extract_dir)
        root = _find_extract_root(extract_dir)

        # 무결성: 다운로드 트리가 자기 MANIFEST 와 일치하는가.
        if make_manifest.manifest_path(root).is_file():
            v = make_manifest.verify(root)
            if not v['ok']:
                out['error'] = i18n.t('cli.update.integrity_failed',
                                      missing=v['missing'],
                                      modified=v['modified'])
                log(out['error'])
                return out
            log(i18n.t('cli.update.integrity_ok'))
        else:
            log(i18n.t('cli.update.no_manifest'))

        new_version = make_manifest.program_version(root)
        label = f"{info['current']}-to-{new_version}-{time.strftime('%Y%m%d-%H%M%S')}"
        _backup_program(base, label, log)

        ov = overlay(root, base, log=log)
        out['copied'], out['deleted'] = ov['copied'], ov['deleted']

    # 오버레이 후 = 디스크는 새 코드. 새 코드로 마이그레이션 재실행.
    out['migrate_ok'] = migrate_fn(base, log)
    out['migrated_to'] = _version.read_schema_version(base)
    out['updated'] = True
    out['ok'] = out['migrate_ok']
    out['to'] = new_version
    out['restart'] = True

    # Pond 배너 캐시를 새 버전 상태로 갱신한다. 이 함수 시작의 check_update 가
    # 적어 둔 캐시는 update_available=True 라, 갱신하지 않으면 업데이트를 마친
    # 뒤(Pond 재시작 후에도) list.php 가 stale 캐시를 읽어 "새 버전 있음" 배너를
    # 계속 띄운다. 프로그램 표면은 이미 새 버전으로 교체됐으므로 available=False.
    _write_cache(base, {
        'current': new_version,
        'latest': info['latest'],
        'update_available': False,
        'zipball_url': None,
        'checked_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'error': None,
    })

    log(i18n.t('cli.update.complete', from_v=out['from'], to_v=new_version,
               schema=out['migrated_to']))
    return out

"""프로그램 표면 MANIFEST 생성·검증 (v1.6.0 신설).

"프로그램 표면" = 업그레이드 시 통째 교체되는 파일 집합. user/ 콘텐츠와 명확히
구분된다. system/MANIFEST.json 은 그 목록 + 각 파일의 sha256 을 담아:

  - Heron.py --check 가 설치된 프로그램이 매니페스트와 일치하는지 검증
    (부분 복사·실수 편집 탐지).
  - 업데이트 엔진이 다운로드한 릴리스의 무결성을 검증하고, "덮어쓸 경로"를
    정확히 안다 (allowlist 오버레이 — user/ 를 절대 건드리지 않도록).

매니페스트는 릴리스에 동봉(커밋)된다. 모든 경로는 base 기준 POSIX 상대경로.

이 모듈은 매니페스트를 *프로그램 버전이 아니라 디스크의 파일* 에서 계산한다
(version 은 대상 트리의 scripts/__init__.py 에서 읽음). 그래서 다운로드한
릴리스 트리에도 그대로 적용된다.
"""
import hashlib
import json
import re
from pathlib import Path

MANIFEST_NAME = 'MANIFEST.json'
MANIFEST_REL = f'system/{MANIFEST_NAME}'

# system/ 외에 프로그램 표면에 포함하는 루트 파일. (.gitignore 는 저장소 인프라
# 라 제외 — 사용자가 손대도 무해하고 업데이트로 덮을 이유가 없다.)
_ROOT_FILES = ('Heron.py', 'Pond.php', 'README.md', 'README.ko.md')

# 표면에서 제외할 경로 조각.
_EXCLUDE_DIR_NAMES = {'__pycache__'}
_EXCLUDE_SUFFIXES = ('.pyc', '.pyo', '.heron_tmp', '.tmp')
# system/ 아래에서 제외할 상대경로 (base 기준). 생성물·매니페스트 자신.
_EXCLUDE_SYSTEM_REL = {
    MANIFEST_REL,
    'system/tests/diagnostics_report.txt',
}


def _sha256_file(path: Path) -> str:
    """파일 내용 sha256 — 텍스트는 개행 정규화 후 해시.

    프로그램 표면은 git 이 관리하므로 autocrlf/eol 설정에 따라 체크아웃마다
    CRLF↔LF 가 달라진다(Windows 작업본 CRLF, GitHub zipball/Linux 는 LF). raw
    바이트 해시는 플랫폼·전달 경로마다 어긋나 무결성 검증이 헛돈다. 그래서
    텍스트 파일은 `\\r\\n`·`\\r` → `\\n` 으로 정규화한 뒤 해시해 *개행 방식과
    무관하게* 안정된 해시를 만든다(우리 자체 무결성 스킴 — `sha256sum` 원본
    해시와는 다르다). 바이트에 NUL 이 있으면 바이너리로 보고 raw 그대로 해시.
    """
    data = path.read_bytes()
    if b'\x00' not in data:  # 텍스트로 간주 → 개행 정규화
        data = data.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
    return hashlib.sha256(data).hexdigest()


def _excluded(rel: str) -> bool:
    parts = rel.split('/')
    if any(seg in _EXCLUDE_DIR_NAMES for seg in parts):
        return True
    if rel.endswith(_EXCLUDE_SUFFIXES):
        return True
    if rel in _EXCLUDE_SYSTEM_REL:
        return True
    return False


def iter_program_files(base) -> list:
    """프로그램 표면 파일의 base 기준 POSIX 상대경로 목록 (정렬)."""
    base = Path(base)
    rels = []
    for name in _ROOT_FILES:
        if (base / name).is_file():
            rels.append(name)
    system = base / 'system'
    if system.is_dir():
        for p in system.rglob('*'):
            if not p.is_file():
                continue
            rel = p.relative_to(base).as_posix()
            if not _excluded(rel):
                rels.append(rel)
    rels.sort()
    return rels


def program_version(base) -> str:
    """대상 트리의 system/scripts/__init__.py 에서 __version__ 을 읽는다."""
    init = Path(base) / 'system' / 'scripts' / '__init__.py'
    try:
        txt = init.read_text(encoding='utf-8')
    except OSError:
        return '0'
    m = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", txt)
    return m.group(1) if m else '0'


def compute_manifest(base) -> dict:
    """{version, files:{relpath: sha256}} 매니페스트 dict 계산."""
    base = Path(base)
    files = {rel: _sha256_file(base / rel) for rel in iter_program_files(base)}
    return {'version': program_version(base), 'files': files}


def manifest_path(base) -> Path:
    return Path(base) / 'system' / MANIFEST_NAME


def write_manifest(base) -> dict:
    """매니페스트를 계산해 system/MANIFEST.json 에 결정적으로 기록."""
    data = compute_manifest(base)
    path = manifest_path(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + '\n'
    tmp = path.with_suffix('.json.heron_tmp')
    tmp.write_text(text, encoding='utf-8')
    tmp.replace(path)
    return data


def load_manifest(base) -> dict:
    """동봉된 system/MANIFEST.json 로드 (없거나 깨지면 빈 dict)."""
    try:
        return json.loads(manifest_path(base).read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}


def verify(base) -> dict:
    """설치된 프로그램 표면을 동봉 매니페스트와 대조.

    반환: {ok:bool, manifest_version, missing:[rel], modified:[rel],
           untracked:[rel]}. untracked = 매니페스트엔 없지만 디스크엔 있는
           프로그램 표면 파일 (정보용; ok 에는 영향 없음).
    """
    base = Path(base)
    man = load_manifest(base)
    files = man.get('files') or {}
    missing, modified = [], []
    for rel, want in sorted(files.items()):
        p = base / rel
        if not p.is_file():
            missing.append(rel)
        elif _sha256_file(p) != want:
            modified.append(rel)
    disk = set(iter_program_files(base))
    untracked = sorted(disk - set(files.keys()))
    return {
        'ok': not missing and not modified,
        'manifest_version': man.get('version'),
        'missing': missing,
        'modified': modified,
        'untracked': untracked,
    }


def main(argv=None) -> int:
    import argparse
    parser = argparse.ArgumentParser(
        prog='make_manifest.py',
        description='Heron 프로그램 표면 MANIFEST.json 생성/검증.')
    parser.add_argument('base', nargs='?', default=None,
                        help='버전 폴더 (기본: 이 파일 기준 저장소 루트).')
    parser.add_argument('--verify', action='store_true',
                        help='생성 대신 기존 매니페스트와 대조.')
    args = parser.parse_args(argv)
    base = Path(args.base) if args.base else Path(__file__).resolve().parents[2]
    if args.verify:
        r = verify(base)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0 if r['ok'] else 1
    data = write_manifest(base)
    print(f"MANIFEST.json 기록: {len(data['files'])} 개 파일, "
          f"version {data['version']}")
    return 0


if __name__ == '__main__':
    import sys
    raise SystemExit(main())

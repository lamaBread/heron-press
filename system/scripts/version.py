"""스키마 버전 스탬프 + semver 비교 (v1.6.0 신설).

*프로그램* 버전은 scripts/__init__.py 의 ``__version__`` 이다. 이 모듈은
*사용자 스키마 버전* — user/ 아래 콘텐츠/설정이 따르는 스키마의 버전 —
을 추가한다. 기록 위치는 ``user/.heron/version`` 한 줄 파일.

왜 별도 스탬프인가:
  업그레이드 시 system/ 은 통째 교체된다. 마이그레이션 엔진은 user/ 가
  마지막으로 어느 스키마까지 맞춰졌는지 알아야 *남은* 스텝만 돌릴 수 있다.
  그래서 스탬프는 system/ 이 아니라 user/ 아래 둔다 (system/ 교체에도 생존,
  user/ 를 통째 이전해도 동행). ``.`` 접두라 빌더가 자동 제외(§6)해 dist 에
  새지 않는다.

스탬프 부재 처리:
  파일이 없으면 ``BASELINE_VERSION`` (스탬프 도입 직전 릴리스) 로 간주한다.
  부재 ⇒ 전체 마이그레이션 체인을 베이스라인부터 실행. 모든 스텝이 멱등이라
  갓 받은 fresh 설치에 돌려도 스탬프만 찍히고 끝난다.

소비자:
  - migrations 엔진 (read/write).
  - Heron.py --check / --migrate.
  - builder._load_config (빌드 step 1 의 버전 미스매치 경고; 읽기 전용).
"""
from pathlib import Path
from typing import Optional

# 스탬프 파일이 없을 때 가정하는 스키마 버전. 스탬프가 존재하지 않던 마지막
# 릴리스(v1.5.3). 부재 ⇒ 여기서부터 전체 체인 실행 (스텝이 모두 멱등이라
# fresh 설치는 결과적으로 no-op + 스탬프만 기록).
BASELINE_VERSION = '1.5.3'

HERON_DIR_NAME = '.heron'
VERSION_FILE_NAME = 'version'


def heron_dir(base) -> Path:
    """``<base>/user/.heron`` — Heron 인스턴스 상태 디렉터리."""
    return Path(base) / 'user' / HERON_DIR_NAME


def version_file(base) -> Path:
    """``<base>/user/.heron/version`` — 스키마 버전 스탬프 파일."""
    return heron_dir(base) / VERSION_FILE_NAME


def parse_version(v) -> Optional[tuple]:
    """'1.6.0' → (1, 6, 0). dotted-int 가 아니면 None.

    선행 'v' 허용, '-'/'+' 뒤의 pre-release/build 접미는 무시.
    """
    if not isinstance(v, str):
        return None
    s = v.strip().lstrip('vV')
    s = s.split('-', 1)[0].split('+', 1)[0]
    if not s:
        return None
    out = []
    for p in s.split('.'):
        if not p.isdigit():
            return None
        out.append(int(p))
    return tuple(out) if out else None


def compare(a: str, b: str) -> int:
    """semver 비교: a<b → -1, a==b → 0, a>b → 1 (짧은 쪽은 0 으로 패딩)."""
    pa = parse_version(a) or ()
    pb = parse_version(b) or ()
    n = max(len(pa), len(pb))
    pa = pa + (0,) * (n - len(pa))
    pb = pb + (0,) * (n - len(pb))
    return (pa > pb) - (pa < pb)


def read_schema_version(base) -> str:
    """user/.heron/version 을 읽는다. 부재/공백/형식오류면 BASELINE_VERSION."""
    try:
        txt = version_file(base).read_text(encoding='utf-8')
    except OSError:
        return BASELINE_VERSION
    line = (txt.splitlines() or [''])[0].strip().lstrip('vV').strip()
    return line if parse_version(line) is not None else BASELINE_VERSION


def write_schema_version(base, version: str) -> None:
    """스탬프를 원자적으로 기록 (필요 시 user/.heron/ 생성).

    bytes 로 쓴다 — write_text 는 Windows 텍스트 모드에서 ``\\n`` → ``\\r\\n``
    번역을 해 커밋되는 스탬프 파일이 플랫폼마다 달라진다. 항상 LF 로 고정해
    체크아웃·OS 무관하게 동일한 한 줄 파일을 만든다.
    """
    heron_dir(base).mkdir(parents=True, exist_ok=True)
    f = version_file(base)
    tmp = f.with_suffix('.tmp')
    tmp.write_bytes((version.strip() + '\n').encode('utf-8'))
    tmp.replace(f)

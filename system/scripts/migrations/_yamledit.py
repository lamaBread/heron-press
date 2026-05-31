"""마이그레이션용 site.yaml 줄단위 편집 (v1.6.0 신설).

site.yaml 은 사람이 손으로 단 주석·키 순서·`|` 블록이 가득하다. yaml_parser
는 읽기 전용(덤퍼 없음)이고, parse→re-dump 왕복은 그 모든 것을 파괴한다.
그래서 마이그레이션은 site.yaml 을 *텍스트* 로 편집한다 — 건드리지 않는 부분은
그대로 보존하는 외과적 줄 연산.

다루는 범위는 **톱레벨(컬럼 0) 키** 뿐이다 (폐기 키 제거·스탬프류가 전부
톱레벨). 중첩 키는 설계상 범위 밖.
"""
import re
from pathlib import Path

_KEY_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)\s*:')


def _top_level_key(line: str):
    """줄이 컬럼 0 의 ``key:`` 이면 키 이름, 아니면 None.

    들여쓰기(블록 내부)·주석·리스트 항목·빈 줄은 None.
    """
    if not line or line[0] in (' ', '\t', '#', '-'):
        return None
    m = _KEY_RE.match(line)
    return m.group(1) if m else None


def has_key(text: str, key: str) -> bool:
    """톱레벨에 ``key:`` 가 있는가."""
    return any(_top_level_key(ln) == key for ln in text.splitlines())


def remove_key(text: str, key: str):
    """톱레벨 ``key: ...`` 항목과 그 키가 소유한 줄(이어지는 들여쓰기 블록)을
    제거한다. 앞뒤 주석은 건드리지 않는다 (다른 키의 문서 주석을 먹지 않도록).

    반환: (new_text, removed: bool).

    소유 범위:
      key 줄 + 그 뒤로 *들여쓰기된*(공백/탭 시작) 줄들이 이어지는 구간.
      다음 컬럼 0 줄(다른 키/주석/빈 줄)을 만나면 멈춘다. 즉
        reserved_slugs: [a, b]          → 한 줄 제거
        reserved_slugs:\n  - a\n  - b   → 키 + 들여쓰기 리스트 항목 제거
      둘 다 안전하게 처리된다.
    """
    lines = text.splitlines(keepends=True)
    out = []
    removed = False
    i = 0
    n = len(lines)
    while i < n:
        raw = lines[i]
        stripped = raw.rstrip('\n').rstrip('\r')
        if _top_level_key(stripped) == key:
            removed = True
            i += 1
            # 이어지는 들여쓰기 블록(공백/탭 시작) 흡수. 빈 줄·주석·다른
            # 톱레벨 키는 흡수하지 않는다.
            while i < n:
                nxt = lines[i].rstrip('\n').rstrip('\r')
                if nxt and nxt[0] in (' ', '\t'):
                    i += 1
                    continue
                break
            continue
        out.append(raw)
        i += 1
    return ''.join(out), removed


def read_preserving(path) -> str:
    """파일을 개행 번역 없이 읽는다 (CRLF/LF 원본을 문자열에 그대로 보존).

    ``Path.read_text`` 는 universal-newline 이라 ``\\r\\n``·``\\r`` 을 읽는 즉시
    ``\\n`` 으로 바꾼다 — 그 뒤 무엇을 쓰든 개행은 이미 LF 로 뭉개진 상태다.
    bytes 로 읽어 디코드하면 원본 개행이 살아 있어, remove_key(keepends) →
    atomic_write(bytes) 전 구간이 LF·CRLF 어느 쪽이든 그대로 보존한다.
    """
    return Path(path).read_bytes().decode('utf-8')


def atomic_write(path, data: str) -> None:
    """temp → rename 으로 원자적 쓰기 (같은 디렉터리).

    bytes 로 쓴다 — ``Path.write_text`` 는 플랫폼 텍스트 모드라 Windows 에서
    ``\\n`` 을 ``\\r\\n`` 으로 번역해 사용자 파일의 개행 방식을 통째로 뒤집는다
    (LF 원본 → 전부 CRLF). ``remove_key`` 가 ``splitlines(keepends=True)`` 로
    원본 개행을 보존하므로, 쓰기 단계도 번역 없이 그대로 내보내야 LF 원본은
    LF·CRLF 원본은 CRLF 로 남아 "건드린 줄만 바뀌는" 외과적 편집이 성립한다.
    """
    p = Path(path)
    tmp = p.with_name(p.name + '.heron_tmp')
    tmp.write_bytes(data.encode('utf-8'))
    tmp.replace(p)

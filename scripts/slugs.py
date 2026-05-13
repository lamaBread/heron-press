"""폴더명 → URL slug 변환.

v0.4.0 변경:
  - _meta.yaml 슬러그 오버라이드 기능 제거. 한국어 폴더명도 결정론적으로
    slug 가 만들어지므로 오버라이드 메커니즘 자체가 불필요.
  - 비ASCII 문자가 포함된 폴더명은 빌드 시 경고를 띄우고, 각 비ASCII 문자를
    소문자 4자리 16진수 코드포인트로 자동 치환한다. 이후 기존 v0.3.2 의
    5단계 (NFKD → 허용문자 필터 → 괄호 제거 → 공백/하이픈 축약 → strip/lower)
    를 그대로 통과시킨다.

  예: '블로그' 폴더 → 'be94-b85c-adf8'
  사용자에게는 'Articles/ 폴더명은 가급적 ASCII 로 작성하세요' 라는 워닝이
  매 빌드마다 출력된다.
"""
import re
import unicodedata


_HAS_NON_ASCII_RE = re.compile(r'[^\x00-\x7f]')


def has_non_ascii(name: str) -> bool:
    return bool(_HAS_NON_ASCII_RE.search(name))


def _escape_non_ascii(name: str) -> str:
    """비ASCII 문자를 '<hex>-' 로 치환 (Hangul U+AC00 등 → 'ac00-')."""
    parts = []
    for ch in name:
        if ord(ch) < 128:
            parts.append(ch)
        else:
            parts.append(f'{ord(ch):04x}-')
    return ''.join(parts)


def category_slug_from_name(name: str) -> str:
    """폴더명 → URL slug. v0.4.0 (5-step + non-ASCII pre-escape).

    1. 비ASCII 문자 → 4자리 hex codepoint + '-'
    2. NFKD 정규화
    3. [A-Za-z0-9 \\-()] 만 유지
    4. 괄호 제거
    5. 공백/연속 하이픈 → 단일 '-', 끝의 '-' 제거, 소문자화
    """
    s = _escape_non_ascii(name)
    s = unicodedata.normalize('NFKD', s)
    s = re.sub(r"[^A-Za-z0-9 \-()]", '', s)
    s = s.replace('(', '').replace(')', '')
    s = re.sub(r'[\s\-]+', '-', s)
    s = s.strip('-')
    return s.lower()


def is_underscore_path(p, base) -> bool:
    """True if any segment in path (relative to base) starts with '_'."""
    try:
        rel = p.relative_to(base)
    except ValueError:
        rel = p
    return any(part.startswith('_') for part in rel.parts)

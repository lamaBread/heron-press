"""폴더명 → URL slug 변환.

v0.8.3 변경:
  - 빌드 제외 접두 일원화. 기존 `is_underscore_path` (`_` 접두만) 를
    `is_excluded_path` 로 일반화하고 단일-구성요소용 `is_excluded_name`
    헬퍼를 신설. 제외 접두 = `_` (작성자가 의도적으로 비공개·편집 중) +
    `.` (OS/VCS 가 만드는 숨김 — `.git` · `.DS_Store`, 그리고 작성자가
    "숨겼다" 고 믿는 `.draft` 등). 두 접두를 한 규칙으로 다뤄, 숨겼다고
    여기는 폴더가 글·카테고리·자산으로 실수 공개되는 길을 막는다. 정본
    Articles 에는 `.` 접두 항목이 없어 산출물 byte 영향 0.

v0.4.5 변경:
  - 비ASCII 폴더명 경고 메시지를 더 명시적으로 보강 (이 메시지는
    builder._build_category_tree 에서 출력됨). 사용자가 빌드 콘솔에서
    *어떤 폴더의 어떤 hex slug 가 자동 생성되었는지* 를 한눈에 보고,
    ASCII rename 을 검토할 수 있도록 한다.

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


# v0.8.3: 빌드 제외 폴더/파일 접두. '_' = 작성자가 의도적으로 비공개
# (편집 중·초안), '.' = OS·VCS 숨김 (.git · .DS_Store · 작성자가 "숨겼다"
# 고 믿는 .draft 등). 두 접두를 같은 규칙으로 다룬다 (스캔·nav·자산 동기화
# 가 모두 이 한 곳을 본다).
_EXCLUDED_PREFIXES = ('_', '.')


def is_excluded_name(name: str) -> bool:
    """단일 경로 구성요소가 빌드 제외 대상인지 (`_` / `.` 접두)."""
    return name.startswith(_EXCLUDED_PREFIXES)


def is_excluded_path(p, base) -> bool:
    """base 기준 상대경로의 한 세그먼트라도 빌드 제외 접두면 True.

    v0.8.3: 구 `is_underscore_path` (`_` 만) 의 일반화 — `_`·`.` 둘 다.
    """
    try:
        rel = p.relative_to(base)
    except ValueError:
        rel = p
    return any(is_excluded_name(part) for part in rel.parts)

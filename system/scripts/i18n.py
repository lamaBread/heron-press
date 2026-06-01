"""로케일 문자열 lookup — 빌드/CLI 메시지 + 사이트 chrome (v1.9.0 i18n 신설).

로케일 팩은 ``system/locales/<locale>/*.yaml`` 에 **플랫 닷(dot) 키 → 인용
문자열** 형태로 둔다 (예: ``site.search.placeholder: "검색"``). 한 로케일
폴더의 모든 ``*.yaml`` 조각을 머지한다 (조각 분리는 표면별 동시 작업 충돌을
피하기 위한 것 — admin/site/build/cli). ``ko`` 가 정본 겸 모든 로케일의 폴백
이며, 키가 없으면 키 문자열 자체를 돌려 출력이 절대 빈칸이 되지 않게 한다.

로케일 파일 규칙 (v1.9.1 — PHP i18n.php 와 **바이트 동일** 파서):
  - 한 줄 = ``키: "값"`` (또는 ``'값'``). 키는 닷 구분, 콜론/샵 없음.
  - 줄 시작 ``#`` 은 주석.
  - escape: **큰따옴표 값** 안에서 ``\\"`` ``\\\\`` ``\\n`` ``\\t`` 를 해석한다.
    그 외 ``\\x`` 는 백슬래시째 보존. **작은따옴표 값** 은 리터럴(해석 없음).
  - 일반 YAML(yaml_parser.yaml_load)이 아니라 이 전용 파서를 쓰는 이유: PHP
    측 admin UI 와 같은 결과를 보장하려면(번역 누수 방지) 두 구현의 파싱
    의미가 정확히 같아야 한다. yaml_load 는 true/false/정수 강제 등 추가
    의미가 있어 미세하게 어긋날 수 있다.

프로그램에는 **독립된 로케일 선택자가 둘** 있다:
  - **사이트 언어** (``site.yaml: lang``) — dist/ 에 빌드 시점에 구워지는
    방문자 chrome (Surface 1). 결정적 빌드 유지를 위해 런타임 lookup 이
    아니라 빌드 때 치환한다.
  - **도구 언어** (``user/.heron/locale``) — 운영자가 보는 빌드/CLI 메시지
    (Surface 3) 와 Pond admin UI (Surface 2, PHP 측 i18n.php 가 담당).

소비자:
  - builder.py — 사이트 chrome 토큰 치환(사이트 언어, site_tr) + 빌드 경고
    (도구 언어, tool_tr). 두 로케일을 동시에 쓰므로 ``Translator`` 인스턴스.
  - Heron.py / deploy.py / update.py / rclone_bin.py / migrations — 운영자
    대면 CLI 메시지(항상 도구 언어). PHP 의 전역 ``t()`` 처럼 **모듈 전역**
    번역기를 ``init()`` 으로 한 번 적재하고 ``i18n.t()`` 로 조회한다 (깊게
    중첩된 순수 함수에 번역기를 인자로 엮지 않기 위함, cli.* 키).
"""
import re
from pathlib import Path

from .version import heron_dir

# system/locales — 이 파일(system/scripts/i18n.py) 기준 부모의 부모/locales.
LOCALES_DIR = Path(__file__).resolve().parent.parent / 'locales'
CANONICAL = 'ko'
TOOL_LOCALE_FILE = 'locale'

# PHP i18n_load_pack 과 동일한 키:값 분리 정규식 (키에 콜론/샵 불가).
_KEY_LINE = re.compile(r'^([^:#]+?):\s*(.*)$')


def _unescape(s: str) -> str:
    r"""큰따옴표 값의 escape 해석: ``\"``→``"``, ``\\``→``\``, ``\n``→개행,
    ``\t``→탭. 그 외 ``\x`` 는 백슬래시째 보존. (PHP i18n_unescape 와 동일.)"""
    out = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == '\\' and i + 1 < n:
            nx = s[i + 1]
            if nx == 'n':
                out.append('\n'); i += 2; continue
            if nx == 't':
                out.append('\t'); i += 2; continue
            if nx == '"':
                out.append('"'); i += 2; continue
            if nx == '\\':
                out.append('\\'); i += 2; continue
            out.append(c)   # 알 수 없는 escape — 백슬래시 보존
            i += 1
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def _unquote(s: str) -> str:
    """양끝 같은 따옴표면 한 겹 제거. 큰따옴표는 escape 해석, 작은따옴표는
    리터럴. (PHP i18n_unquote 와 바이트 동일.)"""
    if len(s) >= 2:
        a, b = s[0], s[-1]
        if a == '"' and b == '"':
            return _unescape(s[1:-1])
        if a == "'" and b == "'":
            return s[1:-1]
    return s


def _load_pack(locale: str) -> dict:
    """``<locales>/<locale>/*.yaml`` 들을 머지한 플랫 {key: str} 맵.

    PHP i18n_load_pack 과 동일한 줄단위 규칙으로 파싱한다 (전용 파서).
    """
    out: dict = {}
    d = LOCALES_DIR / locale
    if d.is_dir():
        for f in sorted(d.glob('*.yaml')):
            try:
                text = f.read_text(encoding='utf-8')
            except OSError:
                continue
            for line in text.splitlines():
                if line == '':
                    continue
                lt = line.lstrip()
                if not lt or lt[0] == '#':
                    continue
                m = _KEY_LINE.match(line)
                if not m:
                    continue
                out[m.group(1).strip()] = _unquote(m.group(2).strip())
    return out


class Translator:
    """한 로케일에 묶인 문자열 조회기. 폴백 체인: locale → ko → 키 문자열."""

    def __init__(self, locale: str = CANONICAL):
        self.locale = locale or CANONICAL
        self._fallback = _load_pack(CANONICAL)
        self._strings = (self._fallback if self.locale == CANONICAL
                         else _load_pack(self.locale))

    def t(self, key: str, **kw) -> str:
        """키의 로케일 문자열. ``kw`` 가 있으면 ``{name}`` 자리표시자 치환.

        키가 없으면 폴백(ko) → 그래도 없으면 키 문자열 자체를 돌려준다.
        ``.format`` 이 실패해도(자리표시자 불일치) 원문을 그대로 돌려 빌드가
        깨지지 않게 한다.
        """
        s = self._strings.get(key)
        if s is None:
            s = self._fallback.get(key, key)
        if not isinstance(s, str):
            s = str(s)
        if kw:
            try:
                return s.format(**kw)
            except (KeyError, IndexError, ValueError):
                return s
        return s


def load(locale: str = CANONICAL) -> Translator:
    return Translator(locale)


# ── 모듈 전역 번역기 (CLI/운영자 메시지용; PHP 전역 t() 미러) ──────────
#
# Heron.py main() 이 시작에서 init() 으로 도구 언어를 한 번 적재하면, 이후
# deploy/update/rclone/migrations 가 i18n.t() 로 조회한다. init 전 기본은 ko —
# 직접 호출(테스트)도 ko 폴백으로 안전. 빌더는 두 로케일을 동시에 쓰므로 이
# 전역이 아니라 Translator 인스턴스(site_tr/tool_tr)를 따로 쓴다.
_ACTIVE: Translator = Translator(CANONICAL)


def init(locale: str = CANONICAL) -> Translator:
    """모듈 전역 번역기를 도구 언어로 (재)적재. 적재된 번역기를 반환."""
    global _ACTIVE
    _ACTIVE = Translator(locale or CANONICAL)
    return _ACTIVE


def init_from_base(base) -> Translator:
    """``user/.heron/locale`` 로 전역 번역기를 적재 (없으면 ko)."""
    return init(read_tool_locale(base))


def active() -> Translator:
    """현재 전역 번역기."""
    return _ACTIVE


def t(key: str, **kw) -> str:
    """전역 번역기로 조회 (CLI/운영자 메시지). init() 전이면 ko."""
    return _ACTIVE.t(key, **kw)


def read_tool_locale(base) -> str:
    """``user/.heron/locale`` 한 줄. 부재/공백/형식오류면 ``ko``."""
    try:
        txt = (heron_dir(base) / TOOL_LOCALE_FILE).read_text(encoding='utf-8')
    except OSError:
        return CANONICAL
    line = (txt.splitlines() or [''])[0].strip()
    return line or CANONICAL


def available_locales() -> list:
    """``system/locales/`` 아래 존재하는 로케일 폴더명 목록 (정렬)."""
    if not LOCALES_DIR.is_dir():
        return [CANONICAL]
    return sorted(p.name for p in LOCALES_DIR.iterdir() if p.is_dir())

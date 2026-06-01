"""로케일 문자열 lookup — 빌드/CLI 메시지 + 사이트 chrome (v1.9.0 i18n 신설).

로케일 팩은 ``system/locales/<locale>/*.yaml`` 에 **플랫 닷(dot) 키 → 인용
문자열** 형태로 둔다 (예: ``site.search.placeholder: "검색"``). 한 로케일
폴더의 모든 ``*.yaml`` 조각을 머지한다 (조각 분리는 표면별 동시 작업 충돌을
피하기 위한 것 — admin/site/build). ``ko`` 가 정본 겸 모든 로케일의 폴백이며,
키가 없으면 키 문자열 자체를 돌려 출력이 절대 빈칸이 되지 않게 한다.

프로그램에는 **독립된 로케일 선택자가 둘** 있다:
  - **사이트 언어** (``site.yaml: lang``) — dist/ 에 빌드 시점에 구워지는
    방문자 chrome (Surface 1). 결정적 빌드 유지를 위해 런타임 lookup 이
    아니라 빌드 때 치환한다.
  - **도구 언어** (``user/.heron/locale``) — 운영자가 보는 빌드/CLI 메시지
    (Surface 3) 와 Pond admin UI (Surface 2, PHP 측 i18n.php 가 담당).

소비자:
  - builder.py — 사이트 chrome 토큰 치환 (사이트 언어).
  - builder.py / deploy.py — 경고·abort·진행 메시지 (도구 언어).
"""
from pathlib import Path

from .yaml_parser import yaml_load
from .version import heron_dir

# system/locales — 이 파일(system/scripts/i18n.py) 기준 부모의 부모/locales.
LOCALES_DIR = Path(__file__).resolve().parent.parent / 'locales'
CANONICAL = 'ko'
TOOL_LOCALE_FILE = 'locale'


def _load_pack(locale: str) -> dict:
    """``<locales>/<locale>/*.yaml`` 들을 머지한 플랫 {key: str} 맵."""
    out: dict = {}
    d = LOCALES_DIR / locale
    if d.is_dir():
        for f in sorted(d.glob('*.yaml')):
            try:
                out.update(yaml_load(f.read_text(encoding='utf-8')))
            except OSError:
                pass
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

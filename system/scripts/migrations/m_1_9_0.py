"""마이그레이션 스텝 1.8.0 → 1.9.0 (v1.9.0 신설).

v1.9.0 은 **도구 다국어(언어팩)** 를 도입한다. Pond admin UI 와 빌드/CLI
메시지의 표시 언어를 ``user/.heron/locale`` 한 줄(BCP 47 코드, 예: ko / en)
로 고른다. 로케일 팩 자체는 프로그램 표면(``system/locales/``)에 들어 있어
자가 업데이트로 함께 교체된다 — 이 스텝이 손대는 user/ 측 산물은 *도구 언어
선택* 파일 하나뿐이다.

파일이 없으면 도구는 정본 ``ko`` 로 폴백하므로 이 스텝은 **시드 한 건** —
파일이 없을 때만 ``ko`` 로 만든다 (기존 사용자의 현재 한국어 UI 를 그대로
유지). 이미 있으면 no-op([] 반환) — 사용자가 고른 언어를 절대 덮어쓰지
않는다 (멱등).

왜 마이그레이션이 시드하나 (m_1_7_0 의 deploy.example.json 시드와 같은 이유):
  자가 업데이트 오버레이는 프로그램 표면(system/ + 진입점)만 교체하고
  ``user/`` 는 절대 건드리지 않는다. 따라서 **기존 사용자가 이 파일을 받는
  유일한 경로** 가 이 마이그레이션 시드다. 신규 clone 은 스키마 스탬프가 이미
  최신이라 체인이 안 돌지만, 그래도 파일 부재 시 ko 폴백이라 동작은 동일하다.
"""
from . import Change, Migration
from .. import version as _version

LOCALE_FILE_NAME = 'locale'
SEED_LOCALE = 'ko'


class Migration_1_9_0(Migration):
    from_version = '1.8.0'
    to_version = '1.9.0'
    summary = ('도구 다국어(언어팩) 도입 — 도구 언어 설정'
               '(user/.heron/locale) 시드 (정본 ko)')
    summary_key = 'cli.migrate.m190.summary'

    def _locale_file(self, base):
        return _version.heron_dir(base) / LOCALE_FILE_NAME

    def _change(self):
        return Change(
            path='user/.heron/locale',
            kind='create',
            detail=f'도구 언어 설정 시드 ({SEED_LOCALE})',
            detail_key='cli.migrate.m190.seed',
            detail_params={'locale': SEED_LOCALE},
        )

    def plan(self, base):
        if self._locale_file(base).exists():
            return []
        return [self._change()]

    def apply(self, base):
        f = self._locale_file(base)
        if f.exists():
            return []
        f.parent.mkdir(parents=True, exist_ok=True)
        # LF 고정 한 줄 (version 스탬프와 동일 규칙 — 플랫폼 무관 동일 바이트).
        f.write_bytes((SEED_LOCALE + '\n').encode('utf-8'))
        return [self._change()]

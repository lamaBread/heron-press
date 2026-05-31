"""마이그레이션 스텝 1.5.3 → 1.6.0 (v1.6.0 신설).

v1.6.0 은 마이그레이션 시스템 *자체* 를 도입하는 릴리스다. 그래서 이 첫 스텝의
콘텐츠 편집은 가볍다 — v1.4.0 이 코드 상수로 승격하며 폐기한 다섯 site.yaml
키(README §11)가 옛 설정에 남아 있으면 정리한다. 스키마 스탬프 기록은 엔진이
중앙에서 하므로 여기선 다루지 않는다.

데모 site.yaml 에는 이 키들이 없으므로 apply() 는 no-op([] 반환)이고, 그래서
이 스텝은 멱등이다 — 한 번 정리된(또는 처음부터 없는) 트리에 다시 돌려도
변경이 없다.
"""
from pathlib import Path

from . import Change, Migration
from . import _yamledit

# v1.4.0 이 site.yaml → 코드 상수로 승격하며 폐기한 다섯 키. 옛 설정(≤ v1.3.x)에
# 남아 있을 수 있고, 파서는 조용히 무시하지만(README §11) 마이그레이션이 정리해
# 파일이 현재 스키마를 반영하도록 한다.
RETIRED_SITE_KEYS = (
    'reserved_slugs',
    'warn_on_underscore_ref',
    'warn_on_missing_asset',
    'error_404_title',
    'search_title',
)


class Migration_1_6_0(Migration):
    from_version = '1.5.3'
    to_version = '1.6.0'
    summary = ('Heron 마이그레이션 시스템 도입 — 스키마 스탬프'
               '(user/.heron/version) + v1.4.0 폐기 site.yaml 키 정리')

    def _site_yaml(self, base) -> Path:
        return Path(base) / 'user' / 'site.yaml'

    def plan(self, base):
        return self._run(base, dry=True)

    def apply(self, base):
        return self._run(base, dry=False)

    def _run(self, base, *, dry):
        changes = []
        sy = self._site_yaml(base)
        if not sy.is_file():
            return changes
        original = sy.read_text(encoding='utf-8')
        text = original
        removed = []
        for key in RETIRED_SITE_KEYS:
            text, did = _yamledit.remove_key(text, key)
            if did:
                removed.append(key)
        if removed:
            changes.append(Change(
                path='user/site.yaml',
                kind='edit',
                detail='v1.4.0 폐기 키 제거: ' + ', '.join(removed),
            ))
            if not dry and text != original:
                _yamledit.atomic_write(sy, text)
        return changes

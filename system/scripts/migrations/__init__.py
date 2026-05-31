"""스키마 마이그레이션 엔진 (v1.6.0 신설).

각 마이그레이션은 *user/* 트리(site.yaml / meta.yaml / templates ...)를 한
스키마 버전에서 다음 버전으로 옮기는 작은 선언적 스텝이다. system/ 은 업그레
이드 시 통째 교체되므로 마이그레이션은 프로그램 코드를 절대 건드리지 않는다 —
오직 사용자 소유의 콘텐츠/설정만.

마이그레이션 한 스텝:
  - from_version / to_version : 잇는 간선 (dotted 버전 문자열).
  - summary                   : 한 줄 사람용 설명.
  - plan(base)  -> list[Change]: dry-run. 쓰기 없이 편집 내용을 기술.
  - apply(base) -> list[Change]: user/ 에 편집 수행. 변경 내역 반환.

apply() 는 **멱등**이어야 한다 — 이미 적용된 트리에 다시 돌리면 no-op([] 반환).
덕분에 fresh 설치도 전체 체인을 무해하게 돌릴 수 있다 (스탬프만 찍힘).

MIGRATIONS 는 순서 레지스트리. ``run()`` 이 기록된 스키마 버전 → 목표(프로그램)
버전까지의 체인을 계산해 순서대로 실행한다. 스탬프 기록은 엔진이 중앙에서 한다
(각 마이그레이션은 콘텐츠 편집에만 집중).
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from .. import version as _version


@dataclass
class Change:
    """마이그레이션이 만든(또는 만들) 변경 한 건.

    path   — base 기준 상대 경로 (예: 'user/site.yaml').
    kind   — 'edit' | 'create' | 'delete' | 'stamp'.
    detail — 한 줄 사람용 설명.
    """
    path: str
    kind: str
    detail: str


class Migration:
    """마이그레이션 스텝 베이스. 구체 스텝이 from/to/summary 와 plan/apply 를
    오버라이드한다."""
    from_version: str = ''
    to_version: str = ''
    summary: str = ''

    def plan(self, base) -> List[Change]:
        return []

    def apply(self, base) -> List[Change]:
        return []


def _build_registry() -> List[Migration]:
    """구체 마이그레이션을 모아 to_version 오름차순으로 정렬해 반환.

    여기서 import 하므로 m_*.py 가 ``from . import Migration, Change`` 로
    이 모듈(부분 초기화 상태)을 다시 import 해도 순환이 풀린다 — Migration/
    Change 가 이 호출 전에 이미 정의돼 있기 때문 (모듈 끝에서 호출).
    """
    from .m_1_6_0 import Migration_1_6_0
    steps = [Migration_1_6_0()]
    steps.sort(key=lambda m: _version.parse_version(m.to_version) or ())
    return steps


def plan_chain(from_version: str, to_version: str) -> List[Migration]:
    """from_version 너머이면서 to_version 이하인 종점을 가진 스텝들 (순서대로).

    스텝 (a→b) 는 현재가 b 에 못 미쳤고(b 가 현재보다 위) b 가 목표 이하일 때
    적용된다. 간선이 연속 체인을 이룬다는 전제 — 현재 한 스텝뿐이라 자명.
    """
    return [m for m in MIGRATIONS
            if _version.compare(from_version, m.to_version) < 0
            and _version.compare(m.to_version, to_version) <= 0]


def run(base, *, target: str, dry_run: bool = False,
        log: Optional[Callable[[str], None]] = None) -> dict:
    """기록된 스키마 버전 → target 까지 마이그레이션 체인을 실행.

    dry_run=True 면 어떤 파일도 쓰지 않고 plan() 만 모은다 (스탬프도 안 찍음).
    실제 적용 시엔 체인을 순서대로 apply() 하고, 마지막에 스탬프를 target 으로
    기록한다 (업그레이드 = 콘텐츠 변경 0건이라도 스키마 도달 사실은 기록).

    반환: {from, to, dry_run, steps:[{from,to,summary,changes:[Change..]}],
           changes:[Change..], stamped:bool}.
    """
    base = Path(base)
    log = log or (lambda _m: None)
    current = _version.read_schema_version(base)
    steps_meta = []
    all_changes: List[Change] = []

    chain = plan_chain(current, target)
    log(f'현재 스키마: {current}  →  목표: {target}'
        + ('  (dry-run)' if dry_run else ''))
    if not chain:
        if _version.compare(current, target) == 0:
            log('이미 최신 스키마입니다 — 적용할 마이그레이션 없음.')
        else:
            log('적용할 마이그레이션 스텝이 없습니다.')

    for m in chain:
        log(f'  [{m.from_version} → {m.to_version}] {m.summary}')
        changes = m.plan(base) if dry_run else m.apply(base)
        for c in changes:
            log(f'      · {c.kind}: {c.path} — {c.detail}')
        if not changes:
            log('      · (변경 없음 — 이미 반영됨)')
        all_changes.extend(changes)
        steps_meta.append({
            'from': m.from_version, 'to': m.to_version,
            'summary': m.summary, 'changes': changes,
        })

    stamped = False
    if not dry_run and _version.compare(current, target) < 0:
        _version.write_schema_version(base, target)
        stamped = True
        log(f'스탬프 기록: user/.heron/version = {target}')

    return {
        'from': current, 'to': target, 'dry_run': dry_run,
        'steps': steps_meta, 'changes': all_changes, 'stamped': stamped,
    }


MIGRATIONS: List[Migration] = _build_registry()

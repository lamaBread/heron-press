"""마이그레이션 스텝 1.6.2 → 1.7.0 (v1.7.0 신설).

v1.7.0 은 rclone 기반 dist 배포 서브시스템을 추가한다. 사용자 콘텐츠/스키마
구조 자체는 바뀌지 않으므로 이 스텝은 **사실상 시드 한 건** — 배포 설정 견본
``user/.heron/deploy.example.json`` 이 없으면 만든다.

왜 마이그레이션이 시드하나:
  견본은 저장소에 커밋되어 신규 clone 은 그대로 받지만, 자가 업데이트 오버레이
  는 프로그램 표면(system/ + 진입점)만 교체하고 ``user/`` 는 절대 건드리지
  않는다. 따라서 **기존 사용자가 업데이트로 견본을 받는 유일한 경로**가 이
  마이그레이션 시드다. 신규 clone 은 이미 파일이 있어 no-op([] 반환) — 멱등.

실값 ``deploy.json`` 은 절대 만들지 않는다 (사용자가 견본을 복사해 채움).
"""
from . import Change, Migration
from .. import deploy as _deploy


class Migration_1_7_0(Migration):
    from_version = '1.6.2'
    to_version = '1.7.0'
    summary = ('rclone 원클릭 배포 도입 — 배포 설정 견본'
               '(user/.heron/deploy.example.json) 시드')
    summary_key = 'cli.migrate.m170.summary'

    def _change(self):
        return Change(
            path='user/.heron/deploy.example.json',
            kind='create',
            detail='배포 설정 견본 생성 (실값 없는 스키마 플레이스홀더)',
            detail_key='cli.migrate.m170.seed',
        )

    def plan(self, base):
        # 견본이 이미 있으면 변경 없음 (멱등).
        if _deploy.example_path(base).exists():
            return []
        return [self._change()]

    def apply(self, base):
        created = _deploy.write_example(base)
        if not created:
            return []
        return [self._change()]

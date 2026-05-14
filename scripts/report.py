"""빌드 리포트 — 모든 경고/검증 실패를 모아 빌드 종료 시 한 번에 표시 (v0.5.5 신설).

설계 사상 — 본문 ↔ 메타데이터 분리 원칙 + fail-soft:
  v0.5.5 이전까지 빌더는 meta.yaml 속성 부족/형식 오류를 `die()` 로 처리해
  *첫 위반에서 빌드를 abort* 했다. 사용자가 여러 글의 meta.yaml 을 한꺼번에
  손보고 싶어도 한 글 고치고 빌드, 다시 한 글 고치고 빌드... 의 패턴을 반복
  해야 했다. v0.5.5 부터 정책 전환:

    - meta.yaml 의 필드 부족 / 빈 문자열 / 형식 오류는 **빌드를 중단시키지
      않는다**. 해당 글만 빌드 산출물에서 제외 (또는 부분 출력) 하고 리포트에
      기록한다.
    - 시스템 결함 (templates/ 못 찾음, Articles/ 없음, Pillow 미설치 등) 만
      `abort()` 로 빌드 중단. 콘텐츠 측 작성자의 실수와 시스템 측 결함을
      구분한다.
    - 빌드는 어떤 경우에도 끝까지 완성된다. 종료 시 터미널에 미완성 글
      목록을 몰아서 표시 — 사용자가 한 번에 모든 보완 지점을 파악.

분류:
  - issue (보완 필요): 작성자가 손봐야 할 글 단위 문제. 빌드는 계속 진행
    되지만 해당 글의 산출물이 부분적으로 누락될 수 있음.
    예: `seo.description` 필드가 빈 문자열, `tags` 가 list 가 아님,
       slug 중복, date 형식 오류 등.
  - warning (조언): 빌드 산출물은 정상이지만 사용자가 한 번 살펴볼 가치가
    있는 사항. 예: 비ASCII 폴더명 슬러그 변환, meta updated 가 파일 mtime
    보다 오래됨, 빈 카테고리 등.
  - abort (시스템 결함): 빌드 자체를 진행할 수 없는 상황. 이 경우만 즉시
    `sys.exit(1)`. 콘텐츠 작성자의 통제 밖이라 리포트로 모을 의미가 없음.

사용 패턴:
  - Builder 가 `self.report = BuildReport()` 를 보유.
  - die() / warn() 전역 함수는 v0.5.5 부터 빌더 메소드 `self._issue(...)` /
    `self._warning(...)` 로 라우팅. 시스템 결함만 `abort()` 호출 (즉시 종료).
  - 빌드 마지막 단계에서 `self.report.render()` 가 정렬된 리포트 출력.
"""
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ReportEntry:
    """리포트 한 항목.

    scope    — 'article' / 'category' / 'home' / 'site' / 'legacy-map'.
               글 단위 / 카테고리 단위 / 전역 메타 단위로 묶어 표시.
    target   — 무엇에 대한 항목인가. 보통 글의 slug 또는 카테고리 경로 (str).
    message  — 사람이 읽을 한 줄 설명.
    location — 관련 파일 경로 (있으면 표시).
    severity — 'issue' (보완 필요, 산출물 누락) / 'warning' (조언, 산출물 정상).
    """
    scope: str
    target: str
    message: str
    location: Optional[Path] = None
    severity: str = 'issue'


@dataclass
class BuildReport:
    """빌드 한 회의 모든 경고/문제를 모아두는 컬렉터.

    빌드 마지막 단계에서 `render()` 호출 시 stderr 에 정렬된 형태로 표시한다.
    아무 항목도 없으면 "보완 필요 없음" 메시지 한 줄. 항목이 있으면 글마다
    묶인 목록 + 끝에 요약 카운트.
    """
    entries: list = field(default_factory=list)

    # ── 등록 메소드 ────────────────────────────────────────

    def issue(
        self,
        scope: str,
        target: str,
        message: str,
        location: Optional[Path] = None,
    ):
        """글/카테고리 단위 보완 필요 항목. 빌드는 계속, 산출물 일부 누락 가능."""
        self.entries.append(ReportEntry(
            scope=scope, target=target, message=message,
            location=location, severity='issue',
        ))

    def warning(
        self,
        scope: str,
        target: str,
        message: str,
        location: Optional[Path] = None,
    ):
        """산출물은 정상이지만 사용자가 한 번 살펴볼 사항."""
        self.entries.append(ReportEntry(
            scope=scope, target=target, message=message,
            location=location, severity='warning',
        ))

    # ── 조회/카운트 ────────────────────────────────────────

    def issue_count(self) -> int:
        return sum(1 for e in self.entries if e.severity == 'issue')

    def warning_count(self) -> int:
        return sum(1 for e in self.entries if e.severity == 'warning')

    # ── 렌더 ───────────────────────────────────────────────

    def render(self, out=sys.stderr):
        """빌드 종료 시 리포트를 stderr 에 표시.

        구조:
          ── 보완이 필요한 글 / 카테고리 ──────────
          [issue]    {scope}:{target}
            - {message}
              ({location})
            ...

          ── 살펴볼 사항 ──────────────────────────
          [warning]  {scope}:{target}
            - {message}
            ...

          요약: 보완 필요 N건, 살펴볼 사항 M건.
        """
        issues = [e for e in self.entries if e.severity == 'issue']
        warnings = [e for e in self.entries if e.severity == 'warning']

        if not issues and not warnings:
            print('빌드 리포트: 보완 필요 / 살펴볼 사항 없음.', file=out)
            return

        if issues:
            print('', file=out)
            print('── 보완이 필요한 항목 (산출물 일부 누락 가능) ──', file=out)
            for header, grp in _group_by_target(issues):
                print(f'  {header}', file=out)
                for e in grp:
                    print(f'      - {e.message}', file=out)
                    if e.location:
                        print(f'        ({e.location})', file=out)

        if warnings:
            print('', file=out)
            print('── 살펴볼 사항 (산출물 정상) ──', file=out)
            for header, grp in _group_by_target(warnings):
                print(f'  {header}', file=out)
                for e in grp:
                    print(f'      - {e.message}', file=out)
                    if e.location:
                        print(f'        ({e.location})', file=out)

        print('', file=out)
        print(
            f'빌드 리포트 요약: 보완 필요 {self.issue_count()}건, '
            f'살펴볼 사항 {self.warning_count()}건.',
            file=out,
        )


def _group_by_target(entries: list) -> list:
    """리포트 항목을 (scope, target) 기준으로 그룹화 — 같은 글의 여러 issue 가
    한 헤더 아래 모이도록.

    헤더는 사람이 읽기 좋게 `[scope] target` 또는 `[scope]` (target 비어있는
    경우) 형태로 포맷. 입력 순서를 보존한다 (Python 3.7+ dict insertion order).
    """
    groups = {}
    for e in entries:
        header = f'[{e.scope}] {e.target}' if e.target else f'[{e.scope}]'
        groups.setdefault(header, []).append(e)
    return list(groups.items())


# ════════════════════════════════════════════════════════════════
# 시스템 결함 abort — 빌드를 즉시 중단할 때만 사용
# ════════════════════════════════════════════════════════════════

def abort(msg: str):
    """시스템 결함 시 즉시 종료. 콘텐츠 작성자가 통제할 수 없는 상황
    (템플릿 누락, Articles/ 디렉터리 없음, 외부 의존성 미설치 등) 만 해당.

    meta.yaml 의 속성 부족이나 형식 오류 같은 콘텐츠 측 문제는 abort 대신
    `BuildReport.issue(...)` 로 기록하고 빌드를 계속 진행한다.
    """
    print(f'[ABORT] {msg}', file=sys.stderr)
    print('빌드 중단 (시스템 결함).', file=sys.stderr)
    sys.exit(1)

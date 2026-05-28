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
    있는 사항. 예: 비ASCII 폴더명 슬러그 변환, 빈 카테고리 등.
  - abort (시스템 결함): 빌드 자체를 진행할 수 없는 상황. 이 경우만 즉시
    `sys.exit(1)`. 콘텐츠 작성자의 통제 밖이라 리포트로 모을 의미가 없음.

사용 패턴:
  - Builder 가 `self.report = BuildReport()` 를 보유.
  - 콘텐츠 결함은 빌더 메소드 `self._issue(...)` / `self._warning(...)` 로
    라우팅. 시스템 결함만 `abort()` 호출 (즉시 종료).
  - 빌드 마지막 단계에서 `self.report.render()` 가 정렬된 리포트 출력.

이력 주의 (v0.8.2): 위 per-Builder 라우팅은 v0.5.5 에 *설계·문서화* 됐으나
구현은 v0.6.5~v0.8.1 동안 모듈 전역 `_report` (builder.py) + build() 진입
자동 reset 이었다. v0.8.2 에서 비로소 이 docstring 대로 `self.report` +
`self._issue`/`self._warning` 로 실구현 (모듈 전역·전역 함수 폐지) — 두
Builder 가 리포트를 공유하지 않아 동시 빌드가 가능하다.
"""
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ReportEntry:
    """리포트 한 항목.

    scope    — 'article' / 'category' / 'home' / 'site'.
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

    v1.4.0: php_built — `index.php` 로 떨어진 글의 slug 목록 (등록 순). issue/
    warning 이 아니라 *의도된 출력 보고* — 예상 사용자가 웹 개발자이므로
    PHP fallback 은 시스템 결함이 아니라 작성 의도. 그래도 어느 글이 .php
    로 떨어졌는지 한눈에 보기 위해 별도 카테고리로 표시한다 (render() 의
    "── PHP 로 빌드된 글 ──" 절, render_markdown() 의 "## PHP 로 빌드된 글"
    절 — issue/warning 절과 같은 톤이되 다른 의미라는 점을 위치·라벨로 구분).
    """
    entries: list = field(default_factory=list)
    php_built: list = field(default_factory=list)

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

    # v1.4.0: PHP 로 빌드된 글 등록.
    def note_php_built(self, slug: str):
        """글이 `index.php` 로 떨어졌음을 기록 (중복 자동 제거, 등록 순 보존).

        호출은 글 1건당 1회 (cache hit/miss 양쪽 모두). 슬러그가 이미 있으면
        no-op. 정렬은 빌드 종료 시 render() / render_markdown() 가 표시 단계
        에서 (사람 가독성 위해) slug 알파벳순으로 일괄 정렬한다.
        """
        if slug and slug not in self.php_built:
            self.php_built.append(slug)

    # ── 조회/카운트 ────────────────────────────────────────

    def issue_count(self) -> int:
        return sum(1 for e in self.entries if e.severity == 'issue')

    def warning_count(self) -> int:
        return sum(1 for e in self.entries if e.severity == 'warning')

    def php_built_count(self) -> int:
        return len(self.php_built)

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
        php_built = sorted(set(self.php_built))

        if not issues and not warnings and not php_built:
            print('빌드 리포트: 보완 필요 / 살펴볼 사항 / PHP 빌드 글 없음.',
                  file=out)
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

        # v1.4.0: PHP 로 빌드된 글 목록 — issue/warning 이 아닌 의도된 출력
        # 보고. 예상 사용자가 웹 개발자라 PHP fallback 은 결함이 아니지만
        # "어느 글이 .php 인지" 가시화가 운영 가치.
        if php_built:
            print('', file=out)
            print(f'── PHP 로 빌드된 글 ({len(php_built)}건) ──', file=out)
            for slug in php_built:
                print(f'  /{slug}/  (dist/{slug}/index.php)', file=out)

        print('', file=out)
        summary = (
            f'빌드 리포트 요약: 보완 필요 {self.issue_count()}건, '
            f'살펴볼 사항 {self.warning_count()}건'
        )
        if php_built:
            summary += f', PHP 빌드 {len(php_built)}건'
        summary += '.'
        print(summary, file=out)

    # ── 마크다운 직렬화 (v0.7.2) ───────────────────────────

    def render_markdown(self) -> str:
        """render() 와 같은 그룹화/정렬을 마크다운 문자열로 (v0.7.2).

        터미널에만 뜨던 리포트를 build-report.md 로도 남기기 위한 직렬화.
        구조는 render() 와 1:1 — issue 절 → warning 절 → 요약. 항목이 하나도
        없으면 한 줄 안내. 반환값은 호출자 (Builder._write_build_report) 가
        문서의 한 블록으로 끼워 넣는다 (앞뒤 빈 줄은 호출자가 관리).

        message 는 사람이 쓴 한국어 산문이라 별도 escape 하지 않고 (render()
        와 parity), location 만 인라인 코드 (`...`) 로 감싸 경로가 깨지지
        않게 한다.
        """
        issues = [e for e in self.entries if e.severity == 'issue']
        warnings = [e for e in self.entries if e.severity == 'warning']
        php_built = sorted(set(self.php_built))

        if not issues and not warnings and not php_built:
            return '_빌드 리포트: 보완 필요 / 살펴볼 사항 / PHP 빌드 글 없음._'

        out = []

        def _emit_group(entries: list):
            for header, grp in _group_by_target(entries):
                out.append(f'### {header}')
                out.append('')
                for e in grp:
                    out.append(f'- {e.message}')
                    if e.location:
                        out.append(f'  - 위치: `{e.location}`')
                out.append('')

        if issues:
            out.append('## 보완이 필요한 항목 (산출물 일부 누락 가능)')
            out.append('')
            _emit_group(issues)

        if warnings:
            out.append('## 살펴볼 사항 (산출물 정상)')
            out.append('')
            _emit_group(warnings)

        # v1.4.0: PHP 로 빌드된 글 목록.
        if php_built:
            out.append(f'## PHP 로 빌드된 글 ({len(php_built)}건)')
            out.append('')
            out.append('_의도된 출력 — `imgBox`/`imgSlideBox` 외 살아 있는 PHP '
                       '구문이 있는 글은 `index.php` 로 떨어진다. 시스템 결함이 '
                       '아니라 작성자(웹 개발자)의 명시적 선택._')
            out.append('')
            for slug in php_built:
                out.append(f'- `/{slug}/` → `dist/{slug}/index.php`')
            out.append('')

        summary = (
            f'> **빌드 리포트 요약**: 보완 필요 {self.issue_count()}건, '
            f'살펴볼 사항 {self.warning_count()}건'
        )
        if php_built:
            summary += f', PHP 빌드 {len(php_built)}건'
        summary += '.'
        out.append(summary)
        return '\n'.join(out)


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

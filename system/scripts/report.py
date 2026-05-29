"""Build report — collects every warning/validation failure and shows them all
at the end of the build.

Design — content/metadata separation + fail-soft:
  Missing fields, empty strings, or format errors in meta.yaml do NOT abort the
  build; the affected article is excluded (or partially emitted) and recorded in
  the report. Only system faults (templates/ missing, no Articles/, Pillow not
  installed, ...) call abort(). The build always runs to completion and lists
  every follow-up point at once.

Categories:
  - issue   — author must fix; build continues but the article's output may be
              partially missing (e.g. empty seo.description, bad date, duplicate
              slug).
  - warning — output is fine, but worth a look (e.g. non-ASCII folder slug
              conversion, empty category).
  - abort   — system fault that prevents building at all; the only case that
              exits immediately.

Usage:
  Builder holds `self.report = BuildReport()`. Content faults route through the
  builder methods `self._issue(...)` / `self._warning(...)`; only system faults
  call abort(). The final build step calls `self.report.render()`.
"""
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ReportEntry:
    """One report item.

    scope    — 'article' / 'category' / 'home' / 'site'.
    target   — what the item is about (usually an article slug or category path).
    message  — one-line human-readable description.
    location — related file path, if any.
    severity — 'issue' (needs fixing, output may be missing) / 'warning' (output fine).
    """
    scope: str
    target: str
    message: str
    location: Optional[Path] = None
    severity: str = 'issue'


@dataclass
class BuildReport:
    """Collector for all warnings/problems of a single build.

    `render()` (called in the final build step) prints a grouped, sorted list to
    stderr; `render_markdown()` serializes the same for build-report.md. With no
    entries it emits a single "nothing to do" line.

    php_built lists the slugs that fell back to `index.php`. This is not an
    issue/warning but an *intended-output* report: the expected user is a web
    developer, so a PHP fallback is a deliberate choice, not a fault — it is
    shown separately (own section, distinct label) just to make ".php articles"
    visible at a glance.
    """
    entries: list = field(default_factory=list)
    php_built: list = field(default_factory=list)

    # ── registration ──────────────────────────────────────

    def issue(
        self,
        scope: str,
        target: str,
        message: str,
        location: Optional[Path] = None,
    ):
        """Article/category-level item to fix. Build continues; output may be partial."""
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
        """Output is fine, but worth a look."""
        self.entries.append(ReportEntry(
            scope=scope, target=target, message=message,
            location=location, severity='warning',
        ))

    def note_php_built(self, slug: str):
        """Record that an article fell back to `index.php` (dedup, insertion order).

        Called once per article (cache hit and miss alike); no-op if the slug is
        already present. render()/render_markdown() sort by slug for display.
        """
        if slug and slug not in self.php_built:
            self.php_built.append(slug)

    # ── queries ───────────────────────────────────────────

    def issue_count(self) -> int:
        return sum(1 for e in self.entries if e.severity == 'issue')

    def warning_count(self) -> int:
        return sum(1 for e in self.entries if e.severity == 'warning')

    def php_built_count(self) -> int:
        return len(self.php_built)

    # ── rendering ──────────────────────────────────────────

    def render(self, out=sys.stderr):
        """Print the report to stderr at the end of the build (issues, then
        warnings, then PHP-built articles, then a summary count)."""
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

        # Intended-output report, not issue/warning: the expected user is a web
        # developer, so a PHP fallback is not a fault — but show which articles
        # became .php for operational visibility.
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

    # ── markdown serialization ─────────────────────────────

    def render_markdown(self) -> str:
        """Markdown form of render() for build-report.md (same grouping/order:
        issues -> warnings -> summary).

        Messages are human-written Korean prose, left unescaped (parity with
        render()); only location is wrapped in inline code so paths don't break.
        The caller (Builder._write_build_report) embeds the return value as one
        block (surrounding blank lines are the caller's job).
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
    """Group report items by (scope, target) so multiple issues for one article
    sit under one header.

    Header is formatted as `[scope] target` (or `[scope]` when target is empty).
    Insertion order is preserved (dict insertion order, Python 3.7+).
    """
    groups = {}
    for e in entries:
        header = f'[{e.scope}] {e.target}' if e.target else f'[{e.scope}]'
        groups.setdefault(header, []).append(e)
    return list(groups.items())


# ════════════════════════════════════════════════════════════════
# System-fault abort — use only to stop the build immediately
# ════════════════════════════════════════════════════════════════

def abort(msg: str):
    """Exit immediately on a system fault outside the author's control
    (missing template, no Articles/ directory, uninstalled dependency, ...).

    Content-side problems (missing meta.yaml fields, format errors) should be
    recorded via BuildReport.issue(...) instead, letting the build continue.
    """
    print(f'[ABORT] {msg}', file=sys.stderr)
    print('빌드 중단 (시스템 결함).', file=sys.stderr)
    sys.exit(1)

"""진단 스크립트 — 빌드 + 단위 테스트 + 결정성 + Python↔PHP 점수 패리티
를 한 번에 돌리고 리포트 파일을 생성한다 (v0.6.0 신설).

사용법:
    python tests/run_diagnostics.py
    python tests/run_diagnostics.py --report-path report.txt   # 파일 경로 override
    python tests/run_diagnostics.py --no-build                 # 빌드 스킵
    python tests/run_diagnostics.py --no-php                   # PHP 검증 스킵

리포트는 기본적으로 `tests/diagnostics_report.txt` 에 저장. 사용자가 터미널
에서 열람하거나 IDE 에서 클릭할 수 있다.

진단 항목:
  [1] 단위 테스트 (`tests/` 디렉터리 전체) — pass/fail 카운트 + 실패 상세.
  [2] 빌드 1 회 + 빌드 2 회 결정성 (dist 의 모든 파일 sha256 비교).
  [3] dist/search.php 의 PHP 구문 (`php -l`) — PHP 가 없으면 skip.
  [4] Python ↔ PHP BM25 점수 패리티 — 6 개 쿼리, 모든 hit 의 점수 일치.
       (PHP 가 없으면 skip.)
  [5] dist/search.php 의 인덱스 형식 검증 (version=4, 필드 존재).
  [6] 글 페이지 JSON-LD 의미 정확성 (v0.8.3) — BreadcrumbList position
       단조·비말단 item distinct·dist 실재·말단 name==headline 등.
       PHP 불필요. dist 가 없으면 skip.

모든 항목이 통과하면 exit code 0, 하나라도 실패하면 1.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


# v0.8.1: 테스트는 src/tests/ 로 이동했다. ROOT = src/ (import 경로 +
# 단위 테스트 discover + 진단 리포트 출력의 기준). PROJECT_ROOT =
# 프로젝트 루트 (Articles/·dist/·site.yaml 이 있는 build.py 폴더) —
# Builder(base_dir) 와 dist/ 경로는 이쪽을 기준으로 한다.
ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))


# ════════════════════════════════════════════════════════════════
# 항목 1: 단위 테스트
# ════════════════════════════════════════════════════════════════

def section_unit_tests(report) -> bool:
    """tests/ 디렉터리 전체 발견 후 실행. 결과를 리포트에 기록."""
    report.section('[1] Unit tests')

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(ROOT / 'tests'), pattern='test_*.py')

    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    t0 = time.time()
    result = runner.run(suite)
    elapsed = time.time() - t0

    report.line(f'  tests run     : {result.testsRun}')
    report.line(f'  failures      : {len(result.failures)}')
    report.line(f'  errors        : {len(result.errors)}')
    report.line(f'  skipped       : {len(result.skipped)}')
    report.line(f'  elapsed       : {elapsed:.3f}s')

    if result.failures:
        report.line('')
        report.line('  -- Failures --')
        for case, tb in result.failures:
            report.line(f'    * {case.id()}')
            for tb_line in tb.strip().splitlines()[-6:]:
                report.line(f'        {tb_line}')

    if result.errors:
        report.line('')
        report.line('  -- Errors --')
        for case, tb in result.errors:
            report.line(f'    * {case.id()}')
            for tb_line in tb.strip().splitlines()[-6:]:
                report.line(f'        {tb_line}')

    if result.skipped:
        report.line('')
        report.line('  -- Skipped --')
        for case, reason in result.skipped:
            report.line(f'    * {case.id()} ({reason})')

    ok = result.wasSuccessful()
    report.status(ok)
    return ok


# ════════════════════════════════════════════════════════════════
# 항목 2: 빌드 결정성
# ════════════════════════════════════════════════════════════════

def _dist_sha256(dist: Path) -> dict:
    """dist 의 모든 일반 파일에 대해 {rel_path: sha256_hex} 를 반환."""
    out = {}
    if not dist.is_dir():
        return out
    for p in sorted(dist.rglob('*')):
        if p.is_file():
            h = hashlib.sha256()
            with p.open('rb') as fh:
                for chunk in iter(lambda: fh.read(65536), b''):
                    h.update(chunk)
            out[str(p.relative_to(dist)).replace('\\', '/')] = h.hexdigest()
    return out


def section_build_determinism(report) -> bool:
    """빌드 2회 후 dist 의 모든 파일 sha256 이 동일한지 확인."""
    report.section('[2] Build determinism (dist sha256 stability)')

    from scripts.builder import Builder
    dist = PROJECT_ROOT / 'dist'

    # 1차 빌드
    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        Builder(PROJECT_ROOT).build()
    snap_a = _dist_sha256(dist)

    # 2차 빌드 (캐시 위에 그대로)
    buf2 = io.StringIO()
    with redirect_stdout(buf2), redirect_stderr(buf2):
        Builder(PROJECT_ROOT).build()
    snap_b = _dist_sha256(dist)

    report.line(f'  files (1st build): {len(snap_a)}')
    report.line(f'  files (2nd build): {len(snap_b)}')

    ok = True
    diff = []
    for k in sorted(set(snap_a) | set(snap_b)):
        a, b = snap_a.get(k), snap_b.get(k)
        if a != b:
            ok = False
            diff.append((k, a, b))
    if diff:
        report.line('  mismatches:')
        for k, a, b in diff:
            report.line(f'    {k}')
            report.line(f'      1st: {a}')
            report.line(f'      2nd: {b}')
    else:
        report.line('  all files identical between 1st and 2nd build.')

    report.status(ok)
    return ok


# ════════════════════════════════════════════════════════════════
# 항목 3: dist/search.php PHP 구문
# ════════════════════════════════════════════════════════════════

def section_php_lint(report, php_bin) -> bool:
    report.section('[3] dist/search.php php -l (PHP syntax)')
    if not php_bin:
        report.line('  PHP not available — skipped.')
        report.status(True, skipped=True)
        return True
    proc = subprocess.run(
        [php_bin, '-l', str(PROJECT_ROOT / 'dist' / 'search.php')],
        capture_output=True, text=True, encoding='utf-8',
    )
    report.line(f'  exit code   : {proc.returncode}')
    report.line(f'  stdout      : {proc.stdout.strip()}')
    if proc.stderr.strip():
        report.line(f'  stderr      : {proc.stderr.strip()}')
    ok = proc.returncode == 0
    report.status(ok)
    return ok


# ════════════════════════════════════════════════════════════════
# 항목 4: Python ↔ PHP BM25 점수 패리티
# ════════════════════════════════════════════════════════════════

DIAGNOSTIC_QUERIES = [
    'hello', 'demo', 'world', 'section',
    '데모', '페이지네이션', '섹션', '마커',
]


def section_score_parity(report, php_bin) -> bool:
    report.section('[4] Python ↔ PHP BM25 score parity')
    if not php_bin:
        report.line('  PHP not available — skipped.')
        report.status(True, skipped=True)
        return True

    from scripts.builder import Builder
    from scripts.search import bm25_score, build_search_index

    # 빌더로 articles / rendered_bodies 준비
    b = Builder(PROJECT_ROOT)
    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        b._load_config()
        b._scan_articles()
        b._parse_frontmatter()
        b._validate()
        b._sync_assets()
        b._copy_site_assets()
        b._render_articles()
    idx = build_search_index(b.articles, b.rendered_bodies, b.categories,
                              b._top_category_for_article)

    ok = True
    total_matches = 0
    total_queries = 0
    for q in DIAGNOSTIC_QUERIES:
        py_scores = {}
        for doc_id in range(len(idx['docs'])):
            s = bm25_score(idx, doc_id, q)
            if s > 0:
                py_scores[doc_id] = s

        # PHP 측 점수
        q_esc = q.replace("'", "\\'")
        php_code = (
            'ob_start(); $_GET = ["q" => "' + q_esc + '"]; '
            'include "' + str(PROJECT_ROOT / "dist" / "search.php").replace('\\', '/') + '"; '
            'ob_end_clean(); '
            '$r = bm25_search($INDEX, "' + q_esc + '", null); '
            '$out = new stdClass(); '
            'foreach ($r as $e) $out->{$e[0]} = $e[1]; '
            'echo json_encode($out);'
        )
        proc = subprocess.run(
            [php_bin, '-r', php_code],
            capture_output=True, text=True, encoding='utf-8',
        )
        php_scores_raw = json.loads(proc.stdout or '{}')
        php_scores = {int(k): v for k, v in php_scores_raw.items()}

        total_queries += 1
        keys = sorted(set(py_scores) | set(php_scores))
        for k in keys:
            py = py_scores.get(k, 0)
            ph = php_scores.get(k, 0)
            if abs(py - ph) >= 1e-6:
                ok = False
                report.line(f'  MISMATCH q={q!r} doc_id={k} py={py} php={ph}')
            else:
                total_matches += 1

    report.line(f'  queries tested : {total_queries}')
    report.line(f'  score matches  : {total_matches}')
    report.status(ok)
    return ok


# ════════════════════════════════════════════════════════════════
# 항목 5: 인덱스 형식 검증
# ════════════════════════════════════════════════════════════════

def section_index_shape(report, php_bin) -> bool:
    report.section('[5] dist/search.php index shape (v4)')
    if not php_bin:
        report.line('  PHP not available — skipped.')
        report.status(True, skipped=True)
        return True
    code = (
        'ob_start(); $_GET = ["q" => ""]; '
        'include "' + str(PROJECT_ROOT / "dist" / "search.php").replace('\\', '/') + '"; '
        'ob_end_clean(); '
        'echo json_encode([\n'
        '  "version" => $INDEX["version"] ?? null,\n'
        '  "fields"  => array_keys($INDEX),\n'
        '  "N"       => $INDEX["stats"]["N"] ?? null,\n'
        '  "docs"    => count($INDEX["docs"] ?? []),\n'
        '  "doc0_keys" => isset($INDEX["docs"][0]) ? array_keys($INDEX["docs"][0]) : []\n'
        '], JSON_UNESCAPED_UNICODE);'
    )
    proc = subprocess.run(
        [php_bin, '-r', code], capture_output=True, text=True, encoding='utf-8',
    )
    if proc.returncode != 0:
        report.line(f'  PHP error: {proc.stderr.strip()}')
        report.status(False)
        return False
    info = json.loads(proc.stdout)
    report.line(f'  version    : {info["version"]}')
    report.line(f'  top fields : {info["fields"]}')
    report.line(f'  N          : {info["N"]}')
    report.line(f'  docs count : {info["docs"]}')
    report.line(f'  doc[0] keys: {info["doc0_keys"]}')

    expected_fields = {
        'version', 'params', 'stats', 'docs', 'categories',
        'df_title', 'df_desc', 'df_tags',
        'tf_title', 'tf_desc', 'tf_tags',
    }
    expected_doc_keys = {
        'slug', 'title', 'date', 'category', 'category_slug',
        'description', 'tags', 'body_snippet',
        'dl_title', 'dl_desc', 'dl_tags',
    }

    ok = True
    if info['version'] != 4:
        report.line(f'  ✗ expected version=4, got {info["version"]}')
        ok = False
    missing_top = expected_fields - set(info['fields'])
    if missing_top:
        report.line(f'  ✗ missing top fields: {sorted(missing_top)}')
        ok = False
    missing_doc = expected_doc_keys - set(info['doc0_keys'])
    if missing_doc:
        report.line(f'  ✗ missing doc[0] keys: {sorted(missing_doc)}')
        ok = False
    # body_snippet 색인 폐기 확인 — df_body / tf_body 가 없어야
    forbidden = {'df_body', 'tf_body'}
    if forbidden & set(info['fields']):
        report.line(f'  ✗ unexpected v3 fields present: {forbidden & set(info["fields"])}')
        ok = False

    report.status(ok)
    return ok


# ════════════════════════════════════════════════════════════════
# 항목 6: JSON-LD 의미 정확성 (v0.8.3 신설 게이트)
# ════════════════════════════════════════════════════════════════
#
# additive·결정성-only 무결성 게이트는 JSON-LD 의 *의미* 정확성을
# 보지 않는다 — 빵부스러기 결함(중간 폴더가 자기 중첩 URL 이 아니라
# 톱레벨 URL 로 링크 = Bug A / 말단 이름이 글 제목이 아니라 폴더명
# = Bug B) 부류가 게이트를 그대로 통과한다. 이 섹션이 그 부류를 가드한다.
# 게이트 개선이지 보류된 SSG 확장이 아니다(메모리 feedback_deferred_
# extensions 비해당).

JSONLD_SCRIPT_PREFIX = '<script type="application/ld+json">'
JSONLD_SCRIPT_SUFFIX = '</script>'


def extract_jsonld(html: str):
    """글 페이지 HTML 에서 ld+json 스크립트 1개를 디코드해 dict 로 반환
    (없으면 None). seo.build_jsonld 의 `<` `>` `&` → `\\u003c` `\\u003e`
    `\\u0026` 치환을 test_jsonld._doc 와 동일하게 역변환한다."""
    i = html.find(JSONLD_SCRIPT_PREFIX)
    if i == -1:
        return None
    j = html.find(JSONLD_SCRIPT_SUFFIX, i)
    if j == -1:
        return None
    payload = html[i + len(JSONLD_SCRIPT_PREFIX):j]
    raw = (payload.replace('\\u003c', '<')
                  .replace('\\u003e', '>')
                  .replace('\\u0026', '&'))
    return json.loads(raw)


def validate_jsonld_doc(doc, *, base_url, exists):
    """디코드된 JSON-LD 문서 1개의 의미 정확성을 검사. 위반 메시지
    리스트를 반환한다(빈 리스트 = 정상). `exists(path)` 는 사이트 내부
    절대경로(예 '/blog/3d-printing/')가 dist 에 실재하는지 판정하는
    bool 콜러블.

    검사 항목 (JSON-LD 의미 정확성 계약):
      - @graph 에 Article 존재 + headline 비공백.
      - BreadcrumbList 가 있으면:
          · position 이 1..n 엄밀 단조 증가.
          · 모든 ListItem 의 name 비공백.
          · 말단(마지막)은 item 생략, 비말단은 item 보유.
          · 비말단 item URL 들이 서로 distinct (Bug A: 중간 폴더가
            top_url 로 중복되면 적발).
          · 사이트 내부 비말단 item 이 실재 dist 경로로 해석
            (top_url 오링크/오타 URL 적발).
          · 글 페이지 말단 name == Article.headline (v0.8.3 계약 —
            Bug B: 말단이 폴더명이면 적발).
    BreadcrumbList 가 없으면(톱레벨 글의 단일 crumb 등) 그 검사들은
    건너뛴다(노드 생략은 schema.org 권장·정상)."""
    errs = []
    graph = doc.get('@graph')
    if not isinstance(graph, list):
        return ['@graph 가 리스트가 아님']
    by_type = {}
    for n in graph:
        if isinstance(n, dict):
            by_type.setdefault(n.get('@type'), n)
    article = by_type.get('Article')
    if article is None:
        return ['@graph 에 Article 노드 없음']
    headline = article.get('headline')
    if not (isinstance(headline, str) and headline.strip()):
        errs.append(f'Article.headline 비공백 아님: {headline!r}')

    bc = by_type.get('BreadcrumbList')
    if bc is None:
        return errs  # 단일 crumb/톱레벨 글 — 노드 생략은 정상
    items = bc.get('itemListElement')
    if not isinstance(items, list) or not items:
        errs.append('BreadcrumbList.itemListElement 가 비어있음/비리스트')
        return errs

    positions = [it.get('position') for it in items]
    if positions != list(range(1, len(items) + 1)):
        errs.append(f'position 이 1..n 엄밀 단조 아님: {positions}')

    for k, it in enumerate(items):
        nm = it.get('name')
        if not (isinstance(nm, str) and nm.strip()):
            errs.append(f'ListItem[{k}].name 비공백 아님: {nm!r}')

    last = items[-1]
    if 'item' in last:
        errs.append(
            f'말단 ListItem 에 item 존재(생략돼야 함): {last.get("item")!r}')
    nonleaf_urls = []
    for k, it in enumerate(items[:-1]):
        if 'item' not in it:
            errs.append(f'비말단 ListItem[{k}] 에 item 없음')
            continue
        nonleaf_urls.append(it['item'])

    if len(set(nonleaf_urls)) != len(nonleaf_urls):
        errs.append(f'비말단 item URL 중복(Bug A 류): {nonleaf_urls}')

    for u in nonleaf_urls:
        if isinstance(u, str) and u.startswith(base_url):
            path = u[len(base_url):]
            if not path.startswith('/'):
                path = '/' + path
            if not exists(path):
                errs.append(f'비말단 item 이 dist 에 미해석: {u} (path {path})')

    leaf_name = last.get('name')
    if isinstance(headline, str) and leaf_name != headline:
        errs.append(
            f'말단 name != Article.headline (Bug B 류): '
            f'{leaf_name!r} != {headline!r}')
    return errs


def section_jsonld_semantics(report) -> bool:
    report.section('[6] JSON-LD semantic correctness (article pages)')

    from scripts.builder import Builder
    dist = PROJECT_ROOT / 'dist'
    if not dist.is_dir():
        report.line('  dist/ 없음 — skipped (먼저 빌드 필요).')
        report.status(True, skipped=True)
        return True

    b = Builder(PROJECT_ROOT)
    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(buf):
        b._load_config()
    base_url = b.site.base_url

    def exists(path: str) -> bool:
        rel = path.strip('/')
        if rel == '':
            return (dist / 'index.html').is_file()
        cand = dist / rel
        return cand.is_file() or (cand / 'index.html').is_file()

    docs_checked = 0
    with_breadcrumb = 0
    violations = []
    for p in sorted(dist.rglob('index.html')):
        doc = extract_jsonld(p.read_text(encoding='utf-8'))
        if doc is None:
            continue
        docs_checked += 1
        if any(isinstance(n, dict) and n.get('@type') == 'BreadcrumbList'
               for n in (doc.get('@graph') or [])):
            with_breadcrumb += 1
        rel = str(p.relative_to(dist)).replace('\\', '/')
        for msg in validate_jsonld_doc(doc, base_url=base_url, exists=exists):
            violations.append((rel, msg))

    report.line(f'  base_url            : {base_url}')
    report.line(f'  ld+json docs        : {docs_checked}')
    report.line(f'  with BreadcrumbList : {with_breadcrumb}')
    report.line(f'  violations          : {len(violations)}')
    ok = not violations
    if violations:
        report.line('  -- Violations --')
        for rel, msg in violations:
            report.line(f'    * {rel}: {msg}')
    report.status(ok)
    return ok


# ════════════════════════════════════════════════════════════════
# 리포트 출력
# ════════════════════════════════════════════════════════════════

class Report:
    """리포트 collector — terminal stdout + 파일에 동시에 출력."""

    def __init__(self, file_path: Path):
        self.lines = []
        self.file_path = file_path
        self.section_results = []  # [(name, ok, skipped)]
        self._current_section = None

    def section(self, name):
        self._current_section = name
        self._emit('')
        self._emit('═' * 60)
        self._emit(name)
        self._emit('─' * 60)

    def line(self, s):
        self._emit(s)

    def status(self, ok: bool, skipped: bool = False):
        if skipped:
            label = 'SKIP'
        elif ok:
            label = 'PASS'
        else:
            label = 'FAIL'
        self.section_results.append((self._current_section, ok, skipped))
        self._emit(f'  → {label}')

    def _emit(self, s):
        self.lines.append(s)
        print(s)

    def finalize(self):
        # 요약
        self._emit('')
        self._emit('═' * 60)
        self._emit('Summary')
        self._emit('═' * 60)
        passed = sum(1 for _, ok, _ in self.section_results if ok)
        failed = sum(1 for _, ok, _ in self.section_results if not ok)
        skipped = sum(1 for _, _, sk in self.section_results if sk)
        for name, ok, sk in self.section_results:
            tag = 'SKIP' if sk else ('PASS' if ok else 'FAIL')
            self._emit(f'  [{tag}] {name}')
        self._emit('')
        self._emit(f'  total: {len(self.section_results)} sections, '
                   f'{passed} pass, {failed} fail, {skipped} skip')

        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text('\n'.join(self.lines) + '\n', encoding='utf-8')
        print('')
        print(f'리포트 파일: {self.file_path}')


# ════════════════════════════════════════════════════════════════
# Entry point
# ════════════════════════════════════════════════════════════════

def _force_utf8_stdio():
    """Windows 한국어 (cp949) 콘솔에서도 진단 리포트가 그대로 출력되도록
    stdout/stderr 를 UTF-8 로 재구성. 리포트는 box-drawing (U+2500, U+2550)
    문자를 사용하므로 cp949 인코더로는 UnicodeEncodeError 가 발생한다.

    Python 3.7+ TextIOWrapper.reconfigure 가 있으면 사용. 비대화형 환경
    (pytest capture 등) 에서 reconfigure 미지원이면 조용히 패스 — 그 경우
    파일에 기록된 리포트로 확인 가능.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, io.UnsupportedOperation):
            pass


def main():
    _force_utf8_stdio()
    parser = argparse.ArgumentParser(description='Heron SSG 진단')
    parser.add_argument('--report-path', default=None,
                        help='리포트 출력 경로 (default: tests/diagnostics_report.txt)')
    parser.add_argument('--no-build', action='store_true',
                        help='빌드 결정성 항목을 스킵 (테스트만)')
    parser.add_argument('--no-php', action='store_true',
                        help='PHP 호출이 필요한 항목을 스킵')
    args = parser.parse_args()

    report_path = (Path(args.report_path).resolve() if args.report_path
                   else ROOT / 'tests' / 'diagnostics_report.txt')
    report = Report(report_path)

    php_bin = None if args.no_php else shutil.which('php')

    overall = True

    if not section_unit_tests(report):
        overall = False
    if not args.no_build:
        if not section_build_determinism(report):
            overall = False
    if not section_php_lint(report, php_bin):
        overall = False
    if not section_score_parity(report, php_bin):
        overall = False
    if not section_index_shape(report, php_bin):
        overall = False
    if not section_jsonld_semantics(report):
        overall = False

    report.finalize()
    return 0 if overall else 1


if __name__ == '__main__':
    sys.exit(main())

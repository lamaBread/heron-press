#!/usr/bin/env python3
"""
siheonlee.com migrate.py — 일회성 마이그레이션 스크립트 (§ 14)

기존 lama_website-main 의 data.json → meta.yaml 변환,
legacy-map.yaml 초안 생성, todo 파일 산출.

v0.4.0: scripts/ 디렉터리로 이동. 프로젝트 루트는 부모 디렉터리.

Usage (프로젝트 루트에서):
    python scripts/migrate.py              # 1차 변환 (백업 포함)
    python scripts/migrate.py --check      # 검증 모드 (파일 수정 없음)
    python scripts/migrate.py --dry-run    # 시뮬레이트 (파일 수정 없음)
"""

import os
import re
import sys
import json
import shutil
import unicodedata
from pathlib import Path
from datetime import datetime, date


BASE = Path(__file__).resolve().parent.parent
ARTICLES = BASE / 'Articles'


# ════════════════════════════════════════════════════════════════
# helpers
# ════════════════════════════════════════════════════════════════

def _slug_candidate(folder_name: str) -> str:
    """
    영문 폴더명에서 slug 후보 자동 생성.
    한국어/비ASCII가 포함되면 빈 문자열 반환 (수동 입력 필요).
    """
    # 비ASCII 문자가 있으면 자동 변환 불가
    try:
        folder_name.encode('ascii')
    except UnicodeEncodeError:
        return ''

    s = unicodedata.normalize('NFKD', folder_name)
    s = s.lower()
    # 영숫자 + 공백 + 하이픈만 유지
    s = re.sub(r'[^a-z0-9 \-]', '', s)
    s = re.sub(r'[\s\-]+', '-', s)
    s = s.strip('-')
    return s


def _mtime_to_date(path: Path) -> str:
    """파일의 mtime → YYYY-MM-DD 문자열."""
    try:
        return date.fromtimestamp(path.stat().st_mtime).isoformat()
    except Exception:
        return ''


def _parse_data_json(path: Path) -> dict:
    """data.json 읽기. title/date 추출."""
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        return {
            'title': data.get('title', ''),
            'date': data.get('date', '') or data.get('created', ''),
        }
    except Exception as e:
        return {'title': '', 'date': '', 'error': str(e)}


def _write_meta_yaml(path: Path, title: str, date_str: str, mtime_str: str):
    """meta.yaml 스캐폴드 작성."""
    content = f"""slug: ""
title: {title}
date: {date_str}
updated: {mtime_str}

seo_title_prefix:
seo_title_suffix:
seo_description:
seo_keywords: []
seo_author:
seo_canonical:
seo_og_title:
seo_og_description:
seo_og_image:
seo_og_image_alt:
seo_og_type: article
seo_twitter_card: summary_large_image
seo_twitter_image:
"""
    path.write_text(content, encoding='utf-8')


def _is_underscore_path(p: Path) -> bool:
    return any(part.startswith('_') for part in p.parts)


# ════════════════════════════════════════════════════════════════
# Scan Articles/
# ════════════════════════════════════════════════════════════════

def scan_articles(articles_dir: Path) -> list:
    """
    Articles/ 트리를 워크하여 글 후보 수집.
    반환: [{'dir': Path, 'rel': str, 'folder_name': str}, ...]
    data.json 을 가진 폴더 (레거시) 또는 content.md / content.html 을 가진 폴더.
    """
    results = []
    for root, dirs, files in os.walk(articles_dir):
        root_path = Path(root)
        # _ 접두 경로 스킵
        if _is_underscore_path(root_path.relative_to(articles_dir)):
            dirs.clear()
            continue
        dirs[:] = [d for d in dirs if not d.startswith('_')]

        has_data = 'data.json' in files
        has_content = 'content.md' in files or 'content.html' in files
        has_meta = 'meta.yaml' in files

        if has_data or has_content or has_meta:
            rel = root_path.relative_to(articles_dir)
            results.append({
                'dir': root_path,
                'rel': str(rel),
                'folder_name': root_path.name,
                'has_data': has_data,
                'has_content': has_content,
                'has_meta': has_meta,
                'files': files,
            })
    return results


# ════════════════════════════════════════════════════════════════
# 검증 모드
# ════════════════════════════════════════════════════════════════

def _check_mode(articles_dir: Path):
    """§ 14.6 — 검증 모드."""
    articles = scan_articles(articles_dir)

    total = len(articles)
    no_meta = [a for a in articles if not a['has_meta']]
    data_json_remain = [a for a in articles if a['has_data']]
    slug_empty = []
    slug_counts = {}
    php_todo = []

    for a in articles:
        if not a['has_meta']:
            continue
        meta_file = a['dir'] / 'meta.yaml'
        try:
            text = meta_file.read_text(encoding='utf-8')
            slug_match = re.search(r'^slug:\s*(.+)', text, re.MULTILINE)
            slug = slug_match.group(1).strip().strip('"').strip("'") if slug_match else ''
            if not slug:
                slug_empty.append(a['dir'])
            else:
                slug_counts.setdefault(slug, []).append(a['dir'])
        except Exception:
            slug_empty.append(a['dir'])

        # Check PHP calls in content.html
        html_file = a['dir'] / 'content.html'
        if html_file.exists():
            content = html_file.read_text(encoding='utf-8', errors='ignore')
            if '<?php' in content:
                php_todo.append(a['dir'])

    slug_conflicts = {s: paths for s, paths in slug_counts.items() if len(paths) > 1}

    # legacy-map.yaml check
    legacy_file = BASE / 'legacy-map.yaml'
    legacy_ok = True
    legacy_empty_slugs = []
    if legacy_file.exists():
        text = legacy_file.read_text(encoding='utf-8')
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            m = re.match(r'^"[^"]+"\s*:\s*(.+)', line)
            if m:
                val = m.group(1).strip()
                if val == '""' or val == "''":
                    legacy_empty_slugs.append(line)
    else:
        legacy_ok = False

    # Report
    ok = '✓'
    fail = '✗'
    blockers = 0

    print(f'\n=== migrate.py --check ===\n')
    print(f'{ok if total > 0 else fail} {total}글 스캔')

    if no_meta:
        print(f'{fail} meta.yaml 없는 글: {len(no_meta)}개')
        for p in no_meta:
            print(f'  - {p}')
        blockers += 1
    else:
        print(f'{ok} 모든 글 meta.yaml 보유')

    if data_json_remain:
        print(f'{fail} data.json 잔존: {len(data_json_remain)}개')
        for a in data_json_remain:
            print(f'  - {a["dir"]}')
        blockers += 1
    else:
        print(f'{ok} data.json 잔존 0개')

    if slug_empty:
        print(f'{fail} slug 비어 있음: {len(slug_empty)}글')
        for p in slug_empty:
            print(f'  - {p}')
        blockers += 1
    else:
        print(f'{ok} 모든 slug 작성됨')

    if slug_conflicts:
        print(f'{fail} slug 충돌: {len(slug_conflicts)}쌍')
        for slug, paths in slug_conflicts.items():
            print(f'  - {slug} ({len(paths)}글):')
            for p in paths:
                print(f'      {p}')
        blockers += 1
    else:
        print(f'{ok} slug 충돌 없음')

    if legacy_file.exists():
        if legacy_empty_slugs:
            print(f'{fail} legacy-map.yaml slug 미완성: {len(legacy_empty_slugs)}개')
            blockers += 1
        else:
            print(f'{ok} legacy-map.yaml 모든 키에 값 채움')
    else:
        print(f'{fail} legacy-map.yaml 없음 (migrate.py 를 먼저 실행)')
        blockers += 1

    if php_todo:
        print(f'⚠  HTML 글 PHP 호출 미해결: {len(php_todo)}건 (빌드 차단 아님, 검토 권장)')
        for p in php_todo:
            print(f'  - {p}')

    print()
    if blockers:
        print(f'❌ 빌드 가능하지 않음 ({blockers}개 차단 사유)')
    else:
        print('✅ 빌드 준비 완료. python build.py 를 실행하세요.')
    print()


# ════════════════════════════════════════════════════════════════
# 1차 변환
# ════════════════════════════════════════════════════════════════

def _migrate(articles_dir: Path, dry_run: bool):
    """§ 14.3 — data.json → meta.yaml 변환."""
    articles = scan_articles(articles_dir)

    todo_slugs = []      # (dir, title, candidate_slug)
    todo_php = []        # (file, line, code)
    todo_pre_php = []    # (file, line, code)
    skipped = 0
    converted = 0

    log_lines = []

    for a in articles:
        article_dir = a['dir']

        # 멱등성: meta.yaml 있고 data.json 없으면 스킵
        if a['has_meta'] and not a['has_data']:
            skipped += 1
            log_lines.append(f'SKIP  {article_dir} (meta.yaml already exists)')
            continue

        # data.json 처리
        if a['has_data']:
            data_file = article_dir / 'data.json'
            info = _parse_data_json(data_file)
            title = info.get('title') or article_dir.name
            date_str = info.get('date') or ''

            # normalize date
            if date_str:
                for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d'):
                    try:
                        d = datetime.strptime(str(date_str)[:10], fmt)
                        date_str = d.strftime('%Y-%m-%d')
                        break
                    except ValueError:
                        pass
            if not date_str:
                date_str = _mtime_to_date(data_file)

            # mtime of content file for updated
            content_file = None
            for cf in ('content.md', 'content.html'):
                if (article_dir / cf).exists():
                    content_file = article_dir / cf
                    break
            mtime_str = _mtime_to_date(content_file) if content_file else date_str

            meta_file = article_dir / 'meta.yaml'

            if not dry_run:
                _write_meta_yaml(meta_file, title, date_str, mtime_str)
                # data.json → data.json.bak
                bak = article_dir / 'data.json.bak'
                shutil.copy2(data_file, bak)
                data_file.unlink()

            converted += 1
            log_lines.append(f'CONV  {article_dir} (data.json → meta.yaml)')

            candidate = _slug_candidate(article_dir.name)
            todo_slugs.append((article_dir, title, candidate))

        elif not a['has_meta']:
            # content only, no meta — create scaffold
            content_file = None
            for cf in ('content.md', 'content.html'):
                if (article_dir / cf).exists():
                    content_file = article_dir / cf
                    break
            mtime_str = _mtime_to_date(content_file) if content_file else ''
            meta_file = article_dir / 'meta.yaml'
            if not dry_run:
                _write_meta_yaml(meta_file, article_dir.name, '', mtime_str)
            converted += 1
            log_lines.append(f'SCAFF {article_dir} (no data.json, created empty meta.yaml)')
            candidate = _slug_candidate(article_dir.name)
            todo_slugs.append((article_dir, article_dir.name, candidate))

        # PHP call scan in content.html
        html_file = article_dir / 'content.html'
        if html_file.exists():
            lines = html_file.read_text(encoding='utf-8', errors='ignore').splitlines()
            for lineno, line in enumerate(lines, 1):
                # PHP calls
                for m in re.finditer(r'<\?php\s+\w+\([^)]*\)\s*\?>', line):
                    todo_php.append((html_file, lineno, m.group()))
                # raw <?php in <pre> context (heuristic: lines between <pre> and </pre>)
                if '<?php' in line and '<pre' in '\n'.join(lines[max(0, lineno-10):lineno]):
                    todo_pre_php.append((html_file, lineno, line.strip()))

    # Generate legacy-map.yaml draft
    legacy_file = BASE / 'legacy-map.yaml'
    if not dry_run:
        with open(legacy_file, 'w', encoding='utf-8') as f:
            f.write('# legacy-map.yaml — lama.pe.kr 구버전 URL → siheonlee.com slug\n')
            f.write('# 키: 구버전 URL path  값: 신규 slug (null = 410 Gone)\n')
            f.write('# 운영자가 slug 칸을 채워 주세요.\n\n')
            for a in articles:
                rel_parts = a['dir'].relative_to(articles_dir).parts
                url_path = '/' + 'Articles/' + '/'.join(rel_parts) + '/'
                # _ 접두 경로는 null
                if any(p.startswith('_') for p in rel_parts):
                    f.write(f'"{url_path}": null\n')
                else:
                    f.write(f'"{url_path}": ""\n')
        log_lines.append(f'GEN   legacy-map.yaml')

    # Write todo files
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')

    if todo_slugs and not dry_run:
        todo_slug_file = BASE / 'migrate-todo-slugs.txt'
        with open(todo_slug_file, 'w', encoding='utf-8') as f:
            f.write(f'# slug 미정 글: {len(todo_slugs)}\n')
            f.write('# 양식: <폴더 경로>\\t<제목>\\t<후보 slug>\n')
            f.write('# 후보는 폴더명 자동 변환. 한국어면 빈칸.\n\n')
            for article_dir, title, candidate in todo_slugs:
                f.write(f'{article_dir}\t{title}\t{candidate}\n')

    if todo_php and not dry_run:
        todo_php_file = BASE / 'migrate-todo-php.txt'
        with open(todo_php_file, 'w', encoding='utf-8') as f:
            f.write(f'# HTML 글의 PHP 함수 호출: {len(todo_php)} 건\n')
            f.write('# 양식: <파일 경로>:<라인>\\t<코드>\n\n')
            for php_file, lineno, code in todo_php:
                f.write(f'{php_file}:{lineno}\t{code}\n')
            f.write('\n# 결정 사항:\n')
            f.write('# - 그대로 두면 SSG 가 시뮬레이트 → 정적 HTML 출력\n')
            f.write('# - <pre> 등 코드 표시 의도면 escape 처리 필요\n')

    if todo_pre_php and not dry_run:
        todo_pre_file = BASE / 'migrate-todo-pre-php.txt'
        with open(todo_pre_file, 'w', encoding='utf-8') as f:
            f.write(f'# <pre> 안 raw <?php 후보: {len(todo_pre_php)} 건\n')
            f.write('# escape 처리 권장 (&lt;?php 로 변경)\n\n')
            for pre_file, lineno, code in todo_pre_php:
                f.write(f'{pre_file}:{lineno}\t{code}\n')

    # Write log
    if not dry_run:
        log_file = BASE / f'migrate-{timestamp}.log'
        with open(log_file, 'w', encoding='utf-8') as f:
            for line in log_lines:
                f.write(line + '\n')

    # Summary
    print(f'\n=== migrate.py {"--dry-run" if dry_run else ""} ===\n')
    if dry_run:
        print('[dry-run 모드: 실제 파일 수정 없음]\n')
    print(f'변환: {converted}글')
    print(f'스킵: {skipped}글 (meta.yaml 이미 존재)')
    if todo_slugs:
        print(f'\nmigrate-todo-slugs.txt: {len(todo_slugs)}글의 slug 입력 필요')
    if todo_php:
        print(f'migrate-todo-php.txt  : {len(todo_php)}건의 PHP 호출 검토 필요')
    if todo_pre_php:
        print(f'migrate-todo-pre-php.txt: {len(todo_pre_php)}건 escape 검토 필요')
    if not dry_run and (todo_slugs or todo_php):
        print('\n다음 단계:')
        print('  1. migrate-todo-slugs.txt 보면서 meta.yaml 에 slug 채우기')
        print('  2. legacy-map.yaml 에 slug 채우기')
        print('  3. python migrate.py --check  (차단 사유 0개 확인)')
        print('  4. python build.py')
    print()


# ════════════════════════════════════════════════════════════════
# Entry point
# ════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    if '--check' in sys.argv:
        _check_mode(ARTICLES)
    elif '--dry-run' in sys.argv:
        _migrate(ARTICLES, dry_run=True)
    else:
        # Backup Articles/ before first migration
        backup_dir = BASE / f'Articles.backup-{datetime.now().strftime("%Y%m%d-%H%M%S")}'
        if ARTICLES.exists():
            print(f'백업 생성 중: {backup_dir.name} ...', flush=True)
            shutil.copytree(ARTICLES, backup_dir)
            print('백업 완료.')
        _migrate(ARTICLES, dry_run=False)

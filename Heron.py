#!/usr/bin/env python3
"""Heron — a lightweight, PHP-targeted static site generator.

This file is only the build entry point; all real logic lives in the
``system/scripts/`` package. The site-wide version string is the single source
of truth in ``system/scripts/__init__.py`` (``__version__``).

Layout (v1.5.0):
    user/        what you own and edit
        articles/    article sources
        site.yaml    global configuration
        templates/   page-layout HTML (article / category / home / 404)
        styles/      site-wide stylesheet
        branding/    site-identity assets (default OG image, ...)
    system/      the program — do not edit to run your site
        scripts/     build-time Python package (the builder)
        runtime/     serve-time code: search*.php (server) + *.js (client)
        admin/       Pond, the local authoring tool
        tests/       unit tests + diagnostics
    dist/        build output (empty to start)
    Heron.py     build entry point (this file)
    Pond.php     local authoring entry point (thin router; never emitted to dist)
    README.md / README.ko.md   documentation

``Heron.py`` puts its own ``system/`` at the front of ``sys.path`` so that
``import scripts...`` resolves to ``system/scripts/``. ``user/`` (incl.
``site.yaml`` and ``Articles/``), ``dist/``, ``.build_cache/`` and
``build-report.md`` stay relative to the project root (this file's folder).

Usage:
    python Heron.py                # full build (uses cache)
    python Heron.py --clean        # wipe dist/ and .build_cache/, then build
    python Heron.py --clean-cache  # wipe .build_cache/ only, then build
    python Heron.py --no-cache     # disable the incremental cache
    python Heron.py --help         # argument help
    python -m unittest discover -s system/tests   # unit tests
    python system/tests/run_diagnostics.py        # integration diagnostics

Version / upgrade actions (v1.6.0 — build 대신 실행되고 종료):
    python Heron.py --check              # 프로그램/스키마 버전 + MANIFEST 무결성
    python Heron.py --migrate            # user/ 스키마를 프로그램 버전까지 마이그레이션
    python Heron.py --migrate --dry-run  # 적용 없이 변경 미리보기
    python Heron.py --check-update       # GitHub 최신 버전 확인 (Pond 배너 캐시 갱신)
    python Heron.py --update             # 최신 릴리스 다운로드 → 오버레이 → 마이그레이션

배포 액션 (v1.7.0 — dist 를 서버로 rclone SFTP 증분 동기화):
    python Heron.py --fetch-rclone       # rclone 바이너리 선확보 (검증 포함). 멱등.
    python Heron.py --deploy --dry-run   # 미리보기: 보낼/지울 목록. 서버 변경 0.
    python Heron.py --deploy             # 실제 증분 동기화 (삭제 포함).

이 액션들은 보통 Pond.php 가 내부적으로 호출한다 (사용자 UX = 터미널 0줄).
Heron.py 직접 실행은 전문 사용자/CI 경로.

After a build, ``build-report.md`` is written next to Heron.py — a Markdown
report of progress, summary, and follow-up items. It lives outside dist/ and
does not affect build determinism.

Build dependencies:
    Python 3.10+ stdlib
    Pillow — automatic image optimization. Set images.enabled=false in
        site.yaml to run without it.
"""
import argparse
import shutil
import sys
from pathlib import Path

# Put this file's system/ at the front of sys.path so `import scripts...`
# resolves to system/scripts/.
sys.path.insert(0, str(Path(__file__).parent / 'system'))

from scripts.builder import Builder  # noqa: E402
from scripts.cache import CACHE_DIR_NAME  # noqa: E402


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='Heron.py',
        description='Heron 정적 사이트 빌드 (런타임 PHP 대상).',
        epilog=('관련 명령:\n'
                '  python -m unittest discover -s system/tests   # 단위 테스트\n'
                '  python system/tests/run_diagnostics.py        # 통합 진단'),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    parser.add_argument(
        '--clean', action='store_true',
        help='dist/ 와 .build_cache/ 를 모두 지운 뒤 빌드 (완전 재빌드).')
    parser.add_argument(
        '--clean-cache', action='store_true',
        help='.build_cache/ 만 폐기한 뒤 빌드 (dist/ 는 유지).')
    parser.add_argument(
        '--no-cache', action='store_true',
        help='증분 캐시 lookup/store 비활성 (v0.6.5 동작).')
    # v1.6.0: 버전/업그레이드 액션 (build 대신 실행되고 종료).
    parser.add_argument(
        '--check', action='store_true',
        help='프로그램/스키마 버전 상태 + MANIFEST 무결성을 출력하고 종료.')
    parser.add_argument(
        '--migrate', action='store_true',
        help='user/ 스키마를 프로그램 버전까지 마이그레이션하고 종료.')
    parser.add_argument(
        '--dry-run', action='store_true',
        help='--migrate 와 함께: 적용 없이 변경 미리보기.')
    parser.add_argument(
        '--check-update', action='store_true',
        help='GitHub 최신 버전을 확인하고 종료 (Pond 배너 캐시 갱신).')
    parser.add_argument(
        '--update', action='store_true',
        help='최신 릴리스를 받아 오버레이 후 마이그레이션하고 종료.')
    # v1.7.0: dist 서버 배포 (rclone SFTP 증분 동기화).
    parser.add_argument(
        '--fetch-rclone', action='store_true',
        help='rclone 바이너리를 선확보(다운로드+SHA256 검증)하고 종료. 멱등.')
    parser.add_argument(
        '--deploy', action='store_true',
        help='dist/ 를 서버에 증분 동기화하고 종료 (--dry-run 으로 미리보기).')
    return parser


def _action_check(base: Path) -> int:
    """프로그램/스키마 버전 + MANIFEST 무결성 출력."""
    from scripts import __version__
    from scripts import version, make_manifest
    schema = version.read_schema_version(base)
    print(f'프로그램 버전  : {__version__}')
    print(f'스키마 스탬프  : {schema}  (user/.heron/version)')
    cmp = version.compare(schema, __version__)
    if cmp < 0:
        print('→ 마이그레이션 필요: python Heron.py --migrate '
              '(미리보기: --migrate --dry-run)')
    elif cmp > 0:
        print('→ 콘텐츠가 프로그램보다 최신입니다. 프로그램 업그레이드를 권장.')
    else:
        print('→ 스키마 최신.')
    man = make_manifest.load_manifest(base)
    if not man:
        print('MANIFEST.json 없음 — 무결성 검증 생략.')
        return 0
    v = make_manifest.verify(base)
    if v['ok']:
        print(f"MANIFEST 무결성: OK ({len(man.get('files', {}))} 파일, "
              f"v{v['manifest_version']}).")
    else:
        print(f"MANIFEST 무결성: 불일치 — missing={v['missing']} "
              f"modified={v['modified']}")
    return 0


def _action_migrate(base: Path, *, dry_run: bool) -> int:
    from scripts import __version__
    from scripts import migrations
    migrations.run(base, target=__version__, dry_run=dry_run, log=print)
    if dry_run:
        print('\n(dry-run — 실제 변경 없음. 적용하려면 --dry-run 없이 다시 실행.)')
    return 0


def _action_check_update(base: Path) -> int:
    from scripts import update
    r = update.check_update(base)
    if r['error']:
        print(f"업데이트 확인 실패: {r['error']}")
        return 1
    if r['update_available']:
        print(f"새 버전 있음: v{r['current']} → v{r['latest']}")
        print('업데이트: python Heron.py --update (또는 Pond 의 업데이트 버튼)')
    else:
        print(f"최신입니다 (v{r['current']}).")
    return 0


def _action_update(base: Path) -> int:
    from scripts import update
    r = update.self_update(base, log=print)
    return 0 if r['ok'] else 1


def _action_fetch_rclone(base: Path) -> int:
    """rclone 바이너리 선확보 (다운로드+SHA256 검증). 멱등."""
    from scripts import rclone_bin
    try:
        rclone_bin.ensure(base, log=lambda m: print(m, flush=True))
    except Exception as e:
        print(f'rclone 확보 실패: {e}', flush=True)
        return 1
    return 0


def _action_deploy(base: Path, *, dry_run: bool) -> int:
    """dist/ 를 서버에 증분 동기화 (rclone SFTP). 출력은 실시간 스트리밍."""
    from scripts import deploy
    try:
        return deploy.run(base, dry_run, log=lambda m: print(m, flush=True))
    except deploy.DeployConfigError as e:
        print(f'배포 설정 오류:\n{e}', flush=True)
        return 1
    except Exception as e:
        print(f'배포 실패: {type(e).__name__}: {e}', flush=True)
        return 1


def main(argv=None) -> int:
    # 콘솔/파이프 인코딩을 UTF-8 로 고정 — Windows 기본 cp949 에서 한글/em-dash
    # 출력이 깨지거나 UnicodeEncodeError 로 죽는 것을 막는다. Pond 는 출력 파이프
    # 를 UTF-8 로 읽어 HTML(UTF-8)에 그대로 싣는다. 산출물(dist/)은 별도로
    # 명시적 UTF-8 쓰기라 빌드 결정성과 무관.
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass

    args = _build_arg_parser().parse_args(argv)
    base = Path(__file__).parent

    # v1.6.0: 버전/업그레이드 액션은 build 대신 실행되고 종료 (우선순위 순).
    if args.check:
        return _action_check(base)
    if args.migrate:
        return _action_migrate(base, dry_run=args.dry_run)
    if args.check_update:
        return _action_check_update(base)
    if args.update:
        return _action_update(base)
    if args.fetch_rclone:
        return _action_fetch_rclone(base)
    if args.deploy:
        return _action_deploy(base, dry_run=args.dry_run)

    # --clean wipes .build_cache/ as well as dist/ (a full rebuild).
    if args.clean:
        for d in (base / 'dist', base / CACHE_DIR_NAME):
            if d.exists():
                shutil.rmtree(d)
                print(f'Cleaned: {d}')

    # --clean-cache wipes only the cache; harmless no-op if --clean already did it.
    if args.clean_cache:
        cache_dir = base / CACHE_DIR_NAME
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
            print(f'Cleaned: {cache_dir}')

    Builder(base, enable_cache=not args.no_cache).build()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

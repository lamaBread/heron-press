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
    return parser


def main(argv=None) -> None:
    args = _build_arg_parser().parse_args(argv)
    base = Path(__file__).parent

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


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Heron — a lightweight, PHP-targeted static site generator.

This file is only the build entry point; all real logic lives in the
``src/scripts/`` package. The site-wide version string is the single source
of truth in ``src/scripts/__init__.py`` (``__version__``).

Layout:
    Articles/    article sources
    dist/        build output (empty to start)
    src/         the builder — scripts/ (Python package), templates/,
                 assets/, tests/, admin/ (local authoring tool)
    admin.php    local authoring entry point (thin router; not part of the
                 build, never emitted to dist)
    build.py     build entry point (this file)
    README.md    documentation
    site.yaml    global configuration

``build.py`` puts its own ``src/`` at the front of ``sys.path`` so that
``import scripts...`` resolves to ``src/scripts/``. ``Articles/``, ``dist/``,
``site.yaml``, ``.build_cache/`` and ``build-report.md`` stay relative to the
project root (this file's folder).

Usage:
    python build.py                # full build (uses cache)
    python build.py --clean        # wipe dist/ and .build_cache/, then build
    python build.py --clean-cache  # wipe .build_cache/ only, then build
    python build.py --no-cache     # disable the incremental cache
    python build.py --help         # argument help
    python -m unittest discover -s src/tests   # unit tests
    python src/tests/run_diagnostics.py        # integration diagnostics

After a build, ``build-report.md`` is written next to build.py — a Markdown
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

# Put this file's src/ at the front of sys.path so `import scripts...`
# resolves to src/scripts/.
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from scripts.builder import Builder  # noqa: E402
from scripts.cache import CACHE_DIR_NAME  # noqa: E402


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='build.py',
        description='siheonlee.com 정적 사이트 빌드 (런타임 PHP 대상).',
        epilog=('관련 명령:\n'
                '  python -m unittest discover -s src/tests   # 단위 테스트\n'
                '  python src/tests/run_diagnostics.py        # 통합 진단'),
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

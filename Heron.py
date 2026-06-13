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

설정 검증 (v1.8.0 — Pond 설정창의 저장 게이트):
    python Heron.py --check-config < site.yaml   # stdin 후보를 빌드와 동일 검증

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
from scripts import i18n  # noqa: E402


def _build_arg_parser() -> argparse.ArgumentParser:
    # v1.9.3: description/epilog/옵션 help 를 cli.help.* 로 현지화. main() 이
    # parse_args 보다 먼저 i18n 을 적재하므로 여기서 도구 언어로 조회된다.
    parser = argparse.ArgumentParser(
        prog='Heron.py',
        description=i18n.t('cli.help.description'),
        epilog=i18n.t('cli.help.epilog'),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    parser.add_argument(
        '--clean', action='store_true',
        help=i18n.t('cli.help.clean'))
    parser.add_argument(
        '--clean-cache', action='store_true',
        help=i18n.t('cli.help.clean_cache'))
    parser.add_argument(
        '--no-cache', action='store_true',
        help=i18n.t('cli.help.no_cache'))
    # v1.6.0: 버전/업그레이드 액션 (build 대신 실행되고 종료).
    parser.add_argument(
        '--check', action='store_true',
        help=i18n.t('cli.help.check'))
    parser.add_argument(
        '--migrate', action='store_true',
        help=i18n.t('cli.help.migrate'))
    parser.add_argument(
        '--dry-run', action='store_true',
        help=i18n.t('cli.help.dry_run'))
    parser.add_argument(
        '--check-update', action='store_true',
        help=i18n.t('cli.help.check_update'))
    parser.add_argument(
        '--update', action='store_true',
        help=i18n.t('cli.help.update'))
    # v1.7.0: dist 서버 배포 (rclone SFTP 증분 동기화).
    parser.add_argument(
        '--fetch-rclone', action='store_true',
        help=i18n.t('cli.help.fetch_rclone'))
    parser.add_argument(
        '--deploy', action='store_true',
        help=i18n.t('cli.help.deploy'))
    # v1.8.0: 후보 site.yaml(stdin)을 빌드와 동일 경로로 검증 (Pond 설정 저장 게이트).
    parser.add_argument(
        '--check-config', action='store_true',
        help=i18n.t('cli.help.check_config'))
    # v1.13.0: 미리보기 수정 파일 한 개의 unified diff (stdin=상대경로). Pond 전용.
    parser.add_argument(
        '--deploy-diff', action='store_true',
        help=i18n.t('cli.help.deploy_diff'))
    # v1.14.8: 후보 페이지 meta.yaml(stdin)을 빌드와 동일 경로로 검증 (Pond 의 홈·
    # 카테고리 설정 저장 게이트). 인자 REL: 빈 문자열=홈, 그 외=카테고리 상대경로.
    parser.add_argument(
        '--check-page-meta', nargs='?', const='', default=None, metavar='REL',
        help=i18n.t('cli.help.check_page_meta'))
    # v1.9.7: 로케일 팩 점검(키 패리티/잔존 백슬래시) + 새 로케일 스캐폴딩.
    parser.add_argument(
        '--check-locale', nargs='?', const='*', metavar='CODE',
        help=i18n.t('cli.help.check_locale'))
    parser.add_argument(
        '--new-locale', metavar='CODE',
        help=i18n.t('cli.help.new_locale'))
    return parser


def _action_check(base: Path) -> int:
    """프로그램/스키마 버전 + MANIFEST 무결성 출력."""
    from scripts import __version__
    from scripts import version, make_manifest
    schema = version.read_schema_version(base)
    print(i18n.t('cli.check.program_version', ver=__version__))
    print(i18n.t('cli.check.schema_stamp', schema=schema))
    cmp = version.compare(schema, __version__)
    if cmp < 0:
        print(i18n.t('cli.check.need_migrate'))
    elif cmp > 0:
        print(i18n.t('cli.check.content_newer'))
    else:
        print(i18n.t('cli.check.schema_current'))
    man = make_manifest.load_manifest(base)
    if not man:
        print(i18n.t('cli.check.no_manifest'))
        return 0
    v = make_manifest.verify(base)
    if v['ok']:
        print(i18n.t('cli.check.manifest_ok',
                     files=len(man.get('files', {})),
                     ver=v['manifest_version']))
    else:
        print(i18n.t('cli.check.manifest_mismatch',
                     missing=v['missing'], modified=v['modified']))
    return 0


def _action_migrate(base: Path, *, dry_run: bool) -> int:
    from scripts import __version__
    from scripts import migrations
    migrations.run(base, target=__version__, dry_run=dry_run, log=print)
    if dry_run:
        print(i18n.t('cli.migrate.dry_run_footer'))
    return 0


def _action_check_update(base: Path) -> int:
    from scripts import update
    r = update.check_update(base)
    if r['error']:
        print(i18n.t('cli.checkupdate.failed', error=r['error']))
        return 1
    if r['update_available']:
        print(i18n.t('cli.checkupdate.available',
                     current=r['current'], latest=r['latest']))
        print(i18n.t('cli.checkupdate.howto'))
    else:
        print(i18n.t('cli.checkupdate.uptodate', current=r['current']))
    return 0


def _action_update(base: Path) -> int:
    from scripts import update
    # flush=True: Pond 가 파이프로 받을 때 단계 로그가 실시간으로 흐르도록
    # (블록 버퍼링 방지 — _action_fetch_rclone 과 같은 이유).
    r = update.self_update(base, log=lambda m: print(m, flush=True))
    return 0 if r['ok'] else 1


def _action_fetch_rclone(base: Path) -> int:
    """rclone 바이너리 선확보 (다운로드+SHA256 검증). 멱등."""
    from scripts import rclone_bin
    try:
        rclone_bin.ensure(base, log=lambda m: print(m, flush=True))
    except Exception as e:
        print(i18n.t('cli.rclone.fetch_failed', error=e), flush=True)
        return 1
    return 0


def _action_deploy(base: Path, *, dry_run: bool) -> int:
    """dist/ 를 서버에 증분 동기화 (rclone SFTP). 출력은 실시간 스트리밍."""
    from scripts import deploy
    try:
        return deploy.run(base, dry_run, log=lambda m: print(m, flush=True))
    except deploy.DeployConfigError as e:
        print(i18n.t('cli.deploy.config_error', error=e), flush=True)
        return 1
    except Exception as e:
        print(i18n.t('cli.deploy.failed',
                     error=f'{type(e).__name__}: {e}'), flush=True)
        return 1


def _action_check_config(base: Path) -> int:
    """stdin 의 site.yaml 후보를 빌드와 동일한 경로로 파싱·검증 (v1.8.0).

    Pond 가 편집 중인 site.yaml 버퍼를 stdin 으로 흘려보내면 디스크의
    site.yaml 을 건드리지 않고 검증만 한다 — 통과(exit 0)해야 Pond 가
    저장(commit)한다. 빌드와 같은 Builder._apply_site_config(abort 검증)를
    재사용하므로 '검증은 통과했는데 빌드는 실패' 가 생기지 않는다
    (parity/Pillow 등 부수효과는 _post_config_checks 로 분리돼 제외). 검증
    실패 시 _apply_site_config 안의 abort() 가 [ABORT] 를 stderr 에 내고
    sys.exit(1) 하므로 여기서 별도 처리 없이 그 종료코드가 그대로 전파된다.
    """
    from scripts.yaml_parser import yaml_load
    text = sys.stdin.read()
    raw = yaml_load(text)   # 관대한 파서 — 예외 없이 dict 반환 (의미 검증은 아래).
    b = Builder(base, enable_cache=False)
    b._apply_site_config(raw)   # 실패 시 abort()→sys.exit(1).
    print(i18n.t('cli.checkconfig.ok'))
    for e in b.report.entries:
        if e.severity == 'warning':
            print(i18n.t('cli.checkconfig.review_item', message=e.message))
    return 0


def _action_check_page_meta(base: Path, rel: str) -> int:
    """stdin 의 페이지 meta.yaml 후보(홈/카테고리)를 빌드와 동일 경로로 검증 (v1.14.8).

    rel='' = 홈(Articles/meta.yaml), 그 외 = 카테고리 폴더 상대경로. Pond 가
    편집 중인 버퍼를 stdin 으로 흘려보내면 디스크를 건드리지 않고 빌드와 같은
    Builder._parse_category_meta_file 로 파싱·검증만 한다 — 통과(exit 0)해야 Pond
    가 저장(commit)한다. styles 외부 CSS·template 상대경로 검증이 실제 폴더를
    기준으로 동작하도록 meta_file 경로는 실제 Articles/<rel>/meta.yaml 을 쓴다.

    이 파서는 빌드에서 fail-soft(이슈 → 폴백 + 리포트, 빌드 중단 없음)지만, 저장
    게이트에서는 이슈가 1건이라도 있으면 exit 1 로 거부한다 — site.yaml 게이트와
    UX 일관 + '저장은 됐는데 빌드 리포트에 경고가 쌓이는' 상황 차단. 또 글
    meta(slug+date 동시 존재)를 카테고리/홈에 잘못 붙여넣은 경우 파서는 조용히 빈
    CategoryMeta 로 폴백하므로 여기서 명시적으로 거부한다.
    """
    from scripts.yaml_parser import yaml_load
    text = sys.stdin.read()

    b = Builder(base, enable_cache=False)
    articles = b.articles_dir

    # rel 정규화 + Articles/ 경계 재검증 (Pond 가 화이트리스트로 거르지만 직접
    # 호출/오류 입력 방어 — 벗어나면 거부). 빈 rel = 홈.
    if rel:
        try:
            target_dir = (articles / rel).resolve()
            target_dir.relative_to(articles.resolve())
        except (ValueError, OSError):
            print(i18n.t('cli.checkpagemeta.bad_rel', rel=rel), file=sys.stderr)
            return 1
        scope = 'category'
    else:
        target_dir = articles
        scope = 'home'
    meta_file = target_dir / 'meta.yaml'

    # 글 meta(slug+date)를 카테고리/홈 meta 로 잘못 붙여넣은 경우 명시 거부.
    raw = yaml_load(text)
    if isinstance(raw, dict) and 'slug' in raw and 'date' in raw:
        print(i18n.t('cli.checkpagemeta.is_article'), file=sys.stderr)
        return 1

    b._parse_category_meta_file(meta_file, scope=scope, text=text)

    issues = [e for e in b.report.entries if e.severity == 'issue']
    if issues:
        print(i18n.t('cli.checkpagemeta.failed'), file=sys.stderr)
        for e in issues:
            print(i18n.t('cli.checkpagemeta.issue_item', message=e.message),
                  file=sys.stderr)
        return 1

    print(i18n.t('cli.checkpagemeta.ok'))
    for e in b.report.entries:
        if e.severity == 'warning':
            print(i18n.t('cli.checkpagemeta.review_item', message=e.message))
    return 0


def _action_deploy_diff(base: Path) -> int:
    """stdin 의 dist 상대경로 한 개의 unified diff 를 JSON 한 줄로 출력 (v1.13.0).

    Pond 가 미리보기 '수정' 패널에서 파일을 클릭하면 그 경로를 stdin 으로 흘려보내고,
    여기서 deploy.compute_diff 가 원격 cat + 로컬 dist 본을 비교해 kind 유니온 JSON
    을 낸다(파싱·diff 로직 단일 출처). 설정/네트워크 오류도 깨지지 않게 JSON 으로
    표면화 — exit 0 고정(Pond 는 stdout JSON 만 신뢰).
    """
    import json
    from scripts import deploy
    rel = sys.stdin.read().strip()
    try:
        result = deploy.compute_diff(base, rel)
    except deploy.DeployConfigError as e:
        result = {'kind': 'error', 'path': rel,
                  'message': i18n.t('cli.deploy.config_error', error=e)}
    except Exception as e:
        result = {'kind': 'error', 'path': rel,
                  'message': f'{type(e).__name__}: {e}'}
    print(json.dumps(result, ensure_ascii=False))
    return 0


def _action_check_locale(base: Path, code) -> int:
    """로케일 팩 점검 — 센티넬 '*'(=전부)를 None 으로 옮겨 locale_tools.check 호출."""
    from scripts import locale_tools
    return locale_tools.check(None if code == '*' else code,
                              log=lambda m: print(m, flush=True))


def _action_new_locale(base: Path, code) -> int:
    """CANONICAL 복사로 새 로케일 폴더를 스캐폴딩."""
    from scripts import locale_tools
    return locale_tools.scaffold(code, log=lambda m: print(m, flush=True))


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

    base = Path(__file__).parent

    # v1.9.1: 운영자 대면 CLI/배포/업데이트/마이그레이션 메시지를 도구 언어
    # (user/.heron/locale)로 적재한다 — 이후 모든 액션(+deploy/update/rclone/
    # migrations)이 전역 i18n.t() 로 조회. Pond 가 도구 언어를 en 으로 두면
    # 빌드/배포/업데이트 패널 출력도 영문이 된다.
    # v1.9.3: argparse --help(description/epilog/옵션 help)도 cli.help.* 로
    # 현지화했으므로, 파서가 텍스트를 생성 시점에 고정하기 전에 i18n 을 적재해야
    # 한다 — 적재를 parse_args 보다 앞으로 둔다 (reconfigure → init → 파서 생성).
    i18n.init_from_base(base)

    args = _build_arg_parser().parse_args(argv)

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
    if args.check_config:
        return _action_check_config(base)
    if args.check_page_meta is not None:
        return _action_check_page_meta(base, args.check_page_meta)
    if args.deploy_diff:
        return _action_deploy_diff(base)
    if args.check_locale is not None:
        return _action_check_locale(base, args.check_locale)
    if args.new_locale is not None:
        return _action_new_locale(base, args.new_locale)

    # --clean wipes .build_cache/ as well as dist/ (a full rebuild).
    if args.clean:
        for d in (base / 'dist', base / CACHE_DIR_NAME):
            if d.exists():
                shutil.rmtree(d)
                print(i18n.t('cli.build.cleaned', path=d))

    # --clean-cache wipes only the cache; harmless no-op if --clean already did it.
    if args.clean_cache:
        cache_dir = base / CACHE_DIR_NAME
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
            print(i18n.t('cli.build.cleaned', path=cache_dir))

    Builder(base, enable_cache=not args.no_cache).build()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

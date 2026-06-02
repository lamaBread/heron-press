"""로케일 팩 점검·스캐폴딩 도구 (v1.9.7 신설 — i18n 기여 워크플로).

두 가지 운영자 대면 기능을 제공한다 (Heron.py 가 --check-locale / --new-locale
로 노출):

  - ``check`` — 한 로케일(또는 전부)의 머지 키 집합을 CANONICAL(en) 과 대조해
    **missing**(en 에 있으나 여기 없음 → 런타임에 영어로 폴백), **extra**(여기만
    있음 → 죽은/오타 키), **stray-backslash**(해석값에 리터럴 ``\\`` 잔존 —
    test_i18n.EscapeDecodingTests 와 동일 규칙) 를 보고하고, 정보성으로
    **untranslated**(en 값과 byte-동일 → 아직 미번역 추정) 개수를 센다.
    missing/extra/stray 중 하나라도 있으면 종료코드 1 — CI/pre-commit 게이트.

  - ``scaffold`` — 새 로케일 폴더를 만들고 CANONICAL 의 모든 ``*.yaml`` 을
    **바이트 그대로** 복사해 즉시 키 패리티를 통과시킨다 (번역 전까지 영어 표시).
    그리고 ``admin.locale.name.<code>`` endonym 키를 모든 팩의 admin.yaml 에
    주입해 Pond 설정 드롭다운과 패리티 테스트(KeyParity/LocaleNameParity)를
    동시에 만족시킨다.

stdlib 만 사용. 사람 대면 출력은 전부 i18n.t('cli.locale.*') 를 거친다.
"""
import re
import shutil

from . import i18n

# BCP-47 풍 로케일 코드 검증. 보안 경계: ``../`` ``a/b`` 절대경로 등 경로 탈출을
# 막아 스캐폴딩이 항상 ``system/locales/<code>/`` 안에만 쓰도록 보장한다.
LOCALE_CODE_RE = re.compile(r'^[A-Za-z][A-Za-z0-9-]*$')


def _is_valid_code(code) -> bool:
    return isinstance(code, str) and bool(LOCALE_CODE_RE.match(code))


def _check_one(code: str, locales_dir, ref: dict, log) -> bool:
    """로케일 하나를 ref(=CANONICAL 머지맵) 와 대조. 결함 없으면 True."""
    pack = i18n._load_pack(code, locales_dir)
    ref_keys, keys = set(ref), set(pack)
    missing = sorted(ref_keys - keys)
    extra = sorted(keys - ref_keys)
    stray = sorted(k for k, v in pack.items() if '\\' in v)
    # 정보성: 공통 키 중 값이 en 과 byte-동일 = 아직 미번역 추정.
    untranslated = sum(
        1 for k in (ref_keys & keys) if pack[k] == ref[k])

    ok = not (missing or extra or stray)
    if missing:
        log(i18n.t('cli.locale.missing',
                   count=len(missing), keys=', '.join(missing)))
    if extra:
        log(i18n.t('cli.locale.extra',
                   count=len(extra), keys=', '.join(extra)))
    if stray:
        log(i18n.t('cli.locale.stray_backslash',
                   count=len(stray), keys=', '.join(stray)))
    if untranslated:
        log(i18n.t('cli.locale.untranslated', count=untranslated))
    if ok:
        log(i18n.t('cli.locale.ok', code=code, total=len(pack)))
    return ok


def check(code=None, locales_dir=None, log=print) -> int:
    """로케일 팩을 CANONICAL 과 대조 점검.

    ``code`` 가 None 이면 CANONICAL 을 제외한 모든 로케일을 점검, 코드가 주어지면
    검증 후 그 하나만. missing/extra/stray 가 하나라도 있으면 1, 아니면 0
    (untranslated 는 정보성 — 종료코드 무관).
    """
    locales_dir = locales_dir or i18n.LOCALES_DIR

    if code is not None and not _is_valid_code(code):
        log(i18n.t('cli.locale.invalid_code', code=code))
        return 1

    ref = i18n._load_pack(i18n.CANONICAL, locales_dir)

    if code is None:
        targets = [loc for loc in _available(locales_dir)
                   if loc != i18n.CANONICAL]
    else:
        targets = [code]

    all_ok = True
    for loc in targets:
        log(i18n.t('cli.locale.check_header', code=loc))
        if not _check_one(loc, locales_dir, ref, log):
            all_ok = False
    return 0 if all_ok else 1


def _available(locales_dir) -> list:
    """locales_dir 아래 로케일 폴더명 (정렬). i18n.available_locales 의 매개화판."""
    if not locales_dir.is_dir():
        return []
    return sorted(p.name for p in locales_dir.iterdir() if p.is_dir())


def _append_endonym(admin_path, code: str) -> None:
    """admin.yaml 끝에 endonym 키 한 줄을 추가 (없으면 새로 만든다).

    플랫 닷키는 순서 무관이므로 EOF 에 ``admin.locale.name.<code>: "<code>"`` 를
    한 줄 붙인다. 파일이 개행으로 끝나지 않으면 먼저 개행을 넣어 줄이 합쳐지지
    않게 한다 (파서 안전).
    """
    line = f'admin.locale.name.{code}: "{code}"\n'
    if admin_path.is_file():
        text = admin_path.read_text(encoding='utf-8')
        if text and not text.endswith('\n'):
            text += '\n'
        text += line
    else:
        text = line
    admin_path.write_text(text, encoding='utf-8')


def scaffold(code, locales_dir=None, log=print) -> int:
    """새 로케일 폴더를 CANONICAL 복사로 만들고 endonym 키를 주입.

    ``code`` 검증 → CANONICAL 거부 → 기존 폴더 거부. CANONICAL 의 모든
    ``*.yaml`` 을 바이트 그대로 복사(주석·값 보존). 이후 모든 팩(+새 팩)의
    admin.yaml 에 ``admin.locale.name.<code>: "<code>"`` 를 추가. 성공 시 0.
    """
    locales_dir = locales_dir or i18n.LOCALES_DIR

    if not _is_valid_code(code):
        log(i18n.t('cli.locale.invalid_code', code=code))
        return 1
    if code == i18n.CANONICAL:
        log(i18n.t('cli.locale.scaffold_exists', code=code))
        return 1

    dest = locales_dir / code
    if dest.exists():
        log(i18n.t('cli.locale.scaffold_exists', code=code))
        return 1

    src = locales_dir / i18n.CANONICAL
    dest.mkdir(parents=True)
    copied = 0
    for f in sorted(src.glob('*.yaml')):
        shutil.copy2(f, dest / f.name)   # 바이트 보존 (메타 포함).
        copied += 1
    log(i18n.t('cli.locale.scaffold_copied', count=copied, code=code))

    # endonym 키를 모든 기존 로케일 + 새 로케일의 admin.yaml 에 주입해
    # 키 패리티(KeyParity)와 표시명 패리티(LocaleNameParity)를 유지.
    for loc in _available(locales_dir):
        _append_endonym(locales_dir / loc / 'admin.yaml', code)
    log(i18n.t('cli.locale.endonym_injected', code=code))

    log(i18n.t('cli.locale.scaffold_done', code=code))
    return 0

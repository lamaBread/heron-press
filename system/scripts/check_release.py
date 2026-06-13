"""릴리스 정합성 게이트 (v1.14.11 신설 — RELEASE-HARNESS.md §1·§2 의 자동화).

단일 명령으로 "이 트리가 릴리스로 내보낼 준비가 됐는가"를 *결정론적* 으로 판정한다.
사람의 자연어 명령("push 해")과 무관하게 git push/tag PreToolUse 훅이 호출하는
저작-시점(author-time) 게이트의 본체 — 표현이 아니라 사실(파일·해시·버전)을 본다.

통과 기준 (둘 다):

  1. **MANIFEST 동기화** — 디스크에서 재계산한 매니페스트가 동봉
     ``system/MANIFEST.json`` 과 *완전히* 같다 (파일 추가/삭제/수정 + ``version``).
     주의: ``make_manifest.verify()`` 의 ``ok`` 는 미등록(untracked) 신규 파일과
     version 불일치를 통과시킨다 — 그래서 여기서는 ``verify()`` 가 아니라 전체
     재계산본을 통째로 비교한다. v1.14.8 이 깨뜨린 지점이 정확히 "신규
     ``pagemeta.php`` 가 매니페스트에 안 잡힘 + version stale" 이었고, 그건
     untracked/version 케이스라 ``ok`` 를 빠져나갔다.

  2. **버전 참조 일치** — ``README.md`` / ``README.ko.md`` 의 제목·푸터·changelog
     최신 행 버전이 모두 단일 출처 ``__version__`` 과 같고, changelog 최신 행은
     굵게(``**``) 다.

종료코드: 0=통과, 1=드리프트(상세는 ``run`` 의 log 으로). i18n 비대상 —
릴리스 엔지니어링 도구라 로케일 팩 패리티 게이트와 무관한 평문 출력이다.
"""
from pathlib import Path
import re

from . import make_manifest as mm

_VER_RE = re.compile(r'(\d+)\.(\d+)\.(\d+)')


def _semver_key(v: str):
    m = _VER_RE.search(v)
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


def check_manifest(base) -> list:
    """동봉 MANIFEST 와 디스크 재계산본의 드리프트 목록 (빈 list = 동기)."""
    base = Path(base)
    committed = mm.load_manifest(base)
    if not committed:
        return ['system/MANIFEST.json 없음/파손 — make_manifest.py 로 생성 필요']
    disk = mm.compute_manifest(base)
    problems = []
    if disk.get('version') != committed.get('version'):
        problems.append(
            f"MANIFEST version={committed.get('version')} ≠ __version__"
            f"={disk.get('version')} (매니페스트 미재생성)")
    df, cf = disk.get('files', {}), committed.get('files', {})
    added = sorted(set(df) - set(cf))
    removed = sorted(set(cf) - set(df))
    changed = sorted(k for k in (set(df) & set(cf)) if df[k] != cf[k])
    if added:
        problems.append(
            f"매니페스트 미등록 파일 {len(added)}: {added[:5]}"
            f"{' …' if len(added) > 5 else ''}")
    if removed:
        problems.append(
            f"매니페스트엔 있으나 디스크에 없음 {len(removed)}: {removed[:5]}"
            f"{' …' if len(removed) > 5 else ''}")
    if changed:
        problems.append(
            f"내용 변경됐는데 해시 stale {len(changed)}: {changed[:5]}"
            f"{' …' if len(changed) > 5 else ''}")
    return problems


def check_version_refs(base) -> list:
    """README 제목·푸터·changelog 최신 행 버전이 __version__ 과 맞는지."""
    base = Path(base)
    ver = mm.program_version(base)
    problems = []
    for fname in ('README.md', 'README.ko.md'):
        path = base / fname
        if not path.is_file():
            problems.append(f'{fname}: 파일 없음')
            continue
        text = path.read_text(encoding='utf-8')

        # 제목: 첫 '# Heron vX.Y.Z' 헤딩
        m = re.search(r'^#\s+Heron\s+v(\d+\.\d+\.\d+)', text, re.M)
        if not m:
            problems.append(f'{fname}: 제목 "# Heron vX.Y.Z" 패턴 못 찾음')
        elif m.group(1) != ver:
            problems.append(f'{fname}: 제목 버전 v{m.group(1)} ≠ v{ver}')

        # 푸터: '*Heron vX.Y.Z …'
        fm = re.search(r'\*Heron\s+v(\d+\.\d+\.\d+)\b', text)
        if not fm:
            problems.append(f'{fname}: 푸터 "*Heron vX.Y.Z" 패턴 못 찾음')
        elif fm.group(1) != ver:
            problems.append(f'{fname}: 푸터 버전 v{fm.group(1)} ≠ v{ver}')

        # changelog 최신 행 = 모든 '| (**)?vX.Y.Z(**)? |' 행 중 semver 최대.
        # (섹션 문구에 의존하지 않고 버전으로 앵커 → 표 구조가 바뀌어도 견고.)
        rows = re.findall(r'^\|\s*(\*\*)?v(\d+\.\d+\.\d+)(\*\*)?\s*\|', text, re.M)
        if not rows:
            problems.append(f'{fname}: changelog 버전 행 못 찾음')
        else:
            lead, topver, trail = max(rows, key=lambda r: _semver_key(r[1]))
            if topver != ver:
                problems.append(f'{fname}: changelog 최신 v{topver} ≠ v{ver}')
            elif not (lead and trail):
                problems.append(
                    f'{fname}: changelog 최신 v{topver} 행이 굵게(**) 아님')
    return problems


def run(base=None, log=print) -> int:
    """전체 게이트 실행. 0=통과, 1=드리프트."""
    base = Path(base) if base else Path(__file__).resolve().parents[2]
    problems = check_manifest(base) + check_version_refs(base)
    if problems:
        log('릴리스 게이트 실패 — 다음을 해결한 뒤 다시 push/tag 하세요:')
        for p in problems:
            log(f'  ✗ {p}')
        log('  → 소스 편집을 끝낸 뒤 마지막에 1회: '
            'python3 system/scripts/make_manifest.py')
        log('  → 버전 참조(README 제목·푸터·changelog 굵게)는 '
            'RELEASE-HARNESS.md §1 참조')
        return 1
    ver = mm.program_version(base)
    log(f'릴리스 게이트 통과 — v{ver}: MANIFEST 동기 + 버전 참조 일치.')
    return 0


def main(argv=None) -> int:
    return run()


if __name__ == '__main__':
    import sys
    raise SystemExit(main())

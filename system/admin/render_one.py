#!/usr/bin/env python3
"""단일 글 본문 렌더 — Pond (Pond.php) 실시간 미리보기 진입점 (v1.1.0).

v1.1.1: site.yaml `php_globals` 를 미리보기에도 적용 — imgBox 캡션의
서명 변수 보간이 산출물과 동일하게 치환되도록(본문 충실도 유지).

admin.php 가 이 스크립트를 서브프로세스로 부른다. 목적은 **미리보기와
산출물의 본문 충실도 일치**: 별도 마크다운 엔진을 두지 않고 실제 빌더가
글 본문을 만들 때 쓰는 `scripts.markdown` 경로를 그대로 재사용한다
(설계 원칙 6·9 — 파서 단일화 / Py 단일 진실원 보존).

빌더의 본문 조립 (scripts/builder.py `_render_articles`) 과 1:1 동일:
    .md   → resolve_section_markers(render_article_md(text, slug, dir).html, title)
    .html → process_html(text, slug, dir).html
헤더/nav/푸터·메타태그·JSON-LD 등 풀페이지 chrome 은 의도적으로 만들지
않는다 — 그건 템플릿 채움 단계라 풀페이지 정확본은 원클릭 빌드(`python
build.py`) 산출물로 확인한다. 이 스크립트가 보장하는 건 *본문* 의
byte 충실도(같은 파서·같은 imgBox/imgSlideBox·같은 asset 경로 재작성).

Usage:
    python render_one.py <article_source_dir> [--ext md|html]

  본문 텍스트는 **stdin** 으로 받는다 (편집 중 미저장 버퍼 → 진짜 실시간
  미리보기). stdin 이 비어 있으면 source_dir 의 content.md/.html 을
  디스크에서 읽는다 (저장본 미리보기). slug·title 은 source_dir 의
  meta.yaml 에서 (없으면 안전한 폴백) — slug 는 asset 경로 재작성에,
  title 은 자동 첫 갭 제목에 쓰인다.

  --ext 는 stdin 본문을 md/html 중 무엇으로 다룰지 (편집기가 안다).
  생략 시 source_dir 의 기존 content 파일에서 추정, 그것도 없으면 md.

출력: 본문 HTML 한 덩어리를 stdout 으로 (UTF-8). 오류 시 사람이 읽을
HTML 조각을 stdout 으로 내고 exit 1 (admin 이 미리보기 창에 그대로 표시).
"""
import sys
from pathlib import Path

# Heron.py 와 동일한 경로 해석: 이 파일은 <verdir>/system/admin/render_one.py
# 이므로 parent.parent = <verdir>/system 을 sys.path 맨 앞에 올리면
# `import scripts...` 가 빌더와 같은 패키지(system/scripts)를 가리킨다.
_SRC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SRC))


def _html_escape(s: str) -> str:
    return (s.replace('&', '&amp;').replace('<', '&lt;')
             .replace('>', '&gt;'))


def _fail(msg: str) -> 'NoReturn':
    sys.stdout.write(
        "<div style=\"font:14px/1.6 ui-monospace,monospace;"
        "color:#b00;background:#fff3f3;border:1px solid #f0caca;"
        "padding:14px;border-radius:8px;white-space:pre-wrap\">"
        "미리보기 렌더 실패\n\n" + _html_escape(msg) + "</div>"
    )
    sys.stdout.flush()
    raise SystemExit(1)


def main(argv=None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)

    ext = None
    rest = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--ext':
            i += 1
            ext = argv[i] if i < len(argv) else None
        elif a.startswith('--ext='):
            ext = a.split('=', 1)[1]
        else:
            rest.append(a)
        i += 1

    if not rest:
        _fail("사용법: python render_one.py <article_source_dir> "
              "[--ext md|html]  (본문은 stdin)")
    source_dir = Path(rest[0])
    if not source_dir.is_dir():
        _fail(f"글 폴더가 없습니다: {source_dir}")

    # 빌더와 같은 모듈을 import (sys.path 에 <verdir>/system 이 올라 있음).
    try:
        from scripts.markdown import (
            render_article_md, process_html, resolve_section_markers,
            parse_php_globals,
        )
        from scripts.yaml_parser import yaml_load
    except Exception as e:  # noqa: BLE001 — 미리보기는 무엇이든 보여줘야
        _fail(f"빌더 모듈 import 실패: {e!r}")

    # v1.1.1: 빌더와 같은 site.yaml php_globals 를 미리보기에도 적용 —
    # imgBox 캡션의 `{$site_credit}` 등이 산출물과 동일하게 치환
    # 되어야 본문 충실도가 유지된다 (설계 원칙 6·9, test_render_one 게이트).
    # 빌더는 <verdir>/user/site.yaml 을 읽으므로 여기서도 같은 파일에서.
    php_globals = {}
    site_yaml = _SRC.parent / 'user' / 'site.yaml'
    if site_yaml.is_file():
        try:
            php_globals = parse_php_globals(
                (yaml_load(site_yaml.read_text(encoding='utf-8')) or {})
                .get('php_globals'))
        except Exception:  # noqa: BLE001 — 폴백으로 계속 (보간만 생략)
            php_globals = {}

    # slug / title 은 meta.yaml 에서. 새 글(아직 meta 미작성) 미리보기도
    # 깨지지 않도록 안전한 폴백을 둔다 — slug 폴백은 asset 경로가
    # /preview/... 로 나올 뿐 본문 구조·텍스트 충실도엔 영향 없다.
    slug, title = 'preview', ''
    meta_path = source_dir / 'meta.yaml'
    if meta_path.is_file():
        try:
            meta = yaml_load(meta_path.read_text(encoding='utf-8')) or {}
            slug = (meta.get('slug') or slug) if isinstance(meta, dict) else slug
            title = (meta.get('title') or '') if isinstance(meta, dict) else ''
        except Exception:  # noqa: BLE001 — 폴백으로 계속
            pass

    # 본문: stdin 우선(미저장 버퍼 = 진짜 실시간), 비면 디스크 저장본.
    raw = sys.stdin.buffer.read()
    if raw:
        text = raw.decode('utf-8', errors='replace')
        if ext not in ('md', 'html'):
            ext = ('html' if (source_dir / 'content.html').is_file()
                   and not (source_dir / 'content.md').is_file() else 'md')
    else:
        cmd = source_dir / 'content.md'
        chtml = source_dir / 'content.html'
        if cmd.is_file():
            text, ext = cmd.read_text(encoding='utf-8'), 'md'
        elif chtml.is_file():
            text, ext = chtml.read_text(encoding='utf-8'), 'html'
        else:
            _fail("본문이 없습니다 (stdin 비어 있고 content.md/"
                  "content.html 도 없음).")

    try:
        if ext == 'html':
            body = process_html(text, slug, source_dir, php_globals).html
        else:
            rr = render_article_md(text, slug, source_dir, php_globals)
            body = resolve_section_markers(rr.html, title)
    except Exception as e:  # noqa: BLE001
        _fail(f"본문 렌더 중 예외: {e!r}")

    sys.stdout.reconfigure(encoding='utf-8', newline='')
    sys.stdout.write(body)
    sys.stdout.flush()


if __name__ == '__main__':
    main()

"""마크다운 렌더링 + 본문 후처리.

파이프라인 (글 .md 한 편 기준):
  1. preprocess_md_custom_syntax(text) — 사용자 정의 문법(imgBox, 섹션 마커)
                                          → raw HTML / sentinel 주석
  2. Parsedown().text(text) → str — 순수 MD → HTML (parsedown.py)
  3. finalize_md_html(html, slug, dir) — asset path 재작성, PHP 함수 시뮬레이션
  4. resolve_section_markers(html, title) — sentinel 주석 → 실제 gap/section
                                            마커, 본문을 자동 첫 갭+섹션으로
                                            감싸기. (builder 가 호출)

v1.5.1 변경 — 안정화 (동작·산출물 불변):
  - `_resolve_selector` 의 죽은 분기 + 미사용 `_SECTION_SCOPED_TAGS` 집합
    제거. 단일 태그명은 화이트리스트 여부와 무관하게 모두 `section TAG` 로
    감싸지므로 (README §4-6) 그 집합과 `if raw in _SECTION_SCOPED_TAGS`
    분기는 항상 같은 결과를 내는 사문(死文)이었다. 출력 byte 불변.

v0.5.5 변경:
  - 본문 첫 단락 / 첫 이미지 추출 폐지 (`_FIRST_P_RE`, `_FIRST_IMG_RE` 제거).
    이전 버전까지는 SEO description / og_image / 갤러리 썸네일 / 피드 summary
    의 폴백 소스로 사용되었으나, "본문 ↔ 메타데이터 분리 원칙" 도입과 함께
    폐기. RenderResult 도 `html` 한 필드로 슬림화.

v0.4.3 변경:
  - 섹션 마커 문법 추가 (마크다운 본문 안에서 사용):
      ===제목===  라인 → 이전 섹션 닫고 + 새 갭(제목) + 새 섹션 열기
      ======      라인 → 현재 섹션을 명시적으로 닫기 (다음 텍스트는 섹션 밖)
    code block (``` ... ```) 안에서는 매칭 안 함.

v0.4.1 변경:
  - PHP CLI 의존 제거. 마크다운 파서는 scripts/parsedown.py (Parsedown 1.7.4
    Python 포팅) 하나만 사용.
  - 추상화 (MarkdownRenderer / BuiltinRenderer / ParsedownRenderer / 팩토리)
    제거 — 단일 파서이므로 인터페이스 불필요.
"""
import re
from pathlib import Path

from .models import RenderResult
from .parsedown import Parsedown


def escape_html(s: str) -> str:
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


# ════════════════════════════════════════════════════════════════
# Custom syntax preprocessing  (parser-agnostic)
# ════════════════════════════════════════════════════════════════

# v1.14.1 견고화 — 자기 구분자를 본문에 품은 입력도 한 줄 imgBox 로 인식:
#   alt  = `(.*?)`  게으름 → 첫 `]]` 에서 종료 (alt 안의 단일 `[`/`]` 허용)
#   url  = `(.+?)`  게으름 → 뒤따르는 `)` 로 종료하되, 캡션이 있으면 캡션의
#                   `)`(예: 파일명 `dog(1).png`, 캡션 `(좌)`)를 삼키지 않음
#   cap  = `(.*)`   탐욕 → 줄 끝 직전 마지막 `}` 까지 (캡션 안의 `{`/`}` 허용)
#   `^[ \t]*` 선행 가로 공백 허용 → 들여쓴 imgBox 가 코드블록으로 떨어지지 않게
#            (치환이 줄 전체를 대체하므로 결과 div 는 컬럼0 으로 나옴).
_IMGBOX_LINE_RE = re.compile(
    r'^[ \t]*!\[\[(.*?)\]\]\((.+?)\)(?:\s+\{(.*)\})?\s*$',
    re.MULTILINE,
)

# 섹션 마커. 라인 단위로 매칭한다. code fence 안은 별도 로직으로 회피.
#   ===제목===  → 새 섹션 열기 (이전 섹션 자동 닫힘)
#   ======      → 현재 섹션 닫기
# = 가 정확히 3개로 시작/끝, 사이에 = 를 포함하지 않는 임의 텍스트.
_SECTION_OPEN_RE = re.compile(r'^===([^=].*?[^=]|[^=])===\s*$')
_SECTION_CLOSE_RE = re.compile(r'^======\s*$')

# Parsedown 이 보존하는 HTML 주석을 sentinel 로 사용.
_OPEN_SENTINEL = '<!--SBR-OPEN:{title}-->'
_CLOSE_SENTINEL = '<!--SBR-CLOSE-->'


def _preprocess_section_markers(md: str) -> str:
    """ ===title===  / ====== 라인을 sentinel HTML 주석으로 치환.

    code fence (``` ... ``` 또는 ~~~ ~~~ ) 안에서는 건들지 않는다.
    sentinel 은 빈 줄로 separate 되어 Parsedown 에 HTML block 으로 전달된다.
    """
    out_lines = []
    in_fence = False
    fence_char = None
    fence_re = re.compile(r'^(`{3,}|~{3,})')

    for line in md.split('\n'):
        stripped = line.lstrip()
        m_fence = fence_re.match(stripped)
        if m_fence:
            fc = m_fence.group(1)[0]
            if not in_fence:
                in_fence = True
                fence_char = fc
            elif fence_char == fc:
                in_fence = False
                fence_char = None
            out_lines.append(line)
            continue

        if in_fence:
            out_lines.append(line)
            continue

        m_open = _SECTION_OPEN_RE.match(line)
        if m_open:
            title = m_open.group(1).strip()
            out_lines.append('')
            out_lines.append(_OPEN_SENTINEL.format(title=title))
            out_lines.append('')
            continue
        if _SECTION_CLOSE_RE.match(line):
            out_lines.append('')
            out_lines.append(_CLOSE_SENTINEL)
            out_lines.append('')
            continue

        out_lines.append(line)

    return '\n'.join(out_lines)


def preprocess_md_custom_syntax(md: str) -> str:
    """프로젝트 고유 마크다운 확장을 raw HTML 로 치환.

    현재 지원:
      ![[alt]](url) {desc}  → <div class="imgBox">…</div>
      ===제목===            → 섹션 시작 (sentinel 주석)
      ======                → 섹션 끝   (sentinel 주석)
    """
    def replace_imgbox(m: re.Match) -> str:
        alt = m.group(1) or ''
        url = m.group(2)
        desc = m.group(3)
        alt_e = escape_html(alt)
        # v1.14.1: 캡션은 이스케이프하지 않는다 — PHP 형(_simulate_imgbox)과
        # 동일하게, 작성자가 캡션에 넣은 `<br>`·`<a …>` 등 raw HTML 을 그대로
        # 살린다(두 형식의 산출물 패리티). `alt` 는 속성값이라 이스케이프 유지.
        if desc:
            return (f'<div class="imgBox">\n'
                    f'  <img src="{url}" alt="{alt_e}">\n'
                    f'  <p class="caption">{desc}</p>\n'
                    f'</div>')
        return (f'<div class="imgBox">\n'
                f'  <img src="{url}" alt="{alt_e}">\n'
                f'</div>')

    md = _preprocess_section_markers(md)
    return _IMGBOX_LINE_RE.sub(replace_imgbox, md)


# ════════════════════════════════════════════════════════════════
# Section marker resolution  (sentinel → gap/section HTML)
# ════════════════════════════════════════════════════════════════

# Parsedown 출력 후의 sentinel. 주변을 빈 줄로 감싸 두었으므로
# Parsedown 은 보통 이 주석을 HTML block 으로 보존한다.
_SENTINEL_SPLIT_RE = re.compile(r'<!--SBR-(OPEN:.+?|CLOSE)-->')


def _gap_html(title: str) -> str:
    return f"<div class='gap'>\n    <p>{escape_html(title)}</p>\n</div>\n"


def resolve_section_markers(html: str, opening_title: str) -> str:
    """sentinel 주석을 실제 gap/section HTML 로 치환한 뒤,
    본문 전체를 자동 첫 갭+섹션으로 감싼다.

    상태 머신:
      시작:   자동으로 [gap(opening_title)] + <section>  (섹션 열림)
      OPEN:t  섹션 열림이면 </section>, [gap(t)] + <section>  (섹션 열림 유지)
      CLOSE   섹션 열림이면 </section>                       (섹션 닫힘)
      종료:   섹션 열림이면 </section>

    빈 갭 / 빈 섹션이 생기면 그대로 출력 — 사용자가 빈 마커 시퀀스를
    의도적으로 적었을 수 있으니 builder 에서 정리하지 않는다.
    """
    parts = _SENTINEL_SPLIT_RE.split(html)
    # parts: [text0, marker1, text1, marker2, ...]

    out = [_gap_html(opening_title), '<section>\n']
    section_open = True

    out.append(parts[0])

    for i in range(1, len(parts), 2):
        marker = parts[i]
        text_after = parts[i + 1] if i + 1 < len(parts) else ''

        if marker == 'CLOSE':
            if section_open:
                out.append('\n</section>\n')
                section_open = False
        elif marker.startswith('OPEN:'):
            title = marker[len('OPEN:'):].strip()
            if section_open:
                out.append('\n</section>\n')
            out.append(_gap_html(title))
            out.append('<section>\n')
            section_open = True

        out.append(text_after)

    if section_open:
        out.append('\n</section>')

    return ''.join(out)


# ════════════════════════════════════════════════════════════════
# Asset path rewriting  (§ 7.2)
# ════════════════════════════════════════════════════════════════

_ABSOLUTE_PREFIXES = ('https://', 'http://', '//', '/')


def rewrite_asset_path(url: str, slug: str) -> str:
    """상대 URL 을 /{slug}/... 절대경로로 재작성 (v0.5.2 자산 경로 일원화).

    v0.5.1 까지는 `/src/{slug}/...` 였으나, v0.5.2 부터 글 자산이 글의
    index.html 과 같은 폴더 (`dist/{slug}/`) 에 들어가도록 일원화됨.
    """
    if not url:
        return url
    for prefix in _ABSOLUTE_PREFIXES:
        if url.startswith(prefix):
            return url
    clean = re.sub(r'^\./', '', url)
    if clean.startswith('/'):
        return clean
    return f'/{slug}/{clean}'


def rewrite_asset_paths_in_html(html: str, slug: str) -> str:
    def replace_attr(m: re.Match) -> str:
        attr = m.group(1)
        quote = m.group(2)
        url = m.group(3)
        new_url = rewrite_asset_path(url, slug)
        return f'{attr}={quote}{new_url}{quote}'

    pattern = r'(src|href|data-src|data-href)=(["\'])([^"\']+)\2'
    return re.sub(pattern, replace_attr, html)


# ════════════════════════════════════════════════════════════════
# Markdown rendering  (Parsedown 1.7.4 Python 포팅 — parsedown.py)
# ════════════════════════════════════════════════════════════════

def render_markdown(text: str) -> str:
    """preprocess 가 끝난 markdown 을 HTML 로 렌더."""
    return Parsedown().text(text)


# ════════════════════════════════════════════════════════════════
# PHP function simulation (imgBox / imgSlideBox)
# ════════════════════════════════════════════════════════════════
#
# 원본 PHP 서버는 `PHP/GlobalFunctions.php`(imgBox/imgSlideBox)
# 와 `PHP/GlobalVariables.php`(서명 변수) 를 auto_prepend 해 글 본문의
# `<?php … ?>` 블록을 런타임에 실행했다.
# 정적 빌드에는 그 런타임이 없으므로, 작성자가 .html
# 본문에 쓴 imgBox/imgSlideBox PHP 를 빌드 시점에 정적 HTML 로 펼친다.
#
# v1.1.1 — 다중 구문 블록 지원 (배포 사고 수정):
#   이전 구현은 한 블록당 호출 1개인 `<?php func(args) ?>` 한 줄 형태
#   만 시뮬레이트했다. 실제 본문은 거의 다 다중 구문 블록
#       <?php
#           global $site_credit;   // 서명 변수 선언
#           imgBox("a.png", "캡션 {$site_credit}");
#           imgBox("b.png", "캡션");
#       ?>
#   형태라 시뮬레이트에 실패해 원본 PHP 가 그대로 dist 로 샜고,
#   런타임이 없는 정적 빌드에서 `Call to undefined function imgBox()` (또는
#   미정의 전역 변수) fatal 이 나 그 지점부터 응답이 잘렸다.
#   이제 블록 전체를 토큰 스캔해 주석(`//` `#` `/* */`)·`global` 선언·
#   세미콜론을 무시하고, 남는 게 imgBox/imgSlideBox 호출뿐이면 정적
#   HTML 로 펼친다. 살아있는 다른 구문이 하나라도 있으면 블록을 원문
#   그대로 둔다 (보수적 — 진짜 동적 PHP 는 건드리지 않음).


def _interpolate_php(s: str, php_globals: dict) -> str:
    """PHP 큰따옴표 문자열 보간: `{$name}` / `$name` → php_globals[name].

    정의 안 된 변수는 빈 문자열 (PHP 의 미정의 변수 echo 동작과 동일).
    작은따옴표 인자에는 호출하지 않는다 (PHP 가 보간 안 함).
    """
    s = re.sub(r'\{\$([A-Za-z_]\w*)\}',
               lambda m: str(php_globals.get(m.group(1), '')), s)
    s = re.sub(r'\$([A-Za-z_]\w*)',
               lambda m: str(php_globals.get(m.group(1), '')), s)
    return s


def _simulate_imgbox(src: str, exp: str, alt: str, slug: str) -> str:
    """imgBox PHP 호출 → 정적 `<div class="imgBox">`.

    `exp`(캡션) 는 **이스케이프하지 않는다** — 정본 GlobalFunctions.php
    의 imgBox 가 `{$exp}` 를 그대로 echo 했고, 작성자가 캡션에 `<br>`·
    `&nbsp;`·`<a …>` 와 서명 변수 보간을 의도적으로 넣기 때문이다(정적
    빌드가 원래 사이트와 같은 결과를 내야 함). `alt` 는 속성값이라
    안전을 위해 이스케이프를 유지한다.
    """
    url = rewrite_asset_path(src, slug)
    alt = alt or ''
    if exp:
        return (f'<div class="imgBox">\n'
                f'  <img src="{url}" alt="{escape_html(alt)}">\n'
                f'  <p class="caption">{exp}</p>\n'
                f'</div>')
    return (f'<div class="imgBox">\n'
            f'  <img src="{url}" alt="{escape_html(alt)}">\n'
            f'</div>')


def _simulate_imgslidebox(dir_path: str, slug: str, article_dir: Path) -> str:
    clean = re.sub(r'^\./', '', dir_path)
    slide_src_dir = article_dir / clean
    if not slide_src_dir.is_dir():
        return f'<!-- imgSlideBox: directory not found: {dir_path} -->'

    img_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}
    images = sorted(
        f for f in slide_src_dir.iterdir()
        if f.is_file() and f.suffix.lower() in img_exts
    )
    if not images:
        return f'<!-- imgSlideBox: no images in {dir_path} -->'

    slides = []
    for idx, img in enumerate(images):
        # v0.5.2: 자산 경로 일원화 — /src/{slug}/... → /{slug}/...
        url = f'/{slug}/{clean}/{img.name}'
        cls = 'slide active' if idx == 0 else 'slide'
        slides.append(f'  <img src="{url}" class="{cls}" alt="{escape_html(img.name)}">')

    slide_html = '\n'.join(slides)
    return (f'<div class="imgSlideBox" data-slug="{slug}">\n'
            f'{slide_html}\n'
            f'  <button class="prev">&#8249;</button>\n'
            f'  <button class="next">&#8250;</button>\n'
            f'</div>')


def _php_call_args(text: str, start: int) -> tuple:
    """`(` 직후 `start` 부터 짝맞춤 `)` 까지 스캔, 인자 목록을 돌려준다.

    quote(작은/큰따옴표, 백슬래시 이스케이프)·중첩 괄호를 인식한다.
    반환: (args, close_idx) — args 는 (값, 따옴표문자|None) 튜플 리스트,
    close_idx 는 닫는 `)` 의 인덱스. 짝이 안 맞으면 (None, None).
    따옴표 문자열은 따옴표를 벗긴 본문만, 그 외(상수/숫자/변수)는 원문.
    """
    args = []
    buf = []
    quote = None          # 현재 문자열 안이면 그 따옴표 문자
    cur_quote = None      # 이 인자가 따옴표 문자열이면 그 따옴표 문자
    depth = 1
    i = start
    n = len(text)
    while i < n:
        ch = text[i]
        if quote:
            if ch == '\\' and i + 1 < n:
                # PHP 문자열 이스케이프 — 다음 문자를 그대로 보존
                buf.append(text[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
                i += 1
                continue
            buf.append(ch)
            i += 1
            continue
        if ch in ('"', "'"):
            quote = ch
            cur_quote = ch
            i += 1
            continue
        if ch == '(':
            depth += 1
            buf.append(ch)
            i += 1
            continue
        if ch == ')':
            depth -= 1
            if depth == 0:
                val = ''.join(buf).strip()
                if val or cur_quote is not None or args:
                    args.append((val, cur_quote))
                return args, i
            buf.append(ch)
            i += 1
            continue
        if ch == ',' and depth == 1:
            args.append((''.join(buf).strip(), cur_quote))
            buf = []
            cur_quote = None
            i += 1
            continue
        buf.append(ch)
        i += 1
    return None, None


def _find_php_block_end(text: str, i: int) -> int:
    """`<?php` 직후 인덱스 `i` 부터 블록을 닫는 `?>` 의 `?` 위치를 찾는다.

    PHP 규칙: `?>` 는 문자열·`/* */` 안에서는 블록을 닫지 않지만,
    `//`·`#` 줄 주석 안에서는 닫는다(그래서 `<?php // x ?>` 가 유효).
    못 찾으면 -1.
    """
    n = len(text)
    state = 'N'   # N 평문 / S '..' / D ".." / L 줄주석 / B /*..*/
    while i < n:
        ch = text[i]
        if state == 'N':
            if ch == '?' and i + 1 < n and text[i + 1] == '>':
                return i
            if ch == "'":
                state = 'S'
            elif ch == '"':
                state = 'D'
            elif ch == '/' and i + 1 < n and text[i + 1] == '/':
                state = 'L'
                i += 2
                continue
            elif ch == '#':
                state = 'L'
            elif ch == '/' and i + 1 < n and text[i + 1] == '*':
                state = 'B'
                i += 2
                continue
        elif state == 'S':
            if ch == '\\' and i + 1 < n:
                i += 2
                continue
            if ch == "'":
                state = 'N'
        elif state == 'D':
            if ch == '\\' and i + 1 < n:
                i += 2
                continue
            if ch == '"':
                state = 'N'
        elif state == 'L':
            if ch == '?' and i + 1 < n and text[i + 1] == '>':
                return i
            if ch == '\n':
                state = 'N'
        elif state == 'B':
            if ch == '*' and i + 1 < n and text[i + 1] == '/':
                state = 'N'
                i += 2
                continue
        i += 1
    return -1


_PHP_IDENT_RE = re.compile(r'[A-Za-z_]\w*')


def _simulate_php_block(interior: str, slug: str, article_dir: Path,
                        php_globals: dict) -> tuple:
    """`<?php` 와 `?>` 사이 본문을 정적 HTML 로 펼친다.

    반환: (html, ok). ok=False 면 imgBox/imgSlideBox·주석·`global`·`;`
    이외의 살아있는 구문이 있다는 뜻 — 호출부가 블록을 원문 그대로 둔다.
    ok=True 이고 호출이 0개면 (전부 주석/global) html='' (블록 소멸).
    """
    parts = []
    i = 0
    n = len(interior)
    while i < n:
        ch = interior[i]
        if ch.isspace():
            i += 1
            continue
        if ch == ';':
            i += 1
            continue
        if interior.startswith('//', i) or ch == '#':
            nl = interior.find('\n', i)
            i = n if nl == -1 else nl + 1
            continue
        if interior.startswith('/*', i):
            end = interior.find('*/', i + 2)
            if end == -1:
                return '', False          # 닫히지 않은 블록 주석
            i = end + 2
            continue
        m = _PHP_IDENT_RE.match(interior, i)
        if not m:
            return '', False              # `$x = …`, `<?=` 등 — 동적
        ident = m.group(0)
        j = m.end()
        if ident == 'global':
            # `global $a, $b;` 선언 — 정적 출력에선 무의미, 건너뛴다.
            semi = interior.find(';', j)
            i = n if semi == -1 else semi + 1
            continue
        # 함수 호출이어야 함: 식별자 뒤 (공백 후) `(`
        k = j
        while k < n and interior[k].isspace():
            k += 1
        if k >= n or interior[k] != '(':
            return '', False              # `echo $x` 등 — 동적
        args, close = _php_call_args(interior, k + 1)
        if args is None:
            return '', False              # 괄호 짝 안 맞음
        # 닫는 `)` 뒤 선택적 `;` 소비
        i = close + 1
        while i < n and interior[i].isspace():
            i += 1
        if i < n and interior[i] == ';':
            i += 1

        def _val(idx):
            if idx >= len(args):
                return ''
            raw, q = args[idx]
            return _interpolate_php(raw, php_globals) if q == '"' else raw

        if ident == 'imgBox':
            parts.append(_simulate_imgbox(_val(0), _val(1), _val(2), slug))
        elif ident == 'imgSlideBox':
            parts.append(_simulate_imgslidebox(_val(0), slug, article_dir))
        else:
            return '', False              # 알 수 없는 살아있는 함수
    return '\n'.join(parts), True


# PHP 여는 태그. v1.14.1: PHP 렉서와 동일하게 `<?php` 를 **대소문자 무시**로
# 인식(`<?PHP`/`<?Php` 도 실행됨)하고, 짧은 echo 태그 `<?=` 도 인식한다.
# `<?= imgBox(...) ?>` 는 `echo imgBox(...)` 의미라 안의 호출을 그대로 펼친다.
# (`<?` 짧은 태그는 short_open_tag 기본 off 라 의도적으로 제외.)
_PHP_OPEN_RE = re.compile(r'<\?php|<\?=', re.IGNORECASE)


def simulate_php_in_html(text: str, slug: str, article_dir: Path,
                         php_globals: dict = None) -> str:
    """본문의 `<?php … ?>` / `<?= … ?>` 블록을 정적 HTML 로 펼친다.

    imgBox/imgSlideBox 호출(과 주석·`global`·`;`)만 든 블록은 통째로
    정적 HTML 로 치환되어 더 이상 라이브 PHP 가 아니다. 그 외 동적
    구문이 섞인 블록은 원문 그대로 보존한다(검색 페이지 등 보호).
    """
    php_globals = php_globals or {}
    out = []
    pos = 0
    while True:
        m = _PHP_OPEN_RE.search(text, pos)
        if m is None:
            out.append(text[pos:])
            break
        idx = m.start()
        open_len = m.end() - m.start()    # `<?php`=5, `<?=`=3
        close = _find_php_block_end(text, idx + open_len)
        if close == -1:
            out.append(text[pos:])        # 닫히지 않은 블록 — 원문 보존
            break
        block_end = close + 2             # `?>` 다음
        interior = text[idx + open_len:close]
        html, ok = _simulate_php_block(interior, slug, article_dir,
                                       php_globals)
        out.append(text[pos:idx])
        out.append(html if ok else text[idx:block_end])
        pos = block_end
    return ''.join(out)


def has_live_php(html: str) -> bool:
    # v1.14.1: `<?PHP` 대소문자 변종·`<?=` 까지 라이브 PHP 로 본다 —
    # simulate_php_in_html 와 동일 기준이어야 빌더의 .php/.html 분기가
    # 시뮬레이션과 어긋나지 않는다(대문자 태그가 .html 로 새는 사고 방지).
    return _PHP_OPEN_RE.search(html) is not None


def parse_php_globals(raw) -> dict:
    """site.yaml `php_globals:` 블록 → `{변수명: 문자열}`.

    원본 PHP 서버의 `PHP/GlobalVariables.php` 가 auto_prepend 하던
    서명 변수($site_credit 등)를 운영자가 site.yaml 에 옮겨 적는
    자리. 정적 빌드는 그 런타임이 없으므로 여기에 값을 두면 imgBox
    캡션의 `{$name}` 보간이 빌드 시점에 치환된다(`_interpolate_php`).

    변수명 앞의 `$` 는 있으면 떼고, 값은 문자열로 강제. dict 가 아니면
    `{}` (forward compat — 옛/빈 site.yaml 도 그냥 보간 없음).
    """
    if not isinstance(raw, dict):
        return {}
    out = {}
    for k, v in raw.items():
        if k is None:
            continue
        name = str(k).lstrip('$').strip()
        if name:
            out[name] = '' if v is None else str(v)
    return out


# ════════════════════════════════════════════════════════════════
# Finalize stage  (parser-agnostic)
# ════════════════════════════════════════════════════════════════
#
# v0.5.5: 본문 첫 단락 / 첫 이미지 추출 로직 제거. SEO description /
# og_image / 갤러리 썸네일 / 피드 summary 가 더 이상 본문에서 휴리스틱
# 추출된 값을 사용하지 않는다 — 모두 author 가 meta.yaml 에 명시한 값만
# 사용. RenderResult 도 `html` 한 필드로 슬림화.


def finalize_md_html(html: str, slug: str, article_dir: Path,
                     php_globals: dict = None) -> RenderResult:
    final = rewrite_asset_paths_in_html(html, slug)
    final = simulate_php_in_html(final, slug, article_dir, php_globals)
    return RenderResult(html=final)


def render_article_md(text: str, slug: str, article_dir: Path,
                      php_globals: dict = None) -> RenderResult:
    pre = preprocess_md_custom_syntax(text)
    raw_html = render_markdown(pre)
    return finalize_md_html(raw_html, slug, article_dir, php_globals)


def process_html(text: str, slug: str, article_dir: Path,
                 php_globals: dict = None) -> RenderResult:
    """content.html 처리: PHP 함수 시뮬레이션 + asset 경로 재작성."""
    text = simulate_php_in_html(text, slug, article_dir, php_globals)
    text = rewrite_asset_paths_in_html(text, slug)
    return RenderResult(html=text)


# ════════════════════════════════════════════════════════════════
# Per-article tag style overrides  (meta.yaml `styles:`)
# ════════════════════════════════════════════════════════════════


def normalize_styles(raw):
    """meta.yaml 의 `styles:` 키를 두 채널로 분리해서 파싱.

    v0.6.3 부터 styles 키가 두 종류의 자식을 동시에 가질 수 있다:
      - 정수 키 (1, 2, 3, ...) — 값은 글 폴더 안의 외부 CSS 파일 상대 경로
        문자열. 정수 키 오름차순 (1 → 2 → 3) 이 head 의 link 태그 출력
        순서가 된다.
      - 문자열 키 (tag 또는 selector) — 값은 인라인 룰 dict (속성:값).
        v0.5.x 까지의 동작 그대로. 머리 안에 `<style>` 블록으로 inject.

    반환: (sheets, rules)
      sheets : list[str] — 외부 CSS 파일의 상대 경로 (정수 키 오름차순).
                            파일 존재 검증은 호출자 (Builder) 가 별도 수행.
      rules  : dict[str, dict[str, str]] — 인라인 룰 (v0.5.x 형식 그대로).

    파서 정책: scripts/yaml_parser 의 토크나이저는 키를 *모두 str 로* 반환
    하므로 `1:` 도 `'1'` 으로 들어온다 — `int(key)` 변환이 성공하면 외부
    CSS 채널로, 실패하면 문자열 (tag/selector) 채널로 분기. PyYAML 류 파서가
    int 키를 그대로 주는 환경에서도 동작하도록 isinstance(int) 도 같이 인식.
    값이 기대 타입과 다른 엔트리는 *조용히 무시* — 형식 오류는 호출자
    (Builder) 가 더 풍부한 문맥과 함께 issue 로 라우팅한다. 빈 입력 / None /
    비-dict 입력은 ([], {}) 폴백.
    """
    if not raw or not isinstance(raw, dict):
        return [], {}
    sheet_items = []  # (int_key, path_str)
    rules = {}
    for key, value in raw.items():
        int_key = _coerce_int_key(key)
        if int_key is not None:
            if not isinstance(value, str):
                continue
            path = value.strip()
            if path:
                sheet_items.append((int_key, path))
            continue
        # 인라인 룰 — 키를 문자열 selector 로 다룬다.
        if not isinstance(value, dict):
            continue
        normalized_props = {}
        for prop, val in value.items():
            if val is None:
                continue
            normalized_props[str(prop).strip()] = str(val).strip()
        if normalized_props:
            rules[str(key).strip()] = normalized_props
    sheet_items.sort(key=lambda kv: kv[0])
    sheets = [p for (_, p) in sheet_items]
    return sheets, rules


def _coerce_int_key(key):
    """styles 키를 외부 CSS 채널의 정수 키로 해석할 수 있으면 int, 아니면 None.

    yaml_parser 가 `1:` 을 `'1'` 으로 반환하므로 str 도 받아 변환 시도.
    bool 은 거부 (YAML 의 `true:` 같은 키가 isinstance(int) 통과하는 함정 방지).
    """
    if isinstance(key, bool):
        return None
    if isinstance(key, int):
        return key
    if isinstance(key, str):
        s = key.strip()
        if not s:
            return None
        try:
            return int(s)
        except ValueError:
            return None
    return None


def _resolve_selector(tag_or_selector: str) -> str:
    """meta.yaml styles 의 문자열 키를 CSS 선택자로 해석.

    복합 선택자 문자 ( · , · > · + · ~ · . · # · : 공백) 가 하나라도 있으면
    작성자가 적은 그대로 쓰고, 그 외 (= 단일 태그명) 는 본문 안에서만
    적용되도록 `section TAG` 로 감싼다. README §4-6 의 "tag 키는 section
    TAG 로 자동 래핑" 규칙.
    """
    raw = tag_or_selector.strip()
    if not raw:
        return ''
    if any(ch in raw for ch in (' ', ',', '>', '+', '~', '.', '#', ':')):
        return raw
    return f'section {raw}'


def render_inline_styles(rules: dict) -> str:
    """인라인 룰 dict 을 head 의 `<style>` 블록으로 렌더.

    v0.6.3 에서 옛 `render_article_styles` 가 이름 변경 — 출력 텍스트는
    동일. 정수 키 (외부 CSS 파일) 와 분리된 *문자열 키* 만 입력으로 받음.
    빈 입력이면 빈 문자열.
    """
    if not rules:
        return ''
    out_rules = []
    for tag, props in rules.items():
        if not props:
            continue
        selector = _resolve_selector(tag)
        if not selector:
            continue
        decls = '; '.join(f'{p}: {v}' for p, v in props.items())
        out_rules.append(f'    {selector} {{ {decls}; }}')
    if not out_rules:
        return ''
    return '<style>\n' + '\n'.join(out_rules) + '\n  </style>'


def render_stylesheet_links(sheets, url_prefix: str) -> str:
    """외부 CSS 파일 리스트를 head 의 `<link>` 태그들로 렌더.

    각 항목은 페이지의 source 폴더 기준 상대 경로. URL 은 페이지 종류 별
    site-absolute 접두 + 상대 경로.

    v0.6.4 변경 — 시그니처 일반화. v0.6.3 의 `(sheets, slug: str)` 는 글의
    `/{slug}/<rel>` 만 만들 수 있었으나, v0.6.4 에서 카테고리/홈도 같은
    함수를 쓰도록 두 번째 인자를 `url_prefix` 로 받는다. 호출 측이 페이지
    종류에 맞게 접두를 구성:
      - 글: f'/{m.slug}/'
      - 카테고리: '/' + '/'.join(cat.slug_path) + '/'
      - 홈: '/'

    url_prefix 는 trailing '/' 을 가지고 있어야 한다 (없으면 자동 보정).

    파일 존재 검증은 호출자 (Builder 의 _parse_frontmatter /
    _parse_category_meta_file) 에서 수행되어 이 함수에 도달하는 sheets 는
    *해당 페이지의 source 폴더에 실제로 존재한다고 가정한다*. 빈 sheets 면
    빈 문자열 (head 의 placeholder 라인이 line-eating 되어 빈 줄이 남지
    않도록 빌더가 별도 처리).
    """
    if not sheets:
        return ''
    if url_prefix is None:
        return ''
    prefix = url_prefix
    if not prefix.endswith('/'):
        prefix = prefix + '/'
    if not prefix.startswith('/'):
        prefix = '/' + prefix
    lines = []
    for rel in sheets:
        # 정규화 — Windows 경로 호환 + leading './' 제거.
        norm = str(rel).replace('\\', '/').strip()
        while norm.startswith('./'):
            norm = norm[2:]
        # 파서가 절대경로 / '..' 이탈을 미리 거부했으므로 여기 도달하는 norm
        # 은 source 폴더 안의 깨끗한 상대 경로.
        url = f'{prefix}{norm}'
        lines.append(f"    <link href='{url}' rel='stylesheet' type='text/css'>")
    return '\n'.join(lines)

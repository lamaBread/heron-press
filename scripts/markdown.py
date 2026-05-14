"""마크다운 렌더링 + 본문 후처리.

파이프라인 (글 .md 한 편 기준):
  1. preprocess_md_custom_syntax(text) — 사용자 정의 문법(imgBox, 섹션 마커)
                                          → raw HTML / sentinel 주석
  2. Parsedown().text(text) → str — 순수 MD → HTML (parsedown.py)
  3. finalize_md_html(html, slug, dir) — asset path 재작성, PHP 함수 시뮬레이션,
                                         first paragraph / image 추출
  4. resolve_section_markers(html, title) — sentinel 주석 → 실제 gap/section
                                            마커, 본문을 자동 첫 갭+섹션으로
                                            감싸기. (builder 가 호출)

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

_IMGBOX_LINE_RE = re.compile(
    r'^!\[\[([^\]]*)\]\]\(([^)]+)\)(?:\s+\{([^}]*)\})?\s*$',
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
        if desc:
            desc_e = escape_html(desc)
            return (f'<div class="imgBox">\n'
                    f'  <img src="{url}" alt="{alt_e}">\n'
                    f'  <p class="caption">{desc_e}</p>\n'
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

def _simulate_imgbox(src: str, exp: str, alt: str, slug: str) -> str:
    url = rewrite_asset_path(src, slug)
    alt = alt or ''
    if exp:
        return (f'<div class="imgBox">\n'
                f'  <img src="{url}" alt="{escape_html(alt)}">\n'
                f'  <p class="caption">{escape_html(exp)}</p>\n'
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


def _parse_php_args(args_str: str) -> list:
    args = []
    current = ''
    in_q = None
    for ch in args_str:
        if in_q:
            if ch == in_q:
                in_q = None
            else:
                current += ch
        elif ch in ('"', "'"):
            in_q = ch
        elif ch == ',':
            args.append(current.strip())
            current = ''
        else:
            current += ch
    if current.strip() or in_q is not None:
        args.append(current.strip())
    return args


_PHP_CALL_OPEN_RE = re.compile(r'<\?php\s+(\w+)\(')
_PHP_CLOSE_RE = re.compile(r'\s*\?>')


def _scan_php_args(text: str, start: int) -> tuple:
    """`(` 직후부터 짝맞춤 `)` 까지 quote/nested parens 인식하며 스캔.

    v0.4.2: 이전의 `\\(([^)]*)\\)` 정규식은 인자 안의 `)` 를 처리 못 해
    `imgBox("a(b).jpg", ...)` 같은 입력이 깨졌다. 이제 nested parens 와
    quote 안의 `)` 모두 정상 처리.

    반환: (args_str, close_paren_index)  매칭 실패 시 (None, None).
    """
    depth = 1
    in_q = None
    i = start
    n = len(text)
    while i < n:
        ch = text[i]
        if in_q:
            if ch == in_q:
                in_q = None
        elif ch in ('"', "'"):
            in_q = ch
        elif ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                return text[start:i], i
        i += 1
    return None, None


def simulate_php_in_html(text: str, slug: str, article_dir: Path) -> str:
    out = []
    pos = 0
    while True:
        m = _PHP_CALL_OPEN_RE.search(text, pos)
        if not m:
            break
        args_str, close_paren = _scan_php_args(text, m.end())
        if args_str is None:
            out.append(text[pos:m.end()])
            pos = m.end()
            continue
        close_m = _PHP_CLOSE_RE.match(text, close_paren + 1)
        if not close_m:
            out.append(text[pos:m.end()])
            pos = m.end()
            continue

        func = m.group(1)
        args = _parse_php_args(args_str)
        out.append(text[pos:m.start()])

        if func == 'imgBox':
            src = args[0] if len(args) > 0 else ''
            exp = args[1] if len(args) > 1 else ''
            alt = args[2] if len(args) > 2 else ''
            out.append(_simulate_imgbox(src, exp, alt, slug))
        elif func == 'imgSlideBox':
            dir_path = args[0] if args else ''
            out.append(_simulate_imgslidebox(dir_path, slug, article_dir))
        else:
            out.append(text[m.start():close_m.end()])

        pos = close_m.end()

    out.append(text[pos:])
    return ''.join(out)


def has_live_php(html: str) -> bool:
    return '<?php' in html or '<?=' in html


# ════════════════════════════════════════════════════════════════
# Finalize stage  (parser-agnostic)
# ════════════════════════════════════════════════════════════════

_FIRST_P_RE = re.compile(r'<p[^>]*>(.*?)</p>', re.DOTALL)
_FIRST_IMG_RE = re.compile(r'<img\s[^>]*src="([^"]+)"')


def finalize_md_html(html: str, slug: str, article_dir: Path) -> RenderResult:
    final = rewrite_asset_paths_in_html(html, slug)
    final = simulate_php_in_html(final, slug, article_dir)

    p_match = _FIRST_P_RE.search(final)
    first_paragraph = ''
    if p_match:
        first_paragraph = re.sub(r'<[^>]+>', '', p_match.group(1)).strip()

    img_match = _FIRST_IMG_RE.search(final)
    first_image = img_match.group(1) if img_match else None

    return RenderResult(
        html=final,
        first_paragraph=first_paragraph,
        first_image=first_image,
    )


def render_article_md(text: str, slug: str, article_dir: Path) -> RenderResult:
    pre = preprocess_md_custom_syntax(text)
    raw_html = render_markdown(pre)
    return finalize_md_html(raw_html, slug, article_dir)


def process_html(text: str, slug: str, article_dir: Path) -> RenderResult:
    """content.html 처리: PHP 함수 시뮬레이션 + asset 경로 재작성."""
    text = simulate_php_in_html(text, slug, article_dir)
    text = rewrite_asset_paths_in_html(text, slug)

    p_match = _FIRST_P_RE.search(text)
    first_paragraph = ''
    if p_match:
        first_paragraph = re.sub(r'<[^>]+>', '', p_match.group(1)).strip()

    img_match = _FIRST_IMG_RE.search(text)
    first_image = img_match.group(1) if img_match else None

    return RenderResult(
        html=text,
        first_paragraph=first_paragraph,
        first_image=first_image,
    )


# ════════════════════════════════════════════════════════════════
# Per-article tag style overrides  (meta.yaml `styles:`)
# ════════════════════════════════════════════════════════════════

_SECTION_SCOPED_TAGS = {
    'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li',
    'blockquote',
    'a',
    'pre', 'code',
    'table', 'th', 'td',
    'img', 'strong', 'em', 'small', 'hr',
    'div', 'section',
}


def normalize_styles(raw) -> dict:
    if not raw or not isinstance(raw, dict):
        return {}
    out = {}
    for tag, props in raw.items():
        if not isinstance(props, dict):
            continue
        normalized_props = {}
        for prop, value in props.items():
            if value is None:
                continue
            normalized_props[str(prop).strip()] = str(value).strip()
        if normalized_props:
            out[str(tag).strip()] = normalized_props
    return out


def _resolve_selector(tag_or_selector: str) -> str:
    raw = tag_or_selector.strip()
    if not raw:
        return ''
    if any(ch in raw for ch in (' ', ',', '>', '+', '~', '.', '#', ':')):
        return raw
    if raw in _SECTION_SCOPED_TAGS:
        return f'section {raw}'
    return f'section {raw}'


def render_article_styles(styles: dict) -> str:
    if not styles:
        return ''
    rules = []
    for tag, props in styles.items():
        if not props:
            continue
        selector = _resolve_selector(tag)
        if not selector:
            continue
        decls = '; '.join(f'{p}: {v}' for p, v in props.items())
        rules.append(f'    {selector} {{ {decls}; }}')
    if not rules:
        return ''
    return '<style>\n' + '\n'.join(rules) + '\n  </style>'

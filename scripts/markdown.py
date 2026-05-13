"""마크다운 렌더링 + 본문 후처리.

파이프라인 (글 .md 한 편 기준):
  1. preprocess_md_custom_syntax(text) — 사용자 정의 문법(imgBox 등) → raw HTML
  2. Parsedown().text(text) → str — 순수 MD → HTML (parsedown.py)
  3. finalize_md_html(html, slug, dir) — asset path 재작성, PHP 함수 시뮬레이션,
                                         first paragraph / image 추출

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


def preprocess_md_custom_syntax(md: str) -> str:
    """프로젝트 고유 마크다운 확장을 raw HTML 로 치환.

    현재 지원:
      ![[alt]](url) {desc}  → <div class="imgBox">…</div>
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

    return _IMGBOX_LINE_RE.sub(replace_imgbox, md)


# ════════════════════════════════════════════════════════════════
# Asset path rewriting  (§ 7.2)
# ════════════════════════════════════════════════════════════════

_ABSOLUTE_PREFIXES = ('https://', 'http://', '//', '/')


def rewrite_asset_path(url: str, slug: str) -> str:
    """상대 URL 을 /src/{slug}/... 절대경로로 재작성."""
    if not url:
        return url
    for prefix in _ABSOLUTE_PREFIXES:
        if url.startswith(prefix):
            return url
    clean = re.sub(r'^\./', '', url)
    if clean.startswith('/'):
        return clean
    return f'/src/{slug}/{clean}'


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
        url = f'/src/{slug}/{clean}/{img.name}'
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

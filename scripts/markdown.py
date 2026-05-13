"""마크다운 파서 추상화 + 본문 후처리.

파이프라인:
  1. preprocess_md_custom_syntax(text) — 사용자 정의 문법(imgBox 등) → raw HTML
  2. MarkdownRenderer.parse(text) → str — 순수 MD → HTML
     구현체: BuiltinRenderer (Python), ParsedownRenderer (PHP subprocess)
  3. finalize_md_html(html, slug, dir) — asset path 재작성, PHP 함수 시뮬레이션,
                                         first paragraph / image 추출

v0.4.0 변경 없음 (v0.3 의 파서 추상화 + per-article styles 그대로).
"""
import re
import subprocess
from pathlib import Path
from typing import Optional

from .models import RenderResult


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
# MarkdownRenderer interface + implementations
# ════════════════════════════════════════════════════════════════

class MarkdownRenderer:
    """교체 가능한 마크다운 파서의 추상 베이스.
    구현체는 `parse(text) -> str` 만 제공하면 된다.
    text 는 preprocess_md_custom_syntax 가 적용된 후의 markdown 문자열.
    """
    name: str = 'abstract'

    def parse(self, text: str) -> str:
        raise NotImplementedError


class BuiltinRenderer(MarkdownRenderer):
    """순수 Python stdlib 으로 구현된 자체 파서."""
    name = 'builtin'

    def parse(self, text: str) -> str:
        return _builtin_md_to_html(text)


class ParsedownRenderer(MarkdownRenderer):
    """parsers/parsedown/Parsedown.php 를 PHP CLI 로 호출.
    원본 lama_website-main 과 완전히 동일한 출력을 보장.
    """
    name = 'parsedown'

    def __init__(self, base_dir: Path, die_fn, php_bin: str = 'php'):
        self.runner = base_dir / 'parsers' / 'parsedown' / 'run.php'
        self.php_bin = php_bin
        self._die = die_fn
        if not self.runner.exists():
            die_fn(f'Parsedown runner not found: {self.runner}')

    def parse(self, text: str) -> str:
        try:
            proc = subprocess.run(
                [self.php_bin, str(self.runner)],
                input=text.encode('utf-8'),
                capture_output=True,
                timeout=60,
            )
        except FileNotFoundError:
            self._die(f"PHP 실행 파일을 찾을 수 없음: '{self.php_bin}'.\n"
                      f"       PATH 에 php 를 추가하거나 site.yaml 의\n"
                      f"       markdown_parser 를 'builtin' 으로 바꾸세요.")
        if proc.returncode != 0:
            err = proc.stderr.decode('utf-8', errors='replace').strip()
            self._die(f'Parsedown 실패 (exit={proc.returncode}):\n{err}')
        return proc.stdout.decode('utf-8')


def make_markdown_renderer(name: str, base_dir: Path, die_fn) -> MarkdownRenderer:
    n = (name or 'builtin').strip().lower()
    if n in ('builtin', 'python', ''):
        return BuiltinRenderer()
    if n in ('parsedown', 'php'):
        return ParsedownRenderer(base_dir, die_fn)
    die_fn(f"알 수 없는 markdown_parser: '{name}'. 지원: builtin, parsedown.")


# ── Builtin renderer internals ────────────────────────────────

def _render_inline(text: str) -> str:
    def inline_code(m):
        return '<code>' + escape_html(m.group(1)) + '</code>'
    text = re.sub(r'`([^`]+)`', inline_code, text)

    def image(m):
        alt = m.group(1)
        url = m.group(2)
        return f'<img src="{url}" alt="{escape_html(alt)}">'
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', image, text)

    def link(m):
        link_text = m.group(1)
        url = m.group(2)
        return f'<a href="{url}">{link_text}</a>'
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, text)

    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    return text


def _builtin_md_to_html(text: str) -> str:
    lines = text.splitlines()
    n = len(lines)
    i = [0]
    output = []

    while i[0] < n:
        line = lines[i[0]]

        if line.startswith('```'):
            lang = line[3:].strip()
            code_lines = []
            i[0] += 1
            while i[0] < n and not lines[i[0]].startswith('```'):
                code_lines.append(escape_html(lines[i[0]]))
                i[0] += 1
            i[0] += 1  # skip closing ```
            lang_attr = f' class="language-{escape_html(lang)}"' if lang else ''
            output.append(f'<pre><code{lang_attr}>{chr(10).join(code_lines)}</code></pre>')
            continue

        hm = re.match(r'^(#{1,6})\s+(.*)', line)
        if hm:
            level = len(hm.group(1))
            content = _render_inline(hm.group(2).strip())
            output.append(f'<h{level}>{content}</h{level}>')
            i[0] += 1
            continue

        if re.match(r'^[-_*]{3,}\s*$', line.strip()):
            output.append('<hr>')
            i[0] += 1
            continue

        if line.startswith('> ') or line == '>':
            quote_lines = []
            while i[0] < n and (lines[i[0]].startswith('> ') or lines[i[0]] == '>'):
                quote_lines.append(lines[i[0]][2:] if lines[i[0]].startswith('> ') else '')
                i[0] += 1
            inner = _render_inline(' '.join(quote_lines))
            output.append(f'<blockquote><p>{inner}</p></blockquote>')
            continue

        if re.match(r'^[-*+] ', line):
            items = []
            while i[0] < n and re.match(r'^[-*+] ', lines[i[0]]):
                items.append(f'<li>{_render_inline(lines[i[0]][2:])}</li>')
                i[0] += 1
            output.append('<ul>' + ''.join(items) + '</ul>')
            continue

        if re.match(r'^\d+\. ', line):
            items = []
            while i[0] < n and re.match(r'^\d+\. ', lines[i[0]]):
                item_text = re.sub(r'^\d+\. ', '', lines[i[0]])
                items.append(f'<li>{_render_inline(item_text)}</li>')
                i[0] += 1
            output.append('<ol>' + ''.join(items) + '</ol>')
            continue

        if not line.strip():
            i[0] += 1
            continue

        if line.lstrip().startswith('<') and not line.lstrip().startswith('<p'):
            html_lines = [line]
            i[0] += 1
            while i[0] < n:
                next_line = lines[i[0]]
                if not next_line.strip():
                    break
                if re.match(r'^(#{1,6} |```|> |[-*+] |\d+\. )', next_line):
                    break
                html_lines.append(next_line)
                i[0] += 1
            output.append('\n'.join(html_lines))
            continue

        para_lines = []
        while i[0] < n:
            l = lines[i[0]]
            if not l.strip():
                break
            if re.match(r'^(#{1,6} |```|> |[-*+] |\d+\. )', l):
                break
            if re.match(r'^[-_*]{3,}\s*$', l.strip()):
                break
            para_lines.append(l)
            i[0] += 1
        if para_lines:
            para_html = _render_inline(' '.join(para_lines))
            output.append(f'<p>{para_html}</p>')

    return '\n'.join(output)


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


_PHP_CALL_RE = re.compile(r'<\?php\s+(\w+)\(([^)]*)\)\s*\?>')


def simulate_php_in_html(text: str, slug: str, article_dir: Path) -> str:
    def replace_php_call(m: re.Match) -> str:
        func = m.group(1)
        args = _parse_php_args(m.group(2))

        if func == 'imgBox':
            src = args[0] if len(args) > 0 else ''
            exp = args[1] if len(args) > 1 else ''
            alt = args[2] if len(args) > 2 else ''
            return _simulate_imgbox(src, exp, alt, slug)

        if func == 'imgSlideBox':
            dir_path = args[0] if args else ''
            return _simulate_imgslidebox(dir_path, slug, article_dir)

        return m.group(0)

    return _PHP_CALL_RE.sub(replace_php_call, text)


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


def render_article_md(text: str, slug: str, article_dir: Path,
                      renderer: MarkdownRenderer) -> RenderResult:
    pre = preprocess_md_custom_syntax(text)
    raw_html = renderer.parse(pre)
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

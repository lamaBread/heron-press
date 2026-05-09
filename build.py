#!/usr/bin/env python3
"""
siheonlee.com SSG v0.3.1 — Static Site Generator
Python 3.x stdlib only (markdown parsing may shell out to PHP).

v0.3.1 차이점 (vs v0.3):
  - 검색 기능 추가. 빌드 시 dist/search-index.json (한글 bigram + 영문 토큰
    역색인) 과 dist/search.php (검색 엔드포인트) 를 생성. 클라이언트 JS
    없이 서버 PHP 가 인덱스를 읽어 결과를 HTML 로 렌더.
  - 모든 페이지 nav 우측에 작은 검색창, 메인 페이지 section 상단에 inline
    검색창 추가. lama 미학에 맞춰 최소 장식.
  - tokenize() 의 Python·PHP 양쪽 일관성이 동작의 핵심. search.php 의
    search_tokenize() 와 build.py 의 _search_tokenize() 는 동일 로직.

v0.3 차이점 (vs v0.2):
  - 마크다운 파서를 추상화. site.yaml 의 `markdown_parser` 로 교체 가능.
      * builtin   — Python-only 자체 파서 (v0.2 의 그것)
      * parsedown — lama_website-main 에서 사용하는 PHP Parsedown.php 를
                    `php` 명령으로 호출 (parsers/parsedown/run.php).
  - meta.yaml 에 `styles:` 필드 추가. p, h1~h6, ul, ol, li, blockquote,
    a, code, pre, table, th, td, img, strong, em 등 lama_website-main 에서
    자주 쓰는 태그의 기본 속성을 글 단위로 조정 가능. 결과는 article.html
    의 `<style>` 블록으로 inject 되어 `section TAG` 선택자로 적용.
  - YAML 파서가 nested mapping 을 지원 (styles: 트리 파싱용).

Usage:
    python build.py           # full build
    python build.py --clean   # wipe dist/ before build
"""

import os
import re
import sys
import json
import shutil
import subprocess
import unicodedata
from pathlib import Path
from datetime import date as Date
from dataclasses import dataclass, field
from typing import Optional


# ════════════════════════════════════════════════════════════════
# YAML Parser — stdlib only, project-specific subset (§ 0)
# ════════════════════════════════════════════════════════════════

def _yaml_load(text: str) -> dict:
    """
    Minimal YAML parser supporting the subset used by this project:
      - key: value  (string, int, bool, null)
      - "quoted key": value  (legacy-map.yaml)
      - key:        → null
      - key: "str" / 'str'
      - key: [a, b]  (inline list)
      - key:\n  - item  (block list)
      - key:\n  subkey: val  (block map, nested mapping — v0.3)
      - key: |  (literal block scalar)
      - # comments
    """
    lines = text.splitlines()
    n = len(lines)
    i = [0]  # mutable index

    def get_indent(s: str) -> int:
        return len(s) - len(s.lstrip(' '))

    def parse_scalar(s: str):
        s = s.strip()
        if not s or s in ('null', '~', 'Null', 'NULL'):
            return None
        if s in ('true', 'True', 'TRUE'):
            return True
        if s in ('false', 'False', 'FALSE'):
            return False
        if (s.startswith('"') and s.endswith('"')) or \
           (s.startswith("'") and s.endswith("'")):
            return s[1:-1]
        try:
            return int(s)
        except ValueError:
            pass
        return s

    def parse_inline_list(inner: str) -> list:
        if not inner.strip():
            return []
        items = []
        cur = ''
        in_q = None
        for ch in inner:
            if in_q:
                if ch == in_q:
                    in_q = None
                cur += ch
            elif ch in ('"', "'"):
                in_q = ch
                cur += ch
            elif ch == ',':
                items.append(parse_scalar(cur.strip()))
                cur = ''
            else:
                cur += ch
        if cur.strip():
            items.append(parse_scalar(cur.strip()))
        return items

    def parse_literal_block(base_indent: int) -> str:
        result = []
        block_indent = None
        while i[0] < n:
            raw = lines[i[0]]
            if not raw.strip():
                result.append('')
                i[0] += 1
                continue
            indent = get_indent(raw)
            if block_indent is None:
                if indent <= base_indent:
                    break
                block_indent = indent
            if indent < block_indent:
                break
            result.append(raw[block_indent:])
            i[0] += 1
        while result and not result[-1]:
            result.pop()
        return '\n'.join(result) + '\n' if result else ''

    def parse_block_list(list_indent: int) -> list:
        items = []
        while i[0] < n:
            raw = lines[i[0]]
            stripped = raw.strip()
            if not stripped or stripped.startswith('#'):
                i[0] += 1
                continue
            indent = get_indent(raw)
            if indent < list_indent:
                break
            if indent == list_indent and stripped.startswith('- '):
                items.append(parse_scalar(stripped[2:]))
                i[0] += 1
            elif indent == list_indent and stripped == '-':
                items.append(None)
                i[0] += 1
            else:
                break
        return items

    def parse_block_map(map_indent: int) -> dict:
        """v0.3: parse nested key-value block at indent==map_indent."""
        out = {}
        while i[0] < n:
            raw = lines[i[0]]
            stripped = raw.strip()
            if not stripped or stripped.startswith('#'):
                i[0] += 1
                continue
            indent = get_indent(raw)
            if indent < map_indent:
                break
            if indent != map_indent:
                # Should not happen given recursive descent; bail to avoid loops.
                i[0] += 1
                continue
            parsed = parse_key_line(raw)
            if parsed is None:
                i[0] += 1
                continue
            k, v = parsed
            if v == '|':
                i[0] += 1
                out[k] = parse_literal_block(map_indent)
            elif v.startswith('[') and v.endswith(']'):
                out[k] = parse_inline_list(v[1:-1])
                i[0] += 1
            elif v == '':
                i[0] += 1
                if i[0] < n:
                    nxt = lines[i[0]]
                    nxt_stripped = nxt.strip()
                    nxt_indent = get_indent(nxt)
                    if nxt_indent > map_indent:
                        if nxt_stripped.startswith('- ') or nxt_stripped == '-':
                            out[k] = parse_block_list(nxt_indent)
                        else:
                            out[k] = parse_block_map(nxt_indent)
                        continue
                out[k] = None
            else:
                out[k] = parse_scalar(v)
                i[0] += 1
        return out

    def parse_key_line(raw: str):
        """Return (key, val_str) or None."""
        s = raw.strip()
        # Quoted key
        for q in ('"', "'"):
            if s.startswith(q):
                end = s.find(q, 1)
                if end < 0:
                    return None
                key = s[1:end]
                rest = s[end + 1:].strip()
                if rest.startswith(':'):
                    return key, rest[1:].strip()
                return None
        # Regular key: first colon not inside quotes
        m = re.match(r'^([^:#\'"]+?):\s*(.*)', s)
        if m:
            return m.group(1).strip(), m.group(2).strip()
        return None

    result = {}
    while i[0] < n:
        raw = lines[i[0]]
        stripped = raw.strip()
        if not stripped or stripped.startswith('#'):
            i[0] += 1
            continue

        parsed = parse_key_line(raw)
        if parsed is None:
            i[0] += 1
            continue

        key, val_str = parsed
        base_indent = get_indent(raw)

        if val_str == '|':
            i[0] += 1
            result[key] = parse_literal_block(base_indent)
        elif val_str.startswith('[') and val_str.endswith(']'):
            result[key] = parse_inline_list(val_str[1:-1])
            i[0] += 1
        elif val_str == '':
            i[0] += 1
            # Peek ahead for block list or nested map (v0.3)
            if i[0] < n:
                next_raw = lines[i[0]]
                next_stripped = next_raw.strip()
                next_indent = get_indent(next_raw)
                if next_indent > base_indent and next_stripped:
                    if next_stripped.startswith('- ') or next_stripped == '-':
                        result[key] = parse_block_list(next_indent)
                        continue
                    # Nested mapping
                    result[key] = parse_block_map(next_indent)
                    continue
            result[key] = None
        else:
            result[key] = parse_scalar(val_str)
            i[0] += 1

    return result


# ════════════════════════════════════════════════════════════════
# Data Models
# ════════════════════════════════════════════════════════════════

@dataclass
class SiteConfig:
    domain: str
    base_url: str
    name: str
    main_title: str
    default_author: str
    default_og_image: str
    default_title_prefix: str
    default_title_suffix: str
    copyright_holder: str
    copyright_year_start: int
    reserved_slugs: list
    warn_on_underscore_ref: bool
    warn_on_missing_asset: bool
    warn_on_stale_updated: bool
    home_excludes_categories: list
    home_sort: str
    description_truncate: int
    robots_txt_main: str
    robots_txt_legacy: str
    markdown_parser: str = 'parsedown'


@dataclass
class ArticleMeta:
    slug: str
    title: str
    date: str
    updated: Optional[str] = None
    seo_title_prefix: Optional[str] = None
    seo_title_suffix: Optional[str] = None
    seo_description: Optional[str] = None
    seo_keywords: Optional[list] = None
    seo_author: Optional[str] = None
    seo_canonical: Optional[str] = None
    seo_og_title: Optional[str] = None
    seo_og_description: Optional[str] = None
    seo_og_image: Optional[str] = None
    seo_og_image_alt: Optional[str] = None
    seo_og_type: str = 'article'
    seo_twitter_card: str = 'summary_large_image'
    seo_twitter_image: Optional[str] = None
    # v0.3: per-document tag style overrides
    # 예: {"p": {"text-indent": 0, "line-height": "1.5em"}, "h3": {...}}
    styles: dict = field(default_factory=dict)


@dataclass
class RenderResult:
    html: str
    first_paragraph: str
    first_image: Optional[str]


@dataclass
class Article:
    meta: ArticleMeta
    source_dir: Path
    content_file: Path
    category_path: list  # [folder_name, ...] from Articles/ to article folder


@dataclass
class Category:
    folder_name: str
    slug: str
    path: list          # [folder_name, ...] path from Articles/
    slug_path: list     # [slug, ...] built from path
    children: list = field(default_factory=list)   # sub-Category objects
    articles: list = field(default_factory=list)   # Article objects (direct)


# ════════════════════════════════════════════════════════════════
# Slug helpers
# ════════════════════════════════════════════════════════════════

def category_slug_from_name(name: str) -> str:
    """Convert category folder name → URL slug. (§ 4.7)"""
    s = unicodedata.normalize('NFKD', name)
    # Keep only ASCII letters, digits, spaces, hyphens, parentheses
    s = re.sub(r"[^A-Za-z0-9 \-()]", '', s)
    # Remove parentheses
    s = s.replace('(', '').replace(')', '')
    # Spaces and consecutive hyphens → single hyphen
    s = re.sub(r'[\s\-]+', '-', s)
    # Strip leading/trailing hyphens
    s = s.strip('-')
    return s.lower()


def is_underscore_path(p: Path, base: Path) -> bool:
    """True if any segment in path (relative to base) starts with _."""
    try:
        rel = p.relative_to(base)
    except ValueError:
        rel = p
    return any(part.startswith('_') for part in rel.parts)


# ════════════════════════════════════════════════════════════════
# Asset path rewriting  (§ 7.2)
# ════════════════════════════════════════════════════════════════

_ABSOLUTE_PREFIXES = ('https://', 'http://', '//', '/')


def rewrite_asset_path(url: str, slug: str) -> str:
    """Rewrite a relative asset URL to /src/{slug}/... absolute path."""
    if not url:
        return url
    for prefix in _ABSOLUTE_PREFIXES:
        if url.startswith(prefix):
            return url
    # Strip leading ./
    clean = url.lstrip('./')
    if url.startswith('./') or (not url.startswith('/') and not url.startswith('http')):
        clean = re.sub(r'^\./', '', url)
        if clean.startswith('/'):
            return clean
        return f'/src/{slug}/{clean}'
    return url


def rewrite_asset_paths_in_html(html: str, slug: str) -> str:
    """Rewrite src/href/data attributes in raw HTML for relative paths."""

    def replace_attr(m: re.Match) -> str:
        attr = m.group(1)
        quote = m.group(2)
        url = m.group(3)
        new_url = rewrite_asset_path(url, slug)
        return f'{attr}={quote}{new_url}{quote}'

    # Match src="...", href="...", data-src="..."
    pattern = r'(src|href|data-src|data-href)=(["\'])([^"\']+)\2'
    return re.sub(pattern, replace_attr, html)


# ════════════════════════════════════════════════════════════════
# Markdown Parser  (§ 8)
# ════════════════════════════════════════════════════════════════
#
# v0.3 구조:
#   1. preprocess_md_custom_syntax(text)   — 사용자 정의 문법(imgBox 등)을
#      raw HTML 으로 치환. 모든 파서 앞단에서 동일하게 수행.
#   2. MarkdownRenderer.parse(text) -> str — 순수 MD → HTML.
#      구현체: BuiltinRenderer (Python), ParsedownRenderer (PHP subprocess).
#   3. _finalize_md_html(html, slug, dir)  — 후처리.
#
# 새 파서 추가는 MarkdownRenderer 를 상속하고 make_markdown_renderer 에
# 한 줄을 추가하면 끝. 파서 교체는 site.yaml 의 `markdown_parser` 만 변경.

def _escape_html(s: str) -> str:
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


# ── Custom syntax preprocessing (parser-agnostic) ─────────────

_IMGBOX_LINE_RE = re.compile(
    r'^!\[\[([^\]]*)\]\]\(([^)]+)\)(?:\s+\{([^}]*)\})?\s*$',
    re.MULTILINE,
)


def preprocess_md_custom_syntax(md: str) -> str:
    """
    Replace project-specific markdown extensions with raw HTML so that
    any downstream parser leaves them untouched (Parsedown preserves
    block-level HTML; the builtin parser routes through its raw-HTML
    passthrough branch).

    Currently handled:
      - ![[alt]](url) {desc}  → <div class="imgBox">…</div>
        (lama_website-main 의 md_imgBox_guide.md 와 동일한 형식)
    """
    def replace_imgbox(m: re.Match) -> str:
        alt = m.group(1) or ''
        url = m.group(2)
        desc = m.group(3)
        alt_e = _escape_html(alt)
        if desc:
            desc_e = _escape_html(desc)
            return (f'<div class="imgBox">\n'
                    f'  <img src="{url}" alt="{alt_e}">\n'
                    f'  <p class="caption">{desc_e}</p>\n'
                    f'</div>')
        return (f'<div class="imgBox">\n'
                f'  <img src="{url}" alt="{alt_e}">\n'
                f'</div>')

    return _IMGBOX_LINE_RE.sub(replace_imgbox, md)


# ── MarkdownRenderer interface + implementations ──────────────

class MarkdownRenderer:
    """
    교체 가능한 마크다운 파서의 추상 베이스.
    구현체는 `parse(text) -> str` 만 제공하면 된다.
    text 는 preprocess_md_custom_syntax 가 적용된 후의 markdown 문자열.
    반환 HTML 은 후속 단계에서 asset path 재작성, PHP 시뮬레이션 등을 거친다.
    """
    name: str = 'abstract'

    def parse(self, text: str) -> str:
        raise NotImplementedError


class BuiltinRenderer(MarkdownRenderer):
    """순수 Python stdlib 으로 구현된 자체 파서 (v0.2 의 그것)."""
    name = 'builtin'

    def parse(self, text: str) -> str:
        return _builtin_md_to_html(text)


class ParsedownRenderer(MarkdownRenderer):
    """
    parsers/parsedown/Parsedown.php 를 PHP CLI 로 호출.
    원본 lama_website-main 과 완전히 동일한 출력을 보장.
    """
    name = 'parsedown'

    def __init__(self, base_dir: Path, php_bin: str = 'php'):
        self.runner = base_dir / 'parsers' / 'parsedown' / 'run.php'
        self.php_bin = php_bin
        if not self.runner.exists():
            _die(f'Parsedown runner not found: {self.runner}')

    def parse(self, text: str) -> str:
        try:
            proc = subprocess.run(
                [self.php_bin, str(self.runner)],
                input=text.encode('utf-8'),
                capture_output=True,
                timeout=60,
            )
        except FileNotFoundError:
            _die(f"PHP 실행 파일을 찾을 수 없음: '{self.php_bin}'.\n"
                 f"       PATH 에 php 를 추가하거나 site.yaml 의\n"
                 f"       markdown_parser 를 'builtin' 으로 바꾸세요.")
        if proc.returncode != 0:
            err = proc.stderr.decode('utf-8', errors='replace').strip()
            _die(f'Parsedown 실패 (exit={proc.returncode}):\n{err}')
        return proc.stdout.decode('utf-8')


def make_markdown_renderer(name: str, base_dir: Path) -> MarkdownRenderer:
    """파서 팩토리. 새 파서 추가 시 여기에 한 줄만 더하면 끝."""
    n = (name or 'builtin').strip().lower()
    if n in ('builtin', 'python', ''):
        return BuiltinRenderer()
    if n in ('parsedown', 'php'):
        return ParsedownRenderer(base_dir)
    _die(f"알 수 없는 markdown_parser: '{name}'. "
         f"지원: builtin, parsedown.")


# ── Builtin renderer internals (slug 무관 — 후처리에서 재작성) ──

def _render_inline(text: str) -> str:
    """Render inline markdown: bold, italic, code, links, images.
    Asset path 재작성은 finalize 단계에서 일괄 처리하므로 여기서는 URL 을 그대로 둠.
    """
    # Inline code (escape content)
    def inline_code(m):
        return '<code>' + _escape_html(m.group(1)) + '</code>'
    text = re.sub(r'`([^`]+)`', inline_code, text)

    # Images  ![alt](url) — URL 그대로 두고 finalize 에서 재작성
    def image(m):
        alt = m.group(1)
        url = m.group(2)
        return f'<img src="{url}" alt="{_escape_html(alt)}">'
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', image, text)

    # Links  [text](url)
    def link(m):
        link_text = m.group(1)
        url = m.group(2)
        return f'<a href="{url}">{link_text}</a>'
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, text)

    # Bold **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic *text*
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)

    return text


def _builtin_md_to_html(text: str) -> str:
    """Builtin Python markdown → HTML (raw, slug 무관)."""
    lines = text.splitlines()
    n = len(lines)
    i = [0]
    output = []

    while i[0] < n:
        line = lines[i[0]]

        # Fenced code block
        if line.startswith('```'):
            lang = line[3:].strip()
            code_lines = []
            i[0] += 1
            while i[0] < n and not lines[i[0]].startswith('```'):
                code_lines.append(_escape_html(lines[i[0]]))
                i[0] += 1
            i[0] += 1  # skip closing ```
            lang_attr = f' class="language-{_escape_html(lang)}"' if lang else ''
            output.append(f'<pre><code{lang_attr}>{chr(10).join(code_lines)}</code></pre>')
            continue

        # Heading  # H1 ... ###### H6
        hm = re.match(r'^(#{1,6})\s+(.*)', line)
        if hm:
            level = len(hm.group(1))
            content = _render_inline(hm.group(2).strip())
            output.append(f'<h{level}>{content}</h{level}>')
            i[0] += 1
            continue

        # Horizontal rule  ---  ___  ***
        if re.match(r'^[-_*]{3,}\s*$', line.strip()):
            output.append('<hr>')
            i[0] += 1
            continue

        # Blockquote
        if line.startswith('> ') or line == '>':
            quote_lines = []
            while i[0] < n and (lines[i[0]].startswith('> ') or lines[i[0]] == '>'):
                quote_lines.append(lines[i[0]][2:] if lines[i[0]].startswith('> ') else '')
                i[0] += 1
            inner = _render_inline(' '.join(quote_lines))
            output.append(f'<blockquote><p>{inner}</p></blockquote>')
            continue

        # Unordered list
        if re.match(r'^[-*+] ', line):
            items = []
            while i[0] < n and re.match(r'^[-*+] ', lines[i[0]]):
                items.append(f'<li>{_render_inline(lines[i[0]][2:])}</li>')
                i[0] += 1
            output.append('<ul>' + ''.join(items) + '</ul>')
            continue

        # Ordered list
        if re.match(r'^\d+\. ', line):
            items = []
            while i[0] < n and re.match(r'^\d+\. ', lines[i[0]]):
                item_text = re.sub(r'^\d+\. ', '', lines[i[0]])
                items.append(f'<li>{_render_inline(item_text)}</li>')
                i[0] += 1
            output.append('<ol>' + ''.join(items) + '</ol>')
            continue

        # Empty line
        if not line.strip():
            i[0] += 1
            continue

        # Raw HTML passthrough (§ 8.3)
        # imgBox preprocessing 결과로 생긴 <div class="imgBox"> 도 여기서 통과.
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

        # Paragraph
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


# ── Common finalize stage (parser-agnostic) ───────────────────

_FIRST_P_RE = re.compile(r'<p[^>]*>(.*?)</p>', re.DOTALL)
_FIRST_IMG_RE = re.compile(r'<img\s[^>]*src="([^"]+)"')


def finalize_md_html(html: str, slug: str, article_dir: Path) -> RenderResult:
    """Run project-specific HTML post-processing on parser output:
       - asset path rewriting
       - PHP function simulation (imgBox / imgSlideBox)
       - first paragraph / first image extraction
    """
    final = rewrite_asset_paths_in_html(html, slug)
    final = _simulate_php_in_html(final, slug, article_dir)

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
    """End-to-end: 사용자 정의 문법 전처리 → 파서 호출 → 후처리."""
    pre = preprocess_md_custom_syntax(text)
    raw_html = renderer.parse(pre)
    return finalize_md_html(raw_html, slug, article_dir)


# ════════════════════════════════════════════════════════════════
# Per-article tag style overrides  (v0.3)
# ════════════════════════════════════════════════════════════════
#
# meta.yaml 예시:
#
#   styles:
#     p:
#       text-indent: 0
#       line-height: 1.5em
#       margin-top: 0.4em
#       margin-bottom: 0.4em
#     h3:
#       margin-top: 1em
#     ul:
#       padding-left: 1em
#     blockquote:
#       border-left: 4px solid #ccc
#     a:
#       text-decoration: underline
#
# 결과로 article.html head 에 다음 형태의 <style> 가 inject 됨:
#
#   <style>
#   section p { text-indent: 0; line-height: 1.5em; ... }
#   section h3 { margin-top: 1em; }
#   ...
#   </style>
#
# 선택자는 항상 `section TAG` 로 묶여 common_template.css 의 같은 선택자
# (specificity 0,0,2) 를 source order 로 덮는다. 글마다 독립적으로 작동.

# section TAG 형태로 자동 wrap 할 화이트리스트.
# lama_website-main 의 common_template.css 에서 직접 스타일링하는 태그들.
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


def _normalize_styles(raw) -> dict:
    """meta.yaml 에서 읽은 styles 값을 표준 dict[str, dict[str, str]] 로 정규화."""
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
    """
    meta.yaml 의 키를 CSS 선택자로 변환:
      - 화이트리스트의 단일 태그 → `section TAG`
      - 그 외 (콤마, 공백, > 등 포함) → 그대로 사용 (사용자 책임)
    """
    raw = tag_or_selector.strip()
    if not raw:
        return ''
    # complex selector — leave as-is
    if any(ch in raw for ch in (' ', ',', '>', '+', '~', '.', '#', ':')):
        return raw
    if raw in _SECTION_SCOPED_TAGS:
        return f'section {raw}'
    # unknown bare token — still scope to section to avoid leakage
    return f'section {raw}'


def render_article_styles(styles: dict) -> str:
    """
    meta.yaml 의 styles dict 를 <style>…</style> 블록으로 변환.
    빈 dict 면 빈 문자열 반환.
    """
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


# ════════════════════════════════════════════════════════════════
# HTML Processor  (§ 9)
# ════════════════════════════════════════════════════════════════

def _simulate_imgbox(src: str, exp: str, alt: str, slug: str) -> str:
    """§ 9.1 imgBox PHP function simulation."""
    url = rewrite_asset_path(src, slug)
    alt = alt or ''
    if exp:
        return (f'<div class="imgBox">\n'
                f'  <img src="{url}" alt="{_escape_html(alt)}">\n'
                f'  <p class="caption">{_escape_html(exp)}</p>\n'
                f'</div>')
    return (f'<div class="imgBox">\n'
            f'  <img src="{url}" alt="{_escape_html(alt)}">\n'
            f'</div>')


def _simulate_imgslidebox(dir_path: str, slug: str, article_dir: Path) -> str:
    """§ 9.1 imgSlideBox PHP function simulation."""
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
        slides.append(f'  <img src="{url}" class="{cls}" alt="{_escape_html(img.name)}">')

    slide_html = '\n'.join(slides)
    return (f'<div class="imgSlideBox" data-slug="{slug}">\n'
            f'{slide_html}\n'
            f'  <button class="prev">&#8249;</button>\n'
            f'  <button class="next">&#8250;</button>\n'
            f'</div>')


def _parse_php_args(args_str: str) -> list:
    """Parse PHP function argument string into a list of string values."""
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


def _simulate_php_in_html(text: str, slug: str, article_dir: Path) -> str:
    """imgBox / imgSlideBox PHP 호출을 정적 HTML 로 치환."""
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

        # Unknown PHP function — return as-is (§ 9.3)
        return m.group(0)

    return _PHP_CALL_RE.sub(replace_php_call, text)


def process_html(text: str, slug: str, article_dir: Path) -> RenderResult:
    """Process content.html: simulate PHP functions, rewrite asset paths."""
    text = _simulate_php_in_html(text, slug, article_dir)
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


def has_live_php(html: str) -> bool:
    """§ 6.1 — detect surviving PHP tokens in rendered HTML."""
    return '<?php' in html or '<?=' in html


# ════════════════════════════════════════════════════════════════
# SEO Metadata  (§ 5)
# ════════════════════════════════════════════════════════════════

def _truncate(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[:max_len].rstrip() + '…'


def build_meta_tags(article: 'Article', rr: RenderResult, site: SiteConfig) -> tuple:
    """
    Returns (meta_tags_html, full_title_str).
    full_title is used for og:title fallback.
    """
    m = article.meta

    # ── <title> ──────────────────────────────────────────────
    prefix = m.seo_title_prefix if m.seo_title_prefix is not None else site.default_title_prefix
    suffix = m.seo_title_suffix if m.seo_title_suffix is not None else site.default_title_suffix
    full_title = f'{prefix}{m.title}{suffix}'

    # ── description ─────────────────────────────────────────
    desc = m.seo_description
    if not desc and rr.first_paragraph:
        desc = _truncate(rr.first_paragraph, site.description_truncate)

    # ── canonical ───────────────────────────────────────────
    canonical = m.seo_canonical or f'{site.base_url}/{m.slug}/'

    # ── og:image ─────────────────────────────────────────────
    og_image_raw = m.seo_og_image
    if not og_image_raw and rr.first_image:
        og_image_raw = rr.first_image
    og_image = og_image_raw or site.default_og_image
    # Make absolute if relative
    if og_image and not og_image.startswith('http'):
        og_image = site.base_url + og_image

    # ── og:title ─────────────────────────────────────────────
    og_title = m.seo_og_title or full_title

    # ── og:description ───────────────────────────────────────
    og_desc = m.seo_og_description or desc or ''

    # ── og:image:alt ─────────────────────────────────────────
    og_image_alt = m.seo_og_image_alt or m.title

    # ── twitter:image ────────────────────────────────────────
    tw_image = m.seo_twitter_image or og_image

    def e(s):
        """Escape for HTML attribute value."""
        return (s or '').replace('&', '&amp;').replace('"', '&quot;')

    # v0.2: <title> 은 템플릿의 PAGE_TITLE 가 처리 (원본 UI = "Lama" 고정).
    #       META_TAGS 에는 description 부터 출력.
    tags = []

    if desc:
        tags.append(f'<meta name="description" content="{e(desc)}">')

    if m.seo_keywords:
        kw = ', '.join(str(k) for k in m.seo_keywords if k)
        if kw:
            tags.append(f'<meta name="keywords" content="{e(kw)}">')

    author = m.seo_author or site.default_author
    if author:
        tags.append(f'<meta name="author" content="{e(author)}">')

    tags.append(f'<link rel="canonical" href="{e(canonical)}">')

    # Open Graph
    tags.append(f'<meta property="og:title" content="{e(og_title)}">')
    if og_desc:
        tags.append(f'<meta property="og:description" content="{e(og_desc)}">')
    if og_image:
        tags.append(f'<meta property="og:image" content="{e(og_image)}">')
        tags.append(f'<meta property="og:image:alt" content="{e(og_image_alt)}">')
    og_type = m.seo_og_type or 'article'
    tags.append(f'<meta property="og:type" content="{e(og_type)}">')
    tags.append(f'<meta property="og:url" content="{e(canonical)}">')
    tags.append(f'<meta property="og:site_name" content="{e(site.name)}">')
    tags.append(f'<meta property="article:published_time" content="{e(m.date)}">')
    modified = m.updated or m.date
    tags.append(f'<meta property="article:modified_time" content="{e(modified)}">')

    # Twitter Card
    tw_card = m.seo_twitter_card or 'summary_large_image'
    tags.append(f'<meta name="twitter:card" content="{e(tw_card)}">')
    tags.append(f'<meta name="twitter:title" content="{e(og_title)}">')
    if og_desc:
        tags.append(f'<meta name="twitter:description" content="{e(og_desc)}">')
    if tw_image:
        tags.append(f'<meta name="twitter:image" content="{e(tw_image)}">')

    return '\n  '.join(tags), full_title


# ════════════════════════════════════════════════════════════════
# Search index — tokenizer & body extractor  (v0.3.1)
# ════════════════════════════════════════════════════════════════
#
# 빌드 시 dist/search-index.json 을 만들고, 검색은 dist/search.php 가
# 그 인덱스를 읽어 처리한다 (서버측). 클라이언트 JS 0줄.
#
# 토크나이저 규칙 — Python 과 PHP 양쪽이 반드시 동일 출력을 내야 한다:
#   - 영문/숫자 (lowercase)  : 단어 단위로 그대로
#   - 한글 (가-힣)          : 음절 2-gram (bigram). 한 글자는 그대로.
#   - 그 외 문자             : 토큰 분리자로만 작용
#
# 예: "Hello 마스크 3D프린팅" →
#     ['hello', '마스', '스크', '3d', '프린', '린팅']
#
# bigram 인덱스이므로 부분 검색이 자연스럽다. "프린" 만 입력해도
# "프린팅", "프린터" 모두 매치. 영어는 정확 단어 매치.

_SEARCH_LATIN_RE = re.compile(r'[a-z0-9]+')
_SEARCH_HAN_RE = re.compile(r'[가-힣]+')


def _search_tokenize(text: str) -> list:
    """build.py / search.php 가 동일하게 사용하는 토크나이저.

    PHP 측 search_tokenize() (templates/search.php) 와 출력이 일치해야 한다.
    변경 시 양쪽 동시 수정 필수.
    """
    if not text:
        return []
    text = text.lower()
    tokens = []
    for m in _SEARCH_LATIN_RE.finditer(text):
        tokens.append(m.group())
    for m in _SEARCH_HAN_RE.finditer(text):
        word = m.group()
        if len(word) == 1:
            tokens.append(word)
        else:
            for i in range(len(word) - 1):
                tokens.append(word[i:i + 2])
    return tokens


_TAG_STRIP_RE = re.compile(r'<[^>]+>')
_STYLE_SCRIPT_RE = re.compile(
    r'<(style|script)\b[^>]*>.*?</\1>', re.DOTALL | re.IGNORECASE
)
_WS_COLLAPSE_RE = re.compile(r'\s+')


def _html_to_plain(html: str) -> str:
    """렌더된 본문 HTML 에서 태그를 제거한 평문. 공백은 1개로 압축.

    <style> / <script> 블록은 내용까지 통째로 제거한다 — content.html 이
    인라인 스타일을 갖는 경우 (예: About 페이지) CSS 가 검색 인덱스에
    들어가 노이즈를 만드는 것을 방지.
    """
    s = _STYLE_SCRIPT_RE.sub(' ', html or '')
    s = _TAG_STRIP_RE.sub(' ', s)
    s = _WS_COLLAPSE_RE.sub(' ', s).strip()
    return s


# ════════════════════════════════════════════════════════════════
# Template Renderer
# ════════════════════════════════════════════════════════════════

def _load_template(templates_dir: Path, name: str) -> str:
    path = templates_dir / name
    if not path.exists():
        _die(f'Template not found: {path}')
    return path.read_text(encoding='utf-8')


def _render(template: str, vars: dict) -> str:
    """Simple {{VAR}} substitution."""
    for k, v in vars.items():
        template = template.replace('{{' + k + '}}', str(v) if v is not None else '')
    return template


# ════════════════════════════════════════════════════════════════
# Build / Error helpers
# ════════════════════════════════════════════════════════════════

_warnings = []
_errors = []


def _warn(msg: str):
    print(f'[WARN] {msg}', file=sys.stderr)
    _warnings.append(msg)


def _die(msg: str):
    print(f'[FAIL] {msg}', file=sys.stderr)
    print('빌드 중단.', file=sys.stderr)
    sys.exit(1)


def _copy_if_newer(src: Path, dst: Path):
    """§ 7.3 — incremental copy using mtime comparison."""
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _remove_empty_dirs(root: Path):
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        p = Path(dirpath)
        if p == root:
            continue
        try:
            p.rmdir()
        except OSError:
            pass


# ════════════════════════════════════════════════════════════════
# Build Pipeline
# ════════════════════════════════════════════════════════════════

class Builder:
    def __init__(self, base_dir: Path):
        self.base = base_dir
        self.articles_dir = base_dir / 'Articles'
        self.assets_dir = base_dir / 'assets'
        self.templates_dir = base_dir / 'templates'
        self.dist = base_dir / 'dist'
        self.dist_legacy = base_dir / 'dist-legacy'

        self.site: SiteConfig = None
        self.legacy_map: dict = {}
        self.articles: list = []
        self.slug_to_article: dict = {}
        self.categories: dict = {}   # slug_path tuple → Category
        self.markdown_renderer: MarkdownRenderer = None  # set after _load_config
        # v0.3.1: slug → 평문 본문. _render_articles 가 채우고 _build_search 가 사용.
        self.rendered_bodies: dict = {}

    # ── [1] Config load ──────────────────────────────────────

    def _load_config(self):
        site_yaml = self.base / 'site.yaml'
        if not site_yaml.exists():
            _die(f'site.yaml not found at {site_yaml}')
        raw = _yaml_load(site_yaml.read_text(encoding='utf-8'))

        def get(key, default=None):
            return raw.get(key, default)

        self.site = SiteConfig(
            domain=get('domain', 'siheonlee.com'),
            base_url=get('base_url', 'https://siheonlee.com'),
            name=get('name', 'Lama'),
            main_title=get('main_title') or get('name', 'Lama'),
            default_author=get('default_author', ''),
            default_og_image=get('default_og_image', '/assets/default-og.png'),
            default_title_prefix=get('default_title_prefix') or '',
            default_title_suffix=get('default_title_suffix') or '',
            copyright_holder=get('copyright_holder', ''),
            copyright_year_start=get('copyright_year_start', 2020),
            reserved_slugs=get('reserved_slugs') or [],
            warn_on_underscore_ref=bool(get('warn_on_underscore_ref', True)),
            warn_on_missing_asset=bool(get('warn_on_missing_asset', True)),
            warn_on_stale_updated=bool(get('warn_on_stale_updated', True)),
            home_excludes_categories=get('home_excludes_categories') or [],
            home_sort=get('home_sort', 'date_desc'),
            description_truncate=int(get('description_truncate') or 150),
            robots_txt_main=get('robots_txt_main') or 'User-agent: *\nAllow: /\n',
            robots_txt_legacy=get('robots_txt_legacy') or 'User-agent: *\nAllow: /\n',
            markdown_parser=str(get('markdown_parser') or 'parsedown'),
        )

        legacy_yaml = self.base / 'legacy-map.yaml'
        if legacy_yaml.exists():
            self.legacy_map = _yaml_load(legacy_yaml.read_text(encoding='utf-8'))
            # Remove comment-only keys (None values from comment parsing)

        # v0.3: 선택된 마크다운 파서 인스턴스화
        self.markdown_renderer = make_markdown_renderer(
            self.site.markdown_parser, self.base
        )
        print(f'[markdown] using parser: {self.markdown_renderer.name}')

    # ── [2] Content scan ──────────────────────────────────────

    def _scan_articles(self):
        if not self.articles_dir.is_dir():
            _die(f'Articles/ directory not found at {self.articles_dir}')

        for root, dirs, files in os.walk(self.articles_dir):
            root_path = Path(root)

            # Skip _ prefixed paths
            if is_underscore_path(root_path, self.articles_dir):
                dirs.clear()
                continue

            # Filter _ prefixed subdirs (but allow _meta.yaml files)
            dirs[:] = [d for d in dirs if not d.startswith('_')]

            if 'meta.yaml' not in files:
                continue

            # Candidate article folder
            rel = root_path.relative_to(self.articles_dir)
            category_path = list(rel.parts[:-1])  # folders above article
            article_folder = rel.parts[-1]

            meta_file = root_path / 'meta.yaml'

            # Verify not nested inside another article
            # (meta.yaml cannot exist in a child of another meta.yaml folder)
            # This is checked via the article structure

            content_md = root_path / 'content.md'
            content_html = root_path / 'content.html'

            if content_md.exists() and content_html.exists():
                _die(f'content.md and content.html both exist\n'
                     f'       at {root_path}')

            content_file = content_md if content_md.exists() else content_html

            article = Article(
                meta=None,       # filled after YAML parse
                source_dir=root_path,
                content_file=content_file,
                category_path=category_path + [article_folder],
            )
            self.articles.append(article)

    # ── [3] Frontmatter parse ────────────────────────────────

    def _parse_frontmatter(self):
        for article in self.articles:
            meta_file = article.source_dir / 'meta.yaml'
            try:
                raw = _yaml_load(meta_file.read_text(encoding='utf-8'))
            except Exception as e:
                _die(f'meta.yaml parse error: {e}\n       at {meta_file}')

            slug = raw.get('slug')
            title = raw.get('title')
            date_str = raw.get('date')

            if not slug:
                _die(f'slug is empty\n       at {meta_file}')
            if not title:
                _die(f'title is empty\n       at {meta_file}')
            if not date_str:
                _die(f'date is missing\n       at {meta_file}')

            # Normalize date to string
            date_str = str(date_str)
            updated = str(raw.get('updated')) if raw.get('updated') else None

            article.meta = ArticleMeta(
                slug=slug,
                title=title,
                date=date_str,
                updated=updated,
                seo_title_prefix=raw.get('seo_title_prefix'),
                seo_title_suffix=raw.get('seo_title_suffix'),
                seo_description=raw.get('seo_description') or None,
                seo_keywords=raw.get('seo_keywords') or None,
                seo_author=raw.get('seo_author') or None,
                seo_canonical=raw.get('seo_canonical') or None,
                seo_og_title=raw.get('seo_og_title') or None,
                seo_og_description=raw.get('seo_og_description') or None,
                seo_og_image=raw.get('seo_og_image') or None,
                seo_og_image_alt=raw.get('seo_og_image_alt') or None,
                seo_og_type=raw.get('seo_og_type') or 'article',
                seo_twitter_card=raw.get('seo_twitter_card') or 'summary_large_image',
                seo_twitter_image=raw.get('seo_twitter_image') or None,
                styles=_normalize_styles(raw.get('styles')),
            )

    # ── [4] Validation ──────────────────────────────────────

    SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$')
    DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')

    def _validate(self):
        seen_slugs = {}

        for article in self.articles:
            m = article.meta
            meta_path = article.source_dir / 'meta.yaml'

            # slug regex
            if not self.SLUG_RE.match(m.slug):
                _die(f'slug 정규식 불일치: {repr(m.slug)}\n       at {meta_path}')

            # reserved slug
            if m.slug in self.site.reserved_slugs:
                _die(f'slug 예약어: {repr(m.slug)}\n       at {meta_path}')

            # slug uniqueness
            if m.slug in seen_slugs:
                other = seen_slugs[m.slug]
                _die(f"slug 충돌: '{m.slug}'\n"
                     f"       at {meta_path}\n"
                     f"          {other / 'meta.yaml'}")
            seen_slugs[m.slug] = article.source_dir

            # date format
            if not self.DATE_RE.match(m.date):
                _die(f'date 형식 오류: {repr(m.date)}\n       at {meta_path}')

            # updated >= date
            if m.updated:
                if not self.DATE_RE.match(m.updated):
                    _die(f'updated 형식 오류: {repr(m.updated)}\n       at {meta_path}')
                if m.updated < m.date:
                    _die(f'updated < date\n       at {meta_path}')

        # legacy-map slug existence
        for url_path, slug in self.legacy_map.items():
            if slug is not None and slug not in seen_slugs:
                _die(f"legacy-map.yaml: slug '{slug}' 미존재\n"
                     f"       ('{url_path}' 항목)")

        self.slug_to_article = {a.meta.slug: a for a in self.articles}

        # Build category tree
        self._build_category_tree()

        # Warn on empty categories
        for cat in self.categories.values():
            all_articles = self._collect_articles(cat)
            if not all_articles:
                _warn(f'empty category: {"/".join(cat.path)}')

        # content + updated stale warning
        if self.site.warn_on_stale_updated:
            for article in self.articles:
                if article.meta.updated and article.content_file:
                    try:
                        mtime = Date.fromtimestamp(
                            article.content_file.stat().st_mtime
                        ).isoformat()
                        if mtime > article.meta.updated:
                            _warn(f'{article.meta.slug}: meta updated may be stale '
                                  f'(file mtime {mtime} > updated {article.meta.updated})')
                    except Exception:
                        pass

    def _build_category_tree(self):
        """Build category hierarchy from article paths."""
        # Collect all category path tuples
        cat_paths = set()
        for article in self.articles:
            cat = article.category_path[:-1]  # all but article folder
            for depth in range(1, len(cat) + 1):
                cat_paths.add(tuple(cat[:depth]))

        # Build Category objects
        for path_tuple in sorted(cat_paths, key=lambda p: (len(p), p)):
            folder_name = path_tuple[-1]
            # Check for _meta.yaml override
            cat_dir = self.articles_dir / Path(*path_tuple)
            override_file = cat_dir / '_meta.yaml'
            if override_file.exists():
                try:
                    override = _yaml_load(override_file.read_text(encoding='utf-8'))
                    slug = override.get('slug') or category_slug_from_name(folder_name)
                except Exception:
                    slug = category_slug_from_name(folder_name)
            else:
                slug = category_slug_from_name(folder_name)

            if not slug:
                _die(f'카테고리 slug 빈 문자열: {folder_name}\n'
                     f'       (Articles/{"/".join(path_tuple)})\n'
                     f'       _meta.yaml 으로 slug override 필요')

            # Build slug_path
            slug_path = []
            for i, part in enumerate(path_tuple):
                sub = path_tuple[:i + 1]
                if sub in [tuple(c.path) for c in self.categories.values()]:
                    pass
                sub_cat_dir = self.articles_dir / Path(*sub)
                sub_override = sub_cat_dir / '_meta.yaml'
                if sub_override.exists():
                    try:
                        ov = _yaml_load(sub_override.read_text(encoding='utf-8'))
                        s = ov.get('slug') or category_slug_from_name(part)
                    except Exception:
                        s = category_slug_from_name(part)
                else:
                    s = category_slug_from_name(part)
                slug_path.append(s)

            cat = Category(
                folder_name=folder_name,
                slug=slug,
                path=list(path_tuple),
                slug_path=slug_path,
            )
            self.categories[path_tuple] = cat

        # Wire up parent-child relationships
        for path_tuple, cat in self.categories.items():
            if len(path_tuple) > 1:
                parent_path = path_tuple[:-1]
                if parent_path in self.categories:
                    parent = self.categories[parent_path]
                    if cat not in parent.children:
                        parent.children.append(cat)

        # Assign articles to their direct category
        for article in self.articles:
            cat_path = tuple(article.category_path[:-1])
            if cat_path in self.categories:
                cat = self.categories[cat_path]
                if article not in cat.articles:
                    cat.articles.append(article)

    def _collect_articles(self, cat: Category) -> list:
        """Recursively collect all articles under a category."""
        result = list(cat.articles)
        for child in cat.children:
            result.extend(self._collect_articles(child))
        return result

    # ── [5] Article render + output ──────────────────────────

    def _copyright_year(self) -> str:
        """원본은 푸터에 단일 연도만 표시 (예: 'Copyright© 2025.')."""
        import datetime
        return str(datetime.date.today().year)

    # ── 네비게이션 헬퍼 (원본 PHP WebPage 동작 재현) ──────────

    def _top_level_entries(self) -> list:
        """Articles/ 직속 항목들을 [(folder_name, slug, is_article), ...] 로 반환.

        원본 PHP generateNavLinks() 와 동일하게:
          - '_' 접두 폴더 제외
          - 'About' 우선, 나머지 알파벳 정렬
        """
        if not self.articles_dir.is_dir():
            return []

        entries = []
        for child in self.articles_dir.iterdir():
            if not child.is_dir():
                continue
            if child.name.startswith('_'):
                continue
            # 톱레벨 글 (meta.yaml 직접 보유) vs 카테고리 폴더 구분
            meta_file = child / 'meta.yaml'
            if meta_file.exists():
                # 톱레벨 글 — slug 는 meta.yaml 에서
                article = next(
                    (a for a in self.articles
                     if a.source_dir == child),
                    None,
                )
                slug = article.meta.slug if article else child.name.lower()
                entries.append((child.name, slug, True))
            else:
                # 카테고리 폴더 — 카테고리 트리에서 slug 조회
                key = (child.name,)
                cat = self.categories.get(key)
                slug = cat.slug if cat else category_slug_from_name(child.name)
                entries.append((child.name, slug, False))

        # About 우선, 나머지 알파벳
        about = [e for e in entries if e[0] == 'About']
        others = sorted(
            (e for e in entries if e[0] != 'About'),
            key=lambda e: e[0],
        )
        return about + others

    def _nav_links_html(self) -> str:
        """원본 generateNavLinks() 출력 형식 그대로:
            <a href='/about/'>About</a><span>|</span> <a href='/blog/'>Blog</a><span>|</span> ...
        """
        entries = self._top_level_entries()
        if not entries:
            return ''
        parts = []
        for folder, slug, _is_article in entries:
            parts.append(f"<a href='/{slug}/'>{_escape_html(folder)}</a>")
        return '<span>|</span> '.join(parts)

    def _nav_tracker_for_path(self, breadcrumb_parts: list) -> str:
        """원본 getNavTracker() 와 같은 형식으로 nav-tracker HTML 생성.

        breadcrumb_parts: [(label, url_or_None), ...] — 'Home' 은 자동으로 앞에 추가됨.
            url=None 이면 마지막 글 항목으로 간주, onClick reload 처리.
        """
        html = "<a href='/'>Home</a>"
        for label, url in breadcrumb_parts:
            label_safe = _escape_html(label)
            if url is None:
                # 원본 마지막 글 segment: clickable 모양 + reload
                html += (f"<a onClick='window.location.reload()' "
                         f"style='cursor: pointer;'> / {label_safe} </a>")
            else:
                html += f"<a href='{url}'> / {label_safe}</a>"
        return html

    def _top_category_for_article(self, article: 'Article'):
        """글이 속한 톱레벨 카테고리 (Category 또는 None)."""
        if not article.category_path or len(article.category_path) < 2:
            return None
        top = (article.category_path[0],)
        return self.categories.get(top)

    def _render_articles(self):
        """원본 lama_website-main 의 ArticlePage / WebPage 렌더링을 재현.

        - content.md: 원본 ArticlePage 처럼 <div class='gap'><p>{title}</p></div>
                      <section>...md...</section> 로 감싸 출력.
        - content.html: 원본 WebPage 처럼 본문을 그대로 (자체 gap+section 구조 유지).
        """
        tpl = _load_template(self.templates_dir, 'article.html')
        nav_links = self._nav_links_html()

        for article in self.articles:
            m = article.meta
            content_path = article.content_file

            if not content_path or not content_path.exists():
                _warn(f'{m.slug}: content file not found, skipping')
                continue

            content_text = content_path.read_text(encoding='utf-8')

            # 본문 렌더링 (v0.3: 파서 추상화)
            if content_path.suffix == '.md':
                rr = render_article_md(
                    content_text, m.slug, article.source_dir,
                    self.markdown_renderer,
                )
                body_html = (f"<div class='gap'>\n"
                             f"    <p>{_escape_html(m.title)}</p>\n"
                             f"</div>\n"
                             f"<section>\n{rr.html}\n</section>")
            else:
                rr = process_html(content_text, m.slug, article.source_dir)
                body_html = rr.html

            # v0.3.1: 검색 인덱스용 평문 캐시 (재렌더링 방지)
            self.rendered_bodies[m.slug] = _html_to_plain(rr.html)

            # v0.3: meta.yaml 의 styles 필드를 <style> 블록으로 변환
            article_styles = render_article_styles(m.styles)

            # _ 접두 자원 참조 경고
            if self.site.warn_on_underscore_ref:
                for pattern in [r'src="([^"]+)"', r'href="([^"]+)"']:
                    for url_match in re.finditer(pattern, rr.html):
                        ref = url_match.group(1)
                        if '/_' in ref or ref.startswith('_'):
                            _warn(f'{m.slug}: referenced excluded asset {ref}')

            # SEO meta (visible UI 영향 없음 — head 의 noindex 가 우선)
            meta_tags, _full_title = build_meta_tags(article, rr, self.site)

            # nav-tracker: Home / 톱카테고리 / 서브카테고리 / 글
            # 원본 PHP getNavTracker() 의 quirk 재현:
            #   서브카테고리 링크는 톱카테고리 페이지로 이동.
            crumb_parts = []
            top_cat = self._top_category_for_article(article)
            if top_cat:
                top_url = f"/{top_cat.slug}/"
                crumb_parts.append((top_cat.folder_name, top_url))
                # 서브카테고리들 — 모두 톱카테고리 URL 로 (원본 quirk)
                middle_folders = article.category_path[1:-1]
                for folder in middle_folders:
                    crumb_parts.append((folder, top_url))
            # 마지막 글 segment — 원본은 reload onClick
            crumb_parts.append((article.category_path[-1], None))
            nav_tracker = self._nav_tracker_for_path(crumb_parts)

            page_title = self.site.name

            vars = {
                'META_TAGS': meta_tags,
                'ARTICLE_STYLES': article_styles,
                'PAGE_TITLE': _escape_html(page_title),
                'MAIN_TITLE': _escape_html(self.site.main_title),
                'NAV_TRACKER': nav_tracker,
                'NAV_LINKS': nav_links,
                'BODY': body_html,
                'COPYRIGHT_YEAR': self._copyright_year(),
                'COPYRIGHT_HOLDER': _escape_html(self.site.copyright_holder),
            }
            page_html = _render(tpl, vars)

            # PHP 검출 → 확장자
            ext = 'php' if has_live_php(page_html) else 'html'

            out_dir = self.dist / m.slug
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f'index.{ext}'
            out_file.write_text(page_html, encoding='utf-8')

    # ── [6] Asset sync ────────────────────────────────────────

    def _sync_assets(self):
        for article in self.articles:
            m = article.meta
            src_root = article.source_dir
            dst_root = self.dist / 'src' / m.slug

            for src_file in src_root.rglob('*'):
                if not src_file.is_file():
                    continue
                if is_underscore_path(src_file, src_root):
                    continue
                if src_file.name in ('meta.yaml', 'content.md', 'content.html'):
                    continue
                rel = src_file.relative_to(src_root)
                dst_file = dst_root / rel

                # Warn on missing asset referenced by body
                _copy_if_newer(src_file, dst_file)

            # Prune orphans for this article
            self._prune_article_assets(article)

    def _prune_article_assets(self, article: Article):
        """§ 7.4 — remove orphan files in dist/src/{slug}/."""
        m = article.meta
        src_root = article.source_dir
        dst_root = self.dist / 'src' / m.slug
        if not dst_root.exists():
            return

        expected = set()
        for src_file in src_root.rglob('*'):
            if not src_file.is_file():
                continue
            if is_underscore_path(src_file, src_root):
                continue
            if src_file.name in ('meta.yaml', 'content.md', 'content.html'):
                continue
            rel = src_file.relative_to(src_root)
            expected.add(dst_root / rel)

        for existing in list(dst_root.rglob('*')):
            if existing.is_file() and existing not in expected:
                existing.unlink()

        _remove_empty_dirs(dst_root)

    # ── [7] Category indexes ──────────────────────────────────

    def _listup_module_html(self, article: 'Article') -> str:
        """원본 listup_module_div 마크업 재현.

        원본 HomePage / CategoryPage 의 article 링크 텍스트는 data.json 의 title.
        v0.2 도 meta.yaml 의 title 을 그대로 사용.
        """
        link_text = article.meta.title
        return (f"<div class='listup_module_div'>"
                f"<span class='listup_module_title'>"
                f"<a href='/{article.meta.slug}/'> "
                f"{_escape_html(link_text)} </a>"
                f"</span>"
                f"<span class='listup_module_date'> &nbsp;&nbsp; "
                f"{article.meta.date}</span>"
                f"</div>")

    def _build_categories(self):
        """원본 CategoryPage.generateCategoryArticleListBySubcategory() 재현.

        - 톱레벨 카테고리(예: Blog) 만 인덱스 페이지 생성.
        - 직속 서브카테고리별로 <div class='gap'><p>{name}</p></div><section>...</section> 그룹.
        - 서브카테고리 내 글은 재귀 수집 후 날짜 내림차순.
        - 원본 quirk 동일: 톱레벨 카테고리에 직접 위치한 글은 표시되지 않음
          (글들은 항상 서브카테고리 안에 있다는 원본 가정).
        """
        tpl = _load_template(self.templates_dir, 'category.html')
        nav_links = self._nav_links_html()

        for path_tuple, cat in self.categories.items():
            # 톱레벨만
            if len(cat.path) != 1:
                continue

            # 서브카테고리별 그룹 섹션
            sections = []
            sorted_children = sorted(cat.children, key=lambda c: c.folder_name)
            for child in sorted_children:
                articles = self._collect_articles(child)
                articles.sort(key=lambda a: a.meta.date, reverse=True)

                if not articles:
                    inner = "<p>No articles found in this subcategory</p>"
                else:
                    inner = '\n'.join(
                        self._listup_module_html(a) for a in articles
                    )

                sections.append(
                    f"<div class='gap'><p>{_escape_html(child.folder_name)}</p></div>\n"
                    f"<section>\n{inner}\n</section>"
                )

            # 직속 글 (원본은 표시 안 했지만, fallback 으로 직속 글이 있으면 카테고리 자체 섹션에 표시)
            if cat.articles and not sorted_children:
                articles = sorted(cat.articles, key=lambda a: a.meta.date, reverse=True)
                inner = '\n'.join(self._listup_module_html(a) for a in articles)
                sections.append(
                    f"<div class='gap'><p>{_escape_html(cat.folder_name)}</p></div>\n"
                    f"<section>\n{inner}\n</section>"
                )

            subcategory_sections = '\n'.join(sections) if sections else (
                f"<div class='gap'><p>{_escape_html(cat.folder_name)}</p></div>\n"
                f"<section><p>No articles found</p></section>"
            )

            # nav-tracker: Home / 카테고리명 (원본 case 2)
            crumb_parts = [(cat.folder_name, f"/{cat.slug}/")]
            nav_tracker = self._nav_tracker_for_path(crumb_parts)

            page_title = self.site.name

            vars = {
                'PAGE_TITLE': _escape_html(page_title),
                'MAIN_TITLE': _escape_html(self.site.main_title),
                'NAV_TRACKER': nav_tracker,
                'NAV_LINKS': nav_links,
                'SUBCATEGORY_SECTIONS': subcategory_sections,
                'COPYRIGHT_YEAR': self._copyright_year(),
                'COPYRIGHT_HOLDER': _escape_html(self.site.copyright_holder),
            }
            page_html = _render(tpl, vars)

            out_dir = self.dist / cat.slug
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / 'index.html').write_text(page_html, encoding='utf-8')

    # ── [8] Home page ─────────────────────────────────────────

    def _build_home(self):
        """원본 HomePage.generateHomepageArticleList() 재현.

        - About 카테고리 글은 제외 (원본도 동일).
        - 모든 글을 평면 리스트로 날짜 내림차순 정렬.
        - 출력은 listup_module_div 마크업 그대로.
        """
        tpl = _load_template(self.templates_dir, 'home.html')

        exclude_top = set(self.site.home_excludes_categories)

        home_articles = []
        for article in self.articles:
            if article.category_path:
                top_cat = article.category_path[0]
                if top_cat in exclude_top:
                    continue
            # 톱레벨 글 (예: About 자체) 도 home_excludes_categories 로 필터
            if (len(article.category_path) == 1
                    and article.category_path[0] in exclude_top):
                continue
            home_articles.append(article)

        home_articles.sort(key=lambda a: a.meta.date, reverse=True)

        article_items = '\n'.join(
            self._listup_module_html(a) for a in home_articles
        )

        page_title = self.site.name

        vars = {
            'PAGE_TITLE': _escape_html(page_title),
            'MAIN_TITLE': _escape_html(self.site.main_title),
            'NAV_LINKS': self._nav_links_html(),
            'ARTICLE_LIST': article_items,
            'COPYRIGHT_YEAR': self._copyright_year(),
            'COPYRIGHT_HOLDER': _escape_html(self.site.copyright_holder),
        }
        page_html = _render(tpl, vars)
        self.dist.mkdir(parents=True, exist_ok=True)
        (self.dist / 'index.html').write_text(page_html, encoding='utf-8')

    # ── [9] Site assets ───────────────────────────────────────

    def _copy_site_assets(self):
        if not self.assets_dir.is_dir():
            return
        dst_assets = self.dist / 'assets'
        dst_assets.mkdir(parents=True, exist_ok=True)
        for src_file in self.assets_dir.rglob('*'):
            if src_file.is_file():
                rel = src_file.relative_to(self.assets_dir)
                _copy_if_newer(src_file, dst_assets / rel)

    # ── [10] 404 page ─────────────────────────────────────────

    def _build_404(self):
        """원본 ErrorPage 재현."""
        tpl = _load_template(self.templates_dir, '404.html')
        # 원본 ErrorPage 의 title 은 'Error 404'
        page_title = 'Error 404'
        vars = {
            'PAGE_TITLE': _escape_html(page_title),
            'MAIN_TITLE': _escape_html(self.site.main_title),
            'NAV_LINKS': self._nav_links_html(),
            'COPYRIGHT_YEAR': self._copyright_year(),
            'COPYRIGHT_HOLDER': _escape_html(self.site.copyright_holder),
        }
        page_html = _render(tpl, vars)
        self.dist.mkdir(parents=True, exist_ok=True)
        (self.dist / '404.html').write_text(page_html, encoding='utf-8')

    # ── [11] robots.txt ───────────────────────────────────────

    def _build_robots(self):
        self.dist.mkdir(parents=True, exist_ok=True)
        (self.dist / 'robots.txt').write_text(
            self.site.robots_txt_main, encoding='utf-8'
        )
        self.dist_legacy.mkdir(parents=True, exist_ok=True)
        (self.dist_legacy / 'robots.txt').write_text(
            self.site.robots_txt_legacy, encoding='utf-8'
        )

    # ── [12] Legacy dispatcher ────────────────────────────────

    def _build_dispatcher(self):
        """§ 11.2 — generate dist-legacy/redirect.php"""
        lines = ["<?php"]
        lines.append("$map = [")
        for url_path, slug in self.legacy_map.items():
            key_escaped = url_path.replace("'", "\\'")
            if slug is None:
                lines.append(f"    '{key_escaped}' => null,")
            else:
                lines.append(f"    '{key_escaped}' => '{slug}',")
        lines.append("];")
        lines.append("")
        lines.append("$path = urldecode(parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH));")
        lines.append("$path = rtrim($path, '/') . '/';")
        lines.append("")
        lines.append("if (array_key_exists($path, $map)) {")
        lines.append("    $slug = $map[$path];")
        lines.append("    if ($slug === null) {")
        lines.append("        http_response_code(410);")
        lines.append("        echo '410 Gone';")
        lines.append("        exit;")
        lines.append("    }")
        lines.append("    header(\"Location: https://siheonlee.com/{$slug}/\", true, 301);")
        lines.append("    exit;")
        lines.append("}")
        lines.append("")
        lines.append("// 미매칭: siheonlee.com 의 404 페이지로 안내")
        lines.append("http_response_code(404);")
        lines.append("header(\"Location: https://siheonlee.com/404.html\", true, 302);")
        lines.append("exit;")

        self.dist_legacy.mkdir(parents=True, exist_ok=True)
        (self.dist_legacy / 'redirect.php').write_text(
            '\n'.join(lines), encoding='utf-8'
        )

    # ── [13] Search index + search.php  (v0.3.1) ──────────────

    def _build_search(self):
        """Build dist/search-index.json + dist/search.php.

        인덱스 포맷:
          {
            "version": 1,
            "docs":  [{"slug","title","date","category","body"}, ...],
            "index":       {"<token>": [[doc_id, tf], ...], ...},  # 본문
            "title_index": {"<token>": [[doc_id, tf], ...], ...}   # 제목
          }

        body 는 스니펫 추출용 평문 (HTML 태그 제거 후, 공백 압축).
        about 카테고리 등 site.yaml 의 home_excludes_categories 도 검색 대상에 포함
        (검색은 글 모두를 대상으로 — 홈 노출 정책과 별개).
        """
        docs = []
        body_index = {}    # token -> {doc_id: tf}
        title_index = {}

        # 안정적인 doc_id 를 위해 slug 정렬
        sorted_articles = sorted(self.articles, key=lambda a: a.meta.slug)

        for doc_id, article in enumerate(sorted_articles):
            m = article.meta
            body_plain = self.rendered_bodies.get(m.slug, '')

            top_cat = ''
            if len(article.category_path) > 1:
                top_cat = article.category_path[0]

            # 본문 저장 길이 제한 (스니펫엔 충분, 인덱스 크기 통제)
            body_for_doc = body_plain[:5000]

            docs.append({
                'slug': m.slug,
                'title': m.title,
                'date': m.date,
                'category': top_cat,
                'body': body_for_doc,
            })

            body_tf = {}
            for t in _search_tokenize(body_plain):
                body_tf[t] = body_tf.get(t, 0) + 1
            for t, tf in body_tf.items():
                body_index.setdefault(t, {})[doc_id] = tf

            title_tf = {}
            for t in _search_tokenize(m.title):
                title_tf[t] = title_tf.get(t, 0) + 1
            for t, tf in title_tf.items():
                title_index.setdefault(t, {})[doc_id] = tf

        def compact(idx):
            return {tok: [[d, tf] for d, tf in posting.items()]
                    for tok, posting in idx.items()}

        index_data = {
            'version': 1,
            'docs': docs,
            'index': compact(body_index),
            'title_index': compact(title_index),
        }

        self.dist.mkdir(parents=True, exist_ok=True)
        (self.dist / 'search-index.json').write_text(
            json.dumps(index_data, ensure_ascii=False, separators=(',', ':')),
            encoding='utf-8',
        )

        # search.php 템플릿 substitute
        tpl_path = self.templates_dir / 'search.php'
        if not tpl_path.exists():
            _warn('templates/search.php not found, skipping search page build')
            return
        tpl = tpl_path.read_text(encoding='utf-8')
        vars = {
            'PAGE_TITLE': _escape_html(self.site.name),
            'MAIN_TITLE': _escape_html(self.site.main_title),
            'NAV_LINKS': self._nav_links_html(),
            'COPYRIGHT_YEAR': self._copyright_year(),
            'COPYRIGHT_HOLDER': _escape_html(self.site.copyright_holder),
        }
        page = _render(tpl, vars)
        (self.dist / 'search.php').write_text(page, encoding='utf-8')

    # ── [14] Global orphan pruning ────────────────────────────

    def _prune_orphans(self):
        """§ 7.4 — remove dist directories for deleted/renamed slugs and categories."""
        current_slugs = {a.meta.slug for a in self.articles}
        current_cat_slug_paths = {tuple(c.slug_path) for c in self.categories.values()}

        # Prune dist/{slug}/
        if self.dist.is_dir():
            for d in self.dist.iterdir():
                if not d.is_dir():
                    continue
                name = d.name
                if name in ('src', 'assets'):
                    continue
                # Skip known category top-level slugs and special dirs
                # Check if it's a slug dir (article)
                if (d / 'index.html').exists() or (d / 'index.php').exists():
                    if name not in current_slugs:
                        # Check if it's a category slug
                        is_cat = any(sp[0] == name for sp in current_cat_slug_paths
                                     if sp)
                        if not is_cat:
                            shutil.rmtree(d)

        # Prune dist/src/{slug}/
        src_dir = self.dist / 'src'
        if src_dir.is_dir():
            for d in src_dir.iterdir():
                if d.is_dir() and d.name not in current_slugs:
                    shutil.rmtree(d)

    # ── Build entry point ─────────────────────────────────────

    def build(self):
        print('빌드 시작...', flush=True)

        self._load_config()                    # [1]
        self._scan_articles()                  # [2]
        self._parse_frontmatter()              # [3]
        self._validate()                       # [4]
        self._render_articles()                # [5]
        self._sync_assets()                    # [6]
        self._build_categories()               # [7]
        self._build_home()                     # [8]
        self._copy_site_assets()               # [9]
        self._build_404()                      # [10]
        self._build_robots()                   # [11]
        self._build_dispatcher()               # [12]
        self._build_search()                   # [13]  v0.3.1
        self._prune_orphans()                  # [14]

        warn_count = len(_warnings)
        art_count = len(self.articles)
        cat_count = len(self.categories)
        print(f'\n빌드 완료: {art_count} 글, {cat_count} 카테고리, {warn_count} 경고.')
        print(f'산출물: dist/ (siheonlee.com), dist-legacy/ (lama.pe.kr).')


# ════════════════════════════════════════════════════════════════
# Entry point
# ════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    base = Path(__file__).parent

    if '--clean' in sys.argv:
        for d in (base / 'dist', base / 'dist-legacy'):
            if d.exists():
                shutil.rmtree(d)
                print(f'Cleaned: {d}')

    Builder(base).build()

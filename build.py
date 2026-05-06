#!/usr/bin/env python3
"""
siheonlee.com SSG v0.1 — Static Site Generator
Python 3.x stdlib only, zero external dependencies. (§ 0)

Usage:
    python build.py           # full build
    python build.py --clean   # wipe dist/ before build
"""

import os
import re
import sys
import shutil
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
            # Peek ahead for block list
            if i[0] < n:
                next_raw = lines[i[0]]
                next_stripped = next_raw.strip()
                if next_stripped.startswith('- ') or next_stripped == '-':
                    next_indent = get_indent(next_raw)
                    if next_indent > base_indent:
                        result[key] = parse_block_list(next_indent)
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

def _escape_html(s: str) -> str:
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _render_inline(text: str, slug: str) -> str:
    """Render inline markdown: bold, italic, code, links, images."""
    # Inline code (escape content)
    def inline_code(m):
        return '<code>' + _escape_html(m.group(1)) + '</code>'
    text = re.sub(r'`([^`]+)`', inline_code, text)

    # Images  ![alt](url)
    def image(m):
        alt = m.group(1)
        url = rewrite_asset_path(m.group(2), slug)
        return f'<img src="{url}" alt="{_escape_html(alt)}">'
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', image, text)

    # Links  [text](url)
    def link(m):
        link_text = m.group(1)
        url = rewrite_asset_path(m.group(2), slug)
        return f'<a href="{url}">{link_text}</a>'
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, text)

    # Bold **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic *text*
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)

    return text


def render_markdown(text: str, slug: str) -> RenderResult:
    """Parse markdown to HTML. Returns RenderResult with html, first_paragraph, first_image."""
    lines = text.splitlines()
    n = len(lines)
    i = [0]
    output = []
    first_paragraph = None
    first_image = [None]

    def track_image(html_fragment: str):
        if first_image[0] is None:
            m = re.search(r'<img\s[^>]*src="([^"]+)"', html_fragment)
            if m:
                first_image[0] = m.group(1)

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
            content = _render_inline(hm.group(2).strip(), slug)
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
            inner = _render_inline(' '.join(quote_lines), slug)
            output.append(f'<blockquote><p>{inner}</p></blockquote>')
            continue

        # Unordered list
        if re.match(r'^[-*+] ', line):
            items = []
            while i[0] < n and re.match(r'^[-*+] ', lines[i[0]]):
                items.append(f'<li>{_render_inline(lines[i[0]][2:], slug)}</li>')
                i[0] += 1
            output.append('<ul>' + ''.join(items) + '</ul>')
            continue

        # Ordered list
        if re.match(r'^\d+\. ', line):
            items = []
            while i[0] < n and re.match(r'^\d+\. ', lines[i[0]]):
                item_text = re.sub(r'^\d+\. ', '', lines[i[0]])
                items.append(f'<li>{_render_inline(item_text, slug)}</li>')
                i[0] += 1
            output.append('<ol>' + ''.join(items) + '</ol>')
            continue

        # Custom imgBox  ![[alt]](url) {desc}  (§ 8.2)
        ibm = re.match(r'^!\[\[([^\]]*)\]\]\(([^)]+)\)(?:\s+\{([^}]*)\})?', line)
        if ibm:
            alt = ibm.group(1)
            url = rewrite_asset_path(ibm.group(2), slug)
            desc = ibm.group(3)
            track_image(f'<img src="{url}">')
            if desc:
                block = (f'<div class="imgBox">\n'
                         f'  <img src="{url}" alt="{_escape_html(alt)}">\n'
                         f'  <p class="caption">{_escape_html(desc)}</p>\n'
                         f'</div>')
            else:
                block = (f'<div class="imgBox">\n'
                         f'  <img src="{url}" alt="{_escape_html(alt)}">\n'
                         f'</div>')
            output.append(block)
            i[0] += 1
            continue

        # Empty line
        if not line.strip():
            i[0] += 1
            continue

        # Raw HTML passthrough (§ 8.3)
        if line.lstrip().startswith('<') and not line.lstrip().startswith('<p'):
            html_lines = [line]
            i[0] += 1
            # Collect continued HTML block (non-empty, non-structural)
            while i[0] < n:
                next_line = lines[i[0]]
                if not next_line.strip():
                    break
                if re.match(r'^(#{1,6} |```|> |[-*+] |\d+\. )', next_line):
                    break
                html_lines.append(next_line)
                i[0] += 1
            html_block = '\n'.join(html_lines)
            html_block = rewrite_asset_paths_in_html(html_block, slug)
            track_image(html_block)
            output.append(html_block)
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
            if re.match(r'^!\[\[', l):
                break
            para_lines.append(l)
            i[0] += 1
        if para_lines:
            para_html = _render_inline(' '.join(para_lines), slug)
            output.append(f'<p>{para_html}</p>')
            if first_paragraph is None:
                first_paragraph = re.sub(r'<[^>]+>', '', para_html).strip()
            track_image(para_html)

    return RenderResult(
        html='\n'.join(output),
        first_paragraph=first_paragraph or '',
        first_image=first_image[0],
    )


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


def process_html(text: str, slug: str, article_dir: Path) -> RenderResult:
    """Process content.html: simulate PHP functions, rewrite asset paths."""
    first_paragraph = [None]
    first_image = [None]

    def replace_php_call(m: re.Match) -> str:
        func = m.group(1)
        args_str = m.group(2)
        args = _parse_php_args(args_str)

        if func == 'imgBox':
            src = args[0] if len(args) > 0 else ''
            exp = args[1] if len(args) > 1 else ''
            alt = args[2] if len(args) > 2 else ''
            result = _simulate_imgbox(src, exp, alt, slug)
            if first_image[0] is None:
                url = rewrite_asset_path(src, slug)
                first_image[0] = url
            return result

        if func == 'imgSlideBox':
            dir_path = args[0] if args else ''
            return _simulate_imgslidebox(dir_path, slug, article_dir)

        # Unknown PHP function — return as-is (§ 9.3)
        return m.group(0)

    # Simulate PHP function calls: <?php funcName("arg1", "arg2") ?>
    php_call_pattern = r'<\?php\s+(\w+)\(([^)]*)\)\s*\?>'
    text = re.sub(php_call_pattern, replace_php_call, text)

    # Rewrite asset paths
    text = rewrite_asset_paths_in_html(text, slug)

    # Extract first paragraph and first image for SEO fallback
    p_match = re.search(r'<p[^>]*>(.*?)</p>', text, re.DOTALL)
    if p_match:
        first_paragraph[0] = re.sub(r'<[^>]+>', '', p_match.group(1)).strip()

    img_match = re.search(r'<img\s[^>]*src="([^"]+)"', text)
    if img_match and first_image[0] is None:
        first_image[0] = img_match.group(1)

    return RenderResult(
        html=text,
        first_paragraph=first_paragraph[0] or '',
        first_image=first_image[0],
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

    tags = [f'<title>{e(full_title)}</title>']

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
            name=get('name', 'siheonlee.com'),
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
        )

        legacy_yaml = self.base / 'legacy-map.yaml'
        if legacy_yaml.exists():
            self.legacy_map = _yaml_load(legacy_yaml.read_text(encoding='utf-8'))
            # Remove comment-only keys (None values from comment parsing)

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
        import datetime
        current_year = datetime.date.today().year
        start = self.site.copyright_year_start
        if current_year > start:
            return f'{start}–{current_year}'
        return str(start)

    def _make_breadcrumb(self, parts: list) -> str:
        """Build breadcrumb HTML from list of (label, url) tuples."""
        html = ''
        for label, url in parts:
            if url:
                html += f'<span class="sep">›</span> <a href="{url}">{label}</a>'
            else:
                html += f'<span class="sep">›</span> <span>{label}</span>'
        return html

    def _render_articles(self):
        tpl = _load_template(self.templates_dir, 'article.html')
        for article in self.articles:
            m = article.meta
            content_path = article.content_file

            if not content_path or not content_path.exists():
                _warn(f'{m.slug}: content file not found, skipping')
                continue

            content_text = content_path.read_text(encoding='utf-8')

            # Render content
            if content_path.suffix == '.md':
                rr = render_markdown(content_text, m.slug)
            else:
                rr = process_html(content_text, m.slug, article.source_dir)

            # Warn on _-referenced assets in body
            if self.site.warn_on_underscore_ref:
                for pattern in [r'src="([^"]+)"', r'href="([^"]+)"']:
                    for url_match in re.finditer(pattern, rr.html):
                        ref = url_match.group(1)
                        if '/_' in ref or ref.startswith('_'):
                            _warn(f'{m.slug}: referenced excluded asset {ref}')

            # SEO
            meta_tags, full_title = build_meta_tags(article, rr, self.site)

            # Breadcrumb: all category levels
            crumb_parts = []
            slug_path_so_far = []
            cat_key = tuple(article.category_path[:-1])
            cat = self.categories.get(cat_key)
            if cat:
                for sp in cat.slug_path:
                    slug_path_so_far.append(sp)
                    folder_idx = len(slug_path_so_far) - 1
                    label = cat.path[folder_idx] if folder_idx < len(cat.path) else sp
                    url = '/' + '/'.join(slug_path_so_far) + '/'
                    crumb_parts.append((label, url))
            crumb_parts.append((article.category_path[-1], None))
            breadcrumb_html = self._make_breadcrumb(crumb_parts)

            # Date display
            date_display = m.date
            updated_html = ''
            if m.updated:
                updated_html = (f'<span class="updated">'
                                f'(updated: {m.updated})</span>')

            vars = {
                'META_TAGS': meta_tags,
                'BREADCRUMB': breadcrumb_html,
                'ARTICLE_TITLE': _escape_html(m.title),
                'DATE_ISO': m.date,
                'DATE_DISPLAY': date_display,
                'UPDATED_META': updated_html,
                'BODY': rr.html,
                'COPYRIGHT_YEAR': self._copyright_year(),
                'COPYRIGHT_HOLDER': _escape_html(self.site.copyright_holder),
            }
            page_html = _render(tpl, vars)

            # PHP detection → ext
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

    def _build_categories(self):
        tpl = _load_template(self.templates_dir, 'category.html')

        for path_tuple, cat in self.categories.items():
            all_articles = self._collect_articles(cat)

            # Sort: date desc
            all_articles.sort(key=lambda a: a.meta.date, reverse=True)

            # Article list HTML
            article_items = ''
            for a in all_articles:
                link_text = a.category_path[-1]  # folder name (§ 4.6)
                article_items += (
                    f'<li>'
                    f'<span class="date">{a.meta.date}</span>'
                    f'<a href="/{a.meta.slug}/">{_escape_html(link_text)}</a>'
                    f'</li>\n'
                )

            # Subcategory list
            sub_html = ''
            if cat.children:
                sub_html = '<ul class="subcategory-list">\n'
                for child in sorted(cat.children, key=lambda c: c.folder_name):
                    child_url = '/' + '/'.join(child.slug_path) + '/'
                    sub_html += f'<li><a href="{child_url}">{_escape_html(child.folder_name)}</a></li>\n'
                sub_html += '</ul>\n'

            # Breadcrumb
            crumb_parts = []
            for depth in range(1, len(cat.slug_path)):
                partial_path = cat.path[:depth]
                partial_slug = cat.slug_path[:depth]
                label = partial_path[-1]
                url = '/' + '/'.join(partial_slug) + '/'
                crumb_parts.append((label, url))
            crumb_parts.append((cat.folder_name, None))
            breadcrumb_html = self._make_breadcrumb(crumb_parts)

            cat_url = '/' + '/'.join(cat.slug_path) + '/'
            cat_title = f'{cat.folder_name} | {self.site.name}'

            vars = {
                'CAT_TITLE': _escape_html(cat_title),
                'BREADCRUMB': breadcrumb_html,
                'CAT_DISPLAY_NAME': _escape_html(cat.folder_name),
                'SUBCATEGORY_LIST': sub_html,
                'ARTICLE_LIST': article_items,
                'COPYRIGHT_YEAR': self._copyright_year(),
                'COPYRIGHT_HOLDER': _escape_html(self.site.copyright_holder),
            }
            page_html = _render(tpl, vars)

            out_dir = self.dist / Path(*cat.slug_path)
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / 'index.html').write_text(page_html, encoding='utf-8')

    # ── [8] Home page ─────────────────────────────────────────

    def _build_home(self):
        tpl = _load_template(self.templates_dir, 'home.html')

        exclude_top = set(self.site.home_excludes_categories)

        # Collect all articles not in excluded top-level categories
        home_articles = []
        for article in self.articles:
            if article.category_path:
                top_cat = article.category_path[0]
                if top_cat in exclude_top:
                    continue
            home_articles.append(article)

        # Sort date desc
        home_articles.sort(key=lambda a: a.meta.date, reverse=True)

        article_items = ''
        for a in home_articles:
            link_text = a.category_path[-1]
            article_items += (
                f'<li>'
                f'<span class="date">{a.meta.date}</span>'
                f'<a href="/{a.meta.slug}/">{_escape_html(link_text)}</a>'
                f'</li>\n'
            )

        vars = {
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
        tpl = _load_template(self.templates_dir, '404.html')
        error_title = (f'{self.site.default_title_prefix}'
                       f'Error 404'
                       f'{self.site.default_title_suffix}')
        vars = {
            'ERROR_TITLE': _escape_html(error_title),
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

    # ── [13] Global orphan pruning ────────────────────────────

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
        self._prune_orphans()                  # [13]

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

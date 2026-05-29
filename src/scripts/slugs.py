"""Folder name -> URL slug.

Korean (and any non-ASCII) folder names are converted deterministically, so no
manual slug override is needed. Each non-ASCII char becomes its lowercase
4-digit hex codepoint; the result then goes through NFKD normalization, an
allowed-char filter, parenthesis removal, and whitespace/hyphen collapsing.

  e.g. '블로그' -> 'be94-b85c-adf8'

A non-ASCII folder name also raises a build warning (emitted by
builder._build_category_tree) so the author can review an ASCII rename.

Excluded prefixes: '_' (author-private / draft) and '.' (OS/VCS hidden, e.g.
.git, .DS_Store). Both are handled by one rule so anything meant to be hidden
never leaks out as an article, category, or asset.
"""
import re
import unicodedata


_HAS_NON_ASCII_RE = re.compile(r'[^\x00-\x7f]')


def has_non_ascii(name: str) -> bool:
    return bool(_HAS_NON_ASCII_RE.search(name))


def _escape_non_ascii(name: str) -> str:
    """Replace each non-ASCII char with '<hex>-' (e.g. Hangul U+AC00 -> 'ac00-')."""
    parts = []
    for ch in name:
        if ord(ch) < 128:
            parts.append(ch)
        else:
            parts.append(f'{ord(ch):04x}-')
    return ''.join(parts)


def category_slug_from_name(name: str) -> str:
    """Folder name -> URL slug (non-ASCII pre-escape + 5 steps).

    1. non-ASCII char -> 4-digit hex codepoint + '-'
    2. NFKD normalization
    3. keep only [A-Za-z0-9 \\-()]
    4. drop parentheses
    5. collapse whitespace/hyphens to a single '-', strip trailing '-', lowercase
    """
    s = _escape_non_ascii(name)
    s = unicodedata.normalize('NFKD', s)
    s = re.sub(r"[^A-Za-z0-9 \-()]", '', s)
    s = s.replace('(', '').replace(')', '')
    s = re.sub(r'[\s\-]+', '-', s)
    s = s.strip('-')
    return s.lower()


# Build-excluded folder/file prefixes: '_' (author-private: draft / WIP) and
# '.' (OS/VCS hidden: .git, .DS_Store, .draft). Scan, nav, and asset sync all
# consult this single rule.
_EXCLUDED_PREFIXES = ('_', '.')


def is_excluded_name(name: str) -> bool:
    """Whether a single path component is build-excluded ('_' / '.' prefix)."""
    return name.startswith(_EXCLUDED_PREFIXES)


def is_excluded_path(p, base) -> bool:
    """True if any segment of p (relative to base) has an excluded prefix."""
    try:
        rel = p.relative_to(base)
    except ValueError:
        rel = p
    return any(is_excluded_name(part) for part in rel.parts)

# Heron v1.5.1 — User Guide

**Heron** is a lightweight, **PHP-targeted static site generator**: keep **one folder per article** for its body and attachments, and `python Heron.py` builds the whole site once. *A site that stands still.*

> 🇰🇷 한국어 사용설명서는 [README.ko.md](README.ko.md) 를 보세요. The Korean guide is the more exhaustive reference; this English guide covers the same system.

| Core value | How it is guaranteed |
|---|---|
| **Permanent URLs** | An article's URL (`slug`) is decoupled from its category/folder name. Move an article and its URL stays. |
| **Minimal ops dependencies** | Build = Python 3 stdlib (+ Pillow). Runtime = Apache + PHP. No `composer`, no client-side JS. |
| **Automatic image optimization** | raster → WebP, multi-resolution `srcset` + `loading="lazy"`, automatically. |
| **Server / content separation** | No `.htaccess`. Routing is registered once in an Apache VirtualHost. |
| **Per-page presentation control** | `meta.yaml` `styles` for inline tweaks + external CSS files + your own template. |
| **Per-article indexing** | Indexed by default; exclude one article with a single `noindex: true`. |
| **In-site search** | Zero client JS. BM25 + tokenizer + index inlined into a single `search.php` (OPcache assumed). |
| **Dark mode** | `prefers-color-scheme`, automatic. No toggle UI — the OS setting is trusted. |
| **Prev / next article** | Same-parent siblings in date order. Site-wide toggle. |

## Table of contents

1. [Quick start](#1-quick-start)
2. [System overview](#2-system-overview)
3. [Folder structure](#3-folder-structure)
4. [Writing articles](#4-writing-articles)
5. [Categories](#5-categories)
6. [Managing articles — private / move / delete](#6-managing-articles)
7. [Build](#7-build)
8. [Output structure and URLs](#8-output-structure-and-urls)
9. [Markdown syntax](#9-markdown-syntax)
10. [SEO settings](#10-seo-settings)
11. [Site-wide settings — site.yaml](#11-site-wide-settings)
12. [Internals — parser / search / feed](#12-internals)
13. [Deployment](#13-deployment)
14. [Troubleshooting](#14-troubleshooting)
15. [Design principles and limits](#15-design-principles-and-limits)
16. [Changelog](#16-changelog)
17. [Local authoring — Pond.php](#17-local-authoring--pondphp)

---

## 1. Quick start

**Requirements**

- **Python 3.x** (3.10+ recommended).
- **Pillow** — converts raster images to multi-resolution WebP. `pip install Pillow`. To skip it, set `images.enabled: false` in `user/site.yaml`.
- **PHP CLI** (optional) — if present, the build auto-verifies the Python↔PHP tokenizer parity. If absent, it warns and skips.

**Build** — open a terminal in this folder:

```bash
python Heron.py                # normal build (incremental cache)
python Heron.py --clean        # wipe dist/ and .build_cache/, then build
python Heron.py --clean-cache  # wipe the cache only, keep dist/
python Heron.py --no-cache     # disable the incremental cache
```

The first build misses every article (empty cache); later builds hit unchanged articles. Changing `user/site.yaml`, a template, or builder code invalidates everything.

**Check the result** — paths are absolute (`/assets/...`), so double-clicking breaks CSS. Use a local server:

```bash
cd dist && python -m http.server 8000   # → http://localhost:8000/
```

---

## 2. System overview

Make one folder per article and `python Heron.py` produces static HTML + a search PHP that Apache serves directly.

```
operator   build → upload dist/
visitor    ├─ normal page       → Apache serves static HTML (fast)
           └─ /search.php?q=…    → PHP runs BM25 over the inlined static index → result HTML
```

- **Minimal ops dependencies** — Python 3 stdlib (build) + PHP (runtime search and `.php` output articles).
- **Article folder = autonomous unit** — manage body, images, and helper files freely inside the article folder.
- **Permanent URLs** — the `slug` is the URL; moving categories does not change it.
- **Per-article styling and indexing** — controlled independently in each `meta.yaml`.

**Build pipeline (16 steps)** — the console `[ n/16]` headers and the per-step timing table in `build-report.md` use the same numbering.

| # | What |
|---|---|
| 1 | Read `user/site.yaml` + tokenizer parity check (if PHP present) |
| 2 | Scan the `user/articles/` tree |
| 3 | Parse each article `meta.yaml` |
| 4 | Validate (slug duplicates/reserved/format) + build the category tree. Problem articles get an issue + are excluded individually; the build continues |
| 5 | Copy per-article assets → `dist/{slug}/`. Raster images become WebP via Pillow (multi-process) |
| 6 | Copy site-wide assets → `dist/assets/` (from `user/styles`, `user/branding`, `system/runtime`'s JS) |
| 7 | Copy category/home external CSS files into dist |
| 8 | Render article bodies (.md via parser, .html as-is) → `<img>` post-processing → style injection → template assembly |
| 9 | Category indexes (top-level + sub) |
| 10 | Home page |
| 11 | 404 page |
| 12 | `robots.txt` (with Sitemap directive) + `dist/ads.txt` |
| 13 | `sitemap.xml` |
| 14 | `feed.atom` / `feed.rss` (same entry list) |
| 15 | `dist/search.php` — 3-field BM25 index + tokenizer + scorer inlined |
| 16 | Prune orphaned output |

---

## 3. Folder structure

Since v1.5.0 the root is split into **`user/` (what you edit) and `system/` (the program):**

```
siheonlee.com_v1.5.1/
│
├── user/                    ← ★ everything you own and edit
│   ├── articles/                ← all articles
│   │   ├── About/                   ← top-level article (meta.yaml + content.html + assets)
│   │   └── Blog/                    ← category folder
│   │       └── Hello World/         ← article folder (folder name = display name)
│   │           ├── meta.yaml        ← slug / title / date / styles
│   │           ├── content.md       ← body (or content.html)
│   │           └── imgs/            ← attachments (optional)
│   ├── site.yaml                ← site-wide settings (§ 11)
│   ├── templates/               ← page-layout HTML (header / nav / footer / structure)
│   │   └── article.html · category.html · home.html · 404.html
│   ├── styles/                  ← site-wide stylesheet
│   │   └── common_template.css      ← loaded as /assets/common_template.css
│   └── branding/                ← site-identity assets
│       └── default-og.png           ← default og:image (favicon / logo go here too)
│
├── system/                  ← ★ the program (you do not touch this to run your site)
│   ├── scripts/                 ← build-time Python package (Heron.py's internal modules)
│   │   ├── __init__.py             ← __version__ (single source of the version string)
│   │   ├── yaml_parser.py · models.py · slugs.py · parsedown.py · markdown.py
│   │   ├── seo.py · search.py · sitemap.py · feed.py · images.py
│   │   ├── cache.py · report.py
│   │   └── builder.py              ← the build pipeline (Builder class)
│   ├── runtime/                 ← serve-time code (runs on a visitor's request)
│   │   ├── search.php               ← runtime search (routing / filter / render)
│   │   ├── search_tokenize.php      ← Py↔PHP shared tokenizer (single source of truth)
│   │   ├── search_bm25.php          ← BM25 score + snippet (the two are inlined into search.php at build)
│   │   ├── pagination.js            ← pagination (builds nav at runtime)
│   │   └── imgslidebox.js           ← image slideshow (builds nav at runtime)
│   ├── admin/                   ← Pond — local authoring tool logic (§ 17)
│   │   ├── render_one.py · slug_one.py    ← reuse scripts.markdown / scripts.slugs
│   │   ├── lib/                     ← fs · proc · metayaml · articles (PHP)
│   │   └── views/                   ← layout · list · new · edit · build (PHP)
│   └── tests/                   ← unit tests (429) + run_diagnostics.py (6 sections)
│
├── dist/                    ← build output (deploy target / do not edit by hand)
│
├── Heron.py                 ← build entry point (puts its system/ on sys.path)
├── Pond.php                 ← local authoring entry point (thin router — § 17, not in dist)
├── README.md                ← this document (English)
└── README.ko.md             ← Korean guide

auto-generated at the project root on build (recommend .gitignore):
  build-report.md   ← progress transcript + summary + follow-ups + per-step timing (outside dist/)
  .build_cache/     ← per-article incremental cache + tokenizer parity cache
```

> **Where does `dist/assets/` come from** — the builder aggregates three sources into one `dist/assets/`: `user/styles/*.css`, `user/branding/*`, and `system/runtime/*.js` (the `/assets/{path}` URL contract is unchanged from v1.4.x). The `system/runtime/*.php` files are serve-time code and are inlined into `dist/search.php` separately.

> **Important:** files inside `dist/` are overwritten on every build. Make changes under `user/` (`articles/`, `site.yaml`, `templates/`, `styles/`, `branding/`) and rebuild. `system/` is the program — you have no reason to touch it to run your site.

---

## 4. Writing articles

### 4-1. Create an article folder

Under a category folder inside `user/articles/`, create a new folder with `meta.yaml` + `content.md` (or `content.html`).

- Folder name: Korean, English, spaces, special characters all allowed. **The folder name is the display name** (link text).
- The folder name is *not* used in the URL — the URL comes from `meta.yaml`'s `slug`.

### 4-2. meta.yaml

```yaml
# ── required ──
slug: my-first-post          # URL identifier. Globally unique
title: My First Post         # top of the body + <title>
date: 2026-05-07             # first-published date YYYY-MM-DD

# ── optional ──
updated: 2026-06-01          # revision date; must be ≥ date
noindex: true                # exclude only this article from search engines
tags: [intro, sample]        # topics (used in feed <category>)
use_common_css: false        # cut the shared CSS link (default true)
lang: en                     # override <html lang> for this article

seo:                         # all sub-keys optional
  title_prefix:              #   <title> prefix/suffix; falls back to site default
  title_suffix:
  description:               #   search / social / feed summary (effectively required)
  author:                    #   falls back to site.default_author
  canonical:                 #   auto-generated if empty
  og_title:                  #   falls back to <title>
  og_description:            #   falls back to description
  og_image:                  #   falls back to site.default_og_image
  og_image_alt:
  og_type: article
  twitter_card: summary_large_image
  twitter_image:
  jsonld:                    #   per-article JSON-LD opt-out (false = not emitted)

styles:                      # § 4-6 — inline tweaks + external CSS, two channels
  # 1: style.css             #   integer key = external CSS file (inside the article folder)
  p:                         #   string key = inline rule
    text-indent: 0
    line-height: 1.7em
```

**slug rules** — lowercase letters/digits/hyphens only, starting and ending alphanumeric, globally unique, reserved words (`assets`/`search`) forbidden, independent of category.

`seo.description` is effectively required: if missing/empty the build passes but records a BuildReport issue (exempt for `noindex: true` articles). No `<meta name="keywords">` is emitted (search engines ignore it).

**No `{{UPPERCASE}}` placeholders in metadata** — `title` / `seo.description` / `tags` / `seo.author` flow through the builder's template substitution. Do not put a literal `{{NAME}}` (uppercase/underscore, regex `{{[A-Z_][A-Z0-9_]*}}`) in these four fields; if it matches a builder variable (`{{COPYRIGHT_YEAR}}`, `{{BODY}}`, …) that value leaks into the output, and non-variable uppercase tokens are stripped + warned. Safe forms: lowercase `{{foo}}`, inner spaces `{{ FOO }}`, single braces `{NAME}`, leading digit `{{1A}}`, non-ASCII `{{변수}}`.

### 4-3. content.md (Markdown)

The parser is [system/scripts/parsedown.py](system/scripts/parsedown.py) (a Python port of Parsedown 1.7.4): close to standard CommonMark plus this system's own syntax (§ 9).

**Image paths** — relative to the article folder; rewritten to absolute at build:

```markdown
![photo](./imgs/photo.jpg)   →   <img src="/my-slug/imgs/photo.jpg" alt="photo">
![ext](https://example.com/i.jpg)   ← external URLs are not rewritten
```

**Section markers** — split the body into `<div class='gap'><p>subtitle</p></div><section>…</section>`:

- `===text===` (on its own line) — close the previous section + new gap (text) + open a new section.
- `======` (exactly six equals) — explicitly close the current section.
- `===` inside code blocks is ignored. The body always starts with an automatic first gap (the article `title`) + first section.

### 4-4. content.html (HTML body)

Write only the body fragment (no `<html>/<head>/<body>`). For migrating existing HTML articles — written HTML goes in **verbatim** (the markdown auto-wrap and section markers do not apply). `content.md` and `content.html` must not both exist (build aborts).

**PHP function auto-conversion** — two functions are converted to HTML:

```html
<?php imgBox("./imgs/p.jpg", "caption", "alt") ?>
  → <div class="imgBox"><img src="/my-slug/imgs/p.jpg" alt="alt"><p class="caption">caption</p></div>

<?php imgSlideBox("./src_slide") ?>
  → images in src_slide/ as an alphabetized slideshow (bottom-center dot indicator, built by JS at runtime)
```

A multi-statement `<?php … imgBox(); imgBox(); … ?>` block is also simulated to static HTML if it contains only imgBox/imgSlideBox. If other live statements remain, the block is kept verbatim and the article is emitted as `.php` (§ 8 PHP auto-detection). Captions interpolate `{$name}` from `user/site.yaml`'s `php_globals` (§ 11).

### 4-5. Attaching assets

- **Per-article assets** — placed inside the article folder. Everything except `meta.yaml`/`content.*` and `_`/`.`-prefixed entries is copied to `dist/{slug}/` (URL `/{slug}/imgs/…`). `_`/`.`-prefixed files/subfolders are treated as private and not copied (§ 6).
- **Site-wide assets** — shared CSS lives in `user/styles/`, identity assets (favicon/logo/default OG) in `user/branding/`, and the runtime JS in `system/runtime/`. All three are copied to `dist/assets/` and load as `/assets/{path}`.

### 4-6. styles — per-article CSS

Under the single `styles:` key, two channels split automatically *by key type*:

| Channel | Key form | Value | Output | Intent |
|---|---|---|---|---|
| Inline rule | string (tag/selector) | dict | head `<style>` | small overrides of common properties |
| External CSS | integer (1, 2, 3…) | path inside the article folder | head `<link>` | your own CSS file (ascending integer order) |

**Load order:** `common_template.css` → external CSS (integer key order) → inline `<style>` (inline has the last word).

- Tag keys (p, h3, ul, blockquote, a, code…) are auto-wrapped as `section TAG` selectors.
- Keys containing whitespace, `>`, `+`, `~`, `,`, `.`, `[attr]` are used as-is.
- **Inline channel limit (intentional — promote to external CSS):** at-rules (`@media`/`@keyframes`/`@font-face`), nesting, multi-line single property, inline comments next to a value.
- **`use_common_css: false`** cuts the shared CSS link entirely (for landing/single-service pages). Default `true`.

---

## 5. Categories

The folder structure under `user/articles/` *is* the category structure — no separate config. The builder distinguishes article folders from category folders by the presence of `content.md`/`content.html` (neither present → category).

**Folder name → slug:** non-ASCII → 4-digit hex codepoints, NFKD normalize, keep alphanumerics/spaces/hyphens, drop parentheses, collapse to single hyphens, lowercase.

```
Blog               → blog
3D Printing        → 3d-printing
Research Notes (CS) → research-notes-cs
블로그              → be94-b85c-adf8   (non-ASCII → hex, build warning; prefer ASCII folder names)
```

**Index pages** — every category (top and sub) gets its own index. Top-level categories embed child subcategories as sections plus a direct-articles section. A category with no articles gets no index + a build warning.

**A category folder's meta.yaml** (all optional, different schema from articles — no `slug`/`date`):

| Field | Default | Meaning |
|---|---|---|
| `per_page` | site `category_per_page` (20) | articles per page on its own index |
| `preview_per_page` | site `category_preview_per_page` (5) | count when embedded as a section in a parent |
| `layout` | `list` | `list` / `gallery` (image tiles) |
| `styles` | {} | same two channels as articles |
| `use_common_css` | `true` | |
| `template` | `category.html` | `name.html`→`user/templates/`, `./name.html`→folder |
| `lang` | site `lang` | `<html lang>` override |
| `title` | folder name | index `<title>` body |
| `seo` | {} | same as article `seo:` |
| `priority` | `0` | sibling section ordering in a parent index (higher first) |
| `nav_priority` | `0` | top-level nav ordering (separate axis from priority) |

---

## 6. Managing articles

- **Private** — prefix the file/folder name with `_` or `.`. Any segment so prefixed hides everything below it from articles, categories, nav, and assets, and `dist/{slug}/` is removed on build. `_` = intentionally private/editing; `.` = OS/VCS hidden (`.git`, `.DS_Store`) and also guards folders you believe are hidden (e.g. `.draft`).
- **Move** — move an article folder to another category; the URL stays as long as `slug` is unchanged.
- **Delete** — delete the article folder and rebuild; `dist/{slug}/` is pruned (orphan cleanup).

To do these in a browser instead of a file explorer, see [§ 17 Pond.php](#17-local-authoring--pondphp).

---

## 7. Build

```bash
python Heron.py            # normal build (incremental cache)
python Heron.py --clean    # wipe dist/ + .build_cache/, then build
```

**Build report** — content defects do not abort the build; the affected article is partially omitted and the build completes. On exit, issues are grouped on stderr and persisted to `build-report.md`:

| Class | Meaning | Examples |
|---|---|---|
| **issue** | author must fix; that article is partially omitted | missing `seo.description` (exempt if noindex), slug regex/reserved/duplicate conflict, bad date, non-list `tags`, **broken internal link** |
| **warning** | output fine, worth a look | non-ASCII folder name hex conversion, missing asset, empty category, image optimization failure, AdSense `exclude_urls` with 0 matches, `_`-prefixed asset reference |
| **PHP-built articles** | *intended output report*, not an issue — which articles fell back to `.php` (the author/web-developer's explicit PHP use) | a body with live `<?php`/`<?=` beyond imgBox/imgSlideBox |

**Build aborts (system faults only)** — only defects the content author cannot control abort immediately: template missing / no `user/articles/` directory / `site.yaml` missing or unparseable / `images.enabled: true` but Pillow absent *when raster images actually exist*.

---

## 8. Output structure and URLs

```
dist/
├── index.html  404.html  robots.txt  ads.txt  sitemap.xml  feed.atom  feed.rss
├── assets/                  ← site-wide resources
├── {slug}/                  ← article page + article assets (same folder)
│   ├── index.html  (or index.php)
│   └── imgs/ …
├── blog/                    ← category index
│   ├── index.html
│   └── tutorials/index.html ← subcategory
└── search.php               ← index + tokenizer + BM25, all inlined
```

| Page | URL | Example |
|---|---|---|
| Home | `/` | `https://siheonlee.com/` |
| Article | `/{slug}/` | `/mask-intake-3d-printing/` |
| Category (top) | `/{cat}/` | `/blog/` |
| Category (sub) | `/{top}/{sub}/` | `/blog/tutorials/` |
| Article asset | `/{slug}/{path}` | `/mask-intake-3d-printing/imgs/p.jpg` |
| Site-wide asset | `/assets/{path}` | `/assets/common_template.css` |

- All article/category URLs end with `/`; slashless URLs get a 301 from Apache.
- Article URLs are independent of category. Reserved slugs (`assets`/`search`, the `Builder.RESERVED_SLUGS` constant) are forbidden.
- **PHP auto-detection** — if `<?php`/`<?=` remains in the rendered result, the article is emitted as `index.php`. The URL stays `/{slug}/`. The BuildReport lists these under "PHP-built articles" — not a fault, but the author's intent (PHP 7.4+ assumed on the deploy server).

---

## 9. Markdown syntax

Close to standard CommonMark — headings (`#`–`######`, Setext), inline (`**bold**` `*italic*` `~~strike~~` `` `code` ``), links/images/reference links/autolinks, nested lists, nested quotes, tables with alignment, rules, block-level HTML passthrough. `<>&` inside code blocks is escaped (so `<?php` does not execute).

**This system's own syntax:**

```markdown
===Section title===          section marker (§ 4-3). ====== (six equals) explicitly closes
![[image alt]](./imgs/p.jpg) {caption}   → <div class="imgBox"><img …><p class="caption">caption</p></div>
```

Omit `{...}` if no caption. The image-box syntax is converted to raw HTML just before the parser runs.

---

## 10. SEO settings

Article, home, and category pages share one fallback chain (the single function [`build_meta_tags`](system/scripts/seo.py)). Body title: article = `meta.title`, home = `user/articles/meta.yaml title` > `site.name`, category = `meta.title` > folder name.

The output `<meta>`/OG/Twitter tags share fallbacks: `<title>` = `{prefix}{title}{suffix}`; `meta description` = `seo.description` (else omitted + issue, exempt for noindex); `canonical` auto if empty; `og:title` → `<title>`; `og:description` → description; `og:image` → `site.default_og_image`; `og:type` = article (articles) / website (home, categories). **If a fallback resolves to empty, the tag itself is omitted.**

**Indexing policy** — indexed by default. Only `noindex: true` articles get `<meta robots noindex>`; they are also excluded from `sitemap.xml`, the `search.php` index, and (within the feed window) RSS/Atom. `search.php` is separately `noindex,follow`.

**Default og:image** — the asset `site.default_og_image` points to is copied to `dist/` verbatim even if raster (the `_copy_site_assets` exception): its consumer is a social-link unfurler, not the `<img>` post-processor, so multi-resolution is meaningless and some crawlers (KakaoTalk, some Facebook) cannot render WebP og:images. The default is `user/branding/default-og.png` (1200×630).

**JSON-LD** — **article pages** get one `<script type="application/ld+json">` with a `@graph` of an `Article` node and (if ≥ 2 crumbs) a `BreadcrumbList` node sharing a single source with the nav breadcrumb. It augments rather than replaces the `<meta>`/OG/Twitter tags. Off via `site.yaml` → `jsonld.enabled: false` (global) or article `seo.jsonld: false`. Not emitted on home/category pages.

---

## 11. Site-wide settings — site.yaml

Only *truly global* (multi-page) settings live in `user/site.yaml`. Page-type-specific settings go in that page's `meta.yaml`.

| Location | Settings |
|---|---|
| `user/site.yaml` | domain · name · copyright · lang · default_og_image / `category_per_page` · `category_preview_per_page` / robots.txt / `description_truncate` / `images:` / `jsonld:` / `prev_next:` / `php_globals:` / `google_adsense:` |
| `user/articles/meta.yaml` | home only — `per_page` `excludes_categories` `lang` `layout` `styles` `title` `seo:` |
| `user/articles/<cat>/meta.yaml` | category only (§ 5 table) |
| `user/articles/<cat>/<article>/meta.yaml` | article only (§ 4-2) |

```yaml
domain: siheonlee.com
base_url: https://siheonlee.com
name: heron
main_title: heron
default_author: 이시헌
default_og_image: /assets/default-og.png
lang: ko
copyright_holder: 이시헌
copyright_year_start: 2025
category_per_page: 20
category_preview_per_page: 5
description_truncate: 150             # feed summary cap (word-boundary aware)
images:                               # automatic image optimization
  enabled: true                       #   false → build without Pillow
  widths: [400, 800, 1600]
  max_width: 1600
  quality: 85
  lazy_loading: true
  default_sizes: "(max-width: 800px) 100vw, 800px"
jsonld:
  enabled: true                       #   per-article: meta.yaml seo.jsonld: false
prev_next:
  enabled: true                       #   sibling pool = same-parent non-noindex, date asc
php_globals:                          # PHP signature variables for imgBox captions
  reference_hanbyeol: "Character illustration by 김한별"
google_adsense:                       # all three fields empty → AdSense disabled
  ads_txt: |
    google.com, pub-XXXXXXXXXXXXXXXX, DIRECT, fXXXXXXXXXXXXXXXX
  head_script: |
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXX" crossorigin="anonymous"></script>
  exclude_urls: ['/404.html', '/search.php', '/about/']   # URLs to skip injection; [] = inject everywhere
```

The five v1.4.0-retired keys (`reserved_slugs` / `warn_on_underscore_ref` / `warn_on_missing_asset` / `error_404_title` / `search_title`) are now code constants in `system/scripts/builder.py`; if left in `site.yaml`, the parser silently ignores them.

---

## 12. Internals — parser / search / feed

### Markdown parser — Parsedown 1.7.4 Python port

A single implementation [system/scripts/parsedown.py](system/scripts/parsedown.py). The port matches the original method-for-method and is byte-identical to PHP Parsedown on 79 fixtures. **Operating policy — fork:** this port is the single source of truth; all fixes go into it directly.

### YAML parser — an intentional subset

`site.yaml`/`meta.yaml` use a self-implemented parser ([system/scripts/yaml_parser.py](system/scripts/yaml_parser.py)) covering only the syntax actually used: flat key-value, nested mapping, block list, inline list (`[a,b]`, including multi-line), quoted strings, ints/bools/null, line `#` comments. No anchors/aliases/folded scalars/flow mappings/inline comments. **No plan to adopt PyYAML.**

### Search — search.php

Zero client JS, zero external search engine. **Indexes only the 3 metadata fields (title / seo.description / tags)** (no body search; the first 1500 chars of body plain text are kept as `body_snippet`).

- **Tokenizer** — English/digits = lowercase word units (exact match); Korean = syllable 2-grams (natural partial search); single-character Korean excluded. [system/scripts/search.py](system/scripts/search.py) `search_tokenize()` ↔ [system/runtime/search_tokenize.php](system/runtime/search_tokenize.php) are a single source of truth, parity-verified against 18 fixtures every build (warns + skips if PHP absent), cached in `.build_cache/parity.json`.
- **Scoring** — per-field Okapi BM25, weighted sum (title 3.0 / desc 1.5 / tags 2.0) with phrase boosts. Parameters are baked into the index so scores are deterministic.
- **Security** — 100-char query cap, all output `htmlspecialchars`-escaped, result page `noindex,follow`.
- **OPcache assumption** — search is designed around a single OPcache-resident PHP file: the index is an inline static PHP array, so from the second request on there is no disk I/O / no JSON parse / no `require_once`, giving single-digit-ms responses. It is deliberately **not** moved to client JS (that would force a multi-KB index download + JS parse on first search).

### RSS / Atom feeds

`dist/feed.atom` (Atom 1.0) + `dist/feed.rss` (RSS 2.0) share one entry list (model in [system/scripts/feed.py](system/scripts/feed.py)): non-noindex articles, minus `excludes_categories`, newest N (default 20), `updated` (or `date`) descending. All times are `00:00:00 UTC` and the feed timestamp is the newest entry lastmod (not build time) — so unchanged content yields identical bytes every build.

### Incremental cache

Per-article cache lives in `.build_cache/articles/`. An article hits if its inputs (meta.yaml + content.* + asset mtime/size + a global hash) are unchanged. Changing `site.yaml`, a template, builder code, or the shared CSS invalidates all articles via the global hash. Search/sitemap/feed/home/category/assets are rebuilt every build (all articles are their input).

### Image multiprocessing

Raster conversion fans out across `ProcessPoolExecutor`; the worker is a module-level free function (Windows-spawn safe). Serial fallback when fewer than 4 raster jobs or ≤ 1 worker.

---

## 13. Deployment

Build, upload `dist/` to the server DocumentRoot, and register an Apache VirtualHost **once**. Adding/removing articles afterward needs no server change. No `.htaccess`.

```bash
rsync -avz --delete dist/ user@siheonlee.com:/var/www/siheonlee.com/
```

```apache
<VirtualHost *:443>
    ServerName siheonlee.com
    DocumentRoot /var/www/siheonlee.com         # ← deploy the contents of dist/
    <Directory /var/www/siheonlee.com>
        AllowOverride None
        DirectoryIndex index.html index.php
        DirectorySlash On                       # /slug → /slug/ redirect
        Options -Indexes -MultiViews +FollowSymLinks
        Require all granted
    </Directory>
    AddType application/x-httpd-php .php
    ErrorDocument 404 /404.html
    AddDefaultCharset UTF-8
</VirtualHost>
```

- The **build machine** does not need PHP (the parser is pure Python). PHP CLI, if present, only enables the parity check.
- The **deploy server** needs **PHP 7.4+ + mbstring** (search.php + `.php` output articles). This is an assumption, not a limit.
- ⚠️ **Never deploy `Pond.php` / `system/admin/`.** The `rsync` above uploads only `dist/`, so they never leave the build machine — and `Pond.php` refuses to run unless served by PHP's built-in server on loopback (§ 17).

---

## 14. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Build OK but CSS broken | Absolute paths (`/assets/...`). Use `cd dist && python -m http.server 8000`, not double-click. |
| Build without PHP? | Yes (parser is pure Python). Without PHP CLI only the parity check warns + skips. The deploy server needs PHP. |
| styles not applied | ① styles are injected for articles/home/categories alike — write home styles in `user/articles/meta.yaml`. ② check the template has `{{PAGE_STYLES}}`/`{{PAGE_STYLESHEETS}}`. ③ specificity → use a more specific selector or `!important`. ④ `:hover`/`#id`/`::before` need YAML quoting. |
| `slug conflict` | two articles share a slug. Change one. |
| URL is `/be94-…/` | non-ASCII folder name auto-converted to hex. Use an ASCII folder name. |
| Image missing | Is it inside the article folder? `./imgs/p.jpg` relative path? Check the `missing asset` warning and `dist/{slug}/imgs/`. |
| `.php` instead of `.html` | An unprocessed `<?php` remains. imgBox/imgSlideBox convert to HTML, so they stay `.html`. |
| Rebuild dist/ fresh | `python Heron.py --clean`. |

---

## 15. Design principles and limits

**Design principles**

1. **Permanent URLs** — independent of category move / folder rename as long as the slug is stable.
2. **Display name ↔ URL slug separation** — screen = folder name, URL = ASCII slug.
3. **Explicit ops dependencies** — Python 3 + Pillow (build), PHP (runtime). Honestly stated + opt-out provided, not "zero dependencies".
4. **Server ↔ content separation** — no `.htaccess`; growing the article count never changes server config.
5. **Build safety** — `user/articles/` is read-only to the builder; it never edits sources.
6. **Single parser** — one Parsedown Python port.
7. **Declarative per-page presentation** — controlled in `meta.yaml`.
8. **Per-article indexing** — allowed by default, only `noindex: true` excluded.
9. **Single-source tokenizer** — Py/PHP parity verified every build.
10. **Body ↔ metadata separation** — SEO/OG/feed copy comes only from author-written `seo:` values, never guessed from the body.
11. **`template:` cross-use — allowed but announced** — a page may pick a template of a different kind; placeholders the builder cannot fill are stripped + warned (neither silent strip nor auto-reject).
12. **(v1.5.0) user / system separation** — `user/` is everything you own and edit; `system/` is the program. The presentation surface (templates, CSS, identity assets) lives in `user/`, not inside the builder.

**Limits (intrinsic)** — single-frame image optimization (animated GIF → first frame only); incremental cache covers article pages only; internal-link validation covers article pages only; the Pond preview is body-fidelity only (full-page chrome is verified by building); Pond is local single-user with no auth.

---

## 16. Changelog

> Paths like `scripts/…`, `templates/…`, `assets/…`, `tests/…` in the entries below are historical (the names at the time): v0.8.1–v1.4.x lived under `src/`, and since v1.5.0 the real locations split into `system/scripts`, `system/runtime`, `user/templates`, `user/styles`, `user/branding`, `system/tests` (§ 3). `build.py` → `Heron.py` and `admin.php` → `Pond.php` are also v1.5.0.
> Code integrity: a **docs-only release** = clean rebuild from canonical sources with dist sha256 == the previous code copy. A **code release** = determinism (two builds identical) + an enumerated diff against the previous code release.

| Version | Date | Summary |
|---|---|---|
| **v1.5.1** | 2026-05-30 | **v1.5.0 stabilization refactor** (code release, dist **byte-identical**) — a pure internal refactor of code consistency/readability with no behavior or output change. ① **Import hygiene**: in `builder.py` the seo/search/sitemap/feed/report/cache imports that sat between the `_pagination_*` helper defs are hoisted into the top import block (PEP 8); the unused `ALL_IMAGE_EXTS` import is dropped. ② **Cross-module encapsulation**: `images._split_url`/`_build_srcset` promoted to public `split_url`/`build_srcset` (builder imported them across the module boundary — underscore = module-internal convention clash); `_HAS_PIL` kept (tests import it directly, a de-facto public flag). ③ **De-duplication (DRY)**: the `SeoMeta(...)` construction duplicated 1:1 across article/category/home folded into `_seo_from_dict`; the priority/nav_priority integer parse-with-fallback at three sites folded into `_int_meta_field` (3-state + issue messages preserved byte-for-byte). ④ **Dead code removed**: `markdown._SECTION_SCOPED_TAGS` + the always-same-result branch in `_resolve_selector` (every bare tag becomes `section TAG` regardless of the whitelist), `BuildCache.stats()` (never called). ⑤ **Stale naming fixed**: `search.run_parity_test`/`_parity_cache_key` arg `templates_dir` → `runtime_dir` (reflects the v1.5.0 folder move; positional call so behavior unchanged), `images.split_url` docstring return-tuple corrected, `Pond.php`'s `site.yaml reserved_slugs` comment updated to `Builder.RESERVED_SLUGS`. Code integrity: **clean rebuild from canonical Articles, dist 787 files sha256 == v1.5.0** (not an enumerated diff — fully byte-identical). Determinism: two builds identical. 429 tests · 6/6 diagnostics unchanged. |
| v1.5.0 | 2026-05-29 | Structure release — root split into `user/` (what you edit) and `system/` (the program); entry points renamed `Heron.py` / `Pond.php`. Pure source-layout change, so dist is byte-identical to v1.4.2. |
| v1.4.1 | 2026-05-28 | Fixed the v1.4.0 internal-link validation regex (`\bhref=` → `\s+href=`) — no more `data-href` mismatch. dist byte-invariant. |
| v1.4.0 | 2026-05-28 | Six-feature bundle — prev/next nav, article-end meta line, dark mode, internal-link validation, five site.yaml keys → code constants, BuildReport "PHP-built articles" category. |
| v1.3.0 | 2026-05-28 | Build-speed bundle — per-step timing, image multiprocessing, asset-pass unification, tokenizer parity cache. dist byte-invariant. |
| v1.2.2 | 2026-05-21 | `yaml_parser` multi-line inline list support (accumulate lines from `[` to `]`). dist unchanged. |
| v1.2.1 | 2026-05-21 | Ops-noise cleanup — `noindex: true` articles exempt from the `seo.description` check; `warn_on_stale_updated` warning dropped. dist byte-invariant. |
| v1.2.0 | 2026-05-21 | v1.1.5 documentation stabilization. dist unchanged. |
| v1.1.5 | 2026-05-20 | AdSense URL-based ad blocking — `exclude_urls` (exact match, per-article possible); empty list = inject everywhere. Replaces v1.1.4's `exclude_pages`. |
| v1.1.4 | 2026-05-20 | AdSense page-type exclusion (`exclude_pages: [article/home/category/404/search]`). Unified into URL-based in v1.1.5. |
| v1.1.3 | 2026-05-20 | Google AdSense integration (`google_adsense.ads_txt` / `head_script`) + default `default-og.png` replaced with a standard 1200×630 OG image. |
| v1.1.2 | 2026-05-20 | imgSlideBox deploy-incident fix + paginated redesign — restored missing CSS `.slide{display:none}` + bottom-center dot indicator (built by runtime JS, static HTML unchanged). |
| v1.1.1 | 2026-05-20 | imgBox deploy-incident fix — multi-statement PHP blocks failed to simulate and leaked raw PHP. Rewrote the `simulate_php_in_html` block scanner + added `site.yaml php_globals` + caption raw preserved. |
| v1.1.0 | 2026-05-19 | Local authoring tool `admin.php` added (now Pond) — mirrors the `build.py` pattern: write/edit, move, hide, delete, preview, one-click build. dist byte-invariant (admin is upstream of the build). |
| v1.0.2 | 2026-05-19 | Home default post count 5 → 10 (canonical `articles/meta.yaml` sets `per_page: 10`, so dist impact 0). |
| v1.0.1 | 2026-05-19 | Subcategory header links — arrow dropped; the subcategory name itself links to its own page (`color: inherit; text-decoration: none`). |
| v1.0.0 | 2026-05-19 | First stable release — default og:image asset pass-through (raster preserved), `articles/About` noindex. |
| v0.8.4 | 2026-05-19 | v0.8.3 documentation stabilization. dist byte-identical to v0.8.3. |
| v0.8.3 | 2026-05-18 | schema.org JSON-LD + correct breadcrumbs — `Article` + (≥ 2 crumbs) `BreadcrumbList` in the article `<head>`; off switches (`jsonld.enabled` / `seo.jsonld`). Build-excluded prefixes `_`/`.` unified. |
| v0.8.2 | 2026-05-18 | Code soundness — `__version__` decoupled (feed `<generator>` version-free), stricter argparse, per-Builder build report. |
| v0.8.1 | 2026-05-17 | Folder cleanup — builder moved under `src/`. Behavior/output unchanged (v1.5.0's `user/`+`system/` split is the sequel). |
| v0.8.0 | 2026-05-17 | README code-consistency fixes. No code/dist change. |
| v0.7.2 | 2026-05-17 | 16-step progress headers + live counter + persistent `build-report.md`. No output-logic change. |
| v0.7.1 | 2026-05-16 | Stabilization. No behavior change. |
| v0.7.0 | 2026-05-16 | Incremental build cache (per-article). Added `--no-cache` / `--clean-cache`. |
| v0.6.5 | 2026-05-15 | Stabilization — auto `reset_report`, 3-pass `_render_template`, removed the forced `og_type` default. |
| v0.6.4 | 2026-05-15 | Home/category CSS unification + `template:` key. |
| v0.6.3 | 2026-05-15 | Per-article external CSS files (integer keys) + `use_common_css` toggle. |
| v0.6.2 | 2026-05-15 | Home/category SEO meta tags output. |
| v0.6.1 | 2026-05-15 | Docs/comment/output readability stabilization. No behavior change. |
| v0.6.0 | 2026-05-15 | Search 3-field metadata index (v4) + single-file inline search.php. Diagnostics script added. |
| v0.5.5 | 2026-05-15 | Body ↔ metadata separation principle + unified build report (`report.py`). |
| v0.5.4 | 2026-05-14 | `<title>` fallback chain generalized + word-boundary truncate + `nav_priority`. |
| v0.5.3 | 2026-05-14 | `tags` + `layout: gallery` + RSS/Atom feeds. |
| v0.5.2 | 2026-05-14 | Asset path unification (`dist/src/{slug}/` → `dist/{slug}/`). |
| v0.5.1 | 2026-05-14 | Automatic image optimization (multi-resolution WebP) + lazy loading. |
| v0.5.0 | 2026-05-14 | Okapi BM25 search (TF-sum → BM25 + phrase boost). Index v3. |
| v0.4.7 | 2026-05-14 | Docs/code consistency restored. dist byte-identical to v0.4.6. |
| v0.4.6 | 2026-05-14 | Pagination FOUC removal + `articles/meta.yaml` + `priority` + config unification. |
| v0.4.5 | 2026-05-14 | Pagination + i18n + subcategory indexes + category meta.yaml. |
| v0.4.4 | 2026-05-14 | Auto `sitemap.xml` + robots.txt Sitemap directive. |
| v0.4.3 | 2026-05-14 | `<title>` normalization + markdown section markers + `seo:` grouping. |
| v0.4.2 | 2026-05-14 | Consistency-gap cleanup (slug ↔ category collision pre-blocked, search.php noindex,follow). |
| v0.4.1 | 2026-05-14 | Build PHP dependency removed — Parsedown 1.7.4 Python port. dist byte-identical to v0.4.0. |
| v0.4.0 | 2026-05-13 | Honest catchphrase + indexing-policy fix (global noindex removed) + module split. |
| v0.3.2 | 2026-05-10 | Search UI cleanup + category-scoped search. Index v2. |
| v0.3.1 | 2026-05-09 | In-site search (`search-index.json` + search.php). |
| v0.3 | 2026-05-09 | Parsedown adoption + per-article styles override. |
| v0.2 | 2026-05-09 | Previous-site UI/UX preserved. About merged as a normal article. |
| v0.1 | — | Python-stdlib-only SSG, first working build. Core design principles established. |

---

## 17. Local authoring — Pond.php

**Pond** is a **local-only, single-user** tool for writing/editing, moving categories, hiding/deleting, **live body preview**, and **one-click build** from a browser instead of a file explorer. It mirrors the `Heron.py` pattern — a thin entry point `Pond.php` at the version-folder root plus all logic in `system/admin/`. Because the builder scans only `user/articles/`, these never leak into `dist/` and are independent of build determinism (Pond is an authoring tool *upstream* of the build: it writes `user/articles/`, and `Heron.py` still only reads — design principle 5 intact).

### 17-1. Run

From the version folder:

```bash
php -S 127.0.0.1:8001 Pond.php
```

Browse to `http://127.0.0.1:8001/`. Needs **PHP 7.4+** (8.x recommended) + **Python 3** (preview/slug/build call the real `scripts.*`). Quit with `Ctrl+C`.

### 17-2. Security — never put it on a public server

Local single-user only. Layered guards:

- **SAPI + loopback guard** — `Pond.php` returns **403** unless served by PHP's built-in server (`cli-server`) on `127.0.0.1`/`::1`. It does not open even under Apache `mod_php`/`php-fpm`.
- **Not deployed** — the § 13 `rsync` uploads only `dist/`; `Pond.php`/`system/admin/` never leave the build machine.
- **CSRF** — state changes verify a session token. No auth (unnecessary for local single-user — noted as a limit in § 15).

### 17-3. Features

- **List** (`/`) — article tree, each with edit / move (dropdown) / visibility toggle / delete; `.trash` contents shown.
- **New** (`?a=new`) — pick a category + folder name (Korean OK) → `slug_one.py` suggests a slug with the **same** rules as the build.
- **Edit** (`?a=edit&id=…`) — split view: left = body (`content.md`/`.html`, no frontmatter — body↔meta separation), right = meta form + collapsible **raw `meta.yaml`** + live preview. **Saving is raw-`meta.yaml`-based** (comments/advanced keys/`styles` preserved); raw is the source of truth.
- **Move/hide/delete** — folder rename (slug stays → URL permanent) / `_` prefix toggle / move to `user/articles/.trash/` (`.`-prefixed → auto-excluded, recoverable).
- **One-click build** — runs `python Heron.py` (`--clean` optional) in the version folder and shows the output.

### 17-4. Preview = body fidelity (single parser)

No separate markdown engine. `system/admin/render_one.py` reuses the very `scripts.markdown` path the builder uses, so the preview *body* is byte-identical to the output. Full-page chrome (header/nav/footer, `<meta>`, JSON-LD) is not built — that is the template-fill step — so the full-page exact version is verified by building to `dist/`. This parity is locked by `system/tests/test_render_one.py`.

---

*Heron v1.5.1 — build with Python + Pillow, runtime PHP (OPcache recommended). Full release history in [README.ko.md § 16](README.ko.md).*

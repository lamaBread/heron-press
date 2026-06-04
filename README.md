# Heron v1.11.2 — User Guide

**Heron** is a lightweight, **PHP-targeted static site generator**: keep **one folder per article** for its body and attachments, and `python Heron.py` builds the whole site once.

> 🇰🇷 한국어 사용설명서는 [README.ko.md](README.ko.md) 를 보세요. The two guides cover the same system at the same depth (bilingual parity).

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
6. [Managing articles — private / move / delete](#6-managing-articles--private--move--delete)
7. [Build](#7-build)
8. [Output structure and URLs](#8-output-structure-and-urls)
9. [Markdown syntax](#9-markdown-syntax)
10. [SEO settings](#10-seo-settings)
11. [Site-wide settings — site.yaml](#11-site-wide-settings--siteyaml)
12. [Internals — parser / search / feed](#12-internals--parser--search--feed)
13. [Deployment](#13-deployment)
14. [Troubleshooting](#14-troubleshooting)
15. [Design principles and limits](#15-design-principles-and-limits)
16. [Changelog](#16-changelog)
17. [Local authoring — Pond.php](#17-local-authoring--pondphp)
18. [Further update proposals](#18-further-update-proposals)

---

## 1. Quick start

**Requirements**

- **Python 3.x** (3.8+ recommended).
- **Pillow** — converts raster images to multi-resolution WebP. `pip install Pillow`. To skip it, set `images.enabled: false` in `site.yaml`.
- **PHP CLI** (optional) — if present, the build auto-verifies the Python↔PHP tokenizer parity. If absent, it warns and skips.

**Build** — open a terminal in this folder:

```bash
python Heron.py                # normal build (incremental cache)
python Heron.py --clean        # wipe dist/ and .build_cache/, then build
python Heron.py --clean-cache  # wipe the cache only, keep dist/
python Heron.py --no-cache     # disable the incremental cache
```

On success the output looks like:

```
Build start - Heron v1.8.0 (...)
[ 1/16] Load settings (site.yaml / tokenizer parity)
[ 2/16] Scan article folders (user/articles/)
   …  (each step has an [ n/16] header; heavy steps show a \r live counter)
[16/16] Prune orphaned output

Build complete: 47 articles, 19 categories, 0 to fix, 0 to review, N PHP builds.
Incremental cache: 0 hits / 47 misses (47 articles).
Report: build-report.md generated.
```

The first build misses every article (empty cache); later builds hit unchanged ones. Changing `site.yaml`, a template, or builder code invalidates everything.

"N PHP builds" is new in v1.4.0 — it counts articles that fell back to `index.php` because their body still contains live PHP statements beyond `imgBox`/`imgSlideBox`. This is not a defect but the author's (web developer's) intent (PHP 7.4+ is assumed on the deploy server). See the "PHP-built articles" section of `build-report.md` for which articles.

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
| 1 | Read `site.yaml` + tokenizer parity check (if PHP present) |
| 2 | Scan the `user/articles/` tree |
| 3 | Parse each article `meta.yaml` |
| 4 | Validate (slug duplicates/reserved/format) + build the category tree. Problem articles get an issue + are excluded individually; the build continues |
| 5 | Copy per-article assets → `dist/{slug}/`. Raster images become WebP via Pillow (multi-process) |
| 6 | Copy `user/styles` · `user/branding` · `system/runtime` (*.js) → `dist/assets/` (site-wide assets) |
| 7 | Copy category/home external CSS files into dist |
| 8 | Render article bodies (.md via parser, .html as-is) → `<img>` post-processing → style injection → template assembly |
| 9 | Category indexes (top-level + sub) |
| 10 | Home page |
| 11 | 404 page |
| 12 | `robots.txt` (with Sitemap directive) + `dist/ads.txt` (not generated, and a stale copy auto-removed, when `google_adsense.ads_txt` is empty) |
| 13 | `sitemap.xml` |
| 14 | `feed.atom` / `feed.rss` (same entry list) |
| 15 | `dist/search.php` — 3-field BM25 index + tokenizer + scorer inlined |
| 16 | Prune orphaned output |

---

## 3. Folder structure

Since v1.5.0 the root is split into **`user/` (what you edit) and `system/` (the program):**

```
heron-press/
│
├── user/                    ← ★ everything you own and edit
│   ├── articles/                ← all articles (ships with a runnable example set — § 4-7)
│   │   ├── About/                   ← top-level article (meta.yaml + content.html + assets)
│   │   └── Blog/                    ← category folder
│   │       └── Welcome to Heron/    ← article folder (folder name = display name)
│   │           ├── meta.yaml        ← slug / title / date / styles
│   │           ├── content.md       ← body (or content.html)
│   │           └── imgs/            ← attachments (optional)
│   ├── site.yaml                ← site-wide settings (§ 11)
│   ├── templates/               ← page-layout HTML (header / nav / footer / structure)
│   │   └── article.html · category.html · home.html · 404.html
│   ├── styles/                  ← site-wide stylesheet
│   │   └── common_template.css      ← loaded as /assets/common_template.css
│   ├── branding/                ← site-identity assets
│   │   └── default-og.png           ← default og:image (favicon / logo go here too)
│   └── .heron/                  ← (v1.6.0) machine-managed instance state — do not hand-edit
│       ├── version                  ← schema-version stamp (§ 17-6; survives system/ replacement)
│       ├── update.json              ← update-check cache (Pond banner; .gitignore)
│       ├── deploy.example.json      ← (v1.7.0) deploy-config template (committed; § 17-7)
│       ├── deploy.json              ← (v1.7.0) real deploy coordinates + key path (.gitignore)
│       └── backups/                 ← pre-migrate/update snapshots (.gitignore)
│
├── system/                  ← ★ the program (you do not touch this to run your site)
│   ├── MANIFEST.json            ← (v1.6.0) program-surface file list + sha256 (integrity / safe overlay)
│   ├── scripts/                 ← build-time Python package (Heron.py's internal modules)
│   │   ├── __init__.py             ← __version__ (single source of the program version string)
│   │   ├── yaml_parser.py          ← stdlib-only partial YAML implementation
│   │   ├── models.py               ← dataclass definitions
│   │   ├── slugs.py                ← folder name → URL slug
│   │   ├── parsedown.py            ← Parsedown 1.7.4 Python port
│   │   ├── markdown.py             ← body pre/post-processing + PHP function simulation
│   │   ├── seo.py                  ← <meta> + JSON-LD builder
│   │   ├── search.py               ← tokenizer / BM25 index / Py↔PHP parity
│   │   ├── sitemap.py              ← sitemap.xml
│   │   ├── feed.py                 ← RSS / Atom feeds (FeedDocument)
│   │   ├── images.py               ← WebP conversion + <img> post-processing
│   │   ├── cache.py                ← per-article incremental cache (BuildCache)
│   │   ├── report.py               ← BuildReport (issue/warning, render_markdown)
│   │   ├── i18n.py                 ← (v1.9.0) locale string lookup (Surface 1/3; en canonical + parser)
│   │   ├── version.py              ← (v1.6.0) schema-version stamp + semver compare
│   │   ├── migrations/             ← (v1.6.0) migration engine (ordered steps, mutate user/ only)
│   │   ├── update.py               ← (v1.6.0) GitHub self-update (download/verify/overlay)
│   │   ├── make_manifest.py        ← (v1.6.0) generate/verify MANIFEST.json
│   │   ├── rclone_bin.py           ← (v1.7.0) rclone binary acquisition (download/SHA256 verify/extract)
│   │   ├── deploy.py               ← (v1.7.0) dist server-deploy orchestration (rclone SFTP)
│   │   └── builder.py              ← the build pipeline (Builder class)
│   ├── runtime/                 ← serve-time code (runs on a visitor's request)
│   │   ├── search.php               ← runtime search (routing / filter / render)
│   │   ├── search_tokenize.php      ← Py↔PHP shared tokenizer (single source of truth)
│   │   ├── search_bm25.php          ← BM25 score + snippet (the two above are inlined into search.php at build)
│   │   ├── pagination.js            ← pagination (builds nav at runtime)
│   │   └── imgslidebox.js           ← image slideshow (builds nav at runtime)
│   ├── admin/                   ← Pond — local authoring tool logic (§ 17)
│   │   ├── render_one.py            ← render one article body (reuses scripts.markdown)
│   │   ├── slug_one.py              ← folder name → slug (reuses scripts.slugs)
│   │   ├── lib/                     ← fs · proc · metayaml · articles · i18n (PHP)
│   │   └── views/                   ← layout · list · new · edit · build · deploy (PHP)
│   ├── locales/                 ← (v1.9.0) i18n string packs (en canonical + ko; loaders = i18n.py / i18n.php)
│   │   └── en/ · ko/                ← admin.yaml · site.yaml · build.yaml · cli.yaml (Surface 2 / 1 / 3 + CLI)
│   │                                  (v1.9.7: --new-locale to scaffold · --check-locale to verify key parity)
│   └── tests/                   ← unit tests (514) + run_diagnostics.py (6 sections)
│
├── dist/                    ← build output (deploy target / do not edit by hand)
│
├── Heron.py                 ← build entry point (puts its own system/ on sys.path)
├── Pond.php                 ← local authoring entry point (thin router — § 17, not in dist)
├── README.md                ← this document (English)
└── README.ko.md             ← Korean guide

auto-generated on build/run (recommend .gitignore):
  build-report.md          ← progress transcript + summary + follow-ups + per-step timing (outside dist/)
  .build_cache/            ← per-article incremental cache + tokenizer parity cache
  user/.heron/update.json  ← (v1.6.0) update-check cache (the version stamp is committed; cache/backups are not)
  user/.heron/backups/     ← (v1.6.0) pre-migrate/update snapshots
  user/.heron/deploy.json  ← (v1.7.0) real deploy config (the deploy.example.json template is committed)
  system/runtime/bin/      ← (v1.7.0) downloaded rclone binary (<os>-<arch>/; excluded from the MANIFEST surface)
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
lang: en                     # override <html lang> for this article (else site.lang)

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
                             #   empty → follows site.yaml jsonld.enabled

styles:                      # § 4-6 — inline tweaks + external CSS, two channels
  # 1: style.css             #   integer key = external CSS file (inside the article folder)
  p:                         #   string key = inline rule
    text-indent: 0
    line-height: 1.7em
```

**slug rules** — lowercase letters/digits/hyphens only, starting and ending alphanumeric, globally unique, reserved words (`assets`/`search`) forbidden, independent of category.

`seo.description` is effectively required: if missing/empty the build passes but records a BuildReport issue. `noindex: true` articles are exempt (they never appear in a SERP or feed). No `<meta name="keywords">` is emitted (search engines ignore it).

`seo.jsonld` — the per-article JSON-LD toggle. If empty, it follows `site.yaml`'s `jsonld.enabled` (on by default). `false` suppresses `<script type="application/ld+json">` for this article only. Turning the site off cannot be re-enabled per article (the site toggle is master). See § 10.

**No `{{UPPERCASE}}` placeholders in metadata** — `title` · `seo.description` · `tags` · `seo.author` all flow through the builder's template substitution (`_render_template`) into `<meta>` · OG · Twitter · JSON-LD identically. Do not put a literal **space-free `{{NAME}}`** (name starting/composed of uppercase or underscore — regex `{{[A-Z_][A-Z0-9_]*}}`) in these four fields. If it matches a builder variable name (`{{COPYRIGHT_YEAR}}` · `{{PAGE_TITLE}}` · `{{MAIN_TITLE}}` · `{{NAV_LINKS}}` · `{{BODY}}`, …) that value silently leaks into the output; a non-variable uppercase token is stripped to empty + a build-report warning. Safe forms — lowercase `{{foo}}` · inner spaces `{{ FOO }}` · single braces `{NAME}` · leading digit `{{1A}}` · non-ASCII `{{변수}}` are all harmless. Other characters (`"` `\` `<` `>` `&` · newlines · CJK · emoji) are auto-escaped.

### 4-3. content.md (Markdown)

The parser is [system/scripts/parsedown.py](system/scripts/parsedown.py) (a Python port of Parsedown 1.7.4): close to standard CommonMark plus this system's own syntax (§ 9).

**Image paths** — relative to the article folder; rewritten to absolute at build:

```markdown
![photo](./imgs/photo.jpg)   →   <img src="/my-slug/imgs/photo.jpg" alt="photo">
![ext](https://example.com/i.jpg)   ← external URLs are not rewritten
```

**Section markers** — split the body into the `<div class='gap'><p>subtitle</p></div><section>…</section>` pattern:

- `===text===` (on its own line) — close the previous section + new gap (text) + open a new section.
- `======` (exactly six equals) — explicitly close the current section (body after it belongs to no section).
- `===` inside a code block is ignored. The body always starts with an automatic first gap (the article `title`) + first section. A missing close is auto-corrected by the builder.

### 4-4. content.html (HTML body)

Write only the body fragment (no `<html>/<head>/<body>`). For migrating existing HTML articles.

> **Write the gap + section yourself.** content.html goes in **verbatim** — the markdown auto-wrap and section markers do not apply. Example: [user/articles/About/content.html](user/articles/About/content.html).

> **`content.md` and `content.html` must not both exist** (build aborts).

**PHP function auto-conversion** — two functions are converted to HTML:

```html
<?php imgBox("./imgs/p.jpg", "caption", "alt") ?>
  → <div class="imgBox"><img src="/my-slug/imgs/p.jpg" alt="alt"><p class="caption">caption</p></div>

<?php imgSlideBox("./src_slide") ?>
  → images in src_slide/ as an alphabetized slideshow (bottom-center dot indicator, built by JS at runtime)
```

A multi-statement `<?php … imgBox(); imgBox(); … ?>` block is also simulated to static HTML as long as it contains only imgBox/imgSlideBox and no other live statement (comments, `global` declarations, and `;` are ignored). If another function call is mixed in, the block is kept verbatim and the article is emitted with a `.php` extension (§ 8 PHP auto-detection).

`{$name}` inside a caption is interpolated from `site.yaml`'s `php_globals` at build (§ 11). Captions preserve raw HTML (`<br>` · `&nbsp;` · `<a>` allowed); `alt`, being an attribute value, is escaped.

### 4-5. Attaching assets

- **Per-article assets** — placed inside the article folder. Everything except `meta.yaml`/`content.*` and `_`/`.`-prefixed entries is copied to `dist/{slug}/` (URL `/{slug}/imgs/…`). `_`/`.`-prefixed files/subfolders are treated as private and not copied (§ 6).
- **Site-wide assets** — shared CSS lives in `user/styles/`, identity assets (favicon/logo/default OG image) in `user/branding/`, and the runtime JS in `system/runtime/`. All three are gathered into `dist/assets/` and load as `/assets/{path}`.

### 4-6. styles — per-article CSS

Under the single `styles:` key in `meta.yaml`, **two channels** split automatically *by key type*:

| Channel | Key form | Value | Output | Intent |
|---|---|---|---|---|
| Inline rule | string (tag/selector) | dict | head `<style>` | small overrides of common properties |
| External CSS | integer (1, 2, 3…) | path inside the article folder | head `<link>` | your own CSS file (ascending integer order) |

**Load order:** `common_template.css` → external CSS (integer key order) → inline `<style>`. Inline has the last word.

```yaml
styles:
  1: layout.css                     # external CSS
  p: { text-indent: 0 }             # inline (auto-wrapped to section p)
  "section p > strong": { color: "#d33" }   # compound selectors are not wrapped
  "p:hover": { color: "#0172d5" }   # :, #, ', " need YAML quoting
```

- Tag keys (p, h3, ul, blockquote, a, code…) are auto-wrapped as `section TAG` selectors → override the same selector in `common_template.css` by source order.
- Keys containing whitespace, `>`, `+`, `~`, `,`, `.`, `[attr]` are used as-is.
- **Inline channel limit (intentional — promote to external CSS):** at-rules (`@media`/`@keyframes`/`@font-face`), CSS nesting, multi-line single property, inline comments next to a value.
- **`use_common_css: false`** cuts the shared CSS link entirely (for landing/single-service pages). Default `true`.
- **Specificity trap** — if `common_template.css` has a more specific rule (e.g. `body section p`), use a more specific selector or `!important`.

---

### 4-7. Example content (shipped in this repo)

`user/articles/` contains a small **runnable** demo site. It doubles as executable documentation — each example demonstrates a different feature, so a freshly cloned tree builds into a browsable site with just `python Heron.py`. When starting your own site, delete the folder wholesale (or keep it as a reference).

| Example article (folder) | URL | Feature demonstrated |
|---|---|---|
| `About` | `/about/` | `content.html` body · `imgBox()` PHP simulation · `{$site_credit}` interpolation from `php_globals` |
| `Blog/Welcome to Heron` | `/welcome-to-heron/` | basic markdown · section markers (`===t===` / `======`) · image box `![[alt]](path){caption}` · aligned tables · `og_image` |
| `Blog/Markdown Syntax Reference` | `/markdown-syntax/` | markdown round-up — ATX/Setext headings, reference links, nested lists, triple quotes, fenced code |
| `Blog/Per-Article Styling` | `/per-article-styling/` | the `styles` two channels: external CSS (integer key) + inline rules (string key), in load order |
| `Blog/Internationalization` | `/i18n/` | per-article `lang:` override + `updated:` revision date |
| `Blog/Tutorials/Working with Images` | `/working-with-images/` | **subcategory** · `imgBox()` + `imgSlideBox()` · raster → multi-resolution WebP `srcset` |
| `Gallery/*` (Sunset · Mountains · Ocean) | `/gallery-*/` | category `layout: gallery` (image tiles) |
| `Notes/Scratchpad` | `/scratchpad/` | `noindex: true` (excluded from sitemap/search/feed) + `seo.description` exemption |
| `Notes/Landing Page` | `/landing/` | `use_common_css: false` self-contained page |
| `Lab/Dynamic Year` | `/dynamic-year/` | a live `<?php … ?>` remains, so it emits `index.php` (reported as a "PHP-built article") |

The categories themselves (`Blog` · `Gallery` · `Notes` · `Lab`) demonstrate `nav_priority` · `priority` · `layout` · `preview_per_page`. A clean build of this set reports **0 to fix / 0 to review / 1 PHP build** (Dynamic Year, intended).

---

## 5. Categories

The folder structure under `user/articles/` *is* the category structure — no separate config. **Folder = category.** The builder distinguishes article folders from category folders by the presence of `content.md`/`content.html` (neither present → category).

**Folder name → slug:** non-ASCII → 4-digit hex codepoints, NFKD normalize, keep alphanumerics/spaces/hyphens, drop parentheses, collapse spaces/repeated hyphens to a single hyphen, lowercase.

```
Blog               → blog
3D Printing        → 3d-printing
Research Notes (CS) → research-notes-cs
블로그              → be94-b85c-adf8   (non-ASCII → hex, build warning; prefer ASCII folder names)
```

**Index pages** — every category (top and sub) gets its own index. A top-level category embeds child subcategories as sections + a direct-articles section. On a top-level category page, each child subcategory header links to that subcategory's page (`color: inherit; text-decoration: none`, no hover effect — a link that looks identical to body text). A category with no articles gets no index + a build warning.

**A category folder's meta.yaml** (all optional, different schema from articles — no `slug`/`date`):

| Field | Default | Meaning |
|---|---|---|
| `per_page` | site `category_per_page` (20) | articles per page on its own index |
| `preview_per_page` | site `category_preview_per_page` (5) | count when embedded as a section in a parent |
| `layout` | `list` | `list` / `gallery` (image tiles); anything else falls back to list |
| `styles` | {} | same two channels as articles |
| `use_common_css` | `true` | |
| `template` | `category.html` | `name.html`→`user/templates/`, `./name.html`→folder |
| `lang` | site `lang` | `<html lang>` override |
| `title` | folder name | index `<title>` body |
| `seo` | {} | same as article `seo:` (meta tags emitted) |
| `priority` | `0` | sibling section ordering in a parent index (higher first) |
| `nav_priority` | `0` | top-level nav ordering (separate axis from priority) |

**`layout: gallery`** — renders the article list as image tiles (CSS Grid `auto-fill, minmax(220px,1fr)`, 4:3 crop, subtle hover, 2 columns on mobile). Thumbnail: `seo.og_image` → `site.default_og_image` → empty placeholder. WebP srcset attached automatically.

To add a layout, register it directly in the `_listup_items_html`/`_render_section` branches of [system/scripts/builder.py](system/scripts/builder.py), the `section.listup-{layout}` rule in [user/styles/common_template.css](user/styles/common_template.css), and the pagination.js selector.

---

## 6. Managing articles — private / move / delete

- **Private** — prefix the file/folder name with `_` or `.`. Any path segment so prefixed hides everything below it from articles, categories, nav, and assets, and `dist/{slug}/` is removed on build. `_` = intentionally private / editing; `.` = OS/VCS hidden (`.git`, `.DS_Store`) **and** guards a folder you believe is hidden (e.g. `.draft`) from being accidentally published.
- **Move** — move an article folder to another category; the URL stays as long as `slug` is unchanged.
- **Delete** — delete the article folder and rebuild; `dist/{slug}/` is pruned (orphan cleanup).

To do these in a browser instead of a file explorer, see [§ 17 Pond.php](#17-local-authoring--pondphp). It follows the same conventions (move = folder rename with stable slug, hide = `_` prefix, delete = move to `.trash` so the build auto-excludes it and it stays recoverable).

---

## 7. Build

```bash
python Heron.py            # normal build (incremental cache)
python Heron.py --clean    # wipe dist/ + .build_cache/, then build
```

**Build report** — content defects do not abort the build; the affected article is *partially omitted* and the build completes. On exit, issues are grouped on stderr and persisted to `build-report.md`:

| Class | Meaning | Examples |
|---|---|---|
| **issue** (to fix) | a per-article problem the author must fix; that article is partially omitted | missing `seo.description` (exempt for noindex), slug regex/reserved/duplicate conflict, bad date format, non-list `tags`, **broken internal link** (v1.4.0 — an `<a href="/...">` with no corresponding file/dir index in dist) |
| **warning** (to review) | output is fine, worth a look | non-ASCII folder name hex conversion, missing asset, empty category, image optimization failure, AdSense `exclude_urls` matching 0 entries, `_`-prefixed asset reference (always warned since v1.4.0 — the old `warn_on_underscore_ref` toggle is retired) |
| **PHP-built articles** (v1.4.0) | *intended-output report*, not an issue/warning — at a glance, which articles fell back to `.php` (tracking the author/web-developer's explicit PHP use) | a body with live `<?php`/`<?=` beyond imgBox/imgSlideBox |

`build-report.md` also serializes a per-step timing table, so you can see at a glance which step costs time (the report lives outside `dist/`, so it is irrelevant to determinism).

**Build aborts (system faults only)** — only defects the content author cannot control abort immediately:

```
[ABORT] templates/article.html not found
Build aborted (system fault).
```

**The above cases (system faults):** template missing / no `user/articles/` directory / `site.yaml` missing or unparseable / `images.enabled: true` but Pillow absent — *only when raster images to convert actually exist* (with no raster at all, it warns and the build passes).

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
| Home | `/` | `https://your-domain.com/` |
| Article | `/{slug}/` | `/mask-intake-3d-printing/` |
| Category (top) | `/{cat}/` | `/blog/` |
| Category (sub) | `/{top}/{sub}/` | `/blog/tutorials/` |
| Article asset | `/{slug}/{path}` | `/mask-intake-3d-printing/imgs/p.jpg` |
| Site-wide asset | `/assets/{path}` | `/assets/common_template.css` |
| System | `/404.html` `/robots.txt` `/sitemap.xml` `/ads.txt` | |

- All article/category URLs end with `/`; a slashless URL gets a 301 from Apache.
- Article URLs are independent of category. Reserved slugs (`assets`/`search` — the `Builder.RESERVED_SLUGS` code constant since v1.4.0) are forbidden.
- **PHP auto-detection** — if `<?php`/`<?=` remains in the rendered result, the article is emitted as `index.php`. The URL stays `/{slug}/` and Apache `DirectoryIndex` handles it. Since v1.4.0 the BuildReport lists these explicitly under "PHP-built articles" — not a fault, but the author's (web developer's) intent (PHP 7.4+ assumed on the deploy server).

---

## 9. Markdown syntax

Close to standard CommonMark — headings (`#`–`######`, Setext), inline (`**bold**` `*italic*` `~~strike~~` `` `code` ``), links/images/reference links/autolinks, nested lists, nested quotes, tables with alignment (`:---`/`:---:`/`---:`), rules, block-level HTML passthrough. `<>&` inside a code block is auto-escaped (so `<?php` does not execute).

**This system's own syntax:**

```markdown
===Section title===          section marker (§ 4-3). ====== (six equals) explicitly closes
![[image alt]](./imgs/p.jpg) {caption}   → <div class="imgBox"><img …><p class="caption">caption</p></div>
```

Omit `{...}` if no caption. The image-box syntax is converted to raw HTML and handed to the parser just before the build runs.

---

## 10. SEO settings

Article, home, and category pages share one fallback chain (the single function [`build_meta_tags`](system/scripts/seo.py)). Body title: article = `meta.title`, home = `user/articles/meta.yaml title` > `site.name`, category = `meta.title` > folder name.

| Output tag | 1st | 2nd | 3rd |
|---|---|---|---|
| ◆ `<title>` | `{prefix}{title}{suffix}` | site default prefix/suffix | — |
| ● `meta description` | `seo.description` | — | omitted + issue (noindex exempt) |
| `meta author` | `seo.author` | `site.default_author` | omitted |
| ■ `link canonical` | `seo.canonical` | auto (article `/{slug}/`, home `/`, category `/{top}/{sub}/`) | — |
| ◆ `og:title` | `seo.og_title` | the `<title>` result | — |
| ● `og:description` | `seo.og_description` | the `meta description` result | omitted |
| ▲ `og:image` | `seo.og_image` | `site.default_og_image` | omitted |
| ◆ `og:image:alt` | `seo.og_image_alt` | page title | omitted |
| `og:type` | `seo.og_type` | article = `article`, home/category = `website` | — |
| ■ `og:url` / `og:site_name` | canonical / `site.name` | — | — |
| `article:published/modified_time` | article `date` / `updated` (else date) — articles only | — | — |
| `twitter:card` | `seo.twitter_card` | `summary_large_image` | — |
| ◆●▲ `twitter:title/description/image` | (same as og) / `seo.twitter_image`→og:image | — | omitted |

**Symbol groups** — the same symbol = a chain that converges on the same final value: ◆ = `<title>` value · ● = `meta description` value · ▲ = `og:image` value · ■ = `canonical` value.

**If a fallback resolves to an empty string, the tag itself is not emitted.** Only `seo.description` treats `''` as an author mistake and records a BuildReport entry (except `noindex: true` articles, which are exempt — being absent from SERP/feed makes the check moot).

**Indexing policy** — indexed by default. Only `noindex: true` articles get `<meta robots noindex>` in that page's `<head>`. Only `search.php` is separately blocked `noindex,follow`. A `noindex: true` article is also excluded from `sitemap.xml`, the `search.php` index, and (if within the feed window) the RSS/Atom feeds.

**Default og:image asset** — the asset `site.default_og_image` points to is emitted to `dist/` **as-is even if raster**, skipping WebP conversion / srcset registration (the `_copy_site_assets` exception). Its consumer is a social-link unfurler, not the `<img>` post-processor — it takes a single fixed URL from the `og:image` meta, so multi-resolution is meaningless, and KakaoTalk and some Facebook cannot render a WebP og:image. The default is `user/branding/default-og.png` (1200×630, standard OG spec). If `default_og_image` is an external URL or outside the asset source folders (`user/styles` · `user/branding` · `system/runtime`), this exception is a no-op (placing the file is the author's responsibility).

**JSON-LD structured data** — one `<script type="application/ld+json">` in the `<head>` of **article pages**, a `@graph` of two nodes:

- `Article` — `headline` (article title) / `datePublished` (date) / `dateModified` (updated > date) / `description` (`seo.description`, key omitted if absent) / `author` (`seo.author` > `site.default_author`, Person) / `publisher` (`site.name`, Organization) / `image` (same resolution as `og:image`) / `keywords` (`tags`) / `inLanguage` (article lang) / `url` · `mainEntityOfPage` (canonical).
- `BreadcrumbList` — a **single shared source** with the nav breadcrumb (same labels/paths, cannot diverge). Each ancestor category links to its own nested-index URL (`/{top}/…/{cat}/`). The last item (the current article) uses the article **title** (= `Article.headline`) as its name and, per schema.org's recommendation, omits `item`. If there are fewer than 2 crumbs (a top-level article), the node itself is omitted.

It **augments rather than replaces** the existing `<meta>`/OG/Twitter (the consumers differ — social unfurler = OG, SERP snippet = `meta description`, indexing control = `robots` meta, search-engine rich results = JSON-LD). `description`/`image`/`author` share the same fallbacks as `build_meta_tags`. **Off:** `site.yaml` → `jsonld.enabled: false` (global) or article `seo.jsonld: false`. Not emitted on home/category pages (only `article.html` carries `{{JSONLD}}`).

---

## 11. Site-wide settings — site.yaml

Only *truly global* (multi-page) settings live here. **A setting specific to one page type goes in that page's meta.yaml:**

| Location | Settings |
|---|---|
| `site.yaml` | domain · name · copyright · lang · default_og_image / `category_per_page` · `category_preview_per_page` / robots.txt / `description_truncate` / `images:` / `jsonld:` / `prev_next:` (v1.4.0) / `php_globals:` / `google_adsense:` |
| `user/articles/meta.yaml` | home only — `per_page` `excludes_categories` `lang` `layout` `styles` `title` `seo:` |
| `user/articles/<cat>/meta.yaml` | category only (§ 5 table) |
| `user/articles/<cat>/<article>/meta.yaml` | article only (§ 4-2) |

> **Retired in v1.4.0** — the five keys `reserved_slugs` · `warn_on_underscore_ref` · `warn_on_missing_asset` · `error_404_title` · `search_title` were promoted to code constants (`RESERVED_SLUGS` / `DEFAULT_ERROR_404_TITLE` / `DEFAULT_SEARCH_TITLE` in `system/scripts/builder.py`, plus a fixed always-warn behavior and dead-config cleanup). If the keys are left in an old `site.yaml`, the parser silently ignores them.

```yaml
domain: your-domain.com
base_url: https://your-domain.com
name: Heron Demo
main_title: Heron Demo
default_author: Your Name
default_og_image: /assets/default-og.png
lang: ko                              # default <html lang> for all pages
default_title_prefix: ""              # <title> prefix/suffix for all pages
default_title_suffix: ""
copyright_holder: Your Name
copyright_year_start: 2025
category_per_page: 20                 # category pagination default
category_preview_per_page: 5
description_truncate: 150             # feed summary cap, max chars (word-boundary aware)
robots_txt_main: |
  User-agent: *
  Allow: /

  Sitemap: https://your-domain.com/sitemap.xml
images:                               # automatic image optimization (defaults below if omitted)
  enabled: true                       #   false → build without Pillow
  widths: [400, 800, 1600]            #   WebP variant widths to generate
  max_width: 1600
  quality: 85
  lazy_loading: true                  #   works independently even if enabled=false
  default_sizes: "(max-width: 800px) 100vw, 800px"
jsonld:                               # schema.org JSON-LD (on if omitted)
  enabled: true                       #   false → no ld+json on any article
                                      #   (per-article: meta.yaml seo.jsonld: false)
prev_next:                            # v1.4.0: article-footer prev/next nav (on if omitted)
  enabled: true                       #   sibling pool = same-parent non-noindex articles,
                                      #   sorted date asc. No per-article off switch.
php_globals:                          # PHP signature variables (no interpolation if omitted)
  site_credit: "Illustrations by the Heron Demo team"
#   Signature variables the original PHP server filled at runtime via
#   PHP/GlobalVariables.php (auto_prepend). A static build has no such runtime,
#   so copying them here substitutes {$site_credit} etc. inside imgBox captions
#   at build (an undefined variable = empty string, like PHP's undefined echo).
#   Omit the leading $ in the variable name.
google_adsense:                       # Google AdSense (disabled by default)
  ads_txt: ""                         #   e.g. google.com, pub-0000000000000000, DIRECT, 0000000000000000
  head_script: ""                     #   e.g. <script async src="…adsbygoogle.js?client=ca-pub-0000…"></script>
  exclude_urls: []                    #   URLs to skip / [] = inject all 5 pages (when enabled)
#   ads_txt is written verbatim to dist/ads.txt (same pattern as robots.txt);
#   head_script is injected raw (no escaping) into the <head> of the 5 templates
#   (article · home · category · 404 · search.php). Both auto-disable when the
#   string/key is empty — consistent with SeoMeta's 3-state principle, with no
#   separate enabled master toggle. Pond.php · system/admin/ are naturally
#   excluded because the builder scans only user/articles/.
#   exclude_urls: a list of site-relative absolute URLs (starting with '/'). A
#   matched URL's page head does not receive the loader script = Google auto-ads
#   JS not loaded = ads blocked at the source. Matching is case-sensitive and
#   exact, trailing-slash included — canonical URL forms: home=/, article=/<slug>/,
#   category=/<slug_path>/, 404=/404.html, search=/search.php. An entry that
#   matches nothing (a typo or a deleted article) is auto-reported under
#   build-report.md "to review". Per-article blocking is possible too (e.g. /about/).
```

**user/articles/meta.yaml** (home only, optional — if absent, `per_page=10`, `excludes_categories=[]`):

```yaml
per_page: 5                  # posts per page in the main Recent list
excludes_categories: [About] # top-level categories to exclude from Recent (e.g. About)
layout: list                 # list / gallery
# lang: ko
# styles: { 1: home.css, p: { line-height: 1.7em } }
# use_common_css: true
# template: my_landing.html   # in user/templates/ or ./ (home folder)
```

> Shares the same schema as a category meta.yaml — on the home page `preview_per_page`/`priority` are ignored (there is nothing to embed; an intended asymmetry).

---

## 12. Internals — parser / search / feed

### Markdown parser — Parsedown 1.7.4 Python port

A single implementation [system/scripts/parsedown.py](system/scripts/parsedown.py).

```
content.md → preprocess (![[...]]{...} → HTML) → Parsedown().text()
           → finalize (rewrite asset paths, PHP simulation) → RenderResult(html)
```

- Source: [Parsedown](http://parsedown.org) 1.7.4 (c) Emanuil Rusev, MIT. The port is one-to-one with the original down to method names, dispatch, and dict keys. No external dependencies (stdlib `re`/`typing`).
- Byte-identical to PHP Parsedown across 79/79 fixtures (46 synthetic + 33 real articles).
- **Operating policy — fork.** This port is the single source of truth. It does not track new upstream releases; all fixes go directly into the port. The PHP comparison target (Parsedown.php) is not shipped in the tree. [system/tests/test_parsedown.py](system/tests/test_parsedown.py) is purely a regression guard for the Python port.
- PHP↔Python regex differences are handled inside the port (`\w` `re.ASCII`, a manual bracket matcher for `(?R)`, possessive → `+`/`*`, single quote `&#039;`).

### YAML parser — an intentional subset

The `site.yaml`/`meta.yaml` parser is self-implemented ([system/scripts/yaml_parser.py](system/scripts/yaml_parser.py)), covering only *the subset of syntax actually used*.

- **Supported:** flat key-value, nested mapping, block list (`- a`), inline list (`[a,b]` — multi-line `[\n  a,\n  b\n]` too), quoted strings, ints/bools/null, line-level `#` comments.
- **Unsupported (intentional):** anchors/aliases, folded scalar `>`, block-scalar chomping variants, flow mapping `{...}`, inline comments (a trailing `key: val # comment`), multi-document.
- **No plan to adopt PyYAML** — the subset is sufficient and avoids an external dependency. New syntax is added directly to this parser.

### Search — search.php

Zero client JS, zero external search engine. **Indexes only the 3 metadata fields (title / seo.description / tags)** (no body search — the first 1500 chars of body plain text are kept as `body_snippet` for snippets).

```
[build] tokenize every article (title/desc/tags) → BM25 index (v4) + serialize as a PHP static array
        → inline tokenizer + BM25 functions + the index into a single dist/search.php.
        noindex articles excluded (consistent with sitemap/feed).
[search] nav search box → /search.php?q=… → loaded from OPcache (index resident in memory)
        → 3-field BM25 weighted sum with the same tokenizer → phrase boost → snippet → render results.
```

- **UI** — only to the right of the nav on the home/category indexes. A category page auto-appends `?cat=<slug>` → scoped inside that top level (whitelist-validated; a bad cat falls back to the whole site). The result header shows the scope + a whole-site toggle. The result snippet is an 80-char window around match density with `<mark>` highlighting.
- **Tokenizer** — English/digits = lowercase word units (exact match); Korean = syllable 2-grams (natural partial search); **single-character Korean excluded**. [system/scripts/search.py](system/scripts/search.py) `search_tokenize()` ↔ [system/runtime/search_tokenize.php](system/runtime/search_tokenize.php) are a single source of truth, parity-verified against 18 fixtures every build (warns + skips if PHP absent). Cached in `.build_cache/parity.json` (key = `sha256(search.py + search_tokenize.php + php -v)`); `--no-cache` re-verifies fully every build.
- **Scoring** — per-field Okapi BM25 (`IDF·tf(k1+1)/(tf+k1(1-b+b·dl/avgdl))`, Robertson-Spärck Jones IDF). Weighted sum w_title=3.0 / w_desc=1.5 / w_tags=2.0. Phrase boost (multiplicative): title ×2.0, desc ×1.5, tags exact-match ×2.5. Parameters are baked into the index so scores are deterministic. `tests/test_bm25.py` + run_diagnostics verify Py↔PHP parity.
- **Security** — 100-char query cap, all output `htmlspecialchars`-escaped (highlight applied after escaping), result page `noindex,follow`.
- **Server** — PHP 7.4+ + `mbstring`. No extra extensions.
- **OPcache assumption (documented in v1.4.0)** — search is designed around a **single OPcache-resident PHP file**. The index is inlined as a static PHP array literal, so PHP parses it only on the first request and **OPcache keeps that bytecode resident in memory**, answering from the second request on with zero disk I/O / zero JSON parse / zero `require_once`. A 47-article index is processed in memory, so single-digit-ms responses are possible — the *feels-instant* search UX (vs. a static site) is a direct result of this structure. It is deliberately **not** moved to client JS — that would pile a multi-KB index download + JS parse/execute on the first load, badly slowing a user's first search response (and Cloudflare CDN caching is meaningless to the first visitor). PHP 7.4+ is added as an ops dependency, but in exchange it guarantees *an instant answer to every visitor*. If the host disables OPcache, response times drop to the 50–100ms range but are still faster and more accurate than client-JS (no index download).
- **Disable** — delete `system/runtime/search.php` (warns, then no search.php is generated) + remove `<form class='nav-search'>` from [user/templates/home.html](user/templates/home.html) and [user/templates/category.html](user/templates/category.html).

### RSS / Atom feeds

`dist/feed.atom` (Atom 1.0) + `dist/feed.rss` (RSS 2.0) share one entry list. The model is `FeedDocument`/`FeedEntry` in [system/scripts/feed.py](system/scripts/feed.py).

- **Includes:** non-noindex articles, minus `excludes_categories`, newest N (default 20, `DEFAULT_MAX_ENTRIES`), `updated` (else `date`) descending.
- **entry:** title = `meta.title`, link/id = absolute URL, published = `date`, updated = `updated`, summary/description = `seo.description` (absent → omitted + issue), author = `seo.author` > `site.default_author` (omitted in RSS), category = top-level folder name + `tags`.
- **Auto-discovery** — `<link rel='alternate' type='application/atom+xml'>` / `rss+xml` inserted in the page `<head>`.
- **Determinism** — `date`/`updated` are all `00:00:00 UTC`. The feed `updated`/`lastBuildDate` is the newest entry lastmod, not build time → unchanged content yields identical bytes every build.
- **Disable** — comment out `self._build_feeds()` in `build()` of [system/scripts/builder.py](system/scripts/builder.py) (no site.yaml toggle).

### Incremental cache

The per-article cache lives in `.build_cache/articles/`. An article hits if its inputs (meta.yaml + content.* + asset mtime/size + a global hash) are unchanged → output is replayed. Changing `site.yaml`, a template, builder code, or site-wide assets invalidates all articles (the global hash). Search/sitemap/feed/home/category/assets are rebuilt every build (all articles are their input; an intended scope).

### Image multiprocessing

Raster conversion fans out across `ProcessPoolExecutor(workers=min(cpu_count, len(jobs)))`; the worker is a module-level free function `_image_worker` (Windows-spawn safe). Result handling (`image_variants` registration, error BuildReport routing) is done by the main `_handle_image_result` helper. Serial fallback when raster_jobs < 4 or worker ≤ 1 (saving the Windows Pillow import cost).

---

## 13. Deployment

After the build, upload `dist/` to the server DocumentRoot and register an Apache VirtualHost **once**. Adding/removing articles afterward needs no server change. No `.htaccess` — if you cannot reach the main config on shared hosting, ask the host to register it.

```bash
rsync -avz --delete dist/ user@your-domain.com:/var/www/your-domain.com/
```

```apache
<VirtualHost *:443>
    ServerName your-domain.com
    ServerAlias www.your-domain.com
    DocumentRoot /var/www/your-domain.com         # ← deploy the contents of dist/

    SSLEngine on
    SSLCertificateFile    /etc/letsencrypt/live/your-domain.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/your-domain.com/privkey.pem

    <Directory /var/www/your-domain.com>
        AllowOverride None                      # ignore .htaccess
        DirectoryIndex index.html index.php
        DirectorySlash On                       # /slug → /slug/ auto-redirect
        Options -Indexes -MultiViews +FollowSymLinks
        Require all granted
    </Directory>

    AddType application/x-httpd-php .php
    ErrorDocument 404 /404.html
    AddDefaultCharset UTF-8
</VirtualHost>

<VirtualHost *:80>                              # HTTP → HTTPS (optional)
    ServerName your-domain.com
    ServerAlias www.your-domain.com
    RewriteEngine On
    RewriteRule ^.*$ https://your-domain.com%{REQUEST_URI} [L,R=301]
</VirtualHost>
```

- The **build machine** does not need PHP. If PHP CLI is present, it auto-verifies the tokenizer parity.
- The **deploy server** needs **PHP 7.4+ + mbstring** (search.php + `.php` output articles). This is an assumption, not a limit.
- ⚠️ **Never deploy `Pond.php` / `system/admin/`.** The `rsync` above uploads only `dist/`, so they never leave the build machine — Pond is a local-only single-user authoring tool. As extra defense `Pond.php` returns 403 unless served by PHP's built-in server (`cli-server`) on loopback ([§ 17](#17-local-authoring--pondphp)). And the DocumentRoot is `dist/` only, so the `.php` router is not even inside it.

**Deploy verification:**

```bash
curl -I https://your-domain.com/                # 200
curl -I https://your-domain.com/hello-world     # 301 → /hello-world/
curl -I https://your-domain.com/hello-world/    # 200
curl -I https://your-domain.com/sitemap.xml     # 200 application/xml
```

### 13-1. Pond one-click deploy (rclone, v1.7.0)

The `rsync` above is the manual path. From v1.7.0, **[Deploy] in Pond's top bar** does the same with a button — an **incremental sync** of `dist/` to the server via rclone's SFTP backend (only changed files transferred + server-only orphans deleted). It solves rsync's "not native on Windows" problem with **rclone** (MIT, a single static binary with zero DLLs): a pinned version (v1.74.2) is fetched once into `system/runtime/bin/<os>-<arch>/`, and the downloaded archive's SHA256 is checked against a source pin to block supply-chain tampering. The binary is machine-specific, so it never leaks into commits, the MANIFEST, or dist.

- **Config** — `user/.heron/deploy.json` (gitignored): `host`/`user`/`port`/`remote_path`/`ssh_key_path` (+ optional `known_hosts_path`). Copy `deploy.example.json` and fill it in. **The private key itself stays outside the repo** in an OS-standard location; deploy.json holds only the *path*.
- **Two-stage gate** — ① preview (`--dry-run`) lists what would be sent/deleted, then ② apply. Since `sync` *deletes* on the remote, this guards against a `remote_path` typo emptying the wrong directory.
- **Host-key verification** — connect once with `ssh user@host` to register the key in `known_hosts` (rclone's sftp backend skips verification by default, so we force it = MITM defense). The server needs **SFTP only** — nothing to install.
- **The first transfer is slow** — the first full sync of all assets (~157MB) can take minutes; Pond streams the progress log live. Subsequent deploys are incremental and fast.
- CLI: `python Heron.py --fetch-rclone` / `--deploy --dry-run` / `--deploy`. Details and safeguards in [§ 17-7](#17-7-deploy-rclone-v170).
- Non-goals: multiple targets (staging/prod), password auth, and zero-downtime atomic swap are out of scope this release (single target, key file, in-place). Deploying `Pond.php` / `system/` themselves is forbidden — only dist goes up.

---

## 14. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Build OK but CSS broken | Absolute paths (`/assets/...`). Use `cd dist && python -m http.server 8000`, not double-click. |
| Build without PHP? | Yes (parser is pure Python). Without PHP CLI only the parity check warns + skips. The deploy server needs PHP. |
| styles not applied | ① styles · external CSS are injected for articles/home/categories alike — write home styles in `user/articles/meta.yaml`, category styles in that category's `meta.yaml`. ② Does the template have `{{PAGE_STYLES}}`/`{{PAGE_STYLESHEETS}}`? ③ specificity conflict → more specific selector / `!important`. ④ `:hover`/`#id`/`::before` need YAML quoting. |
| `@media` in styles | The inline channel takes flat rules only. Put a real CSS file in the article folder + `styles: {1: my.css}`. |
| `slug conflict` | Two articles share a slug. Change one. |
| URL is `/be94-…/` | Non-ASCII folder name → auto hex conversion. Use an ASCII folder name (`블로그`→`Blog`). |
| Image missing | Inside the article folder? `./imgs/p.jpg` relative path? Check the `missing asset` warning and that `dist/{slug}/imgs/` copied. |
| `.php` not appearing, `.html` instead | An unprocessed `<?php` must remain for `.php`. imgBox/imgSlideBox convert to HTML, so they stay `.html`. |
| Rebuild dist/ fresh | `python Heron.py --clean`. |

---

## 15. Design principles and limits

**Design principles**

1. **Permanent URLs** — permanent regardless of category move / folder rename, as long as the slug is stable.
2. **Display name ↔ URL slug separation** — screen = (Korean) folder name, URL = ASCII slug.
3. **Explicit ops dependencies** — Python 3 + Pillow (build), PHP (runtime). Not "zero dependencies" but honestly stated + opt-out provided.
4. **Server ↔ content separation** — no `.htaccess`; growing the article count never changes server config.
5. **Build safety** — `user/articles/` is read-only; sources are never auto-modified.
6. **Single parser** — unified on one Parsedown Python port.
7. **Per-page presentation control** — declaratively, in meta.yaml.
8. **Per-article indexing** — allowed by default, only `noindex: true` articles excluded.
9. **Single-source tokenizer** — Py/PHP parity verified every build.
10. **Body ↔ metadata separation** — SEO/OG/feed copy comes only from author-written `seo:` values, never the body. The body is for readers, metadata for SERP/social — they should be different text. The SSG does not guess; absent `og_image`, it uses `site.default_og_image`, not a body extraction.
11. **`template:` cross-use — allowed but announced** — a page may pick a template of a different kind; placeholders the builder cannot fill are stripped + warned (neither auto-reject nor silent strip — announce + let the author decide).
12. **(v1.5.0) user / system separation** — `user/` is everything you own and edit; `system/` is the program. The presentation surface (templates, CSS, identity assets) lives in `user/`, not inside the builder.
13. **(v1.6.0) migration & self-update — build stays read-only** — upgrades replace only the program surface (`system/` + entry points) and never touch `user/`. A recorded schema stamp (`user/.heron/version`) drives an idempotent, `user/`-only migration chain. The build itself never writes to `user/` (principle 5 intact); `--migrate`/`--update` are the only writers, and they back up first.

**Current limits** — two kinds: ⓐ *intrinsic* limits of the current capabilities, ⓑ *intentionally deferred* extensions.

**ⓐ Intrinsic limits**

| Limit | Detail |
|---|---|
| Image optimization is single-frame | An animated GIF → first frame only as WebP. To preserve it, attach a webp directly / use an external URL. No per-article/per-image toggle (only global `images.enabled`). |
| Incremental caching covers article pages only | Search/sitemap/feed/home/category/assets are rebuilt every build (all articles are their input; an intended scope). |
| Internal-link validation = article pages only (v1.4.0) | The post-build step only scans `<a href>` in `dist/<slug>/index.{html,php}`. Home/category/404/search links are auto-generated, so a break is essentially impossible (article slugs are already validated in `_validate`). Assets (`<img src>`) are handled in the builder's own post-processing, so they are not separately validated. |
| admin preview = body fidelity | Same parser/extensions, so the *body* is byte-identical to the output, but full-page chrome — header/nav/footer, `<meta>`, JSON-LD — is not built (that is the template-fill step). For a full-page exact version, one-click build and check `dist/` — an intended division. Parity is gated by `test_render_one`. |
| admin is local single-user, no auth | Only a PHP built-in server (`cli-server`) + loopback guard (otherwise an immediate 403). Not for multi-user / concurrent editing / remote access. A raw `meta.yaml` form save cannot preserve inline comments via the subset parser — to keep custom comments, save through the raw box (raw is the source of truth). |

**ⓑ Intentionally deferred extensions**

| Candidate | Currently | Why deferred |
|---|---|---|
| Home/category JSON-LD | Article pages only (`article.html` only carries `{{JSONLD}}`). `seo.jsonld` is parsed in home/category `meta.yaml` too, but forward-compat (unused) | A home `WebSite`+`SearchAction` would pin the search URL contract into structured data (guess risk); a category `ItemList` is entangled with pagination, has a large enumeration-diff surface, and low rich-result value |
| Tag index pages `/tag/<slug>/` | `tags` is used only in feed `<category>`, BM25, and JSON-LD `keywords`. No browse page | It would grow the permanent-URL promise and promote `tags` to a first-class taxonomy axis → conflicts with the "category is the taxonomy axis" design (`tags` is intentionally excluded from `CategoryMeta`). The taxonomy axis must be defined before introducing it |
| Parallel article rendering | Sequential | 47 articles · ~3s build, and the dominant image conversion is already multi-process → low ROI. The cost to determinism / cache replay / report ordering is high. Revisit at hundreds of articles |

---

## 16. Changelog

> Paths like `scripts/…`, `templates/…`, `assets/…`, `tests/…` in the entries below are historical (the names at the time): v0.8.1–v1.4.x lived under `src/`, and since v1.5.0 the real locations split into `system/scripts`, `system/runtime`, `user/templates`, `user/styles`, `user/branding`, `system/tests` (§ 3). `build.py` → `Heron.py` and `admin.php` → `Pond.php` are also v1.5.0.
> Code integrity: a **docs-only release** = clean rebuild from canonical sources with dist sha256 == the previous code copy. A **code release** = determinism (two builds identical) + an enumerated diff against the previous code release.

| Version | Date | Summary |
|---|---|---|
| **v1.11.2** | 2026-06-04 | **rclone PATH-fallback integrity warning (security backlog B3 — closes the v1.11.x security arc)** — when the pinned-binary download fails and `rclone_bin.ensure()` falls back to an `rclone` found on `PATH`, that binary runs **without the sha256 verification** the downloaded copy gets (a sha256 *mismatch* on a download still hard-aborts with no fallback — unchanged). The fallback used to log a benign "using rclone from PATH" note; `cli.rclone.fallback_path` now states the binary is **UNVERIFIED / integrity not checked** and points to the remedy (restore network, or place a verified binary under `system/runtime/bin/<os>-<arch>/`). Message-only hardening (call site unchanged); new guard `test_fallback_warns_binary_is_unverified`. Defense-in-depth, single-author-local trust model (Low). No schema change → no new migration step (stamp 1.11.1 → 1.11.2); MANIFEST 88; 542 → 543 unit tests. |
| v1.11.1 | 2026-06-04 | Self-update supply-chain hardening (security backlog B1·B2) — `self_update` now hard-aborts when a downloaded release tree lacks `system/MANIFEST.json` (was: log a note + overlay anyway), and a new `_trusted_zipball()` pins the GitHub `zipball_url` to the `repos/lamaBread/heron-press/` origin (else falls back to the constructed `ZIPBALL`), wired into `check_update` + `self_update`. No schema change (stamp 1.11.0 → 1.11.1); MANIFEST 88; 536 → 542 unit tests. |
| v1.11.0 | 2026-06-04 | Security-audit round — confirmed findings from a parallel 4-domain multi-agent review: `search.py`'s `html_to_plain` gained `html.unescape` so public search snippets stop double-encoding escaped code (`&lt;`→`<`; guard `HtmlToPlainTests`); Pond's visibility toggle `ltrim($name,'_')`→`substr($name,1)` (strips one underscore, not all); `search_bm25.php`'s `highlight_html` got `?? $escaped` to guard a PCRE-null `TypeError`→500 (unreachable on default config); `admin_safe_rel` now rejects NUL bytes. By-design items (single-author trust model) + supply-chain defense-in-depth were split to a backlog. No schema change (stamp 1.10.0 → 1.11.0); MANIFEST 88; 532 → 536 unit tests. |
| v1.10.0 | 2026-06-04 | Deploy hotfix — `deploy.py`'s `build_argv` passed `--sftp-known-hosts`, a flag rclone **never had**, so every deploy (preview and apply) died at flag parsing; corrected to `--sftp-known-hosts-file` (verified against the pinned v1.74.2 binary). The unit tests had **asserted the same typo** and missed it → added a guard (`TestArgvFlagsAgainstRealRclone`) that checks every flag `build_argv` emits against the real rclone `help flags`. No schema change (stamp 1.9.7 → 1.10.0); MANIFEST 88; 531 → 532 unit tests. |
| v1.9.7 | 2026-06-03 | Default tool + site language flipped Korean→English + locale tooling (v1.9.x language-pack line) — the i18n canonical/default/fallback changed `ko`→`en` (`i18n.py` `CANONICAL`, `i18n.php` `I18N_CANONICAL`); an install that never chose a language now defaults to English with missing keys falling back to English, while one that already chose keeps it (change in **Pond ▸ Settings**). The visitor-site `lang` default also flipped `ko`→`en` (self-update never overwrites it, so fresh clones / the demo only). New `--check-locale` (parity / stray-backslash / untranslated diagnostic, non-zero exit on gaps = CI gate) and `--new-locale` (scaffold by copying the English canonical + injecting the endonym). No schema change (stamp 1.9.6 → 1.9.7); MANIFEST 88; 531 unit tests. |
| v1.9.6 | 2026-06-03 | Demo-config comments unified to English (language-pack line) — translated only the comments in `user/site.yaml` (the last user yaml with Korean comments) to English (config values, structure, key order, CRLF, and UTF-8 no-BOM unchanged); the locale packs are left untouched on purpose. No schema change (stamp 1.9.5 → 1.9.6); MANIFEST 86; 519 unit tests. |
| v1.9.5 | 2026-06-03 | Locale-pack translation right-sizing + low-level guards unified to English (language-pack line) — settled technical-term inconsistencies in the `ko` canonical pack are unified to English (cache `hit/miss` ↔ `히트/미스`, `raster` ↔ `래스터`; article-list Actions column `동작`→`작업`) + the mixed Korean/English line in the Pond 403 SAPI/loopback guard goes English (405/CSRF were already English). The `보완 필요`/`살펴볼 사항` issue/warning bodies are kept as writer-facing UX. No schema change (stamp 1.9.4 → 1.9.5); MANIFEST 86; 519 unit tests. |
| v1.9.4 | 2026-06-02 | Per-article content-defect `_issue`/`_warning` localization (language-pack line) — the Korean-hardcoded diagnostic bodies shown only when an article/category is defective (29 sites in builder) + the image-encoding-failure message move to `build.issue.*` (28 keys), `build.label.*` (2 keys), `build.warn.image_optimize_failed` (`{received!r}` preserves repr). No schema change (stamp 1.9.3 → 1.9.4); MANIFEST 86; 517 → 519 unit tests. |
| v1.9.3 | 2026-06-02 | argparse `--help` + remaining-abort localization (language-pack line) — `Heron.py --help`'s description, epilog, and option `help=` move to a new `cli.help.*` (`main()` loads `i18n.init_from_base` before `parse_args`), and the six `images.*` validation aborts + tokenizer-parity-failure/`php_unavailable` become `build.abort.*`/`build.parity.*` (`{received!r}` preserves repr). No schema change (stamp 1.9.2 → 1.9.3); MANIFEST 86; 514 → 517 unit tests. |
| v1.9.2 | 2026-06-02 | Build console + entire `build-report.md` localized (language-pack line) — 16-step progress, start/done/cache milestones, live counters, the `[search]` parity lines, and the report headings/summary/per-step table via `build.step.*` / `build.console.*` / `build.parity.*` / `build.report.*` (builder `tool_tr`; report/search use the global `i18n.t()`). A tool=`en` build panel is fully English; `ko` byte-identical (only the `[search]` line went English→Korean). No schema change (stamp 1.9.1 → 1.9.2); MANIFEST 86; 512 → 514 unit tests. |
| v1.9.1 | 2026-06-02 | Language-pack stabilization + operator-message localization. Unified the PHP/Python locale loaders on one byte-identical parser with escape handling (`\"` `\\` `\n` `\t` in double-quoted values; single-quoted = literal), fixing two v1.9.0 bugs (admin `class` attributes rendered with literal backslashes, a literal `\n` in the Pillow abort). A new `cli.yaml` brought the deploy/update/migration/CLI operator output into the pack via a global `i18n.t()`, so tool=`en` yields English panels (not Korean). No schema change (stamp 1.9.0 → 1.9.1); MANIFEST 84 → 86 files; 503 → 512 unit tests. |
| v1.9.0 | 2026-06-01 | Tool internationalization — language packs. The Korean-only tool became localizable via `system/locales/<locale>/*.yaml` flat-key packs across three surfaces (visitor site chrome / the Pond admin UI / build messages), with **two independent selectors**: the *site language* (`site.yaml: lang`) baked into `dist/` at build time (determinism preserved), and the new *tool language* read at runtime from `user/.heron/locale` (default `ko`, dropdown in **Settings**). `ko` is canonical + fallback (missing key → key string); an `en` pack ships; loaders are dependency-free (`i18n.py` / `i18n.php`). `m_1_9_0` seeds `user/.heron/locale=ko` (idempotent). `ko` values byte-identical to v1.8.0, so `lang=ko`/tool=`ko` output unchanged. Stamp 1.8.0 → 1.9.0; MANIFEST 74 → 84 files. |
| v1.8.0 | 2026-06-01 | Pond **Settings** (`?a=settings`) + system-overview **Home** (`?a=home`) — a structured `deploy.json` form + a raw `site.yaml` editor (saved only after passing the build's own validation via `Heron.py --check-config`, with a backup), and the **Pond admin** brand now links to a home that visualizes the full pipeline (the article list moved to nav `?a=list`) (§ 17-3 · § 17-8). No user/ schema change; stamp 1.7.2 → 1.8.0; dist byte-identical to v1.7.0 (57 files); 490 unit tests + 6/6 diagnostics. |
| v1.7.2 | 2026-06-01 | "Update available" banner won't clear after self-update — hotfix: `self_update` wrote `update_available=true` into the `update.json` cache at its start but never refreshed it after overlay/migration, so the banner persisted across restart; it now refreshes the cache to the new-version state right after a successful overlay (`update.py::self_update`), and `list.php` strips the doubled 'v' (`vv`) from the latest tag. No schema change; stamp 1.7.1 → 1.7.2. dist byte-identical to v1.7.0 (57 files). |
| v1.7.1 | 2026-06-01 | Self-update backup crash hotfix — the backup step copied the schema stamp (`user/.heron/version`) without creating the destination's parent directory, dying with `FileNotFoundError` (`update.py::_backup_program`); `test_full_flow` now writes a baseline stamp to cover that branch. No schema change; stamp 1.7.0 → 1.7.1. dist byte-identical to v1.7.0 (57 files). |
| v1.7.0 | 2026-06-01 | rclone one-click dist deploy (§ 13-1 · § 17-7) — **[Deploy]** in Pond **incrementally syncs** the built `dist/` to the server via rclone (SFTP) — only changed files sent + server orphans deleted, behind a **two-stage dry-run gate** guarding `sync`'s remote deletion. A pinned rclone (**v1.74.2**) is fetched on demand, archive SHA256-verified against platform source pins, and placed under `system/runtime/bin/<os>-<arch>/` (machine-specific → `make_manifest` excludes it from the program surface, paired with .gitignore → no leak into commits, MANIFEST, or dist); auth is an **SSH key file** (path only) with forced `known_hosts` verification. Config lives in the gitignored `user/.heron/deploy.json` (template `deploy.example.json` committed + seeded by an `m_1_7_0` migration). Builder unchanged → dist byte-identical to v1.6.2 (57 files); stamp 1.6.2 → 1.7.0; 464 → 490 unit tests + 6/6 diagnostics. |
| v1.6.2 | 2026-06-01 | Bilingual README parity — English brought to the Korean's depth (dropped the lighter-summary disclaimer, restored § 4-7 · § 18, expanded § 3·10·11·12·13·15·17); Korean side compressed the changelog and aligned the 13 design principles. Docs-only (no code change); stamp 1.6.1 → 1.6.2; dist byte-identical (57 files). |
| v1.6.1 | 2026-06-01 | Migration fidelity fixes (surfaced by replaying a real v1.2.2 `site.yaml`) — the migration now preserves LF/CRLF newlines exactly (reads/writes bytes) and snapshots every at-risk file before mutating. No schema change; stamp advanced 1.6.0 → 1.6.1. dist unchanged (57 files); 464 tests + 6/6 diagnostics. |
| v1.6.0 | 2026-05-31 | Migration & one-click update system (§ 17-6) — a schema-version stamp (`user/.heron/version`) + an idempotent `user/`-only migration engine + `MANIFEST.json` integrity + Pond/CLI one-click update from GitHub. Build stays read-only on `user/`; dist byte-identical to v1.5.3 (57 files). |
| v1.5.3 | 2026-05-30 | Demo-content layout fix — the three example `content.html` bodies were missing the manual `<div class='gap'>` + `<section>` wrappers HTML bodies must supply (§ 4-4), so they rendered unstyled; each is now wrapped to match a `.md` article. Engine unchanged; dist deterministic (57 files). |
| v1.5.2 | 2026-05-30 | Demo content + neutral defaults — `user/articles/` ships a runnable example set exercising every feature; site-identity placeholders genericized (`your-domain.com` / `Your Name`), AdSense disabled by default; neutral `default-og.png`; `.gitignore` scoped so `user/articles/` is tracked. |
| v1.5.1 | 2026-05-30 | v1.5.0 stabilization refactor (code release, dist byte-identical) — import hygiene, cross-module encapsulation (`images.split_url`/`build_srcset` public), DRY (`_seo_from_dict`/`_int_meta_field`), dead-code removal, stale-name fixes. dist 787 files sha256 == v1.5.0. |
| v1.5.0 | 2026-05-29 | Structure release — root split into `user/` (what you edit) and `system/` (the program); entry points renamed `Heron.py` / `Pond.php`. Pure source-layout change, so dist is byte-identical to v1.4.2. |
| v1.4.1 | 2026-05-28 | Fixed the v1.4.0 internal-link validation regex (`\bhref=` → `\s+href=`) — no more `data-href` mismatch. dist byte-invariant. |
| v1.4.0 | 2026-05-28 | Six-feature bundle — prev/next nav, article-end published/modified meta line, dark mode, internal-link validation, five site.yaml keys → code constants, BuildReport "PHP-built articles" category. |
| v1.3.0 | 2026-05-28 | Build-speed bundle — per-step timing, image multiprocessing, asset-pass unification, tokenizer parity cache. dist byte-invariant. |
| v1.2.2 | 2026-05-21 | `yaml_parser` multi-line inline list support (accumulate lines from `[` to `]`). dist unchanged. |
| v1.2.1 | 2026-05-21 | Ops-noise cleanup — `noindex: true` articles exempt from the `seo.description` check; `warn_on_stale_updated` warning dropped. dist byte-invariant. Tests 364→**367**; diagnostics 6/6 carried. |
| v1.2.0 | 2026-05-21 | v1.1.5 documentation stabilization. dist unchanged. |
| v1.1.5 | 2026-05-20 | AdSense URL-based ad blocking — `exclude_urls` (exact match, per-article possible); empty list = inject everywhere. Replaces v1.1.4's `exclude_pages`. |
| v1.1.4 | 2026-05-20 | AdSense page-type exclusion (`exclude_pages: [article/home/category/404/search]`). Unified into URL-based in v1.1.5. |
| v1.1.3 | 2026-05-20 | Google AdSense integration (`google_adsense.ads_txt` / `head_script`) + default `default-og.png` replaced with a standard 1200×630 OG image. |
| v1.1.2 | 2026-05-20 | imgSlideBox deploy-incident fix + paginated redesign — restored missing CSS `.slide{display:none}` + bottom-center dot indicator (built by runtime JS, static HTML unchanged). |
| v1.1.1 | 2026-05-20 | imgBox deploy-incident fix — multi-statement PHP blocks failed to simulate and leaked raw PHP. Rewrote the `simulate_php_in_html` block scanner + added `site.yaml php_globals` + caption raw preserved. Tests 313→**337**. |
| v1.1.0 | 2026-05-19 | Local authoring tool `admin.php` added (now Pond) — mirrors the `build.py` pattern: write/edit, move, hide, delete, preview, one-click build. dist byte-invariant (admin is upstream of the build). Tests 313→**317** ([§ 17](#17-local-authoring--pondphp)). |
| v1.0.2 | 2026-05-19 | Home default post count 5 → 10 (canonical `articles/meta.yaml` sets `per_page: 10`, so dist impact 0). |
| v1.0.1 | 2026-05-19 | Subcategory header links — arrow dropped; the subcategory name itself links to its own page (`color: inherit; text-decoration: none`). |
| v1.0.0 | 2026-05-19 | First stable release — default og:image asset pass-through (raster preserved), `articles/About` noindex. |
| v0.8.4 | 2026-05-19 | v0.8.3 documentation stabilization. dist byte-identical to v0.8.3. |
| v0.8.3 | 2026-05-18 | schema.org JSON-LD + correct breadcrumbs — `Article` + (≥ 2 crumbs) `BreadcrumbList` in the article `<head>`; augments existing meta; off switches (`jsonld.enabled` / `seo.jsonld`). Build-excluded prefixes `_`/`.` unified. Tests 266→313. |
| v0.8.2 | 2026-05-18 | Code soundness — `__version__` decoupled (feed `<generator>` version-free), stricter argparse, per-Builder build report. Tests 258→266. |
| v0.8.1 | 2026-05-17 | Folder cleanup — builder moved under `src/`. Behavior/output unchanged. |
| v0.8.0 | 2026-05-17 | README code-consistency fixes. No code/dist change. |
| v0.7.2 | 2026-05-17 | 16-step progress headers + live counter + persistent `build-report.md`. No output-logic change. |
| v0.7.1 | 2026-05-16 | Stabilization. No behavior change. |
| v0.7.0 | 2026-05-16 | Incremental build cache (per-article). Added `--no-cache` / `--clean-cache`. Tests 231→258. |
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

**Pond** is a **local-only, single-user** tool for writing/editing, moving categories, hiding/deleting, **live body preview**, and **one-click build** from a browser instead of a file explorer. It mirrors the `Heron.py` pattern — a thin entry point `Pond.php` at the version-folder root plus all logic in `system/admin/`. Because the builder scans only `user/articles/`, these **never leak into `dist/`** and are independent of build determinism (Pond is an authoring tool *upstream* of the build: it writes `user/articles/`, and `Heron.py` still only reads — design principle 5 intact).

### 17-1. Run

From the version folder:

```bash
php -S 127.0.0.1:8001 Pond.php
```

Browse to `http://127.0.0.1:8001/`. On the build machine, needs **PHP 7.4+** (8.x recommended for dev) + **Python 3** (preview/slug/build call the real `scripts.*`). Quit with `Ctrl+C` in the terminal.

### 17-2. Security — never put it on a public server

Local single-user only. Layered guards:

- **SAPI + loopback guard** — `Pond.php` returns **403** unless served by PHP's built-in server (`cli-server`) on `127.0.0.1`/`::1`. It does not open even under Apache `mod_php`/`php-fpm`.
- **Not deployed** — the § 13 `rsync` uploads only `dist/`. `Pond.php`/`system/admin/` never leave the build machine, and the DocumentRoot is `dist/` so the router is not even inside it.
- **CSRF** — state changes (save/create/move/delete/build) verify a session token. No auth (unnecessary for local single-user — noted as a limit in § 15 ⓐ).

### 17-3. Features

- **Home** (`/`, v1.8.0) — a system overview visualizing the full Heron+Pond flow (write → build → `dist/` → deploy → serve). The default landing reached by clicking the top-left **Pond admin** brand (with the installed-version badge). Shows article/category counts · `deploy.json`/`site.yaml` status + shortcuts to the main screens.
- **List** (`?a=list`) — the article tree. Each article: edit · move category (dropdown) · public/private toggle · delete. `.trash` contents shown too.
- **New** (`?a=new`) — pick a category + folder name (Korean OK) → `slug_one.py` suggests a slug with the **same** rules as the build (a non-ASCII name warns about hex). Creates the folder + `content.md` (or `.html`) + `meta.yaml` (with the canonical header comment).
- **Edit** (`?a=edit&id=…`) — **split view**: left = body (`content.md`/`.html`, no frontmatter — body↔meta separation principle), right = meta form + collapsible **raw `meta.yaml`** + live preview. The core fields (title · slug · date · updated · tags · `seo.description` · noindex) are *helpers* — editing them patches the raw YAML. **Saving is raw-`meta.yaml`-based** (comments/advanced keys/`styles` preserved); the server guarantees only the one header comment line. That is, raw is the source of truth.
- **Move/hide/delete** — folder rename (slug stays → **URL permanent**, design principle 1) / `_` prefix toggle / move to `user/articles/.trash/` (`.`-prefixed → auto-excluded from build, files remain so it is recoverable; there is intentionally no permanent-delete UI — recover by moving out of `.trash` in a file explorer).
- **One-click build** — the top button runs `python Heron.py` (`--clean` checkable) with the version folder as cwd and shows the output. This is the step that reflects changes onto the site (`dist/`).
- **Check / one-click update** (v1.6.0) — the header **Check for update** queries GitHub's latest tag, and if a new version exists the list banner's **Update now** downloads → verifies → overlays → migrates, then asks for a restart (§ 17-6).
- **Deploy** (v1.7.0) — **Deploy** in the header/nav incrementally syncs the built `dist/` to the server via rclone (SFTP). Two stages — ① preview (dry-run) lists what would be sent/deleted → ② apply — with the progress log streamed live (§ 17-7).
- **Settings** (v1.8.0) — **Settings** in the header/nav edits ① the deploy target (`deploy.json`) form + ② the site-wide config (`site.yaml`) as raw text on one screen. On save, `site.yaml` is only committed if it passes the same validation the build runs (§ 17-8).

### 17-4. Preview = body fidelity (single parser)

No separate markdown engine. `system/admin/render_one.py` reuses the very **`scripts.markdown` path** the builder uses to render an article body — `.md` via `resolve_section_markers(render_article_md(…))`, `.html` via `process_html(…)`, 1:1 with the builder's `_render_articles`. So the preview *body* is byte-identical to the output (same imgBox/imgSlideBox, same asset-path rewriting). The preview pane applies the site-wide CSS and proxies assets from the source folder. Full-page chrome (header/nav/footer, `<meta>`, JSON-LD) is not built — that is the template-fill step — so the **full-page exact version is verified by building to `dist/`** (an intended division). This parity is locked by `system/tests/test_render_one.py` via a byte comparison against the builder path (it breaks if anyone swaps in a different engine/path).

### 17-5. Constraints (same as § 15 ⓐ)

Body↔meta separation is enforced (the form does not mix frontmatter into the body). The subset YAML parser cannot preserve inline comments, so a form save loses custom comments beyond the header — to keep them, save through the raw box. Local single-user, no auth, not for concurrent editing. A Windows non-ASCII folder name depends on PHP 8.x's UTF-8 filesystem handling (verified on PHP 8.3) — the folder name is irrelevant to output (the slug is the URL), so it has no effect on the site output.

### 17-6. Updating & migration (v1.6.0)

The goal of v1.6.0 is that **a site can follow future upgrades comfortably**. It builds on the v1.5.0 `user/` ↔ `system/` split — on upgrade the **program surface** (`system/` + `Heron.py` + `Pond.php`) is replaced wholesale while `user/` is preserved, and a small **migration engine** adapts any schema change into `user/`.

**Schema-version stamp.** `user/.heron/version` records the schema version the `user/` tree conforms to — distinct from the program `__version__`. It lives under `user/` so it survives `system/` replacement and travels with your content, and its `.`-prefix auto-excludes it from the build (§ 6). A missing stamp is treated as the pre-1.6.0 baseline (so a fresh install is just stamped, and every migration step is idempotent).

**One-click update via Pond (the intended path — zero terminal lines).**

1. Header **Check for update** → queries GitHub for the latest tag (cached in `user/.heron/update.json`). If a new version exists, a banner appears atop the list.
2. **Update now** → downloads the latest release → verifies `MANIFEST.json` (sha256) integrity → backs up the program surface + stamp to `user/.heron/backups/` → overlays **only** the program surface (never touches `user/`) → runs the migration chain + bumps the stamp.
3. Pond asks you to **restart** it (`Ctrl+C` → `php -S 127.0.0.1:8001 Pond.php`) — the running PHP process still holds the old code in memory. This is the honest handling of a self-update, not faking a silent reload.

The logic lives in Python (`system/scripts/update.py` + `migrations/`, stdlib `urllib`+`zipfile` only) and Pond is a thin trigger, exactly like one-click build. The repo is pinned (`lamaBread/heron-press`).

**CLI escape hatch (power users / CI).** Direct `Heron.py` use is left to programmers; Pond covers the everyday path. The build itself stays **read-only** on `user/` (design principle 5) — only `--migrate`/`--update` write, and they back up first.

```bash
python Heron.py --check              # program/schema version + MANIFEST integrity
python Heron.py --migrate --dry-run  # preview the migration without applying
python Heron.py --migrate            # migrate user/ to the program version (backs up, then stamps)
python Heron.py --check-update       # query GitHub (refreshes Pond's banner cache)
python Heron.py --update             # download → verify → overlay → migrate
```

> **Caveat** — the update reaches GitHub over HTTPS. On some Windows Python installs the system certificate store may need to be set up for TLS verification (certificates are *not* disabled). If a check fails with a certificate error, fix the cert store rather than bypassing verification.

**Migration step authoring convention (future versions).** Each step is a `Migration` subclass in `system/scripts/migrations/m_<version>.py`, with `from_version`/`to_version`/`summary` and `plan(base)`/`apply(base)`. `apply()` must mutate **only `user/`** (the program code is replaced wholesale, so there is nothing to touch there) and must be **idempotent** (return `[]` on an already-migrated tree). `site.yaml` is handled by line-level text editing (`_yamledit`) to preserve comments, order, and `|` blocks (`yaml_parser` is read-only). The engine records the stamp centrally, so a step focuses only on content edits.

### 17-7. Deploy (rclone, v1.7.0)

Uploading the built `dist/` to the server is done with Pond's **[Deploy]** button ([§ 13-1](#13-1-pond-one-click-deploy-rclone-v170) for the overview). Same **thin-trigger** philosophy as build/update — PHP only spawns `python Heron.py --deploy [--dry-run]`; all download/verify/sync logic lives in Python (`system/scripts/deploy.py` + `rclone_bin.py`).

**Why rclone.** dist is a ~157MB static site, so a full transfer every time is wasteful → incremental is right. `scp -r` cannot delete orphans (old files left only on the server); `ssh + rm -rf` cleanup risks wiping the server on a path-variable mistake, so it is rejected. `rsync --delete` is close, but it is **not native on Windows and not bundled with Git for Windows**. Bundling rsync is encumbered (GPL redistribution). Hence **rclone (MIT, a single static binary with zero DLLs)**: free to bundle/redistribute + rsync-grade incremental + `--dry-run` + `sync` orphan deletion + **an SFTP backend that reuses your existing SSH/local key** (nothing to install server-side).

**Binary acquisition (`rclone_bin.ensure`).** If the pinned **v1.74.2** is already in `system/runtime/bin/<os>-<arch>/` and `rclone version` matches, it is used as-is (idempotent, zero network). Otherwise it downloads `https://downloads.rclone.org/<ver>/rclone-<ver>-<os>-<arch>.zip` and **checks the archive SHA256 against a source pin (6 platforms)** — a mismatch is discarded and aborted (supply-chain block). On success it extracts only `rclone(.exe)` and places it atomically (temp file → `os.replace`, `chmod +x` on POSIX). On a network failure/offline it falls back to rclone on PATH, and if there is none it errors clearly. The downloaded binary is machine-specific, so `.gitignore` + `make_manifest` exclude `system/runtime/bin/` from the program surface — it never leaks into commits, the MANIFEST, or dist.

**Two-stage safety gate.** `sync` *deletes* on the remote, so a `remote_path` typo could empty the wrong directory. Hence ① a **preview** (`--dry-run`) shows the would-send/delete list first → ② only a confirm button runs the real `sync`. The preview also connects and compares both sides, so it doubles as a **connectivity / host-key / key-permission pre-check**. Even when the first ~157MB transfer takes minutes, Pond reads the child's stdout line by line and **streams it live** (not a blocking batch dump).

**Config (`user/.heron/deploy.json` — gitignored).**

```json
{
  "host": "your-domain.com",
  "user": "deployuser",
  "port": 22,
  "remote_path": "/var/www/your-domain.com",
  "ssh_key_path": "C:/Users/you/.ssh/id_ed25519",
  "known_hosts_path": "C:/Users/you/.ssh/known_hosts"
}
```

Copy `deploy.example.json` and fill it in. `known_hosts_path` is optional (defaults to `~/.ssh/known_hosts`); `port` defaults to 22. **Never put the private key itself in deploy.json or the repo — only the path.** The `.`-prefix + gitignore keep it out of dist/commits and unshared per machine. The template is committed, but since the self-update overlay never touches `user/`, **the `m_1_7_0` migration seeds the template for existing users** (idempotent — no-op if already present).

**Security.** rclone's sftp backend skips host-key verification by default (MITM-vulnerable), so `--sftp-known-hosts-file` **forces** it — register the host once with `ssh user@host` (TOFU). Auth is the key file only (`--sftp-key-file`; no password / rclone.conf). An argv list + `bypass_shell` + Python `subprocess` (no shell) blocks injection, and Pond runs only under cli-server on loopback ([§ 17-2](#17-2-security--never-put-it-on-a-public-server)), so the key never leaves the machine and only dist bytes go over encrypted SSH. (A passphrase-protected key needs ssh-agent.)

```bash
python Heron.py --fetch-rclone        # pre-fetch the rclone binary (with verification). Idempotent.
python Heron.py --deploy --dry-run    # preview: send/delete list. Zero server change.
python Heron.py --deploy              # the real incremental sync (deletes included).
```

### 17-8. Settings — deploy target + site-wide config (v1.8.0)

**Settings** (`?a=settings`) in the header/nav edits both config layers on one screen. Same **thin-trigger** philosophy as build/deploy — Pond takes the form/raw text, validates and saves; meaning is interpreted by the Python builder.

**① Deploy (`user/.heron/deploy.json`) — structured form.** Flat JSON, so a form fits. When `deploy.json` is absent, the fields are prefilled from the template (`deploy.example.json`) to help the first write ([§ 17-7](#17-7-deploy-rclone-v170)). `host` · `user` · `port` · `remote_path` · `ssh_key_path` are required; `known_hosts_path` is optional (omitted → `~/.ssh/known_hosts`). The **private key itself is never stored — only its path**, and the key path's existence is *not* validated: it may be on another machine or not yet created, so blocking would be a footgun (if it is truly missing, rclone fails clearly at deploy time). The prior copy is backed up to `user/.heron/backups/settings/` before saving.

**② Site (`user/site.yaml`) — raw editor + build-identical validation.** `site.yaml` is richly-commented YAML, so a form re-dump would destroy the inline docs (the subset parser cannot round-trip). So you edit it **as raw text** (like `meta.yaml`), preserving comments and order, and on save it goes through **the same validation the build runs**, via a new `Heron.py --check-config` — it is only committed if it passes; on failure the on-disk `site.yaml` is left untouched, the builder's `[ABORT]`/warnings are shown, and your edits remain in the editor. The prior copy is backed up to `backups/settings/`. `--check-config` feeds the candidate over stdin through the build's own `Builder._apply_site_config`, so a "validated but build fails" gap is **structurally impossible** (the parity/Pillow side-effects are isolated into `_post_config_checks` and skipped by `--check-config`). Saving applies the same CRLF→LF normalization as article saves.

```bash
python Heron.py --check-config        # validate a site.yaml candidate on stdin exactly as the build does (Pond's save gate).
```

From v1.8.0 the top-left **Pond admin** brand links to a **system-overview home** (`?a=home`) — the default landing that visualizes the whole Heron+Pond flow ([§ 17-3](#17-3-features)). The article list is split out as **List** (`?a=list`) in the nav. From v1.9.0 this screen also has a **tool-language** dropdown ([§ 17-9](#17-9-tool-language--language-packs-v190)).

---

### 17-9. Tool language — language packs (v1.9.0)

Heron+Pond was designed in Korean, but its display strings are externalized into **locale packs** so the tool can run in other languages. The display language splits into two **independent** selectors:

- **Site language** — the visitor-facing chrome in `dist/` (search box, footer, pagination, 404, home/category labels). Set by the existing `site.yaml: lang` and **substituted at build time** (determinism preserved — output is byte-identical for the same `lang`; `search.php` gets its string table injected at build time, like the BM25 index). Since v1.9.7 the **default is English (`en`)** when `lang` is omitted (it was `ko`); the bundled demo `user/site.yaml` also ships `lang: en`. This is unrelated to multilingual *content* (article bodies) — it is the language of the UI chrome the tool generates.
- **Tool language** — the operator-facing Pond admin UI and build/CLI messages (warnings, aborts). Set by a new one-line `user/.heron/locale` (a BCP 47 code), chosen from a dropdown on the **Settings** (`?a=settings`) screen. Runtime lookup, independent of the build. Since v1.9.7 the **default is English (`en`)** when `user/.heron/locale` is absent (it was `ko`). An existing install that already selected a language keeps it (the 1.8.0→1.9.0 migration seeded `ko` for pre-1.9.0 upgraders and is unchanged, so they stay Korean).

**Pack format.** `system/locales/<locale>/*.yaml` — one `key: "value"` per line, flat dotted keys. The fragment files in a folder (`admin.yaml`, `site.yaml`, `build.yaml`, `cli.yaml`) are merged. Since v1.9.7 `en` is canonical and the fallback for every locale (it was `ko`), so a key missing from a pack falls back to its **English value** — a partially translated pack degrades to English, which is universally readable. `{name}` placeholders are substituted (e.g. `{n} results`). Inside a double-quoted value the parser interprets `\"` `\\` `\n` `\t` (any other `\x` keeps the backslash); single-quoted values are literal — so the PHP and Python loaders parse **byte-for-byte identically** (`system/admin/lib/i18n.php` / `system/scripts/i18n.py`, both dependency-free; a `test_i18n` parity test enforces it).

**The three surfaces.** (1) **visitor site chrome** — the *site language* (`site.yaml: lang`), baked into `dist/` at build; (2) the **Pond admin UI** — the *tool language*, via the PHP global `t()`; (3) **build/CLI operator messages** — the *tool language*, via the Python global `i18n.t()` (and the builder's `tool_tr`). Surface 3 covers the deploy/update/migration/CLI output, since v1.9.2 the builder's own **16-step progress, milestones, summary, and the whole `build-report.md`**, and since v1.9.3 the argparse `--help` (description, epilog, option `help=`) plus the `images.*` validation and tokenizer-parity-failure aborts, and since v1.9.4 the per-article `_issue`/`_warning` content-defect bodies and the image-encoding-failure message — so a tool=`en` install runs **every operator surface in English, always-on and conditional (content-defect) alike** (because the parser fixes its text at build time, `Heron.py main()` loads the tool language before parsing args). The only intentional holdouts are the low-level Pond security guards (403/405/CSRF) and some site-chrome values preserved by user decision — all in English, so they stay consistent regardless of the tool language (the 403 guard's mixed Korean/English line was unified to English in v1.9.5; the 403 runs before the i18n bootstrap, so `t()` is unavailable to it anyway).

**Adding a language.** v1.9.7 turns this into a tooled workflow via two CLI commands:

- `python Heron.py --new-locale <code>` — **scaffolds** a new pack at `system/locales/<code>/`. It copies the English canonical `*.yaml` verbatim (so it parses and passes key parity immediately — displaying English until translated) and injects the endonym key `admin.locale.name.<code>` into every pack (so it shows up in the **Settings** dropdown right away). The code is validated (`^[A-Za-z][A-Za-z0-9-]*$`) to block path traversal.
- After translating the values, **verify** with `python Heron.py --check-locale <code>`. This read-only diagnostic checks against the English canonical and reports **missing** keys (which fall back to English), **extra** (dead/typo) keys, **stray-backslash** values (unresolved escapes), and an informational count of **untranslated** keys (value still identical to English). The exit code is non-zero if any missing/extra/stray-backslash exist, so it works as a CI / pre-commit gate. With no code it checks every bundled locale except the English canonical.

**Key parity is strict** — a bundled pack must have the **exact same key set** as the English canonical, enforced by `system/tests/test_i18n.py`. Missing keys fall back to English.

---

## 18. Further update proposals

Candidates that were discussed during the v1.4.0 review but *not* implemented in that release. A starting point for later decisions, not a promise. (Items the user has explicitly deferred — home/category JSON-LD, tag indexes, parallel article rendering — are not kept here; see the [§ 15](#15-design-principles-and-limits) ⓑ table.)

### 18-1. Automatic table of contents (TOC) — auto for long articles only, or `meta.yaml toc: true`

**What** — auto-generate a side (desktop) / inline (mobile) TOC from the body headings (h2/h3). Threshold = body word count ≥ 1500 AND h2 ≥ 3 turns it on automatically; `toc: false` forces OFF / `toc: true` forces ON. The toggle is 3-state for the same reason as noindex — a *default-auto, explicit-override* pattern.

**Why deferred** — most canonical articles are short with few headings, so the immediate benefit is small. Introducing it touches ① the Parsedown port for heading anchors (currently `<h2>Title</h2>` → `<h2 id="title">Title</h2>`), ② a `<nav class="toc">` build in post-processing, ③ CSS for two layouts (side vs inline), ④ the threshold algorithm + the 3-state toggle — not a small feature but a release-sized bundle. Priority rises if *research-note / paper-review* style articles grow.

**Files to touch** — `system/scripts/parsedown.py` (heading IDs), `system/scripts/markdown.py` (TOC extract + render), `system/scripts/models.py` (`ArticleMeta.toc: Optional[bool]`), `user/styles/common_template.css` (`.toc` two layouts), `README.md` (§ 4-2 meta table + § 9 markdown section). One new unit-test set.

### 18-2. `description_truncate` usage note + code-constant promotion candidate

**Where it is used today** — `site.yaml`'s `description_truncate: 150` is used in *exactly one place* — **the summary-text cap (max chars) for the feed (Atom `<summary>` / RSS `<description>`)**. If the `seo.description` body exceeds this length it is truncated *respecting English word boundaries* with a trailing `…` (implemented in `truncate_description` in `system/scripts/seo.py`, called from two places in `system/scripts/builder.py`'s `_render_articles` as `summary = truncate_description(desc_val, self.site.description_truncate)`).

| Channel | `description_truncate` applied? |
|---|---|
| `<meta name="description">` (article head) | **❌ no** — full `seo.description` body verbatim. |
| `<meta property="og:description">` · `<meta name="twitter:description">` | **❌ no** — body verbatim. |
| schema.org JSON-LD `Article.description` | **❌ no** — body verbatim. |
| gallery tile / home / category listing summary | **❌ not shown** (current design). |
| **feed `<summary>` (Atom) / `<description>` (RSS)** | **✅ yes** — capped by `description_truncate`. |

So it serves one purpose: *a one-line summary cap for the small screens of feed readers*. The search-engine SERP snippet (`<meta description>`) is unrelated (the engine truncates with its own logic).

**Why code-constant promotion was deferred** — the user *might* find it worth tuning between 70–200 to fit a given feed reader's display width (e.g. the narrow card of a mobile reader). If it has never been changed, promoting it to a code constant is the right answer; once a year of operation confirms it was never touched, move it then (the same bar as the five F·G·I keys).

**Alternative — author writes short directly** — keeping the feed summary short means `description_truncate` never fires (an operating policy). In that case the key goes dormant and becomes a natural retirement candidate.

### 18-3. Future decision storage

At the time of writing there may be more candidates that *were discussed but dropped from the v1.4.0 decisions* beyond the two above. Items to add accumulate in this section in the same format (what · why deferred · files to touch). When un-deferring a candidate, re-review it alongside the reason recorded here — has the reason changed, or does the same reason still hold.

---

*Heron v1.11.2 — build with Python + Pillow, runtime PHP (OPcache recommended). Full release history in [§ 16](#16-changelog).*

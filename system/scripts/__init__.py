"""Heron — internal builder modules.

The root ``Heron.py`` puts its own ``system/`` on ``sys.path`` and imports
this package (located at ``system/scripts/``). Modules:

  yaml_parser  — minimal stdlib-only YAML subset
  models       — dataclasses (SiteConfig, ArticleMeta, SeoMeta, ...)
  slugs        — category / folder name -> slug
  markdown     — body post-processing, PHP-function simulation, per-article styles
  parsedown    — Python port of Parsedown 1.7.4
  seo          — <meta> tag + JSON-LD builder
  images       — automatic image optimization (WebP + srcset + lazy loading)
  search       — tokenizer, BM25 index, PHP static-array serialization
  sitemap      — sitemap.xml generation
  feed         — RSS / Atom feeds
  report       — BuildReport / issue / warning / abort
  cache        — per-article incremental build cache
  builder      — build pipeline (Builder class)

``__version__`` is the single source of truth for the site version string. It
never reaches dist output; its only consumers (cache global_hash, the build
console, and build-report.md) all live outside dist.
"""

__version__ = '1.11.4'

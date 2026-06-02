The site default language is English (`lang: en` in `site.yaml`), but this
article sets `lang: ko` in its `meta.yaml`. Open the page source and the
`<html lang>` attribute reads `ko` for this page only.

===Why per-article language matters===

The `lang` attribute helps screen readers pick the right pronunciation and
helps search engines serve the right audience. Heron lets you set it globally
and override it per article (and per category).

===Publish date vs. updated date===

This article also carries an `updated:` date that is later than its `date:`.
Heron keeps the two distinct: the publish date orders the article in feeds and
prev/next navigation, while the updated date is what feeds report as the
entry's last-modified time. The article-end meta line shows both.

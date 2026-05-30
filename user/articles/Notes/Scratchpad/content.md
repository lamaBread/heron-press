This article sets `noindex: true`. As a result it is:

- marked `<meta name="robots" content="noindex">`,
- left out of `sitemap.xml`,
- left out of the `search.php` index,
- and left out of the RSS/Atom feeds.

It also has **no** `seo.description`. For a normal article that would be
recorded as a build issue, but `noindex` articles are exempt — so the build
stays clean. Use this for drafts and scratch notes you want reachable by URL
but invisible to crawlers and search.

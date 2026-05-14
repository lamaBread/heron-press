"""scripts/sitemap.build_sitemap 단위 테스트 (v0.6.0).

홈 + 카테고리 + 글 URL / noindex 제외 / excludes_categories / lastmod 결정 규칙.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.sitemap import build_sitemap  # noqa: E402
from scripts.models import (  # noqa: E402
    SiteConfig, ArticleMeta, CategoryMeta, SeoMeta, Article, Category,
)


def _site():
    return SiteConfig(
        domain='example.com',
        base_url='https://example.com',
        name='Ex', main_title='Ex',
        default_author='A', default_og_image='/og.png',
        default_title_prefix='', default_title_suffix='',
        copyright_holder='A', copyright_year_start=2020,
        reserved_slugs=[],
        warn_on_underscore_ref=False, warn_on_missing_asset=False,
        warn_on_stale_updated=False, description_truncate=160,
        robots_txt_main='', robots_txt_legacy='',
    )


def _article(slug, date, updated=None, noindex=False, category_path=None):
    return Article(
        meta=ArticleMeta(slug=slug, title=slug, date=date, updated=updated,
                         noindex=noindex, seo=SeoMeta()),
        source_dir=Path('.'),
        content_file=Path('./content.md'),
        category_path=category_path or [],
    )


def _category(folder_name, slug, slug_path):
    cat = Category(
        folder_name=folder_name,
        slug=slug,
        path=[folder_name],
        slug_path=slug_path,
    )
    cat.meta = CategoryMeta()
    return cat


class SitemapTests(unittest.TestCase):

    def test_home_url_first(self):
        articles = [_article('hello', '2026-01-01', category_path=['Blog'])]
        cats = {('blog',): _category('Blog', 'blog', ['blog'])}
        cats[('blog',)].articles = articles
        sm = build_sitemap(articles, cats, _site(), CategoryMeta())
        # 첫 <loc> 가 홈
        first_loc = sm.split('<loc>')[1].split('</loc>')[0]
        self.assertEqual(first_loc, 'https://example.com/')

    def test_noindex_excluded(self):
        articles = [
            _article('public', '2026-01-01', category_path=['Blog']),
            _article('hidden', '2026-01-01', noindex=True,
                     category_path=['Blog']),
        ]
        cats = {('blog',): _category('Blog', 'blog', ['blog'])}
        cats[('blog',)].articles = articles
        sm = build_sitemap(articles, cats, _site(), CategoryMeta())
        self.assertIn('/public/', sm)
        self.assertNotIn('/hidden/', sm)

    def test_excludes_categories_applies_to_home_lastmod(self):
        # excludes_categories 에 들어 있는 카테고리의 글은 홈 lastmod 계산
        # 에서 제외된다. (URL 자체는 sitemap 에 여전히 포함.)
        articles = [
            _article('on-home', '2026-01-01', category_path=['Blog']),
            _article('off-home', '2026-12-31', category_path=['About']),
        ]
        blog = _category('Blog', 'blog', ['blog'])
        blog.articles = [articles[0]]
        about = _category('About', 'about', ['about'])
        about.articles = [articles[1]]
        cats = {('blog',): blog, ('about',): about}
        home_meta = CategoryMeta(excludes_categories=['About'])
        sm = build_sitemap(articles, cats, _site(), home_meta)
        # 홈 entry 의 lastmod 는 2026-01-01 (about 제외) 이어야.
        # 첫 url 블록을 잡아 lastmod 검사.
        first_block = sm.split('</url>')[0]
        self.assertIn('<lastmod>2026-01-01</lastmod>', first_block)

    def test_article_lastmod_prefers_updated(self):
        articles = [_article('a', '2026-01-01', updated='2026-06-15',
                             category_path=['Blog'])]
        cats = {('blog',): _category('Blog', 'blog', ['blog'])}
        cats[('blog',)].articles = articles
        sm = build_sitemap(articles, cats, _site(), CategoryMeta())
        self.assertIn('<lastmod>2026-06-15</lastmod>', sm)

    def test_no_changefreq_or_priority(self):
        articles = [_article('a', '2026-01-01', category_path=['Blog'])]
        cats = {('blog',): _category('Blog', 'blog', ['blog'])}
        cats[('blog',)].articles = articles
        sm = build_sitemap(articles, cats, _site(), CategoryMeta())
        self.assertNotIn('<changefreq>', sm)
        self.assertNotIn('<priority>', sm)

    def test_empty_subtree_skips_category(self):
        # 모든 글이 noindex 인 카테고리는 sitemap 에 등장 안 함.
        articles = [_article('h', '2026-01-01', noindex=True,
                             category_path=['Blog'])]
        cats = {('blog',): _category('Blog', 'blog', ['blog'])}
        cats[('blog',)].articles = articles
        sm = build_sitemap(articles, cats, _site(), CategoryMeta())
        # Blog 카테고리 URL 미출현 — 글 URL 도 noindex 라 미출현
        self.assertNotIn('/blog/', sm)


if __name__ == '__main__':
    unittest.main()

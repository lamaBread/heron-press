"""scripts/feed 단위 테스트 (v0.6.0).

Atom 1.0 / RSS 2.0 직렬화, 날짜 변환 (ISO 8601 / RFC 822), 빌더 헬퍼
(build_feed_document) 의 noindex / excludes_categories / max_entries 처리.
"""
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.feed import (  # noqa: E402
    FeedEntry, FeedDocument, render_atom, render_rss,
    build_feed_document, _to_iso_z, _to_rfc822,
)
from scripts.models import (  # noqa: E402
    SiteConfig, ArticleMeta, SeoMeta, CategoryMeta, Article,
)


def _site():
    return SiteConfig(
        domain='example.com',
        base_url='https://example.com',
        name='Example Site', main_title='Example Site',
        default_author='Author', default_og_image='/og.png',
        default_title_prefix='', default_title_suffix='',
        copyright_holder='Author', copyright_year_start=2020,
        reserved_slugs=[],
        warn_on_underscore_ref=False, warn_on_missing_asset=False,
        warn_on_stale_updated=False, description_truncate=160,
        robots_txt_main='', robots_txt_legacy='',
    )


def _article(slug, date='2026-01-01', updated=None, noindex=False,
             tags=None, category_path=None):
    return Article(
        meta=ArticleMeta(slug=slug, title=slug.title(), date=date,
                         updated=updated, noindex=noindex,
                         tags=tags or [], seo=SeoMeta()),
        source_dir=Path('.'),
        content_file=Path('./content.md'),
        category_path=category_path or [],
    )


class DateConvertTests(unittest.TestCase):

    def test_iso_z_format(self):
        self.assertEqual(_to_iso_z('2026-05-14'), '2026-05-14T00:00:00Z')

    def test_rfc822_format(self):
        # 2026-05-14 = Thursday
        self.assertEqual(_to_rfc822('2026-05-14'),
                         'Thu, 14 May 2026 00:00:00 +0000')


class RenderAtomTests(unittest.TestCase):

    def _doc(self):
        return FeedDocument(
            title='Site', subtitle='Sub',
            home_link='https://x.com/', atom_self='https://x.com/feed.atom',
            rss_self='https://x.com/feed.rss', doc_id='https://x.com/',
            updated='2026-05-14', language='ko',
            default_author='Author', generator='gen',
            entries=[
                FeedEntry(
                    title='Hello', link='https://x.com/hello/',
                    entry_id='https://x.com/hello/',
                    published='2026-01-01', updated='2026-01-01',
                    summary='intro', author='Author', categories=['Blog'],
                ),
            ],
        )

    def test_parses_as_xml(self):
        out = render_atom(self._doc())
        root = ET.fromstring(out)
        self.assertTrue(root.tag.endswith('}feed'))

    def test_entry_has_title_and_summary(self):
        out = render_atom(self._doc())
        self.assertIn('<title>Hello</title>', out)
        self.assertIn('<summary>intro</summary>', out)

    def test_no_summary_when_empty(self):
        doc = self._doc()
        doc.entries[0].summary = ''
        out = render_atom(doc)
        self.assertNotIn('<summary', out)


class RenderRssTests(unittest.TestCase):

    def _doc(self):
        return FeedDocument(
            title='Site', subtitle='Sub',
            home_link='https://x.com/', atom_self='https://x.com/feed.atom',
            rss_self='https://x.com/feed.rss', doc_id='https://x.com/',
            updated='2026-05-14', language='ko',
            default_author='Author', generator='gen',
            entries=[FeedEntry(
                title='Hello', link='https://x.com/hello/',
                entry_id='https://x.com/hello/',
                published='2026-01-01', updated='2026-01-01',
                summary='intro', categories=['Blog', 'tutorial'],
            )],
        )

    def test_parses_as_xml(self):
        out = render_rss(self._doc())
        ET.fromstring(out)  # 파싱만 성공하면 OK

    def test_categories_each_emit(self):
        out = render_rss(self._doc())
        self.assertIn('<category>Blog</category>', out)
        self.assertIn('<category>tutorial</category>', out)

    def test_description_omitted_when_summary_empty(self):
        doc = self._doc()
        doc.entries[0].summary = ''
        out = render_rss(doc)
        # channel-level description 은 항상 있으나, item-level 은 누락
        self.assertEqual(out.count('<description>'), 1)


class BuildFeedDocumentTests(unittest.TestCase):

    def test_noindex_excluded(self):
        articles = [
            _article('public', category_path=['Blog']),
            _article('hidden', noindex=True, category_path=['Blog']),
        ]
        meta_cache = {
            'public': {'summary': 's', 'thumb': None},
            'hidden': {'summary': 'h', 'thumb': None},
        }
        doc = build_feed_document(
            articles, _site(), CategoryMeta(), meta_cache,
            category_path_for_article=lambda a: a.category_path[0]
                if a.category_path else None,
            generator='gen',
        )
        self.assertIsNotNone(doc)
        slugs = [e.link.rstrip('/').split('/')[-1] for e in doc.entries]
        self.assertIn('public', slugs)
        self.assertNotIn('hidden', slugs)

    def test_excludes_categories_excluded(self):
        articles = [
            _article('keep', category_path=['Blog']),
            _article('skip', category_path=['About']),
        ]
        meta_cache = {
            'keep': {'summary': '', 'thumb': None},
            'skip': {'summary': '', 'thumb': None},
        }
        home_meta = CategoryMeta(excludes_categories=['About'])
        doc = build_feed_document(
            articles, _site(), home_meta, meta_cache,
            category_path_for_article=lambda a: a.category_path[0]
                if a.category_path else None,
            generator='gen',
        )
        slugs = [e.link.rstrip('/').split('/')[-1] for e in doc.entries]
        self.assertIn('keep', slugs)
        self.assertNotIn('skip', slugs)

    def test_empty_returns_none(self):
        # 모든 글이 제외되면 None 반환 (호출자가 빈 파일 작성 skip).
        articles = [_article('hidden', noindex=True, category_path=['Blog'])]
        meta_cache = {'hidden': {'summary': '', 'thumb': None}}
        doc = build_feed_document(
            articles, _site(), CategoryMeta(), meta_cache,
            category_path_for_article=lambda a: 'Blog',
            generator='gen',
        )
        self.assertIsNone(doc)

    def test_categories_merge_folder_and_tags(self):
        article = _article('p', category_path=['Blog'], tags=['py', 'web'])
        meta_cache = {'p': {'summary': '', 'thumb': None}}
        doc = build_feed_document(
            [article], _site(), CategoryMeta(), meta_cache,
            category_path_for_article=lambda a: a.category_path[0],
            generator='gen',
        )
        cats = doc.entries[0].categories
        self.assertIn('Blog', cats)
        self.assertIn('py', cats)
        self.assertIn('web', cats)

    def test_feed_updated_is_latest_entry_lastmod(self):
        # 빌드 시각이 산출물에 새지 않아야 함.
        articles = [
            _article('a', date='2026-01-01', category_path=['Blog']),
            _article('b', date='2026-05-15', category_path=['Blog']),
        ]
        meta_cache = {
            'a': {'summary': '', 'thumb': None},
            'b': {'summary': '', 'thumb': None},
        }
        doc = build_feed_document(
            articles, _site(), CategoryMeta(), meta_cache,
            category_path_for_article=lambda a: 'Blog',
            generator='gen',
        )
        self.assertEqual(doc.updated, '2026-05-15')


if __name__ == '__main__':
    unittest.main()

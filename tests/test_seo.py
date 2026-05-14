"""seo.truncate_description / build_meta_tags 단위 테스트 (v0.6.0).

v0.5.4 의 단어 경계 truncate (영문 단어 중간에 자르지 않기, CJK 글자 단위
자유 절단) + v0.5.5 의 본문 폴백 제거 (본문 ↔ 메타데이터 분리 원칙).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.seo import truncate_description, build_meta_tags  # noqa: E402
from scripts.models import (  # noqa: E402
    SiteConfig, ArticleMeta, SeoMeta, RenderResult, Article,
)


def _site(**overrides):
    defaults = dict(
        domain='example.com',
        base_url='https://example.com',
        name='Example',
        main_title='Example',
        default_author='Author',
        default_og_image='/og.png',
        default_title_prefix='',
        default_title_suffix=' | Example',
        copyright_holder='Author',
        copyright_year_start=2020,
        reserved_slugs=[],
        warn_on_underscore_ref=True,
        warn_on_missing_asset=True,
        warn_on_stale_updated=True,
        description_truncate=160,
        robots_txt_main='',
        robots_txt_legacy='',
    )
    defaults.update(overrides)
    return SiteConfig(**defaults)


def _article(seo=None, title='T', date='2026-01-01', slug='s', updated=None):
    return Article(
        meta=ArticleMeta(slug=slug, title=title, date=date,
                         updated=updated, seo=seo or SeoMeta()),
        source_dir=Path('.'),
        content_file=Path('./content.md'),
        category_path=[],
    )


class TruncateTests(unittest.TestCase):

    def test_shorter_than_max_returns_unchanged(self):
        self.assertEqual(truncate_description('short', 100), 'short')

    def test_exact_max_returns_unchanged(self):
        self.assertEqual(truncate_description('abcde', 5), 'abcde')

    def test_truncate_cjk_at_char_boundary(self):
        # 한국어는 글자 단위 절단 (Latin 단어 검사 통과 못 함)
        result = truncate_description('가나다라마바사', 3)
        self.assertEqual(result, '가나다…')

    def test_truncate_ascii_backs_up_to_word_boundary(self):
        # 'hello world tutorial' 의 13자 절단 → 'hello world ' (마지막
        # 공백까지 backup) → rstrip + …
        result = truncate_description('hello world tutorial', 13)
        self.assertEqual(result, 'hello world…')

    def test_truncate_single_long_word_falls_back(self):
        # max_len 안에 공백이 없는 단일 영문 단어 → 무한 폴백 방지로
        # 원래 절단 지점에서 자름
        result = truncate_description('abcdefghijklmnop', 5)
        # backup 실패 → 'abcde' + …
        self.assertEqual(result, 'abcde…')

    def test_truncate_after_word_boundary(self):
        # 'hello world' 6자 절단 → 'hello ' (절단 직후는 'w' 시작), Latin
        # 단어 한가운데 아님 (cut[-1]=' ' 은 word_char 아님) → rstrip + …
        result = truncate_description('hello world', 6)
        self.assertEqual(result, 'hello…')


class BuildMetaTagsTests(unittest.TestCase):

    def test_description_present_emits_tag(self):
        seo = SeoMeta(description='A nice intro')
        article = _article(seo=seo)
        tags_html, full_title = build_meta_tags(article, RenderResult(''), _site())
        self.assertIn('<meta name="description" content="A nice intro">', tags_html)
        self.assertIn('og:description', tags_html)
        self.assertIn('twitter:description', tags_html)

    def test_description_missing_omits_tag(self):
        # v0.5.5: None → 메타 태그 누락
        seo = SeoMeta(description=None)
        article = _article(seo=seo)
        tags_html, _ = build_meta_tags(article, RenderResult(''), _site())
        self.assertNotIn('<meta name="description"', tags_html)
        self.assertNotIn('og:description', tags_html)

    def test_description_empty_string_omits_tag(self):
        # v0.5.5: '' → 메타 태그 누락 (산출물엔 노이즈를 보내지 않음;
        # BuildReport 가 별도로 기록)
        seo = SeoMeta(description='')
        article = _article(seo=seo)
        tags_html, _ = build_meta_tags(article, RenderResult(''), _site())
        self.assertNotIn('<meta name="description"', tags_html)

    def test_og_image_uses_site_default(self):
        # v0.5.5: og_image 의 본문 폴백 제거. seo.og_image > site.default_og_image.
        seo = SeoMeta(og_image=None)
        article = _article(seo=seo)
        tags_html, _ = build_meta_tags(article, RenderResult(''), _site())
        self.assertIn('og:image" content="https://example.com/og.png"', tags_html)

    def test_full_title_prefix_suffix(self):
        seo = SeoMeta()
        article = _article(seo=seo, title='Hello')
        _, full_title = build_meta_tags(article, RenderResult(''), _site())
        self.assertEqual(full_title, 'Hello | Example')

    def test_seo_title_prefix_overrides_site_default(self):
        seo = SeoMeta(title_prefix='»', title_suffix='«')
        article = _article(seo=seo, title='Hello')
        _, full_title = build_meta_tags(article, RenderResult(''), _site())
        self.assertEqual(full_title, '»Hello«')

    def test_canonical_default(self):
        seo = SeoMeta()
        article = _article(seo=seo, slug='my-post')
        tags_html, _ = build_meta_tags(article, RenderResult(''), _site())
        self.assertIn('<link rel="canonical" href="https://example.com/my-post/">',
                      tags_html)

    def test_updated_falls_back_to_date(self):
        seo = SeoMeta(description='x')
        article = _article(seo=seo, date='2026-01-01', updated=None)
        tags_html, _ = build_meta_tags(article, RenderResult(''), _site())
        self.assertIn('article:modified_time" content="2026-01-01"', tags_html)


if __name__ == '__main__':
    unittest.main()

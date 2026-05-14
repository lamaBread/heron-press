"""seo.truncate_description / build_meta_tags 단위 테스트 (v0.6.2).

v0.6.2 변경:
  - build_meta_tags() 시그니처가 글 전용 (article, rr, site) → keyword-only
    일반 인자 (title, seo, site, canonical_path, page_kind, published, updated)
    로 일반화. 기존 글 테스트는 새 시그니처로 호출하도록 옮겼고, 홈/카테고리
    페이지의 메타 태그 출력 케이스와 og:type 페이지 종류별 디폴트 케이스가
    추가됨.

v0.5.4 의 단어 경계 truncate (영문 단어 중간에 자르지 않기, CJK 글자 단위
자유 절단) + v0.5.5 의 본문 폴백 제거 (본문 ↔ 메타데이터 분리 원칙) 케이스는
그대로 보존.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.seo import truncate_description, build_meta_tags  # noqa: E402
from scripts.models import SiteConfig, SeoMeta  # noqa: E402


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


def _article_meta(**kwargs):
    """글용 build_meta_tags 호출 인자를 한 줄에 합쳐 반환.

    v0.6.2 의 새 시그니처에 맞춰, 글 케이스에서 자주 쓰는 인자
    (page_kind='article', published, updated, canonical_path=f'/{slug}/')
    를 디폴트로 채움.
    """
    seo = kwargs.pop('seo', SeoMeta())
    title = kwargs.pop('title', 'T')
    slug = kwargs.pop('slug', 's')
    date = kwargs.pop('date', '2026-01-01')
    updated = kwargs.pop('updated', None)
    site = kwargs.pop('site', _site())
    return dict(
        title=title,
        seo=seo,
        site=site,
        canonical_path=f'/{slug}/',
        page_kind='article',
        published=date,
        updated=updated or date,
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


class BuildMetaTagsArticleTests(unittest.TestCase):

    def test_description_present_emits_tag(self):
        kwargs = _article_meta(seo=SeoMeta(description='A nice intro'))
        tags_html, _ = build_meta_tags(**kwargs)
        self.assertIn('<meta name="description" content="A nice intro">', tags_html)
        self.assertIn('og:description', tags_html)
        self.assertIn('twitter:description', tags_html)

    def test_description_missing_omits_tag(self):
        # v0.5.5: None → 메타 태그 누락
        kwargs = _article_meta(seo=SeoMeta(description=None))
        tags_html, _ = build_meta_tags(**kwargs)
        self.assertNotIn('<meta name="description"', tags_html)
        self.assertNotIn('og:description', tags_html)

    def test_description_empty_string_omits_tag(self):
        # v0.5.5: '' → 메타 태그 누락 (산출물엔 노이즈를 보내지 않음;
        # BuildReport 가 별도로 기록)
        kwargs = _article_meta(seo=SeoMeta(description=''))
        tags_html, _ = build_meta_tags(**kwargs)
        self.assertNotIn('<meta name="description"', tags_html)

    def test_og_image_uses_site_default(self):
        # v0.5.5: og_image 의 본문 폴백 제거. seo.og_image > site.default_og_image.
        kwargs = _article_meta(seo=SeoMeta(og_image=None))
        tags_html, _ = build_meta_tags(**kwargs)
        self.assertIn('og:image" content="https://example.com/og.png"', tags_html)

    def test_full_title_prefix_suffix(self):
        kwargs = _article_meta(seo=SeoMeta(), title='Hello')
        _, full_title = build_meta_tags(**kwargs)
        self.assertEqual(full_title, 'Hello | Example')

    def test_seo_title_prefix_overrides_site_default(self):
        kwargs = _article_meta(
            seo=SeoMeta(title_prefix='»', title_suffix='«'), title='Hello',
        )
        _, full_title = build_meta_tags(**kwargs)
        self.assertEqual(full_title, '»Hello«')

    def test_canonical_default(self):
        kwargs = _article_meta(seo=SeoMeta(), slug='my-post')
        tags_html, _ = build_meta_tags(**kwargs)
        self.assertIn('<link rel="canonical" href="https://example.com/my-post/">',
                      tags_html)

    def test_article_emits_published_and_modified_time(self):
        # 글 페이지는 published / updated 인자가 전달되어 article:* 시간 태그 출력.
        kwargs = _article_meta(
            seo=SeoMeta(description='x'),
            date='2026-01-01', updated='2026-03-15',
        )
        tags_html, _ = build_meta_tags(**kwargs)
        self.assertIn('article:published_time" content="2026-01-01"', tags_html)
        self.assertIn('article:modified_time" content="2026-03-15"', tags_html)

    def test_article_og_type_defaults_to_article(self):
        # SeoMeta.og_type=None + page_kind='article' → og:type=article.
        kwargs = _article_meta(seo=SeoMeta())
        tags_html, _ = build_meta_tags(**kwargs)
        self.assertIn('<meta property="og:type" content="article">', tags_html)

    def test_seo_og_type_override_wins(self):
        # author 가 seo.og_type 을 명시하면 page_kind 디폴트보다 우선.
        kwargs = _article_meta(seo=SeoMeta(og_type='profile'))
        tags_html, _ = build_meta_tags(**kwargs)
        self.assertIn('<meta property="og:type" content="profile">', tags_html)


class BuildMetaTagsHomeCategoryTests(unittest.TestCase):
    """v0.6.2: 홈/카테고리도 글과 같은 메타 태그 묶음을 출력."""

    def test_home_emits_meta_tags(self):
        # 홈 페이지: page_kind='home' / canonical_path='/' / published/updated 없음.
        # description 있으면 글과 동일하게 description / og:* / twitter:* 출력.
        tags_html, full_title = build_meta_tags(
            title='Example',
            seo=SeoMeta(description='Home tagline'),
            site=_site(),
            canonical_path='/',
            page_kind='home',
        )
        self.assertIn('<meta name="description" content="Home tagline">', tags_html)
        self.assertIn('og:description', tags_html)
        self.assertIn('twitter:description', tags_html)
        self.assertEqual(full_title, 'Example | Example')

    def test_home_canonical_is_root(self):
        tags_html, _ = build_meta_tags(
            title='Example',
            seo=SeoMeta(),
            site=_site(),
            canonical_path='/',
            page_kind='home',
        )
        self.assertIn('<link rel="canonical" href="https://example.com/">',
                      tags_html)
        self.assertIn('og:url" content="https://example.com/"', tags_html)

    def test_home_og_type_defaults_to_website(self):
        # SeoMeta.og_type=None + page_kind='home' → og:type=website (OGP 표준).
        tags_html, _ = build_meta_tags(
            title='Example',
            seo=SeoMeta(),
            site=_site(),
            canonical_path='/',
            page_kind='home',
        )
        self.assertIn('<meta property="og:type" content="website">', tags_html)

    def test_home_omits_article_time_tags(self):
        # 홈/카테고리는 published/updated 가 None 이라 article:* 시간 태그 누락.
        tags_html, _ = build_meta_tags(
            title='Example',
            seo=SeoMeta(description='x'),
            site=_site(),
            canonical_path='/',
            page_kind='home',
        )
        self.assertNotIn('article:published_time', tags_html)
        self.assertNotIn('article:modified_time', tags_html)

    def test_category_emits_meta_tags(self):
        tags_html, full_title = build_meta_tags(
            title='Blog',
            seo=SeoMeta(description='Blog index'),
            site=_site(),
            canonical_path='/blog/',
            page_kind='category',
        )
        self.assertIn('<meta name="description" content="Blog index">', tags_html)
        self.assertEqual(full_title, 'Blog | Example')

    def test_category_canonical_uses_path(self):
        tags_html, _ = build_meta_tags(
            title='Tutorials',
            seo=SeoMeta(),
            site=_site(),
            canonical_path='/blog/tutorials/',
            page_kind='category',
        )
        self.assertIn(
            '<link rel="canonical" href="https://example.com/blog/tutorials/">',
            tags_html,
        )

    def test_category_og_type_defaults_to_website(self):
        # SeoMeta.og_type=None + page_kind='category' → og:type=website.
        tags_html, _ = build_meta_tags(
            title='Blog',
            seo=SeoMeta(),
            site=_site(),
            canonical_path='/blog/',
            page_kind='category',
        )
        self.assertIn('<meta property="og:type" content="website">', tags_html)


if __name__ == '__main__':
    unittest.main()

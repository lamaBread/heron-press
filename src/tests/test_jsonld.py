"""seo.build_jsonld / jsonld_enabled / resolve_* + _parse_jsonld_config
단위 테스트 (v0.8.3 신설).

JSON-LD 는 기존 메타 태그를 *대체하지 않고 보강* (additive) 한다. 이
테스트는 (1) 사이트/글 토글 판정, (2) Article + BreadcrumbList @graph
구조, (3) 본문↔메타데이터 분리 (description/og_image/author 폴백이
build_meta_tags 와 동일), (4) `<script>` raw-text breakout 방지 escape,
(5) 결정성 (sort_keys → dict 삽입 순서 무관 byte 동일), (6) site.yaml
`jsonld:` 블록 파싱을 검증한다.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.seo import (  # noqa: E402
    build_jsonld, jsonld_enabled,
    resolve_canonical, resolve_og_image, resolve_author,
)
from scripts.models import SiteConfig, SeoMeta, JsonLdConfig  # noqa: E402
from scripts.builder import Builder  # noqa: E402


def _site(**overrides):
    defaults = dict(
        domain='example.com',
        base_url='https://example.com',
        name='Example',
        main_title='Example',
        default_author='Default Author',
        default_og_image='/og.png',
        default_title_prefix='',
        default_title_suffix=' | Example',
        copyright_holder='Author',
        copyright_year_start=2020,
        description_truncate=160,
        robots_txt_main='',
    )
    defaults.update(overrides)
    return SiteConfig(**defaults)


def _payload(html):
    """`<script type="application/ld+json">…</script>` 에서 JSON 만 추출."""
    prefix = '<script type="application/ld+json">'
    suffix = '</script>'
    assert html.startswith(prefix), html
    assert html.endswith(suffix), html
    return html[len(prefix):-len(suffix)]


def _doc(html):
    """escape 를 되돌리고 json.loads — 소비자가 보는 객체."""
    raw = (_payload(html)
           .replace('\\u003c', '<')
           .replace('\\u003e', '>')
           .replace('\\u0026', '&'))
    return json.loads(raw)


def _nodes(doc):
    """@graph 를 @type → node 로."""
    return {n['@type']: n for n in doc['@graph']}


# ════════════════════════════════════════════════════════════════
# 토글 판정 — 사이트가 마스터
# ════════════════════════════════════════════════════════════════

class JsonLdEnabledTests(unittest.TestCase):

    def test_default_site_and_seo_enabled(self):
        self.assertTrue(jsonld_enabled(_site(), SeoMeta()))

    def test_site_off_overrides_article_optin(self):
        site = _site(jsonld=JsonLdConfig(enabled=False))
        # 글 단위 True 로도 사이트 off 를 못 뒤집는다.
        self.assertFalse(jsonld_enabled(site, SeoMeta(jsonld=True)))
        self.assertFalse(jsonld_enabled(site, SeoMeta()))

    def test_article_optout_when_site_on(self):
        self.assertFalse(jsonld_enabled(_site(), SeoMeta(jsonld=False)))

    def test_article_none_follows_site(self):
        self.assertTrue(jsonld_enabled(_site(), SeoMeta(jsonld=None)))

    def test_article_true_when_site_on(self):
        self.assertTrue(jsonld_enabled(_site(), SeoMeta(jsonld=True)))


# ════════════════════════════════════════════════════════════════
# resolve_* 헬퍼 — build_meta_tags 와 같은 폴백 (추출 parity)
# ════════════════════════════════════════════════════════════════

class ResolveHelperTests(unittest.TestCase):

    def test_canonical_default_and_override(self):
        site = _site()
        self.assertEqual(
            resolve_canonical(SeoMeta(), site, '/slug/'),
            'https://example.com/slug/',
        )
        self.assertEqual(
            resolve_canonical(SeoMeta(canonical='https://x.test/p'),
                              site, '/slug/'),
            'https://x.test/p',
        )

    def test_og_image_fallback_and_absolutize(self):
        site = _site()
        # seo 부재 → site.default_og_image, 절대화
        self.assertEqual(
            resolve_og_image(SeoMeta(), site), 'https://example.com/og.png',
        )
        # seo 명시 (상대) → 절대화
        self.assertEqual(
            resolve_og_image(SeoMeta(og_image='/a/b.png'), site),
            'https://example.com/a/b.png',
        )
        # 절대 URL 은 그대로
        self.assertEqual(
            resolve_og_image(SeoMeta(og_image='https://cdn.test/x.png'), site),
            'https://cdn.test/x.png',
        )
        # 둘 다 없으면 None
        self.assertIsNone(
            resolve_og_image(SeoMeta(), _site(default_og_image='')),
        )

    def test_author_fallback(self):
        site = _site()
        self.assertEqual(resolve_author(SeoMeta(), site), 'Default Author')
        self.assertEqual(
            resolve_author(SeoMeta(author='Jane'), site), 'Jane',
        )


# ════════════════════════════════════════════════════════════════
# build_jsonld — Article 노드
# ════════════════════════════════════════════════════════════════

class BuildJsonLdArticleTests(unittest.TestCase):

    def _build(self, **kw):
        params = dict(
            title='My Post',
            seo=SeoMeta(description='An intro'),
            site=_site(),
            canonical_path='/my-post/',
            page_lang='ko',
            published='2026-01-02',
            updated='2026-03-04',
            tags=['python', 'ssg'],
            breadcrumb=[('Tech', '/tech/'), ('my-post', None)],
        )
        params.update(kw)
        return build_jsonld(**params)

    def test_script_wrapper_and_valid_json(self):
        html = self._build()
        doc = _doc(html)
        self.assertEqual(doc['@context'], 'https://schema.org')
        self.assertIsInstance(doc['@graph'], list)

    def test_article_core_fields(self):
        art = _nodes(_doc(self._build()))['Article']
        self.assertEqual(art['headline'], 'My Post')
        self.assertEqual(art['url'], 'https://example.com/my-post/')
        self.assertEqual(art['mainEntityOfPage']['@type'], 'WebPage')
        self.assertEqual(art['mainEntityOfPage']['@id'],
                         'https://example.com/my-post/')
        self.assertEqual(art['publisher']['@type'], 'Organization')
        self.assertEqual(art['publisher']['name'], 'Example')
        self.assertEqual(art['publisher']['url'], 'https://example.com')

    def test_dates(self):
        art = _nodes(_doc(self._build()))['Article']
        self.assertEqual(art['datePublished'], '2026-01-02')
        self.assertEqual(art['dateModified'], '2026-03-04')

    def test_description_present_and_absent(self):
        art = _nodes(_doc(self._build()))['Article']
        self.assertEqual(art['description'], 'An intro')
        # 부재(None) / 빈 문자열 → 키 없음 (메타 태그 정책과 동형)
        art2 = _nodes(_doc(self._build(seo=SeoMeta())))['Article']
        self.assertNotIn('description', art2)
        art3 = _nodes(_doc(self._build(seo=SeoMeta(description=''))))['Article']
        self.assertNotIn('description', art3)

    def test_author_fallback_to_site_default(self):
        art = _nodes(_doc(self._build(seo=SeoMeta())))['Article']
        self.assertEqual(art['author'],
                         {'@type': 'Person', 'name': 'Default Author'})
        art2 = _nodes(_doc(self._build(seo=SeoMeta(author='Jane'))))['Article']
        self.assertEqual(art2['author']['name'], 'Jane')

    def test_image_absolute_and_default(self):
        art = _nodes(_doc(self._build(seo=SeoMeta())))['Article']
        # site.default_og_image 폴백, 절대화
        self.assertEqual(art['image'], 'https://example.com/og.png')
        art2 = _nodes(_doc(
            self._build(seo=SeoMeta(og_image='/x.png'))))['Article']
        self.assertEqual(art2['image'], 'https://example.com/x.png')
        # og_image 도 site 디폴트도 없으면 image 키 없음
        art3 = _nodes(_doc(self._build(
            seo=SeoMeta(), site=_site(default_og_image=''))))['Article']
        self.assertNotIn('image', art3)

    def test_keywords_from_tags(self):
        art = _nodes(_doc(self._build()))['Article']
        self.assertEqual(art['keywords'], ['python', 'ssg'])
        art2 = _nodes(_doc(self._build(tags=[])))['Article']
        self.assertNotIn('keywords', art2)
        art3 = _nodes(_doc(self._build(tags=None)))['Article']
        self.assertNotIn('keywords', art3)

    def test_inlanguage(self):
        art = _nodes(_doc(self._build(page_lang='en')))['Article']
        self.assertEqual(art['inLanguage'], 'en')

    def test_canonical_seo_override_used(self):
        art = _nodes(_doc(self._build(
            seo=SeoMeta(canonical='https://x.test/p'))))['Article']
        self.assertEqual(art['url'], 'https://x.test/p')
        self.assertEqual(art['mainEntityOfPage']['@id'], 'https://x.test/p')


# ════════════════════════════════════════════════════════════════
# build_jsonld — BreadcrumbList 노드
# ════════════════════════════════════════════════════════════════

class BuildJsonLdBreadcrumbTests(unittest.TestCase):

    def _build(self, breadcrumb):
        return build_jsonld(
            title='T', seo=SeoMeta(), site=_site(),
            canonical_path='/t/', page_lang='ko',
            published='2026-01-01', updated='2026-01-01',
            tags=[], breadcrumb=breadcrumb,
        )

    def test_two_level_positions_and_items(self):
        # v0.8.3 계약: 중간 조상은 자기 *중첩* URL(부모와 distinct),
        # 말단(현재 페이지)은 item 생략 + name == Article.headline
        # (= 글 제목). 순진한 구현은 중간이 top_url 로 부모와 중복되고
        # 말단이 폴더명인 quirk 가 된다(Bug A / Bug B) — 이를 적발한다.
        doc = _doc(self._build([('Tech', '/tech/'),
                                ('Sub', '/tech/sub/'),
                                ('T', None)]))
        nodes = _nodes(doc)
        items = nodes['BreadcrumbList']['itemListElement']
        self.assertEqual([e['position'] for e in items], [1, 2, 3])
        self.assertEqual(items[0]['name'], 'Tech')
        self.assertEqual(items[0]['item'], 'https://example.com/tech/')
        # 중간 조상 = 자기 중첩 URL → 부모와 distinct (Bug A 교정)
        self.assertEqual(items[1]['item'], 'https://example.com/tech/sub/')
        self.assertNotEqual(items[0]['item'], items[1]['item'])
        # 말단 = item 생략 + name == headline (Bug B 교정)
        self.assertNotIn('item', items[2])
        self.assertEqual(items[2]['name'], 'T')
        self.assertEqual(items[2]['name'], nodes['Article']['headline'])

    def test_absolute_url_passthrough(self):
        doc = _doc(self._build([('Ext', 'https://other.test/x/'),
                                ('here', None)]))
        items = _nodes(doc)['BreadcrumbList']['itemListElement']
        self.assertEqual(items[0]['item'], 'https://other.test/x/')

    def test_single_crumb_omits_breadcrumblist(self):
        # 톱레벨 글의 단일 crumb → 의미 있는 경로 아님 → Article 만
        doc = _doc(self._build([('About', None)]))
        types = {n['@type'] for n in doc['@graph']}
        self.assertEqual(types, {'Article'})

    def test_none_breadcrumb_omits_breadcrumblist(self):
        doc = _doc(self._build(None))
        types = {n['@type'] for n in doc['@graph']}
        self.assertEqual(types, {'Article'})


# ════════════════════════════════════════════════════════════════
# <script> raw-text breakout 방지 + 결정성
# ════════════════════════════════════════════════════════════════

class JsonLdSafetyTests(unittest.TestCase):

    def _build(self, **kw):
        params = dict(
            title='T', seo=SeoMeta(), site=_site(),
            canonical_path='/t/', page_lang='ko',
            published='2026-01-01', updated='2026-01-01',
            tags=[], breadcrumb=[('A', '/a/'), ('b', None)],
        )
        params.update(kw)
        return build_jsonld(**params)

    def test_script_breakout_neutralized(self):
        html = self._build(
            title='Pwn </script><script>alert(1)</script> & <b> end')
        body = _payload(html)
        # 닫는 스크립트/주석 시퀀스가 원문 그대로 새지 않는다
        self.assertNotIn('</script>', body)
        self.assertNotIn('<script>', body)
        self.assertNotIn('<', body)
        self.assertNotIn('>', body)
        self.assertNotIn('&', body)
        self.assertIn('\\u003c', body)
        # escape 를 되돌리면 원문 title 복원 (유효 JSON)
        art = _nodes(_doc(html))['Article']
        self.assertEqual(
            art['headline'],
            'Pwn </script><script>alert(1)</script> & <b> end')

    def test_deterministic_same_input(self):
        a = self._build()
        b = self._build()
        self.assertEqual(a, b)

    def test_key_order_independent(self):
        # SeoMeta 필드 채우는 순서가 달라도 sort_keys 로 byte 동일
        s1 = SeoMeta(description='d', author='x', og_image='/i.png')
        s2 = SeoMeta(og_image='/i.png', author='x', description='d')
        self.assertEqual(self._build(seo=s1), self._build(seo=s2))

    def test_compact_separators(self):
        # separators=(',',':') — 공백 없는 compact 직렬화
        body = _payload(self._build())
        self.assertNotIn(', ', body)
        self.assertNotIn(': ', body)


# ════════════════════════════════════════════════════════════════
# site.yaml `jsonld:` 블록 파싱 (_parse_jsonld_config)
# ════════════════════════════════════════════════════════════════

class ParseJsonLdConfigTests(unittest.TestCase):
    """`_parse_jsonld_config` 는 self 를 쓰지 않으므로 unbound 로 호출
    (full Builder 인스턴스 불필요 — _parse_image_config 테스트와 같은 정신)."""

    def _parse(self, raw):
        return Builder._parse_jsonld_config(None, raw)

    def test_empty_defaults_enabled(self):
        self.assertTrue(self._parse({}).enabled)

    def test_missing_enabled_key_defaults_true(self):
        self.assertTrue(self._parse({'other': 1}).enabled)

    def test_enabled_false(self):
        self.assertFalse(self._parse({'enabled': False}).enabled)

    def test_enabled_falsey_coerced(self):
        self.assertFalse(self._parse({'enabled': 0}).enabled)
        self.assertTrue(self._parse({'enabled': 1}).enabled)

    def test_non_dict_falls_back_to_default(self):
        self.assertTrue(self._parse(None).enabled)
        self.assertTrue(self._parse('nope').enabled)

    def test_unknown_keys_ignored(self):
        cfg = self._parse({'enabled': True, 'future_key': 'x'})
        self.assertTrue(cfg.enabled)


if __name__ == '__main__':
    unittest.main()

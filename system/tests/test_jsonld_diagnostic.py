"""run_diagnostics 항목 [6] (JSON-LD 의미 정확성 게이트) 단위 테스트
(v0.8.3 신설).

검증기 `validate_jsonld_doc` / 추출기 `extract_jsonld` 의 *로직* 을
합성 입력으로 검사한다 — 라이브 dist 에 비의존(섹션 [6] 자체는
빌드 산출물을 읽지만, 이 테스트는 항상 결정적으로 통과/실패).

extract_jsonld 가 seo.build_jsonld 의 직렬화/escape 와 lockstep 임을
실제 build_jsonld 산출 문자열 round-trip 으로 보장한다.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from run_diagnostics import (  # noqa: E402
    extract_jsonld, validate_jsonld_doc,
)
from scripts.seo import build_jsonld  # noqa: E402
from scripts.models import SeoMeta  # noqa: E402
from test_jsonld import _site  # noqa: E402  (같은 스위트의 SiteConfig 픽스처)


def _good_doc():
    """정상 글 페이지 JSON-LD: 3단계 빵부스러기, 중간 distinct·
    실재, 말단 item 없음·name==headline."""
    return {
        '@context': 'https://schema.org',
        '@graph': [
            {'@type': 'Article', 'headline': '글 제목'},
            {'@type': 'BreadcrumbList', 'itemListElement': [
                {'@type': 'ListItem', 'position': 1, 'name': 'Blog',
                 'item': 'https://x.test/blog/'},
                {'@type': 'ListItem', 'position': 2, 'name': '3D Printing',
                 'item': 'https://x.test/blog/3d-printing/'},
                {'@type': 'ListItem', 'position': 3, 'name': '글 제목'},
            ]},
        ],
    }


def _always(_path):
    return True


class ExtractJsonLdTests(unittest.TestCase):

    def test_roundtrip_with_build_jsonld_escapes(self):
        # 이름에 < > & 포함 → seo.build_jsonld 의 \\u003c 등 치환을
        # extract_jsonld 가 정확히 역변환하는지 (production lockstep).
        html = build_jsonld(
            title='A<b>&c', seo=SeoMeta(), site=_site(),
            canonical_path='/p/', page_lang='ko',
            published='2026-01-01', updated='2026-01-01', tags=[],
            breadcrumb=[('R&D <x>', '/rnd/'), ('leaf', None)],
        )
        doc = extract_jsonld('<!doctype html><head>' + html + '</head>')
        nodes = {n['@type']: n for n in doc['@graph']}
        self.assertEqual(nodes['Article']['headline'], 'A<b>&c')
        bc = nodes['BreadcrumbList']['itemListElement']
        self.assertEqual(bc[0]['name'], 'R&D <x>')
        self.assertEqual(bc[0]['item'], 'https://example.com/rnd/')

    def test_returns_none_when_no_script(self):
        self.assertIsNone(extract_jsonld('<html><head></head></html>'))


class ValidateJsonLdDocTests(unittest.TestCase):

    def test_valid_doc_no_violations(self):
        self.assertEqual(
            validate_jsonld_doc(_good_doc(), base_url='https://x.test',
                                exists=_always),
            [])

    def test_bug_a_duplicate_nonleaf_items(self):
        d = _good_doc()
        # 중간(3D Printing)이 부모(Blog)와 같은 top_url → Bug A
        d['@graph'][1]['itemListElement'][1]['item'] = 'https://x.test/blog/'
        errs = validate_jsonld_doc(d, base_url='https://x.test',
                                   exists=_always)
        self.assertTrue(any('중복' in e for e in errs), errs)

    def test_bug_b_leaf_name_not_headline(self):
        d = _good_doc()
        d['@graph'][1]['itemListElement'][2]['name'] = '3D_Printer_hood'
        errs = validate_jsonld_doc(d, base_url='https://x.test',
                                   exists=_always)
        self.assertTrue(
            any('name != Article.headline' in e for e in errs), errs)

    def test_position_not_monotonic(self):
        d = _good_doc()
        d['@graph'][1]['itemListElement'][1]['position'] = 5
        errs = validate_jsonld_doc(d, base_url='https://x.test',
                                   exists=_always)
        self.assertTrue(any('position' in e for e in errs), errs)

    def test_leaf_must_not_have_item(self):
        d = _good_doc()
        d['@graph'][1]['itemListElement'][2]['item'] = 'https://x.test/x/'
        errs = validate_jsonld_doc(d, base_url='https://x.test',
                                   exists=_always)
        self.assertTrue(any('말단' in e and 'item' in e for e in errs), errs)

    def test_blank_headline(self):
        d = _good_doc()
        d['@graph'][0]['headline'] = '   '
        errs = validate_jsonld_doc(d, base_url='https://x.test',
                                   exists=_always)
        self.assertTrue(any('headline' in e for e in errs), errs)

    def test_nonleaf_item_not_resolvable_in_dist(self):
        # 모든 경로 부재 → 비말단 item 미해석 적발
        errs = validate_jsonld_doc(_good_doc(), base_url='https://x.test',
                                   exists=lambda p: False)
        self.assertTrue(any('미해석' in e for e in errs), errs)

    def test_no_breadcrumb_only_headline_checked(self):
        # 톱레벨 글: BreadcrumbList 생략은 정상 — headline 만 검사.
        doc = {'@context': 'https://schema.org',
               '@graph': [{'@type': 'Article', 'headline': 'About'}]}
        self.assertEqual(
            validate_jsonld_doc(doc, base_url='https://x.test',
                                exists=_always),
            [])

    def test_missing_article_node(self):
        doc = {'@context': 'https://schema.org', '@graph': [
            {'@type': 'BreadcrumbList', 'itemListElement': []}]}
        errs = validate_jsonld_doc(doc, base_url='https://x.test',
                                   exists=_always)
        self.assertTrue(any('Article' in e for e in errs), errs)


if __name__ == '__main__':
    unittest.main()

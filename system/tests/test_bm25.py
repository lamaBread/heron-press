"""BM25 알고리즘 핵심 단위 테스트.

v0.6.0 — 인덱스 포맷 v4 (메타데이터 3-필드 색인). v0.5.0 의 25개 테스트가
필드 이름 변경 (body → desc / tags 추가) 과 phrase 부스트 분기에 맞춰
재구성됨.

목표:
  - BM25 IDF / 필드 점수 / 전체 점수 / phrase 부스트 의 수식 회귀 차단
  - 인덱스 빌더 (build_search_index) 의 통계 (N, avgdl, df) 정확성
  - 토크나이저의 1글자 한글 제외 규칙 (v0.4.0 이래 불변)
  - v0.4.x / v0.5.x 의 알려진 결함이 재발하지 않는지 회귀 가드
  - v0.6.0 신규: noindex 글 제외 / 본문 색인 폐기 / tags 정확매치 부스트

런타임 PHP (templates/search_bm25.php → dist/search.php 안에 인라인) 은 본
테스트가 검증하는 Python 참조 구현 (scripts/search.py) 과 동일 공식. 어느
한쪽만 바뀌어도 실제 검색 품질이 흔들리므로 두 곳을 같이 보수해야 한다.

실행: `python -m unittest discover -s tests` (프로젝트 루트에서)
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.search import (  # noqa: E402
    BM25_PARAMS,
    bm25_field_score,
    bm25_idf,
    bm25_score,
    build_search_index,
    search_tokenize,
)


# ════════════════════════════════════════════════════════════════
# 토크나이저 — v0.4.0 규칙 재확인 (v0.5.0 / v0.6.0 변경 없음)
# ════════════════════════════════════════════════════════════════

class TokenizerTests(unittest.TestCase):

    def test_empty(self):
        self.assertEqual(search_tokenize(''), [])

    def test_latin_lowercase(self):
        self.assertEqual(search_tokenize('Hello World'), ['hello', 'world'])

    def test_single_hangul_excluded(self):
        # v0.4.0 규칙: 1글자 한글은 인덱싱하지 않는다.
        self.assertEqual(search_tokenize('한'), [])

    def test_hangul_bigram(self):
        # '한글' → ['한글'] (2-gram 1개)
        self.assertEqual(search_tokenize('한글'), ['한글'])
        # '안녕하세요' → 4개 bigram
        self.assertEqual(
            search_tokenize('안녕하세요'),
            ['안녕', '녕하', '하세', '세요'],
        )

    def test_mixed(self):
        tokens = search_tokenize('Hello 마스크 3D프린팅')
        self.assertIn('hello', tokens)
        self.assertIn('3d', tokens)
        self.assertIn('마스', tokens)
        self.assertIn('스크', tokens)
        self.assertIn('프린', tokens)


# ════════════════════════════════════════════════════════════════
# IDF — Okapi BM25 (Robertson-Spärck Jones, +1 smoothing)
# ════════════════════════════════════════════════════════════════

class IdfTests(unittest.TestCase):

    def test_rare_token_has_high_idf(self):
        idf_rare = bm25_idf(N=10, df=1)
        self.assertGreater(idf_rare, 1.0)

    def test_common_token_has_low_idf(self):
        idf_common = bm25_idf(N=10, df=10)
        self.assertGreaterEqual(idf_common, 0.0)
        self.assertLess(idf_common, 0.5)

    def test_idf_monotonic_in_df(self):
        prev = bm25_idf(N=100, df=1)
        for df in range(2, 101):
            cur = bm25_idf(N=100, df=df)
            self.assertLess(cur, prev,
                            f'IDF should decrease as df grows (df={df})')
            prev = cur


# ════════════════════════════════════════════════════════════════
# 필드 점수 — TF 포화 + 길이 정규화 (필드 무관 공식)
# ════════════════════════════════════════════════════════════════

class FieldScoreTests(unittest.TestCase):

    def _score(self, tf, dl, *, df=1, N=10, k1=1.5, b=0.75, avgdl=100.0):
        return bm25_field_score(
            tokens=['t'],
            df_map={'t': df},
            tf_map={'t': tf},
            dl=dl, avgdl=avgdl, N=N,
            k1=k1, b=b,
        )

    def test_tf_increases_score(self):
        s1 = self._score(tf=1, dl=100)
        s3 = self._score(tf=3, dl=100)
        s10 = self._score(tf=10, dl=100)
        self.assertLess(s1, s3)
        self.assertLess(s3, s10)

    def test_tf_saturates(self):
        s1 = self._score(tf=1, dl=100)
        s10 = self._score(tf=10, dl=100)
        s100 = self._score(tf=100, dl=100)
        self.assertGreater(s10 - s1, s100 - s10)

    def test_length_normalization(self):
        s_short = self._score(tf=3, dl=50,  avgdl=100.0)
        s_avg = self._score(tf=3, dl=100, avgdl=100.0)
        s_long = self._score(tf=3, dl=500, avgdl=100.0)
        self.assertGreater(s_short, s_avg)
        self.assertGreater(s_avg, s_long)

    def test_b_zero_disables_length_norm(self):
        s_a = self._score(tf=3, dl=50,  b=0.0)
        s_b = self._score(tf=3, dl=500, b=0.0)
        self.assertAlmostEqual(s_a, s_b)

    def test_unknown_token_contributes_zero(self):
        s = bm25_field_score(
            tokens=['unknown'],
            df_map={'t': 1},
            tf_map={'t': 5},
            dl=100, avgdl=100.0, N=10,
            k1=1.5, b=0.75,
        )
        self.assertEqual(s, 0.0)

    def test_zero_avgdl_yields_zero(self):
        # avgdl <= 0 (이 필드에 토큰이 한 글도 없음) → 0 점수.
        s = bm25_field_score(
            tokens=['t'],
            df_map={'t': 1},
            tf_map={'t': 5},
            dl=0, avgdl=0.0, N=10,
            k1=1.5, b=0.75,
        )
        self.assertEqual(s, 0.0)


# ════════════════════════════════════════════════════════════════
# 전체 점수 + phrase 부스트 (v4: title / desc / tags 세 필드)
# ════════════════════════════════════════════════════════════════

class _FakeSeo:
    def __init__(self, description=''):
        self.description = description


class _FakeMeta:
    def __init__(self, slug, title, description='', tags=None,
                 date='2026-05-14', noindex=False):
        self.slug = slug
        self.title = title
        self.date = date
        self.noindex = noindex
        self.seo = _FakeSeo(description=description)
        self.tags = tags or []


class _FakeArticle:
    def __init__(self, slug, title, description='', tags=None,
                 noindex=False):
        self.meta = _FakeMeta(slug, title, description, tags, noindex=noindex)


def _mk_index(docs_data, params=None):
    """테스트용 인덱스 dict 를 build_search_index 로 구성.

    docs_data : [(title, description, tags, body)] 튜플 또는
                [(title, description, tags)] (body 생략 시 빈 문자열).
    """
    articles = []
    rendered = {}
    for i, row in enumerate(docs_data):
        if len(row) == 4:
            title, desc, tags, body = row
        else:
            title, desc, tags = row
            body = ''
        slug = f'doc-{i}'
        articles.append(_FakeArticle(slug, title, desc, tags))
        rendered[slug] = body
    idx = build_search_index(
        articles, rendered, {}, top_category_for_article=lambda a: None,
    )
    if params:
        idx['params'].update(params)
    return idx


class FullScoreTests(unittest.TestCase):

    def test_title_match_beats_description_match(self):
        # 같은 쿼리에 대해 제목 매치 > description 매치 (w_title=3.0 > w_desc=1.5).
        index = _mk_index([
            ('python tutorial', 'unrelated about cooking', []),
            ('cooking recipes', 'python tutorial in description', []),
        ])
        s_title = bm25_score(index, 0, 'python')
        s_desc = bm25_score(index, 1, 'python')
        self.assertGreater(s_title, s_desc)

    def test_tags_exact_match_beats_substring(self):
        # tags 의 정확 일치는 강한 신호 — phrase_boost_tags=2.5 적용.
        # substring 매치는 일반 BM25 만 적용.
        index = _mk_index([
            # doc 0: tag 'python' 완전 일치 → phrase 부스트
            ('A', '', ['python']),
            # doc 1: description 에 'python' substring 매치만
            ('B', 'about python language', []),
        ])
        s_tag = bm25_score(index, 0, 'python')
        s_desc = bm25_score(index, 1, 'python')
        self.assertGreater(s_tag, s_desc)

    def test_rare_query_outranks_common_query(self):
        index = _mk_index([
            ('common a', 'apple banana common', []),
            ('common b', 'date elder common', []),
            ('common c', 'grape lemon common rarewordhere', []),
        ])
        score_common = bm25_score(index, 0, 'common')   # df=3
        score_rare = bm25_score(index, 2, 'rarewordhere')  # df=1
        self.assertGreater(score_rare, score_common)

    def test_unknown_query_zero_score(self):
        index = _mk_index([('a', 'apple banana', [])])
        self.assertEqual(bm25_score(index, 0, 'zzznotexist'), 0.0)

    def test_empty_query_zero_score(self):
        index = _mk_index([('a', 'apple banana', [])])
        self.assertEqual(bm25_score(index, 0, ''), 0.0)
        self.assertEqual(bm25_score(index, 0, '   '), 0.0)

    def test_phrase_boost_description(self):
        # description 에 phrase substring 매치 → ×phrase_boost_desc
        index = _mk_index([
            # doc 0: phrase '검색엔진' 이 description 에 그대로 등장
            ('A', '검색엔진 최적화에 관한 글입니다', []),
            # doc 1: 같은 토큰들이지만 phrase 미매치
            ('B', '검색을 위한 색엔 분리 그리고 엔진 별도 단어', []),
        ])
        s0 = bm25_score(index, 0, '검색엔진')
        s1 = bm25_score(index, 1, '검색엔진')
        self.assertGreater(s0, s1)

    def test_phrase_boost_title_multiplicative(self):
        index = _mk_index([
            ('python tutorial guide', '', []),
            ('learn python guide', '', []),
        ])
        s0 = bm25_score(index, 0, 'python tutorial')
        s1 = bm25_score(index, 1, 'python tutorial')
        self.assertGreater(s0, s1)

    def test_no_phrase_boost_when_zero_score(self):
        # phrase 부스트는 곱셈이므로 score=0 이면 여전히 0.
        index = _mk_index([('a', 'apple banana', [])])
        self.assertEqual(bm25_score(index, 0, 'zzznotexist'), 0.0)


# ════════════════════════════════════════════════════════════════
# 인덱스 빌더 — 통계 정확성 + v0.6.0 신규 동작
# ════════════════════════════════════════════════════════════════

class _FakeCategory:
    def __init__(self, folder_name, slug):
        self.folder_name = folder_name
        self.slug = slug


class IndexBuilderTests(unittest.TestCase):

    def test_basic_stats(self):
        articles = [
            _FakeArticle('a', 'Hello World', description='a fine intro',
                         tags=['greet']),
            _FakeArticle('b', '안녕하세요', description='간단한 인사말',
                         tags=['인사']),
        ]
        rendered = {'a': 'apple banana cherry', 'b': '안녕하세요'}
        cats = {('blog',): _FakeCategory('Blog', 'blog')}
        idx = build_search_index(
            articles, rendered, cats,
            top_category_for_article=lambda a: None,
        )
        self.assertEqual(idx['version'], 4)
        self.assertEqual(idx['stats']['N'], 2)
        # avgdl_title: 'Hello World' → 2, '안녕하세요' → 4. 평균 3.0
        self.assertAlmostEqual(idx['stats']['avgdl_title'], 3.0)
        # description / tags 도 토큰 통계 잡혀야.
        self.assertIn('hello', idx['df_title'])
        self.assertIn('fine', idx['df_desc'])
        # 'greet' 는 영문이라 그대로 토큰화
        self.assertIn('greet', idx['df_tags'])
        # 한국어 tag '인사' 는 1글자 bigram → '인사' (자체)
        self.assertIn('인사', idx['df_tags'])

    def test_sorted_by_slug(self):
        articles = [
            _FakeArticle('zebra', 'Z'),
            _FakeArticle('alpha', 'A'),
            _FakeArticle('mango', 'M'),
        ]
        rendered = {'zebra': '', 'alpha': '', 'mango': ''}
        idx = build_search_index(
            articles, rendered, {}, top_category_for_article=lambda a: None,
        )
        slugs_in_order = [d['slug'] for d in idx['docs']]
        self.assertEqual(slugs_in_order, ['alpha', 'mango', 'zebra'])

    def test_categories_only_top_level(self):
        cats = {
            ('blog',): _FakeCategory('Blog', 'blog'),
            ('blog', 'tutorials'): _FakeCategory('Tutorials', 'tutorials'),
        }
        idx = build_search_index(
            [], {}, cats, top_category_for_article=lambda a: None,
        )
        self.assertIn('blog', idx['categories'])
        self.assertNotIn('tutorials', idx['categories'])

    def test_noindex_excluded_from_index(self):
        # v0.6.0 신규: noindex 글은 인덱스에서 제외 (sitemap / feed 와 일관).
        articles = [
            _FakeArticle('public', 'Public Title', description='public desc'),
            _FakeArticle('hidden', 'Hidden Title', description='hidden desc',
                         noindex=True),
        ]
        rendered = {'public': '', 'hidden': ''}
        idx = build_search_index(
            articles, rendered, {}, top_category_for_article=lambda a: None,
        )
        self.assertEqual(idx['stats']['N'], 1)
        self.assertEqual(idx['docs'][0]['slug'], 'public')

    def test_body_snippet_truncated(self):
        # 본문 평문은 docs[].body_snippet 으로 보존되며 길이 제한이 있다.
        from scripts.search import BODY_SNIPPET_MAX_CHARS
        long_body = 'word ' * 1000  # 5000 chars
        articles = [_FakeArticle('long', 'L', description='x')]
        rendered = {'long': long_body}
        idx = build_search_index(
            articles, rendered, {}, top_category_for_article=lambda a: None,
        )
        self.assertLessEqual(len(idx['docs'][0]['body_snippet']),
                             BODY_SNIPPET_MAX_CHARS)

    def test_body_not_indexed_in_v4(self):
        # v0.6.0 핵심 변화: 본문은 더 이상 색인되지 않는다.
        # 'rarebodyterm' 이 본문에만 있고 title/desc/tags 어디에도 없으면
        # 검색 점수가 0.
        articles = [_FakeArticle('a', 'A title', description='nothing')]
        rendered = {'a': 'this body contains rarebodyterm xyz'}
        idx = build_search_index(
            articles, rendered, {}, top_category_for_article=lambda a: None,
        )
        # body_snippet 에는 보존되지만 df/tf 에는 없음.
        self.assertIn('rarebodyterm', idx['docs'][0]['body_snippet'])
        self.assertNotIn('rarebodyterm', idx['df_title'])
        self.assertNotIn('rarebodyterm', idx['df_desc'])
        self.assertNotIn('rarebodyterm', idx['df_tags'])
        self.assertEqual(bm25_score(idx, 0, 'rarebodyterm'), 0.0)

    def test_deterministic_keys(self):
        # 두 번 만들면 dict 키 순서까지 동일 (PHP literal 결정성의 근거).
        articles = [
            _FakeArticle('z', 'Z', description='zebra'),
            _FakeArticle('a', 'A', description='alpha'),
        ]
        rendered = {'z': '', 'a': ''}
        idx1 = build_search_index(
            articles, rendered, {}, top_category_for_article=lambda a: None,
        )
        idx2 = build_search_index(
            articles, rendered, {}, top_category_for_article=lambda a: None,
        )
        self.assertEqual(list(idx1['df_title'].keys()),
                         list(idx2['df_title'].keys()))
        self.assertEqual([d['slug'] for d in idx1['docs']],
                         [d['slug'] for d in idx2['docs']])


# ════════════════════════════════════════════════════════════════
# 회귀 가드 — 알려진 v0.4.x / v0.5.x 결함이 재발하지 않는지
# ════════════════════════════════════════════════════════════════

class RegressionGuards(unittest.TestCase):

    def test_common_korean_bigram_does_not_dominate_rare_term(self):
        # v0.4.x 결함: 흔한 한글 bigram (예: '하다') 이 희귀 영문 토큰과
        # 동등 가중치. IDF 도입으로 해소.
        index = _mk_index([
            ('A', '하다 hello', ['common']),
            ('B', '하다 hello', ['common']),
            ('C', '하다 hello', ['common']),
            ('D', '하다 unique-term', ['common']),
        ])
        scores = {i: bm25_score(index, i, 'unique-term') for i in range(4)}
        self.assertGreater(scores[3], 0)
        for i in [0, 1, 2]:
            self.assertEqual(scores[i], 0.0)

    def test_tags_substring_match_does_not_boost(self):
        # v0.6.0 정책: tags 의 정확 일치만 phrase 부스트. substring 은 일반
        # BM25 만 적용 (짧은 tag 의 substring 매치 노이즈 방지).
        # 두 글의 description / title 이 동일 + tag 만 다르면, "py" 검색
        # 시 tag='python' 의 substring 으로는 phrase 부스트가 발생 안 함.
        index = _mk_index([
            ('A', 'a description', ['python']),
            ('B', 'a description', ['py']),
        ])
        # 'py' 가 tag 와 *정확히* 일치하는 doc 1 이 phrase 부스트 ×2.5 받아
        # doc 0 보다 점수가 높아야 함. (doc 0 의 tag 'python' 은 substring 매치
        # 이지만 정확 일치는 아니므로 부스트 없음.)
        s0 = bm25_score(index, 0, 'py')
        s1 = bm25_score(index, 1, 'py')
        self.assertGreater(s1, s0)


if __name__ == '__main__':
    unittest.main()

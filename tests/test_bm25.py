"""BM25 알고리즘 핵심 단위 테스트 (v0.5.0).

목표:
  - BM25 IDF / 필드 점수 / 전체 점수 / phrase 부스트 의 수식 회귀 차단
  - 인덱스 빌더 (build_search_index) 의 통계 (N, avgdl, df) 정확성
  - 토크나이저의 1글자 한글 제외 규칙 (v0.4.0 이래 불변)

런타임 PHP (templates/search_bm25.php) 은 본 테스트가 검증하는 Python
참조 구현 (scripts/search.py) 과 동일 공식. 어느 한쪽만 바뀌어도
실제 검색 품질이 흔들리므로 두 곳을 같이 보수해야 한다.

실행: `python -m unittest discover -s tests` (프로젝트 루트에서)
"""
import math
import sys
import unittest
from pathlib import Path

# 프로젝트 루트를 sys.path 에 추가 (scripts 가 패키지)
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
# 토크나이저 — v0.4.0 규칙 재확인 (v0.5.0 변경 없음)
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
        # 10 문서 중 1 문서에만 등장 → 큰 IDF
        idf_rare = bm25_idf(N=10, df=1)
        self.assertGreater(idf_rare, 1.0)

    def test_common_token_has_low_idf(self):
        # 모든 문서에 등장 → IDF 가 0 근처. 단 +1 smoothing 으로 음수는 아님.
        idf_common = bm25_idf(N=10, df=10)
        self.assertGreaterEqual(idf_common, 0.0)
        self.assertLess(idf_common, 0.5)

    def test_idf_monotonic_in_df(self):
        # df 가 클수록 IDF 는 작아진다 (단조 감소).
        prev = bm25_idf(N=100, df=1)
        for df in range(2, 101):
            cur = bm25_idf(N=100, df=df)
            self.assertLess(cur, prev, f'IDF should decrease as df grows (df={df})')
            prev = cur


# ════════════════════════════════════════════════════════════════
# 필드 점수 — TF 포화 + 길이 정규화
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
        # BM25 의 핵심 특성: TF 가 커질수록 한계 이득이 감소 (포화).
        s1  = self._score(tf=1, dl=100)
        s10 = self._score(tf=10, dl=100)
        s100 = self._score(tf=100, dl=100)
        # 1→10 증가폭이 10→100 증가폭보다 커야 한다.
        self.assertGreater(s10 - s1, s100 - s10)

    def test_length_normalization(self):
        # 같은 TF 라도 긴 문서일수록 점수가 작아진다 (b > 0).
        s_short = self._score(tf=3, dl=50,  avgdl=100.0)
        s_avg   = self._score(tf=3, dl=100, avgdl=100.0)
        s_long  = self._score(tf=3, dl=500, avgdl=100.0)
        self.assertGreater(s_short, s_avg)
        self.assertGreater(s_avg, s_long)

    def test_b_zero_disables_length_norm(self):
        # b=0 이면 dl 에 무관하게 같은 점수.
        s_a = self._score(tf=3, dl=50,  b=0.0)
        s_b = self._score(tf=3, dl=500, b=0.0)
        self.assertAlmostEqual(s_a, s_b)

    def test_unknown_token_contributes_zero(self):
        s = bm25_field_score(
            tokens=['unknown'],
            df_map={'t': 1},
            tf_map={'t': 5},  # 다른 토큰의 tf 가 있어도 'unknown' 이면 0
            dl=100, avgdl=100.0, N=10,
            k1=1.5, b=0.75,
        )
        self.assertEqual(s, 0.0)


# ════════════════════════════════════════════════════════════════
# 전체 점수 + phrase 부스트
# ════════════════════════════════════════════════════════════════

def _mk_index(docs_data, params=None):
    """테스트용 인덱스 dict 를 토큰화 결과로부터 구성.

    docs_data : [(title, body)] — body 는 평문 (HTML 이 아님).
    """
    p = dict(params) if params else dict(BM25_PARAMS)
    docs = []
    tf_body_map = {}
    tf_title_map = {}
    dls_b = []
    dls_t = []
    for i, (title, body) in enumerate(docs_data):
        body_toks = search_tokenize(body)
        title_toks = search_tokenize(title)
        dl_b = len(body_toks)
        dl_t = len(title_toks)
        dls_b.append(dl_b)
        dls_t.append(dl_t)
        docs.append({
            'slug': f'doc-{i}',
            'title': title,
            'date': '2026-05-14',
            'category': '',
            'category_slug': '',
            'body': body,
            'dl_body': dl_b,
            'dl_title': dl_t,
        })
        tf_b = {}
        for t in body_toks:
            tf_b[t] = tf_b.get(t, 0) + 1
        for t, tf in tf_b.items():
            tf_body_map.setdefault(t, {})[i] = tf
        tf_t = {}
        for t in title_toks:
            tf_t[t] = tf_t.get(t, 0) + 1
        for t, tf in tf_t.items():
            tf_title_map.setdefault(t, {})[i] = tf

    N = len(docs)
    return {
        'version': 3,
        'params': p,
        'stats': {
            'N': N,
            'avgdl_body': sum(dls_b) / N if N else 0.0,
            'avgdl_title': sum(dls_t) / N if N else 0.0,
        },
        'docs': docs,
        'categories': {},
        'df_body': {t: len(post) for t, post in tf_body_map.items()},
        'df_title': {t: len(post) for t, post in tf_title_map.items()},
        'tf_body': {t: [[d, tf] for d, tf in post.items()]
                    for t, post in tf_body_map.items()},
        'tf_title': {t: [[d, tf] for d, tf in post.items()]
                     for t, post in tf_title_map.items()},
    }


class FullScoreTests(unittest.TestCase):

    def test_title_match_beats_body_match(self):
        # 같은 쿼리에 대해 제목 매치 > 본문 매치 (w_title=3.0 + 짧은 dl_title).
        index = _mk_index([
            ('python tutorial', 'something unrelated about cooking'),
            ('cooking recipes', 'python tutorial in the body somewhere'),
        ])
        s_title_match = bm25_score(index, 0, 'python')
        s_body_match = bm25_score(index, 1, 'python')
        self.assertGreater(s_title_match, s_body_match)

    def test_rare_query_outranks_common_query(self):
        # 모든 문서에 흔한 토큰보다, 한 문서에만 등장하는 희귀 토큰이 더 강한 신호.
        index = _mk_index([
            ('a', 'apple banana cherry common'),
            ('b', 'date elder fig common'),
            ('c', 'grape kiwi lemon common rarewordhere'),
        ])
        score_common = bm25_score(index, 0, 'common')   # df=3
        score_rare = bm25_score(index, 2, 'rarewordhere')  # df=1
        self.assertGreater(score_rare, score_common)

    def test_unknown_query_zero_score(self):
        index = _mk_index([('a', 'apple banana')])
        self.assertEqual(bm25_score(index, 0, 'zzznotexist'), 0.0)

    def test_empty_query_zero_score(self):
        index = _mk_index([('a', 'apple banana')])
        self.assertEqual(bm25_score(index, 0, ''), 0.0)
        self.assertEqual(bm25_score(index, 0, '   '), 0.0)

    def test_phrase_boost_body(self):
        # 같은 토큰 (검색 / 색엔 / 엔진) 이 본문에 있지만, phrase 가
        # 연속 substring 으로 등장하는 doc 이 더 높은 점수여야 한다.
        # "검색엔진" → tokens: ['검색','색엔','엔진'].
        index = _mk_index([
            # doc 0: phrase '검색엔진' 이 그대로 등장 → phrase 부스트 ×1.5
            ('A', '검색엔진 최적화에 관한 글입니다'),
            # doc 1: 같은 토큰들이지만 phrase 미매치 (사이에 다른 글자)
            ('B', '검색을 위한 색엔 분리 그리고 엔진 별도 단어'),
        ])
        s0 = bm25_score(index, 0, '검색엔진')
        s1 = bm25_score(index, 1, '검색엔진')
        # phrase 매치한 doc 이 더 높아야 함.
        self.assertGreater(s0, s1)

    def test_phrase_boost_title_multiplicative(self):
        # 제목에 원본 쿼리가 substring 매치되면 ×phrase_boost_title.
        index = _mk_index([
            ('python tutorial guide', 'unrelated body'),
            ('learn python guide', 'unrelated body'),
        ])
        # 두 쿼리 모두 'python' 토큰 매치이지만, doc 0 의 제목에는
        # 'python tutorial' substring 이 있고 doc 1 에는 없다.
        s0 = bm25_score(index, 0, 'python tutorial')
        s1 = bm25_score(index, 1, 'python tutorial')
        self.assertGreater(s0, s1)

    def test_no_phrase_boost_when_zero_score(self):
        # phrase 부스트는 곱셈이므로 score=0 이면 여전히 0. (regression guard)
        index = _mk_index([('a', 'apple banana')])
        # 쿼리 'banana' 는 토큰 매치되지만, 'zzznotexist' 는 매치 안 됨.
        self.assertEqual(bm25_score(index, 0, 'zzznotexist'), 0.0)


# ════════════════════════════════════════════════════════════════
# 인덱스 빌더 — 통계 정확성
# ════════════════════════════════════════════════════════════════

class _FakeMeta:
    def __init__(self, slug, title, date='2026-05-14'):
        self.slug = slug
        self.title = title
        self.date = date


class _FakeArticle:
    def __init__(self, slug, title):
        self.meta = _FakeMeta(slug, title)


class _FakeCategory:
    def __init__(self, folder_name, slug):
        self.folder_name = folder_name
        self.slug = slug


class IndexBuilderTests(unittest.TestCase):

    def test_basic_stats(self):
        articles = [
            _FakeArticle('a', 'Hello World'),
            _FakeArticle('b', '안녕하세요'),
        ]
        rendered = {
            'a': 'apple banana cherry',                   # 3 tokens
            'b': '안녕하세요',                              # 4 bigrams
        }
        cats = {('blog',): _FakeCategory('Blog', 'blog')}
        idx = build_search_index(
            articles, rendered, cats,
            top_category_for_article=lambda a: None,
        )
        self.assertEqual(idx['version'], 3)
        self.assertEqual(idx['stats']['N'], 2)
        # avgdl_body = (3 + 4) / 2 = 3.5
        self.assertAlmostEqual(idx['stats']['avgdl_body'], 3.5)
        # avgdl_title : 'Hello World' → 2 tokens, '안녕하세요' → 4 bigrams.
        # 평균 = 3.0
        self.assertAlmostEqual(idx['stats']['avgdl_title'], 3.0)
        # df_body['apple'] = 1, df_body 에는 한국어 토큰도 포함
        self.assertEqual(idx['df_body'].get('apple'), 1)
        self.assertEqual(idx['df_body'].get('안녕'), 1)

    def test_sorted_by_slug(self):
        # build_search_index 는 슬러그 정렬 순으로 doc_id 부여
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
        # categories_map 은 path 깊이 1 (톱레벨) 만 포함.
        cats = {
            ('blog',): _FakeCategory('Blog', 'blog'),
            ('blog', 'tutorials'): _FakeCategory('Tutorials', 'tutorials'),
        }
        idx = build_search_index(
            [], {}, cats, top_category_for_article=lambda a: None,
        )
        self.assertIn('blog', idx['categories'])
        self.assertNotIn('tutorials', idx['categories'])


# ════════════════════════════════════════════════════════════════
# 회귀 가드 — 알려진 v0.4.x 결함이 재발하지 않는지
# ════════════════════════════════════════════════════════════════

class V04RegressionGuards(unittest.TestCase):

    def test_long_doc_does_not_dominate_by_tf_alone(self):
        # v0.4.x 결함: 단순 TF 합산. 같은 토큰이 본문에 많이 등장하는 긴 글이
        # 부당하게 높은 점수. BM25 의 길이 정규화로 해소.
        long_body = ' '.join(['python'] * 200 + ['filler'] * 800)
        short_body = 'python is a programming language'
        index = _mk_index([
            ('A long', long_body),
            ('B short', short_body),
        ])
        s_long = bm25_score(index, 0, 'python')
        s_short = bm25_score(index, 1, 'python')
        # v0.4.x 였다면 s_long >> s_short (단순 TF 합산). BM25 에서는
        # 길이 정규화로 단순 TF 우위가 약화. 적어도 30배 이상 차이는 나지
        # 않아야 한다 (감각적 임계 — 회귀 시 1000 배 이상 났던 케이스).
        self.assertLess(s_long, s_short * 30,
                        f's_long={s_long}, s_short={s_short} — 길이 정규화 회귀')

    def test_common_korean_bigram_does_not_dominate_rare_term(self):
        # v0.4.x 결함: 흔한 한글 bigram (예: '하다' 의 '하다') 이 희귀 영문
        # 토큰과 동등 가중치. IDF 도입으로 해소.
        index = _mk_index([
            ('A', '하다 하다 하다 hello'),
            ('B', '하다 하다 hello hello hello'),
            ('C', '하다 hello hello'),
            ('D', '하다 unique-term'),
        ])
        # '하다' 는 모든 문서 → df=4. 'unique-term' 은 doc 3 만 → df=1.
        # 'unique-term' 검색 시 doc 3 이 압도적이어야 함.
        scores = {i: bm25_score(index, i, 'unique-term') for i in range(4)}
        self.assertGreater(scores[3], 0)
        # doc 3 외에는 0 (토큰 미매치)
        for i in [0, 1, 2]:
            self.assertEqual(scores[i], 0.0)


if __name__ == '__main__':
    unittest.main()

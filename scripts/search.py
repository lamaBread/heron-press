"""검색 인덱스 구축 (BM25, v3 포맷) + Python↔PHP 토크나이저 패리티 테스트.

v0.5.0 변경 — BM25 기반 랭킹으로 전환:
  (a) 인덱스 포맷 v3. tf 가 필드별 (body / title) 로 분리. df_body / df_title
      (문서 빈도) 와 dl_body / dl_title (문서별 토큰 수), avgdl_body / avgdl_title
      (평균 토큰 수) 추가. 런타임에 search.php 가 이 통계로 BM25 IDF 와 길이
      정규화를 계산.
  (b) 단순 TF 합산 (v0.4.x) → Okapi BM25 점수.
      score = bm25_body(Q,D) + w_title · bm25_title(Q,D)
      옵션 phrase 부스트 (원본 쿼리 substring 매치 시 곱셈) 는 PHP 측에서.
  (c) 한국어 토크나이저 자체는 v0.4.0 과 동일 (1글자 한글 제외, bigram).
      토크나이저 패리티 테스트도 그대로 유지.
  (d) `bm25_score()` Python 참조 구현 추가. tests/test_bm25.py 가 이를 호출
      해 알고리즘 회귀를 차단. 런타임 (PHP) 과 동일 공식.

인덱스 포맷 v3:
  {
    "version": 3,
    "params": {"k1_body", "b_body", "k1_title", "b_title",
               "w_title", "phrase_boost_body", "phrase_boost_title"},
    "stats":  {"N", "avgdl_body", "avgdl_title"},
    "docs":   [{"slug","title","date","category","category_slug","body",
                "dl_body","dl_title"}, ...],
    "categories": {"<slug>": "<folder_name>", ...},
    "df_body":    {"<token>": <doc count>, ...},
    "df_title":   {"<token>": <doc count>, ...},
    "tf_body":    {"<token>": [[doc_id, tf], ...]},
    "tf_title":   {"<token>": [[doc_id, tf], ...]},
  }
"""
import json
import math
import re
import subprocess
from pathlib import Path


_SEARCH_LATIN_RE = re.compile(r'[a-z0-9]+')
_SEARCH_HAN_RE = re.compile(r'[가-힣]+')


def search_tokenize(text: str) -> list:
    """build.py / search.php 가 동일하게 사용하는 토크나이저.

    v0.4.0 규칙 (v0.5.0 변경 없음):
      - 영문/숫자 (lowercase) : 단어 단위로 그대로
      - 한글 (가-힣) : 음절 2-gram (bigram). 길이 1 인 한글 시퀀스는 무시.
      - 그 외 문자 : 토큰 분리자로만 작용

    PHP 측 search_tokenize() (templates/search_tokenize.php) 와 출력이
    바이트 단위로 일치해야 한다.
    """
    if not text:
        return []
    text = text.lower()
    tokens = []
    for m in _SEARCH_LATIN_RE.finditer(text):
        tokens.append(m.group())
    for m in _SEARCH_HAN_RE.finditer(text):
        word = m.group()
        if len(word) < 2:
            continue  # v0.4.0: 1글자 한글 제외
        for i in range(len(word) - 1):
            tokens.append(word[i:i + 2])
    return tokens


_TAG_STRIP_RE = re.compile(r'<[^>]+>')
_STYLE_SCRIPT_RE = re.compile(
    r'<(style|script)\b[^>]*>.*?</\1>', re.DOTALL | re.IGNORECASE
)
_WS_COLLAPSE_RE = re.compile(r'\s+')


def html_to_plain(html: str) -> str:
    """렌더된 본문 HTML 에서 태그를 제거한 평문. 공백은 1개로 압축.

    <style> / <script> 블록은 내용까지 통째로 제거 — 본문 인라인 스타일이
    인덱스 노이즈가 되는 것을 방지.
    """
    s = _STYLE_SCRIPT_RE.sub(' ', html or '')
    s = _TAG_STRIP_RE.sub(' ', s)
    s = _WS_COLLAPSE_RE.sub(' ', s).strip()
    return s


# ════════════════════════════════════════════════════════════════
# BM25 hyperparameters
# ════════════════════════════════════════════════════════════════
#
# 두 필드 (body, title) 에 독립적인 BM25 파라미터를 둔다. 제목은 짧고
# 토큰 하나의 의미 비중이 크므로 b 를 낮춰 길이 정규화 영향을 줄이고
# k1 도 살짝 낮춰 첫 TF 의 보상을 크게.
#
# w_title : 두 필드 점수를 합칠 때 제목 필드 가중치. v0.4.x 의 매직 ×5
#           대신 BM25 정규화된 점수 위에 곱하므로 의미가 명확.
#
# phrase_boost_* : 원본 쿼리 문자열이 평문 본문/제목에 substring 매치되면
#                  최종 점수에 곱하는 부스트. 토큰 단위로 흩어진 매치보다
#                  연속 substring 매치가 훨씬 강한 관련성 신호.

BM25_PARAMS = {
    'k1_body': 1.5,
    'b_body': 0.75,
    'k1_title': 1.2,
    'b_title': 0.5,
    'w_title': 3.0,
    'phrase_boost_body': 1.5,
    'phrase_boost_title': 2.0,
}


def bm25_idf(N: int, df: int) -> float:
    """Okapi BM25 IDF (Robertson-Spärck Jones, +1 smoothing).

    IDF(t) = ln( (N - df + 0.5) / (df + 0.5) + 1 )

    df=0 (인덱스에 없는 토큰) 은 호출자가 미리 거른다. df=N 이어도 +1 덕에
    음수가 되지 않고 0 에 수렴.
    """
    return math.log((N - df + 0.5) / (df + 0.5) + 1.0)


def bm25_field_score(tokens, df_map, tf_map, dl, avgdl, N, k1, b):
    """한 필드 BM25 점수.

    score = Σ_{t ∈ tokens} IDF(t) · ( tf(t,D) · (k1+1) ) /
                            ( tf(t,D) + k1 · (1 - b + b · dl/avgdl) )

    tokens   : 쿼리 토큰 리스트 (중복 허용 — 같은 토큰 2번 들어오면 2번 가산.
               단순 BM25 의 표준 동작. 쿼리 측 TF 가중치를 BM25-Q 식으로
               별도 도입하지는 않음.)
    df_map   : {token: df}.
    tf_map   : {token: tf} — 해당 문서 D 의 토큰 빈도.
    dl       : 문서 D 의 길이 (이 필드 토큰 수).
    avgdl    : 전체 문서의 이 필드 평균 토큰 수.
    """
    if N <= 0 or avgdl <= 0:
        return 0.0
    score = 0.0
    norm = 1.0 - b + b * (dl / avgdl)
    for t in tokens:
        df = df_map.get(t, 0)
        if df <= 0:
            continue
        tf = tf_map.get(t, 0)
        if tf <= 0:
            continue
        idf = bm25_idf(N, df)
        score += idf * (tf * (k1 + 1.0)) / (tf + k1 * norm)
    return score


def bm25_score(index: dict, doc_id: int, query: str,
               params: dict = None) -> float:
    """완전한 BM25 점수 (body + w_title·title) + phrase 부스트.

    Python 참조 구현. tests/test_bm25.py 가 이를 호출해 알고리즘을 검증.
    런타임 (PHP) 의 search.php 도 동일 공식을 구현해야 한다.

    index : build_search_index() 반환값.
    doc_id : 채점 대상 docs[] 인덱스.
    query  : 사용자 쿼리 원문 (phrase 부스트용으로 원본 보존 필요).
    params : 하이퍼파라미터 오버라이드 — None 이면 index['params'].
    """
    p = params if params is not None else index.get('params', BM25_PARAMS)
    stats = index['stats']
    N = stats['N']
    if doc_id < 0 or doc_id >= len(index['docs']):
        return 0.0
    doc = index['docs'][doc_id]

    tokens = search_tokenize(query)
    if not tokens:
        return 0.0

    # 단일 문서의 필드별 TF 를 posting 에서 역추출.
    # (런타임 PHP 는 posting 순회 중 누적하므로 비효율 없음. 참조 구현은
    # 명확성 우선으로 검색-친화적 lookup 으로 구성.)
    def _tf_for_doc(tf_postings, did):
        out = {}
        for tok, posting in tf_postings.items():
            for entry in posting:
                if entry[0] == did:
                    out[tok] = entry[1]
                    break
        return out

    tf_body_doc = _tf_for_doc(index['tf_body'], doc_id)
    tf_title_doc = _tf_for_doc(index['tf_title'], doc_id)

    score_body = bm25_field_score(
        tokens, index['df_body'], tf_body_doc,
        doc['dl_body'], stats['avgdl_body'], N,
        p['k1_body'], p['b_body'],
    )
    score_title = bm25_field_score(
        tokens, index['df_title'], tf_title_doc,
        doc['dl_title'], stats['avgdl_title'], N,
        p['k1_title'], p['b_title'],
    )

    total = score_body + p['w_title'] * score_title
    if total <= 0:
        return 0.0

    # Phrase 부스트 — 원본 쿼리 (lowercase) 가 평문에 substring 매치되면
    # 곱셈 부스트. 0 점수에는 효과 없고 의미 있는 점수만 강화.
    q_lower = query.strip().lower()
    if len(q_lower) >= 2:
        if q_lower in (doc.get('body') or '').lower():
            total *= p['phrase_boost_body']
        if q_lower in (doc.get('title') or '').lower():
            total *= p['phrase_boost_title']

    return total


# ════════════════════════════════════════════════════════════════
# Python ↔ PHP tokenizer parity test  (unchanged from v0.4.x)
# ════════════════════════════════════════════════════════════════

PARITY_FIXTURES = [
    '',
    ' ',
    'Hello',
    'HELLO world',
    'siheonlee.com',
    '한',                       # 1글자 한글 — 토큰 없음
    '한글',                     # bigram 1개
    '안녕하세요',                # bigram 4개
    '검색 테스트',               # 두 단어
    'Hello 마스크 3D프린팅',      # 영문 + 한글 + 영숫자
    '문장. 끝.',                # 구두점
    'A_B_C',                   # 언더스코어 분리
    'café',                    # 비ASCII 라틴 (영문 매치 안 됨)
    '日本語',                   # 한자 (영문/한글 매치 안 됨)
    'X 가나다라마바사 Y',         # 좁은 한국어 시퀀스 사이 영문
    '1234',                    # 숫자
    'V0.4.0',                  # 소문자 정규화
    'a b c d e',               # 짧은 영문 토큰들
]


def _php_tokenize_one(text: str, tokenizer_php: Path, php_bin: str = 'php') -> list:
    """PHP CLI 로 한 줄 토큰화. JSON 배열을 반환."""
    proc = subprocess.run(
        [php_bin, str(tokenizer_php), text],
        capture_output=True,
        timeout=30,
    )
    if proc.returncode != 0:
        err = proc.stderr.decode('utf-8', errors='replace').strip()
        raise RuntimeError(f'PHP tokenizer exit={proc.returncode}: {err}')
    return json.loads(proc.stdout.decode('utf-8'))


def run_parity_test(templates_dir: Path, php_bin: str, warn_fn, die_fn) -> bool:
    """fixture 입력에 대해 Py↔PHP 토크나이저 출력 동등성 검증."""
    tokenizer_php = templates_dir / 'search_tokenize.php'
    if not tokenizer_php.exists():
        die_fn(f'search_tokenize.php not found at {tokenizer_php}')

    try:
        probe = subprocess.run(
            [php_bin, '-v'],
            capture_output=True,
            timeout=10,
        )
        if probe.returncode != 0:
            warn_fn('PHP not available — skipping tokenizer parity test.')
            return False
    except (FileNotFoundError, subprocess.TimeoutExpired):
        warn_fn('PHP not available — skipping tokenizer parity test.')
        return False

    mismatches = []
    for fixture in PARITY_FIXTURES:
        py_tokens = search_tokenize(fixture)
        try:
            php_tokens = _php_tokenize_one(fixture, tokenizer_php, php_bin)
        except Exception as e:
            die_fn(f'PHP tokenizer error on {repr(fixture)}: {e}')
        if py_tokens != php_tokens:
            mismatches.append((fixture, py_tokens, php_tokens))

    if mismatches:
        lines = ['토크나이저 패리티 실패 (Python ≠ PHP):']
        for fx, py, php in mismatches:
            lines.append(f"  input: {repr(fx)}")
            lines.append(f"    Python: {py}")
            lines.append(f"    PHP   : {php}")
        die_fn('\n'.join(lines))

    print(f'[search] tokenizer parity OK ({len(PARITY_FIXTURES)} fixtures)')
    return True


# ════════════════════════════════════════════════════════════════
# Search index build  (v0.5.0: BM25 v3 format)
# ════════════════════════════════════════════════════════════════

def build_search_index(articles, rendered_bodies, categories,
                       top_category_for_article) -> dict:
    """BM25 검색 인덱스 dict 생성. dist 쓰기는 호출자가 수행.

    포맷 v3 (이 모듈 docstring 참조). v0.4.x 의 v2 와 비호환:
      - 인덱스 키 이름 변경 (`index` → `tf_body`, `title_index` → `tf_title`)
      - 필드별 df 추가 (BM25 IDF 용)
      - 문서별 dl_body / dl_title 와 전역 avgdl_* 추가 (길이 정규화 용)
    """
    docs = []
    body_tf_map = {}   # token → {doc_id: tf}
    title_tf_map = {}
    body_dls = []
    title_dls = []

    sorted_articles = sorted(articles, key=lambda a: a.meta.slug)

    for doc_id, article in enumerate(sorted_articles):
        m = article.meta
        body_plain = rendered_bodies.get(m.slug, '')

        top_cat_obj = top_category_for_article(article)
        top_cat_name = top_cat_obj.folder_name if top_cat_obj else ''
        top_cat_slug = top_cat_obj.slug if top_cat_obj else ''

        body_tokens = search_tokenize(body_plain)
        title_tokens = search_tokenize(m.title)
        dl_body = len(body_tokens)
        dl_title = len(title_tokens)
        body_dls.append(dl_body)
        title_dls.append(dl_title)

        docs.append({
            'slug': m.slug,
            'title': m.title,
            'date': m.date,
            'category': top_cat_name,
            'category_slug': top_cat_slug,
            'body': body_plain,
            'dl_body': dl_body,
            'dl_title': dl_title,
        })

        # 필드별 TF 집계
        body_tf = {}
        for t in body_tokens:
            body_tf[t] = body_tf.get(t, 0) + 1
        for t, tf in body_tf.items():
            body_tf_map.setdefault(t, {})[doc_id] = tf

        title_tf = {}
        for t in title_tokens:
            title_tf[t] = title_tf.get(t, 0) + 1
        for t, tf in title_tf.items():
            title_tf_map.setdefault(t, {})[doc_id] = tf

    N = len(docs)
    avgdl_body = (sum(body_dls) / N) if N > 0 else 0.0
    avgdl_title = (sum(title_dls) / N) if N > 0 else 0.0

    # df_field[token] = posting 길이 (그 토큰이 등장한 문서 수)
    df_body = {tok: len(post) for tok, post in body_tf_map.items()}
    df_title = {tok: len(post) for tok, post in title_tf_map.items()}

    def compact(idx):
        return {tok: [[d, tf] for d, tf in posting.items()]
                for tok, posting in idx.items()}

    categories_map = {
        cat.slug: cat.folder_name
        for path_tuple, cat in categories.items()
        if len(path_tuple) == 1
    }

    return {
        'version': 3,
        'params': dict(BM25_PARAMS),
        'stats': {
            'N': N,
            'avgdl_body': avgdl_body,
            'avgdl_title': avgdl_title,
        },
        'docs': docs,
        'categories': categories_map,
        'df_body': df_body,
        'df_title': df_title,
        'tf_body': compact(body_tf_map),
        'tf_title': compact(title_tf_map),
    }

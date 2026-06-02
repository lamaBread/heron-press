"""검색 인덱스 구축 (BM25, v4 포맷) + Python↔PHP 토크나이저 패리티 테스트.

v0.6.0 변경 — 본문 색인 제거 + 메타데이터 3-필드 색인 + OPcache 친화 정적 배열:
  (a) 인덱스 포맷 v4. 색인 대상이 (title, description, tags) 세 필드. 본문
      (body) 은 더 이상 토큰화·역색인 되지 않는다. 본문 평문은 docs[] 의
      `body_snippet` 으로 보존되며 *검색 결과 스니펫 추출에만* 사용된다.
  (b) 인덱스가 `dist/search.php` 안에 PHP 정적 배열 리터럴로 인라인된다.
      별도 `search-index.json` 파일 없음. 런타임에 `json_decode` 비용이
      0 이며, PHP OPcache 가 search.php 의 바이트코드를 캐시하면 인덱스도
      메모리에 상주한다. 결정적인 직렬화 (`php_array_literal`) 로 같은 입력
      → 같은 PHP 파일 바이트 시퀀스를 보장.
  (c) BM25 가중치 — title 의 매직 ×5 가 v0.5.x 의 ×3 으로 줄었던 흐름을
      이어, description / tags 도 본문 대비 가중치를 따로 둔다. tags 는
      author 가 직접 적은 정확한 주제어이므로 phrase 부스트가 강하다.
  (d) noindex 글 제외. v0.5.x 까지는 본문 검색이 핵심이라 noindex 글도 본문
      매치는 노출됐는데, 메타데이터 색인으로 좁히는 김에 noindex (= 검색
      엔진 미노출 의도) 글은 자체 검색에서도 빼는 게 일관적이다.
  (e) v0.5.x 의 phrase 부스트 (원본 쿼리 substring 매치) 가 세 필드 각각에
      대해 작동. tags 는 substring 이 아니라 *전체 일치* 시 부스트 (tag 가
      이미 짧은 단일 단어라 substring 매치는 항상 성립하므로 의미 약화 방지).

인덱스 포맷 v4 (Python dict — PHP 직렬화 시 동일 구조):
  {
    "version": 4,
    "params": {"k1_title","b_title","k1_desc","b_desc","k1_tags","b_tags",
               "w_title","w_desc","w_tags",
               "phrase_boost_title","phrase_boost_desc","phrase_boost_tags"},
    "stats":  {"N","avgdl_title","avgdl_desc","avgdl_tags"},
    "docs":   [{"slug","title","date","category","category_slug",
                "description","tags","body_snippet",
                "dl_title","dl_desc","dl_tags"}, ...],
    "categories":     {"<slug>": "<folder_name>", ...},
    "df_title":       {"<token>": <int>, ...},
    "df_desc":        {"<token>": <int>, ...},
    "df_tags":        {"<token>": <int>, ...},
    "tf_title":       {"<token>": [[doc_id, tf], ...]},
    "tf_desc":        {"<token>": [[doc_id, tf], ...]},
    "tf_tags":        {"<token>": [[doc_id, tf], ...]},
  }

v0.4.0 → v0.5.0 → v0.6.0 흐름:
  - v0.4.x: 단순 TF 합산, ×5 제목 부스트, 본문 토큰 색인.
  - v0.5.0: BM25 도입 (필드별 IDF / TF 포화 / 길이 정규화). 본문 + 제목.
  - v0.6.0: 본문 색인 폐기 → 메타데이터 3-필드 색인 + 정적 PHP 인라인 인덱스.
"""
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

from . import i18n  # v1.9.2: 토크나이저 패리티 진단 라인을 도구 언어로 (전역 t()).


_SEARCH_LATIN_RE = re.compile(r'[a-z0-9]+')
_SEARCH_HAN_RE = re.compile(r'[가-힣]+')


def search_tokenize(text: str) -> list:
    """build.py / search.php 가 동일하게 사용하는 토크나이저.

    v0.4.0 규칙 (v0.5.0 / v0.6.0 변경 없음):
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
    스니펫 노이즈가 되는 것을 방지.
    """
    s = _STYLE_SCRIPT_RE.sub(' ', html or '')
    s = _TAG_STRIP_RE.sub(' ', s)
    s = _WS_COLLAPSE_RE.sub(' ', s).strip()
    return s


# ════════════════════════════════════════════════════════════════
# BM25 hyperparameters  (v0.6.0)
# ════════════════════════════════════════════════════════════════
#
# 세 필드 (title / description / tags) 각각에 독립적인 BM25 파라미터.
#
#   title       : 짧고 의미 비중이 크다. b 낮춤 (길이 정규화 약화),
#                 k1 낮춤 (첫 TF 보상 크게).
#   description : 짧은 문장 한두 줄. 본문 대용은 아니지만 길이 정규화는
#                 유지. k1 / b 는 본문에 쓰던 (1.5, 0.75) 그대로.
#   tags        : 토큰 모음. 길이 정규화를 거의 끄고 (b 낮춤) 정확 매치를
#                 강하게 보상.
#
# w_*    : 두 필드 점수를 합칠 때 각각의 가중치. tags > description 은
#          author 가 직접 적은 주제어가 본문에서 추출한 description 보다
#          신뢰도가 높다는 판단. title > tags 는 제목이 글의 정체성을
#          가장 압축적으로 표현한다는 통념.
#
# phrase_boost_*  : 곱셈 부스트. title / description 은 substring 매치,
#                   tags 는 *전체 일치 (= 한 tag 가 쿼리와 통째로 같음)*
#                   에서만 부스트 (짧은 tag 의 substring 은 노이즈).

BM25_PARAMS = {
    'k1_title': 1.2,
    'b_title': 0.5,
    'k1_desc': 1.5,
    'b_desc': 0.75,
    'k1_tags': 1.2,
    'b_tags': 0.3,
    'w_title': 3.0,
    'w_desc': 1.5,
    'w_tags': 2.0,
    'phrase_boost_title': 2.0,
    'phrase_boost_desc': 1.5,
    'phrase_boost_tags': 2.5,
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

    avgdl <= 0 (이 필드에 토큰이 한 글에도 없을 때) 또는 N <= 0 (빈 코퍼스)
    이면 0 반환. tokens 의 중복은 그대로 가산 (쿼리 측 BM25-Q 가중치 별도
    도입 없음).
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
    """완전한 BM25 점수 (title·desc·tags 합) + phrase 부스트.

    Python 참조 구현. tests/test_bm25.py 가 이를 호출해 알고리즘을 검증.
    런타임 (PHP) 의 search_bm25.php 도 동일 공식.

    index : build_search_index() 반환값 (v4).
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

    def _tf_for_doc(tf_postings, did):
        out = {}
        for tok, posting in tf_postings.items():
            for entry in posting:
                if entry[0] == did:
                    out[tok] = entry[1]
                    break
        return out

    tf_title_doc = _tf_for_doc(index['tf_title'], doc_id)
    tf_desc_doc = _tf_for_doc(index['tf_desc'], doc_id)
    tf_tags_doc = _tf_for_doc(index['tf_tags'], doc_id)

    score_title = bm25_field_score(
        tokens, index['df_title'], tf_title_doc,
        doc['dl_title'], stats['avgdl_title'], N,
        p['k1_title'], p['b_title'],
    )
    score_desc = bm25_field_score(
        tokens, index['df_desc'], tf_desc_doc,
        doc['dl_desc'], stats['avgdl_desc'], N,
        p['k1_desc'], p['b_desc'],
    )
    score_tags = bm25_field_score(
        tokens, index['df_tags'], tf_tags_doc,
        doc['dl_tags'], stats['avgdl_tags'], N,
        p['k1_tags'], p['b_tags'],
    )

    total = (p['w_title'] * score_title
             + p['w_desc'] * score_desc
             + p['w_tags'] * score_tags)
    if total <= 0:
        return 0.0

    # Phrase 부스트.
    # title / desc : 원본 쿼리 (lowercase, trim) 가 substring 매치되면 곱셈.
    # tags         : tag 한 개와 쿼리 (lowercase, trim) 가 완전히 같으면 곱셈.
    q_lower = query.strip().lower()
    if len(q_lower) >= 2:
        if q_lower in (doc.get('title') or '').lower():
            total *= p['phrase_boost_title']
        if q_lower in (doc.get('description') or '').lower():
            total *= p['phrase_boost_desc']
        for tag in (doc.get('tags') or []):
            if (tag or '').lower() == q_lower:
                total *= p['phrase_boost_tags']
                break

    return total


# ════════════════════════════════════════════════════════════════
# Python ↔ PHP tokenizer parity test  (unchanged from v0.4.x)
# ════════════════════════════════════════════════════════════════

PARITY_FIXTURES = [
    '',
    ' ',
    'Hello',
    'HELLO world',
    'your-domain.com',
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


def _parity_cache_key(scripts_dir: Path, runtime_dir: Path,
                      php_version: str) -> str:
    """parity cache key — search.py + search_tokenize.php + PHP -v 합성 sha256.

    v1.3.0 (E 항목): 토크나이저 코드(Py/PHP 양쪽) 와 PHP 바이너리 버전이 모두
    같으면 parity 결과가 같다는 사실을 활용. 두 파일 + php_version 첫 줄을
    바이트열로 합쳐 sha256 — 어느 하나 바뀌면 캐시 자동 무효화.

    v1.5.1: search_tokenize.php 는 v1.5.0 부터 system/runtime/ 에 있으므로
    인자명을 templates_dir → runtime_dir 로 정정 (호출은 위치 인자라 동작 불변).
    """
    h = hashlib.sha256()
    for p in (scripts_dir / 'search.py',
              runtime_dir / 'search_tokenize.php'):
        if p.exists():
            h.update(p.read_bytes())
    h.update(php_version.encode('utf-8'))
    return h.hexdigest()


def run_parity_test(runtime_dir: Path, php_bin: str, warn_fn, die_fn,
                    *, cache_dir: Path = None,
                    scripts_dir: Path = None) -> bool:
    """fixture 입력에 대해 Py↔PHP 토크나이저 출력 동등성 검증.

    v1.3.0 (E 항목): cache_dir + scripts_dir 가 주어지면 결과를
    `<cache_dir>/parity.json` 에 캐시. 같은 코드 + 같은 PHP 버전이면 다음
    빌드에서 18 fixture subprocess 호출 (~3s) 건너뛴다. 캐시 파일 누락/손상
    또는 cache_dir 미전달 시 (--no-cache) 매 빌드 풀 검증.

    v1.5.1: 첫 인자명을 templates_dir → runtime_dir 로 정정. search_tokenize.php
    는 v1.5.0 부터 system/runtime/ 에 있고 builder 가 self.runtime_dir 을
    위치 인자로 넘긴다 (동작 불변, 이름만 실제 출처와 일치).
    """
    tokenizer_php = runtime_dir / 'search_tokenize.php'
    if not tokenizer_php.exists():
        die_fn(f'search_tokenize.php not found at {tokenizer_php}')

    try:
        probe = subprocess.run(
            [php_bin, '-v'],
            capture_output=True,
            timeout=10,
        )
        if probe.returncode != 0:
            warn_fn(i18n.t('build.parity.php_missing'))
            return False
    except (FileNotFoundError, subprocess.TimeoutExpired):
        warn_fn('PHP not available — skipping tokenizer parity test.')
        return False

    php_version = ''
    if probe.stdout:
        first_line = probe.stdout.decode('utf-8', errors='replace').splitlines()
        if first_line:
            php_version = first_line[0]

    # 캐시 hit 체크 — cache_dir 와 scripts_dir 가 같이 주어진 경우만.
    key = None
    if cache_dir is not None and scripts_dir is not None:
        try:
            key = _parity_cache_key(scripts_dir, runtime_dir, php_version)
            cache_file = cache_dir / 'parity.json'
            if cache_file.exists():
                data = json.loads(cache_file.read_text(encoding='utf-8'))
                if data.get('key') == key and data.get('passed') is True:
                    print(i18n.t('build.parity.cached', n=len(PARITY_FIXTURES)))
                    return True
        except (OSError, json.JSONDecodeError):
            pass  # 캐시 깨졌으면 그냥 실행 후 새로 저장.

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

    # 통과 → 캐시 저장.
    if cache_dir is not None and key is not None:
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            (cache_dir / 'parity.json').write_text(
                json.dumps({'key': key, 'passed': True, 'php': php_version},
                           ensure_ascii=False, sort_keys=True),
                encoding='utf-8',
            )
        except OSError:
            pass  # 캐시 쓰기 실패는 빌드 실패가 아님.

    print(i18n.t('build.parity.ok', n=len(PARITY_FIXTURES)))
    return True


# ════════════════════════════════════════════════════════════════
# Search index build  (v0.6.0: BM25 v4 format — meta-only)
# ════════════════════════════════════════════════════════════════

# 본문 평문에서 스니펫용으로 보존할 최대 길이 (글자, UTF-8 코드포인트 단위).
# 너무 길면 search.php 가 비대해진다. 너무 짧으면 매치 밀도 스니펫의
# 후보 윈도우가 좁아진다. 본 SSG 의 글은 보통 1-3KB 평문이라 1500 으로
# 충분. 그 이상 글은 앞 1500 자만 스니펫 후보 — 검색 결과 미리보기는
# 글의 *어느 위치든* 흥미로운 한 구간이 보이면 충분하다는 가정.
BODY_SNIPPET_MAX_CHARS = 1500


def _truncate_snippet(plain: str, limit: int = BODY_SNIPPET_MAX_CHARS) -> str:
    """본문 평문 → 스니펫 후보 (앞 limit 자). 결정성 보장."""
    if not plain:
        return ''
    if len(plain) <= limit:
        return plain
    return plain[:limit]


def build_search_index(articles, rendered_bodies, categories,
                       top_category_for_article) -> dict:
    """BM25 검색 인덱스 dict 생성. dist 쓰기는 호출자가 수행.

    포맷 v4 (이 모듈 docstring 참조). v0.5.x 의 v3 와 비호환:
      - 색인 필드가 body → (title, description, tags) 로 변경
      - 본문 평문은 docs[].body_snippet 으로 보존 (검색 결과 스니펫 추출용,
        BM25 점수 계산에는 사용 안 함)
      - noindex 글은 색인에서 제외 (sitemap / feed 와 일관)
      - tags 필드 색인: 각 tag 를 search_tokenize 한 모든 토큰의 합집합

    description / tags 가 비어 있는 글도 색인된다 (해당 필드 dl=0, tf 없음,
    BM25 점수는 자연스럽게 0). title 은 모든 글에 필수이므로 최소한 title
    매치는 가능.
    """
    docs = []
    title_tf_map = {}   # token → {doc_id: tf}
    desc_tf_map = {}
    tags_tf_map = {}
    title_dls = []
    desc_dls = []
    tags_dls = []

    # noindex 글은 제외 (v0.6.0). 정렬은 slug 사전식으로 결정적.
    indexable = [a for a in articles if not a.meta.noindex]
    sorted_articles = sorted(indexable, key=lambda a: a.meta.slug)

    for doc_id, article in enumerate(sorted_articles):
        m = article.meta
        body_plain = rendered_bodies.get(m.slug, '')

        top_cat_obj = top_category_for_article(article)
        top_cat_name = top_cat_obj.folder_name if top_cat_obj else ''
        top_cat_slug = top_cat_obj.slug if top_cat_obj else ''

        # description: None / '' 모두 빈 문자열로 정규화. (BuildReport 가
        # 누락을 별도로 기록하므로 인덱스 측에서는 같은 빈 색인으로 취급.)
        description = m.seo.description or ''

        # tags: 순서 보존, 빈 문자열 제거. 토큰화는 join 후 한 번에.
        tags = [t for t in (m.tags or []) if t]
        tags_joined = ' '.join(tags)

        title_tokens = search_tokenize(m.title)
        desc_tokens = search_tokenize(description)
        tags_tokens = search_tokenize(tags_joined)

        dl_title = len(title_tokens)
        dl_desc = len(desc_tokens)
        dl_tags = len(tags_tokens)
        title_dls.append(dl_title)
        desc_dls.append(dl_desc)
        tags_dls.append(dl_tags)

        docs.append({
            'slug': m.slug,
            'title': m.title,
            'date': m.date,
            'category': top_cat_name,
            'category_slug': top_cat_slug,
            'description': description,
            'tags': tags,
            'body_snippet': _truncate_snippet(body_plain),
            'dl_title': dl_title,
            'dl_desc': dl_desc,
            'dl_tags': dl_tags,
        })

        for tf_map, tokens in (
            (title_tf_map, title_tokens),
            (desc_tf_map, desc_tokens),
            (tags_tf_map, tags_tokens),
        ):
            field_tf = {}
            for t in tokens:
                field_tf[t] = field_tf.get(t, 0) + 1
            for t, tf in field_tf.items():
                tf_map.setdefault(t, {})[doc_id] = tf

    N = len(docs)

    def _avgdl(dls):
        # 토큰이 한 글에도 없는 필드 (e.g. 모든 글이 tags 비어있음) → 0.
        # BM25 가 avgdl<=0 을 0 점수로 처리하므로 안전.
        positive = [d for d in dls if d > 0]
        return (sum(positive) / len(positive)) if positive else 0.0

    avgdl_title = _avgdl(title_dls)
    avgdl_desc = _avgdl(desc_dls)
    avgdl_tags = _avgdl(tags_dls)

    df_title = {tok: len(post) for tok, post in title_tf_map.items()}
    df_desc = {tok: len(post) for tok, post in desc_tf_map.items()}
    df_tags = {tok: len(post) for tok, post in tags_tf_map.items()}

    def compact(idx):
        # 결정성: 토큰 정렬 + posting 의 doc_id 정렬.
        return {
            tok: [[d, posting[d]] for d in sorted(posting.keys())]
            for tok, posting in sorted(idx.items())
        }

    categories_map = {
        cat.slug: cat.folder_name
        for path_tuple, cat in categories.items()
        if len(path_tuple) == 1
    }
    # 결정성: 카테고리 slug 정렬.
    categories_map = dict(sorted(categories_map.items()))

    df_title = dict(sorted(df_title.items()))
    df_desc = dict(sorted(df_desc.items()))
    df_tags = dict(sorted(df_tags.items()))

    return {
        'version': 4,
        'params': dict(BM25_PARAMS),
        'stats': {
            'N': N,
            'avgdl_title': avgdl_title,
            'avgdl_desc': avgdl_desc,
            'avgdl_tags': avgdl_tags,
        },
        'docs': docs,
        'categories': categories_map,
        'df_title': df_title,
        'df_desc': df_desc,
        'df_tags': df_tags,
        'tf_title': compact(title_tf_map),
        'tf_desc': compact(desc_tf_map),
        'tf_tags': compact(tags_tf_map),
    }


# ════════════════════════════════════════════════════════════════
# PHP 배열 리터럴 직렬화  (v0.6.0)
# ════════════════════════════════════════════════════════════════
#
# 인덱스 dict 를 PHP 의 `array(...)` 또는 `[...]` 리터럴로 직렬화한다.
# 산출물은 dist/search.php 안에 인라인되어 OPcache 가 바이트코드 단계에서
# 캐시한다 — JSON 파싱 비용 0, 디스크 IO 0 (OPcache hit 시).
#
# 결정성 요구사항 — 같은 입력 → 같은 PHP 텍스트:
#   - dict 키 순서는 호출자가 보장 (build_search_index 가 sorted dict 사용)
#   - float 는 repr 사용 — Python 3 의 repr 는 round-trip 보장 + 결정적
#   - 문자열 escape: ' → \\', \ → \\\\  (PHP single-quoted 규칙)
#

def _php_str(s: str) -> str:
    """Python str → PHP single-quoted 리터럴.

    PHP single-quoted 는 `\\\\` 와 `\\'` 두 escape 만 인식 (그 외 \\는 그대로).
    UTF-8 문자열 그대로 둠 — PHP 7+ 가 UTF-8 소스를 정상 처리한다.
    """
    s = s.replace('\\', '\\\\').replace("'", "\\'")
    return f"'{s}'"


def _php_val(v) -> str:
    """임의 Python 값 → PHP 리터럴 표현."""
    if v is None:
        return 'null'
    if v is True:
        return 'true'
    if v is False:
        return 'false'
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        # NaN / Inf 는 인덱스 산출에 등장하지 않는다고 가정.
        # Python repr 는 round-trip 보장 + 길이 최소 + 결정적.
        if v != v:  # NaN
            return 'NAN'
        if v == float('inf'):
            return 'INF'
        if v == float('-inf'):
            return '-INF'
        return repr(v)
    if isinstance(v, str):
        return _php_str(v)
    if isinstance(v, list):
        return _php_array_list(v)
    if isinstance(v, dict):
        return _php_array_assoc(v)
    # 기타 타입은 str() 폴백. 정상 코드 경로에서 등장 안 함.
    return _php_str(str(v))


def _php_array_list(lst: list) -> str:
    if not lst:
        return '[]'
    inner = ','.join(_php_val(x) for x in lst)
    return f'[{inner}]'


def _php_array_assoc(d: dict) -> str:
    if not d:
        return '[]'
    parts = []
    for k, v in d.items():
        # 키는 문자열 또는 정수.
        if isinstance(k, int):
            key_lit = str(k)
        else:
            key_lit = _php_str(str(k))
        parts.append(f'{key_lit}=>{_php_val(v)}')
    return '[' + ','.join(parts) + ']'


def php_array_literal(value) -> str:
    """인덱스 dict 등의 Python 값을 PHP 리터럴 문자열로 변환.

    공백 / 줄바꿈 없음 (compact) — search.php 안에 단 한 줄로 박아넣어
    OPcache 파싱 단계 최소화. 사람이 읽을 일 없음.
    """
    return _php_val(value)

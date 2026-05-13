"""검색 인덱스 구축 + Python↔PHP 토크나이저 패리티 테스트.

v0.4.0 변경:
  (a) 한국어 토큰화 규칙 강화. 한 글자 한글은 인덱싱하지 않고,
      bigram (2-gram) 만 토큰으로 인정. 한 글자 쿼리는 빈 토큰 셋을 만들어
      자연스럽게 결과 없음으로 떨어진다.
  (b) 본문 5000자 절단 제거. 글의 전체 평문이 인덱스/스니펫 후보가 된다.
  (c) build.py 가 fixture 입력에 대해 Py↔PHP 출력 동등성을 빌드마다 검증.
      어긋나면 빌드 실패. parsers 가 PHP 파일을 직접 require_once 하므로
      한쪽만 수정해도 패리티가 깨지면 즉시 발견.

인덱스 포맷 v2 그대로 (docs[], categories, index, title_index).
v0.5.0 이후에 IDF 가중치, posting 분할, 클라이언트 색인 등을 검토.
"""
import json
import re
import subprocess
from pathlib import Path


_SEARCH_LATIN_RE = re.compile(r'[a-z0-9]+')
_SEARCH_HAN_RE = re.compile(r'[가-힣]+')


def search_tokenize(text: str) -> list:
    """build.py / search.php 가 동일하게 사용하는 토크나이저.

    v0.4.0 규칙:
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
# Python ↔ PHP parity test
# ════════════════════════════════════════════════════════════════

# fixture 의 의도:
#   - 영문 단어, 숫자, 영숫자 혼합
#   - 한글 1글자 (인덱싱 안 됨)
#   - 한글 2글자, 3글자 (bigram 1개, 2개)
#   - 영문+한글 혼합
#   - 구두점, 특수문자 (분리자 동작)
#   - 빈 문자열
#   - 좌/우 공백
#   - 대문자 정규화
#   - 한자, 일본어 (가-힣 범위 밖 — 토큰 0개여야 함)
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
    """fixture 입력에 대해 Py↔PHP 토크나이저 출력 동등성 검증.

    PHP 가 없으면 _warn 후 True 를 반환 (Builder 가 검색 비활성화 경로로
    빠지든, builtin 파서 환경에서 검색 인덱스만 만든 후 PHP 부재로 검색
    엔드포인트가 실패하든 책임은 호출자에게).

    동등성 어긋남이 있으면 die_fn 호출 (빌드 실패).
    """
    tokenizer_php = templates_dir / 'search_tokenize.php'
    if not tokenizer_php.exists():
        die_fn(f'search_tokenize.php not found at {tokenizer_php}')

    # PHP 부재 감지
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
# Search index build  (v0.4.0: full body, no length cap)
# ════════════════════════════════════════════════════════════════

def build_search_index(articles, rendered_bodies, categories,
                       top_category_for_article) -> dict:
    """검색 인덱스 dict 생성. dist 쓰기는 호출자가 수행.

    docs[i].body 는 평문 본문 전체 (v0.4.0: 길이 제한 없음).
    스니펫 추출은 search.php 측에서 수행하므로 본문이 길어지면 응답 시
    조금 더 작업이 늘지만, 운영 글 수가 ≤ 수십 건이라 무시 가능.
    """
    docs = []
    body_index = {}
    title_index = {}

    sorted_articles = sorted(articles, key=lambda a: a.meta.slug)

    for doc_id, article in enumerate(sorted_articles):
        m = article.meta
        body_plain = rendered_bodies.get(m.slug, '')

        top_cat_obj = top_category_for_article(article)
        top_cat_name = top_cat_obj.folder_name if top_cat_obj else ''
        top_cat_slug = top_cat_obj.slug if top_cat_obj else ''

        docs.append({
            'slug': m.slug,
            'title': m.title,
            'date': m.date,
            'category': top_cat_name,
            'category_slug': top_cat_slug,
            'body': body_plain,
        })

        body_tf = {}
        for t in search_tokenize(body_plain):
            body_tf[t] = body_tf.get(t, 0) + 1
        for t, tf in body_tf.items():
            body_index.setdefault(t, {})[doc_id] = tf

        title_tf = {}
        for t in search_tokenize(m.title):
            title_tf[t] = title_tf.get(t, 0) + 1
        for t, tf in title_tf.items():
            title_index.setdefault(t, {})[doc_id] = tf

    def compact(idx):
        return {tok: [[d, tf] for d, tf in posting.items()]
                for tok, posting in idx.items()}

    categories_map = {
        cat.slug: cat.folder_name
        for path_tuple, cat in categories.items()
        if len(path_tuple) == 1
    }

    return {
        'version': 2,
        'docs': docs,
        'categories': categories_map,
        'index': compact(body_index),
        'title_index': compact(title_index),
    }

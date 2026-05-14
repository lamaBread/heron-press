<?php
declare(strict_types=1);

// ════════════════════════════════════════════════════════════════
// search_bm25.php — siheonlee.com BM25 점수 모듈 (v0.5.0)
// ════════════════════════════════════════════════════════════════
//
// search.php 가 require_once 로 include 하는 점수 계산 라이브러리.
// 인덱스 포맷 v3 (scripts/search.py 의 build_search_index() 참조) 위에서
// Okapi BM25 + 필드 가중치 + phrase 부스트 를 계산한다.
//
// Python 참조 구현 (scripts/search.py 의 bm25_score()) 과 동일 공식.
// 회귀 방지는 tests/test_bm25.py 가 담당.

require_once __DIR__ . '/search_tokenize.php';


/**
 * Okapi BM25 IDF (Robertson-Spärck Jones, +1 smoothing).
 *   IDF(t) = ln( (N - df + 0.5) / (df + 0.5) + 1 )
 */
function bm25_idf(int $N, int $df): float {
    return log((($N - $df + 0.5) / ($df + 0.5)) + 1.0);
}

/**
 * 한 필드의 BM25 점수.
 *
 * @param array $tokens   쿼리 토큰 (중복 허용)
 * @param array $df_map   {token: df}
 * @param array $tf_map   해당 문서의 {token: tf}
 * @param int   $dl       해당 문서의 이 필드 길이 (토큰 수)
 * @param float $avgdl    전체의 이 필드 평균 길이
 * @param int   $N        전체 문서 수
 * @param float $k1
 * @param float $b
 */
function bm25_field_score(array $tokens, array $df_map, array $tf_map,
                          int $dl, float $avgdl, int $N,
                          float $k1, float $b): float {
    if ($N <= 0 || $avgdl <= 0.0) return 0.0;
    $score = 0.0;
    $norm = 1.0 - $b + $b * ($dl / $avgdl);
    foreach ($tokens as $t) {
        $df = $df_map[$t] ?? 0;
        if ($df <= 0) continue;
        $tf = $tf_map[$t] ?? 0;
        if ($tf <= 0) continue;
        $idf = bm25_idf($N, $df);
        $score += $idf * ($tf * ($k1 + 1.0)) / ($tf + $k1 * $norm);
    }
    return $score;
}

/**
 * 전체 코퍼스를 채점하고 (score 내림차순) 결과 배열을 반환.
 *
 * 인덱스 posting 을 한 번씩 순회하면서 필드별 점수를 누적 — bm25_score()
 * (참조 구현) 와 수식은 동일하지만 단일 문서 lookup 대신 posting-walk 으로
 * 런타임 효율을 높인다.
 *
 * @param array       $index    포맷 v3 인덱스 dict
 * @param string      $query    원본 사용자 쿼리 (phrase 부스트용)
 * @param string|null $cat_slug 카테고리 스코프 (null = 전체)
 * @return array  [[doc_id, score, doc], ...]   score 내림차순.
 */
function bm25_search(array $index, string $query, ?string $cat_slug): array {
    $tokens = search_tokenize($query);
    if (empty($tokens)) return [];

    $stats   = $index['stats'];
    $params  = $index['params'];
    $docs    = $index['docs'];
    $N       = (int)$stats['N'];
    $avgdl_b = (float)$stats['avgdl_body'];
    $avgdl_t = (float)$stats['avgdl_title'];

    $k1_b = (float)$params['k1_body'];
    $b_b  = (float)$params['b_body'];
    $k1_t = (float)$params['k1_title'];
    $b_t  = (float)$params['b_title'];
    $w_t  = (float)$params['w_title'];
    $pb_b = (float)$params['phrase_boost_body'];
    $pb_t = (float)$params['phrase_boost_title'];

    $df_body  = $index['df_body']  ?? [];
    $df_title = $index['df_title'] ?? [];
    $tf_body  = $index['tf_body']  ?? [];
    $tf_title = $index['tf_title'] ?? [];

    // 카테고리 스코프 — 허용 doc_id 집합 (성능 단순화: doc_id 인덱스로).
    $cat_filter = null;
    if ($cat_slug !== null && $cat_slug !== '') {
        $cat_filter = [];
        foreach ($docs as $i => $doc) {
            if (($doc['category_slug'] ?? '') === $cat_slug) {
                $cat_filter[$i] = true;
            }
        }
    }

    // 필드별 분자/분모 (정확히 말하면 분자) 누적. norm 은 dl 에 의존하므로
    // 후처리 단계에서 적용. 여기서는 토큰별 idf 와 tf 를 들고 가서 식 전개.
    //
    // 메모리 최적화: 점수 누적은 마지막에 dl 을 곱해 한 번에 정리.
    // 단, 각 토큰의 idf 가 다르므로 토큰별로 누적해야 한다. 단순화를 위해
    // 토큰 단위 누적 후 합산 (작은 N 에 최적화).

    $scores_body  = [];   // doc_id → score
    $scores_title = [];

    foreach ($tokens as $t) {
        if (isset($tf_body[$t]) && isset($df_body[$t])) {
            $idf = bm25_idf($N, (int)$df_body[$t]);
            foreach ($tf_body[$t] as $entry) {
                $d  = (int)$entry[0];
                $tf = (int)$entry[1];
                if ($cat_filter !== null && !isset($cat_filter[$d])) continue;
                $dl  = (int)($docs[$d]['dl_body'] ?? 0);
                $norm = 1.0 - $b_b + $b_b * ($dl / $avgdl_b);
                $scores_body[$d] = ($scores_body[$d] ?? 0.0)
                    + $idf * ($tf * ($k1_b + 1.0)) / ($tf + $k1_b * $norm);
            }
        }
        if (isset($tf_title[$t]) && isset($df_title[$t])) {
            $idf = bm25_idf($N, (int)$df_title[$t]);
            foreach ($tf_title[$t] as $entry) {
                $d  = (int)$entry[0];
                $tf = (int)$entry[1];
                if ($cat_filter !== null && !isset($cat_filter[$d])) continue;
                $dl  = (int)($docs[$d]['dl_title'] ?? 0);
                $norm = ($avgdl_t > 0)
                    ? 1.0 - $b_t + $b_t * ($dl / $avgdl_t)
                    : 1.0;
                $scores_title[$d] = ($scores_title[$d] ?? 0.0)
                    + $idf * ($tf * ($k1_t + 1.0)) / ($tf + $k1_t * $norm);
            }
        }
    }

    // 합산 + phrase 부스트
    $q_lower = mb_strtolower(trim($query), 'UTF-8');
    $apply_phrase = mb_strlen($q_lower, 'UTF-8') >= 2;

    $totals = [];
    $all_docs = $scores_body + $scores_title;   // 키 합집합 — 값은 _body 우선
    foreach (array_keys($all_docs) as $d) {
        $total = ($scores_body[$d] ?? 0.0) + $w_t * ($scores_title[$d] ?? 0.0);
        if ($total <= 0.0) continue;
        if ($apply_phrase) {
            $doc = $docs[$d];
            $body_lower  = mb_strtolower((string)($doc['body']  ?? ''), 'UTF-8');
            $title_lower = mb_strtolower((string)($doc['title'] ?? ''), 'UTF-8');
            if ($q_lower !== '' && mb_strpos($body_lower,  $q_lower, 0, 'UTF-8') !== false) {
                $total *= $pb_b;
            }
            if ($q_lower !== '' && mb_strpos($title_lower, $q_lower, 0, 'UTF-8') !== false) {
                $total *= $pb_t;
            }
        }
        $totals[$d] = $total;
    }

    arsort($totals);

    $results = [];
    foreach ($totals as $d => $score) {
        $results[] = [$d, $score, $docs[$d]];
    }
    return $results;
}

/**
 * 매치 밀도 기반 스니펫.
 *
 * 평문 본문에서 토큰 매치가 가장 밀집된 윈도우를 선정해 그 구간을 추출.
 * 매치가 전혀 없으면 첫 매치 위치 (v0.4.x 폴백) 또는 본문 처음.
 *
 * @param string $body    평문 본문
 * @param string $query   원본 쿼리
 * @param int    $window  스니펫 길이 (글자 수, UTF-8 단위)
 */
function snippet_density(string $body, string $query, int $window = 80): string {
    if ($body === '' || $query === '') return '';

    $body_lower = mb_strtolower($body, 'UTF-8');
    $body_len   = mb_strlen($body, 'UTF-8');

    // 후보 매치 위치들 (원본 쿼리 substring + 각 토큰 substring) 수집.
    $positions = [];
    $q_lower = mb_strtolower(trim($query), 'UTF-8');
    $patterns = [];
    if ($q_lower !== '') $patterns[] = $q_lower;
    foreach (search_tokenize($query) as $t) {
        if ($t !== '') $patterns[] = $t;
    }
    $patterns = array_values(array_unique($patterns));

    foreach ($patterns as $p) {
        $offset = 0;
        $plen = mb_strlen($p, 'UTF-8');
        if ($plen === 0) continue;
        while (($pos = mb_strpos($body_lower, $p, $offset, 'UTF-8')) !== false) {
            $positions[] = $pos;
            $offset = $pos + max(1, $plen);
            // 안전 가드: 매치 수가 너무 많으면 중단 (밀도만 보면 됨)
            if (count($positions) > 500) break 2;
        }
    }

    if (empty($positions)) {
        // 폴백: 본문 처음
        $s = mb_substr($body, 0, $window * 2, 'UTF-8');
        return ($body_len > $window * 2) ? $s . '…' : $s;
    }

    sort($positions);

    // 슬라이딩 윈도우: 각 매치 위치에서 시작하는 [pos, pos+window) 안에
    // 들어오는 다른 매치 수를 카운트. 최대값의 윈도우를 채택.
    $best_idx = 0;
    $best_count = 0;
    $best_center = $positions[0];
    $n = count($positions);
    for ($i = 0; $i < $n; $i++) {
        $start = $positions[$i];
        $end   = $start + $window;
        $count = 0;
        for ($j = $i; $j < $n && $positions[$j] < $end; $j++) {
            $count++;
        }
        if ($count > $best_count) {
            $best_count = $count;
            $best_idx = $i;
            // 매치들의 평균 위치를 윈도우 중심 후보로
            $sum = 0;
            for ($j = $i; $j < $i + $count; $j++) $sum += $positions[$j];
            $best_center = (int)($sum / $count);
        }
    }

    // 윈도우를 best_center 주위로 정렬. 좌우 약간의 컨텍스트 확보.
    $half = (int)($window / 2);
    $start = max(0, $best_center - $half);
    $len = $window;
    if ($start + $len > $body_len) {
        $start = max(0, $body_len - $len);
    }

    $s = mb_substr($body, $start, $len, 'UTF-8');
    if ($start > 0) $s = '…' . $s;
    if ($start + $len < $body_len) $s .= '…';
    return $s;
}

/**
 * <mark> 하이라이트 — v0.4.x 의 highlight_html() 와 동일 로직 유지.
 */
function highlight_html(string $text, string $q): string {
    $escaped = htmlspecialchars($text, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
    if ($q === '') return $escaped;
    $patterns = array_unique(array_filter(
        array_merge([$q], search_tokenize($q)),
        fn($p) => $p !== ''
    ));
    usort($patterns, fn($a, $b) => mb_strlen($b, 'UTF-8') - mb_strlen($a, 'UTF-8'));
    if (empty($patterns)) return $escaped;
    $alts = array_map(
        fn($p) => preg_quote(htmlspecialchars($p, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'), '/'),
        $patterns
    );
    return preg_replace(
        '/(' . implode('|', $alts) . ')/iu',
        '<mark>$1</mark>',
        $escaped
    );
}

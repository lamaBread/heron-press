<?php
declare(strict_types=1);

// ════════════════════════════════════════════════════════════════
// search_bm25.php — siheonlee.com BM25 점수 모듈 (v0.6.0)
// ════════════════════════════════════════════════════════════════
//
// search.php 가 같은 파일에 인라인된 인덱스 ($INDEX) 위에서 호출하는 점수
// 계산 라이브러리. v0.5.x 까지는 require_once 로 분리되어 있었으나 v0.6.0
// 부터 search.php 안에 인덱스 정적 배열과 함께 인라인되어 OPcache 가
// 단일 바이트코드 단위로 캐시한다. 본 파일은 진단·테스트용으로 유지 —
// build.py 가 dist 로 복사하지 않는다.
//
// 인덱스 포맷 v4 (scripts/search.py 의 build_search_index() 참조):
//   {
//     "version": 4,
//     "params":  {k1_title,b_title,k1_desc,b_desc,k1_tags,b_tags,
//                 w_title,w_desc,w_tags,
//                 phrase_boost_title,phrase_boost_desc,phrase_boost_tags},
//     "stats":   {N, avgdl_title, avgdl_desc, avgdl_tags},
//     "docs":    [{slug,title,date,category,category_slug,
//                  description,tags,body_snippet,
//                  dl_title,dl_desc,dl_tags}, ...],
//     "categories": {<slug>: <folder_name>, ...},
//     "df_title":   {<token>: <int>, ...},
//     "df_desc":    {<token>: <int>, ...},
//     "df_tags":    {<token>: <int>, ...},
//     "tf_title":   {<token>: [[doc_id, tf], ...]},
//     "tf_desc":    {<token>: [[doc_id, tf], ...]},
//     "tf_tags":    {<token>: [[doc_id, tf], ...]}
//   }
//
// Python 참조 구현 (scripts/search.py 의 bm25_score()) 과 동일 공식. 회귀
// 방지는 tests/test_bm25.py 가 담당.

if (!function_exists('search_tokenize')) {
    require_once __DIR__ . '/search_tokenize.php';
}


/**
 * Okapi BM25 IDF (Robertson-Spärck Jones, +1 smoothing).
 *   IDF(t) = ln( (N - df + 0.5) / (df + 0.5) + 1 )
 */
if (!function_exists('bm25_idf')) {
function bm25_idf(int $N, int $df): float {
    return log((($N - $df + 0.5) / ($df + 0.5)) + 1.0);
}
}

/**
 * 한 필드의 BM25 점수.
 */
if (!function_exists('bm25_field_score')) {
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
}

/**
 * 한 필드의 BM25 점수를 코퍼스 전체에 걸쳐 누적.
 *
 * $scores 가 by-reference 매개변수 — PHP 의 array destructuring 이 reference
 * 를 보존하지 않아 spec-array 루프 패턴이 무용지물이라 함수 매개변수로
 * 명시적 reference 를 전달한다 (v0.6.0 초기 빌드의 사일런트 실패 회귀 가드).
 */
if (!function_exists('bm25_field_walk')) {
function bm25_field_walk(array $tokens, array $tf_field, array $df_field,
                         array $docs, string $dl_key, float $avgdl,
                         int $N, float $k1, float $b,
                         ?array $cat_filter, array &$scores): void {
    foreach ($tokens as $t) {
        if (!isset($tf_field[$t]) || !isset($df_field[$t])) continue;
        $idf = bm25_idf($N, (int)$df_field[$t]);
        foreach ($tf_field[$t] as $entry) {
            $d  = (int)$entry[0];
            $tf = (int)$entry[1];
            if ($cat_filter !== null && !isset($cat_filter[$d])) continue;
            $dl = (int)($docs[$d][$dl_key] ?? 0);
            $norm = 1.0 - $b + $b * ($dl / $avgdl);
            $scores[$d] = ($scores[$d] ?? 0.0)
                + $idf * ($tf * ($k1 + 1.0)) / ($tf + $k1 * $norm);
        }
    }
}
}

/**
 * 전체 코퍼스를 채점하고 (score 내림차순) 결과 배열을 반환.
 *
 * v0.6.0 변경: 세 필드 (title / description / tags) 의 가중합 + phrase 부스트.
 * body 필드는 더 이상 점수 계산에 들어가지 않는다 (스니펫 추출용으로만 보존).
 *
 * @param array       $index    포맷 v4 인덱스
 * @param string      $query    원본 사용자 쿼리 (phrase 부스트용)
 * @param string|null $cat_slug 카테고리 스코프 (null = 전체)
 * @return array  [[doc_id, score, doc], ...]   score 내림차순.
 */
if (!function_exists('bm25_search')) {
function bm25_search(array $index, string $query, ?string $cat_slug): array {
    $tokens = search_tokenize($query);
    if (empty($tokens)) return [];

    $stats   = $index['stats'];
    $params  = $index['params'];
    $docs    = $index['docs'];
    $N       = (int)$stats['N'];
    $avgdl_ti = (float)$stats['avgdl_title'];
    $avgdl_de = (float)$stats['avgdl_desc'];
    $avgdl_ta = (float)$stats['avgdl_tags'];

    $k1_ti = (float)$params['k1_title'];
    $b_ti  = (float)$params['b_title'];
    $k1_de = (float)$params['k1_desc'];
    $b_de  = (float)$params['b_desc'];
    $k1_ta = (float)$params['k1_tags'];
    $b_ta  = (float)$params['b_tags'];
    $w_ti  = (float)$params['w_title'];
    $w_de  = (float)$params['w_desc'];
    $w_ta  = (float)$params['w_tags'];
    $pb_ti = (float)$params['phrase_boost_title'];
    $pb_de = (float)$params['phrase_boost_desc'];
    $pb_ta = (float)$params['phrase_boost_tags'];

    $df_title = $index['df_title'] ?? [];
    $df_desc  = $index['df_desc']  ?? [];
    $df_tags  = $index['df_tags']  ?? [];
    $tf_title = $index['tf_title'] ?? [];
    $tf_desc  = $index['tf_desc']  ?? [];
    $tf_tags  = $index['tf_tags']  ?? [];

    // 카테고리 스코프 — 허용 doc_id 집합.
    $cat_filter = null;
    if ($cat_slug !== null && $cat_slug !== '') {
        $cat_filter = [];
        foreach ($docs as $i => $doc) {
            if (($doc['category_slug'] ?? '') === $cat_slug) {
                $cat_filter[$i] = true;
            }
        }
    }

    $scores_title = [];
    $scores_desc  = [];
    $scores_tags  = [];

    // 세 필드를 같은 패턴으로 명시적 처리. PHP destructuring 이 reference 를
    // 보존하지 않아 spec-array + foreach 로 통일하면 점수가 사라지는 사고가
    // 있었음 (v0.6.0 초기 빌드). 명시적 호출이 가장 안전.
    if ($avgdl_ti > 0.0) {
        bm25_field_walk(
            $tokens, $tf_title, $df_title, $docs, 'dl_title',
            $avgdl_ti, $N, $k1_ti, $b_ti, $cat_filter, $scores_title
        );
    }
    if ($avgdl_de > 0.0) {
        bm25_field_walk(
            $tokens, $tf_desc, $df_desc, $docs, 'dl_desc',
            $avgdl_de, $N, $k1_de, $b_de, $cat_filter, $scores_desc
        );
    }
    if ($avgdl_ta > 0.0) {
        bm25_field_walk(
            $tokens, $tf_tags, $df_tags, $docs, 'dl_tags',
            $avgdl_ta, $N, $k1_ta, $b_ta, $cat_filter, $scores_tags
        );
    }

    // 합산 + phrase 부스트
    $q_lower = mb_strtolower(trim($query), 'UTF-8');
    $apply_phrase = mb_strlen($q_lower, 'UTF-8') >= 2;

    // 키 합집합 — `+` 연산자는 좌측 우선이지만, 키 존재 여부만 보기 때문에
    // 어느 쪽의 값을 채택하든 무관 (이후 합산에서 따로 더한다).
    $totals = [];
    foreach (($scores_title + $scores_desc + $scores_tags) as $d => $_unused) {
        $total = $w_ti * ($scores_title[$d] ?? 0.0)
               + $w_de * ($scores_desc[$d]  ?? 0.0)
               + $w_ta * ($scores_tags[$d]  ?? 0.0);
        if ($total <= 0.0) continue;
        if ($apply_phrase) {
            $doc = $docs[$d];
            $title_lower = mb_strtolower((string)($doc['title']       ?? ''), 'UTF-8');
            $desc_lower  = mb_strtolower((string)($doc['description'] ?? ''), 'UTF-8');
            if ($q_lower !== '' && mb_strpos($title_lower, $q_lower, 0, 'UTF-8') !== false) {
                $total *= $pb_ti;
            }
            if ($q_lower !== '' && mb_strpos($desc_lower,  $q_lower, 0, 'UTF-8') !== false) {
                $total *= $pb_de;
            }
            // tags: 정확 일치만 부스트 (substring 노이즈 방지).
            foreach (($doc['tags'] ?? []) as $tag) {
                if (mb_strtolower((string)$tag, 'UTF-8') === $q_lower) {
                    $total *= $pb_ta;
                    break;
                }
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
}

/**
 * 매치 밀도 기반 스니펫.
 *
 * v0.6.0: 본문이 더 이상 색인되지 않지만, docs[].body_snippet 에 본문 앞
 * BODY_SNIPPET_MAX_CHARS 자가 보존되어 있어 스니펫 추출은 그대로 가능하다.
 *
 * @param string $body    평문 본문 (= docs[].body_snippet)
 * @param string $query   원본 쿼리
 * @param int    $window  스니펫 길이 (글자 수, UTF-8 단위)
 */
if (!function_exists('snippet_density')) {
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
            if (count($positions) > 500) break 2;
        }
    }

    if (empty($positions)) {
        // 폴백: 본문 처음
        $s = mb_substr($body, 0, $window * 2, 'UTF-8');
        return ($body_len > $window * 2) ? $s . '…' : $s;
    }

    sort($positions);

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
            $sum = 0;
            for ($j = $i; $j < $i + $count; $j++) $sum += $positions[$j];
            $best_center = (int)($sum / $count);
        }
    }

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
}

/**
 * <mark> 하이라이트.
 */
if (!function_exists('highlight_html')) {
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
}

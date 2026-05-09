<?php
declare(strict_types=1);

// ════════════════════════════════════════════════════════════════
// search.php — siheonlee.com 검색 엔드포인트  (v0.3.2)
// ════════════════════════════════════════════════════════════════
//
// 빌드 시 build.py 가 dist/ 로 복사하면서 {{...}} placeholder 만 치환.
// 런타임에 dist/search-index.json (build.py 가 같은 빌드에서 생성) 을
// 읽어 한글 bigram + 영문 토큰 역색인 위에서 검색을 수행한다.
//
// v0.3.2 차이점:
//   - ?cat=<slug> 으로 카테고리 스코프 검색 지원.
//     cat 미지정 → 전체 글 대상.
//     cat 지정    → docs[i].category_slug == cat 인 글만 후보.
//   - 결과 헤더에 검색 범위 표기 + 스코프 ↔ 전체 토글 링크.
//   - section 내부 home-search 폼 제거. 재검색은 nav-search 만 사용.
//
// 인덱스 포맷 (build.py 의 _build_search() 참조):
//   {
//     "version": 2,
//     "docs":  [{"slug","title","date","category","category_slug","body"}, ...],
//     "categories":  {"<slug>": "<folder_name>", ...},
//     "index":       {"<token>": [[doc_id, tf], ...]},  # 본문
//     "title_index": {"<token>": [[doc_id, tf], ...]}   # 제목 (가중치 ×5)
//   }

$INDEX_PATH = __DIR__ . '/search-index.json';
if (!is_readable($INDEX_PATH)) {
    http_response_code(500);
    echo 'Search index unavailable.';
    exit;
}
$INDEX = json_decode(file_get_contents($INDEX_PATH), true);
if (!is_array($INDEX) || !isset($INDEX['docs'])) {
    http_response_code(500);
    echo 'Search index malformed.';
    exit;
}
$CATEGORIES = isset($INDEX['categories']) && is_array($INDEX['categories'])
    ? $INDEX['categories'] : [];

// build.py 의 _search_tokenize() 와 출력이 100% 일치해야 한다.
// 변경 시 build.py 의 _search_tokenize() 도 동시에 수정.
function search_tokenize(string $text): array {
    if ($text === '') return [];
    $text = mb_strtolower($text, 'UTF-8');
    $tokens = [];
    if (preg_match_all('/[a-z0-9]+/', $text, $m)) {
        foreach ($m[0] as $w) $tokens[] = $w;
    }
    if (preg_match_all('/[\x{AC00}-\x{D7A3}]+/u', $text, $m)) {
        foreach ($m[0] as $word) {
            $chars = preg_split('//u', $word, -1, PREG_SPLIT_NO_EMPTY);
            $len = count($chars);
            if ($len === 1) {
                $tokens[] = $chars[0];
            } else {
                for ($i = 0; $i < $len - 1; $i++) {
                    $tokens[] = $chars[$i] . $chars[$i + 1];
                }
            }
        }
    }
    return $tokens;
}

$q_raw = isset($_GET['q']) ? (string)$_GET['q'] : '';
$q = trim(mb_substr($q_raw, 0, 100, 'UTF-8'));  // 길이 제한 (남용 방지)

$cat_raw = isset($_GET['cat']) ? (string)$_GET['cat'] : '';
$cat = trim($cat_raw);
// cat 화이트리스트: 인덱스에 등재된 슬러그만 허용 (잘못된 입력은 전체 검색으로 폴백)
if ($cat !== '' && !isset($CATEGORIES[$cat])) {
    $cat = '';
}

$hits = [];
if ($q !== '') {
    $tokens = search_tokenize($q);
    if (!empty($tokens)) {
        $scores = [];
        foreach ($tokens as $t) {
            if (isset($INDEX['index'][$t])) {
                foreach ($INDEX['index'][$t] as $entry) {
                    $d = $entry[0]; $tf = $entry[1];
                    if ($cat !== '') {
                        $doc = $INDEX['docs'][$d] ?? null;
                        if (!$doc || ($doc['category_slug'] ?? '') !== $cat) continue;
                    }
                    $scores[$d] = ($scores[$d] ?? 0) + $tf;
                }
            }
            if (isset($INDEX['title_index'][$t])) {
                foreach ($INDEX['title_index'][$t] as $entry) {
                    $d = $entry[0]; $tf = $entry[1];
                    if ($cat !== '') {
                        $doc = $INDEX['docs'][$d] ?? null;
                        if (!$doc || ($doc['category_slug'] ?? '') !== $cat) continue;
                    }
                    $scores[$d] = ($scores[$d] ?? 0) + $tf * 5;
                }
            }
        }
        arsort($scores);
        foreach ($scores as $doc_id => $score) {
            $doc = $INDEX['docs'][$doc_id] ?? null;
            if ($doc) $hits[] = ['doc' => $doc, 'score' => $score];
        }
    }
}

function snippet(string $body, string $q, int $context = 40): string {
    if ($q === '' || $body === '') return '';
    $pos = mb_stripos($body, $q, 0, 'UTF-8');
    if ($pos === false) {
        foreach (search_tokenize($q) as $t) {
            $pos = mb_stripos($body, $t, 0, 'UTF-8');
            if ($pos !== false) break;
        }
    }
    if ($pos === false) {
        return mb_substr($body, 0, $context * 2, 'UTF-8');
    }
    $start = max(0, $pos - $context);
    $len = $context * 2 + mb_strlen($q, 'UTF-8');
    $s = mb_substr($body, $start, $len, 'UTF-8');
    if ($start > 0) $s = '…' . $s;
    if ($start + $len < mb_strlen($body, 'UTF-8')) $s .= '…';
    return $s;
}

function highlight_html(string $text, string $q): string {
    $escaped = htmlspecialchars($text, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
    if ($q === '') return $escaped;
    // 리터럴 쿼리 + bigram 토큰을 하나의 alternation 정규식으로 묶어
    // 한 번만 치환한다. 길이 내림차순 정렬로 가장 긴 매치를 우선.
    // (단일 preg_replace 는 오버랩하지 않으므로 nested <mark> 가 안 생김.)
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

$q_attr = htmlspecialchars($q, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
$cat_attr = htmlspecialchars($cat, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
$cat_name = $cat !== '' ? ($CATEGORIES[$cat] ?? $cat) : '';
$cat_name_html = htmlspecialchars($cat_name, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');

// 결과 헤더 라벨 + 스코프 안내
if ($q === '') {
    $result_label = $cat !== ''
        ? ($cat_name_html . ' 카테고리에서 검색')
        : '검색';
    $scope_html = '';
} else {
    $count = count($hits);
    if ($cat !== '') {
        $result_label = '검색결과: ' . $count . '건';
        // 전체 검색 토글 링크
        $all_url = '/search.php?q=' . rawurlencode($q);
        $scope_html = '<span class="search-scope">— ' . $cat_name_html
            . ' 카테고리에서 검색 (<a href="' . htmlspecialchars($all_url, ENT_QUOTES, 'UTF-8')
            . '">전체에서 검색</a>)</span>';
    } else {
        $result_label = '검색결과: ' . $count . '건';
        $scope_html = '<span class="search-scope">— 전체에서 검색</span>';
    }
}
?>
<!DOCTYPE html>
<html lang='ko'>
<head>
    <meta charset='UTF-8'>
    <meta name='robots' content='noindex'>
    <meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <link href='/assets/common_template.css' rel='stylesheet' type='text/css'>
    <title>{{PAGE_TITLE}}</title>
</head>
<body>
    <header>
        <a id='TITLE' href='/'>
            {{MAIN_TITLE}}
        </a>
    </header>
    <nav>
        <form class='nav-search' action='/search.php' method='get' role='search'>
<?php if ($cat !== ''): ?>
            <input type='hidden' name='cat' value="<?= $cat_attr ?>">
<?php endif ?>
            <input type='search' name='q' value="<?= $q_attr ?>" placeholder='검색' aria-label='Search'>
        </form>
        <div id='nav-tracker'><a href='/'>Home</a><a href='/search.php'> / Search</a></div>
        {{NAV_LINKS}}
    </nav>
    <div class="gap">
        <p><?= $result_label ?><?= $scope_html ?></p>
    </div>
    <section>
<?php if ($q === ''): ?>
        <p class='search-hint'>검색어를 입력하세요.</p>
<?php elseif (empty($hits)): ?>
        <p class='search-hint'>검색 결과가 없습니다.</p>
<?php else: ?>
<?php foreach ($hits as $h): $doc = $h['doc']; ?>
        <div class='listup_module_div search-result'>
            <span class='listup_module_title'>
                <a href='/<?= htmlspecialchars($doc['slug'], ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8') ?>/'> <?= highlight_html($doc['title'], $q) ?> </a>
            </span>
            <span class='listup_module_date'> &nbsp;&nbsp; <?= htmlspecialchars($doc['date'], ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8') ?></span>
<?php $snip = snippet($doc['body'], $q); if ($snip !== ''): ?>
            <div class='search-snippet'><?= highlight_html($snip, $q) ?></div>
<?php endif ?>
        </div>
<?php endforeach ?>
<?php endif ?>
    </section>
    <footer>
        <p>Copyright&copy; {{COPYRIGHT_YEAR}}. {{COPYRIGHT_HOLDER}}. All rights reserved.</p>
    </footer>
</body>
</html>

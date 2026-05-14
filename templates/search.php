<?php
declare(strict_types=1);

// ════════════════════════════════════════════════════════════════
// search.php — siheonlee.com 검색 엔드포인트  (v0.5.0)
// ════════════════════════════════════════════════════════════════
//
// 빌드 시 build.py 가 dist/ 로 복사하면서 {{...}} placeholder 만 치환.
// 런타임에 dist/search-index.json (build.py 가 같은 빌드에서 생성) 을
// 읽어 BM25 + 필드 가중치 + phrase 부스트 로 랭킹을 계산.
//
// v0.5.0 변경 — BM25 기반 랭킹으로 전환:
//   - 인덱스 포맷 v3 (이전 v2). 필드별 df / dl / avgdl 추가.
//   - 점수 계산 로직이 templates/search_bm25.php 로 분리 (require_once).
//     이 파일 (search.php) 은 라우팅·필터·HTML 렌더만 담당.
//   - v0.4.x 의 매직 ×5 제목 부스트, TF 누적 합산 폐지.
//   - 매치 밀도 기반 스니펫 — 토큰 매치가 밀집된 윈도우를 우선.
//
// v0.4.2 변경 (유지):
//   - 검색 결과 페이지에 <meta name='robots' content='noindex,follow'>.
//
// 인덱스 포맷 v3 (scripts/search.py 의 build_search_index() 참조):
//   {
//     "version": 3,
//     "params": {"k1_body","b_body","k1_title","b_title",
//                "w_title","phrase_boost_body","phrase_boost_title"},
//     "stats":  {"N","avgdl_body","avgdl_title"},
//     "docs":   [{"slug","title","date","category","category_slug","body",
//                 "dl_body","dl_title"}, ...],
//     "categories": {"<slug>": "<folder_name>", ...},
//     "df_body":    {"<token>": <int>, ...},
//     "df_title":   {"<token>": <int>, ...},
//     "tf_body":    {"<token>": [[doc_id, tf], ...]},
//     "tf_title":   {"<token>": [[doc_id, tf], ...]}
//   }

require_once __DIR__ . '/search_tokenize.php';
require_once __DIR__ . '/search_bm25.php';

$INDEX_PATH = __DIR__ . '/search-index.json';
if (!is_readable($INDEX_PATH)) {
    http_response_code(500);
    echo 'Search index unavailable.';
    exit;
}
$INDEX = json_decode(file_get_contents($INDEX_PATH), true);
if (!is_array($INDEX) || !isset($INDEX['docs']) || ($INDEX['version'] ?? 0) < 3) {
    http_response_code(500);
    echo 'Search index malformed or version mismatch (expected v3).';
    exit;
}
$CATEGORIES = isset($INDEX['categories']) && is_array($INDEX['categories'])
    ? $INDEX['categories'] : [];

$q_raw = isset($_GET['q']) ? (string)$_GET['q'] : '';
$q = trim(mb_substr($q_raw, 0, 100, 'UTF-8'));  // 길이 제한 (남용 방지)

$cat_raw = isset($_GET['cat']) ? (string)$_GET['cat'] : '';
$cat = trim($cat_raw);
if ($cat !== '' && !isset($CATEGORIES[$cat])) {
    $cat = '';
}

$hits = [];
if ($q !== '') {
    $ranked = bm25_search($INDEX, $q, $cat !== '' ? $cat : null);
    foreach ($ranked as $r) {
        $hits[] = ['doc' => $r[2], 'score' => $r[1]];
    }
}

$q_attr = htmlspecialchars($q, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
$cat_attr = htmlspecialchars($cat, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
$cat_name = $cat !== '' ? ($CATEGORIES[$cat] ?? $cat) : '';
$cat_name_html = htmlspecialchars($cat_name, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');

if ($q === '') {
    $result_label = $cat !== ''
        ? ($cat_name_html . ' 카테고리에서 검색')
        : '검색';
    $scope_html = '';
} else {
    $count = count($hits);
    if ($cat !== '') {
        $result_label = '검색결과: ' . $count . '건';
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
<html lang='{{LANG}}'>
<head>
    <meta charset='UTF-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <meta name='robots' content='noindex,follow'>
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
<?php $snip = snippet_density($doc['body'], $q); if ($snip !== ''): ?>
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

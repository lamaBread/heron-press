<?php
declare(strict_types=1);

// ════════════════════════════════════════════════════════════════
// search.php — Heron 검색 엔드포인트  (v0.6.0)
// ════════════════════════════════════════════════════════════════
//
// 빌드 시 build.py 가 dist/ 로 복사하면서 다음을 처리 (sentinel 패턴은
// 본 헤더에서 일부러 약간 다른 표기로 인용했다 — builder 가 본 헤더 자체를
// 매치하지 않도록):
//   (a) PHP 주석 "INLINE_SEARCH_TOKENIZE" 자리에 templates/search_tokenize.php
//       의 함수 본문을 인라인
//   (b) PHP 주석 "INLINE_SEARCH_BM25" 자리에 templates/search_bm25.php 의
//       함수 본문을 인라인
//   (c) PHP 주석 "INLINE_SEARCH_INDEX" 와 직후 placeholder [] 자리에 빌드
//       시점 정적 인덱스 (PHP 배열 리터럴) 를 인라인. 결정적 직렬화
//       (scripts/search.py 의 php_array_literal) 로 같은 입력 → 같은 PHP 텍스트.
//   (d) HTML 컨텍스트의 변수 placeholder (LANG, PAGE_TITLE, MAIN_TITLE,
//       NAV_LINKS, COPYRIGHT_YEAR, COPYRIGHT_HOLDER) 들을 실제 값으로 치환.
//       빌더의 `_render_template` 가 두 겹 중괄호 패턴을 찾아 단순 문자열
//       교체 — 이 헤더 주석에선 일부러 중괄호를 빼고 적어 placeholder 가
//       주석 안에서도 치환되어 자기 결과를 인용하는 메타-광경을 피한다
//       (v0.6.1).
//
// 위 (a)·(b)·(c) 는 PHP 주석 / 빈 배열 자리에 인라인되므로, 이 템플릿
// 파일 자체도 `php -l` 통과 + IDE 의 PHP 정적 분석 통과한다.
//
// v0.6.0 변경 요약:
//   - search-index.json 폐기. 인덱스가 이 파일 안에 PHP 정적 배열 리터럴로
//     인라인된다. JSON 파싱 / 디스크 IO 0. OPcache 가 search.php 의 바이트
//     코드를 캐시하면 인덱스 배열도 메모리에 상주.
//   - 색인 대상 필드: (title, description, tags). 본문은 더 이상 색인되지
//     않는다. 검색 결과 미리보기용 스니펫만 docs[].body_snippet 으로 보존.
//   - 채점 함수 (bm25_search / snippet_density / highlight_html) 와 토크나이저
//     도 이 파일 안에 인라인된다 — search_bm25.php / search_tokenize.php 의
//     별도 require_once 호출 없음 (OPcache hit 시 한 파일 = 한 캐시 엔트리).
//   - noindex 글은 빌드 단계에서 인덱스에서 제외 (sitemap / feed 와 일관).
//
// v0.4.2 유지: 검색 결과 페이지에 <meta name='robots' content='noindex,follow'>.

// ── 인라인 토크나이저 ────────────────────────────────────────────
/* INLINE: SEARCH_TOKENIZE */

// ── 인라인 BM25 점수 + 스니펫 + 하이라이트 ──────────────────────
/* INLINE: SEARCH_BM25 */

// ── 인라인 정적 인덱스 ──────────────────────────────────────────
//
// 빌드 시 scripts/search.php_array_literal() 가 결정적으로 직렬화한 PHP
// 배열 리터럴이 아래 `[]` 자리에 인라인된다. OPcache 가 캐시하므로 매
// 요청마다 파싱하지 않는다.
$INDEX = /* INLINE: SEARCH_INDEX */ [];

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
    {{ADSENSE_HEAD}}
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
<?php $snip = snippet_density((string)($doc['body_snippet'] ?? ''), $q); if ($snip !== ''): ?>
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

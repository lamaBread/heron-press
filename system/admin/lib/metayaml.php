<?php
// meta.yaml 경량 R/W (admin v1.1.0).
//
// 합의 모델: **raw meta.yaml 이 진실원.** 저장 시 admin 은 편집기의 raw
// 텍스트를 그대로(verbatim) 기록한다 — 서버에서 구조화 재-emit 하지
// 않으므로 주석·미지 키·styles 블록이 손상 없이 보존된다. 유일한 서버
// 정규화는 헤더 주석 한 줄 보장(관례). 아래 reader 는 폼 prefill 전용
// (의도된 YAML 부분집합 기준 경량 파스 — 완벽한 YAML 파서가 아니라,
// 빗나가도 사용자가 raw 칸에서 직접 본다). new_template 은 새 글의
// 최초 파일만 생성 (작은 고정 스키마라 안전).

declare(strict_types=1);

/** 스칼라 따옴표 제거 (부분집합 파서와 동일: 양끝 같은 따옴표면 strip). */
function meta_unquote(string $s): string {
    $s = trim($s);
    $n = strlen($s);
    if ($n >= 2) {
        $a = $s[0]; $b = $s[$n - 1];
        if (($a === '"' && $b === '"') || ($a === "'" && $b === "'")) {
            return substr($s, 1, -1);
        }
    }
    return $s;
}

/** 인라인 리스트 `[a, "b", c]` → 배열. */
function meta_parse_inline_list(string $s): array {
    $s = trim($s);
    if ($s === '' || $s[0] !== '[') return [];
    $inner = substr($s, 1, (strrpos($s, ']') ?: strlen($s)) - 1);
    if (trim($inner) === '') return [];
    $out = []; $cur = ''; $q = null;
    $len = strlen($inner);
    for ($i = 0; $i < $len; $i++) {
        $c = $inner[$i];
        if ($q !== null) { if ($c === $q) $q = null; else $cur .= $c; }
        elseif ($c === '"' || $c === "'") $q = $c;
        elseif ($c === ',') { $out[] = trim($cur); $cur = ''; }
        else $cur .= $c;
    }
    if (trim($cur) !== '') $out[] = trim($cur);
    return array_map('meta_unquote', $out);
}

/**
 * 폼 prefill 용 핵심 필드 경량 추출. 반환 키:
 * slug,title,date,updated (string), noindex (bool),
 * tags (string[]), description (seo.description, string).
 */
function meta_read_core(string $text): array {
    $r = ['slug'=>'','title'=>'','date'=>'','updated'=>'',
          'noindex'=>false,'tags'=>[],'description'=>''];
    $lines = preg_split('/\r\n|\r|\n/', $text);
    $n = count($lines);
    for ($i = 0; $i < $n; $i++) {
        $line = $lines[$i];
        if ($line === '' || ltrim($line)[0] === '#') continue;
        $indent = strlen($line) - strlen(ltrim($line, ' '));

        if ($indent === 0 && preg_match('/^([A-Za-z_][\w]*)\s*:(.*)$/', $line, $m)) {
            $key = $m[1]; $val = trim($m[2]);
            switch ($key) {
                case 'slug':    $r['slug']    = meta_unquote($val); break;
                case 'title':   $r['title']   = meta_unquote($val); break;
                case 'date':    $r['date']    = meta_unquote($val); break;
                case 'updated': $r['updated'] = meta_unquote($val); break;
                case 'noindex':
                    $r['noindex'] = in_array(strtolower($val),
                        ['true','yes','1'], true);
                    break;
                case 'tags':
                    if ($val !== '' && $val[0] === '[') {
                        $r['tags'] = meta_parse_inline_list($val);
                    } else { // 블록 리스트
                        for ($j = $i + 1; $j < $n; $j++) {
                            if (preg_match('/^\s*-\s*(.+)$/', $lines[$j], $mm)) {
                                $r['tags'][] = meta_unquote(trim($mm[1]));
                            } elseif (trim($lines[$j]) === '') { continue; }
                            else break;
                        }
                    }
                    break;
                case 'seo': // 다음의 들여쓰기 블록에서 description
                    for ($j = $i + 1; $j < $n; $j++) {
                        $l2 = $lines[$j];
                        if (trim($l2) === '' || ltrim($l2)[0] === '#') continue;
                        $ind2 = strlen($l2) - strlen(ltrim($l2, ' '));
                        if ($ind2 === 0) break; // seo 블록 종료
                        if (preg_match('/^\s*description\s*:(.*)$/', $l2, $m2)) {
                            $r['description'] = meta_unquote(trim($m2[1]));
                        }
                    }
                    break;
            }
        }
    }
    return $r;
}

/** 정본 헤더 주석 한 줄. */
function meta_header_line(string $relId): string {
    $relId = str_replace('\\', '/', $relId);
    return "# Articles/{$relId}/meta.yaml — 글 페이지 메타데이터.";
}

/** 첫 비공백 줄이 meta.yaml 헤더 주석이 아니면 정본 헤더를 앞에 붙인다. */
function meta_ensure_header(string $text, string $relId): string {
    foreach (preg_split('/\r\n|\r|\n/', $text) as $l) {
        if (trim($l) === '') continue;
        if ($l[0] === '#' && str_contains($l, 'meta.yaml')) return $text;
        break;
    }
    return meta_header_line($relId) . "\n\n\n" . ltrim($text, "\r\n");
}

/** YAML 스칼라 안전 인용 (부분집합 파서는 escape 미지원 → 충돌 회피). */
function meta_q(string $s): string {
    if ($s === '') return "''";
    if (!str_contains($s, "'")) return "'" . $s . "'";
    if (!str_contains($s, '"')) return '"' . $s . '"';
    // 둘 다 포함 — 부분집합 파서가 깰 수 있어 작은따옴표를 타이포그래픽
    // 따옴표로 치환 (드묾; 사용자가 raw 칸에서 원하면 되돌릴 수 있다).
    return "'" . str_replace("'", "\u{2019}", $s) . "'";
}

/**
 * 새 글 최초 meta.yaml 본문 생성. $f: slug,title,date,tags[],description.
 * 작은 고정 스키마라 직접 emit 해도 안전 (부분집합 내).
 */
function meta_new_template(array $f, string $relId): string {
    $tags = '';
    if (!empty($f['tags'])) {
        $tags = '[' . implode(', ', array_map('meta_q', $f['tags'])) . ']';
    }
    $L = [];
    $L[] = meta_header_line($relId);
    $L[] = '';
    $L[] = '';
    $L[] = 'slug: ' . $f['slug'];
    $L[] = 'title: ' . meta_q($f['title']);
    $L[] = 'date: ' . $f['date'];
    if ($tags !== '') $L[] = 'tags: ' . $tags;
    $L[] = '';
    $L[] = '';
    $L[] = 'seo:';
    $L[] = '  description: ' . meta_q($f['description'] ?? '');
    return implode("\n", $L) . "\n";
}

/**
 * 홈/카테고리 페이지 meta.yaml 시드 (v1.14.8 — 파일이 아직 없을 때 편집기 초기값).
 * 대부분 주석이라 그대로 저장해도(=빈 의미) 유효하다 — 사용자가 필요한 키만
 * 주석 해제. 키 어휘 자체가 영어(slug/title/...)라 본문도 영어로 둔다(데모 페이지
 * meta.yaml 과 동일 관례). $isHome=true 면 홈 전용 키(excludes_categories) 포함,
 * 카테고리 전용 키(priority/nav_priority/template)는 제외. $relLabel 은 헤더
 * 주석의 경로 표기용 ('' = 홈).
 */
function meta_page_template(bool $isHome, string $relLabel = ''): string {
    $L = [];
    if ($isHome) {
        $L[] = '# Home page settings (user/articles/meta.yaml).';
        $L[] = '# The home page is special: it has no slug/date. Only the keys below apply.';
        $L[] = '# Uncomment and edit only the keys you need; an empty file means all defaults.';
        $L[] = '';
        $L[] = '# title: My Site            # <title> + home heading (else site.name)';
        $L[] = '# per_page: 10              # articles shown on the home feed (newest first)';
        $L[] = '# excludes_categories: []   # top-level categories to hide from the home feed';
    } else {
        $rel = str_replace('\\', '/', $relLabel);
        $L[] = '# Category page settings (user/articles/' . $rel . '/meta.yaml).';
        $L[] = '# This file is optional — without it the category uses all defaults.';
        $L[] = '# Uncomment and edit only the keys you need; an empty file means all defaults.';
        $L[] = '';
        $L[] = '# title: ' . ($rel === '' ? 'My Category' : basename($rel))
             . '            # <title> override for this category page';
        $L[] = '# per_page: 10              # articles per page in this category feed';
        $L[] = '# layout: list              # list | grid';
        $L[] = '# priority: 0               # sort weight among sibling categories (higher = earlier)';
        $L[] = '# nav_priority: 0           # top-level nav ordering (separate axis from priority)';
        $L[] = '# template:                 # custom template ref (omit for default)';
    }
    $L[] = '# use_common_css: true      # include the shared stylesheet';
    $L[] = '# seo:';
    $L[] = '#   description: ...';
    $L[] = '#   og_image: /assets/default-og.png';
    $L[] = '# styles:';
    $L[] = '#   p:';
    $L[] = '#     line-height: 1.75em';
    return implode("\n", $L) . "\n";
}

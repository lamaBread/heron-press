<?php
declare(strict_types=1);

// ════════════════════════════════════════════════════════════════
// search_tokenize.php — Heron 검색 토크나이저 (v0.4.0)
// ════════════════════════════════════════════════════════════════
//
// 두 가지 모드로 동작:
//   (a) 빌더가 인라인: build.py 가 빌드 시 이 파일의 함수 본문을 dist/search
//       .php 의 sentinel 자리에 직접 인라인한다 (v0.6.0 부터; v0.5.x 까지는
//       dist/search_tokenize.php 로 복사되고 search.php 가 require_once 했음).
//       헤더 배너와 `<?php` 등은 builder._inline_php_body 가 strip.
//   (b) CLI 직접 호출: argv[1] 로 입력 문자열을 받아 JSON 배열을 stdout 으로.
//       — scripts/search.py 가 빌드 시 패리티 검증에 사용 + tests/run_diagnostics
//       .py 가 Python↔PHP 점수 패리티 검사에서 토크나이저 일치까지 함께 검증.
//
// 출력 규칙 (scripts/search.py 의 search_tokenize() 와 1:1 일치):
//   - 영문/숫자 (lowercase) : 단어 단위로
//   - 한글 (가-힣)          : 2-gram. 1글자 시퀀스는 제외 (v0.4.0)
//   - 그 외 문자             : 분리자
//
// 이 파일은 단일 진실원 (single source of truth) 이다 — 빌더가 인라인하고
// build.py / 진단 스크립트가 CLI 로 직접 실행해 패리티를 검증한다. 어느
// 한쪽에 사본을 두지 말 것.

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
            if ($len < 2) continue;  // v0.4.0: 1글자 한글 제외
            for ($i = 0; $i < $len - 1; $i++) {
                $tokens[] = $chars[$i] . $chars[$i + 1];
            }
        }
    }
    return $tokens;
}

// CLI 모드 — 패리티 검증용. argv[1] 을 토큰화해 JSON 으로 출력.
if (PHP_SAPI === 'cli' && isset($argv[0])
        && realpath($argv[0]) === realpath(__FILE__)) {
    $input = $argv[1] ?? '';
    echo json_encode(search_tokenize($input), JSON_UNESCAPED_UNICODE);
}

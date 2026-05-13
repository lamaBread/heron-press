<?php
declare(strict_types=1);

// ════════════════════════════════════════════════════════════════
// search_tokenize.php — siheonlee.com 검색 토크나이저 (v0.4.0)
// ════════════════════════════════════════════════════════════════
//
// 두 가지 모드로 동작:
//   (a) require_once: search_tokenize() 함수만 정의. 다른 PHP 가 include.
//   (b) CLI 직접 호출: argv[1] 로 입력 문자열을 받아 JSON 배열을 stdout 으로.
//       — Python 의 scripts/search.py 가 빌드 시 패리티 검증에 사용.
//
// 출력 규칙 (scripts/search.py 의 search_tokenize() 와 1:1 일치):
//   - 영문/숫자 (lowercase) : 단어 단위로
//   - 한글 (가-힣)          : 2-gram. 1글자 시퀀스는 제외 (v0.4.0)
//   - 그 외 문자             : 분리자
//
// 이 파일은 단일 진실원 (single source of truth) 이다. search.php 가
// require_once 하고, build.py 가 CLI 로 직접 실행해 패리티를 검증한다.
// 어느 한 쪽에 사본을 두지 말 것.

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

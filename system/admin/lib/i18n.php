<?php
// 로케일 문자열 lookup — Pond admin UI (Surface 2) 전용 (v1.9.0 i18n 신설).
//
// 팩: system/locales/<locale>/*.yaml (플랫 닷키 → 인용 문자열). 한 로케일
// 폴더의 모든 *.yaml 조각을 머지한다. en 이 기본 겸 폴백(키 패리티 기준;
// ko 는 완전 번역으로 동봉); 키가 없으면 키 문자열을 그대로 돌려 절대 빈칸이
// 안 되게 한다. 도구 언어는 user/.heron/locale 한 줄로 정해진다 (없으면 en).
//
// 빌드/CLI(Surface 3)·사이트 chrome(Surface 1)은 Python 측 system/scripts/
// i18n.py 가 담당한다 — 같은 로케일 포맷을 공유한다.
//
// 로케일 파일 규칙(파서 단순화):
//   - 한 줄 = `키: "값"` (또는 '값'). 키는 닷(dot) 구분, 콜론/샵 없음.
//   - 줄 시작 `#` 은 주석. 값 안 인라인 주석은 쓰지 말 것(그대로 보존됨).
//   - escape (v1.9.1): **큰따옴표 값** 안에서 `\"` `\\` `\n` `\t` 를 해석한다.
//     그 외 `\x` 는 백슬래시째 보존. **작은따옴표 값** 은 리터럴(해석 없음,
//     YAML 동일). HTML 속성은 `class='k'` 처럼 작은따옴표를 써 큰따옴표 값에
//     백슬래시 없이 담는 것을 권장. (i18n.py 와 바이트 동일 규칙 — test_i18n
//     의 파서 패리티 테스트가 강제.)
declare(strict_types=1);

// 기본 도구 언어 + 폴백 + 키 패리티 기준 (v1.9.7: ko→en). i18n.py 의 CANONICAL 과 동일.
const I18N_CANONICAL = 'en';

/** system/locales 절대 경로 (이 파일: system/admin/lib/i18n.php). */
function i18n_locales_dir(): string {
    return dirname(__DIR__, 2) . '/locales';
}

/**
 * 양끝 같은 따옴표면 한 겹 제거. 큰따옴표 값은 추가로 escape 를 해석하고
 * (i18n_unescape), 작은따옴표 값은 리터럴 그대로 둔다 (YAML 동일). i18n.py 의
 * _unquote 와 바이트 동일.
 */
function i18n_unquote(string $s): string {
    $n = strlen($s);
    if ($n >= 2) {
        $a = $s[0]; $b = $s[$n - 1];
        if ($a === '"' && $b === '"') return i18n_unescape(substr($s, 1, -1));
        if ($a === "'" && $b === "'") return substr($s, 1, -1);
    }
    return $s;
}

/**
 * 큰따옴표 값의 escape 해석: `\"`→`"`, `\\`→`\`, `\n`→개행, `\t`→탭.
 * 그 외 `\x` 는 백슬래시째 보존. ASCII 만 특수 처리하므로 UTF-8 멀티바이트
 * (한글 등)는 바이트 단위로 안전히 통과한다. (i18n.py 의 _unescape 와 동일.)
 */
function i18n_unescape(string $s): string {
    $out = '';
    $len = strlen($s);
    for ($i = 0; $i < $len; $i++) {
        $c = $s[$i];
        if ($c === '\\' && $i + 1 < $len) {
            $nx = $s[$i + 1];
            if ($nx === 'n')  { $out .= "\n"; $i++; continue; }
            if ($nx === 't')  { $out .= "\t"; $i++; continue; }
            if ($nx === '"')  { $out .= '"';  $i++; continue; }
            if ($nx === '\\') { $out .= '\\'; $i++; continue; }
            $out .= $c;   // 알 수 없는 escape — 백슬래시 보존
            continue;
        }
        $out .= $c;
    }
    return $out;
}

/** <locale>/*.yaml 들을 머지한 플랫 [key => string] 맵. */
function i18n_load_pack(string $locale): array {
    $dir = i18n_locales_dir() . '/' . $locale;
    if (!is_dir($dir)) return [];
    $out = [];
    foreach (glob($dir . '/*.yaml') ?: [] as $f) {
        $text = (string)@file_get_contents($f);
        foreach (preg_split('/\r\n|\r|\n/', $text) as $line) {
            if ($line === '') continue;
            $lt = ltrim($line);
            if ($lt === '' || $lt[0] === '#') continue;
            if (!preg_match('/^([^:#]+?):\s*(.*)$/', $line, $m)) continue;
            $out[trim($m[1])] = i18n_unquote(trim($m[2]));
        }
    }
    return $out;
}

// 부트스트랩 전 안전 기본값 (t() 가 init 전에 불려도 키를 그대로 돌려줌).
$GLOBALS['__i18n'] = ['locale' => I18N_CANONICAL, 'fallback' => [], 'strings' => []];

/** 도구 언어로 로케일 테이블을 적재한다. ko 는 항상 폴백으로 함께 적재. */
function i18n_init(string $locale): void {
    $locale = $locale !== '' ? $locale : I18N_CANONICAL;
    $fallback = i18n_load_pack(I18N_CANONICAL);
    $strings = $locale === I18N_CANONICAL ? $fallback : i18n_load_pack($locale);
    $GLOBALS['__i18n'] = [
        'locale' => $locale, 'fallback' => $fallback, 'strings' => $strings,
    ];
}

/** 현재 적재된 도구 언어 코드 (예: 'en'). 미초기화면 en. */
function i18n_locale(): string {
    return (string)($GLOBALS['__i18n']['locale'] ?? I18N_CANONICAL);
}

/**
 * 로케일 문자열. $vars: ['n' => 3] → 값 안의 `{n}` 치환.
 * 키가 없으면 폴백(ko) → 그래도 없으면 키 문자열 자체를 돌려준다.
 */
function t(string $key, array $vars = []): string {
    $g = $GLOBALS['__i18n'];
    $s = $g['strings'][$key] ?? ($g['fallback'][$key] ?? $key);
    if ($vars) {
        $rep = [];
        foreach ($vars as $k => $v) $rep['{' . $k . '}'] = (string)$v;
        $s = strtr($s, $rep);
    }
    return $s;
}

/** user/.heron/locale 한 줄. 부재/공백이면 'en'. $base = 버전 폴더 루트. */
function i18n_read_tool_locale(string $base): string {
    $f = $base . '/user/.heron/locale';
    if (!is_file($f)) return I18N_CANONICAL;
    $first = strtok((string)@file_get_contents($f), "\r\n");
    $line = trim($first === false ? '' : $first);
    return $line !== '' ? $line : I18N_CANONICAL;
}

/** system/locales/ 아래 존재하는 로케일 폴더명 목록 (정렬). 설정 드롭다운용. */
function i18n_available_locales(): array {
    $dir = i18n_locales_dir();
    if (!is_dir($dir)) return [I18N_CANONICAL];
    $out = [];
    foreach (glob($dir . '/*', GLOB_ONLYDIR) ?: [] as $d) $out[] = basename($d);
    sort($out);
    return $out ?: [I18N_CANONICAL];
}

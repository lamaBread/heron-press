<?php
// 파일시스템 안전 헬퍼 (admin v1.1.0).
// 모든 글 연산은 <verdir>/user/articles/ 안에서만 — id 는 articles 기준
// 상대경로(슬래시 구분). path traversal 차단이 이 파일의 핵심 책임.

declare(strict_types=1);

/** <verdir> (Pond.php 가 있는 폴더). */
function admin_base_dir(): string {
    return dirname(__DIR__, 3); // system/admin/lib → system/admin → system → <verdir>
}

/** <verdir>/user/articles 절대경로 (v1.5.0: articles 가 user/ 아래로). */
function admin_articles_dir(): string {
    return admin_base_dir() . DIRECTORY_SEPARATOR . 'user'
        . DIRECTORY_SEPARATOR . 'articles';
}

/**
 * Articles 기준 상대 id 를 정규화·검증한다.
 * - 슬래시/역슬래시 → '/' 통일, 빈 세그먼트·'.'·'..' 거부.
 * - 절대경로·드라이브문자 거부.
 * 반환: 정규화된 rel ('' = Articles 루트) 또는 null(거부).
 */
function admin_safe_rel(?string $rel): ?string {
    if ($rel === null) return null;
    if (str_contains($rel, "\x00")) return null;   // NUL 거부 (경로 절단 방지).
    $rel = str_replace('\\', '/', trim($rel));
    $rel = ltrim($rel, '/');
    if ($rel === '') return '';
    if (preg_match('#^[A-Za-z]:#', $rel)) return null;
    $parts = explode('/', $rel);
    $out = [];
    foreach ($parts as $p) {
        if ($p === '' || $p === '.' || $p === '..') return null;
        $out[] = $p;
    }
    return implode('/', $out);
}

/** rel id → 실제 절대경로 (검증 통과 전제). null = 거부된 rel. */
function admin_abs(?string $rel): ?string {
    $rel = admin_safe_rel($rel);
    if ($rel === null) return null;
    $abs = admin_articles_dir();
    if ($rel !== '') {
        $abs .= DIRECTORY_SEPARATOR . str_replace('/', DIRECTORY_SEPARATOR, $rel);
    }
    return $abs;
}

/**
 * 해석된 실제 경로가 Articles/ 안에 있는지 realpath 로 한 번 더 검증
 * (심링크·대소문자 우회 방어). 존재하는 경로에만 의미가 있다.
 */
function admin_is_inside_articles(string $abs): bool {
    $root = realpath(admin_articles_dir());
    $real = realpath($abs);
    if ($root === false || $real === false) return false;
    $root = rtrim($root, DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR;
    return str_starts_with($real . DIRECTORY_SEPARATOR, $root)
        || $real === rtrim($root, DIRECTORY_SEPARATOR);
}

/** 폴더가 '글' 인가 (content.md xor content.html 존재). */
function admin_is_post_dir(string $abs): bool {
    return is_file($abs . DIRECTORY_SEPARATOR . 'content.md')
        || is_file($abs . DIRECTORY_SEPARATOR . 'content.html');
}

/** 폴더가 '카테고리' 인가 (meta.yaml 있고 content 파일 없음). */
function admin_is_category_dir(string $abs): bool {
    return is_file($abs . DIRECTORY_SEPARATOR . 'meta.yaml')
        && !admin_is_post_dir($abs);
}

/** 글의 content 파일 ['ext'=>'md'|'html', 'path'=>abs] 또는 null. */
function admin_content_file(string $abs): ?array {
    $md = $abs . DIRECTORY_SEPARATOR . 'content.md';
    $html = $abs . DIRECTORY_SEPARATOR . 'content.html';
    if (is_file($md))   return ['ext' => 'md',   'path' => $md];
    if (is_file($html)) return ['ext' => 'html', 'path' => $html];
    return null;
}

/** 원자적 파일 쓰기 (temp → rename, 같은 디렉터리). */
function admin_atomic_write(string $path, string $data): bool {
    $dir = dirname($path);
    if (!is_dir($dir) && !@mkdir($dir, 0777, true) && !is_dir($dir)) {
        return false;
    }
    $tmp = $dir . DIRECTORY_SEPARATOR . '.admin_tmp_' . bin2hex(random_bytes(6));
    if (@file_put_contents($tmp, $data) === false) { @unlink($tmp); return false; }
    if (!@rename($tmp, $path)) { @unlink($tmp); return false; }
    return true;
}

/** 휴지통 경로 (.trash → '.' 접두라 빌더 자동 제외). */
function admin_trash_dir(): string {
    return admin_articles_dir() . DIRECTORY_SEPARATOR . '.trash';
}

/** user/.heron 디렉터리 절대경로 (설정·캐시·백업 보관소). */
function admin_heron_dir(): string {
    return admin_base_dir() . DIRECTORY_SEPARATOR . 'user'
        . DIRECTORY_SEPARATOR . '.heron';
}

/** user/.heron/update.json 경로 (v1.6.0 업데이트 체크 캐시). */
function admin_update_cache_path(): string {
    return admin_heron_dir() . DIRECTORY_SEPARATOR . 'update.json';
}

/** user/site.yaml 경로 (v1.8.0 설정창이 편집하는 사이트 전역 설정). */
function admin_site_yaml_path(): string {
    return admin_base_dir() . DIRECTORY_SEPARATOR . 'user'
        . DIRECTORY_SEPARATOR . 'site.yaml';
}

/**
 * 페이지 meta.yaml 경로 (v1.14.8 — 홈/카테고리 설정 편집기). $rel='' = 홈
 * (user/articles/meta.yaml), 그 외 = 카테고리 폴더 상대경로의 meta.yaml.
 * null = 거부된 rel (admin_safe_rel 실패). 호출부는 $rel 을 먼저 화이트리스트
 * (admin_scan()['categories']) 로 검증한다.
 */
function admin_page_meta_path(string $rel): ?string {
    $abs = admin_abs($rel);
    if ($abs === null) return null;
    return $abs . DIRECTORY_SEPARATOR . 'meta.yaml';
}

/**
 * 덮어쓰기 전 안전 백업 (v1.8.0 설정 저장 게이트용). $absPath 를
 * user/.heron/backups/settings/<Ymd-His>__<tag>__<basename> 으로 복사한다.
 * 마이그레이션 백업(user/.heron/backups/)과 같은 보관소·타임스탬프 관례.
 * 원본이 없으면(최초 생성) 백업 없이 true. 반환: 백업 성공 여부.
 */
function admin_backup_file(string $absPath, string $tag): bool {
    if (!is_file($absPath)) return true;   // 최초 생성 — 백업할 원본 없음.
    $dir = admin_heron_dir() . DIRECTORY_SEPARATOR . 'backups'
        . DIRECTORY_SEPARATOR . 'settings';
    if (!is_dir($dir) && !@mkdir($dir, 0777, true) && !is_dir($dir)) return false;
    $dest = $dir . DIRECTORY_SEPARATOR . date('Ymd-His') . '__' . $tag
        . '__' . basename($absPath);
    return @copy($absPath, $dest);
}

/**
 * 프로그램 버전 문자열 (단일 진실원 = system/scripts/__init__.py __version__).
 * 홈/설명 화면 표시용. 못 읽으면 빈 문자열. update.json 캐시(네트워크 기준)와
 * 달리 현재 설치본 자체의 버전을 직접 읽는다.
 */
function admin_program_version(): string {
    $p = admin_base_dir() . DIRECTORY_SEPARATOR . 'system'
        . DIRECTORY_SEPARATOR . 'scripts' . DIRECTORY_SEPARATOR . '__init__.py';
    $src = (string)@file_get_contents($p);
    if ($src !== '' && preg_match('/__version__\s*=\s*[\'"]([^\'"]+)[\'"]/', $src, $m)) {
        return $m[1];
    }
    return '';
}

/** 업데이트 체크 캐시 읽기 — 배너용 (없거나 깨지면 []). */
function admin_read_update_cache(): array {
    $p = admin_update_cache_path();
    if (!is_file($p)) return [];
    $j = json_decode((string)@file_get_contents($p), true);
    return is_array($j) ? $j : [];
}

/** 콘텐츠 타입 추정 (미리보기 asset 프록시용). */
function admin_mime(string $path): string {
    static $map = [
        'jpg'=>'image/jpeg','jpeg'=>'image/jpeg','png'=>'image/png',
        'gif'=>'image/gif','webp'=>'image/webp','svg'=>'image/svg+xml',
        'css'=>'text/css','js'=>'text/javascript','pdf'=>'application/pdf',
        'mp4'=>'video/mp4','webm'=>'video/webm','txt'=>'text/plain',
    ];
    $e = strtolower(pathinfo($path, PATHINFO_EXTENSION));
    return $map[$e] ?? 'application/octet-stream';
}

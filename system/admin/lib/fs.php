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

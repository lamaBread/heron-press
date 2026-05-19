<?php
/**
 * siheonlee.com — 로컬 글쓰기 admin (v1.1.0).
 *
 * 이 파일은 build.py 와 같은 위치(버전 폴더 루트)의 *얇은 라우터* 일
 * 뿐, 로직은 전부 src/admin/ 안에 있다 (build.py = 얇은 진입점 +
 * src/scripts/ 패턴 미러). 빌더는 Articles/ 만 스캔하므로 이 파일과
 * src/admin/ 은 dist 에 새지 않는다 (산출물 byte-불변).
 *
 * 실행 (버전 폴더에서):
 *     php -S 127.0.0.1:8001 admin.php
 *   브라우저: http://127.0.0.1:8001/
 *
 * 보안: **로컬 전용 단일 사용자 도구.** PHP 내장 서버(cli-server)
 * + 루프백에서만 동작 — 그 외 SAPI/원격이면 즉시 403. 배포(§13)는
 * dist/ 만 올리므로 admin.php·src/admin/ 은 빌드 머신을 떠나지 않는다.
 * 그래도 실수로 서버에 놓여도 열리지 않게 다층 가드를 둔다. **절대
 * 공개 서버에 두지 말 것.**
 */
declare(strict_types=1);

// ── 다층 보안 가드 ────────────────────────────────────────────────
$sapi = php_sapi_name();
$remote = $_SERVER['REMOTE_ADDR'] ?? '';
$loopback = in_array($remote, ['127.0.0.1', '::1', ''], true);
if ($sapi !== 'cli-server' || !$loopback) {
    http_response_code(403);
    header('Content-Type: text/plain; charset=utf-8');
    exit("403 — admin 은 로컬 PHP 내장 서버(php -S 127.0.0.1:8001 "
        . "admin.php)에서만 동작합니다. (sapi={$sapi})");
}

require_once __DIR__ . '/src/admin/lib/fs.php';
require_once __DIR__ . '/src/admin/lib/proc.php';
require_once __DIR__ . '/src/admin/lib/metayaml.php';
require_once __DIR__ . '/src/admin/lib/articles.php';

session_start();
if (empty($_SESSION['csrf'])) {
    $_SESSION['csrf'] = bin2hex(random_bytes(16));
}
$CSRF = $_SESSION['csrf'];

function h(?string $s): string {
    return htmlspecialchars((string)$s, ENT_QUOTES, 'UTF-8');
}
function redirect(string $qs): never {
    header('Location: ' . $_SERVER['SCRIPT_NAME'] . $qs);
    exit;
}
function want_post(): void {
    if ($_SERVER['REQUEST_METHOD'] !== 'POST') { http_response_code(405); exit('POST only'); }
}
function check_csrf(): void {
    global $CSRF;
    if (!hash_equals($CSRF, (string)($_POST['csrf'] ?? ''))) {
        http_response_code(403); exit('CSRF token mismatch');
    }
}
/** 글 폴더 abs 를 안전하게 해석 (검증 실패 시 404 종료). */
function require_post_abs(string $id): string {
    $abs = admin_abs($id);
    if ($abs === null || !is_dir($abs) || !admin_is_inside_articles($abs)
        || !admin_is_post_dir($abs)) {
        http_response_code(404); exit('글을 찾을 수 없습니다: ' . h($id));
    }
    return $abs;
}

$action = $_GET['a'] ?? 'list';

// ── ajax: slug 제안 ───────────────────────────────────────────────
if ($action === 'slug') {
    want_post(); check_csrf();
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(admin_suggest_slug((string)($_POST['name'] ?? '')),
        JSON_UNESCAPED_UNICODE);
    exit;
}

// ── ajax: 실시간 미리보기 (본문 충실도) ──────────────────────────
if ($action === 'preview') {
    want_post(); check_csrf();
    $id = (string)($_POST['id'] ?? '');
    $abs = require_post_abs($id);
    $ext = ($_POST['ext'] ?? 'md') === 'html' ? 'html' : 'md';
    $content = (string)($_POST['content'] ?? '');
    // slug 은 (편집 중인) raw meta 우선 — 없으면 디스크 meta.
    $metaRaw = (string)($_POST['meta'] ?? '');
    if (trim($metaRaw) === '' && is_file($abs . '/meta.yaml')) {
        $metaRaw = (string)@file_get_contents($abs . '/meta.yaml');
    }
    $slug = trim(meta_read_core($metaRaw)['slug'] ?? '');
    if ($slug === '') $slug = 'preview';

    [$ok, $body] = admin_render_body($abs, $ext, $content);

    // render_one 은 asset 을 /{slug}/... 절대경로로 낸다 (빌드 충실).
    // 미리보기에서 그 자원이 뜨도록 asset 프록시로 재지정.
    $proxy = $_SERVER['SCRIPT_NAME'] . '?a=asset&id=' . rawurlencode($id) . '&p=';
    if ($ok) {
        $body = str_replace(
            ['src="/' . $slug . '/', "src='/" . $slug . '/',
             'href="/' . $slug . '/', "href='/" . $slug . '/'],
            ['src="' . $proxy, "src='" . $proxy,
             'href="' . $proxy, "href='" . $proxy],
            $body);
    }

    $css = @file_get_contents(__DIR__ . '/src/assets/common_template.css') ?: '';
    $js  = @file_get_contents(__DIR__ . '/src/assets/imgslidebox.js') ?: '';
    header('Content-Type: text/html; charset=utf-8');
    echo "<!DOCTYPE html><html lang='ko'><head><meta charset='UTF-8'>"
       . "<meta name='viewport' content='width=device-width,initial-scale=1'>"
       . "<style>\n{$css}\n"
       . "body{padding:24px;max-width:880px;margin:0 auto}</style>"
       . "</head><body>\n{$body}\n<script>{$js}</script></body></html>";
    exit;
}

// ── 미리보기 asset 프록시 (소스 폴더에서 직접 스트림) ────────────
if ($action === 'asset') {
    $id = (string)($_GET['id'] ?? '');
    $postAbs = require_post_abs($id);
    $p = admin_safe_rel((string)($_GET['p'] ?? ''));
    if ($p === null || $p === '') { http_response_code(404); exit('no asset'); }
    $file = $postAbs . DIRECTORY_SEPARATOR . str_replace('/', DIRECTORY_SEPARATOR, $p);
    $real = realpath($file);
    $base = realpath($postAbs);
    if ($real === false || $base === false
        || !str_starts_with($real, rtrim($base, DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR)
        || !is_file($real)) {
        http_response_code(404); exit('asset not found');
    }
    header('Content-Type: ' . admin_mime($real));
    header('Content-Length: ' . filesize($real));
    header('Cache-Control: no-store');
    readfile($real);
    exit;
}

// ── 저장 (기존 글) ───────────────────────────────────────────────
if ($action === 'save') {
    want_post(); check_csrf();
    $id = (string)($_POST['id'] ?? '');
    $abs = require_post_abs($id);
    $cf = admin_content_file($abs);
    $ext = ($_POST['ext'] ?? ($cf['ext'] ?? 'md')) === 'html' ? 'html' : 'md';
    $content = (string)($_POST['content'] ?? '');
    $metaRaw = (string)($_POST['meta'] ?? '');

    $content = str_replace("\r\n", "\n", $content);
    $metaRaw = str_replace("\r\n", "\n", $metaRaw);
    $metaRaw = meta_ensure_header($metaRaw, $id);

    $target = $abs . DIRECTORY_SEPARATOR . 'content.' . $ext;
    $okC = admin_atomic_write($target, $content);
    // 확장자가 바뀌었으면 반대편 content 파일 제거 (md xor html).
    $other = $abs . DIRECTORY_SEPARATOR . 'content.' . ($ext === 'md' ? 'html' : 'md');
    if ($okC && is_file($other)) @unlink($other);
    $okM = admin_atomic_write($abs . DIRECTORY_SEPARATOR . 'meta.yaml', $metaRaw);

    redirect('?a=edit&id=' . rawurlencode($id)
        . (($okC && $okM) ? '&saved=1' : '&err=1'));
}

// ── 새 글 생성 ───────────────────────────────────────────────────
if ($action === 'create') {
    want_post(); check_csrf();
    $cat = admin_safe_rel((string)($_POST['category'] ?? ''));
    $folder = trim((string)($_POST['folder'] ?? ''));
    $slug = trim((string)($_POST['slug'] ?? ''));
    $title = trim((string)($_POST['title'] ?? ''));
    $date = trim((string)($_POST['date'] ?? date('Y-m-d')));
    $desc = trim((string)($_POST['description'] ?? ''));
    $ext = ($_POST['ext'] ?? 'md') === 'html' ? 'html' : 'md';
    $tags = array_values(array_filter(array_map('trim',
        explode(',', (string)($_POST['tags'] ?? '')))));

    $errs = [];
    if ($cat === null) $errs[] = '카테고리 경로가 올바르지 않습니다.';
    if ($folder === '' || strpbrk($folder, "/\\:*?\"<>|") !== false
        || $folder[0] === '.') $errs[] = '폴더명이 비었거나 금지 문자를 포함합니다.';
    if ($slug === '') $errs[] = 'slug 가 비었습니다.';
    if (!preg_match('/^[a-z0-9][a-z0-9\-]*$/', $slug))
        $errs[] = 'slug 는 소문자/숫자/하이픈만 (slug_one 제안값 권장).';
    if (in_array($slug, ['assets', 'search'], true))
        $errs[] = "예약 slug 입니다: {$slug} (site.yaml reserved_slugs).";
    if ($title === '') $errs[] = '제목이 비었습니다.';
    if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $date))
        $errs[] = 'date 는 YYYY-MM-DD 형식.';

    // slug 중복 검사 (전체 글 스캔).
    if (!$errs) {
        foreach (admin_scan()['posts'] as $pp) {
            $mp = admin_abs($pp['id']) . DIRECTORY_SEPARATOR . 'meta.yaml';
            if (is_file($mp)
                && meta_read_core((string)@file_get_contents($mp))['slug'] === $slug) {
                $errs[] = "slug 중복: '{$slug}' 는 이미 {$pp['id']} 가 사용 중.";
                break;
            }
        }
    }
    $newRel = ($cat === '' ? '' : $cat . '/') . $folder;
    $newAbs = admin_abs($newRel);
    if (!$errs && ($newAbs === null || file_exists($newAbs)))
        $errs[] = '대상 폴더가 이미 존재하거나 경로가 올바르지 않습니다.';

    if ($errs) {
        $_SESSION['flash_errs'] = $errs;
        redirect('?a=new');
    }
    @mkdir($newAbs, 0777, true);
    admin_atomic_write($newAbs . DIRECTORY_SEPARATOR . 'content.' . $ext, '');
    admin_atomic_write($newAbs . DIRECTORY_SEPARATOR . 'meta.yaml',
        meta_new_template([
            'slug' => $slug, 'title' => $title, 'date' => $date,
            'tags' => $tags, 'description' => $desc,
        ], $newRel));
    redirect('?a=edit&id=' . rawurlencode($newRel) . '&saved=1');
}

// ── 카테고리 이동 (폴더 rename — slug 불변이라 URL 영구) ──────────
if ($action === 'move') {
    want_post(); check_csrf();
    $id = (string)($_POST['id'] ?? '');
    $abs = require_post_abs($id);
    $target = admin_safe_rel((string)($_POST['target'] ?? ''));
    if ($target === null) { http_response_code(400); exit('대상 경로 오류'); }
    $name = basename(str_replace('\\', '/', $id));
    $destRel = ($target === '' ? '' : $target . '/') . $name;
    $destAbs = admin_abs($destRel);
    if ($destAbs === null || file_exists($destAbs)) {
        $_SESSION['flash_errs'] = ['이동 대상이 이미 존재하거나 경로 오류: ' . $destRel];
        redirect('?a=list');
    }
    @mkdir(dirname($destAbs), 0777, true);
    @rename($abs, $destAbs);
    redirect('?a=list&moved=1');
}

// ── 비공개/공개 토글 ('_' 접두) ──────────────────────────────────
if ($action === 'visibility') {
    want_post(); check_csrf();
    $id = (string)($_POST['id'] ?? '');
    $abs = require_post_abs($id);
    $name = basename(str_replace('\\', '/', $id));
    $parent = trim(dirname(str_replace('\\', '/', $id)), '.');
    $newName = $name[0] === '_' ? ltrim($name, '_') : '_' . $name;
    if ($newName === '' || $newName === '_') {
        $_SESSION['flash_errs'] = ['폴더명 토글 결과가 비어 중단.'];
        redirect('?a=list');
    }
    $destRel = ($parent === '' ? '' : $parent . '/') . $newName;
    $destAbs = admin_abs($destRel);
    if ($destAbs === null || file_exists($destAbs)) {
        $_SESSION['flash_errs'] = ['토글 대상이 이미 존재: ' . $destRel];
        redirect('?a=list');
    }
    @rename($abs, $destAbs);
    redirect('?a=list&vis=1');
}

// ── 삭제 → .trash 이동 (빌더 자동 제외, 복구 가능) ───────────────
if ($action === 'delete') {
    want_post(); check_csrf();
    $id = (string)($_POST['id'] ?? '');
    $abs = require_post_abs($id);
    $trash = admin_trash_dir();
    @mkdir($trash, 0777, true);
    $name = basename(str_replace('\\', '/', $id));
    $dest = $trash . DIRECTORY_SEPARATOR
        . date('Ymd-His') . '__' . str_replace(['/', '\\'], '_', $id);
    @rename($abs, $dest);
    redirect('?a=list&deleted=1');
}

// ── 원클릭 빌드 ──────────────────────────────────────────────────
if ($action === 'build') {
    want_post(); check_csrf();
    $clean = !empty($_POST['clean']);
    [$code, $out, $err] = admin_run_build($clean);
    $title = '빌드 ' . ($code === 0 ? '성공' : "실패 (exit {$code})");
    $bodyOut = trim($out . "\n" . $err);
    require __DIR__ . '/src/admin/views/build.php';
    exit;
}

// ── 새 글 폼 ─────────────────────────────────────────────────────
if ($action === 'new') {
    $scan = admin_scan();
    $flashErrs = $_SESSION['flash_errs'] ?? [];
    unset($_SESSION['flash_errs']);
    require __DIR__ . '/src/admin/views/new.php';
    exit;
}

// ── 편집기 ───────────────────────────────────────────────────────
if ($action === 'edit') {
    $id = (string)($_GET['id'] ?? '');
    $abs = require_post_abs($id);
    $cf = admin_content_file($abs);
    $bothContent = is_file($abs . '/content.md') && is_file($abs . '/content.html');
    $ext = $cf['ext'] ?? 'md';
    $content = $cf ? (string)@file_get_contents($cf['path']) : '';
    $metaRaw = is_file($abs . '/meta.yaml')
        ? (string)@file_get_contents($abs . '/meta.yaml') : '';
    $core = meta_read_core($metaRaw);
    $scan = admin_scan();
    $saved = !empty($_GET['saved']);
    $err = !empty($_GET['err']);
    require __DIR__ . '/src/admin/views/edit.php';
    exit;
}

// ── 목록 (기본) ──────────────────────────────────────────────────
$scan = admin_scan();
$trash = admin_scan_trash();
$flashErrs = $_SESSION['flash_errs'] ?? [];
unset($_SESSION['flash_errs']);
require __DIR__ . '/src/admin/views/list.php';

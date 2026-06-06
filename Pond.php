<?php
/**
 * Heron — 로컬 글쓰기 admin "Pond" (v1.5.0).
 *
 * 이 파일은 Heron.py 와 같은 위치(버전 폴더 루트)의 *얇은 라우터* 일
 * 뿐, 로직은 전부 system/admin/ 안에 있다 (Heron.py = 얇은 진입점 +
 * system/scripts/ 패턴 미러). 빌더는 user/Articles/ 만 스캔하므로 이
 * 파일과 system/admin/ 은 dist 에 새지 않는다 (산출물 byte-불변).
 *
 * 실행 (버전 폴더에서):
 *     php -S 127.0.0.1:8001 Pond.php
 *   브라우저: http://127.0.0.1:8001/
 *
 * 보안: **로컬 전용 단일 사용자 도구.** PHP 내장 서버(cli-server)
 * + 루프백에서만 동작 — 그 외 SAPI/원격이면 즉시 403. 배포(§13)는
 * dist/ 만 올리므로 Pond.php·system/admin/ 은 빌드 머신을 떠나지
 * 않는다. 그래도 실수로 서버에 놓여도 열리지 않게 다층 가드를 둔다.
 * **절대 공개 서버에 두지 말 것.**
 */
declare(strict_types=1);

// ── 다층 보안 가드 ────────────────────────────────────────────────
$sapi = php_sapi_name();
$remote = $_SERVER['REMOTE_ADDR'] ?? '';
$loopback = in_array($remote, ['127.0.0.1', '::1', ''], true);
if ($sapi !== 'cli-server' || !$loopback) {
    http_response_code(403);
    header('Content-Type: text/plain; charset=utf-8');
    exit("403 — Pond runs only on the local PHP built-in server "
        . "(php -S 127.0.0.1:8001 Pond.php). (sapi={$sapi})");
}

require_once __DIR__ . '/system/admin/lib/fs.php';
require_once __DIR__ . '/system/admin/lib/proc.php';
require_once __DIR__ . '/system/admin/lib/metayaml.php';
require_once __DIR__ . '/system/admin/lib/articles.php';
require_once __DIR__ . '/system/admin/lib/i18n.php';

// 도구 언어(user/.heron/locale, 없으면 ko)로 admin UI 문자열을 적재한다.
// 이후 모든 뷰/라우트에서 t('admin.…') 가 쓰인다. (Surface 2)
i18n_init(i18n_read_tool_locale(__DIR__));

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
        http_response_code(404); exit(t('admin.error.post_not_found', ['id' => h($id)]));
    }
    return $abs;
}

$action = $_GET['a'] ?? 'home';

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

    $css = @file_get_contents(__DIR__ . '/user/styles/common_template.css') ?: '';
    $js  = @file_get_contents(__DIR__ . '/system/runtime/imgslidebox.js') ?: '';
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

// ── ajax: 배포 미리보기 '수정' 파일 한 개의 unified diff (v1.13.0) ─────
// '이전' 내용은 로컬 dist 에 없고 원격에만 있어, 사용자가 클릭한 그 파일만
// Heron.py --deploy-diff 가 서버에서 cat 해 로컬 dist 본과 비교한다. 경로는
// asset 액션과 동일한 방식으로 정규화·realpath 경계 검증(dist 안 + is_file)해야
// 한다. 경계를 벗어나면 가져오기 자체를 안 하고 {kind:'gone'} 으로 우아하게 응답.
if ($action === 'deploy_diff') {
    want_post(); check_csrf();
    header('Content-Type: application/json; charset=utf-8');
    $rel = admin_safe_rel((string)($_POST['path'] ?? ''));
    if ($rel === null || $rel === '') {
        echo json_encode(['kind' => 'error', 'message' => t('admin.deploy_diff.err.path')],
            JSON_UNESCAPED_UNICODE);
        exit;
    }
    $dist = admin_base_dir() . DIRECTORY_SEPARATOR . 'dist';
    $file = $dist . DIRECTORY_SEPARATOR . str_replace('/', DIRECTORY_SEPARATOR, $rel);
    $real = realpath($file);
    $baseReal = realpath($dist);
    if ($baseReal === false || $real === false
        || !str_starts_with($real, rtrim($baseReal, DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR)
        || !is_file($real)) {
        echo json_encode(['kind' => 'gone', 'path' => $rel], JSON_UNESCAPED_UNICODE);
        exit;
    }
    [$code, $out, $err] = admin_deploy_diff($rel);
    $j = json_decode(trim($out), true);
    echo is_array($j)
        ? json_encode($j, JSON_UNESCAPED_UNICODE)
        : json_encode(['kind' => 'error',
                       'message' => trim($err) !== '' ? trim($err) : t('admin.deploy_diff.err.run')],
            JSON_UNESCAPED_UNICODE);
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
    if ($cat === null) $errs[] = t('admin.create.err.category');
    if ($folder === '' || strpbrk($folder, "/\\:*?\"<>|") !== false
        || $folder[0] === '.') $errs[] = t('admin.create.err.folder');
    if ($slug === '') $errs[] = t('admin.create.err.slug_empty');
    if (!preg_match('/^[a-z0-9][a-z0-9\-]*$/', $slug))
        $errs[] = t('admin.create.err.slug_format');
    if (in_array($slug, ['assets', 'search'], true))
        $errs[] = t('admin.create.err.slug_reserved', ['slug' => $slug]);
    if ($title === '') $errs[] = t('admin.create.err.title_empty');
    if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $date))
        $errs[] = t('admin.create.err.date_format');

    // slug 중복 검사 (전체 글 스캔).
    if (!$errs) {
        foreach (admin_scan()['posts'] as $pp) {
            $mp = admin_abs($pp['id']) . DIRECTORY_SEPARATOR . 'meta.yaml';
            if (is_file($mp)
                && meta_read_core((string)@file_get_contents($mp))['slug'] === $slug) {
                $errs[] = t('admin.create.err.slug_dup', ['slug' => $slug, 'id' => $pp['id']]);
                break;
            }
        }
    }
    $newRel = ($cat === '' ? '' : $cat . '/') . $folder;
    $newAbs = admin_abs($newRel);
    if (!$errs && ($newAbs === null || file_exists($newAbs)))
        $errs[] = t('admin.create.err.dest_exists');

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
    if ($target === null) { http_response_code(400); exit(t('admin.error.target_path')); }
    // 드롭다운이 현재 카테고리를 기본 선택하므로, 같은 대상 제출 = 이동 없음.
    $parent = trim(dirname(str_replace('\\', '/', $id)), '.');
    if ($target === $parent) redirect('?a=list');
    $name = basename(str_replace('\\', '/', $id));
    $destRel = ($target === '' ? '' : $target . '/') . $name;
    $destAbs = admin_abs($destRel);
    if ($destAbs === null || file_exists($destAbs)) {
        $_SESSION['flash_errs'] = [t('admin.move.err.dest_exists', ['dest' => $destRel])];
        redirect('?a=list');
    }
    @mkdir(dirname($destAbs), 0777, true);
    @rename($abs, $destAbs);
    // hl=새 경로 → 목록에서 그 행의 '경로' 칸을 한 번 반짝(이동 인지). #moved 로 스크롤.
    redirect('?a=list&moved=1&hl=' . rawurlencode($destRel) . '#moved');
}

// ── 비공개/공개 토글 ('_' 접두) ──────────────────────────────────
if ($action === 'visibility') {
    want_post(); check_csrf();
    $id = (string)($_POST['id'] ?? '');
    $abs = require_post_abs($id);
    $name = basename(str_replace('\\', '/', $id));
    $parent = trim(dirname(str_replace('\\', '/', $id)), '.');
    $newName = $name[0] === '_' ? substr($name, 1) : '_' . $name;
    if ($newName === '' || $newName === '_') {
        $_SESSION['flash_errs'] = [t('admin.visibility.err.empty')];
        redirect('?a=list');
    }
    $destRel = ($parent === '' ? '' : $parent . '/') . $newName;
    $destAbs = admin_abs($destRel);
    if ($destAbs === null || file_exists($destAbs)) {
        $_SESSION['flash_errs'] = [t('admin.visibility.err.dest_exists', ['dest' => $destRel])];
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
    $title = t('admin.build.title', ['result' => $code === 0
        ? t('admin.build.title.ok')
        : t('admin.build.title.fail', ['code' => $code])]);
    $bodyOut = trim($out . "\n" . $err);
    require __DIR__ . '/system/admin/views/build.php';
    exit;
}

// ── dist 서버 배포 (v1.7.0) — rclone SFTP 증분 동기화 ────────────
if ($action === 'deploy') {
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        want_post(); check_csrf();
        // stage=apply 만 실제 sync(삭제 포함). 그 외(미지정 포함)=미리보기.
        $stage = (($_POST['stage'] ?? '') === 'apply') ? 'apply' : 'preview';
        $dryRun = ($stage === 'preview');
        // 스트리밍 응답: 출력 버퍼를 끄고 자식 출력을 한 줄씩 흘려보낸다
        // (첫 ~157MB 전송이 수 분 걸려도 진행이 실시간으로 보이게).
        while (ob_get_level() > 0) { @ob_end_flush(); }
        ob_implicit_flush(true);
        require __DIR__ . '/system/admin/views/deploy_run.php';
        exit;
    }
    // GET → 랜딩: 설정 상태 패널 + 미리보기 버튼 (적용은 미리보기 뒤에만).
    $deployCfg = admin_deploy_config();
    $deployExample = admin_deploy_example_exists();
    require __DIR__ . '/system/admin/views/deploy.php';
    exit;
}

// ── 설정 (v1.8.0) — 배포(deploy.json) 폼 + 사이트(site.yaml) 원문 편집 ─────
if ($action === 'settings') {
    $deployCfg = admin_deploy_config();
    $deployExample = admin_deploy_example_exists();
    // deploy.json 부재 시 견본(example) 값으로 폼을 채워 최초 작성을 돕는다.
    $deploySeed = [];
    if ($deployCfg === null && $deployExample) {
        $j = json_decode((string)@file_get_contents(admin_deploy_example_path()), true);
        if (is_array($j)) $deploySeed = $j;
    }
    // site.yaml: 검증 실패로 되돌아온 편집 버퍼가 있으면 그것을 보여 편집을
    // 보존한다 (없으면 디스크 원문). 플래시는 한 번 쓰고 즉시 소거.
    $siteYaml = $_SESSION['site_buffer']
        ?? (string)@file_get_contents(admin_site_yaml_path());
    $siteErr = (string)($_SESSION['site_err'] ?? '');
    $deployErrs = $_SESSION['flash_deploy_errs'] ?? [];
    unset($_SESSION['site_buffer'], $_SESSION['site_err'], $_SESSION['flash_deploy_errs']);
    $deploySaved = !empty($_GET['deploy_saved']);
    $siteSaved = !empty($_GET['site_saved']);
    require __DIR__ . '/system/admin/views/settings.php';
    exit;
}

// ── 배포 설정 저장 (v1.8.0) — 검증 후 deploy.json 기록 (직전본 백업) ──────
if ($action === 'settings_deploy') {
    want_post(); check_csrf();
    [$ok, $errs] = admin_save_deploy_config($_POST);
    if (!$ok) { $_SESSION['flash_deploy_errs'] = $errs; redirect('?a=settings'); }
    redirect('?a=settings&deploy_saved=1');
}

// ── 사이트 설정 저장 (v1.8.0) — 빌드와 동일 검증 통과해야 commit ──────────
if ($action === 'settings_site') {
    want_post(); check_csrf();
    $candidate = str_replace("\r\n", "\n", (string)($_POST['site'] ?? ''));
    [$valid, $msg] = admin_validate_site_yaml($candidate);
    if (!$valid) {
        $_SESSION['site_buffer'] = $candidate;   // 편집 보존 — 디스크는 불변.
        $_SESSION['site_err'] = $msg;
        redirect('?a=settings');
    }
    $path = admin_site_yaml_path();
    if (!admin_backup_file($path, 'site') || !admin_atomic_write($path, $candidate)) {
        $_SESSION['site_buffer'] = $candidate;
        $_SESSION['site_err'] = t('admin.site.err.write');
        redirect('?a=settings');
    }
    redirect('?a=settings&site_saved=1');
}

// ── 도구 언어 저장 (v1.9.0) — user/.heron/locale 한 줄에 로케일 기록 ──────
if ($action === 'settings_locale') {
    want_post(); check_csrf();
    $locale = trim((string)($_POST['locale'] ?? ''));
    // 존재하는 로케일 폴더만 허용 (임의 값 차단).
    if (!in_array($locale, i18n_available_locales(), true)) {
        $_SESSION['flash_errs'] = [t('admin.settings.locale.err.invalid')];
        redirect('?a=settings');
    }
    $path = __DIR__ . '/user/.heron/locale';
    if (!admin_atomic_write($path, $locale . "\n")) {
        $_SESSION['flash_errs'] = [t('admin.settings.locale.err.write')];
        redirect('?a=settings');
    }
    redirect('?a=settings&locale_saved=1');
}

// ── 업데이트 확인 (v1.6.0) — GitHub 최신 버전 조회, 캐시 갱신 후 목록 복귀 ─
if ($action === 'checkupdate') {
    want_post(); check_csrf();
    admin_run_heron(['--check-update']);   // user/.heron/update.json 갱신
    redirect('?a=list&checked=1');
}

// ── 업데이트 실행 (v1.6.0) — 다운로드 → 오버레이 → 마이그레이션 ──────────
if ($action === 'update') {
    want_post(); check_csrf();
    [$code, $out, $err] = admin_run_heron(['--update']);
    $title = t('admin.update.title', ['result' => $code === 0
        ? t('admin.update.title.ok')
        : t('admin.update.title.fail', ['code' => $code])]);
    $bodyOut = trim($out . "\n" . $err);
    require __DIR__ . '/system/admin/views/update.php';
    exit;
}

// ── 새 글 폼 ─────────────────────────────────────────────────────
if ($action === 'new') {
    $scan = admin_scan();
    $flashErrs = $_SESSION['flash_errs'] ?? [];
    unset($_SESSION['flash_errs']);
    require __DIR__ . '/system/admin/views/new.php';
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
    require __DIR__ . '/system/admin/views/edit.php';
    exit;
}

// ── 홈 / 시스템 개요 (v1.8.0, 기본) — 브랜드 클릭 시 도착하는 메인 페이지 ──
if ($action === 'home') {
    $scan = admin_scan();
    $ver = admin_program_version();
    $postCount = count($scan['posts']);
    $catCount = count(array_filter($scan['categories'], static fn($c) => $c !== ''));
    $hasDeploy = is_file(admin_deploy_config_path());
    $hasSiteYaml = is_file(admin_site_yaml_path());
    require __DIR__ . '/system/admin/views/home.php';
    exit;
}

// ── 목록 ─────────────────────────────────────────────────────────
$scan = admin_scan();
$trash = admin_scan_trash();
$flashErrs = $_SESSION['flash_errs'] ?? [];
unset($_SESSION['flash_errs']);
$updateInfo = admin_read_update_cache();   // v1.6.0 업데이트 배너용 (캐시)
require __DIR__ . '/system/admin/views/list.php';

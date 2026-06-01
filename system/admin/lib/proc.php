<?php
// 파이썬 서브프로세스 실행 (admin v1.1.0).
// admin 은 마크다운/slug 를 PHP 로 재구현하지 않는다 — 빌드가 쓰는 실제
// scripts.* 를 render_one.py / slug_one.py 로 호출하고, 원클릭 빌드는
// Heron.py 를 그대로 돌린다 (설계 원칙 6·9 단일 진실원 보존).

declare(strict_types=1);

/** 사용할 python 실행 인자 벡터. ['python'] 또는 ['py','-3']. */
function admin_python(): array {
    static $cached = null;
    if ($cached !== null) return $cached;
    foreach ([['python'], ['python3'], ['py', '-3']] as $cand) {
        $cmd = array_merge($cand, ['-c', 'import sys;print(sys.version)']);
        if (admin_proc($cmd, null, null)[0] === 0) { return $cached = $cand; }
    }
    return $cached = ['python']; // 폴백 — 실패 메시지는 호출부에서 표면화
}

/**
 * proc_open 으로 명령 실행. Windows 안전 (bypass_shell).
 * 반환: [exitCode:int, stdout:string, stderr:string].
 */
function admin_proc(array $argv, ?string $stdin, ?string $cwd): array {
    $desc = [
        0 => ['pipe', 'r'],
        1 => ['pipe', 'w'],
        2 => ['pipe', 'w'],
    ];
    $opts = ['bypass_shell' => true];
    $proc = @proc_open($argv, $desc, $pipes, $cwd, null, $opts);
    if (!is_resource($proc)) return [-1, '', 'proc_open 실패'];

    if ($stdin !== null && $stdin !== '') {
        fwrite($pipes[0], $stdin);
    }
    fclose($pipes[0]);

    stream_set_blocking($pipes[1], true);
    stream_set_blocking($pipes[2], true);
    $out = stream_get_contents($pipes[1]);
    $err = stream_get_contents($pipes[2]);
    fclose($pipes[1]);
    fclose($pipes[2]);
    $code = proc_close($proc);
    return [$code, $out ?? '', $err ?? ''];
}

/** <verdir>/system/admin/<script> 절대경로. */
function admin_pyscript(string $name): string {
    return __DIR__ . DIRECTORY_SEPARATOR . '..' . DIRECTORY_SEPARATOR . $name;
}

/**
 * render_one.py 로 글 본문 렌더. $contentText 가 미저장 편집 버퍼.
 * 반환: [ok:bool, html:string].
 */
function admin_render_body(string $sourceDirAbs, string $ext, string $contentText): array {
    $argv = array_merge(
        admin_python(),
        [admin_pyscript('render_one.py'), $sourceDirAbs, '--ext', $ext]
    );
    [$code, $out, $err] = admin_proc($argv, $contentText, admin_base_dir());
    if ($code === 0) return [true, $out];
    // render_one.py 는 실패 시에도 사람이 읽을 HTML 조각을 stdout 에 낸다.
    $msg = $out !== '' ? $out : ('<pre>' . htmlspecialchars($err) . '</pre>');
    return [false, $msg];
}

/** slug_one.py 로 폴더명 → slug 제안. 반환: ['slug'=>..,'non_ascii'=>bool]. */
function admin_suggest_slug(string $name): array {
    $argv = array_merge(admin_python(), [admin_pyscript('slug_one.py'), $name]);
    [$code, $out] = admin_proc($argv, null, admin_base_dir());
    $j = json_decode(trim($out), true);
    if ($code !== 0 || !is_array($j)) return ['slug' => '', 'non_ascii' => false];
    return ['slug' => (string)($j['slug'] ?? ''),
            'non_ascii' => (bool)($j['non_ascii'] ?? false)];
}

/** 원클릭 빌드: python Heron.py [--clean]. 반환 [code,out,err]. */
function admin_run_build(bool $clean): array {
    $argv = array_merge(
        admin_python(),
        [admin_base_dir() . DIRECTORY_SEPARATOR . 'Heron.py']
    );
    if ($clean) $argv[] = '--clean';
    return admin_proc($argv, null, admin_base_dir());
}

/**
 * python Heron.py <flags...> 호출 (v1.6.0 — 버전/업데이트 액션).
 * 빌드와 동일 패턴 — 로직은 Python 엔진에, Pond 는 얇은 트리거.
 * 반환 [code,out,err].
 */
function admin_run_heron(array $flags): array {
    $argv = array_merge(
        admin_python(),
        [admin_base_dir() . DIRECTORY_SEPARATOR . 'Heron.py'],
        $flags
    );
    return admin_proc($argv, null, admin_base_dir());
}

/**
 * proc_open 으로 명령 실행 + stdout 을 **줄 단위로 실시간 콜백** (v1.7.0).
 * 첫 dist 배포(~157MB)는 수 분이 걸려 블로킹 출력은 UX 가 죽으므로, 자식
 * 프로세스가 한 줄 flush 할 때마다 $onLine 으로 흘려보낸다.
 *
 * 이식성: Windows 에서 stream_select() 는 proc_open 파이프(소켓 아님)에 안
 * 먹으므로 stdout 블로킹 fgets 루프를 쓴다. 자식(deploy.run)이 rclone stderr
 * 를 자기 stdout 으로 합치고 자체 로그도 stdout 으로 내므로 거의 모든 출력이
 * pipe1 로 온다 — 남은 stderr(예외/argparse)는 종료 후 드레인. 반환: exit code.
 */
function admin_proc_stream(array $argv, ?string $cwd, callable $onLine): int {
    $desc = [
        0 => ['pipe', 'r'],
        1 => ['pipe', 'w'],
        2 => ['pipe', 'w'],
    ];
    $proc = @proc_open($argv, $desc, $pipes, $cwd, null, ['bypass_shell' => true]);
    if (!is_resource($proc)) { $onLine('proc_open 실패'); return -1; }
    fclose($pipes[0]);

    stream_set_blocking($pipes[1], true);
    while (($line = fgets($pipes[1])) !== false) {
        $onLine(rtrim($line, "\r\n"));
    }
    fclose($pipes[1]);

    stream_set_blocking($pipes[2], true);
    $err = stream_get_contents($pipes[2]);
    fclose($pipes[2]);
    if ($err !== '' && $err !== false) {
        foreach (preg_split('/\r?\n/', rtrim($err)) as $l) {
            if ($l !== '') $onLine($l);
        }
    }
    return proc_close($proc);
}

/**
 * dist 배포 스트리밍: python Heron.py --deploy [--dry-run].
 * $dryRun=true 면 미리보기(서버 변경 0), false 면 실제 sync(삭제 포함).
 * 반환: rclone/Heron exit code (0=성공).
 */
function admin_deploy_stream(bool $dryRun, callable $onLine): int {
    $argv = array_merge(
        admin_python(),
        [admin_base_dir() . DIRECTORY_SEPARATOR . 'Heron.py', '--deploy']
    );
    if ($dryRun) $argv[] = '--dry-run';
    return admin_proc_stream($argv, admin_base_dir(), $onLine);
}

/** user/.heron/deploy.json 절대경로. */
function admin_deploy_config_path(): string {
    return admin_heron_dir() . DIRECTORY_SEPARATOR . 'deploy.json';
}

/** user/.heron/deploy.example.json 절대경로. */
function admin_deploy_example_path(): string {
    return admin_heron_dir() . DIRECTORY_SEPARATOR . 'deploy.example.json';
}

/** user/.heron/deploy.json 을 표시용으로 읽는다 (없거나 깨지면 null). */
function admin_deploy_config(): ?array {
    $p = admin_deploy_config_path();
    if (!is_file($p)) return null;
    $j = json_decode((string)@file_get_contents($p), true);
    return is_array($j) ? $j : null;
}

/** 배포 설정 견본(deploy.example.json) 존재 여부. */
function admin_deploy_example_exists(): bool {
    return is_file(admin_deploy_example_path());
}

/**
 * 배포 설정(deploy.json) 저장 (v1.8.0 설정창). 들어온 값을 정규화·검증한
 * 뒤 pretty JSON 으로 원자적 저장. known_hosts_path 는 빈 값이면 생략한다
 * (deploy.run 이 ~/.ssh/known_hosts 로 폴백). 반환: [ok:bool, errs:string[]].
 * 개인키 자체는 받지 않는다 — 저장소 밖 OS 표준 위치의 *경로*만 보관.
 */
function admin_save_deploy_config(array $in): array {
    $host = trim((string)($in['host'] ?? ''));
    $user = trim((string)($in['user'] ?? ''));
    $portRaw = trim((string)($in['port'] ?? '22'));
    $remote = trim((string)($in['remote_path'] ?? ''));
    $key = trim((string)($in['ssh_key_path'] ?? ''));
    $known = trim((string)($in['known_hosts_path'] ?? ''));

    $errs = [];
    if ($host === '') $errs[] = t('admin.deploy_cfg.err.host_empty');
    if ($user === '') $errs[] = t('admin.deploy_cfg.err.user_empty');
    if ($remote === '') $errs[] = t('admin.deploy_cfg.err.remote_empty');
    if ($key === '') $errs[] = t('admin.deploy_cfg.err.key_empty');
    if (!preg_match('/^\d{1,5}$/', $portRaw) || (int)$portRaw < 1 || (int)$portRaw > 65535)
        $errs[] = t('admin.deploy_cfg.err.port_range');
    // ssh_key_path 의 실제 존재는 검증하지 않는다 — 다른 머신/아직 미생성
    // 경로일 수 있어 차단하면 footgun. 키가 정말 없으면 배포(rclone) 시점에
    // 명확히 실패하므로 여기선 형식·필수값만 본다.
    if ($errs) return [false, $errs];

    $cfg = [
        'host' => $host,
        'user' => $user,
        'port' => (int)$portRaw,
        'remote_path' => $remote,
        'ssh_key_path' => $key,
    ];
    if ($known !== '') $cfg['known_hosts_path'] = $known;

    $path = admin_deploy_config_path();
    if (!admin_backup_file($path, 'deploy'))
        return [false, [t('admin.deploy_cfg.err.backup')]];
    $json = json_encode($cfg,
        JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    if (!admin_atomic_write($path, $json . "\n"))
        return [false, [t('admin.deploy_cfg.err.write')]];
    return [true, []];
}

/**
 * 후보 site.yaml 텍스트를 빌드와 동일한 경로로 검증 (v1.8.0).
 * Heron.py --check-config 에 stdin 으로 후보를 흘려 보내 디스크 site.yaml 을
 * 건드리지 않고 파싱·abort 검증만 돌린다 — Pond 저장 게이트. 빌드와 같은
 * Builder._apply_site_config 을 재사용하므로 '검증 통과 → 빌드 실패' 불일치가
 * 없다. 반환: [ok:bool, message:string] (실패 시 [ABORT]/stderr 를 그대로).
 */
function admin_validate_site_yaml(string $candidate): array {
    $argv = array_merge(
        admin_python(),
        [admin_base_dir() . DIRECTORY_SEPARATOR . 'Heron.py', '--check-config']
    );
    [$code, $out, $err] = admin_proc($argv, $candidate, admin_base_dir());
    $msg = trim($out . "\n" . $err);
    return [$code === 0, $msg];
}

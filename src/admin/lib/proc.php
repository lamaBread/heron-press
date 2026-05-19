<?php
// 파이썬 서브프로세스 실행 (admin v1.1.0).
// admin 은 마크다운/slug 를 PHP 로 재구현하지 않는다 — 빌드가 쓰는 실제
// scripts.* 를 render_one.py / slug_one.py 로 호출하고, 원클릭 빌드는
// build.py 를 그대로 돌린다 (설계 원칙 6·9 단일 진실원 보존).

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

/** <verdir>/src/admin/<script> 절대경로. */
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

/** 원클릭 빌드: python build.py [--clean]. 반환 [code,out,err]. */
function admin_run_build(bool $clean): array {
    $argv = array_merge(
        admin_python(),
        [admin_base_dir() . DIRECTORY_SEPARATOR . 'build.py']
    );
    if ($clean) $argv[] = '--clean';
    return admin_proc($argv, null, admin_base_dir());
}

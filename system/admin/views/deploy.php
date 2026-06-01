<?php
// dist 배포 랜딩 뷰 (v1.7.0). 변수: $deployCfg(?array), $deployExample(bool).
// 설정 상태를 보여 주고 ① 미리보기(dry-run) 로 funnel 진입. 실제 적용은
// 미리보기 결과 화면(deploy_run.php)에서만 노출 — 2단계 안전 게이트.
declare(strict_types=1);
require_once __DIR__ . '/layout.php';
$self = $_SERVER['SCRIPT_NAME'];
admin_head('배포');

$keyMask = static function (?string $p): string {
    $p = trim((string)$p);
    if ($p === '') return '(미설정)';
    $name = basename(str_replace('\\', '/', $p));
    return '…/' . $name;   // 전체 경로 대신 파일명만 (마스킹)
};
?>
<h2 style="margin:0 0 4px">dist 서버 배포</h2>
<p class="muted" style="margin:0 0 16px">
  빌드된 <code class="k">dist/</code> 를 rclone(SFTP)으로 서버에 <strong>증분
  동기화</strong>합니다 — 바뀐 파일만 올리고, 서버에만 남은 옛 파일은 지웁니다.
  먼저 <strong>① 미리보기</strong>로 보낼·지울 목록을 확인한 뒤
  <strong>② 적용</strong>합니다.
</p>

<?php if ($deployCfg === null): ?>
  <div class="flash err">
    <strong>배포 설정이 없습니다.</strong>
    <code class="k">user/.heron/deploy.json</code> 이 필요합니다.
    <?php if ($deployExample): ?>
      같은 폴더의 <code class="k">deploy.example.json</code> 을 복사해
      값을 채우세요(개인키는 넣지 말고 <em>경로만</em>).
    <?php else: ?>
      견본이 보이지 않습니다 — <code class="k">python Heron.py --migrate</code>
      를 한 번 실행하면 <code class="k">deploy.example.json</code> 이 시드됩니다.
    <?php endif; ?>
  </div>
  <table style="margin:0 0 16px">
    <tr><th>필수 키</th><th>설명</th></tr>
    <tr><td class="mono">host</td><td>서버 호스트명 (예: your-domain.com)</td></tr>
    <tr><td class="mono">user</td><td>SSH 사용자</td></tr>
    <tr><td class="mono">port</td><td>SSH 포트 (기본 22)</td></tr>
    <tr><td class="mono">remote_path</td><td>서버 DocumentRoot (예: /var/www/your-domain.com)</td></tr>
    <tr><td class="mono">ssh_key_path</td><td>개인키 <em>경로</em> (저장소 밖 OS 표준 위치)</td></tr>
    <tr><td class="mono">known_hosts_path</td><td>선택 — 생략 시 <code class="k">~/.ssh/known_hosts</code></td></tr>
  </table>
<?php else: ?>
  <table style="margin:0 0 16px">
    <tr><th>항목</th><th>값</th></tr>
    <tr><td class="mono">host</td><td class="mono"><?= h((string)($deployCfg['host'] ?? '')) ?></td></tr>
    <tr><td class="mono">user</td><td class="mono"><?= h((string)($deployCfg['user'] ?? '')) ?></td></tr>
    <tr><td class="mono">port</td><td class="mono"><?= h((string)($deployCfg['port'] ?? 22)) ?></td></tr>
    <tr><td class="mono">remote_path</td><td class="mono"><?= h((string)($deployCfg['remote_path'] ?? '')) ?></td></tr>
    <tr><td class="mono">ssh_key_path</td><td class="mono"><?= h($keyMask($deployCfg['ssh_key_path'] ?? '')) ?></td></tr>
    <tr><td class="mono">known_hosts_path</td><td class="mono"><?= h(trim((string)($deployCfg['known_hosts_path'] ?? '')) ?: '~/.ssh/known_hosts (기본)') ?></td></tr>
  </table>
<?php endif; ?>

<div class="flash" style="background:#fff7e6;border:1px solid #f0d9a8;color:#7a5b00">
  <strong>알아두기</strong>
  <ul style="margin:6px 0 0">
    <li><strong>호스트키 등록</strong> — 최초 1회 <code class="k">ssh user@host</code> 로
        접속해 호스트키를 <code class="k">known_hosts</code> 에 등록해야 합니다
        (rclone 의 호스트키 검증 = MITM 방어). 미리보기도 서버에 접속하므로
        등록 전이면 미리보기에서 막힙니다.</li>
    <li><strong>먼저 빌드</strong> — 배포는 현재 <code class="k">dist/</code> 를 그대로
        올립니다. 최신 글을 반영하려면 상단 <strong>빌드</strong> 후 배포하세요.</li>
    <li><strong>첫 배포는 느립니다</strong> — 전체 자산(~157MB) 첫 전송은 수 분 걸릴 수
        있고, 그동안 이 창은 진행 로그를 실시간으로 흘립니다. 이후 배포는 증분이라 빠릅니다.</li>
  </ul>
</div>

<div class="row" style="margin-bottom:12px">
  <a class="btn" href="<?= h($self) ?>?a=list">← 목록</a>
  <form method="post" action="<?= h($self) ?>?a=deploy" style="display:inline">
    <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
    <input type="hidden" name="stage" value="preview">
    <button class="primary" type="submit" <?= $deployCfg === null ? 'disabled' : '' ?>>
      ① 미리보기 (dry-run)
    </button>
  </form>
</div>
<?php admin_foot();

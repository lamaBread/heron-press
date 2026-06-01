<?php
// dist 배포 실행/스트리밍 뷰 (v1.7.0). 변수: $stage('preview'|'apply'), $dryRun(bool).
// 출력 버퍼는 Pond.php 가 이미 끈 상태. 자식 프로세스가 한 줄 flush 할 때마다
// <pre> 에 흘려보내고, 종료 코드(exit)를 안 뒤 다음 단계 버튼을 노출한다.
declare(strict_types=1);
require_once __DIR__ . '/layout.php';
$self = $_SERVER['SCRIPT_NAME'];
$isApply = ($stage === 'apply');
admin_head($isApply ? '배포 — 적용' : '배포 — 미리보기');
?>
<div class="flash" style="background:#eef;border:1px solid #ccd">
  <strong><?= $isApply ? '② 실제 동기화 진행 중' : '① 미리보기 (dry-run)' ?></strong>
  — <code class="k">python Heron.py --deploy<?= $dryRun ? ' --dry-run' : '' ?></code>.
  <?= $isApply
      ? '서버를 실제로 갱신합니다 (바뀐 파일 전송 + 서버 고아 파일 삭제).'
      : '서버는 변경하지 않고 “보낼/지울” 목록만 계산합니다.' ?>
  진행 로그가 아래에 실시간으로 흐릅니다.
</div>
<pre id="log" style="background:#0d0d12;color:#d6d6dc;padding:16px;border-radius:8px;
     overflow:auto;font:12px/1.5 ui-monospace,Consolas,monospace;
     white-space:pre-wrap"><?php
flush();
$code = admin_deploy_stream($dryRun, static function (string $line): void {
    echo htmlspecialchars($line, ENT_QUOTES, 'UTF-8') . "\n";
    @flush();
});
?></pre>

<div class="flash <?= $code === 0 ? 'ok' : 'err' ?>">
  <strong><?= $code === 0
      ? ($isApply ? '배포 완료' : '미리보기 완료')
      : "실패 (exit {$code})" ?></strong>
  <?php if ($code !== 0): ?>
    — 위 로그를 확인하세요. 흔한 원인: 호스트키 미등록(<code class="k">ssh user@host</code> 1회),
    개인키 경로/권한, <code class="k">remote_path</code> 오타, 네트워크.
  <?php elseif (!$isApply): ?>
    — 위 “Transferred/Deleted” 목록을 확인하고, 맞으면 아래 <strong>② 적용</strong>으로 진행하세요.
  <?php else: ?>
    — 서버가 <code class="k">dist/</code> 와 일치하도록 갱신되었습니다.
  <?php endif; ?>
</div>

<div class="row" style="margin-bottom:12px">
  <a class="btn" href="<?= h($self) ?>?a=list">← 목록</a>
  <form method="post" action="<?= h($self) ?>?a=deploy" style="display:inline">
    <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
    <input type="hidden" name="stage" value="preview">
    <button type="submit">다시 미리보기</button>
  </form>
  <?php if (!$isApply && $code === 0): ?>
  <form method="post" action="<?= h($self) ?>?a=deploy" style="display:inline"
        onsubmit="return confirm('서버를 실제로 갱신합니다 (서버 고아 파일 삭제 포함). 위 미리보기 목록을 확인했나요?')">
    <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
    <input type="hidden" name="stage" value="apply">
    <button class="primary" type="submit">② 이대로 적용 (실제 배포)</button>
  </form>
  <?php endif; ?>
</div>
<script>
  // 스트리밍 중 새 줄이 쌓이면 로그 하단으로 따라간다.
  (function(){ var p=document.getElementById('log'); if(p) p.scrollTop=p.scrollHeight; })();
</script>
<?php admin_foot();

<?php
// dist 배포 실행/스트리밍 뷰 (v1.7.0). 변수: $stage('preview'|'apply'), $dryRun(bool).
// 출력 버퍼는 Pond.php 가 이미 끈 상태. 자식 프로세스가 한 줄 flush 할 때마다
// <pre> 에 흘려보내고, 종료 코드(exit)를 안 뒤 다음 단계 버튼을 노출한다.
declare(strict_types=1);
require_once __DIR__ . '/layout.php';
$self = $_SERVER['SCRIPT_NAME'];
$isApply = ($stage === 'apply');
admin_head($isApply ? t('admin.deploy_run.title.apply') : t('admin.deploy_run.title.preview'));
?>
<div class="flash" style="background:#eef;border:1px solid #ccd">
  <strong><?= $isApply ? t('admin.deploy_run.banner.apply') : t('admin.deploy_run.banner.preview') ?></strong>
  — <code class="k">python Heron.py --deploy<?= $dryRun ? ' --dry-run' : '' ?></code>.
  <?= $isApply
      ? t('admin.deploy_run.banner.apply.desc')
      : t('admin.deploy_run.banner.preview.desc') ?>
  <?= t('admin.deploy_run.banner.tail') ?>
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
      ? ($isApply ? t('admin.deploy_run.result.apply.ok') : t('admin.deploy_run.result.preview.ok'))
      : t('admin.deploy_run.result.fail', ['code' => $code]) ?></strong>
  <?php if ($code !== 0): ?>
    <?= t('admin.deploy_run.result.fail.hint') ?>
  <?php elseif (!$isApply): ?>
    <?= t('admin.deploy_run.result.preview.hint') ?>
  <?php else: ?>
    <?= t('admin.deploy_run.result.apply.hint') ?>
  <?php endif; ?>
</div>

<div class="row" style="margin-bottom:12px">
  <a class="btn" href="<?= h($self) ?>?a=list"><?= h(t('admin.deploy_run.back')) ?></a>
  <form method="post" action="<?= h($self) ?>?a=deploy" style="display:inline">
    <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
    <input type="hidden" name="stage" value="preview">
    <button type="submit"><?= h(t('admin.deploy_run.again')) ?></button>
  </form>
  <?php if (!$isApply && $code === 0): ?>
  <form method="post" action="<?= h($self) ?>?a=deploy" style="display:inline"
        onsubmit="return confirm('<?= h(t('admin.deploy_run.apply.confirm')) ?>')">
    <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
    <input type="hidden" name="stage" value="apply">
    <button class="primary" type="submit"><?= h(t('admin.deploy_run.apply_btn')) ?></button>
  </form>
  <?php endif; ?>
</div>
<script>
  // 스트리밍 중 새 줄이 쌓이면 로그 하단으로 따라간다.
  (function(){ var p=document.getElementById('log'); if(p) p.scrollTop=p.scrollHeight; })();
</script>
<?php admin_foot();

<?php
// 업데이트 결과 뷰 (v1.6.0). 변수: $title, $code, $bodyOut.
declare(strict_types=1);
require_once __DIR__ . '/layout.php';
$self = $_SERVER['SCRIPT_NAME'];
admin_head($title);
?>
<div class="flash <?= $code === 0 ? 'ok' : 'err' ?>">
  <strong><?= h($title) ?></strong>
  <?= t('admin.update.banner') ?>
</div>

<?php if ($code === 0): ?>
<div class="flash" style="background:#fff7e6;border:1px solid #f0d9a8;color:#7a5b00">
  <strong><?= t('admin.update.restart.title') ?></strong>
  <?= t('admin.update.restart.body') ?>
</div>
<?php endif; ?>

<div class="row" style="margin-bottom:12px">
  <a class="btn" href="<?= h($self) ?>?a=list"><?= h(t('admin.update.back')) ?></a>
</div>
<pre style="background:#0d0d12;color:#d6d6dc;padding:16px;border-radius:8px;
     overflow:auto;max-height:70vh;font:12px/1.5 ui-monospace,Consolas,monospace;
     white-space:pre-wrap"><?= h($bodyOut !== '' ? $bodyOut : t('admin.update.empty')) ?></pre>
<?php admin_foot();

<?php
// 자가 업데이트 실행/스트리밍 뷰 (v1.6.0; v1.14.6 스트리밍 전환).
// 출력 버퍼는 Pond.php 가 이미 끈 상태. update.py 의 단계 로그(다운로드→
// 무결성→백업→오버레이→마이그레이션)가 한 줄 flush 될 때마다 <pre> 에
// 흘려보내고, 종료 코드를 안 뒤에야 결과 배너를 노출한다 (build.php 와
// 동일 구조). 이 뷰·layout·proc 는 오버레이 전에 로드가 끝나므로 페이지
// 전체가 구버전 코드로 일관되게 렌더된다 — 재시작 안내가 그 다음 단계.
declare(strict_types=1);
require_once __DIR__ . '/layout.php';
$self = $_SERVER['SCRIPT_NAME'];
admin_head(t('admin.update.title.run'));
?>
<div class="flash" style="background:#eef;border:1px solid #ccd">
  <strong><?= h(t('admin.update.banner.running')) ?></strong>
  <?= t('admin.update.banner') ?>
  <?= t('admin.log.stream_note') ?>
</div>

<?php admin_log_widget_head(t('admin.log.title'), t('admin.log.expand'), t('admin.log.collapse')); ?>
<pre id="log" class="log-peek"><?php
flush();
$any = false;
$code = admin_run_update_stream(static function (string $line) use (&$any): void {
    $any = true;
    echo htmlspecialchars($line, ENT_QUOTES, 'UTF-8') . "\n";
    @flush();
});
if (!$any) echo h(t('admin.update.empty'));
?></pre>

<div class="flash <?= $code === 0 ? 'ok' : 'err' ?>" style="margin-top:14px">
  <strong><?= h(t('admin.update.title', ['result' => $code === 0
      ? t('admin.update.title.ok')
      : t('admin.update.title.fail', ['code' => $code])])) ?></strong>
  <?php if ($code !== 0): ?><?= t('admin.update.result.fail.hint') ?><?php endif; ?>
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
<?php admin_foot();

<?php
// 원클릭 빌드 실행/스트리밍 뷰 (admin v1.1.0; v1.14.5 스트리밍 전환).
// 출력 버퍼는 Pond.php 가 이미 끈 상태. 빌더의 단계 헤더([ n/16])가 한 줄
// flush 될 때마다 <pre> 에 흘려보내고, 종료 코드를 안 뒤에야 결과 배너와
// 다음 단계 버튼을 노출한다 — 결과는 스트림이 끝나야 알 수 있으므로 배너가
// 로그 *아래*다 (deploy_run.php 와 동일 구조). 변수: $clean.
declare(strict_types=1);
require_once __DIR__ . '/layout.php';
$self = $_SERVER['SCRIPT_NAME'];
admin_head(t('admin.build.title.run'));
?>
<div class="flash" style="background:#eef;border:1px solid #ccd">
  <strong><?= h(t('admin.build.banner.running')) ?></strong>
  <?= $clean ? ' · <code class="k">--clean</code>' : '' ?>
  <?= t('admin.build.banner') ?>
  <?= t('admin.log.stream_note') ?>
</div>

<?php admin_log_widget_head(t('admin.log.title'), t('admin.log.expand'), t('admin.log.collapse')); ?>
<pre id="log" class="log-peek"><?php
flush();
$any = false;
$code = admin_run_build_stream($clean, static function (string $line) use (&$any): void {
    $any = true;
    echo htmlspecialchars($line, ENT_QUOTES, 'UTF-8') . "\n";
    @flush();
});
if (!$any) echo h(t('admin.build.empty'));
?></pre>

<div class="flash <?= $code === 0 ? 'ok' : 'err' ?>" style="margin-top:14px">
  <strong><?= h(t('admin.build.title', ['result' => $code === 0
      ? t('admin.build.title.ok')
      : t('admin.build.title.fail', ['code' => $code])])) ?></strong>
  <?php if ($code === 0): ?><?= t('admin.build.banner.ok') ?>
  <?php else: ?><?= t('admin.build.result.fail.hint') ?><?php endif; ?>
</div>

<div class="row" style="margin-bottom:12px">
  <a class="btn" href="<?= h($self) ?>?a=list"><?= h(t('admin.build.back')) ?></a>
  <form method="post" action="<?= h($self) ?>?a=build" style="display:inline">
    <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
    <?php if ($clean): ?><input type="hidden" name="clean" value="1"><?php endif; ?>
    <button type="submit"><?= $clean ? h(t('admin.build.again.clean')) : h(t('admin.build.again')) ?></button>
  </form>
</div>
<?php admin_foot();

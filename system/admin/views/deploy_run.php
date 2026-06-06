<?php
// dist 배포 실행/스트리밍 뷰 (v1.7.0; v1.12.0 접이식 로그 + dry-run 요약).
// 출력 버퍼는 Pond.php 가 이미 끈 상태. 자식 프로세스가 한 줄 flush 할 때마다
// <pre> 에 흘려보내고, 종료 코드(exit)를 안 뒤 다음 단계 버튼을 노출한다.
// 미리보기(dry-run)에선 deploy.py 가 끝에 기계용 요약 한 줄(JSON sentinel)을
// 내므로 그 줄을 가로채 로그에서 숨기고 아래에 카드·표로 시각화한다.
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

<div class="logbar">
  <span class="ttl"><?= h(t('admin.deploy_run.log.title')) ?></span>
  <button type="button" id="logtoggle"
          data-expand="<?= h(t('admin.deploy_run.log.expand')) ?>"
          data-collapse="<?= h(t('admin.deploy_run.log.collapse')) ?>"><?= h(t('admin.deploy_run.log.expand')) ?></button>
</div>
<script>
  // 스트리밍 중 라이브 추적 + 접기/펼치기. <pre> 보다 먼저 와 즉시 실행되며,
  // 접힌(log-peek) 상태일 때만 하단을 따라가고 응답 완료(load) 시 멈춘다.
  (function(){
    var $ = function(id){ return document.getElementById(id); };
    var btn = $('logtoggle');
    if (btn) btn.addEventListener('click', function(){
      var p = $('log'); if (!p) return;
      var full = p.classList.toggle('log-full');
      p.classList.toggle('log-peek', !full);
      btn.textContent = full ? btn.dataset.collapse : btn.dataset.expand;
      if (full) p.scrollTop = 0;
    });
    var follow = setInterval(function(){
      var p = $('log');
      if (p && p.classList.contains('log-peek')) p.scrollTop = p.scrollHeight;
    }, 200);
    window.addEventListener('load', function(){
      clearInterval(follow);
      var p = $('log');
      if (p && p.classList.contains('log-peek')) p.scrollTop = p.scrollHeight;
    });
  })();
</script>
<pre id="log" class="log-peek"><?php
flush();
$SENTINEL = "\x1eHERON_DEPLOY_SUMMARY\x1e";
$summary = null;
$code = admin_deploy_stream($dryRun, static function (string $line) use (&$summary, $SENTINEL): void {
    // 기계용 요약 줄은 화면 로그에서 가로채 숨기고, 나머지는 그대로 흘려보낸다.
    if (strncmp($line, $SENTINEL, strlen($SENTINEL)) === 0) {
        $summary = json_decode(substr($line, strlen($SENTINEL)), true);
        return;
    }
    echo htmlspecialchars($line, ENT_QUOTES, 'UTF-8') . "\n";
    @flush();
});
?></pre>

<?php if (!$isApply && $code === 0 && is_array($summary)):
    $hsize = static function ($n): string {
        $n = (int)$n;
        $u = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB'];
        $f = (float)$n; $i = 0;
        while ($f >= 1024 && $i < count($u) - 1) { $f /= 1024; $i++; }
        return $i === 0 ? $n . ' B' : number_format($f, 1) . ' ' . $u[$i];
    };
    $up    = $summary['upload'] ?? ['count' => 0, 'bytes' => 0];
    $del   = $summary['delete'] ?? ['count' => 0, 'bytes' => 0];
    $dirs  = $summary['dirs']   ?? ['make' => 0, 'remove' => 0, 'touch' => 0];
    $dirOps = (int)($dirs['make'] ?? 0) + (int)($dirs['remove'] ?? 0) + (int)($dirs['touch'] ?? 0);
    $warns = $summary['warnings'] ?? [];
    $junk  = $summary['junk'] ?? [];
    $byDir = $summary['by_dir'] ?? [];
    $warnCount = count($warns) + count($junk);
?>
<h3 style="margin:16px 0 4px;font-size:15px"><?= h(t('admin.deploy_run.summary.title')) ?></h3>
<div class="cards">
  <div class="card">
    <div class="lbl"><?= h(t('admin.deploy_run.summary.upload')) ?></div>
    <div class="num"><?= number_format((int)($up['count'] ?? 0)) ?></div>
    <div class="sub"><?= h($hsize($up['bytes'] ?? 0)) ?></div>
  </div>
  <div class="card<?= ((int)($del['count'] ?? 0) > 0) ? ' danger' : '' ?>">
    <div class="lbl"><?= h(t('admin.deploy_run.summary.delete')) ?></div>
    <div class="num"><?= number_format((int)($del['count'] ?? 0)) ?></div>
    <div class="sub"><?= h($hsize($del['bytes'] ?? 0)) ?></div>
  </div>
  <div class="card">
    <div class="lbl"><?= h(t('admin.deploy_run.summary.dirs')) ?></div>
    <div class="num"><?= number_format($dirOps) ?></div>
    <div class="sub"><?= h(t('admin.deploy_run.summary.dirs_detail', [
        'make' => (int)($dirs['make'] ?? 0),
        'remove' => (int)($dirs['remove'] ?? 0),
        'touch' => (int)($dirs['touch'] ?? 0)])) ?></div>
  </div>
  <div class="card<?= $warnCount > 0 ? ' warn' : '' ?>">
    <div class="lbl"><?= h(t('admin.deploy_run.summary.warnings')) ?></div>
    <div class="num"><?= number_format($warnCount) ?></div>
  </div>
</div>

<?php if ((int)($up['count'] ?? 0) === 0 && (int)($del['count'] ?? 0) === 0): ?>
<p class="muted" style="margin:0 0 8px"><?= h(t('admin.deploy_run.summary.none')) ?></p>
<?php endif; ?>

<?php if ($byDir): ?>
<h3 style="margin:18px 0 6px;font-size:14px"><?= h(t('admin.deploy_run.summary.bydir_title')) ?></h3>
<table>
  <tr>
    <th><?= h(t('admin.deploy_run.summary.col.dir')) ?></th>
    <th class="r"><?= h(t('admin.deploy_run.summary.col.files')) ?></th>
    <th class="r"><?= h(t('admin.deploy_run.summary.col.size')) ?></th>
  </tr>
  <?php foreach ($byDir as $row):
      $d = (string)($row['dir'] ?? '');
      $label = $d === '' ? t('admin.deploy_run.summary.root') : $d; ?>
  <tr>
    <td class="mono"><?= h($label) ?></td>
    <td class="r"><?= number_format((int)($row['count'] ?? 0)) ?></td>
    <td class="r mono"><?= h($hsize($row['bytes'] ?? 0)) ?></td>
  </tr>
  <?php endforeach; ?>
  <?php if (!empty($summary['by_dir_more'])): $mo = $summary['by_dir_more']; ?>
  <tr>
    <td class="muted"><?= h(t('admin.deploy_run.summary.others', ['n' => (int)($mo['dirs'] ?? 0)])) ?></td>
    <td class="r muted"><?= number_format((int)($mo['count'] ?? 0)) ?></td>
    <td class="r muted"><?= h($hsize($mo['bytes'] ?? 0)) ?></td>
  </tr>
  <?php endif; ?>
</table>
<?php endif; ?>

<?php if ($warnCount > 0): ?>
<h3 style="margin:18px 0 6px;font-size:14px"><?= h(t('admin.deploy_run.summary.warnings')) ?></h3>
<ul class="warns">
  <?php foreach ($junk as $j): ?>
  <li><?= h(t('admin.deploy_run.summary.junk', ['path' => (string)$j])) ?></li>
  <?php endforeach; ?>
  <?php foreach ($warns as $w): ?>
  <li class="mono"><?= h((string)$w) ?></li>
  <?php endforeach; ?>
</ul>
<?php endif; ?>
<?php endif; /* summary viz */ ?>

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
<?php admin_foot();

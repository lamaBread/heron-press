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
  <?= t('admin.log.stream_note') ?>
</div>

<?php admin_log_widget_head(t('admin.log.title'), t('admin.log.expand'), t('admin.log.collapse')); ?>
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
    $added = $summary['added']    ?? ['count' => 0, 'bytes' => 0];
    $modif = $summary['modified'] ?? ['count' => 0, 'bytes' => 0];
    $del   = $summary['delete']   ?? ['count' => 0, 'bytes' => 0];
    $unch  = $summary['unchanged'] ?? ['count' => 0, 'bytes' => 0];
    $warns = $summary['warnings'] ?? [];
    $junk  = $summary['junk'] ?? [];
    $byDir = $summary['by_dir'] ?? [];
    $warnCount = count($warns) + count($junk);
    $remotePath = rtrim((string)($summary['remote_path'] ?? ''), '/');
    $addedFiles = $summary['added_files'] ?? [];
    $modFiles   = $summary['modified_files'] ?? [];
    $delFiles   = $summary['deleted_files'] ?? [];
    $unchFiles  = $summary['unchanged_files'] ?? [];
    $addedN = (int)($added['count'] ?? 0);
    $modN   = (int)($modif['count'] ?? 0);
    $delN   = (int)($del['count'] ?? 0);
    $unchN  = (int)($unch['count'] ?? 0);
    // 파일 목록 한 벌 렌더: 경로(+옵션 접두) + 크기, diff 버튼(수정만), '+N개 더' 롤업.
    $fileList = static function (array $files, $more, callable $hsize,
                                bool $withDiff, string $prefix = '') {
        echo '<ul class="files">';
        foreach ($files as $f) {
            $path = (string)($f['path'] ?? '');
            echo '<li>';
            if ($withDiff) {
                echo '<button type="button" class="diffbtn" data-path="' . h($path)
                   . '">' . h(t('admin.deploy_run.diff.show')) . '</button>';
            }
            echo '<span class="fp">' . h($prefix . $path) . '</span>';
            echo '<span class="fs">' . h($hsize($f['bytes'] ?? 0)) . '</span>';
            if ($withDiff) echo '<div class="diffbox" hidden></div>';
            echo '</li>';
        }
        echo '</ul>';
        if (is_array($more) && (int)($more['count'] ?? 0) > 0) {
            echo '<p class="muted more">'
               . h(t('admin.deploy_run.detail.more', ['n' => (int)$more['count']]))
               . ' · ' . h($hsize($more['bytes'] ?? 0)) . '</p>';
        }
    };
?>
<h3 style="margin:16px 0 4px;font-size:15px"><?= h(t('admin.deploy_run.summary.title')) ?></h3>
<p class="muted" style="margin:0 0 8px;font-size:12px"><?= h(t('admin.deploy_run.summary.hint')) ?></p>
<div class="cards acc">
  <button type="button" class="card accbtn" data-panel="added" aria-expanded="false">
    <div class="lbl"><?= h(t('admin.deploy_run.summary.added')) ?></div>
    <div class="num"><?= number_format($addedN) ?></div>
    <div class="sub"><?= h($hsize($added['bytes'] ?? 0)) ?></div>
  </button>
  <button type="button" class="card accbtn" data-panel="modified" aria-expanded="false">
    <div class="lbl"><?= h(t('admin.deploy_run.summary.modified')) ?></div>
    <div class="num"><?= number_format($modN) ?></div>
    <div class="sub"><?= h($hsize($modif['bytes'] ?? 0)) ?></div>
  </button>
  <button type="button" class="card accbtn<?= $delN > 0 ? ' danger' : '' ?>" data-panel="deleted" aria-expanded="false">
    <div class="lbl"><?= h(t('admin.deploy_run.summary.delete')) ?></div>
    <div class="num"><?= number_format($delN) ?></div>
    <div class="sub"><?= h($hsize($del['bytes'] ?? 0)) ?></div>
  </button>
  <button type="button" class="card accbtn" data-panel="unchanged" aria-expanded="false">
    <div class="lbl"><?= h(t('admin.deploy_run.summary.unchanged')) ?></div>
    <div class="num"><?= number_format($unchN) ?></div>
    <div class="sub"><?= h($hsize($unch['bytes'] ?? 0)) ?></div>
  </button>
  <button type="button" class="card accbtn<?= $warnCount > 0 ? ' warn' : '' ?>" data-panel="warnings" aria-expanded="false">
    <div class="lbl"><?= h(t('admin.deploy_run.summary.warnings')) ?></div>
    <div class="num"><?= number_format($warnCount) ?></div>
  </button>
</div>

<?php if ($addedN === 0 && $modN === 0 && $delN === 0): ?>
<p class="muted" style="margin:0 0 8px"><?= h(t('admin.deploy_run.summary.none')) ?></p>
<?php endif; ?>

<div class="panels">
  <section class="panel" id="panel-added" hidden>
    <h4><?= h(t('admin.deploy_run.detail.added')) ?></h4>
    <?php if ($addedFiles) { $fileList($addedFiles, $summary['added_more'] ?? null, $hsize, false); }
          else { ?><p class="muted"><?= h(t('admin.deploy_run.detail.empty')) ?></p><?php } ?>
  </section>
  <section class="panel" id="panel-modified" hidden>
    <h4><?= h(t('admin.deploy_run.detail.modified')) ?></h4>
    <?php if ($modFiles) { $fileList($modFiles, $summary['modified_more'] ?? null, $hsize, true); }
          else { ?><p class="muted"><?= h(t('admin.deploy_run.detail.empty')) ?></p><?php } ?>
  </section>
  <section class="panel" id="panel-deleted" hidden>
    <h4><?= h(t('admin.deploy_run.detail.deleted')) ?></h4>
    <?php if ($delFiles) { ?>
    <p class="muted"><?= h(t('admin.deploy_run.detail.deleted_note')) ?></p>
    <?php $fileList($delFiles, $summary['deleted_more'] ?? null, $hsize, false,
                    $remotePath !== '' ? $remotePath . '/' : ''); }
          else { ?><p class="muted"><?= h(t('admin.deploy_run.detail.empty')) ?></p><?php } ?>
  </section>
  <section class="panel" id="panel-unchanged" hidden>
    <h4><?= h(t('admin.deploy_run.detail.unchanged')) ?></h4>
    <?php if ($unchFiles) { ?>
    <p class="muted"><?= h(t('admin.deploy_run.detail.unchanged_note')) ?></p>
    <?php $fileList($unchFiles, $summary['unchanged_more'] ?? null, $hsize, false); }
          else { ?><p class="muted"><?= h(t('admin.deploy_run.detail.empty')) ?></p><?php } ?>
  </section>
  <section class="panel" id="panel-warnings" hidden>
    <h4><?= h(t('admin.deploy_run.summary.warnings')) ?></h4>
    <?php if ($warnCount > 0): ?>
    <ul class="warns">
      <?php foreach ($junk as $j): ?>
      <li><?= h(t('admin.deploy_run.summary.junk', ['path' => (string)$j])) ?></li>
      <?php endforeach; ?>
      <?php foreach ($warns as $w): ?>
      <li class="mono"><?= h((string)$w) ?></li>
      <?php endforeach; ?>
    </ul>
    <?php else: ?><p class="muted"><?= h(t('admin.deploy_run.detail.empty')) ?></p><?php endif; ?>
  </section>
</div>

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

<script>
  // 카드=아코디언(클릭 시 그 패널만 열림) + '수정' 패널의 파일별 diff lazy fetch.
  // diff '이전'은 서버에만 있어, 클릭한 그 파일만 ?a=deploy_diff 로 받아 렌더한다.
  (function(){
    var I = <?= json_encode([
        'show' => t('admin.deploy_run.diff.show'),
        'hide' => t('admin.deploy_run.diff.hide'),
        'loading' => t('admin.deploy_run.diff.loading'),
        'identical' => t('admin.deploy_run.diff.identical'),
        'nolines' => t('admin.deploy_run.diff.nolines'),
        'binary' => t('admin.deploy_run.diff.binary'),
        'too_large' => t('admin.deploy_run.diff.too_large'),
        'gone' => t('admin.deploy_run.diff.gone'),
        'truncated' => t('admin.deploy_run.diff.truncated'),
        'error' => t('admin.deploy_run.diff.error'),
    ], JSON_UNESCAPED_UNICODE | JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_HEX_AMP) ?>;
    var SELF = <?= json_encode($self, JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_HEX_AMP) ?>;
    var CSRF = <?= json_encode($CSRF, JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_HEX_AMP) ?>;
    function esc(s){ return String(s).replace(/[&<>"']/g, function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }
    var cards = Array.prototype.slice.call(document.querySelectorAll('.accbtn'));
    var panels = Array.prototype.slice.call(document.querySelectorAll('.panel'));
    cards.forEach(function(btn){
      btn.addEventListener('click', function(){
        var open = btn.getAttribute('aria-expanded') === 'true';
        cards.forEach(function(b){ b.setAttribute('aria-expanded', 'false'); });
        panels.forEach(function(p){ p.hidden = true; });
        if (!open) {
          btn.setAttribute('aria-expanded', 'true');
          var p = document.getElementById('panel-' + btn.dataset.panel);
          if (p) p.hidden = false;
        }
      });
    });
    function renderDiff(box, d){
      var k = d && d.kind;
      var msg = { identical: I.identical, binary: I.binary, too_large: I.too_large,
                  gone: I.gone }[k];
      if (msg) { box.innerHTML = '<p class="dmsg">' + esc(msg) + '</p>'; return; }
      if (k === 'error') {
        box.innerHTML = '<p class="dmsg err">' + esc(I.error)
          + (d.message ? ' — ' + esc(d.message) : '') + '</p>'; return; }
      var hunks = (d && d.hunks) || [];
      if (!hunks.length) { box.innerHTML = '<p class="dmsg">' + esc(I.nolines) + '</p>'; return; }
      var html = '<table class="diff">';
      hunks.forEach(function(hk){
        html += '<tr class="hh"><td class="ln"></td><td class="ln"></td><td class="tx">@@ -'
              + esc(hk.old_start) + ' +' + esc(hk.new_start) + ' @@</td></tr>';
        (hk.lines || []).forEach(function(ln){
          var cls = ln.tag === '+' ? 'add' : (ln.tag === '-' ? 'del' : 'ctx');
          html += '<tr class="' + cls + '"><td class="ln">' + (ln.old == null ? '' : esc(ln.old))
                + '</td><td class="ln">' + (ln.new == null ? '' : esc(ln.new))
                + '</td><td class="tx">' + esc(ln.tag) + esc(ln.text) + '</td></tr>';
        });
      });
      html += '</table>';
      if (d.truncated) html += '<p class="dmsg">' + esc(I.truncated) + '</p>';
      box.innerHTML = html;
    }
    var modPanel = document.getElementById('panel-modified');
    if (modPanel) modPanel.addEventListener('click', function(ev){
      var btn = ev.target.closest ? ev.target.closest('.diffbtn') : null;
      if (!btn) return;
      var box = btn.parentNode.querySelector('.diffbox');
      if (!box) return;
      if (btn.dataset.loaded === '1') {
        box.hidden = !box.hidden;
        btn.textContent = box.hidden ? I.show : I.hide;
        return;
      }
      box.hidden = false;
      box.innerHTML = '<p class="dmsg">' + esc(I.loading) + '</p>';
      btn.textContent = I.hide;
      var fd = new FormData();
      fd.append('csrf', CSRF);
      fd.append('path', btn.dataset.path);
      fetch(SELF + '?a=deploy_diff', { method: 'POST', body: fd, credentials: 'same-origin' })
        .then(function(r){ return r.json(); })
        .then(function(d){ btn.dataset.loaded = '1'; renderDiff(box, d); })
        .catch(function(){ box.innerHTML = '<p class="dmsg err">' + esc(I.error) + '</p>'; });
    });
  })();
</script>
<?php endif; /* summary viz */ ?>

<div class="flash <?= $code === 0 ? 'ok' : 'err' ?>" style="margin-top:14px">
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

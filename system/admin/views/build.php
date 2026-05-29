<?php
// 빌드 결과 뷰 (admin v1.1.0). 변수: $title, $code, $bodyOut, $clean.
declare(strict_types=1);
require_once __DIR__ . '/layout.php';
$self = $_SERVER['SCRIPT_NAME'];
admin_head($title);
?>
<div class="flash <?= $code === 0 ? 'ok' : 'err' ?>">
  <strong><?= h($title) ?></strong>
  <?= $clean ? ' · <code class="k">--clean</code>' : '' ?>
  — <code class="k">python Heron.py</code> (cwd = 버전 폴더).
  <?php if ($code === 0): ?> dist/ 가 갱신되었습니다.<?php endif; ?>
</div>
<div class="row" style="margin-bottom:12px">
  <a class="btn" href="<?= h($self) ?>?a=list">← 목록</a>
  <form method="post" action="<?= h($self) ?>?a=build" style="display:inline">
    <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
    <?php if ($clean): ?><input type="hidden" name="clean" value="1"><?php endif; ?>
    <button type="submit">다시 빌드<?= $clean ? ' (--clean)' : '' ?></button>
  </form>
</div>
<pre style="background:#0d0d12;color:#d6d6dc;padding:16px;border-radius:8px;
     overflow:auto;max-height:70vh;font:12px/1.5 ui-monospace,Consolas,monospace;
     white-space:pre-wrap"><?= h($bodyOut !== '' ? $bodyOut : '(출력 없음)') ?></pre>
<?php admin_foot();

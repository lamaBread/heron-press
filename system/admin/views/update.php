<?php
// 업데이트 결과 뷰 (v1.6.0). 변수: $title, $code, $bodyOut.
declare(strict_types=1);
require_once __DIR__ . '/layout.php';
$self = $_SERVER['SCRIPT_NAME'];
admin_head($title);
?>
<div class="flash <?= $code === 0 ? 'ok' : 'err' ?>">
  <strong><?= h($title) ?></strong>
  — <code class="k">python Heron.py --update</code> (GitHub lamaBread/heron-press).
</div>

<?php if ($code === 0): ?>
<div class="flash" style="background:#fff7e6;border:1px solid #f0d9a8;color:#7a5b00">
  <strong>재시작이 필요합니다.</strong>
  Pond.php·system/ 이 방금 교체되었지만 지금 실행 중인 PHP 프로세스는 옛 코드를
  메모리에 들고 있습니다. 터미널에서 <code class="k">Ctrl+C</code> 후
  <code class="k">php -S 127.0.0.1:8001 Pond.php</code> 로 다시 시작하세요.
  (user/ 콘텐츠는 그대로이며, 업데이트 직전 스냅샷이
  <code class="k">user/.heron/backups/</code> 에 백업되어 있습니다.)
</div>
<?php endif; ?>

<div class="row" style="margin-bottom:12px">
  <a class="btn" href="<?= h($self) ?>?a=list">← 목록</a>
</div>
<pre style="background:#0d0d12;color:#d6d6dc;padding:16px;border-radius:8px;
     overflow:auto;max-height:70vh;font:12px/1.5 ui-monospace,Consolas,monospace;
     white-space:pre-wrap"><?= h($bodyOut !== '' ? $bodyOut : '(출력 없음)') ?></pre>
<?php admin_foot();

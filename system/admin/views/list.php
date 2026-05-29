<?php
// 글 목록 뷰 (admin v1.1.0). 변수: $scan, $trash, $flashErrs.
declare(strict_types=1);
require_once __DIR__ . '/layout.php';
$self = $_SERVER['SCRIPT_NAME'];
admin_head('목록');
admin_flash_errs($flashErrs);
foreach ([['moved','카테고리 이동 완료 (slug 불변이라 URL 영구).'],
          ['deleted','삭제 → .trash 로 이동 (빌드 자동 제외, 복구 가능).'],
          ['vis','공개/비공개 상태를 토글했습니다.']] as $f) {
    if (!empty($_GET[$f[0]])) echo '<div class="flash ok">' . h($f[1]) . '</div>';
}
$cats = $scan['categories'];
?>
<div class="row" style="justify-content:space-between;margin-bottom:14px">
  <h2 style="margin:0">글 <span class="muted">(<?= count($scan['posts']) ?>)</span></h2>
  <a class="btn" href="<?= h($self) ?>?a=new">+ 새 글</a>
</div>
<table>
  <thead><tr><th>제목</th><th>경로 (Articles/…)</th><th>상태</th>
    <th style="width:340px">동작</th></tr></thead>
  <tbody>
  <?php foreach ($scan['posts'] as $p): $eid = rawurlencode($p['id']); ?>
    <tr>
      <td><a href="<?= h($self) ?>?a=edit&id=<?= $eid ?>"><?= h($p['title']) ?></a></td>
      <td class="mono muted"><?= h($p['id']) ?></td>
      <td>
        <?php if ($p['hidden']): ?><span class="tag hid">비공개</span><?php
          else: ?><span class="tag">공개</span><?php endif; ?>
        <?php if ($p['both']): ?>
          <span class="tag warn">content.md+html 동시</span><?php endif; ?>
        <?php if ($p['ext'] === 'html'): ?><span class="tag">HTML</span><?php endif; ?>
      </td>
      <td>
        <div class="row">
          <a class="btn" href="<?= h($self) ?>?a=edit&id=<?= $eid ?>">편집</a>

          <form method="post" action="<?= h($self) ?>?a=move" class="row"
                style="gap:4px" onsubmit="return confirm('이 글을 선택한 카테고리로 이동합니다. (URL slug 는 그대로 — 영구)')">
            <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
            <input type="hidden" name="id" value="<?= h($p['id']) ?>">
            <select name="target" title="이동할 카테고리">
              <?php foreach ($cats as $c):
                if ($c === $p['parent']) continue; ?>
                <option value="<?= h($c) ?>"><?= $c === '' ? '(톱레벨)' : h($c) ?></option>
              <?php endforeach; ?>
            </select>
            <button type="submit">이동</button>
          </form>

          <form method="post" action="<?= h($self) ?>?a=visibility" style="display:inline">
            <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
            <input type="hidden" name="id" value="<?= h($p['id']) ?>">
            <button type="submit"><?= $p['hidden'] ? '공개' : '비공개' ?></button>
          </form>

          <form method="post" action="<?= h($self) ?>?a=delete" style="display:inline"
                onsubmit="return confirm('이 글을 .trash 로 보냅니다. 빌드에서 제외되며 파일은 남아 복구 가능합니다. 계속?')">
            <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
            <input type="hidden" name="id" value="<?= h($p['id']) ?>">
            <button type="submit" class="danger">삭제</button>
          </form>
        </div>
      </td>
    </tr>
  <?php endforeach; ?>
  <?php if (!$scan['posts']): ?>
    <tr><td colspan="4" class="muted">글이 없습니다. <a href="<?= h($self) ?>?a=new">새 글</a>을 써보세요.</td></tr>
  <?php endif; ?>
  </tbody>
</table>

<?php if ($trash): ?>
<h3 style="margin:26px 0 8px">.trash <span class="muted">(<?= count($trash) ?>)</span></h3>
<p class="muted" style="margin:0 0 8px">
  삭제된 글. <code class="k">.</code> 접두라 빌드에서 자동 제외됩니다.
  복구하려면 파일 탐색기에서 <code class="k">Articles/.trash/</code> 밖으로 폴더를 옮기세요
  (admin 은 의도적으로 영구 삭제 UI 를 두지 않습니다).</p>
<ul class="mono muted">
  <?php foreach ($trash as $t): ?><li><?= h($t) ?></li><?php endforeach; ?>
</ul>
<?php endif; ?>
<?php admin_foot();

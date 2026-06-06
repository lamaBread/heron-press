<?php
// 글 목록 뷰 (admin v1.1.0). 변수: $scan, $trash, $flashErrs.
declare(strict_types=1);
require_once __DIR__ . '/layout.php';
$self = $_SERVER['SCRIPT_NAME'];
admin_head(t('admin.list.title'));
admin_flash_errs($flashErrs);
foreach ([['moved','admin.list.flash.moved'],
          ['deleted','admin.list.flash.deleted'],
          ['vis','admin.list.flash.vis']] as $f) {
    if (!empty($_GET[$f[0]])) echo '<div class="flash ok">' . h(t($f[1])) . '</div>';
}
$cats = $scan['categories'];
$hl = (string)($_GET['hl'] ?? '');   // 방금 이동한 글 id — 경로 칸 문자열 1회 강조.

// v1.6.0 업데이트 배너 — admin_read_update_cache() 결과($updateInfo)에 기반.
// 캐시는 헤더 "업데이트 확인" 버튼이 GitHub 를 조회해 갱신한다 (페이지 로드마다
// 네트워크를 치지 않음).
$ui = $updateInfo ?? [];
if (!empty($ui['error'])):
?>
  <div class="flash err"><?= h(t('admin.list.update.error', ['error' => (string)$ui['error']])) ?></div>
<?php elseif (!empty($ui['update_available'])): ?>
  <div class="flash" style="background:#eef4ff;border:1px solid #c5d6f5;color:#234">
    <strong><?= h(t('admin.list.update.available', ['latest' => ltrim((string)($ui['latest'] ?? '?'), 'vV')])) ?></strong>
    <?= h(t('admin.list.update.current', ['current' => (string)($ui['current'] ?? '?')])) ?>
    <form method="post" action="<?= h($self) ?>?a=update" style="display:inline;margin-left:8px"
          onsubmit="return confirm('<?= h(t('admin.list.update.confirm')) ?>')">
      <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
      <button class="primary" type="submit"><?= h(t('admin.list.update.now')) ?></button>
    </form>
  </div>
<?php elseif (!empty($_GET['checked']) && !empty($ui)): ?>
  <div class="flash ok"><?= h(t('admin.list.update.uptodate', ['current' => (string)($ui['current'] ?? '?')])) ?></div>
<?php endif; ?>
<?php // (배너 종료) ?>
<div class="row" style="justify-content:space-between;margin-bottom:14px">
  <h2 style="margin:0"><?= h(t('admin.list.heading')) ?> <span class="muted">(<?= count($scan['posts']) ?>)</span></h2>
  <a class="btn" href="<?= h($self) ?>?a=new"><?= h(t('admin.nav.new')) ?></a>
</div>
<table>
  <thead><tr><th><?= h(t('admin.list.col.title')) ?></th><th><?= h(t('admin.list.col.path')) ?></th><th><?= h(t('admin.list.col.status')) ?></th>
    <th style="width:340px"><?= h(t('admin.list.col.actions')) ?></th></tr></thead>
  <tbody>
  <?php foreach ($scan['posts'] as $p): $eid = rawurlencode($p['id']); $isHl = ($p['id'] === $hl); ?>
    <tr>
      <td><a href="<?= h($self) ?>?a=edit&id=<?= $eid ?>"><?= h($p['title']) ?></a></td>
      <td class="mono muted"><?php if ($isHl): ?><span id="moved" class="pathmoved"><?= h($p['id']) ?></span><?php else: ?><?= h($p['id']) ?><?php endif; ?></td>
      <td>
        <?php if ($p['hidden']): ?><span class="tag hid"><?= h(t('admin.list.status.hidden')) ?></span><?php
          else: ?><span class="tag"><?= h(t('admin.list.status.public')) ?></span><?php endif; ?>
        <?php if ($p['both']): ?>
          <span class="tag warn"><?= h(t('admin.list.status.both')) ?></span><?php endif; ?>
        <?php if ($p['ext'] === 'html'): ?><span class="tag">HTML</span><?php endif; ?>
      </td>
      <td>
        <div class="row">
          <a class="btn" href="<?= h($self) ?>?a=edit&id=<?= $eid ?>"><?= h(t('admin.list.action.edit')) ?></a>

          <?php // 카테고리 변경 = 즉시 이동(별도 버튼 없음). confirm 1회 —
                // 취소 시 현재값으로 복원(data-cur), 휠 스크롤 오작동은 blur 로 가드. ?>
          <form method="post" action="<?= h($self) ?>?a=move">
            <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
            <input type="hidden" name="id" value="<?= h($p['id']) ?>">
            <select name="target" title="<?= h(t('admin.list.action.move.title')) ?>"
                    data-cur="<?= h($p['parent']) ?>" style="width:auto;max-width:200px"
                    onchange="if(confirm('<?= h(t('admin.list.action.move.confirm')) ?>'))this.form.submit();else this.value=this.dataset.cur"
                    onwheel="this.blur()">
              <?php foreach ($cats as $c): ?>
                <option value="<?= h($c) ?>"<?= $c === $p['parent'] ? ' selected' : '' ?>><?= $c === '' ? h(t('admin.list.cat.toplevel')) : h($c) ?></option>
              <?php endforeach; ?>
            </select>
          </form>

          <form method="post" action="<?= h($self) ?>?a=visibility" style="display:inline">
            <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
            <input type="hidden" name="id" value="<?= h($p['id']) ?>">
            <button type="submit"><?= $p['hidden'] ? h(t('admin.list.action.make_public')) : h(t('admin.list.action.make_hidden')) ?></button>
          </form>

          <form method="post" action="<?= h($self) ?>?a=delete" style="display:inline"
                onsubmit="return confirm('<?= h(t('admin.list.action.delete.confirm')) ?>')">
            <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
            <input type="hidden" name="id" value="<?= h($p['id']) ?>">
            <button type="submit" class="danger"><?= h(t('admin.list.action.delete')) ?></button>
          </form>
        </div>
      </td>
    </tr>
  <?php endforeach; ?>
  <?php if (!$scan['posts']): ?>
    <tr><td colspan="4" class="muted"><?= t('admin.list.empty', ['href' => h($self) . '?a=new']) ?></td></tr>
  <?php endif; ?>
  </tbody>
</table>

<?php if ($trash): ?>
<h3 style="margin:26px 0 8px"><?= t('admin.list.trash.heading') ?> <span class="muted">(<?= count($trash) ?>)</span></h3>
<p class="muted" style="margin:0 0 8px">
  <?= t('admin.list.trash.note') ?></p>
<ul class="mono muted">
  <?php foreach ($trash as $t): ?><li><?= h($t) ?></li><?php endforeach; ?>
</ul>
<?php endif; ?>
<?php admin_foot();

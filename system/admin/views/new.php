<?php
// 새 글 폼 (admin v1.1.0). 변수: $scan, $flashErrs.
declare(strict_types=1);
require_once __DIR__ . '/layout.php';
$self = $_SERVER['SCRIPT_NAME'];
admin_head(t('admin.new.title'));
admin_flash_errs($flashErrs);
?>
<h2 style="margin:0 0 4px"><?= h(t('admin.new.heading')) ?></h2>
<p class="muted" style="margin:0 0 18px">
  <?= t('admin.new.intro') ?>
</p>
<form method="post" action="<?= h($self) ?>?a=create" style="max-width:680px">
  <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">

  <div class="field">
    <label><?= t('admin.new.field.category') ?></label>
    <select name="category">
      <?php foreach ($scan['categories'] as $c): ?>
        <option value="<?= h($c) ?>"><?= $c === '' ? h(t('admin.new.cat.toplevel')) : h($c) ?></option>
      <?php endforeach; ?>
    </select>
  </div>

  <div class="field">
    <label><?= t('admin.new.field.folder') ?></label>
    <input type="text" name="folder" id="folder" autocomplete="off"
           placeholder="<?= h(t('admin.new.field.folder.placeholder')) ?>">
  </div>

  <div class="field">
    <label><?= t('admin.new.field.slug') ?>
      <span id="slughint" class="muted"></span></label>
    <input type="text" name="slug" id="slug" autocomplete="off"
           placeholder="<?= h(t('admin.new.field.slug.placeholder')) ?>">
  </div>

  <div class="field">
    <label><?= t('admin.new.field.title') ?></label>
    <input type="text" name="title" id="title" autocomplete="off">
  </div>

  <div class="row" style="gap:20px">
    <div class="field" style="flex:1">
      <label><?= t('admin.new.field.date') ?></label>
      <input type="date" name="date" value="<?= h(date('Y-m-d')) ?>">
    </div>
    <div class="field" style="flex:1">
      <label><?= t('admin.new.field.ext') ?></label>
      <select name="ext">
        <option value="md"><?= h(t('admin.new.ext.md')) ?></option>
        <option value="html"><?= h(t('admin.new.ext.html')) ?></option>
      </select>
    </div>
  </div>

  <div class="field">
    <label><?= t('admin.new.field.tags') ?></label>
    <input type="text" name="tags" placeholder="<?= h(t('admin.new.field.tags.placeholder')) ?>">
  </div>

  <div class="field">
    <label><?= t('admin.new.field.desc') ?></label>
    <textarea name="description" rows="2"></textarea>
  </div>

  <div class="row" style="margin-top:10px">
    <button type="submit" class="primary"><?= h(t('admin.new.submit')) ?></button>
    <a class="btn" href="<?= h($self) ?>?a=list"><?= h(t('admin.new.cancel')) ?></a>
  </div>
</form>

<script>
const self = <?= json_encode($self) ?>, CSRF = <?= json_encode($CSRF) ?>;
const folder = document.getElementById('folder'),
      slug = document.getElementById('slug'),
      title = document.getElementById('title'),
      hint = document.getElementById('slughint');
let slugTouched = false, titleTouched = false;
slug.addEventListener('input', () => slugTouched = true);
title.addEventListener('input', () => titleTouched = true);
let t;
folder.addEventListener('input', () => {
  if (!titleTouched) title.value = folder.value;
  clearTimeout(t);
  t = setTimeout(async () => {
    if (slugTouched || !folder.value.trim()) return;
    const fd = new FormData();
    fd.append('csrf', CSRF); fd.append('name', folder.value);
    try {
      const r = await fetch(self + '?a=slug', {method:'POST', body:fd});
      const j = await r.json();
      if (!slugTouched) slug.value = j.slug || '';
      hint.textContent = j.non_ascii
        ? <?= json_encode(t('admin.new.slug.nonascii')) ?> : '';
    } catch (e) {}
  }, 350);
});
</script>
<?php admin_foot();

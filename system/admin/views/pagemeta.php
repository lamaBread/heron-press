<?php
// 페이지 설정 편집기 뷰 (v1.14.8). 홈/카테고리 meta.yaml 원문 편집 — site.yaml
// 편집(settings.php ②)과 같은 raw 편집 + 저장 시 Heron.py --check-page-meta 로
// 빌드와 동일 검증 통과해야 commit. 변수:
//   $cats(string[] — '' 포함), $cat(string — 현재 선택, ''=홈),
//   $pageMetaYaml(string), $pageMetaErr(string), $isHome(bool),
//   $fileExists(bool), $saved(bool), $deleted(bool).
declare(strict_types=1);
require_once __DIR__ . '/layout.php';
$self = $_SERVER['SCRIPT_NAME'];
admin_head(t('admin.pagemeta.title'));
?>
<h2 style="margin:0 0 4px"><?= h(t('admin.pagemeta.heading')) ?></h2>
<p class="muted" style="margin:0 0 18px">
  <?= t('admin.pagemeta.intro') ?>
</p>

<?php if ($saved): ?>
  <div class="flash ok"><?= t('admin.pagemeta.flash.saved') ?></div>
<?php endif; ?>
<?php if ($deleted): ?>
  <div class="flash ok"><?= t('admin.pagemeta.flash.deleted') ?></div>
<?php endif; ?>

<!-- ── 페이지 선택 (홈 + 카테고리) ─────────────────────────────────── -->
<div class="field" style="max-width:420px;margin:0 0 16px">
  <label><?= h(t('admin.pagemeta.select.label')) ?></label>
  <select onchange="location.href='<?= h($self) ?>?a=pagemeta&cat='+encodeURIComponent(this.value)"
          onwheel="this.blur()" style="width:auto;max-width:400px">
    <?php foreach ($cats as $c): ?>
      <option value="<?= h($c) ?>"<?= $c === $cat ? ' selected' : '' ?>><?php
        echo $c === '' ? h(t('admin.pagemeta.select.home')) : h($c); ?></option>
    <?php endforeach; ?>
  </select>
  <p class="muted" style="font-size:12px;margin:4px 0 0">
    <?= $isHome ? t('admin.pagemeta.scope.home') : t('admin.pagemeta.scope.category') ?>
    <?php if (!$fileExists): ?>
      · <em><?= h(t('admin.pagemeta.no_file')) ?></em>
    <?php endif; ?>
  </p>
</div>

<?php if ($pageMetaErr !== ''): ?>
  <div class="flash err"><strong><?= t('admin.pagemeta.err.title') ?></strong>
    <?= t('admin.pagemeta.err.body') ?>
    <pre class="mono" style="white-space:pre-wrap;margin:8px 0 0;font-size:12px"><?= h($pageMetaErr) ?></pre>
  </div>
<?php endif; ?>

<form method="post" action="<?= h($self) ?>?a=pagemeta_save"
      onsubmit="return confirm('<?= h(t('admin.pagemeta.confirm')) ?>')">
  <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
  <input type="hidden" name="cat" value="<?= h($cat) ?>">
  <textarea name="meta" rows="22" spellcheck="false"
    style="height:440px"><?= h($pageMetaYaml) ?></textarea>
  <div class="row" style="margin:12px 0">
    <button type="submit" class="primary"><?= h(t('admin.pagemeta.save')) ?></button>
    <a class="btn" href="<?= h($self) ?>?a=settings"><?= h(t('admin.pagemeta.to_settings')) ?></a>
    <span class="muted" style="font-size:12px">
      <?= t('admin.pagemeta.save.note') ?></span>
  </div>
</form>
<?php admin_foot();

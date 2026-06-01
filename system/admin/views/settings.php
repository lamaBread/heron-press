<?php
// 설정 뷰 (v1.8.0). 한 화면 두 섹션:
//   ① 배포 (deploy.json)  — 구조화 폼. 평평한 JSON·주석 없음 → 폼이 적합.
//   ② 사이트 (site.yaml)   — 원문 편집기. 주석이 풍부한 YAML 이라 폼-덤프는
//      인라인 문서(=주석)를 파괴한다. meta.yaml 편집과 같은 raw 편집 +
//      저장 시 Heron.py --check-config 로 빌드와 동일 검증 통과해야 commit.
// 변수: $deployCfg(?array), $deploySeed(array), $deployExample(bool),
//       $siteYaml(string), $deployErrs(string[]), $siteErr(string),
//       $deploySaved(bool), $siteSaved(bool).
declare(strict_types=1);
require_once __DIR__ . '/layout.php';
$self = $_SERVER['SCRIPT_NAME'];
admin_head(t('admin.settings.title'));

// 폼 프리필: 저장된 설정 우선, 없으면 example 견본값(최초 작성 도우미).
$d = $deployCfg ?? $deploySeed;
$dv = static fn(string $k, $def = '') => h((string)($d[$k] ?? $def));
?>
<h2 style="margin:0 0 4px"><?= h(t('admin.settings.heading')) ?></h2>
<p class="muted" style="margin:0 0 18px">
  <?= t('admin.settings.intro') ?>
</p>

<?php if ($deploySaved): ?>
  <div class="flash ok"><?= t('admin.settings.flash.deploy_saved') ?></div>
<?php endif; ?>
<?php if ($siteSaved): ?>
  <div class="flash ok"><?= t('admin.settings.flash.site_saved') ?></div>
<?php endif; ?>
<?php if (!empty($_GET['locale_saved'])): ?>
  <div class="flash ok"><?= t('admin.settings.flash.locale_saved') ?></div>
<?php endif; ?>

<!-- ── ① 배포 설정 (deploy.json) ───────────────────────────────── -->
<section style="margin:0 0 32px">
  <h3 style="margin:0 0 4px"><?= t('admin.settings.deploy.heading') ?></h3>
  <p class="muted" style="font-size:13px;margin:0 0 12px">
    <?= t('admin.settings.deploy.intro') ?>
  </p>

  <?php admin_flash_errs($deployErrs); ?>
  <?php if ($deployCfg === null): ?>
    <div class="flash" style="background:#fff7e6;border:1px solid #f0d9a8;color:#7a5b00">
      <?= t('admin.settings.deploy.none', ['hint' => $deployExample
          ? t('admin.settings.deploy.none.has_example')
          : t('admin.settings.deploy.none.no_example')]) ?>
    </div>
  <?php endif; ?>

  <form method="post" action="<?= h($self) ?>?a=settings_deploy">
    <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
    <div class="row" style="gap:14px">
      <div class="field" style="flex:2"><label>host</label>
        <input type="text" name="host" value="<?= $dv('host') ?>"
               placeholder="your-domain.com"></div>
      <div class="field" style="flex:1"><label>port</label>
        <input type="text" name="port" value="<?= $dv('port', '22') ?>"
               placeholder="22"></div>
    </div>
    <div class="row" style="gap:14px">
      <div class="field" style="flex:1"><label><?= t('admin.settings.deploy.field.user') ?></label>
        <input type="text" name="user" value="<?= $dv('user') ?>"
               placeholder="deployuser"></div>
      <div class="field" style="flex:2"><label><?= t('admin.settings.deploy.field.remote_path') ?></label>
        <input type="text" name="remote_path" value="<?= $dv('remote_path') ?>"
               placeholder="/var/www/your-domain.com"></div>
    </div>
    <div class="field"><label><?= t('admin.settings.deploy.field.ssh_key_path') ?></label>
      <input type="text" name="ssh_key_path" value="<?= $dv('ssh_key_path') ?>"
             placeholder="C:/Users/you/.ssh/id_ed25519"></div>
    <div class="field"><label><?= t('admin.settings.deploy.field.known_hosts_path') ?></label>
      <input type="text" name="known_hosts_path" value="<?= $dv('known_hosts_path') ?>"
             placeholder="C:/Users/you/.ssh/known_hosts"></div>
    <div class="row" style="margin:6px 0">
      <button type="submit" class="primary"><?= h(t('admin.settings.deploy.save')) ?></button>
      <a class="btn" href="<?= h($self) ?>?a=deploy"><?= h(t('admin.settings.deploy.to_deploy')) ?></a>
    </div>
  </form>
</section>

<!-- ── ② 사이트 설정 (site.yaml) ───────────────────────────────── -->
<section style="margin:0 0 32px">
  <h3 style="margin:0 0 4px"><?= t('admin.settings.site.heading') ?></h3>
  <p class="muted" style="font-size:13px;margin:0 0 12px">
    <?= t('admin.settings.site.intro') ?>
  </p>

  <?php if ($siteErr !== ''): ?>
    <div class="flash err"><strong><?= t('admin.settings.site.err.title') ?></strong>
      <?= t('admin.settings.site.err.body') ?>
      <pre class="mono" style="white-space:pre-wrap;margin:8px 0 0;font-size:12px"><?= h($siteErr) ?></pre>
    </div>
  <?php endif; ?>

  <form method="post" action="<?= h($self) ?>?a=settings_site"
        onsubmit="return confirm('<?= h(t('admin.settings.site.confirm')) ?>')">
    <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
    <textarea name="site" rows="34" spellcheck="false"
      style="height:680px"><?= h($siteYaml) ?></textarea>
    <div class="row" style="margin:12px 0">
      <button type="submit" class="primary"><?= h(t('admin.settings.site.save')) ?></button>
      <span class="muted" style="font-size:12px">
        <?= t('admin.settings.site.save.note') ?></span>
    </div>
  </form>
</section>

<!-- ── ③ 도구 언어 (locale) ─────────────────────────────────────── -->
<section>
  <h3 style="margin:0 0 4px"><?= t('admin.settings.locale.heading') ?></h3>
  <p class="muted" style="font-size:13px;margin:0 0 12px">
    <?= t('admin.settings.locale.intro') ?>
  </p>

  <form method="post" action="<?= h($self) ?>?a=settings_locale" style="max-width:680px">
    <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
    <div class="field" style="max-width:280px">
      <label><?= t('admin.settings.locale.label') ?></label>
      <select name="locale">
        <?php $cur = i18n_locale(); foreach (i18n_available_locales() as $loc): ?>
          <option value="<?= h($loc) ?>" <?= $loc === $cur ? 'selected' : '' ?>><?= h($loc) ?></option>
        <?php endforeach; ?>
      </select>
    </div>
    <div class="row" style="margin:6px 0">
      <button type="submit" class="primary"><?= h(t('admin.settings.locale.save')) ?></button>
    </div>
  </form>
</section>
<?php admin_foot();

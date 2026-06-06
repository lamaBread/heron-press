<?php
// dist 배포 랜딩 뷰 (v1.7.0). 변수: $deployCfg(?array), $deployExample(bool).
// 설정 상태를 보여 주고 ① 미리보기(dry-run) 로 funnel 진입. 실제 적용은
// 미리보기 결과 화면(deploy_run.php)에서만 노출 — 2단계 안전 게이트.
declare(strict_types=1);
require_once __DIR__ . '/layout.php';
$self = $_SERVER['SCRIPT_NAME'];
admin_head(t('admin.deploy.title'));

$keyMask = static function (?string $p): string {
    $p = trim((string)$p);
    if ($p === '') return t('admin.deploy.key.unset');
    $name = basename(str_replace('\\', '/', $p));
    return '…/' . $name;   // 전체 경로 대신 파일명만 (마스킹)
};
?>
<h2 style="margin:0 0 4px"><?= h(t('admin.deploy.heading')) ?></h2>
<p class="muted" style="margin:0 0 16px">
  <?= t('admin.deploy.intro') ?>
</p>

<?php if ($deployCfg === null): ?>
  <div class="flash err">
    <strong><?= t('admin.deploy.noconfig.title') ?></strong>
    <?= t('admin.deploy.noconfig.need') ?>
    <?php if ($deployExample): ?>
      <?= t('admin.deploy.noconfig.copy') ?>
    <?php else: ?>
      <?= t('admin.deploy.noconfig.seed') ?>
    <?php endif; ?>
  </div>
  <table style="margin:0 0 16px">
    <tr><th><?= h(t('admin.deploy.req.col.key')) ?></th><th><?= h(t('admin.deploy.req.col.desc')) ?></th></tr>
    <tr><td class="mono">host</td><td><?= t('admin.deploy.req.host') ?></td></tr>
    <tr><td class="mono">user</td><td><?= t('admin.deploy.req.user') ?></td></tr>
    <tr><td class="mono">port</td><td><?= t('admin.deploy.req.port') ?></td></tr>
    <tr><td class="mono">remote_path</td><td><?= t('admin.deploy.req.remote_path') ?></td></tr>
    <tr><td class="mono">ssh_key_path</td><td><?= t('admin.deploy.req.ssh_key_path') ?></td></tr>
    <tr><td class="mono">known_hosts_path</td><td><?= t('admin.deploy.req.known_hosts_path') ?></td></tr>
  </table>
<?php else: ?>
  <table style="margin:0 0 16px">
    <tr><th><?= h(t('admin.deploy.cfg.col.item')) ?></th><th><?= h(t('admin.deploy.cfg.col.value')) ?></th></tr>
    <tr><td class="mono">host</td><td class="mono"><?= h((string)($deployCfg['host'] ?? '')) ?></td></tr>
    <tr><td class="mono">user</td><td class="mono"><?= h((string)($deployCfg['user'] ?? '')) ?></td></tr>
    <tr><td class="mono">port</td><td class="mono"><?= h((string)($deployCfg['port'] ?? 22)) ?></td></tr>
    <tr><td class="mono">remote_path</td><td class="mono"><?= h((string)($deployCfg['remote_path'] ?? '')) ?></td></tr>
    <tr><td class="mono">ssh_key_path</td><td class="mono"><?= h($keyMask($deployCfg['ssh_key_path'] ?? '')) ?></td></tr>
    <tr><td class="mono">known_hosts_path</td><td class="mono"><?= h(trim((string)($deployCfg['known_hosts_path'] ?? '')) ?: t('admin.deploy.cfg.known_hosts_default')) ?></td></tr>
<?php if (trim((string)($deployCfg['ssh_alias'] ?? '')) !== ''): ?>
    <tr><td class="mono">ssh_alias</td><td class="mono"><?= h((string)$deployCfg['ssh_alias']) ?></td></tr>
<?php endif; ?>
  </table>
<?php endif; ?>

<div class="flash" style="background:#fff7e6;border:1px solid #f0d9a8;color:#7a5b00">
  <strong><?= t('admin.deploy.note.title') ?></strong>
  <ul style="margin:6px 0 0">
    <li><?= t('admin.deploy.note.hostkey') ?></li>
    <li><?= t('admin.deploy.note.build') ?></li>
    <li><?= t('admin.deploy.note.slow') ?></li>
  </ul>
</div>

<div class="row" style="margin-bottom:12px">
  <a class="btn" href="<?= h($self) ?>?a=list"><?= h(t('admin.deploy.back')) ?></a>
  <form method="post" action="<?= h($self) ?>?a=deploy" style="display:inline">
    <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
    <input type="hidden" name="stage" value="preview">
    <button class="primary" type="submit" <?= $deployCfg === null ? 'disabled' : '' ?>>
      <?= h(t('admin.deploy.preview_btn')) ?>
    </button>
  </form>
</div>
<?php admin_foot();

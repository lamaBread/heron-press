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
admin_head('설정');

// 폼 프리필: 저장된 설정 우선, 없으면 example 견본값(최초 작성 도우미).
$d = $deployCfg ?? $deploySeed;
$dv = static fn(string $k, $def = '') => h((string)($d[$k] ?? $def));
?>
<h2 style="margin:0 0 4px">설정</h2>
<p class="muted" style="margin:0 0 18px">
  배포 대상과 사이트 전역 설정을 여기서 직접 편집합니다. 변경은
  <code class="k">user/</code> 의 설정 파일에만 반영되며, 사이트(dist/)에
  적용하려면 상단 <strong>빌드</strong> 후 <strong>배포</strong>하세요.
</p>

<?php if ($deploySaved): ?>
  <div class="flash ok">배포 설정 저장됨 (<code class="k">user/.heron/deploy.json</code>).</div>
<?php endif; ?>
<?php if ($siteSaved): ?>
  <div class="flash ok">사이트 설정 저장됨 (<code class="k">user/site.yaml</code>) —
    검증 통과. 사이트에 반영하려면 상단 <strong>빌드</strong>.</div>
<?php endif; ?>

<!-- ── ① 배포 설정 (deploy.json) ───────────────────────────────── -->
<section style="margin:0 0 32px">
  <h3 style="margin:0 0 4px">① 배포 (deploy.json)</h3>
  <p class="muted" style="font-size:13px;margin:0 0 12px">
    rclone(SFTP)으로 <code class="k">dist/</code> 를 올릴 서버 정보입니다.
    개인키는 저장하지 않습니다 — 저장소 밖 OS 표준 위치의 <em>경로</em>만 보관.
  </p>

  <?php admin_flash_errs($deployErrs); ?>
  <?php if ($deployCfg === null): ?>
    <div class="flash" style="background:#fff7e6;border:1px solid #f0d9a8;color:#7a5b00">
      아직 <code class="k">deploy.json</code> 이 없습니다.
      <?= $deployExample ? '견본(deploy.example.json) 값을 채워 두었으니' : '아래 칸을 채워' ?>
      저장하면 새로 만들어집니다.
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
      <div class="field" style="flex:1"><label>user (SSH)</label>
        <input type="text" name="user" value="<?= $dv('user') ?>"
               placeholder="deployuser"></div>
      <div class="field" style="flex:2"><label>remote_path (서버 DocumentRoot)</label>
        <input type="text" name="remote_path" value="<?= $dv('remote_path') ?>"
               placeholder="/var/www/your-domain.com"></div>
    </div>
    <div class="field"><label>ssh_key_path (개인키 <em>경로</em> — 저장소 밖)</label>
      <input type="text" name="ssh_key_path" value="<?= $dv('ssh_key_path') ?>"
             placeholder="C:/Users/you/.ssh/id_ed25519"></div>
    <div class="field"><label>known_hosts_path (선택 — 비우면 ~/.ssh/known_hosts)</label>
      <input type="text" name="known_hosts_path" value="<?= $dv('known_hosts_path') ?>"
             placeholder="C:/Users/you/.ssh/known_hosts"></div>
    <div class="row" style="margin:6px 0">
      <button type="submit" class="primary">배포 설정 저장</button>
      <a class="btn" href="<?= h($self) ?>?a=deploy">배포 화면으로 →</a>
    </div>
  </form>
</section>

<!-- ── ② 사이트 설정 (site.yaml) ───────────────────────────────── -->
<section>
  <h3 style="margin:0 0 4px">② 사이트 (site.yaml)</h3>
  <p class="muted" style="font-size:13px;margin:0 0 12px">
    도메인·사이트명·이미지/광고/JSON-LD 등 전역 설정입니다.
    <strong>원문 그대로 편집</strong>하므로 주석이 보존됩니다. 저장 시
    빌드와 동일한 검증을 거쳐 <strong>통과해야만 기록</strong>되고, 직전 내용은
    <code class="k">user/.heron/backups/settings/</code> 에 백업됩니다.
  </p>

  <?php if ($siteErr !== ''): ?>
    <div class="flash err"><strong>검증 실패 — 저장하지 않았습니다.</strong>
      아래는 빌더가 보고한 내용입니다 (고친 뒤 다시 저장):
      <pre class="mono" style="white-space:pre-wrap;margin:8px 0 0;font-size:12px"><?= h($siteErr) ?></pre>
    </div>
  <?php endif; ?>

  <form method="post" action="<?= h($self) ?>?a=settings_site"
        onsubmit="return confirm('site.yaml 을 검증한 뒤 통과하면 덮어씁니다 (직전 내용은 백업). 계속할까요?')">
    <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
    <textarea name="site" rows="34" spellcheck="false"
      style="height:680px"><?= h($siteYaml) ?></textarea>
    <div class="row" style="margin:12px 0">
      <button type="submit" class="primary">검증 후 저장</button>
      <span class="muted" style="font-size:12px">
        통과하지 못하면 디스크의 site.yaml 은 바뀌지 않고, 편집 내용은 위에 그대로 남습니다.</span>
    </div>
  </form>
</section>
<?php admin_foot();

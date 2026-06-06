<?php
// 공용 레이아웃 헬퍼 (admin v1.1.0 뷰). h()/CSRF 는 Pond.php 에 정의됨.
declare(strict_types=1);

function admin_head(string $title): void {
    global $CSRF;
    $self = $_SERVER['SCRIPT_NAME'];
    $act = $_GET['a'] ?? 'home';            // 활성 nav 강조용 현재 액션.
    $navOn = static fn(string $a): string => $act === $a ? ' class="on"' : '';
    ?><!DOCTYPE html>
<html lang="<?= h(i18n_locale()) ?>">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title><?= h($title) ?> · <?= h(t('admin.layout.title_suffix')) ?></title>
<style>
  :root{--bd:#dcdce0;--mut:#6b6b72;--accent:#2b6cb0;--bg:#fafafb}
  *{box-sizing:border-box}
  body{margin:0;font:14px/1.55 -apple-system,"Segoe UI",system-ui,sans-serif;
       color:#1a1a1e;background:var(--bg)}
  a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
  header.bar{display:flex;align-items:center;gap:18px;padding:10px 18px;
       background:#fff;border-bottom:1px solid var(--bd);position:sticky;top:0;z-index:5}
  header.bar a.brand{font-weight:700;color:#1a1a1e;text-decoration:none;
       display:inline-flex;align-items:baseline;gap:6px}
  header.bar a.brand:hover{color:var(--accent)}
  header.bar a.brand .ver{font-weight:400;font-size:11px;color:var(--mut)}
  header.bar nav{display:flex;gap:14px}
  header.bar nav a.on{font-weight:700;color:#1a1a1e}
  header.bar form.bld{margin-left:auto;display:flex;gap:8px;align-items:center}
  main{padding:20px;max-width:1280px;margin:0 auto}
  button,.btn{font:inherit;padding:6px 12px;border:1px solid var(--bd);
       background:#fff;border-radius:6px;cursor:pointer;color:#1a1a1e}
  button:hover,.btn:hover{border-color:#b9b9c0}
  button.primary{background:var(--accent);border-color:var(--accent);color:#fff}
  button.danger{color:#b00020;border-color:#e6b8bf}
  table{border-collapse:collapse;width:100%;background:#fff}
  th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--bd);
       vertical-align:top}
  th{font-size:12px;color:var(--mut);text-transform:uppercase;letter-spacing:.04em}
  .muted{color:var(--mut)}.mono{font-family:ui-monospace,Consolas,monospace}
  .tag{display:inline-block;font-size:11px;padding:1px 7px;border-radius:999px;
       border:1px solid var(--bd);color:var(--mut);background:#fff}
  .tag.hid{color:#9a6700;border-color:#e6d8a8;background:#fffaf0}
  .tag.warn{color:#b00020;border-color:#e6b8bf;background:#fff5f6}
  .flash{padding:10px 14px;border-radius:7px;margin:0 0 16px}
  .flash.ok{background:#edf7ed;border:1px solid #cbe6cb;color:#1e5b1e}
  .flash.err{background:#fdecec;border:1px solid #f0c6c6;color:#9a1b1b}
  .field{margin:0 0 12px}.field label{display:block;font-size:12px;
       color:var(--mut);margin:0 0 4px}
  input[type=text],input[type=date],textarea,select{width:100%;font:inherit;
       padding:7px 9px;border:1px solid var(--bd);border-radius:6px;background:#fff}
  textarea{font-family:ui-monospace,Consolas,monospace;resize:vertical}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:20px;align-items:start}
  @media(max-width:1000px){.grid2{grid-template-columns:1fr}}
  details>summary{cursor:pointer;font-size:12px;color:var(--mut);margin:6px 0}
  .row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
  iframe.pv{width:100%;height:640px;border:1px solid var(--bd);border-radius:8px;
       background:#fff}
  code.k{background:#eef;padding:1px 5px;border-radius:4px}
  /* 배포 실행 로그 + dry-run 요약 (deploy_run.php) */
  pre#log{background:#0d0d12;color:#d6d6dc;padding:14px 16px;border-radius:8px;
       overflow:auto;white-space:pre-wrap;margin:0;
       font:12px/1.5 ui-monospace,Consolas,monospace}
  pre#log.log-peek{max-height:212px}   /* ≈ 10행 + 패딩 */
  pre#log.log-full{max-height:75vh}
  .logbar{display:flex;align-items:center;gap:10px;margin:0 0 6px}
  .logbar .ttl{font-size:12px;color:var(--mut);text-transform:uppercase;
       letter-spacing:.04em}
  .logbar button{margin-left:auto;font-size:12px;padding:3px 10px}
  .cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:14px 0}
  @media(max-width:700px){.cards{grid-template-columns:1fr 1fr}}
  .card{border:1px solid var(--bd);border-radius:8px;padding:10px 12px;background:#fff}
  .card .lbl{font-size:11px;color:var(--mut);text-transform:uppercase;
       letter-spacing:.04em}
  .card .num{font-size:21px;font-weight:700;margin:2px 0 0}
  .card .sub{font-size:12px;color:var(--mut)}
  .card.warn{border-color:#e6d8a8;background:#fffaf0}.card.warn .num{color:#9a6700}
  .card.danger{border-color:#e6b8bf;background:#fff5f6}.card.danger .num{color:#b00020}
  td.r,th.r{text-align:right}
  ul.warns{margin:6px 0 0;padding:0 0 0 18px}ul.warns li{margin:2px 0}
  /* v1.13.0 — 카드 아코디언 + 파일별 unified diff */
  /* v1.13.1 — 카드 5장(추가/수정/삭제/변경 없음/경고). 컨테이너 폭에 맞춰
     auto-fit 로 한 줄에 5장 → 좁으면 자연 줄바꿈(고정 4열 그리드 무시). */
  .cards.acc{grid-template-columns:repeat(auto-fit,minmax(130px,1fr))}
  button.card.accbtn{font:inherit;text-align:left;cursor:pointer;width:100%;
       display:block;transition:border-color .12s,box-shadow .12s}
  button.card.accbtn:hover{border-color:var(--accent)}
  button.card.accbtn[aria-expanded=true]{border-color:var(--accent);
       box-shadow:0 0 0 2px rgba(43,108,176,.18)}
  .panels{margin:0 0 8px}
  .panel{border:1px solid var(--bd);border-radius:8px;padding:10px 12px;
       margin:0 0 12px;background:#fff}
  .panel h4{margin:0 0 8px;font-size:13px}
  ul.files{list-style:none;margin:0;padding:0;font-size:13px}
  ul.files li{padding:4px 0;border-top:1px solid var(--bd)}
  ul.files li:first-child{border-top:0}
  ul.files .fp{font-family:ui-monospace,Consolas,monospace;word-break:break-all}
  ul.files .fs{color:var(--mut);font-size:12px;margin-left:8px;white-space:nowrap}
  .diffbtn{font-size:11px;padding:2px 8px;margin-right:8px;vertical-align:baseline}
  .more{font-size:12px;margin:6px 0 0}
  .diffbox{margin:8px 0 2px}
  .dmsg{font-size:12px;color:var(--mut);margin:4px 0}.dmsg.err{color:#b00020}
  table.diff{width:100%;border-collapse:collapse;font-family:ui-monospace,Consolas,
       monospace;font-size:12px;background:#0d0d12;color:#d6d6dc;border-radius:6px;
       overflow:hidden;table-layout:fixed}
  table.diff td{padding:0 8px;vertical-align:top}
  table.diff td.ln{width:46px;text-align:right;color:#6b6b76;user-select:none;
       white-space:nowrap}
  table.diff td.tx{white-space:pre-wrap;word-break:break-all}
  table.diff tr.hh td{color:#7aa2f7;background:#161b29;padding:3px 8px}
  table.diff tr.add td.tx{background:#0f2a17;color:#b6f0c2}
  table.diff tr.del td.tx{background:#2b1416;color:#f3b6bd}
  table.diff tr.add td.ln,table.diff tr.del td.ln{background:#11151f}
</style>
</head>
<body>
<header class="bar">
  <a class="brand" href="<?= h($self) ?>?a=home" title="<?= h(t('admin.layout.brand.title')) ?>">Pond admin<?php
    $ver = admin_program_version();
    if ($ver !== '') echo '<span class="ver">Heron v' . h($ver) . '</span>';
  ?></a>
  <nav>
    <a<?= $navOn('list') ?> href="<?= h($self) ?>?a=list"><?= h(t('admin.nav.list')) ?></a>
    <a<?= $navOn('new') ?> href="<?= h($self) ?>?a=new"><?= h(t('admin.nav.new')) ?></a>
    <a<?= $navOn('deploy') ?> href="<?= h($self) ?>?a=deploy" title="<?= h(t('admin.layout.nav.deploy.title')) ?>"><?= h(t('admin.nav.deploy')) ?></a>
    <a<?= $navOn('settings') ?> href="<?= h($self) ?>?a=settings" title="<?= h(t('admin.layout.nav.settings.title')) ?>"><?= h(t('admin.nav.settings')) ?></a>
  </nav>
  <form method="post" action="<?= h($self) ?>?a=checkupdate" style="display:inline"
        title="<?= h(t('admin.layout.checkupdate.title')) ?>">
    <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
    <button type="submit"><?= h(t('admin.nav.check_update')) ?></button>
  </form>
  <form class="bld" method="post" action="<?= h($self) ?>?a=build"
        onsubmit="return confirm('<?= h(t('admin.layout.build.confirm')) ?>')">
    <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
    <label class="muted" style="font-size:12px">
      <input type="checkbox" name="clean" value="1"> --clean</label>
    <button class="primary" type="submit"><?= h(t('admin.nav.build')) ?></button>
  </form>
</header>
<main>
<?php
}

function admin_flash_errs(array $errs): void {
    if (!$errs) return;
    echo '<div class="flash err"><strong>' . h(t('admin.layout.flash_errs.title'))
        . '</strong><ul style="margin:6px 0 0">';
    foreach ($errs as $e) echo '<li>' . h($e) . '</li>';
    echo '</ul></div>';
}

function admin_foot(): void {
    ?>
</main>
<footer style="padding:14px 20px;color:#6b6b72;font-size:12px;border-top:1px solid #dcdce0;margin-top:30px">
  <?= t('admin.layout.footer') ?>
</footer>
</body>
</html>
<?php
}

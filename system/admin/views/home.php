<?php
// 홈 / 시스템 개요 뷰 (v1.8.0). 브랜드("Pond admin") 클릭 시 도착하는
// 메인 페이지 — Heron(빌더) + Pond(이 도구)의 전체 흐름을 한눈에 시각화한다.
// 정본 설명서는 README.md/README.ko.md; 여기는 그 요약 + 바로가기.
// 변수: $ver(string), $postCount(int), $catCount(int),
//       $hasDeploy(bool), $hasSiteYaml(bool).
declare(strict_types=1);
require_once __DIR__ . '/layout.php';
$self = $_SERVER['SCRIPT_NAME'];
admin_head(t('admin.home.title'));
?>
<style>
  /* 홈 전용 스코프 스타일 — 공용 토큰(--accent/--bd/--mut) 재사용. */
  .hero{margin:0 0 26px}
  .hero h1{margin:0 0 6px;font-size:24px;letter-spacing:-.01em}
  .hero h1 .v{font-size:13px;font-weight:400;color:var(--mut);margin-left:8px}
  .hero p{margin:0;color:var(--mut);max-width:760px}
  .flow{display:flex;align-items:stretch;gap:0;flex-wrap:wrap;margin:0 0 30px}
  .flow .node{flex:1;min-width:130px;background:#fff;border:1px solid var(--bd);
       border-radius:10px;padding:12px 14px}
  .flow .node .k{font-size:11px;text-transform:uppercase;letter-spacing:.05em;
       color:var(--accent);font-weight:700}
  .flow .node .t{font-weight:700;margin:2px 0 3px}
  .flow .node .d{font-size:12px;color:var(--mut);line-height:1.45}
  .flow .node.you{border-color:#cfe0f7;background:#f5f9ff}
  .flow .node.srv{border-color:#cbe6cb;background:#f4fbf4}
  .flow .arr{display:flex;align-items:center;justify-content:center;
       color:var(--mut);font-size:20px;padding:0 8px;flex:0 0 auto}
  @media(max-width:860px){
    .flow{flex-direction:column}
    .flow .arr{transform:rotate(90deg);padding:6px 0}
  }
  .cards{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin:0 0 30px}
  @media(max-width:760px){.cards{grid-template-columns:1fr}}
  .card{background:#fff;border:1px solid var(--bd);border-radius:10px;padding:16px 18px}
  .card h3{margin:0 0 6px;font-size:15px}
  .card h3 .badge{font-size:11px;font-weight:600;color:var(--mut);
       border:1px solid var(--bd);border-radius:999px;padding:1px 8px;margin-left:6px}
  .card p{margin:0 0 8px;font-size:13px;color:#333;line-height:1.55}
  .card ul{margin:0;padding-left:18px;font-size:13px;color:#333;line-height:1.6}
  .card .file{font-family:ui-monospace,Consolas,monospace;font-size:12px;
       background:#eef;padding:1px 6px;border-radius:4px}
  .qa{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:0 0 8px}
  @media(max-width:760px){.qa{grid-template-columns:repeat(2,1fr)}}
  .qa a{display:block;background:#fff;border:1px solid var(--bd);border-radius:10px;
       padding:14px;text-decoration:none;color:#1a1a1e}
  .qa a:hover{border-color:var(--accent);text-decoration:none}
  .qa a .t{font-weight:700;margin:0 0 2px}
  .qa a .d{font-size:12px;color:var(--mut)}
  .qa a .st{font-size:11px;margin-top:6px}
  .qa a .st.ok{color:#1e5b1e}.qa a .st.no{color:#9a6700}
  .principles{display:grid;grid-template-columns:repeat(2,1fr);gap:8px 24px;
       margin:10px 0 0;padding:0;list-style:none;font-size:13px}
  @media(max-width:760px){.principles{grid-template-columns:1fr}}
  .principles li{padding-left:20px;position:relative;color:#333;line-height:1.5}
  .principles li::before{content:"✓";position:absolute;left:0;color:var(--accent);font-weight:700}
  .sec-h{font-size:12px;text-transform:uppercase;letter-spacing:.05em;
       color:var(--mut);font-weight:700;margin:0 0 12px}
</style>

<div class="hero">
  <h1>Heron <span class="muted" style="font-weight:400">+</span> Pond<?php
    if ($ver !== '') echo '<span class="v">' . h(t('admin.home.hero.version', ['ver' => $ver])) . '</span>'; ?></h1>
  <p>
    <?= t('admin.home.hero.body') ?>
  </p>
</div>

<!-- ── 전체 파이프라인 ───────────────────────────────────────────── -->
<div class="flow">
  <div class="node you">
    <div class="k"><?= t('admin.home.flow.you.k') ?></div>
    <div class="t"><?= t('admin.home.flow.you.t') ?></div>
    <div class="d"><?= t('admin.home.flow.you.d') ?></div>
  </div>
  <div class="arr">→</div>
  <div class="node">
    <div class="k">Heron.py</div>
    <div class="t"><?= t('admin.home.flow.build.t') ?></div>
    <div class="d"><?= t('admin.home.flow.build.d') ?></div>
  </div>
  <div class="arr">→</div>
  <div class="node">
    <div class="k"><?= t('admin.home.flow.dist.k') ?></div>
    <div class="t">dist/</div>
    <div class="d"><?= t('admin.home.flow.dist.d') ?></div>
  </div>
  <div class="arr">→</div>
  <div class="node">
    <div class="k"><?= t('admin.home.flow.deploy.k') ?></div>
    <div class="t"><?= t('admin.home.flow.deploy.t') ?></div>
    <div class="d"><?= t('admin.home.flow.deploy.d') ?></div>
  </div>
  <div class="arr">→</div>
  <div class="node srv">
    <div class="k"><?= t('admin.home.flow.serve.k') ?></div>
    <div class="t">Apache + PHP</div>
    <div class="d"><?= t('admin.home.flow.serve.d') ?></div>
  </div>
</div>

<!-- ── 구성 요소 ─────────────────────────────────────────────────── -->
<div class="sec-h"><?= t('admin.home.sec.components') ?></div>
<div class="cards">
  <div class="card">
    <h3>Heron.py <span class="badge"><?= t('admin.home.card.builder.title') ?></span></h3>
    <p><?= t('admin.home.card.builder.body') ?></p>
    <ul>
      <li><?= t('admin.home.card.builder.li1') ?></li>
      <li><?= t('admin.home.card.builder.li2') ?></li>
      <li><?= t('admin.home.card.builder.li3') ?></li>
    </ul>
  </div>
  <div class="card">
    <h3>Pond <span class="badge"><?= t('admin.home.card.pond.title') ?></span></h3>
    <p><?= t('admin.home.card.pond.body') ?></p>
    <ul>
      <li><?= t('admin.home.card.pond.li1') ?></li>
      <li><?= t('admin.home.card.pond.li2') ?></li>
      <li><?= t('admin.home.card.pond.li3') ?></li>
    </ul>
  </div>
  <div class="card">
    <h3><?= t('admin.home.card.config.title') ?> <span class="badge">user/</span></h3>
    <p><?= t('admin.home.card.config.body') ?></p>
    <ul>
      <li><?= t('admin.home.card.config.li1') ?></li>
      <li><?= t('admin.home.card.config.li2') ?></li>
      <li><?= t('admin.home.card.config.li3') ?></li>
    </ul>
  </div>
  <div class="card">
    <h3><?= t('admin.home.card.url.title') ?> <span class="badge"><?= t('admin.home.card.url.badge') ?></span></h3>
    <p><?= t('admin.home.card.url.body') ?></p>
    <ul>
      <li><?= t('admin.home.card.url.li1') ?></li>
      <li><?= t('admin.home.card.url.li2') ?></li>
      <li><?= t('admin.home.card.url.li3') ?></li>
    </ul>
  </div>
</div>

<!-- ── 바로가기 ──────────────────────────────────────────────────── -->
<div class="sec-h"><?= t('admin.home.sec.actions') ?></div>
<div class="qa">
  <a href="<?= h($self) ?>?a=list">
    <div class="t"><?= t('admin.home.qa.list.t') ?></div>
    <div class="d"><?= t('admin.home.qa.list.d') ?></div>
    <div class="st"><?= t('admin.home.qa.list.st', ['posts' => (int)$postCount, 'cats' => (int)$catCount]) ?></div>
  </a>
  <a href="<?= h($self) ?>?a=new">
    <div class="t"><?= t('admin.home.qa.new.t') ?></div>
    <div class="d"><?= t('admin.home.qa.new.d') ?></div>
  </a>
  <a href="<?= h($self) ?>?a=deploy">
    <div class="t"><?= t('admin.home.qa.deploy.t') ?></div>
    <div class="d"><?= t('admin.home.qa.deploy.d') ?></div>
    <div class="st <?= $hasDeploy ? 'ok' : 'no' ?>">
      <?= $hasDeploy ? t('admin.home.qa.deploy.set') : t('admin.home.qa.deploy.unset') ?></div>
  </a>
  <a href="<?= h($self) ?>?a=settings">
    <div class="t"><?= t('admin.home.qa.settings.t') ?></div>
    <div class="d"><?= t('admin.home.qa.settings.d') ?></div>
    <div class="st <?= $hasSiteYaml ? 'ok' : 'no' ?>">
      <?= $hasSiteYaml ? t('admin.home.qa.settings.has') : t('admin.home.qa.settings.none') ?></div>
  </a>
</div>
<p class="muted" style="font-size:12px;margin:10px 0 0">
  <?= t('admin.home.qa.note') ?>
</p>

<!-- ── 핵심 원칙 ─────────────────────────────────────────────────── -->
<div class="sec-h" style="margin-top:30px"><?= t('admin.home.sec.principles') ?></div>
<ul class="principles">
  <li><?= t('admin.home.principle.li1') ?></li>
  <li><?= t('admin.home.principle.li2') ?></li>
  <li><?= t('admin.home.principle.li3') ?></li>
  <li><?= t('admin.home.principle.li4') ?></li>
  <li><?= t('admin.home.principle.li5') ?></li>
  <li><?= t('admin.home.principle.li6') ?></li>
</ul>

<p class="muted" style="font-size:12.5px;margin:24px 0 0">
  <?= t('admin.home.docs') ?>
</p>
<?php admin_foot();

<?php
// 공용 레이아웃 헬퍼 (admin v1.1.0 뷰). h()/CSRF 는 Pond.php 에 정의됨.
declare(strict_types=1);

function admin_head(string $title): void {
    global $CSRF;
    $self = $_SERVER['SCRIPT_NAME'];
    $act = $_GET['a'] ?? 'home';            // 활성 nav 강조용 현재 액션.
    $navOn = static fn(string $a): string => $act === $a ? ' class="on"' : '';
    ?><!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title><?= h($title) ?> · Pond admin</title>
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
</style>
</head>
<body>
<header class="bar">
  <a class="brand" href="<?= h($self) ?>?a=home" title="Heron + Pond 시스템 개요 (홈)">Pond admin<?php
    $ver = admin_program_version();
    if ($ver !== '') echo '<span class="ver">Heron v' . h($ver) . '</span>';
  ?></a>
  <nav>
    <a<?= $navOn('list') ?> href="<?= h($self) ?>?a=list">목록</a>
    <a<?= $navOn('new') ?> href="<?= h($self) ?>?a=new">+ 새 글</a>
    <a<?= $navOn('deploy') ?> href="<?= h($self) ?>?a=deploy" title="빌드된 dist/ 를 서버로 증분 동기화">배포</a>
    <a<?= $navOn('settings') ?> href="<?= h($self) ?>?a=settings" title="배포 대상 + 사이트 전역 설정 편집">설정</a>
  </nav>
  <form method="post" action="<?= h($self) ?>?a=checkupdate" style="display:inline"
        title="GitHub 에서 새 버전이 있는지 확인합니다">
    <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
    <button type="submit">업데이트 확인</button>
  </form>
  <form class="bld" method="post" action="<?= h($self) ?>?a=build"
        onsubmit="return confirm('python Heron.py 를 실행해 dist/ 를 다시 만듭니다. 계속할까요?')">
    <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
    <label class="muted" style="font-size:12px">
      <input type="checkbox" name="clean" value="1"> --clean</label>
    <button class="primary" type="submit">빌드</button>
  </form>
</header>
<main>
<?php
}

function admin_flash_errs(array $errs): void {
    if (!$errs) return;
    echo '<div class="flash err"><strong>처리 실패</strong><ul style="margin:6px 0 0">';
    foreach ($errs as $e) echo '<li>' . h($e) . '</li>';
    echo '</ul></div>';
}

function admin_foot(): void {
    ?>
</main>
<footer style="padding:14px 20px;color:#6b6b72;font-size:12px;border-top:1px solid #dcdce0;margin-top:30px">
  로컬 전용 도구 · 변경은 <code class="k">Articles/</code> 소스에만 반영됨 ·
  사이트(dist/)에 적용하려면 상단 <strong>빌드</strong> · 절대 공개 서버에 두지 말 것
</footer>
</body>
</html>
<?php
}

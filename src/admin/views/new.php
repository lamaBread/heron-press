<?php
// 새 글 폼 (admin v1.1.0). 변수: $scan, $flashErrs.
declare(strict_types=1);
require_once __DIR__ . '/layout.php';
$self = $_SERVER['SCRIPT_NAME'];
admin_head('새 글');
admin_flash_errs($flashErrs);
?>
<h2 style="margin:0 0 4px">새 글</h2>
<p class="muted" style="margin:0 0 18px">
  글 1개 = 폴더 1개 (<code class="k">content.md</code> + <code class="k">meta.yaml</code>).
  폴더명은 한국어 가능 — URL 은 아래 <strong>slug</strong> 로만 정해집니다(폴더명 무관·영구).
</p>
<form method="post" action="<?= h($self) ?>?a=create" style="max-width:680px">
  <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">

  <div class="field">
    <label>카테고리 (글이 들어갈 폴더)</label>
    <select name="category">
      <?php foreach ($scan['categories'] as $c): ?>
        <option value="<?= h($c) ?>"><?= $c === '' ? '(톱레벨 — Articles/ 바로 아래)' : h($c) ?></option>
      <?php endforeach; ?>
    </select>
  </div>

  <div class="field">
    <label>폴더명 (표시용 이름, 한국어 가능)</label>
    <input type="text" name="folder" id="folder" autocomplete="off"
           placeholder="예: 첫 번째 글">
  </div>

  <div class="field">
    <label>slug (URL — 소문자/숫자/하이픈, 영구)
      <span id="slughint" class="muted"></span></label>
    <input type="text" name="slug" id="slug" autocomplete="off"
           placeholder="폴더명 입력 시 자동 제안 (수정 가능)">
  </div>

  <div class="field">
    <label>제목 (&lt;title&gt; · 화면 제목)</label>
    <input type="text" name="title" id="title" autocomplete="off">
  </div>

  <div class="row" style="gap:20px">
    <div class="field" style="flex:1">
      <label>date (YYYY-MM-DD)</label>
      <input type="date" name="date" value="<?= h(date('Y-m-d')) ?>">
    </div>
    <div class="field" style="flex:1">
      <label>본문 형식</label>
      <select name="ext">
        <option value="md">content.md (마크다운)</option>
        <option value="html">content.html (HTML 본문)</option>
      </select>
    </div>
  </div>

  <div class="field">
    <label>tags (쉼표 구분, 선택)</label>
    <input type="text" name="tags" placeholder="예: essay, 에세이, writing">
  </div>

  <div class="field">
    <label>seo.description (SERP/소셜용 — 본문과 다른 글, 사실상 필수)</label>
    <textarea name="description" rows="2"></textarea>
  </div>

  <div class="row" style="margin-top:10px">
    <button type="submit" class="primary">만들고 편집으로</button>
    <a class="btn" href="<?= h($self) ?>?a=list">취소</a>
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
        ? '· 비ASCII → hex 자동변환됨 (ASCII slug 권장)' : '';
    } catch (e) {}
  }, 350);
});
</script>
<?php admin_foot();

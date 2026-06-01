<?php
// 편집기 뷰 (admin v1.1.0). 2분할(본문 + 메타) + 실시간 본문 미리보기.
// 변수: $id,$abs,$ext,$content,$metaRaw,$core,$scan,$saved,$err,$bothContent.
//
// 합의 모델: raw meta.yaml 이 진실원(저장은 raw 그대로 기록 + 헤더 보장).
// 위 핵심 입력칸은 *보조* — 바꾸면 아래 raw YAML 을 패치한다(단방향).
// raw 를 직접 고치면 위 칸과 어긋날 수 있고, 저장은 항상 raw 기준.
declare(strict_types=1);
require_once __DIR__ . '/layout.php';
$self = $_SERVER['SCRIPT_NAME'];
admin_head(t('admin.edit.title', ['name' => ($core['title'] ?: $id)]));
if ($saved) echo '<div class="flash ok">' . t('admin.edit.flash.saved') . '</div>';
if ($err) echo '<div class="flash err">' . t('admin.edit.flash.err') . '</div>';
?>
<div class="row" style="justify-content:space-between;margin-bottom:10px">
  <div>
    <a href="<?= h($self) ?>?a=list"><?= h(t('admin.edit.back')) ?></a>
    <h2 style="margin:6px 0 0"><?= h($core['title'] ?: $id) ?></h2>
    <div class="mono muted" style="font-size:12px"><?= t('admin.edit.path_label', ['id' => h($id), 'ext' => h($ext)]) ?></div>
  </div>
</div>
<?php if ($bothContent): ?>
  <div class="flash err"><?= t('admin.edit.both') ?></div>
<?php endif; ?>

<form method="post" action="<?= h($self) ?>?a=save" id="ed">
  <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
  <input type="hidden" name="id" value="<?= h($id) ?>">
  <div class="grid2">

    <!-- 좌: 본문 -->
    <section>
      <div class="row" style="justify-content:space-between">
        <strong><?= h(t('admin.edit.content.heading')) ?></strong>
        <label class="muted" style="font-size:12px"><?= h(t('admin.edit.content.format')) ?>
          <select name="ext" id="ext">
            <option value="md" <?= $ext==='md'?'selected':'' ?>>content.md</option>
            <option value="html" <?= $ext==='html'?'selected':'' ?>>content.html</option>
          </select></label>
      </div>
      <p class="muted" style="font-size:12px;margin:6px 0">
        <?= t('admin.edit.content.note', ['fmt' => $ext==='html'?t('admin.edit.content.format.html'):t('admin.edit.content.format.md')]) ?></p>
      <textarea name="content" id="content" rows="34"
        style="height:680px"><?= h($content) ?></textarea>
    </section>

    <!-- 우: 메타 + 미리보기 -->
    <section>
      <strong><?= h(t('admin.edit.meta.heading')) ?></strong>
      <div class="muted" style="font-size:12px;margin:6px 0 12px">
        <?= t('admin.edit.meta.note') ?></div>

      <div class="row" style="gap:14px">
        <div class="field" style="flex:2"><label>title</label>
          <input type="text" id="f_title" value="<?= h($core['title']) ?>"></div>
        <div class="field" style="flex:2"><label><?= t('admin.edit.meta.slug') ?></label>
          <input type="text" id="f_slug" value="<?= h($core['slug']) ?>"></div>
      </div>
      <div class="row" style="gap:14px">
        <div class="field" style="flex:1"><label>date</label>
          <input type="text" id="f_date" value="<?= h($core['date']) ?>"
                 placeholder="YYYY-MM-DD"></div>
        <div class="field" style="flex:1"><label><?= t('admin.edit.meta.updated') ?></label>
          <input type="text" id="f_updated" value="<?= h($core['updated']) ?>"
                 placeholder="YYYY-MM-DD"></div>
        <div class="field" style="flex:1"><label>noindex</label>
          <select id="f_noindex">
            <option value="false" <?= $core['noindex']?'':'selected' ?>>false</option>
            <option value="true" <?= $core['noindex']?'selected':'' ?>>true</option>
          </select></div>
      </div>
      <div class="field"><label><?= t('admin.edit.meta.tags') ?></label>
        <input type="text" id="f_tags"
               value="<?= h(implode(', ', $core['tags'])) ?>"></div>
      <div class="field"><label>seo.description</label>
        <textarea id="f_desc" rows="2"><?= h($core['description']) ?></textarea></div>

      <details open>
        <summary><?= t('admin.edit.meta.raw.summary') ?></summary>
        <textarea name="meta" id="meta" rows="14"
          style="height:300px"><?= h($metaRaw) ?></textarea>
      </details>

      <div class="row" style="margin:14px 0">
        <button type="submit" class="primary"><?= h(t('admin.edit.save')) ?></button>
        <span class="muted" style="font-size:12px"><?= t('admin.edit.save.note') ?></span>
      </div>

      <strong><?= h(t('admin.edit.preview.heading')) ?> <span class="muted" style="font-weight:400;font-size:12px">
        <?= t('admin.edit.preview.note') ?></span></strong>
      <iframe class="pv" id="pv" title="preview"></iframe>
    </section>
  </div>
</form>

<script>
const self = <?= json_encode($self) ?>, CSRF = <?= json_encode($CSRF) ?>,
      ID = <?= json_encode($id) ?>;
const $ = id => document.getElementById(id);
const content = $('content'), meta = $('meta'), ext = $('ext'), pv = $('pv');

// ── 보조 입력칸 → raw YAML 단방향 패치 (라인 기반·보수적) ──────────
function setTopScalar(text, key, val, quote) {
  const v = quote ? "'" + String(val).replace(/'/g, "’") + "'" : val;
  const re = new RegExp('^' + key + '\\s*:.*$', 'm');
  if (re.test(text)) return text.replace(re, key + ': ' + v);
  // 없으면 헤더 주석 블록 뒤에 삽입(없으면 맨 앞).
  const lines = text.split('\n');
  let i = 0;
  while (i < lines.length && (lines[i].trim() === '' ||
         lines[i].trim().startsWith('#'))) i++;
  lines.splice(i, 0, key + ': ' + v);
  return lines.join('\n');
}
function setTags(text, arr) {
  const list = '[' + arr.filter(s=>s.trim()).map(s =>
      "'" + s.trim().replace(/'/g,"’") + "'").join(', ') + ']';
  if (!arr.filter(s=>s.trim()).length)
    return text.replace(/^tags\s*:.*$/m, '').replace(/\n{3,}/g,'\n\n');
  if (/^tags\s*:.*$/m.test(text))
    return text.replace(/^tags\s*:.*$/m, 'tags: ' + list);
  return setTopScalar(text, 'tags', list, false);
}
function setDesc(text, val) {
  const v = "'" + String(val).replace(/'/g,"’") + "'";
  // seo: 블록의 description: 자식 줄을 교체. 없으면 seo 블록 만들기.
  if (/^seo\s*:/m.test(text)) {
    if (/^\s+description\s*:.*$/m.test(text))
      return text.replace(/^(\s+)description\s*:.*$/m, '$1description: ' + v);
    return text.replace(/^seo\s*:.*$/m, m => m + '\n  description: ' + v);
  }
  return text.replace(/\s*$/, '') + '\n\n\nseo:\n  description: ' + v + '\n';
}
function syncField(fn) {
  meta.value = fn(meta.value);
  schedulePreview();
}
$('f_title').addEventListener('input', e =>
  syncField(t => setTopScalar(t, 'title', e.target.value, true)));
$('f_slug').addEventListener('input', e =>
  syncField(t => setTopScalar(t, 'slug', e.target.value, false)));
$('f_date').addEventListener('input', e =>
  syncField(t => setTopScalar(t, 'date', e.target.value, false)));
$('f_updated').addEventListener('input', e =>
  syncField(t => e.target.value.trim()
    ? setTopScalar(t, 'updated', e.target.value, false)
    : t.replace(/^updated\s*:.*$\n?/m, '')));
$('f_noindex').addEventListener('change', e =>
  syncField(t => e.target.value === 'true'
    ? setTopScalar(t, 'noindex', 'true', false)
    : t.replace(/^noindex\s*:.*$\n?/m, '')));
$('f_tags').addEventListener('input', e =>
  syncField(t => setTags(t, e.target.value.split(','))));
$('f_desc').addEventListener('input', e =>
  syncField(t => setDesc(t, e.target.value)));

// ── 실시간 미리보기 (debounce) ────────────────────────────────────
let pt;
function schedulePreview() { clearTimeout(pt); pt = setTimeout(preview, 500); }
async function preview() {
  const fd = new FormData();
  fd.append('csrf', CSRF); fd.append('id', ID);
  fd.append('ext', ext.value); fd.append('content', content.value);
  fd.append('meta', meta.value);
  try {
    const r = await fetch(self + '?a=preview', {method:'POST', body:fd});
    pv.srcdoc = await r.text();
  } catch (e) {
    pv.srcdoc = '<p style="font:14px sans-serif;color:#b00">'
      + <?= json_encode(t('admin.edit.preview.fail')) ?> + e + '</p>';
  }
}
content.addEventListener('input', schedulePreview);
meta.addEventListener('input', schedulePreview);
ext.addEventListener('change', schedulePreview);
preview();
</script>
<?php admin_foot();

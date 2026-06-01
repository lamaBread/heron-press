<?php
// 글 목록 뷰 (admin v1.1.0). 변수: $scan, $trash, $flashErrs.
declare(strict_types=1);
require_once __DIR__ . '/layout.php';
$self = $_SERVER['SCRIPT_NAME'];
admin_head('목록');
admin_flash_errs($flashErrs);
foreach ([['moved','카테고리 이동 완료 (slug 불변이라 URL 영구).'],
          ['deleted','삭제 → .trash 로 이동 (빌드 자동 제외, 복구 가능).'],
          ['vis','공개/비공개 상태를 토글했습니다.']] as $f) {
    if (!empty($_GET[$f[0]])) echo '<div class="flash ok">' . h($f[1]) . '</div>';
}
$cats = $scan['categories'];

// v1.6.0 업데이트 배너 — admin_read_update_cache() 결과($updateInfo)에 기반.
// 캐시는 헤더 "업데이트 확인" 버튼이 GitHub 를 조회해 갱신한다 (페이지 로드마다
// 네트워크를 치지 않음).
$ui = $updateInfo ?? [];
if (!empty($ui['error'])):
?>
  <div class="flash err">업데이트 확인 실패 — <?= h((string)$ui['error']) ?></div>
<?php elseif (!empty($ui['update_available'])): ?>
  <div class="flash" style="background:#eef4ff;border:1px solid #c5d6f5;color:#234">
    <strong>새 버전 v<?= h(ltrim((string)($ui['latest'] ?? '?'), 'vV')) ?> 있음</strong>
    (현재 v<?= h((string)($ui['current'] ?? '?')) ?>).
    <form method="post" action="<?= h($self) ?>?a=update" style="display:inline;margin-left:8px"
          onsubmit="return confirm('GitHub 에서 최신 릴리스를 받아 프로그램(system/·Heron.py·Pond.php)을 교체하고 마이그레이션을 실행합니다. user/ 콘텐츠는 보존되고 직전 스냅샷이 user/.heron/backups/ 에 백업됩니다. 완료 후 Pond 재시작이 필요합니다. 계속할까요?')">
      <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
      <button class="primary" type="submit">지금 업데이트</button>
    </form>
  </div>
<?php elseif (!empty($_GET['checked']) && !empty($ui)): ?>
  <div class="flash ok">최신 버전입니다 (v<?= h((string)($ui['current'] ?? '?')) ?>).</div>
<?php endif; ?>
<?php // (배너 종료) ?>
<div class="row" style="justify-content:space-between;margin-bottom:14px">
  <h2 style="margin:0">글 <span class="muted">(<?= count($scan['posts']) ?>)</span></h2>
  <a class="btn" href="<?= h($self) ?>?a=new">+ 새 글</a>
</div>
<table>
  <thead><tr><th>제목</th><th>경로 (Articles/…)</th><th>상태</th>
    <th style="width:340px">동작</th></tr></thead>
  <tbody>
  <?php foreach ($scan['posts'] as $p): $eid = rawurlencode($p['id']); ?>
    <tr>
      <td><a href="<?= h($self) ?>?a=edit&id=<?= $eid ?>"><?= h($p['title']) ?></a></td>
      <td class="mono muted"><?= h($p['id']) ?></td>
      <td>
        <?php if ($p['hidden']): ?><span class="tag hid">비공개</span><?php
          else: ?><span class="tag">공개</span><?php endif; ?>
        <?php if ($p['both']): ?>
          <span class="tag warn">content.md+html 동시</span><?php endif; ?>
        <?php if ($p['ext'] === 'html'): ?><span class="tag">HTML</span><?php endif; ?>
      </td>
      <td>
        <div class="row">
          <a class="btn" href="<?= h($self) ?>?a=edit&id=<?= $eid ?>">편집</a>

          <form method="post" action="<?= h($self) ?>?a=move" class="row"
                style="gap:4px" onsubmit="return confirm('이 글을 선택한 카테고리로 이동합니다. (URL slug 는 그대로 — 영구)')">
            <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
            <input type="hidden" name="id" value="<?= h($p['id']) ?>">
            <select name="target" title="이동할 카테고리">
              <?php foreach ($cats as $c):
                if ($c === $p['parent']) continue; ?>
                <option value="<?= h($c) ?>"><?= $c === '' ? '(톱레벨)' : h($c) ?></option>
              <?php endforeach; ?>
            </select>
            <button type="submit">이동</button>
          </form>

          <form method="post" action="<?= h($self) ?>?a=visibility" style="display:inline">
            <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
            <input type="hidden" name="id" value="<?= h($p['id']) ?>">
            <button type="submit"><?= $p['hidden'] ? '공개' : '비공개' ?></button>
          </form>

          <form method="post" action="<?= h($self) ?>?a=delete" style="display:inline"
                onsubmit="return confirm('이 글을 .trash 로 보냅니다. 빌드에서 제외되며 파일은 남아 복구 가능합니다. 계속?')">
            <input type="hidden" name="csrf" value="<?= h($CSRF) ?>">
            <input type="hidden" name="id" value="<?= h($p['id']) ?>">
            <button type="submit" class="danger">삭제</button>
          </form>
        </div>
      </td>
    </tr>
  <?php endforeach; ?>
  <?php if (!$scan['posts']): ?>
    <tr><td colspan="4" class="muted">글이 없습니다. <a href="<?= h($self) ?>?a=new">새 글</a>을 써보세요.</td></tr>
  <?php endif; ?>
  </tbody>
</table>

<?php if ($trash): ?>
<h3 style="margin:26px 0 8px">.trash <span class="muted">(<?= count($trash) ?>)</span></h3>
<p class="muted" style="margin:0 0 8px">
  삭제된 글. <code class="k">.</code> 접두라 빌드에서 자동 제외됩니다.
  복구하려면 파일 탐색기에서 <code class="k">Articles/.trash/</code> 밖으로 폴더를 옮기세요
  (admin 은 의도적으로 영구 삭제 UI 를 두지 않습니다).</p>
<ul class="mono muted">
  <?php foreach ($trash as $t): ?><li><?= h($t) ?></li><?php endforeach; ?>
</ul>
<?php endif; ?>
<?php admin_foot();

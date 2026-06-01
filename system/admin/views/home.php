<?php
// 홈 / 시스템 개요 뷰 (v1.8.0). 브랜드("Pond admin") 클릭 시 도착하는
// 메인 페이지 — Heron(빌더) + Pond(이 도구)의 전체 흐름을 한눈에 시각화한다.
// 정본 설명서는 README.md/README.ko.md; 여기는 그 요약 + 바로가기.
// 변수: $ver(string), $postCount(int), $catCount(int),
//       $hasDeploy(bool), $hasSiteYaml(bool).
declare(strict_types=1);
require_once __DIR__ . '/layout.php';
$self = $_SERVER['SCRIPT_NAME'];
admin_head('홈');
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
    if ($ver !== '') echo '<span class="v">설치본 v' . h($ver) . '</span>'; ?></h1>
  <p>
    <strong>Heron</strong> 은 글 한 편을 폴더 하나로 두면 <code class="file">python Heron.py</code>
    한 번으로 사이트 전체를 정적 파일로 빚는 <strong>PHP 지향 정적 사이트 생성기</strong>입니다.
    <strong>Pond</strong>(이 도구)는 그 글을 로컬에서 쓰고·관리하고·빌드·배포까지 누르는
    <strong>얇은 관리 화면</strong>이에요. 아래는 글 한 편이 방문자에게 닿기까지의 전체 흐름입니다.
  </p>
</div>

<!-- ── 전체 파이프라인 ───────────────────────────────────────────── -->
<div class="flow">
  <div class="node you">
    <div class="k">당신 · Pond</div>
    <div class="t">글 작성</div>
    <div class="d"><code class="file">user/articles/</code> 폴더 하나 = 글 한 편
      (본문 + 이미지 + 첨부).</div>
  </div>
  <div class="arr">→</div>
  <div class="node">
    <div class="k">Heron.py</div>
    <div class="t">빌드 (16단계)</div>
    <div class="d">Markdown 렌더 · 이미지 WebP 변환 · 검색 인덱스 · 사이트맵/피드
      생성. Python 3 표준라이브러리(+Pillow)만 사용.</div>
  </div>
  <div class="arr">→</div>
  <div class="node">
    <div class="k">산출물</div>
    <div class="t">dist/</div>
    <div class="d">정적 HTML + <code class="file">search.php</code>.
      입력이 같으면 바이트까지 동일(결정적 빌드).</div>
  </div>
  <div class="arr">→</div>
  <div class="node">
    <div class="k">배포 · rclone</div>
    <div class="t">증분 동기화</div>
    <div class="d">바뀐 파일만 SFTP 로 업로드, 서버에만 남은 옛 파일은 정리.</div>
  </div>
  <div class="arr">→</div>
  <div class="node srv">
    <div class="k">서버 · 방문자</div>
    <div class="t">Apache + PHP</div>
    <div class="d">일반 페이지는 정적으로 즉시 서빙, <code class="file">/search.php</code>
      만 BM25 검색을 실행.</div>
  </div>
</div>

<!-- ── 구성 요소 ─────────────────────────────────────────────────── -->
<div class="sec-h">구성 요소</div>
<div class="cards">
  <div class="card">
    <h3>Heron.py <span class="badge">Python 빌더</span></h3>
    <p>모든 로직의 단일 진실원. <code class="file">user/articles/</code> 만 읽어
      <code class="file">dist/</code> 를 만들고, <code class="file">user/</code> 는
      절대 건드리지 않습니다(읽기 전용).</p>
    <ul>
      <li>래스터 이미지 → 다해상도 WebP + <code class="file">srcset</code> · lazy-load</li>
      <li>증분 캐시 — 바뀐 글만 다시 렌더</li>
      <li>클라이언트 JS 없는 검색을 <code class="file">search.php</code> 에 인라인</li>
    </ul>
  </div>
  <div class="card">
    <h3>Pond <span class="badge">이 관리 화면</span></h3>
    <p>로컬 전용 단일 사용자 도구(루프백에서만 동작). 마크다운/slug 를 PHP 로
      재구현하지 않고 실제 빌드 스크립트를 그대로 호출합니다 — 미리보기·빌드가
      배포 결과와 어긋나지 않게.</p>
    <ul>
      <li><strong>목록·새 글·편집</strong> — 실시간 미리보기 포함</li>
      <li><strong>빌드·배포</strong> — 한 번의 클릭으로</li>
      <li><strong>설정</strong> — 배포 대상 + 사이트 전역 설정 편집</li>
    </ul>
  </div>
  <div class="card">
    <h3>설정 파일 <span class="badge">user/</span></h3>
    <p>두 층위의 설정이 빌드를 좌우합니다. 모두 <strong>설정</strong> 화면에서
      편집할 수 있어요.</p>
    <ul>
      <li><code class="file">site.yaml</code> — 도메인·사이트명·이미지/광고/JSON-LD 등
        사이트 전역 (저장 시 빌드와 동일 검증 통과해야 기록)</li>
      <li><code class="file">meta.yaml</code> — 글마다의 slug·제목·날짜·태그·노출</li>
      <li><code class="file">.heron/deploy.json</code> — 배포 서버 정보(개인키는 경로만)</li>
    </ul>
  </div>
  <div class="card">
    <h3>영구 URL &amp; 안전장치 <span class="badge">설계</span></h3>
    <p>글의 URL 은 <code class="file">slug</code> 이고 폴더·카테고리와 분리돼 있어,
      카테고리를 옮겨도 URL 은 그대로입니다.</p>
    <ul>
      <li>삭제는 <code class="file">.trash</code> 이동(빌드 제외·복구 가능)</li>
      <li>설정 저장 전 직전본을 <code class="file">.heron/backups/</code> 에 백업</li>
      <li>GitHub 릴리스로 원클릭 자가 업데이트 + 마이그레이션</li>
    </ul>
  </div>
</div>

<!-- ── 바로가기 ──────────────────────────────────────────────────── -->
<div class="sec-h">여기서 할 수 있는 일</div>
<div class="qa">
  <a href="<?= h($self) ?>?a=list">
    <div class="t">글 목록</div>
    <div class="d">편집 · 이동 · 공개/비공개 · 삭제</div>
    <div class="st"><?= (int)$postCount ?>편 · <?= (int)$catCount ?>개 카테고리</div>
  </a>
  <a href="<?= h($self) ?>?a=new">
    <div class="t">+ 새 글</div>
    <div class="d">폴더 한 개로 글 한 편 시작</div>
  </a>
  <a href="<?= h($self) ?>?a=deploy">
    <div class="t">배포</div>
    <div class="d">dist/ 를 서버로 증분 동기화</div>
    <div class="st <?= $hasDeploy ? 'ok' : 'no' ?>">
      <?= $hasDeploy ? 'deploy.json 설정됨' : 'deploy.json 미설정' ?></div>
  </a>
  <a href="<?= h($self) ?>?a=settings">
    <div class="t">설정</div>
    <div class="d">배포 대상 + site.yaml 편집</div>
    <div class="st <?= $hasSiteYaml ? 'ok' : 'no' ?>">
      <?= $hasSiteYaml ? 'site.yaml 있음' : 'site.yaml 없음' ?></div>
  </a>
</div>
<p class="muted" style="font-size:12px;margin:10px 0 0">
  빌드는 상단 우측 <strong>빌드</strong> 버튼 · 새 버전 확인은 <strong>업데이트 확인</strong>.
</p>

<!-- ── 핵심 원칙 ─────────────────────────────────────────────────── -->
<div class="sec-h" style="margin-top:30px">핵심 원칙</div>
<ul class="principles">
  <li><strong>최소 운영 의존성</strong> — 빌드는 Python 표준라이브러리, 런타임은 Apache+PHP뿐</li>
  <li><strong>단일 진실원</strong> — 로직은 Python 한 곳에, Pond 는 얇은 트리거</li>
  <li><strong>결정적 빌드</strong> — 같은 입력이면 dist/ 가 바이트까지 동일</li>
  <li><strong>서버/콘텐츠 분리</strong> — <code class="file">.htaccess</code> 없이 VirtualHost 한 번</li>
  <li><strong>영구 URL</strong> — slug 가 URL, 카테고리 이동에 불변</li>
  <li><strong>다크모드 자동</strong> — OS <code class="file">prefers-color-scheme</code> 신뢰</li>
</ul>

<p class="muted" style="font-size:12.5px;margin:24px 0 0">
  자세한 설명서는 저장소 루트의 <code class="file">README.md</code>(영문) /
  <code class="file">README.ko.md</code>(국문) 에 있습니다 — 두 문서는 같은 깊이로 동등합니다.
</p>
<?php admin_foot();

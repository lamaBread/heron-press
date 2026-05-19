"""siheonlee.com v1.0.1 — 빌더 내부 모듈 묶음.

이 패키지는 v0.8.1 부터 `src/scripts/` 에 있다 (최상위 정리 — 빌더
일체가 src/ 아래로 이동). 프로젝트 루트의 build.py 가 자기 폴더의 src/
를 sys.path 에 올린 뒤 이 패키지를 import 한다.
모듈:
  - yaml_parser  — stdlib only YAML 부분 구현
  - models       — dataclass 정의 (SiteConfig, ArticleMeta, SeoMeta, ...)
  - slugs        — 카테고리/폴더명 → slug 변환
  - markdown     — 마크다운 본문 후처리 + PHP 함수 시뮬레이션 + per-article styles
  - parsedown    — Parsedown 1.7.4 의 Python 포팅 (v0.4.1)
  - seo          — <meta> 태그 + JSON-LD 빌더. v0.5.5 본문 폴백 제거 (메타데이터
                   분리 원칙). v0.8.3 schema.org JSON-LD (build_jsonld) 추가.
  - images       — 이미지 자동 최적화 (WebP + srcset + lazy loading, v0.5.1)
  - search       — 토크나이저, BM25 인덱스, PHP 정적 배열 직렬화 (v0.6.0 v4 포맷)
  - sitemap      — sitemap.xml 생성 (v0.4.4)
  - feed         — RSS / Atom 피드 생성 (v0.5.3)
  - report       — BuildReport / issue / warning / abort (v0.5.5)
  - cache        — 글 단위 빌드 증분 캐시 (v0.7.0 신설)
  - builder      — 빌드 파이프라인 (Builder 클래스)

__version__:
  사이트 전역 버전 문자열의 단일 source of truth.

  v0.8.2 의 버전 디커플링 (B1) 이전까지는 feed.atom/feed.rss 의
  <generator> 가 이 값을 표기해 dist 산출물에 새는 유일한 경로였다.
  그 때문에 문서·구조 전용 릴리스 (v0.7.2 → v0.8.0 → v0.8.1) 는 이
  값을 '0.7.2' 에 동결해야 dist byte-동일 검증이 성립했다.

  v0.8.2 부터 generator 문자열에서 버전 토큰이 제거돼 `__version__`
  은 **dist 산출물에 전혀 영향을 주지 않는다**. 남은 소비자는 모두
  dist 밖이다:
    - cache global_hash (`cache.py`) — 빌더 버전이 바뀌면 캐시 일괄
      무효화. 단 코드 릴리스는 `scripts/` 해시로 이미 무효화되므로
      실효는 거의 없고, 문서 릴리스는 캐시를 유지하는 게 옳다.
    - 빌드 콘솔 출력 / build-report.md (모두 dist 밖).
  따라서 이 값은 이제 릴리스 버전을 자유롭게 추종한다 — 더 이상
  byte-동일 검증을 위해 동결할 필요가 없다.

  주의 (v0.8.3): v0.8.3 은 dist 를 바꾼다 — 글 페이지에 JSON-LD
  스크립트 한 줄 추가 + 정확한 빵부스러기 (중간 조상=자기 중첩
  URL, 글 말단=글 제목). 그러나 그것은 **JSON-LD 기능·정확
  빵부스러기** 때문이지 `__version__` 때문이 아니다 — 위 B1
  디커플링은 그대로 유효해 버전 문자열 자체의 dist 영향은 여전히
  0 이다. 그래서 v0.8.3 의 무결성 계약은 "문서 전용 = 직전과
  sha256 동일" 이 아니라 코드 릴리스용 "결정성 2회 동일 + 직전
  (v0.8.2) 대비 *열거된* diff" (= 글 렌더 페이지에 한정, 그 외
  byte 불변) 이다.

  v0.8.4 는 v0.8.3 의 *문서 안정화* (코드 로직 무변경) — v0.8.3
  README 에 남아 있던 잘못된 수치/표현만 §16 의 정정값에 정합:
  한 줄 요약 박스·§3 트리의 `단위 266→297` → `266→313` (실제
  스위트 313 — 라이브 실행·[1]·§16 모두 일치, 297 은 stale 잔재),
  §3 트리 `run_diagnostics.py (5 항목)` → `(6 항목)` ([6] 게이트는
  v0.8.3 신설), box/§3 노트의 미검증 하드 수치 framing → §16 의
  정성 서술에 일치. `diagnostics_report.txt` 는 stale 가 아니라
  정상이었다 ([6]=37/36 은 article `index.html` 한정인 게이트
  스코프상 정확) — v0.8.4 클린 재빌드 후 재생성해 임베드 경로·
  실행 메타만 v0.8.4 로 갱신, 결과는 불변 ([1]=313, [2] 결정성,
  [6]=37/36 violations 0, 6/6). 빵부스러기/JSON-LD 로직 무변경,
  `__version__` 0.8.3→0.8.4 는 B1 으로 dist 누수 0 — v0.8.4
  무결성 계약은 문서 전용 형 (정본 클린 재빌드 후 dist sha256
  == 직전 코드 복사본 v0.8.3; 실측 785=785 byte-동일).

  v1.0.0 은 첫 정식 릴리스이자 *기능* 릴리스 — dist 가 바뀐다 (B1 은
  유지라 `__version__` 0.8.4→1.0.0 자체의 dist 누수는 0). 두 변경:
  (1) 기본 og:image 자산 패스스루 — `_copy_site_assets` 가
  `site.default_og_image` 가 가리키는 자산만 webp 변환·variant 등록을
  건너뛰고 원본을 그대로 dist 에 낸다. og:image 소비자는 `<img srcset>`
  후처리가 아니라 SNS 링크 언퍼ler — 고정 URL 하나만 가져가 다중
  해상도가 무의미하고, KakaoTalk·일부 Facebook 은 WebP og:image 를
  못 렌더하며, `resolve_og_image` 가 이 값을 문자열 그대로 쓰므로
  변환 시 그 URL 이 404 가 된다 (seo.py 의 "소비자가 다르다" 원칙).
  실제 `default-og.png`(1200×480) 자산 동반 — v0.8.4 까지는 site.yaml
  이 가리키는 경로에 파일이 없어 본문 이미지 없는 모든 페이지의
  og:image 가 죽은 404 였다 (latent 결함 해소). (2) `About` 글
  `noindex: true` — 그 페이지 robots noindex + sitemap.xml·검색
  인덱스에서 제외. (피드는 최신 20개 윈도우라 date 2025-01-01 인
  About 은 v0.8.4 에서도 이미 미수록 — noindex 가 피드엔 no-op.)
  v0.8.4 대비 실측 dist diff (786 vs 785) = +assets/default-og.png,
  Δ about/index.html(robots 한 줄)·sitemap.xml·search.php;
  feed.rss/feed.atom 포함 그 외 전부 byte-불변, 클린 빌드 2회
  결정성 동일 (combined sha256 bf4293c7…) — 코드 릴리스 형
  무결성 계약.

  v1.0.1 은 소분류 헤더 UI *기능* 릴리스 — dist 가 바뀐다 (B1 유지라
  `__version__` 1.0.0→1.0.1 자체의 dist 누수는 0). 변경 한 가지:
  톱레벨 카테고리 페이지의 자식 소분류 section 헤더에서 (1) 우측
  → 화살표를 폐지하고 (2) 소분류명 글씨 자체를 그 소분류 페이지
  (`more_url` = `/{top}/{sub}/`)로 가는 스타일 없는 링크로 만든다 —
  글씨를 클릭하면 그 소분류 글만 보인다. `_render_section` 의
  `more_url` 분기가 `{label} <a class='more-link'>→</a>` 대신
  `<a class='subcat-link'>{label}</a>` 를 내고, `common_template
  .css` 의 `.more-link` 3 룰을 `.gap .subcat-link` 1 룰(color
  inherit + text-decoration none, 호버 없음 — 본문 글씨와 동일
  외양)으로 교체. `more_url` 없는 section(자기 직속 글)·홈의 정적
  "Recent posts" 갭은 무영향. 무결성 = 코드 릴리스 형 (정본
  Articles 고정, v1.0.0 코드 클린 재빌드[검증 복사본 v1.0.0.1] vs
  v1.0.1 클린 재빌드 열거 diff): 5 파일만 변경 — `assets/common_
  template.css` + `blog`·`project`·`research`·`study`/`index.html`
  (자식 소분류를 둔 4 톱레벨 카테고리 페이지), 0 added/0 removed,
  781 byte-동일(786=786). 홈·소분류 말단 페이지·피드·사이트맵·
  검색·robots·글 페이지 전부 byte-불변. 결정성: v1.0.1 클린 빌드
  2회 dist 완전 동일 (combined sha256 bac1e2c6…). 단위 313 승계,
  진단 6/6. 부수 발견(이번 변경과 직교): 불변 아카이브 v1.0.0 의
  *shipped* `dist/index.html`(홈) 이 v1.0.0 코드 클린 재빌드와
  1파일 불일치 — v1.0.0 자체의 사전 staleness. 그래서 baseline 을
  shipped dist 가 아니라 v1.0.0 *코드* 클린 재빌드로 잡아(v0.8.3
  식 클린-vs-클린) 순수 코드 델타를 격리했다. v1.0.0 폴더는 불변
  아카이브라 손대지 않았다 (검증은 4번째 숫자 복사본 v1.0.0.1 에서).
"""

__version__ = '1.0.1'

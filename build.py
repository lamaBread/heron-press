#!/usr/bin/env python3
"""siheonlee.com v1.2.2 — PHP 기반 경량 웹 사이트 생성기.

이 파일은 빌드의 진입점(entry point) 일 뿐, 모든 실제 로직은
`src/scripts/` 패키지 안에 모듈별로 나뉘어 있다 (v0.8.1 재배치 — 아래
폴더 구조 참조). 사이트 전역 버전 문자열은
[src/scripts/__init__.py](src/scripts/__init__.py) 의 `__version__` 이
단일 source of truth — 피드 generator 등이 이 값을 참조.

폴더 구조 (v0.8.1):
    Articles/    글 소스 (최초엔 참고용 자료들)
    dist/        빌드 산출물 (최초엔 빈 폴더)
    src/         빌더 일체 — scripts/ (Python 패키지) · templates/ ·
                 assets/ · tests/ · admin/ (v1.1.0 로컬 글쓰기 도구)
    admin.php    로컬 글쓰기 진입점 (v1.1.0 — 얇은 라우터; 빌더 무관,
                 dist 미포함. 이 파일과 직교한 별도 저작 도구)
    build.py     빌드 진입점 (이 파일)
    README.md    문서
    site.yaml    전역 설정
  최상위에는 위 7 개만 보인다 (v1.1.0 에서 admin.php 1 개 추가 — 빌더는
  Articles/ 만 스캔하므로 admin.php·src/admin/ 은 dist 에 새지 않는다).
  build.py 가 자기 폴더의 src/ 를 sys.path 맨 앞에 올려 `import
  scripts...` 가 src/scripts/ 를 가리킨다.

Usage:
    python build.py                # full build (캐시 사용)
    python build.py --clean        # wipe dist/, .build_cache/ 후 빌드
    python build.py --clean-cache  # .build_cache/ 만 폐기 후 빌드 (dist 는 유지)
    python build.py --no-cache     # 증분 캐시 비활성 (v0.6.5 동작)
    python build.py --help         # 인자 도움말 (v0.8.2: argparse)
    python -m unittest discover -s src/tests   # 단위 테스트 (v0.8.3: 313개)
    python src/tests/run_diagnostics.py        # 빌드 결정성/BM25 패리티 등 통합 진단

v0.8.2 부터 인자 파싱이 argparse 라 미지/오타 인자 (`--clena` 등) 는 조용히
무시되지 않고 즉시 거부된다 (exit 2 + usage). 유효 인자의 빌드 동작은
v0.8.1 과 1:1 동일.

빌드가 끝나면 build.py 가 있는 폴더에 `build-report.md` 가 생성/갱신된다 —
터미널 진행·요약·보완 필요/살펴볼 사항을 마크다운으로 서식화한 문서
(v0.7.2 신설). dist/ 산출물에는 포함되지 않으므로 빌드 결정성과 무관.

빌드 의존성 (v0.7.2):
    Python 3.10+ stdlib
    Pillow (PIL fork) — 이미지 자동 최적화 (`pip install Pillow`).
        site.yaml 의 images.enabled=false 로 두면 Pillow 없어도 동작.

v1.2.2 변경 사항 (vs v1.2.1) — yaml_parser 멀티라인 inline list 지원 (코드, dist 의도 변경):
  - **`yaml_parser` 멀티라인 inline list 지원** — v0.4.0 의 분기가
    `val.startswith('[') and val.endswith(']')` 라 같은 줄에 `]` 가 없는
    `exclude_urls: [\n  '/',\n  ...\n]` 같은 multi-line 형이 silently 스칼
    라 `'['` 로 파싱돼 frozenset(['/[']) 로 정규화 → URL 매칭 0건 (의도된
    AdSense 차단 미작동). 헬퍼 `parse_inline_list_multiline(first_val)` 신설
    — `[` 로 시작하고 `]` 가 후속 줄에 있으면 `]` 줄까지 누적해 inline list
    로 파싱. 줄 단위 trailing comma · 단독 주석 줄 허용. 두 호출 사이트
    (top-level loop · `parse_block_map`) 를 `startswith('[')` 단일 검사로
    통일 후 `endswith(']')` 여부로 single/multi-line 분기. single-line 케이스
    동치 분기 그대로 — v0.4.0 의 모든 yaml 호환.
  - **무결성** = 코드 릴리스 형이되 dist 가 *의도된* 1줄 변화. 정본
    Articles 기본은 그대로 `siheonlee.com_v1.2.0.1/Articles`. site.yaml 도
    v1.2.1 의 service-tuned 본 그대로(`exclude_urls` multi-line 형). 비교
    baseline = `siheonlee.com_v1.2.0.1/dist`. 변화: 26 URL 의 자동광고
    로더 한 줄이 마침내 사라진다(v1.2.1 까진 파싱 실패로 dormant). 그
    외 자산·feed·sitemap·검색 인덱스 등 본문 무관 산출물 byte-불변.
    `__version__` 1.2.1→1.2.2 dist 누수 0 (B1 유지). 단위 367→**374**
    (`MultilineInlineListTests` 7 신설). 진단 6/6 승계.

v1.2.1 변경 사항 (vs v1.2.0) — 운영 잡음 정리 릴리스 (코드, dist byte-불변):
  - **noindex 글의 `seo.description` 필수 검사 면제** — `noindex: true` 인
    글은 robots noindex + sitemap/feed/검색 인덱스에서 모두 제외되므로 SERP
    스니펫·피드 summary 가 무의미. description 부재가 더는 "외부 노출용
    빠뜨림" 이 아니다 (정본 `About` 이 그 예). og:description 미리보기는
    여전히 author 가 원하면 적을 수 있다 (검사 면제일 뿐 출력 경로 불변).
    빈 문자열 `''` 도 동일 경로 (m.noindex 분기가 None/''/text 3-상태에
    선행). 비-noindex 글에 대한 v0.5.5 정책은 그대로.
  - **`warn_on_stale_updated` 워닝 일괄 제거** — content.md 파일 mtime 이
    meta.yaml `updated` 보다 새로울 때 띄우던 warning. 의도적 mtime>updated
    케이스가 흔해 매 빌드 잡음이라 사용자 결정으로 완전 폐기 (builder.py
    검사 블록 + `Date` import + `SiteConfig.warn_on_stale_updated` 필드 +
    4 테스트 kwarg + site.yaml 행/주석 + README §11·§7·report.py docstring
    일괄 삭제, no-migration). updated 자체 의미 (lastmod) 와 `updated <
    date` 형식 검사는 무변경.
  - **무결성** = 코드 릴리스 형이되 *dist byte-불변* 형. 정본 Articles 기본
    이 2026-05-21 부터 `siheonlee.com_v1.2.0.1/Articles` (사용자 서비스용
    조정본). 비교 baseline = `siheonlee.com_v1.2.0.1/dist` 클린 재빌드.
    dist byte-동일 추론: noindex `_issue`·stale_updated `_warning` 호출
    변화는 BuildReport.entries (dist 미경유, 터미널·build-report.md 표시
    전용), 그 외 코드 경로 무변경. `__version__` 1.2.0→1.2.1 dist 누수 0
    (B1 유지). 단위 364→**367** (`NoindexDescriptionExemptionTests` 3
    신설). 진단 6/6 승계.

v1.2.0 변경 사항 (vs v1.1.5) — 안정화 릴리스 (문서 전용, dist byte-불변):
  - **빌드 로직·테스트·dist 산출물 무변경** — v1.1.5 의 URL 기반 광고 차단
    기능을 그대로 승계. `__version__` 1.1.5→1.2.0 자체의 dist 누수 0
    (B1 유지 — v0.8.2 의 generator 디커플링 그대로).
  - **README 정리** — v1.1.5 까지 누적된 §16 v1.x.x 변경 인용구(>)를 표
    행으로 압축, 한 줄 요약을 진짜 한 줄로(v1.1.2 의 장황한 박스 제거),
    §3 폴더명(`siheonlee.com_v1.1.0/` → `_v1.2.0/`)·§15 "현재 한계
    (v1.1.2)" → "(v1.2.0)"·바닥글의 stale 표기·v1.1.5 인용구 순서 어긋남
    교정. `__init__.py`·`build.py` docstring 도 v1.2.0 헤더 + v1.2.0
    changelog 단락 추가.
  - **무결성** = 문서 전용 형 (정본 Articles 고정, 직전 코드 복사본
    `siheonlee.com_v1.1.5` 의 v1.1.5 *코드* 클린 재빌드 vs v1.2.0 클린
    재빌드의 dist 가 sha256 byte-완전 동일 — 모든 docstring/README 변경은
    빌더 입력이 아니다). v0.8.4 ↔ v0.8.3 선례와 일치.

v1.1.5 변경 사항 (vs v1.1.4) — AdSense URL 기반 광고 차단 (기능 릴리스, 기본값 byte-불변):
  - **`exclude_pages` → `exclude_urls` 교체** — v1.1.4 의 page-type 5종
    식별자(`article`/`home`/`category`/`404`/`search`) 방식은 폐기. 새 필드
    `exclude_urls` 는 사이트 내 임의 URL 의 절대 경로 리스트(예
    `['/', '/about/', '/404.html']`) 로 정확 일치 매칭(case-sensitive ·
    trailing-slash 포함). 페이지별 canonical URL: 홈=`/`, 글=`/<slug>/`,
    카테고리=`/<slug_path>/`, 404=`/404.html`, 검색=`/search.php`. 이로써
    v1.1.4 의 "어느 페이지 *타입*" 단위 통제가 "어느 *URL*" 단위로 일원화
    되어, 개별 글 차단 (예: `/about/`·`/clear/`) 이 자연스럽게 가능. 빈
    리스트/키 부재면 v1.1.3 과 동일 동작 (5 페이지 전체 주입). 빈
    `head_script` = 전체 차단 의미는 유지 — 빈 문자열이면 `exclude_urls`
    와 무관하게 5 페이지 모두 미주입.
  - **호환성** — v1.1.4 의 `exclude_pages` 키는 v1.1.5 파서가 무시
    (`raw.get('exclude_urls')` 만 본다) → 옛 site.yaml 이 자동으로
    "전체 주입" 으로 안전 폴백. compat shim 없이 깨끗한 교체.
  - **검증 워닝** — 매 페이지 렌더 시 `_apply_adsense_head_placeholder`
    가 자기 URL 을 `self._adsense_seen_urls` 에 적재; 빌드 종료 직후
    새 `_check_exclude_urls()` 가 `exclude_urls - seen` 차집합을
    BuildReport warning 으로 보고(오타·삭제된 글 감지). 산출물 영향 0
    — quiet check, `_step` 번호 추가 없음.
  - **코드 변경** — `AdSenseConfig.exclude_pages: frozenset[str]` →
    `exclude_urls: frozenset[str]`. 파서 `_parse_adsense_config` 가
    `raw.get('exclude_urls')` 를 받아 leading `/` 보정 (`about/` →
    `/about/`) + `str().strip()` 정규화 + frozenset 변환(대소문자 보존).
    헬퍼 `_apply_adsense_head_placeholder(tpl, page_url)` 시그니처에서
    `page_type` → `page_url` 로 교체. 5 호출 위치 모두 자기 페이지 URL
    전달. 빌더 클래스 변수 `_ADSENSE_PAGE_TYPES` 폐지(URL 매칭으로 enum
    의미 사라짐). 빌더 인스턴스 속성 `self._adsense_seen_urls: set[str]`
    신설(build() 진입 시 reset).
  - **결정성·산출물** — 코드 릴리스 형이되 *기본값 byte-불변* 형. 정본
    Articles 고정, 불변 `siheonlee.com_v1.1.4` 미수정·4번째-숫자 검증
    복사본 `siheonlee.com_v1.1.4.2` 의 v1.1.4 *코드* 클린 재빌드 with
    `exclude_pages: []` vs v1.1.5 클린 재빌드 with `exclude_urls: []` 의
    dist 가 **byte-완전 동일** 목표(두 빈 리스트는 동일 `frozenset()` 으로
    정규화돼 5 호출 위치에서 v1.1.3·v1.1.4 와 동일 분기 경로). 운영자가
    실제 URL 을 추가하면 매칭된 페이지들의 HTML 에서 자동광고 스크립트
    한 줄이 사라지는 것만이 변화 — 그 외 산출물 byte-불변. 클린 빌드 2회
    결정성 동일. `__version__` 1.1.4→1.1.5 의 dist 누수 0 (B1 유지).

v1.1.4 변경 사항 (vs v1.1.3) — AdSense 페이지 타입 제외 리스트 (기능 릴리스, 기본값 byte-불변):
  - **AdSense `exclude_pages` 필드 추가** — site.yaml `google_adsense:`
    블록에 `exclude_pages` 신설 (문자열·정수 리스트). 매칭된 페이지 타입은
    `{{ADSENSE_HEAD}}` placeholder 가 line-eating 으로 제거되어 그 페이지
    head 에 auto-ads 로더 스크립트가 들어가지 않는다 = Google auto-ads JS
    자체가 로드되지 않아 광고 원천 차단. 페이지 단위 on/off 메커니즘 —
    인-페이지 광고 위치는 여전히 Google auto-ads 알고리즘이 결정한다.
    식별자 5종: `article` / `home` / `category` / `404` / `search`.
    모르는 식별자는 자연 무시 (forward compat). `AdSenseConfig
    .exclude_pages: frozenset[str]` 신설 + 파서가 리스트(또는 단일 스칼라)
    수용 + `str.strip().lower()` 정규화 + frozenset 변환 (yaml `404` 의
    int 파싱도 str() 캐스팅으로 흡수). `_apply_adsense_head_placeholder
    (tpl, page_type)` 헬퍼 시그니처에 `page_type` 추가, 5 호출 위치가
    각자 식별자(`'article'` / `'category'` / `'home'` / `'404'` /
    `'search'`)를 넘긴다. v1.1.3 의 `head_script` 빈 문자열 = 전체 차단
    의미는 유지 — 빈 문자열이면 exclude_pages 와 무관하게 5 페이지 모두
    미주입.
  - **결정성·산출물** — 코드 릴리스 형이되 *기본값 byte-불변* 형. 정본
    Articles 고정, 불변 `siheonlee.com_v1.1.3` 미수정·4번째-숫자 검증
    복사본 `siheonlee.com_v1.1.3.1` 의 v1.1.3 *코드* 클린 재빌드 vs
    v1.1.4 클린 재빌드 with `exclude_pages: []`(=기본값)의 dist 가
    **787=787, 0 added/0 removed/0 changed = byte-완전 동일** (모든
    부재 상태 — 키 부재·빈 리스트·None — 가 동일 frozenset() 으로
    정규화돼 v1.1.3 와 같은 분기 경로). 운영자가 실제 페이지 타입을
    추가하면(예 `[404, search]`) 그 페이지들의 HTML 에서
    `<script async src=...adsbygoogle...>` 한 줄이 사라지는 것만이
    변화 — 그 외 자산·feed·sitemap·검색 인덱스 byte-불변. 클린 빌드
    2회 결정성 동일. `__version__` 1.1.3→1.1.4 의 dist 누수 0 (B1 유지).

v1.1.3 변경 사항 (vs v1.1.2) — Google AdSense 통합 + 기본 og:image 자산 교체 (기능 릴리스):
  - **(1) AdSense 통합** — site.yaml `google_adsense:` 블록 신설
    (`ads_txt` + `head_script` 두 문자열 필드, `AdSenseConfig`
    dataclass). 두 필드는 빈 문자열/키 부재 시 자동 비활성 (SeoMeta 의
    3-state 원칙 일관 — 별도 enabled 마스터 토글 없음). `ads_txt` 는
    새 빌드 단계 [11b] `_build_ads_txt` 가 `dist/ads.txt` 로 그대로
    기록(robots.txt 와 같은 패턴); 빈 값이면 미생성 + 이전 빌드의
    잔존 ads.txt 가 있으면 삭제 (stale 가드). `head_script` 는 5 개
    템플릿(article·home·category·404·search.php)의 `<head>` 에 새
    `{{ADSENSE_HEAD}}` placeholder 로 raw 그대로 주입 (escape 없음);
    빈 값이면 placeholder 라인 자체 strip (ROBOTS_META · JSONLD ·
    COMMON_CSS 와 동일 line-eating 패턴, 공용 헬퍼
    `_apply_adsense_head_placeholder`). 적용 대상은 사용자가 방문하는
    5 개 dist 페이지 종류 — `admin.php`/`src/admin/` 은 빌더가 dist
    에 내보내지 않으므로 자연 제외.
  - **(2) 기본 og:image 자산 교체** — `src/assets/default-og.png` 를
    표준 OG 규격으로 갱신 (1200×480 → 1200×630, Pretendard SemiBold).
    v1.0.0 의 default_og_image 패스스루 예외 그대로 — webp 변환 없이
    원본 그대로 `dist/assets/` 로 복사돼 SNS 언퍼ler 가 고정 URL 로
    가져간다.
  - **결정성·산출물** — 코드 릴리스 형·dist 의도적 변경형. 정본
    Articles 고정, 불변 `siheonlee.com_v1.1.2` 미수정·4번째-숫자 검증
    복사본 `siheonlee.com_v1.1.2.1` 의 v1.1.2 *코드* 클린 재빌드 vs
    v1.1.3 클린 재빌드의 *열거된* diff: `+dist/ads.txt`, 모든 HTML/PHP
    head 에 자동광고 스크립트 한 줄 삽입, `dist/assets/default-og.png`
    byte 교체. 그 외 자산·feed·sitemap·검색 인덱스 등 본문 무관
    산출물 byte-불변. 클린 빌드 2회 결정성 동일. `__version__`
    1.1.2→1.1.3 의 dist 누수 0 (B1 유지).

v1.0.2 변경 사항 (vs v1.0.1) — 홈 기본 출력 개수 디폴트 5→10 (정책 릴리스):
  - **메인페이지 Recent posts 코드 디폴트 5 → 10** — 사용자 결정.
    `Builder.HOME_PER_PAGE_DEFAULT` 상수를 `5` → `10` 으로 바꾸고
    README § 11 ("Articles/meta.yaml … 없으면 `per_page=10`") 와
    `Articles/README.md` 의 per_page 예시·디폴트 표기를 정합. 이
    상수는 `Articles/meta.yaml` 에 `per_page` 가 없을 때만 발효
    한다 — 정본 `Articles/meta.yaml` 은 `per_page: 10` 을 명시
    하므로 상수는 dormant 다.
  - **결정성·산출물** — 상수가 dormant 라 dist 영향이 **0**.
    `__version__` 1.0.1→1.0.2 의 dist 누수도 0 (v0.8.2 B1 유지).
    무결성 = 코드 릴리스 형이되 산출물 byte-불변형: 정본 Articles
    고정, v1.0.1 *코드* 클린 재빌드(불변 `siheonlee.com_v1.0.1`
    을 손대지 않는 4번째-숫자 검증 복사본 `siheonlee.com_
    v1.0.1.1`) vs v1.0.2 클린 재빌드의 dist 가 786=786, 0 added/
    0 removed/0 changed = **byte-완전 동일** (디폴트 변경이 어떤
    페이지도 바꾸지 않음 — Articles/meta.yaml 명시값 10 이 우선).
    `Articles/README.md` 표기도 10 으로 정합했으나 그 파일은 글
    폴더가 아니라 dist 로 새지 않음 (위 0-diff 로 실측 확인).
    클린 빌드 2회 결정성 동일, 단위 313 · 진단 6/6 승계.

v1.0.1 변경 사항 (vs v1.0.0) — 소분류 헤더 링크화 (기능 릴리스):
  - **소분류명 글씨 자체가 링크 + 우측 → 화살표 폐지** — 톱레벨
    카테고리 페이지(예: `/blog/`)의 자식 소분류 section 헤더가
    v1.0.0 까지는 `소분류명 <a class='more-link'>→</a>` (이름은
    plain text, 우측에 가는 화살표 링크) 였다. v1.0.1 은 화살표를
    없애고 소분류명 글씨 자체를 그 소분류의 자기 페이지
    (`/{top}/{sub}/`)로 가는 a 태그로 만든다 — 글씨를 클릭하면 그
    소분류 글만 보인다. `scripts/builder.py` 의 `_render_section`
    `more_url` 분기가 `<a class='subcat-link'>{이름}</a>` 를 내고,
    `src/assets/common_template.css` 의 `.more-link` 관련 3 룰을
    `.gap .subcat-link` 한 룰(`color: inherit; text-decoration:
    none;`, 호버 효과 없음)로 교체 — 링크지만 본문 글씨와 똑같이
    보이고(스타일 없이·깔끔하게), 클릭 가능 암시는 브라우저 기본
    포인터 커서뿐. `more_url` 이 없는 section(카테고리 자기 직속
    글)과 홈의 정적 "Recent posts" 갭은 무영향.
  - **결정성·산출물** — `__version__` 1.0.0→1.0.1 의 dist 누수는
    0 (v0.8.2 B1 유지). 무결성 = 코드 릴리스 형 (정본 Articles
    고정, v1.0.0 *코드* 클린 재빌드[불변 v1.0.0 손대지 않는
    4번째-숫자 검증 복사본 `siheonlee.com_v1.0.0.1`] vs v1.0.1
    클린 재빌드의 열거 diff). v1.0.0 대비 변경은 **5 파일** —
    `assets/common_template.css` + `blog`·`project`·`research`·
    `study`/`index.html` (자식 소분류를 둔 4 톱레벨 카테고리
    페이지), 0 added/0 removed, 781 byte-동일(786=786). 홈
    (`index.html`)·소분류 말단 페이지·`feed.rss`/`feed.atom`·
    `sitemap.xml`·`search.php`·글 페이지 전부 byte-불변. 클린
    빌드 2회 dist 완전 동일 (combined sha256 `bac1e2c6…`). 단위
    313 승계 · 진단 6/6. (부수 발견·이번 변경과 직교: 불변
    아카이브 `siheonlee.com_v1.0.0` 의 *shipped* `dist/index.html`
    이 v1.0.0 코드 클린 재빌드와 1파일 불일치 = v1.0.0 자체의
    사전 staleness. baseline 을 shipped dist 가 아니라 코드 클린
    재빌드로 잡아 순수 코드 델타를 격리했다 — v0.8.3 식 클린-vs-
    클린. v1.0.0 폴더는 불변이라 손대지 않았다.)

v1.0.0 변경 사항 (vs v0.8.4) — 첫 정식 릴리스 (기능 릴리스):
  - **기본 og:image 자산 패스스루** — `_copy_site_assets` 가
    `site.default_og_image` 가 가리키는 자산만 webp 변환·variant 등록을
    건너뛰고 원본을 그대로 `dist/assets/` 에 복사. og:image 소비자는
    `<img srcset>` 후처리가 아니라 SNS 링크 언퍼ler — 고정 URL 하나만
    가져가 다중 해상도가 무의미하고, KakaoTalk·일부 Facebook 은 WebP
    og:image 를 못 렌더한다. `seo.resolve_og_image` 도 이 값을 문자열
    그대로 쓰므로(webp 재매핑 없음) 변환하면 그 URL 이 dist 에서 404.
    실제 `src/assets/default-og.png`(1200×480) 동반 — v0.8.4 까지는
    site.yaml 이 `/assets/default-og.png` 를 가리키되 그 파일이 없어
    본문 이미지가 없는 모든 글·홈·카테고리의 og:image 가 죽은 404
    였다 (이번에 해소). `default_og_image` 가 외부 URL 이거나 assets/
    밖이면 매칭 자산이 없어 이 예외는 무동작.
  - **`About` 글 검색 비허용** — `Articles/About/meta.yaml` 에
    `noindex: true`. 그 페이지 `<head>` 에 `<meta name='robots'
    content='noindex'>` + `sitemap.xml`·`search.php` 인덱스에서
    제외 (v0.4.0 색인 정책·v0.6.0 검색 제외와 일관). 피드는 최신
    20개(`DEFAULT_MAX_ENTRIES`) 윈도우라 date 2025-01-01 인 About
    은 v0.8.4 에서도 이미 미수록 — noindex 가 피드엔 no-op
    (`feed.rss`/`feed.atom` byte-불변).
  - **결정성·산출물** — `__version__` 0.8.4→1.0.0 의 dist 누수는 0
    (v0.8.2 B1 유지). v0.8.4 dist 대비 실측 diff (786 vs 785) =
    `+assets/default-og.png`, Δ `about/index.html`(robots 한 줄)·
    `sitemap.xml`·`search.php`; `feed.rss`/`feed.atom` 포함 그 외
    산출물 전부 byte-불변, 클린 빌드 2회 결정성 동일 (combined
    sha256 `bf4293c7…`). 무결성 = "결정성 + v0.8.4 기준 위 실측
    열거 diff" (코드 릴리스 형). 단위 313 · 진단 6/6 승계.

v0.8.3 변경 사항 (vs v0.8.2) — schema.org JSON-LD + 정확 빵부스러기 (코드 릴리스):
  - 글 페이지 `<head>` 에 `<script type="application/ld+json">` 한 줄을
    추가 — `@graph` 로 Article + (crumb 2개↑이면) BreadcrumbList. 기존
    OG/Twitter/canonical/robots `<meta>` 를 *대체하지 않고 보강* 한다
    (소비자가 다름: SNS=OG, SERP=description, 색인=robots, 리치결과=JSON-LD).
  - off 스위치 (v0.5.5 원칙): `site.yaml`→`jsonld.enabled` (기본 true,
    사이트 전역) + `meta.yaml`→`seo.jsonld: false` (글 단위 opt-out).
    사이트 토글이 마스터. 비출력 시 `{{JSONLD}}` 라인은 ROBOTS_META 와
    같은 방식으로 라인-이팅 (빈 줄 없음).
  - 빵부스러기 의미 정확: nav-tracker HTML 과 JSON-LD `BreadcrumbList`
    가 단일 공유 소스(`Builder._crumb_parts_for`)를 먹는다. 중간 조상
    = 각자 자기 중첩 카테고리 URL (`/{top}/…/{cat}/`), 글 말단 = 글
    제목 (= `Article.headline`). 카테고리 페이지 말단은 폴더명 유지
    (글 제목 개념 없음). 명시 `slug:`·`meta.yaml` 스키마 불변 — 폴더
    명은 출력에 무관한 자유형 그대로 (마이그레이션 아님).
  - 게이트: `src/tests/run_diagnostics.py` 에 JSON-LD 의미 정확성
    검증 [6] — BreadcrumbList position 단조, 비말단 item distinct,
    비말단 item 의 dist 실재, 말단 item 생략·name==headline. additive·
    결정성-only 게이트가 놓치는 의미 결함 부류를 잡는다.
  - 코드 릴리스라 dist 가 바뀐다. 무결성 = "결정성 2회 동일 + v0.8.2
    대비 *열거된* diff" — 글 렌더 페이지에 한정 (ld+json 추가 + 빵부스
    러기 정확 라벨·링크), 그 외 (피드/사이트맵/검색/홈/카테고리/assets)
    byte 불변. `__version__` 자체의 dist 누수는 여전히 0 (v0.8.2 B1
    유지) — dist 변경은 기능·정확성 때문.

v0.8.2 변경 사항 (vs v0.8.1) — 코드 건전성 (버전 디커플링 / CLI / 리포트):
  - **(1) `__version__` 디커플링 (B1)** — v0.8.1 까지 `__version__` 이
    dist 로 새는 경로는 feed.atom/feed.rss 의 `<generator>` 한 줄뿐이었다.
    그 때문에 문서·구조 전용 릴리스 (v0.7.2→v0.8.0→v0.8.1) 는 byte-동일
    검증을 위해 `__version__` 을 '0.7.2' 에 동결해야 했다. v0.8.2 는
    generator 문자열에서 버전 토큰을 제거 (`siheonlee.com v0.7.2 — …`
    → `siheonlee.com — …`) — `__version__` 의 dist 영향이 영구히 0 이
    되고, 드디어 릴리스를 자유롭게 추종한다 (`'0.7.2'` → `'0.8.2'`).
    이후 문서 릴리스는 진짜 byte-동일 (동결 불필요·무비용).
  - **(2) CLI argparse 견고화** — v0.8.1 까지 raw `'--clean' in sys.argv`
    라 오타 (`--clena`) 가 경고 없이 일반 빌드로 흘러가는 silent footgun
    이었다. argparse (allow_abbrev=False) 로 전환 — `--help` 제공 +
    미지/오타/약어 인자 즉시 거부 (SystemExit 2 + usage). run_diagnostics
    .py 와 같은 idiom 으로 통일. 유효 인자의 빌드 동작은 v0.8.1 과 1:1.
  - **(3) 빌드 리포트 per-Builder** — scripts/report.py docstring 이
    v0.5.5 부터 명세해 온 "Builder 가 self.report 보유, self._issue /
    self._warning 라우팅" 을 실제로 구현. v0.6.5~v0.8.1 은 모듈 전역
    `_report` + build() 진입 시 reset 이라 동시 빌드(멀티스레드/프로세스)
    가 원천 봉쇄돼 있었다. 부수적으로 `build()` 멱등성 결함 1건 수정 —
    옛 코드는 self.report/_console 만 리셋하고 데이터 컬렉션
    (articles/slug_to_article/categories/...) 은 __init__ 에서만 초기화
    돼, 같은 인스턴스로 두 번째 build() 시 'slug 중복' 을 잘못 보고했다
    (옛 테스트가 매번 새 인스턴스를 써서 가려짐).
  - **결정성·산출물** — (2)(3) 은 dist 0. (1) 은 feed.atom/feed.rss 의
    `<generator>` 한 줄만 v0.8.0 과 차이 (의도된 1회성, 그 외 783 파일
    byte-동일 · 0 missing/extra · 결정성 2회 빌드 동일). 단위 테스트
    258 → **266** (test_build_cli.py 7 + per-Builder 격리/멱등 2). 진단
    5/5 PASS. 이번 릴리스 무결성 = "결정성 + v0.8.0 기준 열거된 2파일
    1줄 diff" (v0.5.1 식 프레이밍 — 문서 전용 sha256 동치가 아님).

v0.8.1 변경 사항 (vs v0.8.0) — 폴더 구조 정리 (코드 동작·산출물 불변):
  - **최상위 6 항목으로 축약** — 시스템에 들어갔을 때 보이는 것을
    `Articles/` · `dist/` · `src/` · `build.py` · `README.md` ·
    `site.yaml` 만으로 정리. 빌더 일체 (`scripts/` Python 패키지,
    `templates/`, `assets/`, `tests/`) 를 `src/` 한 폴더 아래로 이동.
  - **src/ 내부 계층** — `src/scripts/` (빌드 파이프라인 모듈),
    `src/templates/` (HTML/PHP 템플릿), `src/assets/` (사이트 공통
    CSS/JS), `src/tests/` (단위 테스트 + run_diagnostics). 각 역할이
    한 폴더로 분리돼 평면적이던 최상위가 2 단 계층으로 구조화.
  - **경로 해석 일원화** — `build.py` 가 자기 폴더의 `src/` 를 sys.path
    맨 앞에 올려 `import scripts...` 가 `src/scripts/` 를 가리킨다.
    `Builder` 는 `self.src_dir = base/src` 를 두고 templates/assets,
    캐시 global_hash 의 scripts_dir 을 그 아래에서 해석. `Articles/`
    `dist/` `site.yaml` `.build_cache/` `build-report.md` 는 그대로
    프로젝트 루트(= build.py 폴더) 기준 — 글 소스·산출물 위치 불변.
  - **결정성·산출물 불변** — 이동은 *파일 위치* 만 바꾸고 빌드 로직은
    한 줄도 바꾸지 않았다. `__version__` 도 `'0.7.2'` 그대로 (별도
    범위). dist/ 산출물은 v0.8.0 과 **byte 동일** — 정본 Articles 클린
    재빌드로 sha256 전수 검증. 단위 테스트 258 그대로 (테스트 하네스의
    템플릿/자산 복사 대상 경로만 `tmp/src/...` 로 따라 이동), 진단
    5/5 PASS.

v0.7.2 변경 사항 (vs v0.7.1) — 빌드 진행 표시 + 빌드 리포트 문서화:
  - **16 단계 진행 헤더** — `build()` 가 각 파이프라인 단계 직전에
    `[ n/16] <설명>` 을 출력. 큰 사이트에서 빌드가 오래 걸려도 "지금 무엇이
    진행 중인지" 가 보인다 (v0.7.1 까지는 시작/완료 두 줄뿐이라 사진이
    많은 글을 빌드하면 멈춘 듯 보였다).
  - **무거운 루프의 라이브 카운터** — 자산 동기화 (이미지 WebP 변환) /
    글 렌더 단계가 글·이미지마다 같은 줄을 `\r` 로 in-place 갱신
    (`Builder._live`). 터미널(TTY) 전용 — stdout 이 redirect 된 환경
    (run_diagnostics / 단위 테스트) 에서는 no-op 이라 캡처 로그가 깔끔하고
    결정성·테스트에 영향이 없다. 단계 요약은 항상 한 줄 남는다.
  - **build-report.md 자동 생성** — 빌드 완료 시 `build.py` 가 있는 폴더
    (`Builder.base`) 에 마크다운 리포트를 쓴다. 메타 (버전/시각/소요/글·
    카테고리 수/캐시) + "빌드 진행" 트랜스크립트 (코드 블록) + "보완이
    필요한 항목" / "살펴볼 사항" 절. 그동안 터미널에만 뜨던
    `BuildReport` 출력을 파일로도 남겨, 빌드 후 무엇을 보완해야 하는지
    문서로 확인 가능. 새 `BuildReport.render_markdown()` 가 `render()`
    와 1:1 구조로 마크다운 직렬화. 파일 쓰기 실패는 콘텐츠 결함이
    아니므로 abort 하지 않고 stderr 경고 후 빌드 정상 종료.
  - **결정성 불변** — 진행 출력·리포트 문서는 dist/ 밖이라 한 글자도
    산출물에 새지 않는다. dist 산출물은 v0.7.1 과 *바이트 동일*
    (`feed.atom` / `feed.rss` 의 generator 문자열만 v0.7.1 → v0.7.2 자동
    갱신 — `__version__` 단일 source 효과). 단위 테스트 258 그대로,
    진단 5/5 PASS.

v0.7.1 변경 사항 (vs v0.7.0) — 안정화 패치 (정합성 회복, 코드 동작 변경 0):
  - v0.7.0 에서 lama.pe.kr 마이그레이션 인프라 일괄 제거 직후 누적된 문서·주석
    drift 정리. dist 산출물은 v0.7.0 과 *바이트 동일* (`__version__` 단일 source
    효과로 feed.atom / feed.rss 의 generator 문자열만 v0.7.0 → v0.7.1 자동
    갱신).
  - **빌더 docstring 의 파이프라인 헤더 정정** — scripts/builder.py 의 "15단계
    파이프라인" 헤더가 v0.6.4 에서 추가된 `_sync_page_css` 단계 ([6b]) 를
    빠뜨리고 있던 부분 갱신. 실 파이프라인 (`build()` 의 16개 self._… 호출) 과
    docstring 의 단계 표가 일치.
  - **README §2 빌드 단계 표 재작성** — v0.5.1 의 asset/render 순서 역전,
    v0.5.3 의 `_build_feeds` ([12b]), v0.6.4 의 `_sync_page_css` ([6b]) 가
    누락돼 있던 표를 실 파이프라인 그대로 재기술.
  - **본문 폴백 잔존 안내 정리** — README §5 (gallery 썸네일 결정 규칙) /
    §13b (feed entry table 의 `<summary>` 폴백) 가 v0.5.5 폐기된 "본문 첫
    이미지 / 본문 첫 단락" 폴백을 여전히 안내하던 부분 정정. 모든 외부 노출
    메타데이터는 `meta.yaml` 의 명시값만 사용한다는 본문 ↔ 메타데이터 분리
    원칙 (설계 원칙 10) 과 일관.
  - **stale § cross-ref 정정** — 마이그레이션 절 (구 §14) 제거에 따른 §
    번호 시프트가 코드 docstring 에 따라잡지 못한 부분 정정: build.py 의
    `§ 18 (업데이트 로그)` → `§ 17`, scripts/builder.py 의 `§ 17 참조` →
    `§ 16 의 설계 원칙 10`, scripts/builder.py 와 scripts/models.py 의 옛
    `§ 5-1 참조` (한 시점에 본문 ↔ 메타데이터 분리 원칙이 있었던 절) →
    현재의 `§ 16 의 설계 원칙 10`.
  - **README 헤더/푸터/폴더 트리의 버전 표기** v0.7.0 → v0.7.1. v0.7.0 의
    각 기능 도입 시점을 가리키는 changelog 본문의 v0.7.0 표기는 *역사 기록* 이라
    그대로 유지.
  - 검증: 단위 테스트 258 (v0.7.0 과 동일), 진단 5/5 PASS.

v0.7.0 변경 사항 (vs v0.6.5) — 빌드 증분 캐싱 도입:
  - **글 단위 증분 캐시** (`scripts/cache.py` 신설) — 매 빌드마다 모든 글을
    재렌더하던 동작이, 변경되지 않은 글은 캐시된 HTML/PHP 를 그대로 dist 에
    복원하는 방식으로 전환. 캐시 저장소는 `.build_cache/` (manifest.json +
    articles/{slug}.{ext}). 캐시는 마크다운 파싱 (Parsedown 포팅) + 템플릿
    렌더 + <img> 후처리 등 빌드 시간의 대부분을 차지하는 단계를 통째로
    건너뛴다.
  - **캐시 대상 범위 (사용자 결정)**: 글 페이지 (`_render_articles` 단계)
    만. 검색 인덱스 / sitemap / feed / 홈 / 카테고리 / assets 는 모든 글이
    입력이라 invalidate 빈도가 높고 계산 비용이 낮아 캐싱 효과가 적으므로
    제외.
  - **캐시 키 입도 (사용자 결정)**: 글별 fine-grained. `article_hash` 는
    (a) 모든 글에 영향을 주는 `global_hash` (site.yaml + scripts/ +
    templates/ + assets/common_template.css + Articles/*/meta.yaml +
    __version__) 와 (b) 그 글 고유의 입력 (content 파일 + 글 폴더의 모든
    자산/CSS) 두 부분으로 구성. 한 글의 content 만 바뀌면 그 글만
    invalidate, site.yaml / 템플릿 / 빌더 코드가 바뀌면 모든 글 invalidate
    (정확한 의존성 추적).
  - **CLI 플래그 3 개 신설**:
      `--no-cache`     : 캐시 lookup/store 비활성. v0.6.5 와 동등 동작.
      `--clean-cache`  : `.build_cache/` 만 폐기 후 빌드 (dist 는 유지).
      `--clean` (확장) : dist/ 폐기에 더해 `.build_cache/` 도 함께 폐기 —
                         '완전 재빌드' 의도.
  - **부수 캐싱**: 글 페이지 HTML 외에도 (a) 검색 인덱스용 plain text body,
    (b) gallery/feed 용 thumb/summary, (c) 그 글의 BuildReport issue /
    warning 항목들도 함께 캐시. 캐시 hit 시 이들이 replay 되어 빌드 리포트
    가 매 빌드 byte-identical 로 유지.
  - **결정성 보장**: 캐시는 *재렌더 여부* 만 바꾸고 *산출물 자체* 는 바꾸지
    않는다. `tests/run_diagnostics.py` 의 [2] 결정성 섹션 (sha256 2 회 빌드
    비교) 이 캐시 hit 경로에서도 통과 — 두 번째 빌드의 dist 가 첫 빌드와
    byte 동일.
  - 단위 테스트: 231 → **258** (`tests/test_cache.py` 신설 27 케이스 — 캐시
    키 결정성/민감도, lookup/store round-trip, --no-cache 동작, selective
    invalidation, 통합 빌드 시나리오).
  - **결정성 + 산출물 byte 동일**: 글 6 개 / 카테고리 2 개 / search.php /
    sitemap / robots / 404 / 홈 등 *모든* dist 산출물이 v0.6.5 와 byte
    단위로 동일하다 (feed.atom / feed.rss 의 generator 문자열만
    `v0.6.5` → `v0.7.0` 자동 갱신 — `__version__` 단일 source effect).
  - 적용 메모: 옛 글/카테고리/홈 `meta.yaml` 변경 의무 없음. `.build_cache/`
    는 자동 생성 + 자동 정리. CI / 프로덕션 빌드에서 캐시를 끄려면
    `--no-cache` (또는 `.build_cache/` 를 매번 폐기). `.build_cache/` 는
    버전 관리 대상이 아님 — `.gitignore` 권장.

v0.6.5 변경 사항 (vs v0.6.4) — 안정화 패치 (v0.6.0 ~ v0.6.4 누적 회귀 4 건):
  - **(#1) Builder.build() 가 자동으로 _report 를 reset** — v0.6.4 까지는 한
    프로세스에서 build() 를 여러 번 호출하면 issue/warning 이 누적됐다.
    tests/run_diagnostics.py 의 [2] 결정성 섹션이 build() 를 두 번 돌리면서
    이 버그를 드러냈는데 (출력에 '보완 필요 9건' 처럼 부풀려진 카운트), 산출
    물 자체는 정상이라 묻혀 있었다. v0.6.5 부터 build() 진입 시 reset_report()
    가 자동 호출 — 호출자는 더 이상 명시적 초기화를 신경 쓸 필요 없다.
  - **(#2) _render_template 가 BODY 안의 `{{XXX}}` 패턴을 보존** — v0.6.4 의
    placeholder strip 이 BODY substitute 이후에 돌아서, 사용자 본문에 들어
    있던 대문자 placeholder 패턴 (예: 템플릿 엔진 튜토리얼의
    `{{COPYRIGHT_YEAR}}` 코드 블록) 이 silent 으로 제거되는 회귀가 있었다.
    v0.6.5 는 3-pass 로 분리:
      Pass 1 — frame vars (LANG, META_TAGS, NAV_LINKS, ...) substitute.
      Pass 2 — leftover 검출 + strip + warn (BODY 등 content_vars 는 제외).
      Pass 3 — content_vars (BODY / SUBCATEGORY_SECTIONS / ARTICLE_LIST)
               substitute — 사용자 본문 안의 `{{XXX}}` 가 보존된다.
    호출자가 `content_vars=` 인자로 어느 vars 가 사용자 콘텐츠인지 명시.
  - **(#3) og_type 디폴트 강제 제거** — v0.6.2 의 설계는 SeoMeta.og_type=None
    일 때 build_meta_tags 가 page_kind 로 결정 (글=article, 홈/카테고리=
    website) 이었으나, _parse_frontmatter 가 'or "article"', _parse_category_
    meta_file 이 'or "website"' 로 디폴트를 강제해 page_kind 분기가 dead
    code 가 됐다. v0.6.5 는 두 파서가 raw 값을 그대로 보존 — page_kind 분기가
    되살아남. 산출물 동일 (현재 케이스에서는 두 디폴트가 같은 결과).
  - 단위 테스트: 227 → **231** (test_builder.py 의
    BodyPlaceholderPreservationTests 3 개 + BuildReportResetTests 1 개 추가).
  - 회귀 가드: v0.6.4 와 dist 차이 2 파일 — `feed.atom` / `feed.rss` =
    generator v0.6.4 → v0.6.5 자동 갱신 (__version__ 단일 source 효과).
    글 6 개 / 카테고리 2 개 / search.php / sitemap / robots / 404 / 홈
    index.html 등 *모든 다른 산출물 byte 동일*.

v0.6.4 변경 사항 (vs v0.6.3) — 홈/카테고리 CSS 일원화 + template: 키:
  - v0.6.3 의 비대칭 (글만 외부 CSS / use_common_css 지원, 홈/카테고리는 영구
    미지원) 해소. CategoryMeta 가 글의 ArticleMeta 와 같은 stylesheets +
    use_common_css 필드를 가져 *세 페이지 종류 모두* 동일한 styles 두 채널
    (정수 키 = 외부 CSS 파일 상대 경로, 문자열 키 = 인라인 룰) + 공통 CSS
    토글을 지원한다.
  - 외부 CSS URL 은 페이지 종류 별 접두 + 상대 경로:
      글       : /<slug>/<rel>
      카테고리 : /<cat_slug_path>/<rel>
      홈       : /<rel> (사이트 루트)
    파일 위치는 항상 meta.yaml 의 부모 폴더 (= 글 폴더 / 카테고리 폴더 /
    Articles/). `render_stylesheet_links(sheets, url_prefix)` 시그니처
    일반화로 한 함수가 세 페이지 종류 모두 처리.
  - 새 빌드 단계 [6b] `_sync_page_css` — 카테고리/홈의 선언된 CSS 파일을
    dist 에 명시 복사 (글은 기존 [5] `_sync_assets` 가 폴더 통째로 복사).
  - 공용 검증 헬퍼 `_validate_stylesheets` — 글/카테고리/홈이 같은 규칙으로
    절대 경로/'..'/빈 경로 거부 + 파일 존재 확인.
  - **새 `template:` 키** — meta.yaml 이 자기 페이지에 사용할 템플릿 파일을
    명시 (`'name.html'` → templates/ 에서, `'./name.html'` → meta.yaml 의
    부모 폴더에서). 글/카테고리/홈 모두 같은 형식. 검증 실패 / 파일 없음 →
    BuildReport issue + 페이지 종류 기본 템플릿 (article.html /
    category.html / home.html) 으로 폴백.
  - `_render_template` 후처리: 치환 후 남은 `{{XXX}}` placeholder 를 빈
    문자열로 strip + warn_context 가 주어진 호출에서는 각 미치환 이름마다
    BuildReport warning. author 가 페이지 종류를 가로지르는 템플릿을
    골랐을 때 발생하는 silent leak 가드.
  - 템플릿 placeholder 이름 통일: `{{COMMON_CSS}}` / `{{PAGE_STYLESHEETS}}` /
    `{{PAGE_STYLES}}` 가 세 템플릿 모두에서 같은 이름. v0.6.3 의
    `{{ARTICLE_STYLESHEETS}}` / `{{ARTICLE_STYLES}}` / `{{CATEGORY_STYLES}}` 는
    일제히 변경 — dist 산출물은 placeholder 가 렌더 후 사라지므로 byte 영향
    없음 (단 `home/index.html` 은 신설 `{{PAGE_STYLES}}` 라인 1줄 추가).
  - 단위 테스트: 210 → **227** (test_markdown.py 의 url_prefix 케이스 4 개 +
    test_builder.py 의 카테고리/홈 styles + template 키 케이스 13 개).
  - 회귀 가드: v0.6.3 의 글 6 개 / 카테고리 2 개 / search.php / sitemap /
    robots / 404 등 모두 v0.6.4 와 *바이트 동일*. dist 차이는 3 파일 — (a)
    `feed.atom` / `feed.rss` = generator v0.6.3 → v0.6.4 자동, (b)
    `index.html` (홈) = 신설 `{{PAGE_STYLES}}` placeholder 의 빈 치환 결과로
    trailing whitespace 라인 1 줄 추가.

v0.6.3 변경 사항 (vs v0.6.2) — 글 단위 외부 CSS 파일 + use_common_css 토글:
  - meta.yaml 의 `styles:` 키가 두 채널을 동시에 가질 수 있게 확장 — 정수
    키 (1, 2, 3, ...) 는 글 폴더 안의 외부 CSS 파일 상대 경로, 문자열 키
    (tag/selector) 는 기존 인라인 룰 (v0.5.x 동작 그대로). 두 종류가 한 키
    아래 자유롭게 섞임. 정수 키들의 오름차순이 head 의 `<link>` 출력 순서.
    글 폴더의 css 파일은 v0.5.2 자산 경로 일원화에 따라 `dist/{slug}/<rel>`
    로 자동 복사되고, head 의 `<link href='/{slug}/<rel>'>` 가 가리킨다.
    "글 = 폴더" 원칙에 따라 글이 자기 디자인을 가질 때 그 디자인 파일을
    글 폴더 안에 두는 것이 가장 자연스럽다는 의도.
  - **로드 순서**: common_template.css → 외부 CSS (정수 키 순) → 인라인
    `<style>` (문자열 키). 인라인이 마지막 발언권 — 인라인 채널이 "자주
    사용되는 일부 속성의 미세 override" 의도라는 README §11 정의와 부합.
  - **CSS 파일 누락 정책**: meta.yaml 에 명시한 파일이 글 폴더에 없으면
    BuildReport 의 issue 로 기록 + 해당 link 만 출력에서 제외. 빌드는 통과.
    v0.5.5 의 "description 누락 = issue + 메타 태그 미출력" 정책과 일관.
    상위 디렉터리 이탈 (`..`) 과 절대 경로도 동일하게 issue + 출력 제외.
  - **`use_common_css` 토글** (ArticleMeta 의 새 bool 필드, 기본 True). False
    면 `<link href='/assets/common_template.css'>` 태그가 head 에서 *통째로*
    출력되지 않음. 글에서 완전히 새로운 서비스/랜딩페이지를 제공할 때 사이트
    공통 톤 (header / nav / footer / pagination / gallery 기본 디자인) 을
    의도적으로 끊는 옵션. 기본 True 라 모든 옛 글이 변경 의무 없음.
  - **카테고리/홈은 외부 CSS 미지원** — 카테고리/홈은 사이트 공통 톤에서
    벗어날 가능성이 매우 희박하다는 정책 (영구적). Articles/meta.yaml /
    Articles/<카테고리>/meta.yaml 의 styles 에 정수 키가 들어오면 issue 로
    알려주고 인라인 룰만 적용. use_common_css 토글도 카테고리/홈에는 없음.
  - 템플릿: `templates/article.html` 의 `<head>` 에 `{{COMMON_CSS}}` +
    `{{ARTICLE_STYLESHEETS}}` 두 placeholder 추가. 비활성/0개 케이스에서는
    `{{ROBOTS_META}}` 와 같은 line-eating 패턴으로 빈 줄 잔존 방지.
  - 데이터 모델: ArticleMeta 에 `stylesheets` (list[str]) + `use_common_css`
    (bool=True) 필드 신설. `styles` 필드의 의미가 좁아져 *문자열 키만* 담음
    (= 인라인 룰). normalize_styles 가 (sheets, rules) 튜플로 반환.
  - 함수 분리: 옛 `render_article_styles` 를 `render_inline_styles` (인라인
    `<style>` 블록 렌더) 로 이름 변경 + 새 `render_stylesheet_links` (외부
    CSS link 태그 렌더) 신설. 카테고리 측 `_category_styles_html` 도
    `render_inline_styles` 로 전환.
  - 단위 테스트: 188 → **210** (test_markdown.py 의 styles 분리/렌더 케이스
    11개 + test_builder.py 의 통합 빌드 시나리오 9개).
  - 회귀 가드: 외부 CSS 를 안 쓰는 모든 옛 글의 dist 산출물은 v0.6.2 와
    **바이트 동일**. 데모로 `Articles/Blog/Hello World/style.css` 와 같은
    글의 meta.yaml 에 `styles.1: style.css` 한 줄을 추가한 결과만 두 파일
    차이 (`dist/hello-world/index.html` 의 link 한 줄 추가 +
    `dist/hello-world/style.css` 신규 복사).

v0.6.2 변경 사항 (vs v0.6.1) — 홈/카테고리 페이지 SEO 메타 태그 출력:
  - v0.5.4 의 한계 표 "홈/카테고리 페이지의 SEO 메타 태그 출력 (description /
    og_* / twitter_*)" 항목 해소. 글에만 출력되던 description / og_title /
    og_description / og_image / og:image:alt / og:type / og:url / og:site_name /
    twitter:card / twitter:title / twitter:description / twitter:image / link
    canonical 메타 태그가 홈 / 톱레벨 카테고리 / 서브카테고리 페이지에도
    동일한 폴백 규칙으로 출력된다.
  - **`build_meta_tags()` 시그니처 일반화** — 글 전용 `article` 객체 대신
    `title`, `seo`, `site`, `canonical_path`, `page_kind`, `published`,
    `updated` 키워드 인자. 글/홈/카테고리 세 호출자 모두 같은 함수를 사용.
    `og:type` 디폴트는 page_kind 에 따라 자동 결정 (글=article, 홈/카테고리
    =website — OGP 표준 권장). `article:published_time` / `modified_time` 은
    published 인자가 전달됐을 때만 (= 글일 때만) 출력.
  - **`SeoMeta.og_type` 디폴트 변경** — `'article'` → `None`. 글/홈/카테고리가
    같은 SeoMeta 모델을 쓰기 때문에 디폴트는 페이지 종류 별로 달라야
    자연스럽다. author 가 meta.yaml 의 `seo.og_type` 으로 명시 override 하면
    그 값이 우선. 글 페이지의 dist 산출물은 변경 0 (None → page_kind='article'
    → 'article').
  - **description 필수화 정책의 홈/카테고리 확장** — v0.5.5 의 본문 ↔
    메타데이터 분리 원칙에 따라 글에만 적용되던 `seo.description` 누락/빈
    문자열 issue 가 홈/카테고리에도 동일 적용. `Articles/meta.yaml` /
    `Articles/<카테고리>/meta.yaml` 에 description 이 없거나 빈 문자열이면
    BuildReport 의 issue 에 기록 (빌드는 통과).
  - **색인 정책 유지** — 홈 / 톱레벨 카테고리 / 서브카테고리 모두 *색인
    허용* 그대로. robots meta 는 글 단위 noindex 와 search.php 외에는 출력
    되지 않으며, sitemap.xml 도 홈/카테고리 URL 을 포함하는 v0.4.4 ~ v0.6.1
    정책 그대로.
  - 템플릿: `templates/home.html` + `templates/category.html` 의 `<head>` 에
    `{{META_TAGS}}` placeholder 추가 (article.html 과 같은 위치).
  - 빌더: `_render_articles` / `_build_home` / `_build_category_page` 세 곳이
    같은 `build_meta_tags` 호출 패턴으로 정돈. 새 헬퍼 `_check_page_description`
    이 description 누락 검사를 페이지 종류 별로 일반화.
  - 단위 테스트: 179 → 187 (test_seo.py 의 홈/카테고리 메타 태그 케이스 +
    og:type 페이지 종류별 디폴트 + test_builder.py 의 메타 태그 출력 확인).
  - 글 페이지 dist 산출물은 v0.6.1 과 *바이트 동일* (회귀 가드). 새 메타
    태그가 추가되는 곳은 홈 / 톱레벨 카테고리 / 서브카테고리 인덱스 페이지뿐.

v0.6.1 변경 사항 (vs v0.6.0) — 문서·주석·산출물 가독성 안정화 3회차:
  - 콘텐츠 측 meta.yaml 의 폐기된 동작 안내 정리. Articles/Blog/Hello
    World/meta.yaml 의 "본문에서의 자동 폴백 (first_paragraph, first_image
    등)" 안내가 v0.5.5 의 본문 ↔ 메타데이터 분리 원칙으로 사라진 동작을
    여전히 가르치고 있던 부분 + 같은 글의 tags 주석 "현재 빌드 산출물에는
    직접 노출되지 않지만" 이 v0.5.3 의 feed `<category>` / v0.6.0 의 BM25
    색인 합류로 거짓이 된 부분 동시 갱신.
  - 카테고리 meta.yaml 의 layout 거짓말 잔존분 (`Articles/Blog/meta.yaml`)
    을 v0.5.3 의 gallery 구현 사실로 정정. 2회차 패치에서 Articles/meta.yaml
    과 scripts/models.py 의 같은 거짓말은 잡았으나 형제 카테고리 meta.yaml
    한 곳을 빠뜨린 누락분.
  - scripts/models.py 의 ArticleMeta.tags 관련 두 군데 (v0.5.3 변경 절 +
    필드 옆 인라인 주석) 가 "tags 는 현재 미사용" 으로 굳어 있던 부분 정리.
  - 템플릿 source 의 v0.6.0 미반영 주석 잔존분: templates/search_tokenize
    .php 의 "search.php 가 require_once 하고" 안내가 v0.6.0 의 인라인 흐름
    에 맞춰 갱신.
  - dist/search.php 헤더 주석의 placeholder 누수 결함 해소. 빌더의
    `_render_template` 가 주석 안의 placeholder 도 동등하게 치환해버려 dist
    헤더가 자기 자신의 결과를 인용하던 메타-광경을 정리. 템플릿 측에서
    안내 줄에 실제 placeholder 토큰을 쓰지 않고 plain 이름으로 표기.
  - README.md §12 의 마크다운 파이프라인 도식이 v0.5.5 폐기된 `first_paragraph`
    / `first_image` 를 여전히 그리고 있던 부분 + §13 의 토크나이저 "PHP 가
    require_once 하고 dist/search_tokenize.php 로 복사" 가 v0.6.0 의 인라인
    흐름에 어긋나던 부분 + 파일 트리에서 search_tokenize.php 의 인라인 사실
    누락 동시 정정. §18 history 의 v0.x.x 검증 노트는 역사 기록으로 보존.
  - **코드 동작 변경 0**. site.yaml / Articles/ 스키마 / 글 산출물 / 검색
    결과 모두 v0.6.0 과 바이트 단위로 동등 (search.php 의 헤더 주석 텍스트만
    가독성 정정으로 달라짐).

v0.6.0 변경 사항 (vs v0.5.5):
  - **검색 인덱스를 메타데이터 3-필드 (title / description / tags) 만 색인**.
    v0.5.x 까지 본문도 색인하던 정책 폐기. tags 가 새 가중치 필드로 합류
    (`w_title=3.0`, `w_description=1.0`, `w_tags=2.5`). 본문 평문은 스니펫
    추출 목적으로 글마다 앞 1500 자만 인덱스에 보존. 작성자가 의도적으로
    메타데이터에 적은 단어만 검색의 대상이 됨 → 검색 결과의 신호/잡음비 향상.
  - **search-index.json 폐기 + `dist/search.php` 한 파일 인라인**. 인덱스가
    PHP 정적 배열 리터럴로 search.php 안에 직접 박힘 (`/* INLINE: SEARCH_INDEX */`
    sentinel 치환). 토크나이저 + BM25 함수도 같은 파일에 인라인되어 dist
    검색 산출물이 search.php 하나로 축약. require_once / 디스크 IO / JSON
    파싱 전부 0 — OPcache 가 바이트코드와 함께 인덱스를 메모리에 캐시.
  - **결정적 직렬화**: scripts/search.py 의 `php_array_literal()` 가 dict
    키를 정렬해 출력 → 두 번 빌드해도 dist/search.php 의 sha256 동일. 빌드
    당 build_time 같은 비결정 값을 산출물에 절대 새지 않는 원칙 유지.
  - **단위 테스트 본격 확장**: 25 → **179**. `test_bm25.py` 31개 (BM25 v4
    + 신규 가드 6개) + `test_builder.py` / `test_markdown.py` / `test_seo.py`
    / `test_sitemap.py` / `test_feed.py` / `test_yaml_parser.py` /
    `test_slugs.py` / `test_report.py` / `test_parsedown.py` /
    `test_php_literal.py`.
  - **`tests/run_diagnostics.py` 신설** — 단위 테스트 + 빌드 결정성 (sha256
    동등성) + PHP 구문 (php -l) + Python↔PHP BM25 점수 패리티 + 인덱스
    형식을 한 번에 검사하고 리포트 파일 생성. Windows cp949 콘솔에서도
    동작하도록 stdout/stderr 를 UTF-8 로 재구성.
  - **`scripts/__init__.py` 의 `__version__`** 신설 — 사이트 버전 문자열의
    단일 source of truth. feed generator 등 버전을 표기하는 산출물이 이
    값을 참조 (v0.5.x 의 하드코딩된 'v0.5.4' 문자열 제거).
  - 콘텐츠 측 출력 (글 페이지, 홈, 카테고리, sitemap.xml, robots.txt,
    feed.atom, feed.rss) 의 형식은 v0.5.5 와 동등. 변경은 검색 시스템과
    단위 테스트·진단 인프라에 한정.

v0.5.5 변경 사항 (vs v0.5.4):
  - **본문 ↔ 메타데이터 분리 원칙 도입** (README § 5-1). SEO description /
    og_image / 갤러리 썸네일 / 피드 summary 가 더 이상 본문 첫 `<p>` / 첫
    `<img>` 를 폴백 소스로 쓰지 않는다. 모든 외부 노출 메타데이터는 author
    가 `meta.yaml` 의 `seo:` 블록에 명시한 값만 사용. v0.4.2 로드맵 B-5
    (description 폴백 범위) 가 *폴백 자체를 제거* 하는 방향으로 해소.
  - `seo.description` 이 필수 필드로 격상. 부재 / 빈 문자열 시 빌드는
    완성되지만 미완성 글 리포트에 기록되어 작성자가 보완 — description /
    og:description / twitter:description / 피드 summary / 갤러리 description
    이 누락된 채 산출물이 만들어진다.
  - `og_image` 의 본문 폴백 제거. `meta.seo.og_image` > `site.default_og_image`
    > 태그 누락. SNS / 메신저 미리보기가 og:image 없을 때 본문 첫 이미지를
    임의로 긁어가는 행동을 SSG 가 빌드 시점에 자동화하지 않는다.
  - **빌드 리포트 일원화** (scripts/report.py 신설). 기존의 abort 경로
    (meta.yaml 파싱 실패 / 필드 누락 / 형식 오류 등) 가 빌드 종료 후 정렬된
    리포트로 통합. 빌드는 어떤 콘텐츠 결함에도 중단되지 않고 끝까지 완성된다.
    시스템 결함 (템플릿 누락, Articles/ 없음, Pillow 미설치 등) 만 `abort()`
    로 즉시 중단.
  - SeoMeta 의 Optional[str] 필드 의미 확장: `None` (opt-out, 태그 누락),
    `''` (실수, 태그 누락 + 리포트), 비어있지 않은 str (정상 출력). 빈 문자
    열을 None 으로 강제 변환하던 동작 폐기.
  - RenderResult 슬림화: `first_paragraph` / `first_image` 필드 제거. markdown
    .py 의 `_FIRST_P_RE` / `_FIRST_IMG_RE` 정규식과 추출 로직 일괄 제거.

v0.5.4 변경 사항 (vs v0.5.3):
  - `<head>`의 `<title>` 폴백 체인 (`{prefix}{title}{suffix}`) 이 글에만 적용
    되던 한계 해소. 홈/카테고리 페이지는 각자의 meta.yaml 에서 (Articles/
    meta.yaml, Articles/<카테고리>/meta.yaml) `title` + `seo.title_prefix` /
    `seo.title_suffix` 로 오버라이드. 404 / search 는 콘텐츠 페이지가 아니라
    meta.yaml 을 두지 않는 대신 site.yaml 의 `error_404_title` /
    `search_title` 로 설정 (default_title_prefix / suffix 폴백 체인은 동일
    적용). CategoryMeta 에 `title` / `seo` (SeoMeta) 추가. SiteConfig 에
    `error_404_title` / `search_title` 추가.
  - description_truncate 가 영문 단어 한가운데를 자르지 않음. scripts/seo.py
    의 `truncate_description` (구 `_truncate` 의 word-boundary 강화판) 으로
    통합. 절단 지점이 ASCII 영문/숫자/하이픈/언더스코어 시퀀스 한가운데이면
    직전 공백까지 backup. 한국어 등 CJK 는 영향 없음 (글자 단위가 의미 단위
    이므로 ASCII 단어 검사 통과 못함). builder 의 article_render_meta 캐시
    (gallery + feed summary) 도 같은 함수를 import 해서 중복 로직 제거.
  - 톱레벨 nav 정렬에 `nav_priority` 도입. ArticleMeta + CategoryMeta 양쪽에
    정수 필드 (기본 0). 값이 클수록 먼저, 같은 값끼리는 폴더명 알파벳 순.
    v0.4.6 까지의 'About 최상단 하드코딩' 폐기. `priority` (부모 카테고리
    page 의 sibling section 정렬) 와는 별개 축. 기존 데이터 그대로 두면
    About 은 알파벳 순으로 여전히 첫째 (A < B) — 명시적으로 다른 자리에 두려면
    Articles/<항목>/meta.yaml 의 nav_priority 를 사용.

v0.5.3 변경 사항 (vs v0.5.2):
  - meta.yaml `tags` 필드 (글 단위 주제어 리스트). 작성자가 직접 적음. inline /
    block 두 형태 모두 허용. 빈 문자열/중복 자동 제거. 현재는 feed `<category>`
    에만 사용 — 검색 가중치 / 태그별 색인 페이지 / 관련 글은 미래 의제.
    카테고리 meta.yaml 에는 의도적으로 두지 않음 (카테고리가 그 자체로 분류 축).
  - 카테고리/홈 `layout: gallery` (이미지 타일 그리드). CSS Grid 반응형
    (auto-fill, minmax 220px), 4:3 강제 크롭, modern minimal 톤. 썸네일은
    seo.og_image > 본문 첫 이미지 > 그라데이션 플레이스홀더. 빌드 시 이미지
    자동 최적화 (v0.5.1) 와 자동 연동.
  - RSS / Atom 피드 자동 생성. scripts/feed.py 신설 — Atom 1.0 기반 추상
    모델 (FeedDocument / FeedEntry) + 두 직렬화 (render_atom / render_rss).
    dist/feed.atom + dist/feed.rss 두 파일이 같은 entry 목록으로. 홈/카테고리/
    글 `<head>` 에 `<link rel='alternate'>` 자동 발견 태그.
  - README §17 한계 표에서 "JS 비활성화 시 페이지 2+ 미표시" 제거 (JS 비활성
    환경 지원 계획 없음). "`layout: list` 만" 항목은 list/gallery 둘 다 구현된
    상태로 갱신. 새 항목으로 "`tags` 의 구체적 활용처 없음".

v0.5.2 변경 사항 (vs v0.5.1):
  - 자산 경로 일원화 (글 자산은 글 폴더 안으로). 옛 `dist/src/{slug}/...`
    트리 폐지, 글 자산은 글의 index.html 과 같은 폴더 `dist/{slug}/` 에
    동거. URL 도 `/src/{slug}/foo.jpg` → `/{slug}/foo.jpg`. "글 폴더 안에서
    자료를 둔다" 라는 글 소스 측 원칙과 dist 출력 구조가 일관됨.
  - reserved_slugs 에서 `src` 항목 제거. `assets`, `search` 만 남음.
  - rewrite_asset_path / imgBox / imgSlideBox 시뮬레이션 모두 새 URL 스킴.
  - _prune_article_assets 가 글 폴더에 동거하는 글 본체 산출물
    (index.html / index.php) 을 잘못 삭제하지 않도록 가드.
  - _prune_orphans 가 옛 빌드의 `dist/src/` 트리를 발견하면 통째로 정리.
    재현성 확보가 필요하면 `--clean` 권장.
  - 비-이미지 산출물 (검색, sitemap.xml, robots.txt, 404.html, 페이지 HTML
    구조) 은 v0.5.1 과 동등. 자산 URL 만 다름.

v0.5.1 변경 사항 (vs v0.5.0):
  - 이미지 자동 최적화 + lazy loading 도입. SEO 직접 영향 (Google
    PageSpeed Insights / Lighthouse 가 Modern image format 미사용 +
    responsive srcset 부재를 명시적으로 감점) 을 고려해 "최소한도의 외부
    의존성 원칙" 의 SEO 예외로 Pillow 의존성 도입.
  - 새 모듈 scripts/images.py — ImageConfig + optimize_image() + transform_img_tags().
  - 빌드 시 모든 raster 이미지 (.jpg .jpeg .png .gif) 를 WebP 다중 해상도
    변종 `{stem}-{width}.webp` 로 변환. site.yaml 의 images.widths 가 기본
    [400, 800, 1600] — 원본 width 이하인 변종만 실제 파일로 생성.
  - 글 본문 HTML 의 모든 <img> 를 후처리 — WebP src 치환 + srcset (다중
    해상도) + sizes 디폴트 + loading="lazy" 자동 부착. 외부 URL / SVG 는
    src 그대로 두고 loading="lazy" 만 추가.
  - 빌드 파이프라인 단계 순서 변경 — _sync_assets / _copy_site_assets 가
    _render_articles 보다 먼저 ([5][6][7] 로 재배치). asset 단계가
    self.image_variants 를 채워야 article render 단계의 <img> 후처리가
    참조할 수 있기 때문.
  - 새 site.yaml 블록 `images:` (enabled / widths / max_width / quality /
    lazy_loading / default_sizes). 모든 키가 기본값 보유 — 옛 site.yaml
    그대로 두어도 v0.5.1 기본 정책으로 동작.
  - dist 산출물 변화: raster 이미지 자리에 `{stem}-{w}.webp` 가 떨어지고,
    원본 파일은 dist 에 복사되지 않음. HTML 의 <img> src 도 webp 로 치환.
  - 검색 / sitemap / robots.txt 등 비-이미지 산출물은 v0.5.0 과 바이트 동일.

v0.5.0 변경 사항 (vs v0.4.7):
  - 검색 시스템을 Okapi BM25 기반 랭킹으로 전환.
      * 검색 인덱스 포맷 v3 (이전 v2 와 비호환). 필드별 df_*, dl_*,
        stats.avgdl_*, params 추가. scripts/search.py 가 빌드.
      * Per-field BM25 점수 (본문: k1=1.5, b=0.75 / 제목: k1=1.2, b=0.5,
        w_title=3.0). v0.4.x 의 매직 ×5 제목 부스트, 단순 TF 합산 폐지.
      * Phrase 부스트 (곱셈) — 원본 쿼리 substring 매치 시 본문 ×1.5,
        제목 ×2.0. 매치 밀도 기반 스니펫.
      * 점수 계산 모듈 분리 (templates/search_bm25.php). search.php 는
        라우팅·필터·HTML 렌더만 담당.
  - tests/ 디렉터리 신설 — BM25 알고리즘 핵심 회귀 차단 (25개 단위 테스트).
    `python -m unittest discover -s tests` 로 실행.
  - 콘텐츠 측 출력 (글 페이지, 홈, 카테고리, sitemap.xml, robots.txt) 은
    v0.4.7 과 출력 동일. 변하는 것은 검색 결과 순서와 스니펫 구간뿐.

v0.4.7 변경 사항 (vs v0.4.6):
  - 문서·코드 정합성 회복 (회귀 0, dist 산출물은 v0.4.6 과 바이트 동일).
      * build.py / scripts/ docstring 의 v0.4.x 표기 일괄 갱신.
      * README §1·§3 의 폴더명 표기를 현행화 (`siheonlee.com_v0.4.7/`).
      * README §11 (site.yaml) 의 옛 home_* 키 예시 제거 + v0.4.6 의
        "설정 책임 분리표" 를 §11 본문으로 끌어올림.
      * README §17 "한계 표" 를 v0.4.6 기준으로 전면 재작성 — v0.4.5 에서
        해결된 항목 (페이지네이션 / i18n / 서브카테고리 인덱스) 제거 +
        v0.4.5/v0.4.6 에서 새로 명시화된 한계 추가.
      * builder._build_home 의 카테고리 path 분기 dead branch 정리.

v0.4.6 변경 사항 (vs v0.4.5):
  - 페이지네이션 nav 의 상/하단 여백 축소 (assets/common_template.css).
  - SSR 시점의 첫 페이지 상태 정적 생성 — 비활성 페이지 항목에 inline
    `style='display:none'` 을 미리 부착해 FOUC 제거. pagination.js 는
    클릭 핸들러만 부착하고, 첫 페이지 항목의 inline style 을 비워 표시.
  - `Articles/meta.yaml` 신설 — 메인페이지 (홈) 의 카테고리-격 설정.
    카테고리 폴더 meta.yaml 과 동일 스키마.
  - `priority` 필드 신설 — 카테고리 meta.yaml 에서 카테고리들이 함께
    표시될 때의 등장 순서를 결정. 값이 클수록 먼저. 같은 값끼리는
    폴더명 알파벳 순. 정수, 기본값 0.
  - 설정 일원화 — 옛 site.yaml 의 `home_per_page` /
    `home_excludes_categories` / `home_sort` 를 `Articles/meta.yaml`
    로 이전 (마지막 항목은 빌더가 사용한 적 없는 dead field 라 폐기).
    site.yaml 은 이제 진짜 '전역' 만 보유.

v0.4.5 변경 사항 (vs v0.4.4):
  - 페이지네이션: 메인 / 카테고리 인덱스 (대분류·소분류) / 상위 인덱스의
    서브카테고리 section 마다 독립적인 페이지 컨트롤. JS DOM hide/show
    (모든 항목 SSR → SEO 영향 없음).
  - 다국어: 템플릿의 <html lang> 가 더 이상 'ko' 하드코딩이 아님. site.lang
    디폴트, 글/카테고리 meta.yaml 의 `lang:` 으로 페이지별 오버라이드.
  - 서브카테고리 인덱스 페이지 신설 (`/{top}/{sub}/`). 톱레벨 페이지는 그대로
    유지 — 서브카테고리들이 section 으로 임베드되는 점도 그대로.
  - 카테고리 meta.yaml 신설 (CategoryMeta): per_page / preview_per_page /
    layout / styles / lang. 한 카테고리의 자기 페이지와 상위 임베드 section
    의 페이지당 글 수를 독립적으로 설정.
  - 비ASCII 폴더명 워닝 메시지 보강 (어떤 폴더가 어떤 hex slug 로 변환되는지
    빌드 로그에서 한눈에 확인).
  - sitemap.xml 에 서브카테고리 URL 포함.

v0.4.4 변경 사항 (vs v0.4.3):
  - sitemap.xml 자동 생성 (scripts/sitemap.py + builder pipeline step [12]).
  - robots.txt 의 `Sitemap:` 디렉티브 주석 해제.

v0.4.3 변경 사항 (vs v0.4.2):
  - 글 `<title>` 에 글 제목 사용 (이전엔 site.name 으로 덮어쓰던 quirk).
  - 마크다운 본문에서 섹션 마커 (`===제목===` / `======`) 사용 가능.
  - meta.yaml 의 평면 seo_* 필드 → `seo:` 하위 블록.

v0.4.2 변경 사항 (vs v0.4.1):
  - 글 slug ↔ 톱레벨 카테고리 slug 충돌을 검증 단계에서 차단.
  - 검색 결과 페이지에 noindex,follow 메타 태그 추가.
  - imgBox/imgSlideBox 인자 파서가 nested parens + quoted `)` 정상 처리.
  - article.html 의 {{ROBOTS_META}} placeholder 들여쓰기 일반화.

v0.4.1 변경 사항 (vs v0.4.0):
  - Parsedown.php → scripts/parsedown.py 포팅. 빌드 PHP 의존 제거.
  - 마크다운 파서 추상화 폐지 (단일 파서).

v0.4.0 변경 사항 (vs v0.3.2):
  - 시스템 캐치프레이즈: SSG → PHP 기반 경량 웹 사이트 생성기.
  - 전역 noindex 메타 태그 제거. 글마다 `noindex: true` 로 개별 차단 가능.
  - 검색 토크나이저: 한국어 1글자는 인덱싱/쿼리 대상에서 제외 (bigram 만 사용).
                  본문 길이 5000자 절단 폐지.
  - Python ↔ PHP 토크나이저 패리티를 빌드 시 fixture 로 자동 검증.
  - 카테고리 _meta.yaml 슬러그 오버라이드 폐기. 한국어 폴더명은
                  코드포인트 hex 로 결정론적으로 변환하되 경고를 띄움.
  - reserved_slugs 정리, seo_keywords 필드 폐기 등 잔재 청소.
  - build.py 분할: 모든 모듈은 scripts/ 패키지에 거주.

자세한 내용은 README.md 의 § 17 (업데이트 로그) 참조.
"""
import argparse
import shutil
import sys
from pathlib import Path

# v0.8.1: 빌더 패키지(scripts/)·템플릿·자산·테스트는 모두 src/ 아래로
# 재배치됐다. build.py 가 자기 폴더의 src/ 를 import 경로 맨 앞에 올려
# `import scripts...` 가 src/scripts/ 를 가리키게 한다. 빌드 동작·산출물은
# 불변 — dist 는 v0.8.0 과 byte 동일 (구조만 정리).
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from scripts.builder import Builder  # noqa: E402
from scripts.cache import CACHE_DIR_NAME  # noqa: E402


# v0.8.2: CLI 견고화. v0.8.1 까지는 raw `'--clean' in sys.argv` 검사라
# 오타 (`--clena`) 가 경고 없이 일반 빌드로 흘러가는 silent footgun 이
# 있었다. argparse 로 전환해 (a) `--help`, (b) 미지/오타 인자 즉시 거부
# (exit 2), (c) run_diagnostics.py 와 같은 idiom 으로 통일. allow_abbrev=
# False 라 `--clean` 이 `--clean-cache` 의 약어로 잘못 흡수되지 않고 오타도
# 약어로 통과하지 않는다. 빌드 로직·산출물은 불변 — 유효 인자의 동작은
# v0.8.1 과 1:1.
def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='build.py',
        description='siheonlee.com 정적 사이트 빌드 (런타임 PHP 대상).',
        epilog=('관련 명령:\n'
                '  python -m unittest discover -s src/tests   # 단위 테스트\n'
                '  python src/tests/run_diagnostics.py        # 통합 진단'),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    parser.add_argument(
        '--clean', action='store_true',
        help='dist/ 와 .build_cache/ 를 모두 지운 뒤 빌드 (완전 재빌드).')
    parser.add_argument(
        '--clean-cache', action='store_true',
        help='.build_cache/ 만 폐기한 뒤 빌드 (dist/ 는 유지).')
    parser.add_argument(
        '--no-cache', action='store_true',
        help='증분 캐시 lookup/store 비활성 (v0.6.5 동작).')
    return parser


def main(argv=None) -> None:
    args = _build_arg_parser().parse_args(argv)
    base = Path(__file__).parent

    # v0.7.0: --clean 은 dist/ 외에 .build_cache/ 도 함께 지운다 (사용자
    # 결정 — '--clean = 완전 재빌드' 의도).
    if args.clean:
        for d in (base / 'dist', base / CACHE_DIR_NAME):
            if d.exists():
                shutil.rmtree(d)
                print(f'Cleaned: {d}')

    # v0.7.0: --clean-cache 만 — dist 는 유지하고 캐시만 폐기. --clean 과
    # 함께 주면 .build_cache/ 가 위에서 이미 사라져 여기선 no-op (무해 —
    # v0.8.1 의 두 독립 if 문과 동일 결과).
    if args.clean_cache:
        cache_dir = base / CACHE_DIR_NAME
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
            print(f'Cleaned: {cache_dir}')

    # v0.7.0: --no-cache — 캐시 lookup/store 비활성. v0.6.5 동작 그대로.
    Builder(base, enable_cache=not args.no_cache).build()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""siheonlee.com v0.6.2 — PHP 기반 경량 웹 사이트 생성기.

이 파일은 빌드의 진입점(entry point) 일 뿐, 모든 실제 로직은
`scripts/` 패키지 안에 모듈별로 나뉘어 있다. 사이트 전역 버전 문자열은
[scripts/__init__.py](scripts/__init__.py) 의 `__version__` 이 단일
source of truth — 피드 generator 등이 이 값을 참조.

Usage:
    python build.py           # full build
    python build.py --clean   # wipe dist/ + dist-legacy/ before build
    python -m unittest discover -s tests   # 단위 테스트 (v0.6.2: 187개)
    python tests/run_diagnostics.py        # 빌드 결정성/BM25 패리티 등 통합 진단

빌드 의존성 (v0.6.2):
    Python 3.10+ stdlib
    Pillow (PIL fork) — 이미지 자동 최적화 (`pip install Pillow`).
        site.yaml 의 images.enabled=false 로 두면 Pillow 없어도 동작.

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
    `_render_template` 가 `(d) {{LANG}} / {{PAGE_TITLE}} / ...` 같이 주석
    *안* 의 placeholder 도 동등하게 치환해버려 dist 헤더가 자기 자신의
    결과를 인용하던 메타-광경 (예: `(d) ko / Search / Lama / <a ...>...</a>`)
    을 정리. 템플릿 측에서 안내 줄에 실제 placeholder 토큰을 쓰지 않고
    plain 이름으로 표기.
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
    redirect.php, feed.atom, feed.rss) 의 형식은 v0.5.5 와 동등. 변경은
    검색 시스템과 단위 테스트·진단 인프라에 한정.

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
  - 비-이미지 산출물 (검색, sitemap.xml, robots.txt, redirect.php, 404.html,
    페이지 HTML 구조) 은 v0.5.1 과 동등. 자산 URL 만 다름.

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
  - 검색 / sitemap / robots.txt / redirect.php 등 비-이미지 산출물은 v0.5.0
    과 바이트 동일.

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
  - 콘텐츠 측 출력 (글 페이지, 홈, 카테고리, sitemap.xml, robots.txt,
    redirect.php) 은 v0.4.7 과 출력 동일. 변하는 것은 검색 결과 순서와
    스니펫 구간뿐.

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
  - dist-legacy/redirect.php 가 site.yaml 의 base_url 을 사용 (도메인
    하드코딩 제거).
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

자세한 내용은 README.md 의 § 18 (업데이트 로그) 참조.
"""
import shutil
import sys
from pathlib import Path

from scripts.builder import Builder


if __name__ == '__main__':
    base = Path(__file__).parent

    if '--clean' in sys.argv:
        for d in (base / 'dist', base / 'dist-legacy'):
            if d.exists():
                shutil.rmtree(d)
                print(f'Cleaned: {d}')

    Builder(base).build()

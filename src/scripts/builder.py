"""빌드 파이프라인 (Builder 클래스).

v0.8.3 변경 — schema.org JSON-LD 구조화 데이터 (additive):
  - **글 페이지 `<head>` 에 `<script type="application/ld+json">` 한 줄**
    추가. `@graph` 로 Article + (2개 이상이면) BreadcrumbList. 기존
    OG/Twitter/canonical/robots 메타 태그를 *대체하지 않고 보강* 한다 —
    소비자가 다르다 (SNS 언퍼ler=OG, SERP=meta description, 색인=robots,
    리치 결과=JSON-LD). 로직은 seo.py 의 `build_jsonld` / `jsonld_enabled`,
    canonical/og_image/author 해석은 build_meta_tags 와 공유 헬퍼
    (resolve_*) 로 추출 — 메타 태그 산출물 byte 불변 (순수 리팩터).
  - **off 스위치** (v0.5.5 "새 기능은 off 스위치 동반" 원칙): 사이트 전역
    `site.yaml`→`jsonld.enabled` (기본 True), 글 단위 `meta.yaml`→
    `seo.jsonld: false`. 사이트 토글이 마스터 (글 단위 true 로 사이트 off
    를 못 뒤집음). 비출력 시 `{{JSONLD}}` 라인을 ROBOTS_META 와 같은
    방식으로 라인-이팅 (빈 줄 잔존 없음).
  - **결정성**: `json.dumps(ensure_ascii=False, sort_keys=True,
    separators=(',',':'))` + `<` `>` `&` → `\\u003c/\\u003e/\\u0026`
    (`<script>` raw-text breakout 방지). 코드 릴리스라 무결성 계약은
    "결정성 2회 동일 + v0.8.2 기준 *열거* diff (= 글 페이지마다 ld+json
    한 줄 추가, 그 외 byte 불변)". 단위 266→297 (+test_jsonld 31).

v0.8.2 변경 — per-Builder 리포트 + build() 멱등성 + 버전 디커플링:
  - **모듈 전역 `_report` 폐지 → `self.report`** — scripts/report.py 가
    v0.5.5 부터 docstring 으로 명세해 온 "Builder 가 self.report 보유,
    self._issue / self._warning 로 라우팅" 을 실제 구현. v0.6.5~v0.8.1 은
    모듈 전역 `_report` + build() 진입 reset 이라 동시 빌드가 봉쇄됐다.
    모듈 함수 warn()/issue()/report()/reset_report() 제거. 모듈 레벨
    `_render_template` 은 self 가 없어 `report=` 인자로 받는다.
  - **`build()` 멱등성 결함 수정** — v0.6.5/v0.7.2 가 _report/_console 만
    리셋했고 데이터 컬렉션 (articles/slug_to_article/categories/...) 은
    __init__ 에서만 초기화돼, 같은 인스턴스로 두 번째 build() 시
    `_validate` 가 'slug 중복' 을 잘못 보고했다 (옛 테스트가 매번 새
    인스턴스를 써서 가려짐 — v0.8.2 의 재사용 테스트가 노출). build()
    진입 시 누적 상태 전부 초기화. 캐시 디스크 매니페스트는 빌드 간
    의도적 영속이라 범위 밖.
  - **버전 디커플링 (B1)** — `_build_feeds` 의 generator 문자열에서
    `v{__version__}` 토큰 제거. `__version__` 의 dist 영향이 영구히 0
    (이전엔 이 한 줄이 유일 누수). dist 는 v0.8.0 과 generator 한 줄만
    차이 (의도). 단위 258→266, 진단 5/5.

v0.7.2 변경 — 빌드 진행 표시 + 빌드 리포트 문서화:
  - **진행 헬퍼 3종 (`_emit` / `_live` / `_step`)** — `_emit` 은 마일스톤
    한 줄을 터미널에 출력하면서 `self._console` 에 누적 (빌드 종료 시
    build-report.md 의 "빌드 진행" 트랜스크립트). `_live` 는 무거운 루프
    (`_sync_assets` 이미지 변환 / `_render_articles`) 의 in-place(`\\r`)
    카운터 — `sys.stdout.isatty()` 가 False 면 no-op 이라 redirect 된
    환경 (run_diagnostics / 단위 테스트) 의 캡처 로그가 깔끔하고 결정성에
    영향이 없다. `_step` 은 `[ n/16]` 16 단계 헤더.
  - **`build()` 가 16 단계 헤더 + 타이밍 + 리포트 문서 생성** — 단계 직전
    `_step`, 종료 시 `_write_build_report()` 가 `self.base` 에
    build-report.md 작성. 요약/완료 라인도 `_emit` 경유라 트랜스크립트에
    포함. `# [n]` 주석은 v0.4.x~v0.6.4 의 역사적 파이프라인 id 라
    유지하고, 사용자 대상 진행 번호만 1..16 단조.
  - **결정성 불변** — 진행 출력·리포트 문서는 dist/ 밖. dist 산출물은
    v0.7.1 과 byte 동일 (feed generator 문자열만 자동 갱신).

v0.7.0 변경 — 빌드 증분 캐싱 (글 단위, fine-grained):
  - **scripts/cache.py 신설** — `BuildCache` + `CachedArticle` + `replay_*` 헬퍼.
    `_render_articles` 가 글마다 `compute_article_hash` 로 해시를 만들고
    `cache.lookup(slug, hash)` 로 매니페스트와 비교한다. hit 면 캐시된 HTML/
    PHP 를 dist 에 그대로 복원 + 부수 산출 (rendered_bodies[slug] / article_
    render_meta[slug] / BuildReport 의 issue·warning 항목) 도 함께 복원해
    이후 단계 (검색 인덱스 / 피드 / 갤러리) 가 캐시 hit 경로에서도 첫 빌드와
    동등하게 진행된다. miss 면 평소대로 렌더한 뒤 `cache.store(...)` 로 다음
    빌드를 위해 기록.
  - **`Builder.__init__(base_dir, *, enable_cache=True)`** — `--no-cache` CLI
    플래그가 `enable_cache=False` 로 인스턴스를 만든다. 그 경우 lookup() 이
    항상 None 을 반환하고 store() 가 no-op — v0.6.5 와 동등 동작 + 매니페스트
    디스크 I/O 0.
  - **글 단위 캐시 통계** — `Builder._cache_hits` / `_cache_misses` 가 빌드
    종료 시 콘솔에 "증분 캐시: N 히트 / M 미스 (글 K건)" 로 표시. 캐시 hit/
    miss 가 0/0 인 경우 (예: 글 0 개) 라인 자체가 출력되지 않음.
  - **결정성 가드** — 캐시는 *재렌더 여부* 만 결정하고 *산출물 자체* 는 바꾸지
    않는다. tests/run_diagnostics.py 의 [2] 결정성 섹션이 캐시 hit 경로에서
    도 통과 (두 번째 빌드의 dist 가 byte 동일).
  - **글의 issue / warning 도 캐시** — `_render_articles` 내부에서 `_report`
    에 들어가는 항목 중 `scope='article'` AND `target=slug` 인 것만 *현재 글*
    의 캐시로 분리 저장. 캐시 hit 시 그 항목들이 `replay_issue` /
    `replay_warning` 으로 다시 `_report` 에 들어가 빌드 리포트가 매 빌드 byte
    동일.

v0.6.5 변경 — 안정화 패치 (v0.6.0 ~ v0.6.4 누적 회귀 4 건):
  - **Builder.build() 자동 _report reset** — 한 프로세스에서 build() 를 여러
    번 호출해도 _report 가 누적되지 않는다. v0.6.4 까지는 호출자가 명시적으로
    reset_report() 를 호출해야 했고, tests/run_diagnostics.py 의 결정성
    섹션 (build 2 회 연속) 이 이 버그를 가시화 했다. build() 진입 시 reset.
  - **_render_template 의 3-pass 분리** — content_vars 인자 추가. 사용자
    콘텐츠 (BODY / SUBCATEGORY_SECTIONS / ARTICLE_LIST) 의 substitute 를
    leftover 검출/strip 이후로 미뤄, 사용자 본문 안의 `{{XXX}}` 대문자
    placeholder 패턴이 silent 으로 제거되지 않게 한다. v0.6.4 의 회귀였다.
  - **og_type 디폴트 강제 제거** — _parse_frontmatter / _parse_category_meta_file
    가 og_type 의 빈 값을 'article' / 'website' 로 강제하던 코드를 제거.
    v0.6.2 의 page_kind 기반 디폴트 분기 (build_meta_tags) 가 dead code 가
    아닌, 의도된 단일 진실원으로 되살아남.

v0.6.4 변경 — CSS 일원화 (홈/카테고리도 글과 동일) + template 키:
  - 글/카테고리/홈의 `styles:` 두 채널 (정수 키 = 외부 CSS, 문자열 키 = 인라인
    룰) + `use_common_css` 토글이 *모두* 동일 의미로 작동. v0.6.3 의 "카테고리/
    홈은 외부 CSS 영구 미지원" 정책 폐기. CategoryMeta 가 글의 ArticleMeta 와
    같은 `stylesheets` / `use_common_css` 필드를 가진다.
  - **공용 검증 헬퍼 `_validate_stylesheets`** — 글/카테고리/홈의 styles 정수
    키 (CSS 파일 상대 경로) 를 같은 규칙으로 검증 (절대 경로 거부, `..` 거부,
    빈 경로 거부, 파일 존재 확인). 검증 통과한 상대 경로만 stylesheets 에
    저장. 거부된 항목은 scope 별 issue.
  - **새 빌드 단계 `_sync_page_css`** — 카테고리/홈의 선언된 CSS 파일을
    dist 에 명시적으로 복사. 글은 기존 [6] `_sync_assets` 가 폴더를 통째로
    복사하므로 별도 처리 불필요. 카테고리: `Articles/Cat/<rel>` →
    `dist/<cat_slug_path>/<rel>` (URL = `/<cat_slug_path>/<rel>`). 홈:
    `Articles/<rel>` → `dist/<rel>` (URL = `/<rel>`, 사이트 루트).
  - **`render_stylesheet_links` 시그니처 일반화** — 두 번째 인자가 `slug` →
    `url_prefix`. 글은 `f'/{m.slug}/'`, 카테고리는 `'/' + '/'.join(slug_path) + '/'`,
    홈은 `'/'` 로 호출.
  - **placeholder 이름 통일** — 세 템플릿 모두 `{{COMMON_CSS}}` /
    `{{PAGE_STYLESHEETS}}` / `{{PAGE_STYLES}}` 같은 이름. v0.6.3 의
    `{{ARTICLE_STYLESHEETS}}` / `{{ARTICLE_STYLES}}` / `{{CATEGORY_STYLES}}` 는
    모두 일제히 변경. dist 산출물은 placeholder 가 렌더 후 사라지므로 byte
    영향 없음 (단 home/index.html 은 새 `{{PAGE_STYLES}}` 라인이 1줄 추가됨 —
    기본 styles 비어있어 trailing whitespace 줄 1 줄).

  - **새 `template:` 키 (Level 2)** — `meta.yaml` 이 자기 페이지에 사용할
    템플릿 파일을 명시. 키 부재 시 페이지 종류 기본 (글=article.html,
    카테고리=category.html, 홈=home.html). 값 형식:
      'name.html'   → templates/ 에서 검색.
      './name.html' → meta.yaml 의 부모 폴더에서 검색 (글 폴더, 카테고리 폴더,
                      Articles/ 루트 — "글 = 폴더" 원칙의 자연 연장).
      절대 경로 / `..` 포함 / 존재하지 않는 파일 → BuildReport issue + 기본
      페이지 종류 템플릿으로 폴백 (빌드는 계속).
    검증 + 로드는 새 `_resolve_template` 메서드가 담당.
  - **`_render_template` 후처리** — 마지막에 남은 `{{XXX}}` placeholder 를
    빈 문자열로 strip + 각 미치환 이름마다 BuildReport 의 warning. author 가
    페이지 종류를 가로지르는 템플릿 (예: 카테고리 meta 가 article.html 을
    template 로 지정) 을 골랐을 때, 필요한 vars 가 안 들어와 발생하는 silent
    leak 을 가드. 호출자가 warn_context=(scope, target, location) 로 알리고
    싶으면 이를 넘기고, 시스템 페이지 (404 / search) 처럼 빌더가 직접
    컨트롤하는 템플릿은 None 으로 호출 — strip 만 적용.

v0.6.3 변경 — 글 단위 외부 CSS 파일 + use_common_css 토글:
  - `meta.yaml` 의 `styles:` 키가 두 채널을 동시에 가질 수 있게 확장. 정수
    키 (1, 2, 3, ...) 는 글 폴더 안의 외부 CSS 파일 상대 경로, 문자열 키
    (tag/selector) 는 기존 인라인 룰. 두 채널이 같은 키 아래 자유롭게 섞임.
    `_parse_frontmatter` 가 `normalize_styles` 의 (sheets, rules) 결과를
    받아 ArticleMeta 의 새 `stylesheets` 필드와 기존 `styles` 필드로 분리
    저장. CSS 파일은 글 폴더에 *실제로 존재해야* 함 — 없거나 글 폴더를
    이탈 (`/`, `..`) 하면 BuildReport 의 issue 로 기록 + 해당 link 만 출력
    제외 (빌드는 통과).
  - `_render_articles` 가 두 새 placeholder 를 렌더 — `{{COMMON_CSS}}` 는
    `use_common_css` 가 True 면 `<link href='/assets/common_template.css' ...>`,
    False 면 placeholder 라인 통째로 제거 (ROBOTS_META 와 동일한 line-eating
    패턴). `{{ARTICLE_STYLESHEETS}}` 는 ArticleMeta.stylesheets 의 각 항목을
    `<link href='/{slug}/<rel>' rel='stylesheet'>` 로 렌더 (정수 키 오름차순).
    로드 순서 = common → 외부 CSS → 인라인 `<style>` (인라인이 마지막 발언권
    = "미세 override" 의도).
  - 카테고리/홈은 외부 CSS 미지원 (영구적 정책). `_parse_category_meta_file`
    이 styles 의 정수 키를 발견하면 issue 로 알려주고 인라인 룰만 채택.
    `use_common_css` 토글도 글에만 존재 (카테고리/홈에는 없음).
  - 함수 이름 변경: 옛 `render_article_styles` 가 `render_inline_styles` 로
    바뀌고, 새 `render_stylesheet_links(sheets, slug)` 가 외부 CSS link 렌더
    전담. 카테고리의 `_category_styles_html` 도 `render_inline_styles` 로 전환.

v0.6.2 변경 — 홈/카테고리 페이지 SEO 메타 태그 출력:
  - v0.5.4 의 한계 표 "홈/카테고리 페이지의 SEO 메타 태그 출력 (description /
    og_* / twitter_*)" 항목 해소. `_build_home` 과 `_build_category_page` 가
    `build_meta_tags()` 를 호출해 글과 동일한 메타 태그 묶음을 생성하고,
    home.html / category.html 의 새 `{{META_TAGS}}` placeholder 자리에
    렌더한다. 글 페이지 산출물 (dist/{slug}/index.html) 은 v0.6.1 과 바이트
    동일 (회귀 가드).
  - **`build_meta_tags()` 시그니처 일반화** — keyword-only 인자 `title`, `seo`,
    `site`, `canonical_path`, `page_kind` (+옵션 `published` / `updated`) 로
    변경. 글의 `_render_articles` 도 새 시그니처로 호출 (`page_kind='article'`,
    `published=m.date`, `updated=m.updated or m.date`). 페이지 종류별 차이는
    seo.py 안에 두 군데 — og:type 디폴트와 article:* 시간 태그의 출력 여부.
  - **`SeoMeta.og_type` 디폴트 변경** — `'article'` → `None`. 글/홈/카테고리가
    같은 SeoMeta 모델을 쓰기 때문에 페이지 종류 별 디폴트가 필요. None 이면
    `build_meta_tags` 가 page_kind 로 결정 (글=article, 홈/카테고리=website).
  - **description 필수화 정책의 홈/카테고리 확장** — 새 헬퍼
    `_check_page_description(seo, page_kind, location, slug='')` 가 글과
    동일한 누락/빈 문자열 검사를 페이지 종류 별로 일반화. issue 의 scope 가
    'home' / 'category' / 'article' 셋 중 하나.
  - `_wrap_page_title` 의 사용처가 404 / search 두 곳으로 축소 (글/홈/카테고리는
    모두 build_meta_tags 의 full_title 을 직접 사용 — `<title>` 폴백 체인이
    한 함수로 통일).
  - 색인 정책 변경 없음 — 홈 / 톱레벨 카테고리 / 서브카테고리 모두 색인 허용
    그대로. robots meta 출력 안 함. sitemap.xml 도 v0.4.4 ~ v0.6.1 정책 그대로.

v0.6.1 변경 — 문서·주석·산출물 가독성 안정화 3회차 (코드 동작 변경 0):
  - templates/search.php 헤더 주석의 placeholder 누수 결함 해소. 안내 자체에
    placeholder 토큰을 박아 두면 `_render_template` 의 단순 문자열 치환이
    주석 안에서도 동작해 dist 의 헤더가 자기 결과를 인용하는 메타-광경이
    됐다. 템플릿 측에서 안내 줄에 plain 변수명 (LANG, PAGE_TITLE, ...) 만
    적도록 정리. 빌더 코드는 그대로.
  - templates/search_tokenize.php 의 헤더 주석 "search.php 가 require_once 하고
    build.py 가 CLI 로 실행" 이 v0.6.0 의 인라인 흐름과 모순되던 부분 갱신.
    템플릿은 진단·CLI 패리티용 단일 진실원으로 그대로 유지된다.
  - scripts/models.py 의 ArticleMeta.tags 관련 두 군데가 v0.5.3 / v0.6.0 의
    실제 사용처 (feed `<category>` + BM25 색인) 를 누락하고 "미사용" 으로
    안내하던 부분, Articles/Blog/Hello World/meta.yaml 의 옛 본문 폴백 안내
    + tags 미사용 안내, Articles/Blog/meta.yaml 의 layout=gallery 미구현
    안내가 일괄 정리됨.
  - README §12 마크다운 파이프라인 도식의 first_paragraph / first_image
    잔존 + §13 토크나이저 절의 require_once 흐름 + 파일 트리에서
    search_tokenize.php 의 인라인 사실 누락 정정. §18 release notes 의 v0.x.x
    검증 노트는 역사 기록으로 보존.

v0.6.0 변경 — 검색 인덱스 재설계 (메타데이터 3-필드 + PHP 인라인):
  - `_build_search` 가 `search-index.json` / `search_tokenize.php` /
    `search_bm25.php` 세 파일 산출 → `dist/search.php` 한 파일 인라인으로
    전환. 템플릿의 sentinel 주석 (`/* INLINE: SEARCH_TOKENIZE */`,
    `/* INLINE: SEARCH_BM25 */`, `/* INLINE: SEARCH_INDEX */ []`) 을
    builder 가 치환. `_inline_php_body` helper 가 인라인 대상 파일의
    `<?php` 헤더 / `declare(strict_types)` / 끝의 `?>` / CLI block 을 정리.
    v0.5.x dist 위에 빌드하면 잔존 세 파일은 명시적으로 unlink.
  - 인덱스 자체는 [scripts/search.py](scripts/search.py) 의 v4 포맷 —
    title / description / tags 3-필드만 색인. 본문 평문은 스니펫용으로
    글마다 앞 1500 자만 인덱스에 보존. tags 가 새 가중치 필드 (`w_tags=2.5`).
    `php_array_literal` 의 결정적 직렬화로 두 번 빌드 시 sha256 동일.
  - 콘텐츠 측 (글/홈/카테고리/sitemap/robots/feed) 의 형식은
    v0.5.5 와 동등. builder 변경은 검색 단계와 import 한 줄
    (`from . import __version__ as _SITE_VERSION` — 피드 generator 문자열용).

v0.5.5 변경 — 본문 ↔ 메타데이터 분리 원칙 + 빌드 리포트 일원화:
  - 본문 폴백 폐지: SEO description / og_image / 갤러리 썸네일 / 피드 summary
    가 더 이상 본문 첫 `<p>` / 첫 `<img>` 를 폴백 소스로 쓰지 않는다.
    `_render_articles` 의 article_render_meta 캐시는 author 가 meta.yaml 에
    직접 적은 `seo.description` / `seo.og_image` (또는 site.default_og_image)
    만 참조. v0.5.3 부터 있던 `rr.first_paragraph` / `rr.first_image` 참조
    제거. RenderResult 도 `html` 한 필드로 슬림화 (scripts/markdown.py 참조).
  - SeoMeta 의 3-상태 의미 도입: `None` = opt-out (메타 태그 누락),
    `''` = 작성자 실수 (메타 태그 누락 + BuildReport 기록), 비어있지 않은
    str = 정상 출력. `_parse_frontmatter` 의 `_seo_str` helper 가 빈 문자열을
    None 으로 강제 변환하던 동작을 폐기 — yaml_load 가 돌려준 값을 그대로
    보존해 builder 가 None vs '' 를 구분할 수 있다.
  - 필수 필드: `seo.description` 누락/빈 문자열을 리포트에 기록. 글 자체의
    빌드는 진행되며 description / og:description / twitter:description /
    피드 summary 가 누락된다 (작성자가 보완해야 할 미완성 상태).
  - og_image 의 본문 폴백 제거: `seo.og_image` > `site.default_og_image`.
    둘 다 부재하면 og:image 태그 자체를 출력하지 않는다. SNS 가 본문 첫
    이미지를 임의로 긁어가는 행동을 SSG 가 빌드 시점에 자동화하지 않는다는
    원칙 (README § 16 의 설계 원칙 10 참조).
  - 빌드 리포트 일원화 (scripts/report.py): 기존의 `warn()` / `die()` 가
    모듈 전역 BuildReport 인스턴스로 라우팅. meta.yaml 의 필드 부족 / 빈
    문자열 / 형식 오류는 *글 단위로 산출물 일부를 누락* 한 채 빌드를
    완성하고, 빌드 종료 시 터미널에 미완성 글 목록을 몰아서 표시. 시스템
    결함 (템플릿 누락, Articles/ 없음, Pillow 미설치 등) 만 `abort()` 로
    즉시 중단. 콘텐츠 작성자의 실수와 시스템 측 결함이 명확히 분리된다.

v0.5.4 변경 — `<title>` 폴백 체인 일반화 + 단어 경계 truncate + nav_priority:
  - v0.4.3 부터 글에만 적용되던 `<title>` 폴백 체인이 홈/카테고리/404/search
    에도 적용됨. 새 helper `_wrap_page_title(body, seo_override=None)` 가
    `{prefix}{body}{suffix}` 를 만들고, prefix/suffix 는 페이지의 seo
    override (있으면) > site.default_title_prefix / suffix (폴백). 본문은
    홈은 home_meta.title or site.name, 카테고리는 cat.meta.title or
    cat.folder_name, 404 는 site.error_404_title, search 는 site.search_title.
  - description_truncate 가 영문 단어 경계를 존중. 새 함수
    `seo.truncate_description` (구 `_truncate` 의 word-boundary 강화판) 으로
    통합. builder 의 article_render_meta 캐시 (gallery + feed summary) 도 같은
    함수를 import 해서 중복 로직 제거. 영문 단어 한가운데에서 절단되려고
    하면 직전 공백까지 backup. 한국어 등 CJK 는 영향 없음 (글자 단위가 의미
    단위이므로 ASCII 단어 검사를 통과 못함).
  - 톱레벨 nav 정렬에 `nav_priority` 도입. ArticleMeta + CategoryMeta 양쪽에
    정수 필드 (기본 0). `_top_level_entries` 가 `(-nav_priority, folder_name)`
    로 정렬. v0.4.6 까지의 'About 최상단 하드코딩' 폐기. `priority` (부모
    카테고리 page 의 sibling section 정렬) 와는 별개 축.

16단계 파이프라인 (v0.5.3 에서 _build_feeds 추가, v0.6.4 에서 _sync_page_css 추가):
  [1] _load_config           — site.yaml + 토크나이저 패리티 검증
  [2] _scan_articles         — Articles/ 트리 순회, _ / . 접두 제외
  [3] _parse_frontmatter     — meta.yaml 파싱 → ArticleMeta 채움 (seo: 블록 +
                                v0.5.3 의 tags 필드 포함)
  [4] _validate              — slug 검증, 카테고리 트리 구축 (한글 폴더 워닝),
                                카테고리 meta.yaml 파싱 (v0.4.5)
  [5] _sync_assets           — 본문 외 자원 → dist/{slug}/ (v0.5.2 부터 글의
                                index.html 과 같은 폴더). v0.5.1 부터 raster
                                이미지 (.jpg .jpeg .png .gif) 는 Pillow 로
                                WebP 변종들 (srcset 너비별) 로 변환 +
                                self.image_variants 에 등록.
  [6] _copy_site_assets      — assets/ → dist/assets/. v0.5.1 부터 raster
                                이미지는 _sync_assets 와 동일하게 WebP 변환.
  [6b] _sync_page_css        — 카테고리/홈의 선언된 외부 CSS 파일을 dist 에
                                명시 복사 (v0.6.4). 글의 외부 CSS 파일은
                                [5] _sync_assets 가 글 폴더 통째 복사로 처리.
  [7] _render_articles       — 본문 렌더 + 섹션 마커 처리 + nav/SEO/styles +
                                v0.5.1 의 <img> 후처리 (WebP src + srcset +
                                sizes + loading=lazy) → dist/{slug}/. v0.5.3
                                부터 글 단위 thumb/summary 캐시 (gallery + feed
                                가 참조) 를 self.article_render_meta 에 등록.
  [8] _build_categories      — 톱레벨 + 서브카테고리 인덱스 페이지 (v0.4.5).
                                v0.5.3 부터 카테고리 meta.layout='gallery' 면
                                section 이 이미지 타일 그리드로 렌더.
  [9] _build_home            — 루트 페이지 (Recent + 페이지네이션, v0.4.5).
                                v0.5.3 부터 Articles/meta.yaml 의
                                layout='gallery' 도 지원.
  [10] _build_404            — 404 페이지
  [11] _build_robots         — robots.txt
  [12] _build_sitemap        — dist/sitemap.xml (v0.4.4 신설, v0.4.5 에서
                                서브카테고리 URL 도 포함)
  [12b] _build_feeds         — dist/feed.atom + dist/feed.rss (v0.5.3 신설).
                                scripts/feed.py 의 추상 모델로 두 파일이 같은
                                entry 목록을 공유.
  [13] _build_search         — dist/search.php 단일 파일 생성 (v0.6.0).
                                메타데이터 3-필드 BM25 인덱스를 PHP 정적 배열
                                리터럴로, 토크나이저 + BM25 점수 계산기를
                                같은 파일에 인라인. 옛 search-index.json /
                                search_tokenize.php / search_bm25.php 가
                                dist 에 남아 있으면 명시적으로 unlink.
  [14] _prune_orphans        — 삭제된 슬러그/카테고리의 dist 잔재 정리 +
                                v0.5.2: 옛 dist/src/ 트리 일괄 제거

v0.5.3 변경 — tags + gallery layout + RSS/Atom 피드:
  - meta.yaml `tags` 필드. ArticleMeta.tags 신설 (list[str]). 파싱은
    `_parse_frontmatter`. 빈 문자열·중복 자동 제거 (순서 보존). 카테고리
    meta.yaml 에는 의도적으로 두지 않음.
  - 카테고리/홈 `layout: gallery`. `_gallery_tile_html` 신설,
    `_listup_items_html` / `_render_section` 에 layout 매개변수 추가.
    pagination.js 가 `.gallery-tile` 도 페이지네이션 대상으로 인식.
    썸네일 결정 규칙: seo.og_image > rr.first_image > 빈 플레이스홀더.
    이미지 자동 최적화 (v0.5.1) 와 자동 연동.
  - scripts/feed.py 신설 — Atom 1.0 기반 추상 모델 + render_atom /
    render_rss 두 직렬화. `_build_feeds` 가 파이프라인 [12b] 단계로 추가.
    홈/카테고리/글 템플릿 `<head>` 에 `<link rel='alternate'>` 자동 발견
    태그 삽입.
  - self.article_render_meta 캐시 도입 — _render_articles 단계에서 글마다
    {thumb, summary} 를 저장, gallery 와 feed 양쪽이 참조.

v0.5.2 변경 — 자산 경로 일원화 (글 자산은 글 폴더 안으로):
  - 글 자산이 dist/src/{slug}/ 대신 dist/{slug}/ 로 (글 index.html 과 같은
    폴더). "글 폴더 안에서 자료를 둔다" 라는 글 소스 측 원칙과 dist 출력
    구조가 일관됨.
  - reserved_slugs 에서 `src` 제거 — 더 이상 충돌 가능 디렉터리가 아님.
    `assets`, `search` 만 남음.
  - rewrite_asset_path / imgBox / imgSlideBox 시뮬레이션이 모두 새 URL
    스킴 (`/{slug}/...`) 으로 출력.
  - _prune_article_assets 가 글 폴더에 동거하는 index.html / index.php 를
    잘못 삭제하지 않도록 가드. (asset sync 가 article render 보다 먼저
    돌지만, 두 번째 빌드부터는 이전 빌드의 index.html 이 같은 폴더에 이미
    존재한다.)
  - _prune_orphans 가 옛 빌드의 dist/src/ 트리를 발견하면 통째로 정리.

v0.5.1 변경 — 이미지 자동 최적화 + lazy loading:
  - 외부 의존성 도입: Pillow. v0.4.1 의 "빌드 PHP 의존 제거" 와 같은
    보수적 의존성 정책에도 불구하고, WebP 인코딩 / 정확한 리샘플링은
    stdlib 만으로 현실적으로 구현 불가. WebP / responsive srcset 부재는
    Google PageSpeed Insights 및 모바일 검색 랭킹에 직접 감점 요인이라
    "최소한도의 외부 의존성 원칙" 의 SEO 예외로 허용. site.yaml 의
    images.enabled=false 로 끄면 의존성 없이 v0.5.0 과 동등 동작.
  - 새 모듈 scripts/images.py — ImageConfig dataclass + optimize_image()
    (raster → WebP 변종 다중 해상도) + transform_img_tags() (<img> 후처리:
    WebP src 치환, srcset / sizes 추가, loading="lazy" 자동 부착).
  - 빌드 파이프라인 단계 순서 변경 — _sync_assets / _copy_site_assets 가
    _render_articles 보다 먼저. 두 asset 단계가 self.image_variants 에
    원본 URL → 변종 정보를 등록하고, _render_articles 가 그 정보로 본문
    <img> 를 후처리한다.
  - raster 이미지 (.jpg .jpeg .png .gif) 는 원본을 dist 에 복사하지 않고
    `{stem}-{width}.webp` 변종만 생성. 원본 width 이하의 widths 만 실제
    파일이 생긴다. SVG / 이미 webp 인 파일은 그대로 복사하고 후처리는
    loading="lazy" 부착에만 한정.
  - 캐시 — variant 의 mtime 이 원본 mtime 이상이면 재인코딩 건너뜀.
    _prune_article_assets 가 stem-*.webp 자매 파일을 보존 대상으로 인식.

v0.5.0 변경 — BM25 검색 시스템:
  - scripts/search.py 가 BM25 인덱스 (포맷 v3) 를 빌드. 필드별 (body/title)
    df / dl / avgdl 통계 + tf posting.
  - 런타임 점수 계산이 templates/search_bm25.php (신설) 로 분리. search.php
    는 라우팅·필터·HTML 렌더만. _build_search 가 search_bm25.php 도 dist 로
    복사 (search.php 가 require_once).
  - v0.4.x 의 단순 TF 누적 + 매직 ×5 제목 부스트 폐지. 흔한 한글 bigram 의
    과대 영향, 긴 글의 부당한 가산점, 짧은 매치 vs 정확한 phrase 매치의
    역전 등 알려진 결함 일괄 해소.
  - 매치 밀도 기반 스니펫 — 토큰 매치가 가장 밀집된 80자 윈도우.
  - tests/test_bm25.py 신설 — BM25 알고리즘 핵심 회귀 차단.

v0.4.7 변경:
  - _build_home 의 카테고리 path 분기 dead branch 정리 (출력 동일).
  - docstring 의 v0.4.x 버전 표기 일괄 갱신. 동작 변경 없음.

v0.4.6 변경:
  - 페이지네이션 nav 의 상/하단 여백 축소 (assets/common_template.css).
  - SSR 단계에서 페이지네이션 첫 페이지 상태를 정적으로 출력 — 비활성 페이지
    항목은 inline `style='display:none'` 으로 미리 숨김 → FOUC 제거.
    pagination.js 는 그 후에 첫 페이지 항목의 inline style 을 비워 정상 표시.
  - Articles/meta.yaml 신설 (메인페이지 = 홈의 카테고리-격 설정).
  - 모든 카테고리/홈 meta.yaml 에 priority 필드 (정수, 값이 클수록 먼저).
  - **설정 일원화**: 홈 (메인페이지) 전용 설정은 site.yaml 에서 Articles/
    meta.yaml 로 전부 이전. site.yaml 은 진짜 '전역' (카테고리류 디폴트, lang
    디폴트, SEO 폴백 등) 만 보유. 옛 home_per_page / home_excludes_categories
    는 각각 Articles/meta.yaml 의 per_page / excludes_categories 로 이동.
    home_sort 는 빌더가 사용한 적 없는 dead field 라 폐기.

v0.4.5 변경:
  - 카테고리 폴더의 meta.yaml 파싱 (CategoryMeta). per_page /
    preview_per_page / layout / styles / lang.
  - 서브카테고리도 자기 인덱스 페이지를 가짐 (`/{top}/{sub}/`). 톱레벨
    페이지는 그대로 유지 (서브카테고리들의 section 들이 임베드).
  - 메인페이지 Recent / 카테고리 인덱스 (대분류·소분류) / 상위 카테고리에
    임베드된 서브카테고리 section 마다 독립적인 페이지 컨트롤.
    JS DOM hide/show 로 구현 — 모든 항목은 SSR.
  - 다국어: 템플릿의 `<html lang>` 가 더 이상 'ko' 하드코딩이 아님.
    site.lang 디폴트, 글/카테고리 meta.yaml 의 `lang:` 으로 오버라이드.
  - 한국어 폴더명 워닝의 메시지 보강 (어떤 폴더가 어떤 hex slug 로
    변환되었는지 빌드 로그에서 한눈에).

v0.4.4 변경:
  - sitemap.xml 자동 생성 (scripts/sitemap.py). 글·카테고리·홈 URL 을 포함.
    noindex 글과 서브카테고리는 제외. lastmod 는 updated 우선, 없으면 date.
  - robots.txt 의 `Sitemap:` 디렉티브가 더 이상 주석 처리되지 않음.

v0.4.3 변경:
  - <title> 에 글 제목 사용 (이전엔 항상 site.name 으로 덮어쓰던 quirk 제거).
    `{seo.title_prefix}{title}{seo.title_suffix}` 형태.
  - meta.yaml 의 평면 seo_* 필드 → `seo:` 하위 블록 (SeoMeta 로 파싱).
  - 마크다운 본문 안에서 섹션 마커 (===제목===, ======) 사용 가능.
    body 조립을 markdown.resolve_section_markers 에 위임.

v0.4.0 변경:
  - _meta.yaml 슬러그 오버라이드 코드 경로 완전 제거.
  - 한국어 폴더명 자동 경고 + ASCII 코드포인트 폴백 (slugs.py).
  - ROBOTS_META placeholder 로 article 단위 noindex.
  - search 인덱스 빌드 직전 토크나이저 패리티 검증.
  - 본문 길이 절단 제거 (search.build_search_index).
"""
import datetime
import os
import re
import shutil
import sys
import time
import unicodedata
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from .yaml_parser import yaml_load
from .models import (
    SiteConfig, ArticleMeta, SeoMeta, CategoryMeta, Article, Category,
    JsonLdConfig, AdSenseConfig,
)
from .slugs import (
    category_slug_from_name, is_excluded_path, is_excluded_name, has_non_ascii,
)
from .markdown import (
    escape_html,
    render_article_md,
    render_inline_styles,
    render_stylesheet_links,
    normalize_styles,
    process_html,
    has_live_php,
    parse_php_globals,
    resolve_section_markers,
)
from .images import (
    ImageConfig,
    VariantSet,
    optimize_image,
    transform_img_tags,
    RASTER_EXTS,
    ALL_IMAGE_EXTS,
    _HAS_PIL,
    _split_url,
    _build_srcset,
)


# ════════════════════════════════════════════════════════════════
# 페이지네이션 helper (v0.4.5)
#
# 모든 페이지네이션은 JS DOM hide/show. 서버는 한 페이지에 모든 항목을
# 렌더하고 (SEO 친화), data-per-page 와 함께 pagination_nav HTML 을 같이
# 출력한다. pagination.js 가 `.paginated` 섹션과 그 직후의 `.pagination-nav`
# 를 짝지어 클라이언트에서 hide/show.
#
# 한 페이지에 *여러* 페이지네이션 컨트롤이 있을 수 있으므로
# (예: 톱레벨 카테고리 인덱스의 서브카테고리 섹션들), 각 짝을 명확히
# 묶기 위해 data-pagination-group="<key>" 속성을 사용한다.
# ════════════════════════════════════════════════════════════════


def _pagination_section_attrs(group_key: str, per_page: int) -> str:
    """`.paginated` section 의 data 속성 모음 (group_key, per_page)."""
    safe = escape_html(group_key)
    return f'class="paginated" data-pagination-group="{safe}" data-per-page="{per_page}"'


def _pagination_nav_html(group_key: str, total_items: int, per_page: int) -> str:
    """페이지 컨트롤 HTML.

    items 가 per_page 이하면 빈 문자열 (컨트롤 자체 미출력).
    """
    if per_page <= 0:
        per_page = 1
    pages = (total_items + per_page - 1) // per_page
    if pages <= 1:
        return ''
    safe = escape_html(group_key)
    return (
        f'<nav class="pagination-nav" data-pagination-group="{safe}" '
        f'data-total-pages="{pages}" aria-label="pagination">'
        f'<button type="button" class="pagi-btn pagi-prev" '
        f'aria-label="Previous page" disabled>‹</button>'
        f'<span class="pagi-info"><span class="pagi-current">1</span>'
        f' / <span class="pagi-total">{pages}</span></span>'
        f'<button type="button" class="pagi-btn pagi-next" '
        f'aria-label="Next page">›</button>'
        f'</nav>'
    )
from .seo import (
    build_meta_tags, build_jsonld, jsonld_enabled, truncate_description,
)
from .search import (
    html_to_plain,
    build_search_index,
    php_array_literal,
    run_parity_test,
)
from .sitemap import build_sitemap
from .feed import build_feed_document, render_atom, render_rss
from .report import BuildReport, abort
from .cache import (
    BuildCache,
    issue_payload,
    replay_issue,
    replay_warning,
)
from . import __version__ as _SITE_VERSION


# ════════════════════════════════════════════════════════════════
# Build / Error helpers
#
# v0.8.2: 리포트는 **per-Builder 인스턴스** 다 (모듈 전역 `_report` 폐지).
# scripts/report.py 의 docstring 이 v0.5.5 부터 명세해 온 설계 —
# "Builder 가 self.report 를 보유, self._issue / self._warning 로 라우팅" —
# 가 실제로 구현된 시점이 v0.8.2. v0.6.5 ~ v0.8.1 은 모듈 전역 `_report`
# + build() 진입 시 자동 reset() 으로 누적을 가렸으나, 전역 상태라 동시
# 빌드(멀티스레드/프로세스)가 원천 봉쇄돼 있었다. v0.8.2 부터:
#
#   - Builder.__init__ 가 self.report = BuildReport() 보유.
#   - self._issue(scope, target, …) → 글/카테고리 단위 'issue'.
#   - self._warning(scope, target, …) → 'warning' (산출물 정상, 조언).
#   - build() 진입 시 self.report = BuildReport() (인스턴스 재사용 시
#     누적 방지 — v0.6.5 자동 reset 과 같은 의도, 이제 인스턴스 단위).
#   - abort(msg) (report.py) → 시스템 결함. 즉시 sys.exit(1) (전역 무관).
#
# 모듈 레벨 `_render_template` 은 self 가 없으므로 report 를 인자로 받는다
# (호출자가 report=self.report 전달). die()/warn()/issue()/reset_report()
# 모듈 전역 함수는 v0.8.2 에서 제거 — 두 빌드가 상태를 공유하지 않는다.
# ════════════════════════════════════════════════════════════════


def _copy_if_newer(src: Path, dst: Path):
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _image_worker(args):
    """ProcessPoolExecutor 워커 — 이미지 한 장을 webp 변종으로 변환.

    v1.3.0 신설 (B 항목). 모듈-레벨 자유 함수라 Windows spawn 에서도 pickle
    가능. `optimize_image` 가 이미 순수 함수 (사이드 이펙트 = 디스크 쓰기 +
    반환값) 라 워커는 결과만 메인으로 돌려준다. 메인은 image_variants 등록
    과 에러 라우팅 (BuildReport.warning) 을 담당.

    args = (src_file, dst_dir, config). 키워드 인자 패킹이 아닌 위치 튜플 —
    `ProcessPoolExecutor.map` 가 iterable 한 원소를 그대로 함수에 넘기는데,
    map(fn, iterable) 형태에서 fn(item) 호출이므로 단일 인자로 받는다.
    """
    src_file, dst_dir, config = args
    return optimize_image(src=src_file, dst_dir=dst_dir, config=config)


def _remove_empty_dirs(root: Path):
    for dirpath, _dirnames, _filenames in os.walk(root, topdown=False):
        p = Path(dirpath)
        if p == root:
            continue
        try:
            p.rmdir()
        except OSError:
            pass


def _load_template(templates_dir: Path, name: str) -> str:
    path = templates_dir / name
    if not path.exists():
        abort(f'Template not found: {path}')
    return path.read_text(encoding='utf-8')


_UNFILLED_PLACEHOLDER_RE = re.compile(r'\{\{([A-Z_][A-Z0-9_]*)\}\}')


def _render_template(template: str, vars: dict, *,
                     content_vars=None, warn_context=None, report=None) -> str:
    """Substitute `{{KEY}}` placeholders with `vars[KEY]`.

    v0.6.4: 치환 후 남은 `{{XXX}}` 패턴을 빈 문자열로 strip + (warn_context 가
    주어지면) 각 미치환 이름마다 BuildReport.warning 발생. author 가
    `template:` 키로 페이지 종류를 가로지르는 템플릿을 선택했을 때 빌더의
    vars dict 에 해당 키가 없어 발생하는 silent leak 을 가드. 시스템 페이지
    (404 / search) 처럼 빌더가 컨트롤하는 템플릿은 None 으로 호출 — strip
    만 적용.

    v0.6.5: content_vars 인자 추가. 사용자 콘텐츠를 담는 vars (BODY,
    SUBCATEGORY_SECTIONS, ARTICLE_LIST) 의 substitution 을 leftover 검출/strip
    이후로 미룬다. v0.6.4 는 BODY 가 먼저 substitute 된 뒤에 leftover 검출/
    strip 이 돌아서, 사용자 본문에 들어 있던 `{{COPYRIGHT_YEAR}}` 같은 대문자
    placeholder 패턴이 silent 으로 제거되는 회귀가 있었다. 3-pass 로 분리:
      Pass 1 — frame vars (vars - content_vars) 를 모두 substitute.
      Pass 2 — leftover 검출 + strip + warn. content_vars 자리는 아직
               placeholder 형태로 남아 있으므로 검출 대상에서 제외.
      Pass 3 — content_vars 자리에 값 substitute (사용자 본문 안의
               `{{XXX}}` 패턴은 그대로 보존된다).

    warn_context 형식: (scope: str, target: str, location: Path|str|None).
    """
    content_vars = set(content_vars or ())
    # Pass 1: frame vars 만 치환.
    for k, v in vars.items():
        if k in content_vars:
            continue
        template = template.replace('{{' + k + '}}', str(v) if v is not None else '')
    # Pass 2: leftover 검출 — content_vars 자리는 아직 placeholder 라 검출
    # 대상에서 제외. 그 외 미치환 placeholder 만 warn + strip.
    leftovers = sorted({
        name for name in _UNFILLED_PLACEHOLDER_RE.findall(template)
        if name not in content_vars
    })
    # v0.8.2: report 는 per-Builder BuildReport (모듈 전역 폐지). 호출자가
    # report=self.report 로 전달. warn_context 가 주어졌는데 report 가
    # None 이면 (이론상 없음) leftover 경고만 생략 — strip 은 그대로 수행.
    if leftovers and warn_context is not None and report is not None:
        scope, target, location = warn_context
        for name in leftovers:
            report.warning(
                scope, target,
                f"템플릿에 채우지 못한 placeholder 가 발견되어 빈 문자열로 "
                f"strip 되었습니다: {{{{{name}}}}}.",
                location,
            )
    for name in leftovers:
        template = template.replace('{{' + name + '}}', '')
    # Pass 3: content_vars 치환 (사용자 본문의 `{{XXX}}` 가 보존된다).
    for k in content_vars:
        if k not in vars:
            continue
        v = vars[k]
        template = template.replace('{{' + k + '}}', str(v) if v is not None else '')
    return template


# ════════════════════════════════════════════════════════════════
# Builder
# ════════════════════════════════════════════════════════════════

class Builder:
    SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$')
    DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')

    # v1.4.0: 시스템 내재 상수 (옛 site.yaml 키에서 승격).
    # - RESERVED_SLUGS: glob 폴더 (/assets/) + 검색 엔드포인트 (/search.php)
    #   두 시스템 경로와 충돌하는 글 slug 금지. 운영자가 바꿀 사유가 없는
    #   *시스템 내재 제약* 이라 site.yaml 노출이 footgun 였다 (운영자가
    #   'search' 를 지우면 slug=search 글이 만들어져 검색이 깨진다).
    # - DEFAULT_*_TITLE: meta.yaml 을 두지 않는 시스템 페이지의 <title> 본문.
    #   다국어가 필요해지면 i18n 묶음을 도입하지 코드 상수 둘로 흩지 않는다.
    RESERVED_SLUGS = frozenset({'assets', 'search'})
    DEFAULT_ERROR_404_TITLE = 'Not Found'
    DEFAULT_SEARCH_TITLE = 'Search'

    def __init__(self, base_dir: Path, *, enable_cache: bool = True):
        self.base = base_dir
        # v0.8.1: 빌더 일체(scripts/·templates/·assets/·tests/)가 src/ 아래로
        # 재배치됐다. 글 소스(Articles/)·산출물(dist/)·전역 설정(site.yaml)·
        # 캐시(.build_cache/)·리포트(build-report.md)는 그대로 프로젝트 루트
        # (= base_dir) 기준. templates/assets 만 src/ 아래에서 해석한다 —
        # 산출물 경로·내용은 v0.8.0 과 불변.
        self.src_dir = base_dir / 'src'
        self.articles_dir = base_dir / 'Articles'
        self.assets_dir = self.src_dir / 'assets'
        self.templates_dir = self.src_dir / 'templates'
        self.dist = base_dir / 'dist'

        # v0.8.2: per-Builder 빌드 리포트 (모듈 전역 폐지). build() 진입 시
        # 새 BuildReport 로 교체되므로 한 인스턴스를 재사용해 build() 를
        # 여러 번 불러도 issue/warning 이 누적되지 않는다. 두 Builder 가
        # 상태를 공유하지 않아 동시 빌드(멀티스레드/프로세스)가 가능하다.
        self.report: BuildReport = BuildReport()

        self.site: SiteConfig = None
        self.articles: list = []
        self.slug_to_article: dict = {}
        self.categories: dict = {}      # path_tuple → Category
        self.rendered_bodies: dict = {} # slug → plain text body (검색용)
        # v0.4.6: Articles/meta.yaml — 메인페이지 (루트) 의 카테고리-격 설정.
        # 없으면 기본 CategoryMeta (모든 필드 None / 0).
        self.home_meta: CategoryMeta = CategoryMeta()
        # v0.5.1: 이미지 최적화 — 원본 URL → VariantSet (생성된 webp 변종 정보).
        # _sync_assets / _copy_site_assets 에서 채워지고, _render_articles 의
        # HTML 후처리 및 템플릿 컨텍스트 (face_img 등) 에서 참조한다.
        self.image_variants: dict = {}  # URL str → VariantSet
        # v0.5.3: 글의 thumbnail / summary 캐시. _render_articles 단계에서 채워지고
        # _build_categories (gallery layout), _build_feeds (RSS/Atom) 가 참조한다.
        # slug → {'thumb': URL or None, 'summary': str}
        self.article_render_meta: dict = {}
        # v0.7.0: 글 단위 빌드 증분 캐시. enable_cache=False 면 lookup() 이 항상
        # None 이라 v0.6.5 와 동일 동작 (--no-cache 플래그 경로).
        self.cache: BuildCache = BuildCache(base_dir, enabled=enable_cache)
        # v0.7.0: 빌드 종료 시 출력할 캐시 히트/미스 카운트.
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        # v0.7.2: 진행 표시 + 리포트 콘솔 트랜스크립트.
        #   _console      — _emit() 한 마일스톤 라인 누적. 빌드 종료 시
        #                    build-report.md 의 "빌드 진행" 트랜스크립트.
        #   _live_*        — _live() 의 in-place(\r) 진행 라인 상태.
        #                    TTY 가 아니면 (run_diagnostics / 단위 테스트가
        #                    stdout 을 StringIO 로 redirect) _live() 는 no-op
        #                    이라 캡처 로그가 깔끔하고 결정성에 영향 없음.
        self._console: list = []
        self._live_pending: bool = False
        self._live_lastlen: int = 0
        self._live_cols: int = 78
        # v1.3.0: 단계별 timing. _step() 가 직전 단계를 닫고 새 단계를 연다.
        # _step_close() 가 build() 끝에서 마지막 단계를 닫는다. 리포트에만
        # 사용 — dist 산출물에 영향 없음 (결정성 무관).
        self._step_times: list = []
        self._step_current: tuple = ()
        try:
            self._stdout_isatty: bool = bool(sys.stdout.isatty())
        except Exception:
            self._stdout_isatty = False

    # ── 빌드 리포트 라우팅 (v0.8.2: per-Builder) ───────────────
    #
    # scripts/report.py 의 docstring 이 v0.5.5 부터 명세한 self._issue /
    # self._warning 라우팅을 실제로 구현. 옛 모듈 전역 issue()/warn() 의
    # 1:1 대체 — 시그니처·의미 동일, 대상만 self.report.

    def _issue(self, scope: str, target: str, msg: str, location=None):
        """글/카테고리 단위 보완 항목으로 self.report 에 기록.

        호출자는 _issue() 후 산출물에서 해당 글/카테고리를 적절히 처리해야
        한다 (글 단위 skip, 폴백 값 사용 등). _issue() 자체는 빌드 흐름을
        끊지 않는다 (콘텐츠 결함 fail-soft — 시스템 결함만 abort()).
        """
        self.report.issue(scope, target, msg, location)

    def _warning(self, scope: str, target: str, msg: str, location=None):
        """산출물은 정상이지만 살펴볼 사항으로 self.report 에 기록.

        옛 모듈 전역 warn(msg) 의 사이트 전역 조언은
        self._warning('site', '', msg) 로 표현한다 (scope='site').
        """
        self.report.warning(scope, target, msg, location)

    # ── 진행 표시 / 콘솔 로그 (v0.7.2) ─────────────────────────
    #
    # v0.7.2: 큰 사이트에서 빌드가 오래 걸려도 "지금 무엇이 진행 중인지" 가
    # 보이도록 16 단계 헤더 + 무거운 루프 (자산 동기화 / 글 렌더) 의 라이브
    # 카운터를 출력한다. 동시에 _emit() 한 줄들을 _console 에 모아 빌드 종료
    # 시 build-report.md 트랜스크립트로 직렬화한다 (터미널에만 뜨던 안내를
    # 파일로도 남겨달라는 요구). _emit 은 산출물 (dist/) 에 한 글자도 쓰지
    # 않으므로 빌드 결정성에 무관하다.

    @staticmethod
    def _console_print(msg: str, *, end: str = '\n'):
        """콘솔 전용 안전 출력 — 인코딩 깨짐으로 빌드가 죽지 않게 한다.

        Windows 기본 콘솔은 cp949 (`python -m unittest` 처럼 stdout 을
        reconfigure 하지 않으면 cp949) 라 cp949 밖 문자를 print 하면
        UnicodeEncodeError 로 빌드 전체가 중단된다. 진행 라인에는 글
        파일명 (`_live` 의 rel) 처럼 작성자가 통제하는 임의 유니코드가
        섞일 수 있으므로, 인코딩 불가 문자는 'replace' 로 떨어뜨리고
        진행은 계속한다. 리포트 .md 파일은 별도로 utf-8 로 쓰므로 (원문
        보존) 여기 sanitize 는 터미널 표시에만 영향.

        고정 문자열 (`_step` 라벨 등) 은 cp949 안전 문자 (한글 + ASCII +
        U+2500 박스 드로잉) 로만 적어 정상 콘솔에서 '?' 가 안 뜨게 한다.
        """
        try:
            print(msg, end=end, flush=True)
        except UnicodeEncodeError:
            enc = getattr(sys.stdout, 'encoding', None) or 'utf-8'
            safe = msg.encode(enc, 'replace').decode(enc, 'replace')
            sys.stdout.write(safe + end)
            sys.stdout.flush()

    def _emit(self, msg: str = ''):
        """마일스톤 한 줄 — 터미널 + 리포트 콘솔 트랜스크립트에 기록.

        _console 에는 원문(rich)을 그대로 쌓는다 — build-report.md 는
        utf-8 이라 콘솔 sanitize 와 무관하게 원문이 보존된다.
        """
        if self._live_pending:
            # 진행 중이던 in-place 라인을 줄바꿈으로 마감.
            self._console_print('')
            self._live_pending = False
        self._console_print(msg)
        self._console.append(msg)

    def _live(self, msg: str):
        """무거운 루프의 in-place(\\r) 진행 표시 — 터미널(TTY) 전용.

        stdout 이 redirect 된 환경에서는 isatty()=False → no-op. 단계별
        요약은 _emit() 가 항상 남기므로 캡처 로그·리포트는 깔끔하게 유지된다.
        리포트 트랜스크립트에는 남기지 않는다 (_console 에 append 안 함).
        """
        if not self._stdout_isatty:
            return
        line = msg[:self._live_cols]
        self._console_print(line.ljust(self._live_lastlen), end='\r')
        self._live_lastlen = len(line)
        self._live_pending = True

    def _step(self, n: int, label: str):
        """`[ n/16] label` 단계 헤더 (총 16 단계 파이프라인).

        v1.3.0: 호출 시 직전 단계의 경과 시간을 self._step_times 에 기록한 뒤
        새 단계를 연다. 마지막 단계는 build() 종료 직전 self._step_close() 가
        닫는다.
        """
        now = time.perf_counter()
        if self._step_current:
            prev_n, prev_label, prev_start = self._step_current
            self._step_times.append((prev_n, prev_label, now - prev_start))
        self._step_current = (n, label, now)
        self._emit(f'[{n:2d}/16] {label}')

    def _step_close(self):
        """마지막으로 열려 있는 단계를 닫는다 (build() 종료 직전 호출).

        idempotent — 닫을 게 없으면 no-op. _step() 와 짝이 되어 16 단계 모두
        self._step_times 에 기록되도록 한다.
        """
        if self._step_current:
            n, label, start = self._step_current
            self._step_times.append((n, label, time.perf_counter() - start))
            self._step_current = ()

    # ── [1] Config load ──────────────────────────────────────

    def _load_config(self):
        site_yaml = self.base / 'site.yaml'
        if not site_yaml.exists():
            abort(f'site.yaml not found at {site_yaml}')
        raw = yaml_load(site_yaml.read_text(encoding='utf-8'))

        def get(key, default=None):
            return raw.get(key, default)

        # v1.4.0: prev_next 토글 파싱 — site.yaml 의 `prev_next:` 블록의
        # `enabled:` 키 (기본 True). 블록 부재 / dict 가 아니면 기본 활성.
        pn_raw = get('prev_next')
        if isinstance(pn_raw, dict):
            pn_enabled_raw = pn_raw.get('enabled')
            pn_enabled = True if pn_enabled_raw is None else bool(pn_enabled_raw)
        else:
            pn_enabled = True

        self.site = SiteConfig(
            domain=get('domain', 'siheonlee.com'),
            base_url=get('base_url', 'https://siheonlee.com'),
            name=get('name', 'siheonlee.com'),
            main_title=get('main_title') or get('name', 'siheonlee.com'),
            default_author=get('default_author', ''),
            default_og_image=get('default_og_image', '/assets/default-og.png'),
            default_title_prefix=get('default_title_prefix') or '',
            default_title_suffix=get('default_title_suffix') or '',
            copyright_holder=get('copyright_holder', ''),
            copyright_year_start=get('copyright_year_start', 2025),
            # v1.4.0: reserved_slugs / warn_on_underscore_ref /
            # warn_on_missing_asset / error_404_title / search_title 다섯 키는
            # SiteConfig 에서 제거됨 — 시스템 내재 상수 (RESERVED_SLUGS /
            # DEFAULT_ERROR_404_TITLE / DEFAULT_SEARCH_TITLE) 와 항상-경고
            # 행동 고정으로 옮겨졌다. 옛 site.yaml 에 키가 남아 있어도 여기서
            # 더 이상 읽지 않는다 (compat shim 없이 안전 — v1.2.1 의
            # warn_on_stale_updated 제거 선례).
            description_truncate=int(get('description_truncate') or 150),
            robots_txt_main=get('robots_txt_main') or 'User-agent: *\nAllow: /\n',
            # v0.4.5: i18n + 카테고리 페이지네이션 디폴트.
            # v0.4.6: home_* 류 (home_per_page / home_excludes_categories /
            # home_sort) 는 Articles/meta.yaml 로 이전됨 — 더 이상 site.yaml
            # 에서 읽지 않는다. 옛 site.yaml 에 잔존하더라도 조용히 무시.
            lang=str(get('lang') or 'ko'),
            category_per_page=int(get('category_per_page') or 20),
            category_preview_per_page=int(get('category_preview_per_page') or 5),
            # v0.5.1: 이미지 자동 최적화 설정.
            images=self._parse_image_config(get('images') or {}),
            # v0.8.3: schema.org JSON-LD 사이트 전역 토글.
            jsonld=self._parse_jsonld_config(get('jsonld') or {}),
            # v1.1.1: PHP 서명 변수 (imgBox 캡션 `{$name}` 보간).
            php_globals=parse_php_globals(get('php_globals')),
            # v1.1.3: Google AdSense (ads.txt + head_script). 블록 부재 시
            # 기본값(두 필드 모두 빈 문자열 = 자동 비활성) → v1.1.2 와 동일 동작.
            google_adsense=self._parse_adsense_config(get('google_adsense') or {}),
            # v1.4.0: 글 푸터 이전/다음 글 내비게이션 토글.
            prev_next_enabled=pn_enabled,
        )

        # v0.4.6: 사용자가 옛 home_* 키를 site.yaml 에 그대로 두면 알아채지
        # 못한 채 무시될 수 있으므로 한 번 경고 — 마이그레이션 가이드 역할.
        for legacy_key in ('home_per_page', 'home_excludes_categories', 'home_sort'):
            if legacy_key in raw:
                self._warning('site', '', f"site.yaml: '{legacy_key}' 는 v0.4.6 부터 Articles/meta.yaml "
                     f"로 이전되었습니다. site.yaml 에서 제거하고 Articles/meta.yaml "
                     f"의 해당 필드를 사용하세요.")

        # 토크나이저 패리티 검증 (PHP 없으면 워닝만)
        # v0.5.5: 패리티 검증 실패는 시스템 결함 (Py/PHP 토크나이저 동등성
        # 위배 — 검색 인덱스 신뢰도에 직결) 이라 abort 경로로 보낸다.
        # v0.8.2: warn_fn 은 이제 per-Builder report 로 라우팅 (옛 모듈 전역
        # warn(msg) == _report.warning('site','',msg) 의 1:1 어댑터).
        # v1.3.0 (E 항목): 캐시 활성 시 .build_cache/parity.json 에 결과
        # 캐시 — 토크나이저 코드와 PHP 버전이 모두 같으면 다음 빌드에서
        # 18 fixture subprocess 호출 (~3s) 건너뜀. --no-cache 시 매 빌드
        # 풀 검증.
        parity_cache_dir = (
            self.base / '.build_cache' if self.cache.enabled else None
        )
        run_parity_test(self.templates_dir, php_bin='php',
                        warn_fn=lambda m: self._warning('site', '', m),
                        die_fn=abort,
                        cache_dir=parity_cache_dir,
                        scripts_dir=self.src_dir / 'scripts')

        # v0.5.1: 이미지 최적화가 켜져 있는데 Pillow 가 없으면 워닝 (die 가 아닌
        # 워닝 — 이미지가 한 장도 없는 사이트는 빌드가 통과해야 하므로 _sync_assets
        # 단계에서 실제 raster 이미지를 만났을 때 die 한다).
        if self.site.images.enabled and not _HAS_PIL:
            self._warning('site', '', '이미지 최적화가 켜져 있지만 Pillow 가 설치되지 않았습니다. '
                 'raster 이미지를 만나면 빌드가 중단됩니다. '
                 "pip install Pillow 로 설치하거나 site.yaml 의 "
                 "images.enabled 를 false 로 두세요.")

    def _parse_image_config(self, raw) -> ImageConfig:
        """site.yaml 의 `images:` 블록을 ImageConfig 로 파싱 (v0.5.1).

        비어 있거나 모든 키가 없으면 ImageConfig 의 기본값. 알 수 없는 키는
        조용히 무시 (forward compat).
        """
        if not isinstance(raw, dict):
            raw = {}

        def _bool(key, default):
            v = raw.get(key)
            if v is None:
                return default
            return bool(v)

        widths_raw = raw.get('widths')
        if widths_raw is None:
            widths = [400, 800, 1600]
        elif isinstance(widths_raw, list):
            try:
                widths = sorted({int(w) for w in widths_raw if int(w) > 0})
            except (TypeError, ValueError):
                abort(f"site.yaml: images.widths 는 양의 정수 리스트여야 합니다 "
                      f"(받은 값: {widths_raw!r})")
            if not widths:
                abort("site.yaml: images.widths 가 비어 있습니다")
        else:
            abort(f"site.yaml: images.widths 는 리스트여야 합니다 "
                  f"(받은 값: {widths_raw!r})")

        max_width_raw = raw.get('max_width')
        if max_width_raw is None:
            max_width = max(widths)
        else:
            try:
                max_width = int(max_width_raw)
            except (TypeError, ValueError):
                abort(f"site.yaml: images.max_width 는 정수여야 합니다 "
                      f"(받은 값: {max_width_raw!r})")

        quality_raw = raw.get('quality')
        if quality_raw is None:
            quality = 85
        else:
            try:
                quality = int(quality_raw)
            except (TypeError, ValueError):
                abort(f"site.yaml: images.quality 는 정수여야 합니다 "
                      f"(받은 값: {quality_raw!r})")
            if not (0 <= quality <= 100):
                abort(f"site.yaml: images.quality 는 0~100 범위여야 합니다 "
                      f"(받은 값: {quality})")

        sizes = raw.get('default_sizes')
        if sizes is None:
            sizes = "(max-width: 800px) 100vw, 800px"

        return ImageConfig(
            enabled=_bool('enabled', True),
            widths=widths,
            max_width=max_width,
            quality=quality,
            lazy_loading=_bool('lazy_loading', True),
            default_sizes=str(sizes),
        )

    def _parse_jsonld_config(self, raw) -> JsonLdConfig:
        """site.yaml 의 `jsonld:` 블록을 JsonLdConfig 로 파싱 (v0.8.3).

        `_parse_image_config` 와 같은 패턴 — 비어 있거나 dict 가 아니면
        기본값(enabled=True). 알 수 없는 키는 조용히 무시 (forward compat —
        후속 버전이 하위 키를 추가해도 옛 빌더가 깨지지 않음). 값이 없으면
        (`enabled:` 부재) 기본 True 라 옛 site.yaml 도 변경 의무 없이
        JSON-LD 가 켜진다.
        """
        if not isinstance(raw, dict):
            raw = {}
        enabled_raw = raw.get('enabled')
        enabled = True if enabled_raw is None else bool(enabled_raw)
        return JsonLdConfig(enabled=enabled)

    def _parse_adsense_config(self, raw) -> AdSenseConfig:
        """site.yaml 의 `google_adsense:` 블록을 AdSenseConfig 로 파싱 (v1.1.3).

        `_parse_image_config` / `_parse_jsonld_config` 와 같은 패턴 — 비어
        있거나 dict 가 아니면 기본값(두 필드 모두 빈 문자열 = 자동 비활성).
        site.yaml 에 `google_adsense:` 블록이 없으면 옛 빌드와 byte-동일.

        두 필드는 문자열로 정규화 — None/누락은 빈 문자열로 (비활성), 값이
        있으면 str() 캐스팅 후 보존. literal block(`|`)으로 적힌 경우의
        말미 줄바꿈은 yaml 파서가 보존 → ads.txt 가 trailing newline 으로
        끝나는 표준 텍스트 파일 형식을 자연스럽게 따른다.

        v1.1.5: v1.1.4 의 `exclude_pages` 를 `exclude_urls` 로 교체.
        리스트(또는 단일 스칼라)를 받아 str().strip() 후 leading `/` 보정
        → frozenset. 매칭은 case-sensitive (URL 표준) 이고 trailing-slash
        도 그대로 유지 — 운영자가 페이지의 canonical URL 과 정확히 일치
        시키도록 한다. 매칭 안 되는 entry 는 빌드 종료 시점에 BuildReport
        warning 으로 보고 (`_check_exclude_urls`).
        """
        if not isinstance(raw, dict):
            raw = {}
        def _s(key):
            v = raw.get(key)
            return '' if v is None else str(v)
        # ads_txt: trailing newline 보존 (텍스트 파일 표준).
        # head_script: trailing newline strip — yaml literal block `|` 이
        # 자동으로 붙이는 마지막 \n 이 placeholder 치환 시 head 에 빈 줄
        # 하나를 더하는 결과를 방지. yaml flow 인용 ("…") 형태로 적든
        # literal block 으로 적든 head 출력이 일관된다.
        excl_raw = raw.get('exclude_urls')
        if excl_raw is None:
            excl_items = []
        elif isinstance(excl_raw, list):
            excl_items = excl_raw
        else:
            # 스칼라 한 개를 적은 경우 (예: `exclude_urls: /about/`) 도 흡수.
            excl_items = [excl_raw]
        # leading `/` 보정 — `about/` 처럼 적어도 `/about/` 로 정규화.
        # 그 외 trailing slash·대소문자는 손대지 않는다 (URL 의미 보존).
        def _norm(x):
            s = str(x).strip()
            if not s:
                return ''
            return s if s.startswith('/') else '/' + s
        excl = frozenset(
            u for u in (_norm(x) for x in excl_items
                       if x is not None) if u != ''
        )
        return AdSenseConfig(
            ads_txt=_s('ads_txt'),
            head_script=_s('head_script').rstrip('\n'),
            exclude_urls=excl,
        )

    # ── [2] Content scan ──────────────────────────────────────

    def _scan_articles(self):
        if not self.articles_dir.is_dir():
            abort(f'Articles/ directory not found at {self.articles_dir}')

        for root, dirs, files in os.walk(self.articles_dir):
            root_path = Path(root)

            # v0.8.3: 제외 접두 = '_' 또는 '.' (slugs.is_excluded_*). 경로의
            # 어느 세그먼트든 해당하면 그 서브트리 전체를 스캔에서 배제 →
            # .draft 같은 폴더가 글/카테고리로 새지 않는다.
            if is_excluded_path(root_path, self.articles_dir):
                dirs.clear()
                continue

            dirs[:] = [d for d in dirs if not is_excluded_name(d)]

            if 'meta.yaml' not in files:
                continue

            # v0.4.5: meta.yaml 이 있는 폴더가 '글' 인지 '카테고리' 인지 구분.
            # 글 폴더: content.md / content.html 중 하나가 존재.
            # 카테고리 폴더: 둘 다 없음 (이 경우 meta.yaml 은 카테고리 설정).
            # 카테고리 폴더의 meta.yaml 은 _build_category_tree 에서 처리.
            content_md = root_path / 'content.md'
            content_html = root_path / 'content.html'
            if not content_md.exists() and not content_html.exists():
                continue

            rel = root_path.relative_to(self.articles_dir)
            category_path = list(rel.parts[:-1])
            article_folder = rel.parts[-1]

            if content_md.exists() and content_html.exists():
                # 어느 쪽을 우선할지 결정 불가 → 글을 건너뛰고 리포트 기록.
                self._issue(
                    'article', '/'.join(category_path + [article_folder]),
                    'content.md 와 content.html 이 둘 다 존재합니다 '
                    '(한 글에 하나만 두세요).',
                    root_path,
                )
                continue

            content_file = content_md if content_md.exists() else content_html

            article = Article(
                meta=None,
                source_dir=root_path,
                content_file=content_file,
                category_path=category_path + [article_folder],
            )
            self.articles.append(article)

    # ── v0.6.4: 공용 검증/해결 헬퍼 (글·카테고리·홈 공유) ─────────────

    def _validate_stylesheets(self, raw_sheets, source_dir: Path,
                              scope: str, target: str, meta_file: Path):
        """v0.6.4: styles 정수 키 (CSS 파일 상대 경로) 리스트의 공용 검증기.

        글의 _parse_frontmatter 와 카테고리/홈의 _parse_category_meta_file 이
        같은 규칙으로 호출. 각 항목에 대해 — 정규화 (백슬래시→슬래시, leading
        './' 제거), 절대 경로 거부, '..' 거부, 빈 경로 거부, 파일 존재 확인.
        통과한 정규화 경로만 리스트로 반환. 거부된 항목마다 scope/target 의
        issue 발생 (빌드는 계속).
        """
        validated = []
        for rel in raw_sheets:
            rel_norm = str(rel).replace('\\', '/').strip()
            while rel_norm.startswith('./'):
                rel_norm = rel_norm[2:]
            if (not rel_norm
                    or rel_norm.startswith('/')
                    or '..' in rel_norm.split('/')):
                self._issue(
                    scope, target,
                    f"meta.yaml: styles 의 CSS 파일 경로는 페이지 폴더 안의 "
                    f"상대 경로여야 합니다 (받은 값: {rel!r}) — 이 항목 무시.",
                    meta_file,
                )
                continue
            css_path = source_dir / rel_norm
            if not css_path.is_file():
                self._issue(
                    scope, target,
                    f"meta.yaml: styles 에 명시한 CSS 파일이 페이지 폴더에 "
                    f"없습니다: {rel!r} — link 출력 안 함.",
                    meta_file,
                )
                continue
            validated.append(rel_norm)
        return validated

    def _validate_template_ref(self, raw_template, source_dir: Path,
                               scope: str, target: str, meta_file: Path):
        """v0.6.4: meta.yaml 의 template 키 값을 검증 + 정규화.

        반환: (None, None) — 키 부재/검증 실패 → 페이지 종류 기본 템플릿으로
        폴백. (norm: str, origin: str) — origin 은 'templates_dir' (= templates/
        에서) 또는 'page_folder' (= meta.yaml 의 부모 폴더에서).

        검증:
          - None 또는 누락 → (None, None), issue 없음 (정상 케이스).
          - 문자열이 아님 / 빈 문자열 → issue + (None, None).
          - 절대 경로 / '..' 포함 → issue + (None, None).
          - './name' 으로 시작 → page_folder. 그 외 → templates_dir.
        """
        if raw_template is None:
            return (None, None)
        if not isinstance(raw_template, str):
            self._issue(
                scope, target,
                f"meta.yaml: 'template' 은 문자열이어야 합니다 "
                f"(받은 값: {raw_template!r}) — 기본 템플릿으로 폴백.",
                meta_file,
            )
            return (None, None)
        ref = raw_template.strip()
        if not ref:
            self._issue(
                scope, target,
                "meta.yaml: 'template' 이 빈 문자열입니다 — "
                "기본 템플릿으로 폴백.",
                meta_file,
            )
            return (None, None)
        norm = ref.replace('\\', '/')
        if norm.startswith('./'):
            inner = norm[2:]
            if (not inner
                    or inner.startswith('/')
                    or '..' in inner.split('/')):
                self._issue(
                    scope, target,
                    f"meta.yaml: 'template' 의 페이지 폴더 상대 경로가 "
                    f"유효하지 않습니다 ({ref!r}) — 기본 템플릿으로 폴백.",
                    meta_file,
                )
                return (None, None)
            return (norm, 'page_folder')
        if norm.startswith('/') or '..' in norm.split('/'):
            self._issue(
                scope, target,
                f"meta.yaml: 'template' 의 경로가 유효하지 않습니다 "
                f"({ref!r}) — 기본 템플릿으로 폴백.",
                meta_file,
            )
            return (None, None)
        return (norm, 'templates_dir')

    def _resolve_template(self, meta_template, source_dir: Path,
                          default_name: str, scope: str, target: str,
                          meta_file=None) -> str:
        """v0.6.4: meta.yaml 의 template 키를 실제 템플릿 텍스트로 해결.

        meta_template 형식 — _validate_template_ref 의 첫 반환값 (norm) 과
        같은 형식. None 이면 default_name 으로 폴백.

        파일이 없으면 issue + default_name 로 폴백. default_name 자체가
        없으면 abort (시스템 결함).
        """
        if not meta_template:
            return _load_template(self.templates_dir, default_name)
        norm = meta_template
        if norm.startswith('./'):
            inner = norm[2:]
            tpl_path = source_dir / inner
            origin_label = '페이지 폴더'
        else:
            tpl_path = self.templates_dir / norm
            origin_label = 'templates/'
        if not tpl_path.is_file():
            self._issue(
                scope, target,
                f"meta.yaml: 'template' 에 명시한 파일이 {origin_label}에 "
                f"없습니다: {meta_template!r} — 기본 {default_name} 로 폴백.",
                meta_file,
            )
            return _load_template(self.templates_dir, default_name)
        return tpl_path.read_text(encoding='utf-8')

    _COMMON_CSS_LINK = (
        "<link href='/assets/common_template.css' "
        "rel='stylesheet' type='text/css'>"
    )

    def _apply_css_placeholders(self, tpl: str, *,
                                use_common_css: bool,
                                stylesheets_html: str) -> str:
        """v0.6.4: 세 페이지 종류 공용 — {{COMMON_CSS}} / {{PAGE_STYLESHEETS}}
        의 line-eating + 치환을 한 군데서 처리.

        - use_common_css=True → `<link href='/assets/common_template.css' …>` 치환.
        - use_common_css=False → 그 라인 통째로 제거 (ROBOTS_META 와 동일).
        - stylesheets_html 비어있지 않음 → 그대로 치환.
        - stylesheets_html 비어있음 → 그 라인 통째로 제거.

        {{PAGE_STYLES}} (인라인 룰) 은 빈 문자열일 때도 placeholder 라인을
        통째로 제거하지 않음 (v0.6.3 동작 유지 — 4-space 들여쓰기 라인이 남음;
        후처리 strip 대상은 아님 — _render_template 의 vars dict 으로 치환됨).
        """
        if use_common_css:
            tpl = tpl.replace('{{COMMON_CSS}}', self._COMMON_CSS_LINK)
        else:
            tpl = re.sub(
                r'^[ \t]*\{\{COMMON_CSS\}\}[ \t]*\r?\n',
                '', tpl, flags=re.MULTILINE,
            )
        if stylesheets_html:
            tpl = tpl.replace(
                '{{PAGE_STYLESHEETS}}', stylesheets_html.lstrip(),
            )
        else:
            tpl = re.sub(
                r'^[ \t]*\{\{PAGE_STYLESHEETS\}\}[ \t]*\r?\n',
                '', tpl, flags=re.MULTILINE,
            )
        return tpl

    def _apply_adsense_head_placeholder(self, tpl: str, page_url: str) -> str:
        """v1.1.3: 다섯 페이지 공용 — `{{ADSENSE_HEAD}}` line-eating.

        site.yaml 의 `google_adsense.head_script` 가 비어 있으면 placeholder
        가 자리한 라인 자체를 통째로 제거 (ROBOTS_META · JSONLD · COMMON_CSS
        와 동일한 패턴). 비어 있지 않으면 placeholder 를 그대로 두어 호출자
        의 `_render_template` 가 vars_ 의 ADSENSE_HEAD 값으로 raw 치환한다
        (escape 없음 — author 가 명시한 스크립트 문자열을 신뢰).

        호출자는 이 헬퍼로 템플릿을 전처리한 뒤 vars_ 에
        'ADSENSE_HEAD' 키를 항상 채워 둔다 (비어 있으면 빈 문자열).
        비활성일 때는 위에서 라인 자체가 strip 되어 substitution 이
        no-op, 활성일 때는 vars_ 값이 치환된다.

        v1.1.5: v1.1.4 의 `page_type` 인자를 `page_url` 로 교체.
        호출자가 자기 페이지의 canonical URL (site-relative, '/' 로 시작)
        을 넘기고, site.yaml 의 `google_adsense.exclude_urls` 에 정확히
        일치하면 (case-sensitive · trailing-slash 포함) head_script 가
        비어 있을 때와 동일하게 placeholder 라인이 제거된다 = 그 페이지에
        한해 auto-ads 로더가 head 에 들어가지 않음 → 광고 원천 차단.
        매 호출마다 `self._adsense_seen_urls` 에 URL 을 적재 — 빌드 종료
        시점 `_check_exclude_urls` 가 exclude_urls - seen 의 차집합을
        warning 으로 보고 (오타·삭제된 글 감지).
        """
        adsense = self.site.google_adsense
        # 빌드 단위 URL 집합 — 빈 string 이 와도 set 의 자연 처리. 호출자
        # 가 빈 string 을 넘기지는 않지만 방어적으로 (시그니처 신뢰).
        if page_url:
            self._adsense_seen_urls.add(page_url)
        excluded = page_url in adsense.exclude_urls
        if adsense.head_script and not excluded:
            return tpl
        return re.sub(
            r'^[ \t]*\{\{ADSENSE_HEAD\}\}[ \t]*\r?\n',
            '', tpl, flags=re.MULTILINE,
        )

    def _check_exclude_urls(self):
        """v1.1.5: `exclude_urls` 의 매칭 안 되는 entry 를 warning 으로 보고.

        매 페이지 렌더 시 `_apply_adsense_head_placeholder` 가
        `self._adsense_seen_urls` 에 자기 URL 을 적재해 두므로, 이 메서드
        는 빌드 종료 시점 (`_build_search` 직후) 에 호출되어
        exclude_urls - seen 의 차집합을 BuildReport warning 으로 보고한다.
        오타 (예: `/abuot/`) 또는 삭제된 글 (예: 예전엔 있었으나 지금은
        없는 slug) 을 감지한다. 산출물 자체는 정상이라 issue 가 아니라
        warning ("살펴볼 사항") 스코프.
        """
        excl = self.site.google_adsense.exclude_urls
        orphans = sorted(excl - self._adsense_seen_urls)
        for url in orphans:
            self._warning(
                'site', '',
                f'google_adsense.exclude_urls 의 "{url}" 가 빌드 결과 '
                f'어느 페이지 URL 과도 매칭되지 않습니다 — 오타 또는 '
                f'삭제된 글일 가능성 (광고 차단 없음).',
            )

    # ── [3] Frontmatter parse ────────────────────────────────

    def _parse_frontmatter(self):
        """meta.yaml 파싱 → ArticleMeta.

        v0.5.5: 콘텐츠 측 결함은 모두 BuildReport 의 issue 로 라우팅.
          - parse 실패 / 필수 필드 (slug, title, date) 누락 → 글 전체를
            self.articles 에서 제외하고 리포트 기록.
          - 부수 필드 형식 오류 (seo 매핑 아님, tags 리스트 아님 등) →
            폴백값 사용 후 진행, 리포트 기록.
          - seo.description 등 Optional[str] 필드의 빈 문자열은 *보존* —
            None 과 구분된 채 SeoMeta 로 넘어가 build_meta_tags 가 적절히
            처리하고 _render_articles 가 별도로 리포트한다.
        """
        kept = []
        for article in self.articles:
            meta_file = article.source_dir / 'meta.yaml'
            article_target = '/'.join(article.category_path)
            try:
                raw = yaml_load(meta_file.read_text(encoding='utf-8'))
            except Exception as e:
                self._issue(
                    'article', article_target,
                    f'meta.yaml 파싱 오류 — 글이 빌드에서 제외됨: {e}',
                    meta_file,
                )
                continue
            if raw is None:
                raw = {}

            slug = raw.get('slug')
            title = raw.get('title')
            date_str = raw.get('date')

            missing = []
            if not slug:
                missing.append('slug')
            if not title:
                missing.append('title')
            if not date_str:
                missing.append('date')
            if missing:
                self._issue(
                    'article', article_target,
                    f"meta.yaml 의 필수 필드가 비어있습니다 "
                    f"— 글이 빌드에서 제외됨: {', '.join(missing)}",
                    meta_file,
                )
                continue

            date_str = str(date_str)
            updated = str(raw.get('updated')) if raw.get('updated') else None
            noindex_raw = raw.get('noindex')
            noindex = bool(noindex_raw) if noindex_raw is not None else False
            # v0.4.5: 글 단위 lang override. 비우면 site.lang.
            lang_val = raw.get('lang')
            lang = str(lang_val) if lang_val else None

            seo_raw = raw.get('seo') or {}
            if not isinstance(seo_raw, dict):
                self._issue(
                    'article', slug,
                    f"meta.yaml: 'seo' 는 매핑이어야 합니다 "
                    f"(받은 값: {seo_raw!r}) — 빈 seo 로 폴백.",
                    meta_file,
                )
                seo_raw = {}

            # v0.5.5: 빈 문자열을 None 으로 강제 변환하지 않는다.
            # SeoMeta 가 None/''/'text' 세 상태를 보존해 build_meta_tags 가
            # 적절히 처리한다 (None/'' → 메타 태그 누락, '' → 추가로 리포트).
            # v0.6.5: og_type 의 디폴트 강제 ('article') 제거. v0.6.2 설계대로
            # SeoMeta.og_type=None (= author 명시 안 함) 일 때 build_meta_tags
            # 가 page_kind 로 결정 ('article'/'website'). 여기서 또 디폴트를
            # 강제하면 v0.6.2 의 page_kind 분기가 죽은 코드가 된다.
            seo = SeoMeta(
                title_prefix=seo_raw.get('title_prefix'),
                title_suffix=seo_raw.get('title_suffix'),
                description=seo_raw.get('description'),
                author=seo_raw.get('author'),
                canonical=seo_raw.get('canonical'),
                og_title=seo_raw.get('og_title'),
                og_description=seo_raw.get('og_description'),
                og_image=seo_raw.get('og_image'),
                og_image_alt=seo_raw.get('og_image_alt'),
                og_type=seo_raw.get('og_type'),
                twitter_card=seo_raw.get('twitter_card') or 'summary_large_image',
                twitter_image=seo_raw.get('twitter_image'),
                # v0.8.3: 글 단위 JSON-LD opt-out/opt-in. yaml_load 가
                # true/false 를 Python bool 로, 부재는 None 으로 보존하므로
                # 그대로 전달 (None=site 디폴트 / False=이 글만 끔 / True=명시
                # opt-in). jsonld_enabled 가 `is False` 만 특수 처리한다.
                jsonld=seo_raw.get('jsonld'),
            )

            # v0.5.3: tags — 작성자가 직접 적는 주제어 목록.
            # YAML 파서는 inline list (`[a, b]`) 와 block list (`- a` ...) 둘 다 list 로 반환.
            # 정규화: 양끝 공백 trim, 빈 문자열 제거, 중복 제거 (입력 순서 보존),
            #          내부 공백은 그대로 둠 (한국어 다어절 태그 허용).
            tags_raw = raw.get('tags')
            if tags_raw is None:
                tags = []
            elif isinstance(tags_raw, list):
                seen = set()
                tags = []
                for item in tags_raw:
                    if item is None:
                        continue
                    s = str(item).strip()
                    if not s or s in seen:
                        continue
                    seen.add(s)
                    tags.append(s)
            else:
                self._issue(
                    'article', slug,
                    f"meta.yaml: 'tags' 는 리스트여야 합니다 "
                    f"(받은 값: {tags_raw!r}) — 빈 리스트로 폴백.",
                    meta_file,
                )
                tags = []

            # v0.5.4: nav_priority — 글이 톱레벨일 때만 의미 (예: About).
            nav_priority_raw = raw.get('nav_priority')
            if nav_priority_raw is None:
                nav_priority = 0
            else:
                try:
                    nav_priority = int(nav_priority_raw)
                except (TypeError, ValueError):
                    self._issue(
                        'article', slug,
                        f"meta.yaml: 'nav_priority' 는 정수여야 합니다 "
                        f"(받은 값: {nav_priority_raw!r}) — 0 으로 폴백.",
                        meta_file,
                    )
                    nav_priority = 0

            # v0.6.3: styles 키가 두 채널로 분리 — 정수 키 = 외부 CSS 파일
            # 상대 경로, 문자열 키 = 인라인 룰. v0.6.4 부터 공용 헬퍼
            # _validate_stylesheets 가 검증 + 정규화 담당 (카테고리/홈도 동일
            # 헬퍼 사용).
            raw_sheets, rules = normalize_styles(raw.get('styles'))
            validated_sheets = self._validate_stylesheets(
                raw_sheets, article.source_dir,
                scope='article', target=slug, meta_file=meta_file,
            )

            # v0.6.3: use_common_css — common_template.css link 출력 여부.
            # 기본 True (= 모든 옛 글이 변경 의무 없음). False 면 link 태그
            # 자체가 head 에서 출력되지 않음.
            use_common_css_raw = raw.get('use_common_css')
            if use_common_css_raw is None:
                use_common_css = True
            else:
                use_common_css = bool(use_common_css_raw)

            # v0.6.4: template 키 — 글이 사용할 템플릿 파일.
            template_norm, _origin = self._validate_template_ref(
                raw.get('template'), article.source_dir,
                scope='article', target=slug, meta_file=meta_file,
            )

            article.meta = ArticleMeta(
                slug=slug,
                title=title,
                date=date_str,
                updated=updated,
                noindex=noindex,
                lang=lang,
                seo=seo,
                styles=rules,
                stylesheets=validated_sheets,
                use_common_css=use_common_css,
                template=template_norm,
                tags=tags,
                nav_priority=nav_priority,
            )
            kept.append(article)

        # 빌드에서 제외된 글은 articles 에서 제거 — 후속 단계가 invalid meta 를
        # 만나지 않도록.
        self.articles = kept

    # ── [4] Validation + category tree ───────────────────────

    def _validate(self):
        """v0.5.5: slug/date 검증 실패는 글 단위 issue 로 기록하고 빌드에서
        제외 (산출물 누락). 빌드는 계속 진행.
        """
        seen_slugs = {}
        kept = []

        for article in self.articles:
            m = article.meta
            meta_path = article.source_dir / 'meta.yaml'
            keep_this = True

            if not self.SLUG_RE.match(m.slug):
                self._issue(
                    'article', m.slug,
                    f'slug 정규식 불일치: {m.slug!r} — 글이 빌드에서 제외됨.',
                    meta_path,
                )
                keep_this = False

            # v1.4.0: site.yaml reserved_slugs → Builder.RESERVED_SLUGS 상수.
            if m.slug in self.RESERVED_SLUGS:
                self._issue(
                    'article', m.slug,
                    f'slug 예약어: {m.slug!r} — 시스템 경로 '
                    f'({"/" + m.slug + "/" if m.slug == "assets" else "/search.php"}) '
                    f'와 충돌. 글이 빌드에서 제외됨.',
                    meta_path,
                )
                keep_this = False

            if m.slug in seen_slugs:
                other = seen_slugs[m.slug]
                self._issue(
                    'article', m.slug,
                    f"slug 중복: {m.slug!r} — 뒤늦게 발견된 쪽의 글이 "
                    f"빌드에서 제외됨 (먼저 발견된 글: {other}).",
                    meta_path,
                )
                keep_this = False
            else:
                seen_slugs[m.slug] = article.source_dir

            if not self.DATE_RE.match(m.date):
                self._issue(
                    'article', m.slug,
                    f'date 형식 오류: {m.date!r} (YYYY-MM-DD 형식 필요) '
                    f'— 글이 빌드에서 제외됨.',
                    meta_path,
                )
                keep_this = False

            if m.updated:
                if not self.DATE_RE.match(m.updated):
                    self._issue(
                        'article', m.slug,
                        f'updated 형식 오류: {m.updated!r} — updated 를 '
                        f'무시하고 진행.',
                        meta_path,
                    )
                    m.updated = None
                elif m.updated < m.date:
                    self._issue(
                        'article', m.slug,
                        f'updated ({m.updated}) 가 date ({m.date}) 보다 '
                        f'앞섭니다 — 그대로 진행하지만 의도 확인 권장.',
                        meta_path,
                    )

            if keep_this:
                kept.append(article)

        self.articles = kept

        self.slug_to_article = {a.meta.slug: a for a in self.articles}

        # v0.4.6: Articles/meta.yaml (메인페이지 카테고리-격 설정) 파싱.
        self._load_home_meta()

        self._build_category_tree()

        # 글 slug ↔ 톱레벨 카테고리 slug 충돌 검증 (v0.4.2).
        # 둘 다 dist/{slug}/index.html 자리에 떨어지므로 — 충돌하는 글을
        # 빌드에서 제외 (카테고리가 우선) + 리포트.
        cat_slugs = {
            cat.slug: cat
            for cat in self.categories.values()
            if len(cat.path) == 1
        }
        filtered = []
        for article in self.articles:
            if article.meta.slug in cat_slugs:
                cat = cat_slugs[article.meta.slug]
                self._issue(
                    'article', article.meta.slug,
                    f"slug 충돌 (글 ↔ 카테고리): {article.meta.slug!r} — "
                    f"카테고리 폴더 Articles/{'/'.join(cat.path)} 와 같은 "
                    f"slug 라 글이 빌드에서 제외됨.",
                    article.source_dir / 'meta.yaml',
                )
                continue
            filtered.append(article)
        self.articles = filtered
        self.slug_to_article = {a.meta.slug: a for a in self.articles}

        for cat in self.categories.values():
            all_articles = self._collect_articles(cat)
            if not all_articles:
                self._warning(
                    'category', '/'.join(cat.path),
                    '이 카테고리에 글이 하나도 없습니다 (빈 카테고리).',
                    self.articles_dir.joinpath(*cat.path),
                )

    def _build_category_tree(self):
        """v0.4.5: 카테고리 폴더의 meta.yaml 도 파싱한다.

        v0.4.0: _meta.yaml 오버라이드 코드 경로 제거.
        한국어 등 비ASCII 폴더명은 slugs.category_slug_from_name 이
        결정론적으로 ASCII 코드포인트 hex 로 변환한다. 경고는 한 번만 (폴더당).
        v0.4.5 에서 워닝 메시지를 보강해, 어떤 폴더명이 어떤 hex slug 로
        변환되었는지 빌드 로그에서 한눈에 보이도록 한다.
        """
        cat_paths = set()
        for article in self.articles:
            cat = article.category_path[:-1]
            for depth in range(1, len(cat) + 1):
                cat_paths.add(tuple(cat[:depth]))

        warned_folders = set()

        def to_slug(folder_name: str, full_path_for_warn) -> str:
            s = category_slug_from_name(folder_name)
            if not s:
                # 빈 카테고리 slug — 빌드는 계속 (해당 카테고리는 산출물에서
                # 자연스럽게 누락). 작성자가 폴더명을 보완해야 함.
                self._issue(
                    'category', '/'.join(full_path_for_warn),
                    f'카테고리 폴더명이 빈 slug 로 변환됩니다: {folder_name!r} '
                    f'— 카테고리가 빌드되지 않을 수 있습니다.',
                    self.articles_dir.joinpath(*full_path_for_warn),
                )
            if has_non_ascii(folder_name) and folder_name not in warned_folders:
                self._warning(
                    'category', '/'.join(full_path_for_warn),
                    f"URL slug 에 비ASCII 문자 포함: '{folder_name}' → '{s}'. "
                    f"빌드는 정상 진행되었으나, URL 가독성/공유성을 위해 "
                    f"폴더명을 ASCII (영문/숫자/하이픈) 로 바꾸는 것을 권장합니다.",
                    self.articles_dir.joinpath(*full_path_for_warn),
                )
                warned_folders.add(folder_name)
            return s

        for path_tuple in sorted(cat_paths, key=lambda p: (len(p), p)):
            folder_name = path_tuple[-1]
            slug = to_slug(folder_name, list(path_tuple))

            slug_path = [
                to_slug(part, list(path_tuple[:i + 1]))
                for i, part in enumerate(path_tuple)
            ]

            cat = Category(
                folder_name=folder_name,
                slug=slug,
                path=list(path_tuple),
                slug_path=slug_path,
                meta=self._parse_category_meta(path_tuple),
            )
            self.categories[path_tuple] = cat

        for path_tuple, cat in self.categories.items():
            if len(path_tuple) > 1:
                parent_path = path_tuple[:-1]
                if parent_path in self.categories:
                    parent = self.categories[parent_path]
                    if cat not in parent.children:
                        parent.children.append(cat)

        for article in self.articles:
            cat_path = tuple(article.category_path[:-1])
            if cat_path in self.categories:
                cat = self.categories[cat_path]
                if article not in cat.articles:
                    cat.articles.append(article)

    def _parse_category_meta(self, path_tuple) -> CategoryMeta:
        """`Articles/<카테고리경로>/meta.yaml` 파일 (있으면) 파싱.

        없으면 모든 필드가 None 인 기본 CategoryMeta.
        per_page / preview_per_page 가 None 이면 사이트 디폴트가 적용됨.
        """
        cat_dir = self.articles_dir.joinpath(*path_tuple)
        return self._parse_category_meta_file(cat_dir / 'meta.yaml')

    def _parse_category_meta_file(self, meta_file: Path,
                                  scope: str = 'category') -> CategoryMeta:
        """임의 경로의 meta.yaml 을 CategoryMeta 로 파싱 (v0.4.6 helper).

        `Articles/meta.yaml` (루트 = 메인페이지) 와 카테고리 폴더의 meta.yaml
        둘 다에 동일한 파싱 로직 적용.

        v0.5.4: `title` / `seo` / `nav_priority` 도 파싱한다. `title` 은
        페이지 자체의 `<title>` 본문이고, `seo.title_prefix` / `seo.title_suffix`
        는 site 디폴트를 오버라이드한다. 글 폴더의 meta.yaml 이 우연히 이
        함수로 들어와도 (`_scan_articles` 가 미리 거른 경우만) `slug` / `date`
        가 있으면 빈 CategoryMeta 로 폴백 (안전망). 단 `title` 만 있는 경우는
        카테고리/홈 페이지의 정상적인 title override 로 취급한다.

        v0.6.4: scope 인자 추가 — 호출자가 'home' (홈 = Articles/meta.yaml) 또는
        'category' (카테고리 폴더의 meta.yaml) 를 지정. issue 분류 일관성용.
        styles 의 정수 키 (외부 CSS 파일 경로) 가 v0.6.4 부터 카테고리/홈에서도
        유효해짐 — 글과 같은 _validate_stylesheets 헬퍼로 검증. use_common_css
        토글과 template 키도 글과 같은 의미로 파싱.
        """
        if not meta_file.exists():
            return CategoryMeta()

        # issue 의 target 은 페이지 종류 별로 다름 — home 은 '' (단일), category
        # 는 폴더명. 동일 폴더 안의 모든 issue 가 한 헤더 아래 묶이도록 일관.
        if scope == 'home':
            target = ''
        else:
            target = str(meta_file.parent.name)

        try:
            raw = yaml_load(meta_file.read_text(encoding='utf-8'))
        except Exception as e:
            self._issue(
                scope, target,
                f'meta.yaml 파싱 오류 — 기본 CategoryMeta 로 폴백: {e}',
                meta_file,
            )
            return CategoryMeta()

        if raw is None:
            raw = {}
        # v0.5.4: 글 meta.yaml 의 외형은 `slug` + `date` 의 동시 존재로 식별
        # (둘 다 ArticleMeta 의 필수 필드). 한쪽만 있는 건 카테고리 meta.yaml
        # 에서의 오타/실수일 수 있으므로 die 가 적절할 수 있겠지만, 이 함수는
        # 카테고리 트리 구축 단계라 die 하면 정보가 적다 — 이번 버전에서는
        # 그대로 빈 CategoryMeta 폴백을 유지하며, `title` 은 카테고리에서도
        # 유효한 키로 통과시킨다.
        if 'slug' in raw and 'date' in raw:
            return CategoryMeta()

        # v0.5.5: 카테고리 meta.yaml 의 형식 오류는 모두 폴백값으로 진행하고
        # 리포트만 기록 (빌드 중단 없음).

        per_page = raw.get('per_page')
        preview = raw.get('preview_per_page')
        layout = raw.get('layout') or 'list'
        lang_val = raw.get('lang')
        styles_raw = raw.get('styles')
        # v0.4.6: priority. 빈값/누락이면 0. 정수만 허용.
        priority_raw = raw.get('priority')
        if priority_raw is None:
            priority = 0
        else:
            try:
                priority = int(priority_raw)
            except (TypeError, ValueError):
                self._issue(
                    scope, target,
                    f"meta.yaml: 'priority' 는 정수여야 합니다 "
                    f"(받은 값: {priority_raw!r}) — 0 으로 폴백.",
                    meta_file,
                )
                priority = 0

        # v0.4.6: excludes_categories. 홈 (Articles/meta.yaml) 에서만 의미를
        # 가진다 — 카테고리 meta.yaml 에 들어있어도 파싱만 되고 사용되지 않음.
        excludes_raw = raw.get('excludes_categories')
        if excludes_raw is None:
            excludes = []
        elif isinstance(excludes_raw, list):
            excludes = [str(x) for x in excludes_raw]
        else:
            self._issue(
                scope, target,
                f"meta.yaml: 'excludes_categories' 는 리스트여야 합니다 "
                f"(받은 값: {excludes_raw!r}) — 빈 리스트로 폴백.",
                meta_file,
            )
            excludes = []

        # v0.5.4: title (페이지 <title> 본문 override).
        title_val = raw.get('title')
        title = str(title_val) if title_val else None

        # v0.5.4: seo (글의 SeoMeta 와 동일 스키마).
        seo_raw = raw.get('seo') or {}
        if not isinstance(seo_raw, dict):
            self._issue(
                scope, target,
                f"meta.yaml: 'seo' 는 매핑이어야 합니다 "
                f"(받은 값: {seo_raw!r}) — 빈 seo 로 폴백.",
                meta_file,
            )
            seo_raw = {}

        # v0.5.5: 빈 문자열 보존 (글 SeoMeta 와 동일 정책).
        # v0.6.5: og_type 의 디폴트 강제 ('website') 제거. build_meta_tags 가
        # page_kind 로 결정하도록 None 을 그대로 보존 (글 _parse_frontmatter 와
        # 같은 정책).
        seo = SeoMeta(
            title_prefix=seo_raw.get('title_prefix'),
            title_suffix=seo_raw.get('title_suffix'),
            description=seo_raw.get('description'),
            author=seo_raw.get('author'),
            canonical=seo_raw.get('canonical'),
            og_title=seo_raw.get('og_title'),
            og_description=seo_raw.get('og_description'),
            og_image=seo_raw.get('og_image'),
            og_image_alt=seo_raw.get('og_image_alt'),
            og_type=seo_raw.get('og_type'),
            twitter_card=seo_raw.get('twitter_card') or 'summary_large_image',
            twitter_image=seo_raw.get('twitter_image'),
            # v0.8.3: 카테고리/홈 SeoMeta 도 글과 같은 스키마 유지를 위해
            # jsonld 를 파싱 (대칭성). 단 JSON-LD 출력은 글 페이지에서만
            # 하므로 (article.html 만 {{JSONLD}} 보유) 카테고리/홈에서는
            # 파싱만 되고 사용되지 않는다 — seo.title_prefix 외 다른 seo
            # 필드들과 같은 forward-compat 취급.
            jsonld=seo_raw.get('jsonld'),
        )

        # v0.5.4: nav_priority — 톱레벨 nav 정렬 키 (priority 와 별개 축).
        nav_priority_raw = raw.get('nav_priority')
        if nav_priority_raw is None:
            nav_priority = 0
        else:
            try:
                nav_priority = int(nav_priority_raw)
            except (TypeError, ValueError):
                self._issue(
                    scope, target,
                    f"meta.yaml: 'nav_priority' 는 정수여야 합니다 "
                    f"(받은 값: {nav_priority_raw!r}) — 0 으로 폴백.",
                    meta_file,
                )
                nav_priority = 0

        # v0.6.4: styles 의 정수 키 (외부 CSS 파일 경로) + 문자열 키 (인라인
        # 룰) 두 채널 — 글과 동일. 검증은 _validate_stylesheets 공용 헬퍼.
        # source_dir 은 meta.yaml 의 부모 폴더 — 홈은 Articles/, 카테고리는
        # Articles/<path>/.
        raw_sheets, cat_rules = normalize_styles(styles_raw)
        validated_sheets = self._validate_stylesheets(
            raw_sheets, meta_file.parent,
            scope=scope, target=target, meta_file=meta_file,
        )

        # v0.6.4: use_common_css 토글. 기본 True (= 모든 옛 페이지가 변경
        # 의무 없음). 글의 ArticleMeta.use_common_css 와 같은 의미.
        use_common_css_raw = raw.get('use_common_css')
        if use_common_css_raw is None:
            use_common_css = True
        else:
            use_common_css = bool(use_common_css_raw)

        # v0.6.4: template 키 — 카테고리/홈도 자기 템플릿 선택 가능. 검증은
        # 공용 _validate_template_ref. 페이지 종류 가로지르기 시 발생할 수
        # 있는 silent leak 은 _render_template 후처리가 가드 (warning).
        template_norm, _origin = self._validate_template_ref(
            raw.get('template'), meta_file.parent,
            scope=scope, target=target, meta_file=meta_file,
        )

        return CategoryMeta(
            per_page=int(per_page) if per_page is not None else None,
            preview_per_page=int(preview) if preview is not None else None,
            layout=str(layout),
            lang=str(lang_val) if lang_val else None,
            styles=cat_rules,
            stylesheets=validated_sheets,
            use_common_css=use_common_css,
            template=template_norm,
            priority=priority,
            excludes_categories=excludes,
            title=title,
            seo=seo,
            nav_priority=nav_priority,
        )

    def _load_home_meta(self):
        """v0.4.6: Articles/meta.yaml 파싱 (메인페이지의 카테고리-격 설정).

        없으면 모든 필드가 기본값인 CategoryMeta. _build_category_tree 와
        독립적으로 동작 — Articles/ 루트는 self.categories 의 path_tuple ()
        로 들어가지 않는다 (루트는 카테고리가 아니라 사이트 자체).
        """
        self.home_meta = self._parse_category_meta_file(
            self.articles_dir / 'meta.yaml',
            scope='home',
        )

    # v0.4.6: Articles/meta.yaml 이 통째로 없거나 per_page 가 비어 있을 때
    # 적용되는 코드 디폴트. site.yaml 에서 home_per_page 가 제거된 자리.
    # v1.0.2: 사용자 결정으로 5 → 10 (메인페이지 Recent posts 기본 출력
    # 개수). 정본 Articles/meta.yaml 은 per_page 를 명시(=10)하므로 이
    # 상수는 그때 dormant — dist 영향 0, per_page 미설정 시에만 발효.
    HOME_PER_PAGE_DEFAULT = 10

    def _home_per_page(self) -> int:
        """메인페이지 Recent posts 의 페이지당 글 수.

        Articles/meta.yaml 의 per_page 가 있으면 그 값, 없으면 코드 디폴트
        (Builder.HOME_PER_PAGE_DEFAULT).
        """
        if self.home_meta.per_page is not None:
            return self.home_meta.per_page
        return self.HOME_PER_PAGE_DEFAULT

    def _category_per_page(self, cat: Category) -> int:
        """카테고리 자기 인덱스 페이지의 페이지당 글 수."""
        if cat.meta.per_page is not None:
            return cat.meta.per_page
        return self.site.category_per_page

    def _category_preview_per_page(self, cat: Category) -> int:
        """카테고리가 상위 인덱스 페이지의 section 으로 임베드될 때의 페이지당 글 수."""
        if cat.meta.preview_per_page is not None:
            return cat.meta.preview_per_page
        return self.site.category_preview_per_page

    def _collect_articles(self, cat: Category) -> list:
        result = list(cat.articles)
        for child in cat.children:
            result.extend(self._collect_articles(child))
        return result

    # ── [5] Article render + output ──────────────────────────

    def _copyright_year(self) -> str:
        return str(datetime.date.today().year)

    # ── Title fallback chain (v0.5.4) ─────────────────────────
    #
    # 글, 홈, 카테고리, 404, search 모두 동일한 폴백 규칙으로 `<title>` 을
    # 만든다: `{prefix}{title}{suffix}`. prefix/suffix 는 페이지 단위 override
    # 가 없으면 site.default_title_prefix / default_title_suffix.
    #
    # 페이지별 title 본문 결정:
    #   글       — m.title (글 폴더명과 무관한 글 자체의 제목)
    #   홈       — home_meta.title 이 있으면 그 값, 없으면 site.name
    #   카테고리 — cat.meta.title 이 있으면 그 값, 없으면 cat.folder_name
    #   404      — site.error_404_title
    #   search   — site.search_title
    #
    # 글의 prefix/suffix 폴백 체인은 seo.py 의 build_meta_tags 가 담당하고,
    # 나머지 페이지는 _wrap_page_title 이 같은 규칙을 적용한다.

    def _wrap_page_title(self, body: str, seo_override: SeoMeta = None) -> str:
        """주어진 본문 텍스트를 default_title_prefix / suffix 로 감싸 반환.

        seo_override 가 있고 title_prefix / title_suffix 가 None 이 아니면
        site 디폴트 대신 그 값을 사용. 글의 build_meta_tags 와 동일한 규칙.

        v0.6.2 변경: 글/홈/카테고리는 모두 build_meta_tags 가 반환하는
        full_title 을 직접 사용한다. 이 헬퍼는 meta.yaml 이 없는 시스템
        페이지 (404 / search) 에서만 쓰인다 — 그 두 페이지는 description /
        og_* 등의 메타 태그를 출력하지 않으므로 build_meta_tags 를 호출하지
        않고 prefix/suffix 폴백 체인만 적용하면 충분.
        """
        prefix = self.site.default_title_prefix
        suffix = self.site.default_title_suffix
        if seo_override is not None:
            if seo_override.title_prefix is not None:
                prefix = seo_override.title_prefix
            if seo_override.title_suffix is not None:
                suffix = seo_override.title_suffix
        return f'{prefix}{body}{suffix}'

    def _check_page_description(
        self,
        *,
        seo: SeoMeta,
        page_kind: str,
        location,
        slug: str = '',
    ):
        """페이지의 seo.description 누락/빈 문자열 검사 (v0.6.2).

        글의 _render_articles 에서 적용하던 description 필수화 정책을 홈/
        카테고리 페이지에도 동일하게 적용. 누락(None) 또는 빈 문자열('') 이면
        BuildReport 의 issue 에 기록 (빌드는 통과 + meta 태그 누락).

        page_kind 는 issue scope 로 그대로 사용된다 ('home' / 'category').
        location 은 그 페이지의 meta.yaml 경로 (홈은 Articles/meta.yaml,
        카테고리는 Articles/<path>/meta.yaml).
        """
        desc_val = seo.description
        if desc_val is None:
            self._issue(
                page_kind, slug,
                "meta.yaml: 'seo.description' 필드가 없습니다 "
                "— 외부 노출용 한 줄 설명을 작성해주세요. "
                "(description / og:description / twitter:description 메타 "
                "태그가 누락됩니다.)",
                location,
            )
        elif desc_val == '':
            self._issue(
                page_kind, slug,
                "meta.yaml: 'seo.description' 이 빈 문자열입니다 "
                "— 외부 노출용 한 줄 설명을 작성해주세요. "
                "(description 메타 태그가 누락됩니다.)",
                location,
            )

    def _top_level_entries(self) -> list:
        """Articles/ 직속 항목을 [(folder_name, slug, is_article), ...] 로 반환.

        v0.4.5: 카테고리 폴더에도 meta.yaml 이 있을 수 있으므로, meta.yaml
        존재만으로 '글' 인지 판단하지 않는다. _scan_articles 에서 이미
        분류한 self.articles 리스트와 source_dir 매칭으로 결정.

        v0.5.4: 'About 최상단 하드코딩' 폐기. 모든 톱레벨 항목 (글 + 카테고리)
        의 `nav_priority` 로 정렬한다. 값이 클수록 먼저, 같은 값끼리는 폴더명
        알파벳 순. nav_priority 가 없는 (= 기본 0) 항목들은 알파벳 순 폴백.
        About 을 nav 최상단에 두고 싶으면 Articles/About/meta.yaml 에
        `nav_priority: 100` 같은 큰 값을 명시한다.
        """
        if not self.articles_dir.is_dir():
            return []

        # 항목별 (folder_name, slug, is_article, nav_priority) 4-튜플.
        # 정렬 후 외부에는 처음 3개만 노출.
        raw_entries = []
        for child in self.articles_dir.iterdir():
            if not child.is_dir():
                continue
            # v0.8.3: glob 직속 순회라 _scan_articles 의 제외와 별개로
            # 여기서도 '_'/'.' 접두 폴더를 nav 후보에서 직접 배제 (글 없는
            # 카테고리-격 폴더도 nav 에 오를 수 있으므로 단독 가드 필요).
            if is_excluded_name(child.name):
                continue
            article = next(
                (a for a in self.articles if a.source_dir == child),
                None,
            )
            if article is not None:
                raw_entries.append((
                    child.name, article.meta.slug, True,
                    article.meta.nav_priority,
                ))
            else:
                key = (child.name,)
                cat = self.categories.get(key)
                slug = cat.slug if cat else category_slug_from_name(child.name)
                nav_pri = cat.meta.nav_priority if cat else 0
                raw_entries.append((child.name, slug, False, nav_pri))

        raw_entries.sort(key=lambda e: (-e[3], e[0]))
        return [(name, slug, is_art) for (name, slug, is_art, _pri) in raw_entries]

    def _nav_links_html(self) -> str:
        entries = self._top_level_entries()
        if not entries:
            return ''
        parts = []
        for folder, slug, _is_article in entries:
            parts.append(f"<a href='/{slug}/'>{escape_html(folder)}</a>")
        return '<span>|</span> '.join(parts)

    def _nav_tracker_for_path(self, breadcrumb_parts: list) -> str:
        html = "<a href='/'>Home</a>"
        for label, url in breadcrumb_parts:
            label_safe = escape_html(label)
            if url is None:
                html += (f"<a onClick='window.location.reload()' "
                         f"style='cursor: pointer;'> / {label_safe} </a>")
            else:
                html += f"<a href='{url}'> / {label_safe}</a>"
        return html

    def _top_category_for_article(self, article: 'Article'):
        if not article.category_path or len(article.category_path) < 2:
            return None
        top = (article.category_path[0],)
        return self.categories.get(top)

    def _ancestor_categories(self, path_parts):
        """path_parts (Articles/ 기준 폴더명 리스트, 톱→부모 순) 를 등록된
        Category 객체 리스트로 해석한다. 각 접두 경로
        (path_parts[:1], [:2], …) 를 카테고리 트리에서 찾는다. 미등록
        깊이는 건너뛴다 — 정본 콘텐츠에서는 글/카테고리의 모든 접두
        경로가 Category 로 등록돼 있다(빌더의 카테고리 트리)."""
        out = []
        for k in range(1, len(path_parts) + 1):
            c = self.categories.get(tuple(path_parts[:k]))
            if c is not None:
                out.append(c)
        return out

    def _crumb_parts_for(self, *, ancestors, leaf):
        """nav-tracker HTML 과 JSON-LD BreadcrumbList 의 단일 공유 crumb 소스.

        파라미터
            ancestors : 톱레벨→최근접 부모 순의 조상 Category 리스트.
                        각 조상은 자기 *중첩* 카테고리 URL
                        ('/' + '/'.join(cat.slug_path) + '/') 로 링크된다.
            leaf      : (이름, url|None) — 현재 페이지(말단) 항목.

        글 페이지·카테고리 페이지(톱/서브) 세 호출자가 공유한다.
        빵부스러기 의미 정확성:
          · Bug A 회피 — 모든 중간 조상이 톱레벨 URL(top_url)이 아니라
            자기 중첩 카테고리 URL 로 링크한다 (톱레벨 조상의 중첩
            URL 은 '/{top.slug}/').
          · Bug B 회피 — 글 호출자가 leaf=(글 제목, None) 을 넘긴다
            (말단 이름이 폴더명이 아니라 글 제목 = Article.headline).
            카테고리 페이지 호출자는 K2(폴더명 유지)에 따라 leaf 에
            cat.folder_name 을 그대로 넘긴다.
        조상이 0개면(톱레벨 글 / 톱 카테고리 페이지) crumb 은 [leaf]
        뿐 — 항목 2개 미만이라 JSON-LD BreadcrumbList 노드는 생략된다
        (build_jsonld 의 기존 정책 유지). nav-tracker HTML 은 그대로
        한 줄 렌더되며 말단 텍스트만 (글이면) 제목이 된다."""
        crumb_parts = [
            (anc.folder_name, '/' + '/'.join(anc.slug_path) + '/')
            for anc in ancestors
        ]
        crumb_parts.append(leaf)
        return crumb_parts

    # ── v1.4.0: prev/next sibling navigation ──────────────────
    #
    # 사이트 전역 토글 (site.yaml prev_next.enabled, 기본 True). sibling 풀
    # = 같은 부모 폴더의 다른 글 (Articles/Blog/A 의 sibling 은 같은 Blog/
    # 의 형제 글). noindex 글은 풀에서 제외 (UI 내비게이션은 색인 정책과
    # 별개라 자기 자신은 표시 가능하지만 *남의* prev/next 에는 안 잡힘).
    # 정렬은 date asc + slug tiebreak — 의미: prev = 시간상 *과거* 글,
    # next = 시간상 *미래* 글 (관습적 블로그 패턴).
    #
    # 글의 본문 끝 (body_html 의 </section> 뒤) 에 nav 한 줄로 append.
    # 템플릿에 새 placeholder 를 두지 않고 본문 안에 넣는 이유 = 캐시 일관성:
    # _render_articles 가 만드는 page_html 이 그대로 .build_cache/articles/
    # <slug>.<ext> 에 저장되므로, 캐시 hit 시에도 이 nav 가 함께 복원되어
    # 결정성·byte-동일성이 자연 유지된다.

    def _build_sibling_index(self) -> dict:
        """parent_path_tuple -> 같은 부모의 (자신 포함) non-noindex 글 list,
        date 오름차순 정렬 (동률 시 slug). _render_articles 진입 시 한 번
        만들고 글마다 _prev_next_for 가 참조한다.
        """
        by_parent = {}
        for a in self.articles:
            if a.meta.noindex:
                continue
            parent = tuple(a.category_path[:-1])
            by_parent.setdefault(parent, []).append(a)
        for k in by_parent:
            by_parent[k].sort(key=lambda x: (x.meta.date, x.meta.slug))
        return by_parent

    def _prev_next_for(self, article: 'Article', sibs_by_parent: dict):
        """(prev_article|None, next_article|None) — 둘 다 None 이면 nav 미출력.

        자기 자신이 noindex 면 sibs_by_parent 풀에 없어 자연스럽게 (None, None).
        sibling 이 한 명도 없는 단일 글 카테고리도 (None, None).
        """
        parent = tuple(article.category_path[:-1])
        sibs = sibs_by_parent.get(parent, [])
        for i, a in enumerate(sibs):
            if a is article:
                prev_a = sibs[i - 1] if i > 0 else None
                next_a = sibs[i + 1] if i + 1 < len(sibs) else None
                return prev_a, next_a
        return None, None

    def _render_prev_next_nav(self, article: 'Article',
                               sibs_by_parent: dict) -> str:
        """글 본문 끝에 붙일 prev/next nav HTML. 빈 문자열이면 미출력.

        대칭 레이아웃을 위해 한 쪽만 있을 때 빈 자리에 placeholder span 을
        둔다 (display:flex + space-between 패턴이 한쪽만 있을 때 정렬을
        깨지 않게).
        """
        if not self.site.prev_next_enabled:
            return ''
        prev_a, next_a = self._prev_next_for(article, sibs_by_parent)
        if prev_a is None and next_a is None:
            return ''
        parts = ['<nav class="prev-next-nav" aria-label="다른 글">']
        if prev_a is not None:
            parts.append(
                f'<a class="prev-next-link prev" href="/{prev_a.meta.slug}/" rel="prev">'
                f'<span class="prev-next-dir">‹ 이전 글</span>'
                f'<span class="prev-next-title">{escape_html(prev_a.meta.title)}</span>'
                f'</a>'
            )
        else:
            parts.append(
                '<span class="prev-next-link prev prev-next-placeholder" aria-hidden="true"></span>'
            )
        if next_a is not None:
            parts.append(
                f'<a class="prev-next-link next" href="/{next_a.meta.slug}/" rel="next">'
                f'<span class="prev-next-dir">다음 글 ›</span>'
                f'<span class="prev-next-title">{escape_html(next_a.meta.title)}</span>'
                f'</a>'
            )
        else:
            parts.append(
                '<span class="prev-next-link next prev-next-placeholder" aria-hidden="true"></span>'
            )
        parts.append('</nav>')
        return '\n' + ''.join(parts) + '\n'

    # ── v1.4.0: 글 끝 발행/수정 메타 줄 ───────────────────────
    #
    # 사용자 요청 — "글의 마지막 section 아래에 작고 모던한 디자인으로
    # 심플하게". 헤더가 아니라 본문 끝. 정본 글들이 그동안 마지막 section
    # 안에 수동으로 적던 발행/수정 줄을 한 곳에서 자동 생성한다 (사용자가
    # 수동 줄을 점차 제거할 예정 — 자동 줄은 그 자리를 대체).
    # updated 가 date 와 같거나 부재면 "발행" 한 줄만 (불필요한 ' · 수정'
    # 잔재 방지). 토글 없음 — 시스템 전역 기본.

    def _render_article_end_meta(self, m: 'ArticleMeta') -> str:
        date = m.date or ''
        if not date:
            return ''
        # 본문 끝 한 줄. 절제된 디자인은 CSS (.article-end-meta) 에서.
        out = [
            '\n<div class="article-end-meta">',
            f'<time class="published" datetime="{escape_html(date)}">'
            f'{escape_html(date)} 발행</time>',
        ]
        upd = m.updated
        if upd and upd != date:
            out.append(
                f'<span class="article-end-meta-sep"> · </span>'
                f'<time class="updated" datetime="{escape_html(upd)}">'
                f'{escape_html(upd)} 수정</time>'
            )
        out.append('</div>\n')
        return ''.join(out)

    def _render_articles(self):
        # v0.6.4: 글마다 template 키가 다를 수 있어 per-article load. 기본 article.html.
        nav_links = self._nav_links_html()
        # v1.4.0: prev/next 인덱스를 글 루프 진입 전에 한 번만 만든다.
        # 글마다 같은 정렬을 다시 돌면 O(N²) 라 한 번 만들어 dict lookup
        # 으로 재사용. cache hit 경로에선 호출되지 않으므로 (이미 캐시된
        # HTML 이 nav 를 포함) miss 한 글만 비용 부담.
        sibs_by_parent = self._build_sibling_index()

        # v0.7.0: 빌드 증분 캐시 — global_hash 가 모든 글에 영향을 주는 입력의
        # 종합 sha256. _render_articles 진입 시점이 안전한 호출 위치다 (site /
        # meta / template / assets 모두 디스크에 확정된 상태).
        if self.cache.enabled and self.cache.global_hash is None:
            self.cache.compute_global_hash(
                site_yaml=self.base / 'site.yaml',
                scripts_dir=self.src_dir / 'scripts',  # v0.8.1: src/ 아래로
                templates_dir=self.templates_dir,
                assets_dir=self.assets_dir,
                articles_dir=self.articles_dir,
                version=_SITE_VERSION,
            )

        _n = len(self.articles)
        for _i, article in enumerate(self.articles, 1):
            m = article.meta
            content_path = article.content_file
            # v0.7.2: in-place 진행 (TTY 전용). slug 은 meta 가 채워진 뒤라
            # 항상 존재. 캐시 hit/miss 총계는 빌드 종료 요약에서 보고된다.
            self._live(f'  글 {_i}/{_n}  {m.slug}')

            if not content_path or not content_path.exists():
                self._issue(
                    'article', m.slug,
                    'content 파일을 찾을 수 없어 글을 빌드하지 않습니다.',
                    article.source_dir,
                )
                continue

            # v0.7.0: 캐시 조회 — article_hash 가 일치하면 dist 에 직접 복원 +
            # 부수 산출 (rendered_bodies, article_render_meta) 도 캐시에서 복원.
            article_hash = None
            if self.cache.enabled:
                try:
                    article_hash = self.cache.compute_article_hash(
                        slug=m.slug,
                        source_dir=article.source_dir,
                        content_file=content_path,
                    )
                except OSError:
                    article_hash = None
                if article_hash is not None:
                    hit = self.cache.lookup(m.slug, article_hash)
                    if hit is not None:
                        for it in hit.issues:
                            replay_issue(self.report, it)
                        for wn in hit.warnings:
                            replay_warning(self.report, wn)
                        self.rendered_bodies[m.slug] = hit.body_plain
                        self.article_render_meta[m.slug] = {
                            'thumb': hit.thumb,
                            'summary': hit.summary,
                        }
                        out_dir = self.dist / m.slug
                        out_dir.mkdir(parents=True, exist_ok=True)
                        out_file = out_dir / f'index.{hit.output_ext}'
                        out_file.write_text(hit.output, encoding='utf-8')
                        # v1.4.0: PHP 빌드 글 목록 — 캐시 hit 경로에서도 등록.
                        if hit.output_ext == 'php':
                            self.report.note_php_built(m.slug)
                        self.cache.record_hit(m.slug, hit, article_hash)
                        self._cache_hits += 1
                        continue

            # 캐시 miss — 평소대로 렌더한 뒤 cache.store() 로 기록.
            self._cache_misses += 1
            article_report_offset = len(self.report.entries)

            content_text = content_path.read_text(encoding='utf-8')

            if content_path.suffix == '.md':
                rr = render_article_md(
                    content_text, m.slug, article.source_dir,
                    self.site.php_globals,
                )
                # v0.4.3: 본문 자동 첫 갭 + 섹션 마커 (===제목===, ======) 처리.
                body_html = resolve_section_markers(rr.html, m.title)
            else:
                rr = process_html(content_text, m.slug, article.source_dir,
                                  self.site.php_globals)
                body_html = rr.html

            # v1.4.0: 검색용 plain text 는 nav/메타가 *없는* 본문에서 추출
            # (검색 결과 스니펫이 "이전 글" / "2026-05-14 발행" 같은 메타
            # 텍스트를 인용하지 않게).
            self.rendered_bodies[m.slug] = html_to_plain(rr.html)

            # v1.4.0: 본문 끝 메타 줄 + prev/next nav 를 body_html 에 append.
            # 두 자동 요소가 본문 일부로 포함돼 page_html 의 어디든 들어가도록
            # _render_template 의 BODY 치환에 자연 흡수된다. 캐시된 HTML 에도
            # 함께 박혀 있어 cache hit 시 결정성 유지.
            body_html += self._render_article_end_meta(m)
            body_html += self._render_prev_next_nav(article, sibs_by_parent)

            # v0.5.5: description 필수 정책 + 본문 ↔ 메타데이터 분리.
            #   - seo.description 이 None (키 부재/값 부재) → 작성자가 의도적
            #     으로 누락한 게 아니라 필수 필드를 빠뜨린 것으로 간주, issue.
            #   - seo.description 이 '' (빈 문자열) → 작성자 실수, issue.
            #   - 둘 다의 경우 summary 가 누락된다 (피드 <summary> /
            #     <description> 태그 자체가 출력되지 않음, gallery 도 description
            #     없이 그라데이션 플레이스홀더만).
            #   - 본문 폴백 없음. rr.first_paragraph / rr.first_image 참조 제거.
            # v1.2.1: noindex 글은 description 필수 검사 면제. noindex 시맨틱
            #   (검색엔진 미색인 + sitemap/feed/search.php 인덱스 제외) 상 SERP
            #   스니펫·피드 summary 가 모두 무의미해, description 누락이 더이상
            #   "외부 노출용 빠뜨림" 이 아니다. og:description 미리보기는 여전히
            #   원하면 author 가 직접 적을 수 있다 (검사가 면제될 뿐 출력 경로는
            #   불변). 빈 문자열 '' 도 동일 경로 — 의도적 비움/누락 구분이
            #   noindex 안에서는 의미가 없다.
            desc_val = m.seo.description
            if m.noindex:
                summary = (
                    truncate_description(desc_val, self.site.description_truncate)
                    if desc_val else ''
                )
            elif desc_val is None:
                self._issue(
                    'article', m.slug,
                    "meta.yaml: 'seo.description' 필드가 없습니다 "
                    "— 외부 노출용 한 줄 설명을 작성해주세요. "
                    "(description / og:description / twitter:description / "
                    "피드 summary 가 모두 누락됩니다.)",
                    article.source_dir / 'meta.yaml',
                )
                summary = ''
            elif desc_val == '':
                self._issue(
                    'article', m.slug,
                    "meta.yaml: 'seo.description' 이 빈 문자열입니다 "
                    "— 외부 노출용 한 줄 설명을 작성해주세요. "
                    "(description 메타 태그 / 피드 summary 가 누락됩니다.)",
                    article.source_dir / 'meta.yaml',
                )
                summary = ''
            else:
                summary = truncate_description(
                    desc_val, self.site.description_truncate,
                )

            # 갤러리 썸네일 — v0.5.5 부터 본문 폴백 없음.
            # seo.og_image > site.default_og_image > None.
            # build_meta_tags 와 같은 우선순위지만, 갤러리 타일은 URL 만 필요해
            # base_url 접두를 붙이지 않은 그대로 보관 (templates 측에서 사용).
            thumb = m.seo.og_image if (m.seo.og_image not in (None, '')) else None
            if thumb is None and self.site.default_og_image:
                thumb = self.site.default_og_image
            self.article_render_meta[m.slug] = {
                'thumb': thumb,
                'summary': summary,
            }

            # v0.5.1: <img> 후처리 — WebP src 치환 + srcset + sizes + loading=lazy.
            # image_variants 가 비어 있어도 (전체 이미지 비활성 / lazy_loading
            # 만 켠 케이스) transform_img_tags 는 loading 부착은 수행한다.
            if (self.site.images.enabled
                    or self.site.images.lazy_loading):
                body_html = transform_img_tags(
                    body_html,
                    variant_lookup=self.image_variants.get,
                    config=self.site.images,
                )

            # v0.6.3: styles 키 분리 — 외부 CSS link 와 인라인 <style> 블록을
            # 각각 렌더. 로드 순서는 common_template.css → 외부 CSS → 인라인 —
            # 인라인이 마지막으로 발언해 "미세 override" 의도를 보장.
            # v0.6.4: render_stylesheet_links 의 두 번째 인자가 url_prefix.
            page_stylesheets = render_stylesheet_links(
                m.stylesheets, f'/{m.slug}/',
            )
            page_styles = render_inline_styles(m.styles)

            # v1.4.0: 옛 site.yaml warn_on_underscore_ref 토글 폐기 — 항상 경고.
            # 빌드에서 제외된 `_` 접두 자산 참조는 dist 에 404 자국을 남기므로
            # 끄고 싶을 사유가 없다 (디버깅을 어렵게 만들 뿐).
            for pattern in [r'src="([^"]+)"', r'href="([^"]+)"']:
                for url_match in re.finditer(pattern, rr.html):
                    ref = url_match.group(1)
                    if '/_' in ref or ref.startswith('_'):
                        self._warning(
                            'article', m.slug,
                            f'본문이 빌드에서 제외된 자산을 참조: {ref}',
                            article.source_dir,
                        )

            # v0.6.2: build_meta_tags 시그니처 일반화 — 글/홈/카테고리 공용.
            meta_tags, full_title = build_meta_tags(
                title=m.title,
                seo=m.seo,
                site=self.site,
                canonical_path=f'/{m.slug}/',
                page_kind='article',
                published=m.date,
                updated=m.updated or m.date,
            )

            # 말단 = 글 제목(m.title) — 폴더명/slug 아님(Bug B).
            # 조상 = 글을 담은 카테고리들(자기 폴더 제외), 각자 자기
            # 중첩 카테고리 URL 로 링크(Bug A). 톱레벨 글(조상 0)은
            # 단일 crumb → BreadcrumbList 생략, nav-tracker 말단=제목.
            crumb_parts = self._crumb_parts_for(
                ancestors=self._ancestor_categories(
                    article.category_path[:-1]),
                leaf=(m.title, None),
            )
            nav_tracker = self._nav_tracker_for_path(crumb_parts)

            # v0.8.3: schema.org JSON-LD (additive — 메타 태그를 대체하지
            # 않고 보강). 사이트(site.jsonld.enabled)/글(seo.jsonld) 토글로
            # 출력 여부 결정. breadcrumb 은 위 crumb_parts 를 그대로 재사용
            # 해 사이트 nav-tracker 와 동일한 라벨/경로를 쓴다.
            if jsonld_enabled(self.site, m.seo):
                jsonld_html = build_jsonld(
                    title=m.title,
                    seo=m.seo,
                    site=self.site,
                    canonical_path=f'/{m.slug}/',
                    page_lang=m.lang or self.site.lang,
                    published=m.date,
                    updated=m.updated or m.date,
                    tags=m.tags,
                    breadcrumb=crumb_parts,
                )
            else:
                jsonld_html = ''

            # v0.6.4: 글 단위 template override. 폴백 = article.html.
            tpl = self._resolve_template(
                m.template, article.source_dir,
                default_name='article.html',
                scope='article', target=m.slug,
                meta_file=article.source_dir / 'meta.yaml',
            )

            # noindex 가 켜진 글은 robots meta 한 줄을 넣고, 꺼진 글은
            # placeholder 가 자리한 라인 자체를 통째로 제거 — 빈 줄 잔존 방지.
            # v0.4.2: 들여쓰기에 무관하게 라인 단위로 제거 (이전 버전은
            # '    {{ROBOTS_META}}\n' 4공백 하드코딩).
            if m.noindex:
                tpl_local = tpl.replace(
                    '{{ROBOTS_META}}',
                    "<meta name='robots' content='noindex'>",
                )
            else:
                tpl_local = re.sub(
                    r'^[ \t]*\{\{ROBOTS_META\}\}[ \t]*\r?\n',
                    '',
                    tpl,
                    flags=re.MULTILINE,
                )

            # v0.8.3: JSON-LD placeholder 는 ROBOTS_META 와 같은 라인-이팅
            # 규칙. 비출력(사이트/글 토글 off)이면 `{{JSONLD}}` 가 자리한
            # 라인을 통째로 제거해 빈 줄이 남지 않게 한다. 출력이면
            # placeholder 를 그대로 두고 아래 vars_ 의 'JSONLD' 로 치환
            # (META_TAGS 와 동일한 _render_template Pass 1 경로 — 사용자
            # 텍스트가 섞인 값도 같은 방식으로 안전 처리됨).
            if not jsonld_html:
                tpl_local = re.sub(
                    r'^[ \t]*\{\{JSONLD\}\}[ \t]*\r?\n',
                    '',
                    tpl_local,
                    flags=re.MULTILINE,
                )

            # v0.6.4: COMMON_CSS + PAGE_STYLESHEETS line-eating 을 공용 헬퍼로.
            tpl_local = self._apply_css_placeholders(
                tpl_local,
                use_common_css=m.use_common_css,
                stylesheets_html=page_stylesheets,
            )

            # v1.1.3: ADSENSE_HEAD line-eating (비활성 시 placeholder 라인 제거).
            # v1.1.5: page_url=/<slug>/ — site.yaml exclude_urls 에 이 URL 이
            # 포함돼 있으면 head_script 활성이어도 이 글의 placeholder 제거.
            tpl_local = self._apply_adsense_head_placeholder(
                tpl_local, f'/{m.slug}/',
            )

            # v0.4.3: <title> 에 글 제목 사용. full_title 은
            # build_meta_tags 가 만든 `{prefix}{title}{suffix}` 문자열.
            page_title = full_title or self.site.name

            # v0.4.5: 글 단위 lang override (없으면 site.lang).
            page_lang = m.lang or self.site.lang

            vars_ = {
                'LANG': escape_html(page_lang),
                'META_TAGS': meta_tags,
                # v0.8.3: 비출력이면 위에서 라인 자체를 strip 했으므로 이
                # 키는 무해하게 미사용. 출력이면 placeholder 를 치환.
                'JSONLD': jsonld_html,
                # v1.1.3: ADSENSE_HEAD — 비활성이면 위에서 라인 strip, 활성이면
                # raw 스크립트 문자열을 치환.
                'ADSENSE_HEAD': self.site.google_adsense.head_script,
                'PAGE_STYLES': page_styles,
                'PAGE_TITLE': escape_html(page_title),
                'MAIN_TITLE': escape_html(self.site.main_title),
                'NAV_TRACKER': nav_tracker,
                'NAV_LINKS': nav_links,
                'BODY': body_html,
                'COPYRIGHT_YEAR': self._copyright_year(),
                'COPYRIGHT_HOLDER': escape_html(self.site.copyright_holder),
            }
            page_html = _render_template(
                tpl_local, vars_,
                content_vars={'BODY'},
                warn_context=('article', m.slug,
                              article.source_dir / 'meta.yaml'),
                report=self.report,
            )

            ext = 'php' if has_live_php(page_html) else 'html'

            out_dir = self.dist / m.slug
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f'index.{ext}'
            out_file.write_text(page_html, encoding='utf-8')

            # v1.4.0: PHP 빌드 글 목록 등록 (cache miss 경로).
            if ext == 'php':
                self.report.note_php_built(m.slug)

            # v0.7.0: 캐시 store — 이번 글 렌더 중 self.report 에 추가된 항목
            # 중 scope='article' AND target=slug 인 것만 캐시 기록 (다음
            # 빌드의 hit 에서 replay 됨). v0.8.2: per-Builder report.
            if self.cache.enabled and article_hash is not None:
                new_entries = self.report.entries[article_report_offset:]
                cache_issues = [
                    issue_payload(e.scope, e.target, e.message, e.location)
                    for e in new_entries
                    if e.severity == 'issue'
                    and e.scope == 'article'
                    and e.target == m.slug
                ]
                cache_warnings = [
                    issue_payload(e.scope, e.target, e.message, e.location)
                    for e in new_entries
                    if e.severity == 'warning'
                    and e.scope == 'article'
                    and e.target == m.slug
                ]
                self.cache.store(
                    slug=m.slug,
                    article_hash=article_hash,
                    output=page_html,
                    output_ext=ext,
                    body_plain=self.rendered_bodies.get(m.slug, ''),
                    thumb=self.article_render_meta.get(m.slug, {}).get('thumb'),
                    summary=self.article_render_meta.get(m.slug, {}).get('summary', ''),
                    issues=cache_issues,
                    warnings=cache_warnings,
                )

        # v0.7.2: 단계 요약 (리포트 트랜스크립트에 한 줄로 남는다).
        if _n:
            self._emit(f'        {_n} 글 처리 '
                       f'(캐시 {self._cache_hits} hit / '
                       f'{self._cache_misses} miss).')

    # ── [6] Asset sync ────────────────────────────────────────

    def _sync_assets(self):
        """글 폴더의 자원을 dist/{slug}/ 로 동기화 (v0.5.2 부터 글 폴더 안).

        v0.5.2: 옛 `dist/src/{slug}/` 트리를 폐지하고, 글 자산을 글의 index.html
        과 같은 폴더 (`dist/{slug}/`) 로 떨어뜨린다.

        v0.5.1: raster 이미지 (.jpg .jpeg .png .gif) 는 `optimize_image()` 가
        webp 변종들로 변환하고, 원본은 dist 에 복사하지 않는다. 변종 정보를
        `self.image_variants` 에 등록하여, _render_articles 의 HTML 후처리가
        `<img>` 의 src 를 webp + srcset 으로 치환할 때 참조한다. (rewrite_asset_path
        가 상대 경로를 `/{slug}/...` 로 절대화한 형태가 키.)

        v1.3.0: 두 패스 분리 + raster 이미지 변환 멀티프로세스 병렬화.
          1. 메인 스레드가 모든 글 폴더를 rglob 으로 한 번 훑어 raster 변환
             대상과 그 외 복사 대상으로 분류 (raster_jobs / copy_jobs).
          2. raster_jobs 를 ProcessPoolExecutor 로 fan-out — `optimize_image`
             는 순수 함수라 워커가 독립적으로 디스크에 변종을 떨어뜨리고
             VariantSet 만 메인으로 돌려준다. 결과 등록 (self.image_variants)
             과 에러 라우팅 (self._warning) 은 메인에서.
          3. copy_jobs 시리얼 처리 (단순 mtime 비교라 병렬화 가치 낮음) +
             글마다 prune.
          소형 잡 (raster_jobs < 4) 또는 워커 1 인 경우 시리얼 폴백 — Windows
          spawn 비용 절약. 결정성: 변환 순서는 결과에 무관 (각 파일이 자기
          dst 에 독립 기록, image_variants 는 dict lookup).

        SVG / WebP / 비이미지 파일은 v0.5.0 과 동일하게 그대로 복사.
        """
        # v0.7.2: 이미지 최적화가 빌드 시간의 대부분 — 글마다 + 이미지마다
        # in-place 진행 (TTY 전용). 사진이 많은 사이트에서 "멈춘 게 아니라
        # 변환 중" 이 보이게 한다.
        _n = len(self.articles)

        # ─ 패스 1: 분류 + per-article expected set 누적 ─────────
        # raster_jobs:     (idx, slug, src_file, dst_file, url, rel)
        # copy_jobs:       (idx, slug, src_file, dst_file, rel)
        # article_expected: slug -> set[Path] (prune 단계의 보존 화이트리스트)
        # v1.3.0 (D 항목): _prune_article_assets 가 다시 src rglob 도는
        # 중복 패스를 제거. 분류 단계에서 expected 를 같이 채워, prune 은
        # dst rglob 한 번만 돌고 expected 와 비교. raster 변종은 configured
        # widths 의 기본 후보를 먼저 넣고, 변환 종료 후 실제 dst 디렉터리의
        # 같은 stem-*.webp glob 으로 overrun width 변종까지 보강한다.
        raster_jobs = []
        copy_jobs = []
        article_expected = {}
        for _i, article in enumerate(self.articles, 1):
            m = article.meta
            src_root = article.source_dir
            dst_root = self.dist / m.slug
            expected = {dst_root / 'index.html', dst_root / 'index.php'}
            for src_file in src_root.rglob('*'):
                if not src_file.is_file():
                    continue
                if is_excluded_path(src_file, src_root):
                    continue
                if src_file.name in ('meta.yaml', 'content.md', 'content.html'):
                    continue
                rel = src_file.relative_to(src_root)
                dst_file = dst_root / rel
                if self._should_optimize_image(src_file):
                    rel_str = str(rel).replace('\\', '/')
                    url = f'/{m.slug}/' + rel_str
                    raster_jobs.append((_i, m.slug, src_file, dst_file, url, rel))
                    stem = src_file.stem
                    for w in self.site.images.widths:
                        expected.add(dst_root / rel.parent / f'{stem}-{w}.webp')
                else:
                    copy_jobs.append((_i, m.slug, src_file, dst_file, rel))
                    expected.add(dst_file)
            article_expected[m.slug] = expected

        # ─ 패스 2: raster 변환 (병렬 또는 시리얼) ────────────────
        img_done = 0
        if raster_jobs:
            if not _HAS_PIL:
                abort(f"이미지 최적화가 켜져 있는데 Pillow 가 없습니다. "
                      f"raster 이미지를 만났습니다: {raster_jobs[0][2]}\n"
                      f"       pip install Pillow 로 설치하거나 "
                      f"site.yaml 의 images.enabled 를 false 로 두세요.")
            # 워커가 race 없이 쓸 수 있도록 dst 부모 디렉터리를 미리 만든다.
            for _i, slug, src_file, dst_file, url, rel in raster_jobs:
                dst_file.parent.mkdir(parents=True, exist_ok=True)
            workers = min(os.cpu_count() or 1, len(raster_jobs))
            cfg = self.site.images
            # 소형 잡은 spawn 비용 (Windows 워커마다 Pillow import ~0.5s) 이
            # 더 커서 시리얼이 빠르다. 4 미만이면 시리얼.
            if workers <= 1 or len(raster_jobs) < 4:
                for _i, slug, src_file, dst_file, url, rel in raster_jobs:
                    variants, err = optimize_image(
                        src=src_file, dst_dir=dst_file.parent, config=cfg,
                    )
                    self._handle_image_result(
                        slug, src_file, dst_file, url, variants, err,
                        article_expected[slug],
                    )
                    img_done += 1
                    self._live(f'  자산 글 {_i}/{_n}  {slug}  '
                               f'(이미지 {img_done} 변환  {rel})')
            else:
                # ProcessPoolExecutor.map 은 결과 순서를 입력 순서로 보장한다.
                args = [
                    (src_file, dst_file.parent, cfg)
                    for _i, slug, src_file, dst_file, url, rel in raster_jobs
                ]
                with ProcessPoolExecutor(max_workers=workers) as pool:
                    results = pool.map(_image_worker, args)
                    for job, result in zip(raster_jobs, results):
                        _i, slug, src_file, dst_file, url, rel = job
                        variants, err = result
                        self._handle_image_result(
                            slug, src_file, dst_file, url, variants, err,
                            article_expected[slug],
                        )
                        img_done += 1
                        self._live(f'  자산 글 {_i}/{_n}  {slug}  '
                                   f'(이미지 {img_done} 변환  {rel})')

        # ─ 패스 3: 비-raster 복사 + per-article prune ────────────
        for _i, slug, src_file, dst_file, rel in copy_jobs:
            self._live(f'  자산 글 {_i}/{_n}  {slug}  ({rel})')
            _copy_if_newer(src_file, dst_file)
        for article in self.articles:
            self._prune_article_assets(
                article, article_expected.get(article.meta.slug, set()),
            )

        # v0.7.2: 단계 요약 (리포트 트랜스크립트 한 줄).
        if _n:
            self._emit(f'        {_n} 글 자산 동기화 '
                       f'(이미지 {img_done} 변환).')

    def _handle_image_result(self, slug, src_file, dst_file, url,
                             variants, err, expected_set):
        """워커 또는 시리얼 변환 결과를 메인에서 처리 — variants 등록 + 에러 라우팅.

        v1.3.0 (B 항목 병렬화 분리에서 추출 + D 통합으로 expected_set 등록):
        _optimize_and_register 의 결과 처리 절을 메인 전용 헬퍼로 옮기고,
        실제 생성된 variant widths 를 expected_set 에 추가해 prune 단계가
        overrun width (configured max 초과 원본을 추가 보존하는 케이스) 도
        보존하도록 한다. 인코딩 실패 폴백 시에는 원본을 그대로 복사하므로
        그 원본 dst 도 expected 로 등록.
        """
        if variants is None:
            # 인코딩 실패 — 폴백으로 원본 복사. 워닝은 BuildReport 로 라우팅.
            # 산출물 자체는 정상 (원본이 그대로 dist 에 들어감) → 'warning' 분류.
            if err:
                self._warning('site', '', err, location=src_file)
            _copy_if_newer(src_file, dst_file)
            expected_set.add(dst_file)
            return
        # URL 등록 — HTML 의 <img src> 가 갖는 형태와 정확히 일치해야 함.
        self.image_variants[url] = variants
        # 실제 생성된 widths 를 expected 에 추가 — overrun width 변종 보존.
        stem = src_file.stem
        rel_parent = dst_file.parent
        for w in variants.widths:
            expected_set.add(rel_parent / f'{stem}-{w}.webp')

    def _should_optimize_image(self, src: Path) -> bool:
        """이 파일이 WebP 변환 대상인지."""
        if not self.site.images.enabled:
            return False
        return src.suffix.lower() in RASTER_EXTS

    def _optimize_and_register(
        self,
        *,
        src_file: Path,
        dst_file: Path,
        url_prefix: str,
        rel_path: Path,
    ):
        """raster 이미지 한 장을 webp 변종들로 변환하고 image_variants 에 등록.

        url_prefix + rel_path 가 HTML 안의 (rewrite 된) src URL 과 매칭되어야
        한다. 예: /about/face_img.png (실제 dist 에는 face_img-800.webp 등).
        v0.5.2: 옛 `/src/{slug}/...` → `/{slug}/...` 로 변경.
        """
        if not _HAS_PIL:
            abort(f"이미지 최적화가 켜져 있는데 Pillow 가 없습니다. "
                  f"raster 이미지를 만났습니다: {src_file}\n"
                  f"       pip install Pillow 로 설치하거나 "
                  f"site.yaml 의 images.enabled 를 false 로 두세요.")

        variants, err = optimize_image(
            src=src_file,
            dst_dir=dst_file.parent,
            config=self.site.images,
        )
        if variants is None:
            # 인코딩 실패 — 폴백으로 원본 복사. 워닝은 BuildReport 로 라우팅.
            # 산출물 자체는 정상 (원본이 그대로 dist 에 들어감) → 'warning' 분류.
            if err:
                self._warning('site', '', err, location=src_file)
            _copy_if_newer(src_file, dst_file)
            return

        # URL 등록 — HTML 의 <img src> 가 갖는 형태와 정확히 일치해야 함.
        rel_str = str(rel_path).replace('\\', '/')
        url = url_prefix + rel_str
        self.image_variants[url] = variants

    def _prune_article_assets(self, article: Article, expected: set):
        """글 폴더 dist/{slug}/ 의 고아 파일 정리.

        v1.3.0 (D 항목): _sync_assets 패스 1 분류 단계가 채워둔 expected set
        을 받아 src rglob 중복 패스를 제거. 패스 1 이 configured widths 의
        후보 변종을 미리 등록하고, 패스 2 결과 처리 (_handle_image_result)
        가 실제 생성된 variants.widths 를 expected 에 추가해 overrun width
        변종도 보존된다. raster 가 빌드 사이에 삭제됐다면 그 stem 의 stale
        stem-W.webp 는 expected 에 없어 자연 정리된다.

        v0.5.2: 글 자산이 글의 index.html 과 같은 폴더에 동거 — 본체 산출물
        (index.html / index.php) 도 보존 대상. expected 에 두 경로가 이미
        등록된 채 들어온다.
        """
        m = article.meta
        dst_root = self.dist / m.slug
        if not dst_root.exists():
            return
        for existing in list(dst_root.rglob('*')):
            if existing.is_file() and existing not in expected:
                existing.unlink()
        _remove_empty_dirs(dst_root)

    # ── [7] Category indexes ──────────────────────────────────

    def _gallery_tile_html(self, article: 'Article', hidden: bool = False) -> str:
        """v0.5.3: 갤러리 레이아웃의 한 타일 HTML.

        v0.5.5: 썸네일 우선순위 = seo.og_image > site.default_og_image > 빈
        플레이스홀더 (그라데이션). 본문 폴백 (옛 `rr.first_image`) 제거 —
        본문 ↔ 메타데이터 분리 원칙 (README § 16 의 설계 원칙 10 참조). 썸네일이 없는 타일은
        옅은 그라데이션 배경만 보여 일관된 그리드를 유지한다 (4:3 강제 크롭).
        """
        m = article.meta
        link_text = m.title
        rmeta = self.article_render_meta.get(m.slug, {})
        thumb = rmeta.get('thumb')
        style_attr = " style='display:none'" if hidden else ""

        if thumb:
            # 썸네일은 raster 원본 URL 일 수 있고, 이 경우 image_variants 에 webp
            # 변종 정보가 등록되어 있다. transform_img_tags 와 같은 로직으로
            # primary webp src + srcset 을 만든다. variants 가 없으면 (외부 URL,
            # SVG, 이미 webp, 또는 images.enabled=false) src 를 그대로 사용.
            primary_src = thumb
            srcset_attr = ''
            sizes_attr = ''
            variants = self.image_variants.get(thumb)
            if variants is not None:
                dir_part, stem, _ext, tail = _split_url(thumb)
                prefix = '' if dir_part in ('.', '') else dir_part + '/'
                primary_src = f'{prefix}{stem}-{variants.primary_width}.webp{tail}'
                srcset = _build_srcset(dir_part, stem, variants.widths)
                srcset_attr = f" srcset='{escape_html(srcset)}'"
                if self.site.images.default_sizes:
                    sizes_attr = (
                        f" sizes='{escape_html(self.site.images.default_sizes)}'"
                    )
            thumb_inner = (
                f"<img src='{escape_html(primary_src)}'"
                f"{srcset_attr}{sizes_attr}"
                f" alt='' loading='lazy'>"
            )
            thumb_class = 'gallery-tile-thumb'
        else:
            thumb_inner = ''
            thumb_class = 'gallery-tile-thumb gallery-tile-thumb-empty'

        return (
            f"<a class='gallery-tile' href='/{m.slug}/'{style_attr}>"
            f"<div class='{thumb_class}'>{thumb_inner}</div>"
            f"<div class='gallery-tile-meta'>"
            f"<span class='gallery-tile-title'>{escape_html(link_text)}</span>"
            f"<span class='gallery-tile-date'>{m.date}</span>"
            f"</div>"
            f"</a>"
        )

    def _listup_module_html(self, article: 'Article', hidden: bool = False) -> str:
        """글 한 줄의 listup HTML.

        v0.4.6: hidden=True 면 `style='display:none'` 를 inline 으로 부착.
        SSR 시점에 페이지네이션의 비활성 페이지 항목을 미리 숨겨 FOUC 를 방지.
        pagination.js 는 그 후에 첫 페이지 항목의 inline style 을 비워
        (`style.display=''`) 정상 표시한다.
        """
        link_text = article.meta.title
        style_attr = " style='display:none'" if hidden else ""
        return (f"<div class='listup_module_div'{style_attr}>"
                f"<span class='listup_module_title'>"
                f"<a href='/{article.meta.slug}/'> "
                f"{escape_html(link_text)} </a>"
                f"</span>"
                f"<span class='listup_module_date'> &nbsp;&nbsp; "
                f"{article.meta.date}</span>"
                f"</div>")

    def _listup_items_html(self, articles, per_page: int,
                           layout: str = 'list') -> str:
        """v0.4.6: 페이지네이션이 부착된 항목 목록 HTML.

        per_page 가 0 이하면 모든 항목을 그대로 출력. 그 외에는 per_page 초과
        인덱스의 항목에 `style='display:none'` 을 미리 부착하여 FOUC 방지.

        v0.5.3: layout='gallery' 면 텍스트 list 대신 이미지 타일 (`_gallery_tile_html`).
        """
        parts = []
        for i, a in enumerate(articles):
            hidden = per_page > 0 and i >= per_page
            if layout == 'gallery':
                parts.append(self._gallery_tile_html(a, hidden=hidden))
            else:
                parts.append(self._listup_module_html(a, hidden=hidden))
        return '\n'.join(parts)

    def _render_section(self, label: str, articles: list, group_key: str,
                        per_page: int, more_url: str = None,
                        layout: str = 'list') -> str:
        """페이지네이션이 부착된 한 개의 section HTML 을 반환.

        articles 는 이미 정렬되어 있어야 한다.
        group_key 는 같은 페이지 내에서 unique 해야 한다 (페이지 컨트롤 짝짓기).
        more_url 이 주어지면 section 헤더의 라벨(소분류명) *자체* 가 그 URL
        로 가는 링크가 된다 — 클릭하면 그 소분류의 자기 페이지(그 분류 글
        만)로 이동. (v1.0.1: 라벨 우측의 → 화살표 폐지. 링크는 본문 글씨와
        동일하게 보이도록 스타일을 비운 a 태그 — .gap .subcat-link.)
        layout 이 'gallery' 면 section 에 listup-gallery 클래스가 추가되고 항목이
        이미지 타일로 렌더된다 (v0.5.3).
        """
        # v0.5.3: list 외 미지원 layout 은 list 로 폴백 (forward compat).
        if layout not in ('list', 'gallery'):
            layout = 'list'

        section_extra_class = ' listup-gallery' if layout == 'gallery' else ''

        if not articles:
            inner = "<p>No articles found</p>"
            attrs = f"class='paginated-empty{section_extra_class}'"
            nav_html = ''
        else:
            # _pagination_section_attrs 의 class 를 확장.
            base_attrs = _pagination_section_attrs(group_key, per_page)
            if section_extra_class:
                base_attrs = base_attrs.replace(
                    'class="paginated"',
                    f'class="paginated{section_extra_class}"',
                    1,
                )
            attrs = base_attrs
            # v0.4.6: per_page 를 넘는 항목은 SSR 단계에서 inline style 로
            # 미리 숨겨 FOUC 를 방지.
            inner = self._listup_items_html(articles, per_page, layout=layout)
            nav_html = _pagination_nav_html(group_key, len(articles), per_page)

        if more_url:
            # v1.0.1: 소분류명 글씨 자체에 스타일 없는 a 태그를 건다 (우측
            # → 화살표 폐지). 글씨를 클릭하면 그 소분류의 자기 페이지로
            # 가 그 분류 글만 보인다. 링크 외양은 .gap .subcat-link 가
            # color inherit + text-decoration none 으로 본문 글씨와 동일.
            label_html = (
                f"<a class='subcat-link' href='{more_url}'>"
                f"{escape_html(label)}</a>"
            )
        else:
            label_html = escape_html(label)

        return (
            f"<div class='gap'><p>{label_html}</p></div>\n"
            f"<section {attrs}>\n{inner}\n</section>\n"
            f"{nav_html}"
        )

    def _category_styles_html(self, cat: Category) -> str:
        """카테고리 meta.yaml 의 인라인 styles → <style> 블록.

        section TAG 선택자로 글 styles 와 동일한 우선순위 정책 적용.
        v0.6.4: 카테고리/홈도 외부 CSS 파일 지원으로 일원화. 여기 도달하는
        styles 는 *인라인 룰 (문자열 키) 만* 담는다 — 외부 CSS 파일 link 는
        _build_category_page 가 별도 placeholder 로 처리.
        """
        return render_inline_styles(cat.meta.styles)

    def _build_category_page(self, cat: Category):
        """톱레벨/서브카테고리 공용 인덱스 페이지 빌더 (v0.4.5).

        - 톱레벨 카테고리: 자식 서브카테고리마다 section 한 개씩.
                          자식이 없으면 (이 카테고리의 직속 articles 만 있는 경우)
                          자기 자신을 한 section 으로.
        - 서브카테고리: 자기 자신을 한 section 으로. 만약 더 깊은 자식이
                       있다면 (3+ depth) 자식별 section 도 추가로.
        - 페이지네이션: section 마다 독립 (data-pagination-group 으로 짝지음).
        - styles: 이 카테고리의 meta.yaml 의 인라인 styles 가 head 의 <style> 로.
        - stylesheets: v0.6.4 부터 외부 CSS link 도 지원 (글과 동일 메커니즘).
        - use_common_css: v0.6.4 부터 토글 지원 (글과 동일).
        - template: v0.6.4 부터 카테고리도 자기 템플릿 파일 선택 가능.
        - lang: 카테고리 meta.yaml 의 lang 우선, 없으면 site.lang.
        """
        # v0.6.4: 카테고리 단위 template override. 폴백 = category.html.
        cat_meta_file = (
            self.articles_dir.joinpath(*cat.path) / 'meta.yaml'
        )
        tpl = self._resolve_template(
            cat.meta.template, cat_meta_file.parent,
            default_name='category.html',
            scope='category', target='/'.join(cat.slug_path),
            meta_file=cat_meta_file,
        )
        nav_links = self._nav_links_html()

        is_top = len(cat.path) == 1

        # URL prefix — 톱레벨이면 "/{slug}/", 서브이면 "/{top}/{sub}/"
        url_prefix = '/' + '/'.join(cat.slug_path) + '/'

        sections = []
        # v0.4.6: 자식 카테고리 정렬은 priority 내림차순 (큰 값 먼저), 같은
        # priority 끼리는 folder_name 알파벳 오름차순.
        sorted_children = sorted(
            cat.children,
            key=lambda c: (-c.meta.priority, c.folder_name),
        )

        # 자식 서브카테고리가 있는 경우 — 자식별로 section 생성.
        # 톱레벨이면 "더 보기" 링크가 자식의 자기 페이지 (`/top/sub/`) 로.
        # v0.5.3: 자식 section 의 layout 은 그 자식 자신의 meta.layout 을 사용
        # (Tutorials 카테고리가 gallery 면, 부모 Blog 페이지의 Tutorials section 도 gallery).
        for child in sorted_children:
            articles = self._collect_articles(child)
            articles.sort(key=lambda a: a.meta.date, reverse=True)
            child_url = '/' + '/'.join(child.slug_path) + '/'
            group_key = f"cat-{'-'.join(child.slug_path)}"
            sections.append(
                self._render_section(
                    label=child.folder_name,
                    articles=articles,
                    group_key=group_key,
                    per_page=self._category_preview_per_page(child),
                    more_url=child_url,
                    layout=child.meta.layout,
                )
            )

        # 이 카테고리 직속 글들이 있는 경우 또는 자식이 없는 경우 — 자신을 section 으로.
        # (자식이 있어도 직속 글이 있을 수 있다 — 그러면 둘 다 표시.)
        own_articles = sorted(cat.articles, key=lambda a: a.meta.date, reverse=True)
        if own_articles or not sorted_children:
            if not is_top and not sorted_children:
                # 서브카테고리의 자기 페이지에서, 자식이 없는 경우 — 큰 per_page 사용.
                section_per_page = self._category_per_page(cat)
            elif is_top and not sorted_children:
                # 톱레벨인데 자식이 없는 경우 — 자기 자신이 글 목록의 본진.
                # (예: Blog 직속 글들만 있는 현 상태)
                section_per_page = self._category_per_page(cat)
            else:
                # 자식이 있는데 직속 글도 있는 경우 — 톱레벨이면 preview,
                # 서브이면 per_page.
                section_per_page = (
                    self._category_preview_per_page(cat) if is_top
                    else self._category_per_page(cat)
                )

            group_key = f"cat-{'-'.join(cat.slug_path)}-own"
            sections.append(
                self._render_section(
                    label=cat.folder_name,
                    articles=own_articles,
                    group_key=group_key,
                    per_page=section_per_page,
                    layout=cat.meta.layout,
                )
            )

        subcategory_sections = '\n'.join(sections) if sections else (
            f"<div class='gap'><p>{escape_html(cat.folder_name)}</p></div>\n"
            f"<section><p>No articles found</p></section>"
        )

        # breadcrumb: 글 페이지와 동일한 단일 공유 소스(_crumb_parts_for).
        # 조상은 자기 중첩 카테고리 URL 로 링크(Bug A 회피). 카테고리
        # 페이지의 말단 이름은 K2(폴더명 유지)에 따라 cat.folder_name
        # 그대로다(카테고리 페이지엔 '글 제목' 개념이 없다). 톱이면
        # 조상 0 + 자기 url_prefix 단일 crumb(BreadcrumbList 생략),
        # 서브면 조상들 + (folder, None).
        if is_top:
            crumb_parts = self._crumb_parts_for(
                ancestors=[], leaf=(cat.folder_name, url_prefix),
            )
        else:
            crumb_parts = self._crumb_parts_for(
                ancestors=self._ancestor_categories(cat.path[:-1]),
                leaf=(cat.folder_name, None),
            )
        nav_tracker = self._nav_tracker_for_path(crumb_parts)

        # v0.6.2: 카테고리에도 글과 동일한 description 필수화 정책.
        # 누락/빈 문자열이면 BuildReport 의 issue 에 기록 (빌드는 통과).
        cat_meta_path = (
            self.articles_dir.joinpath(*cat.path) / 'meta.yaml'
        )
        self._check_page_description(
            seo=cat.meta.seo,
            page_kind='category',
            location=cat_meta_path,
            slug='/'.join(cat.slug_path),
        )

        # v0.5.4 → v0.6.2: 카테고리 페이지의 SEO 메타 태그 출력.
        # 본문 = cat.meta.title (override) > cat.folder_name (폴백).
        # 양옆 = cat.meta.seo.title_prefix/suffix > site.default_title_prefix/suffix.
        # build_meta_tags 가 두 폴백 체인을 적용하고 description / og_* /
        # twitter_* 도 함께 만든다 (글과 동일 — v0.5.4 한계 표 해소).
        title_body = cat.meta.title or cat.folder_name
        meta_tags, full_title = build_meta_tags(
            title=title_body,
            seo=cat.meta.seo,
            site=self.site,
            canonical_path=url_prefix,
            page_kind='category',
        )
        page_title = full_title
        page_lang = cat.meta.lang or self.site.lang

        # 검색 스코프: 톱레벨이면 자기 slug, 서브이면 톱레벨 slug 로 한정.
        # (search-index 의 category_slug 가 톱레벨 slug 만 갖기 때문.)
        search_cat = cat.slug_path[0]

        # v0.6.4: 카테고리도 글과 동일한 CSS 처리 — COMMON_CSS / PAGE_STYLESHEETS
        # line-eating + PAGE_STYLES 인라인.
        page_stylesheets = render_stylesheet_links(
            cat.meta.stylesheets, url_prefix,
        )
        tpl_local = self._apply_css_placeholders(
            tpl,
            use_common_css=cat.meta.use_common_css,
            stylesheets_html=page_stylesheets,
        )
        # v1.1.3: ADSENSE_HEAD line-eating.
        # v1.1.5: page_url=url_prefix (=/<slug_path>/) — exclude_urls 매칭 시 제거.
        tpl_local = self._apply_adsense_head_placeholder(tpl_local, url_prefix)

        vars_ = {
            'LANG': escape_html(page_lang),
            'META_TAGS': meta_tags,
            'ADSENSE_HEAD': self.site.google_adsense.head_script,
            'PAGE_TITLE': escape_html(page_title),
            'MAIN_TITLE': escape_html(self.site.main_title),
            'NAV_TRACKER': nav_tracker,
            'NAV_LINKS': nav_links,
            'NAV_SEARCH_CAT': escape_html(search_cat),
            'SUBCATEGORY_SECTIONS': subcategory_sections,
            'PAGE_STYLES': self._category_styles_html(cat),
            'COPYRIGHT_YEAR': self._copyright_year(),
            'COPYRIGHT_HOLDER': escape_html(self.site.copyright_holder),
        }
        page_html = _render_template(
            tpl_local, vars_,
            content_vars={'SUBCATEGORY_SECTIONS'},
            warn_context=('category', '/'.join(cat.slug_path), cat_meta_file),
            report=self.report,
        )

        out_dir = self.dist.joinpath(*cat.slug_path)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / 'index.html').write_text(page_html, encoding='utf-8')

    def _build_categories(self):
        """v0.4.5: 톱레벨 + 모든 서브카테고리에 대해 인덱스 페이지 생성.

        v0.4.4 까지는 톱레벨만 인덱스가 있었음. v0.4.5 부터 서브카테고리도
        자기 인덱스 페이지를 가짐.
        """
        # 빈 카테고리 (글이 한 편도 없는 카테고리 트리) 는 인덱스 페이지를
        # 만들지 않는다. _validate 가 이미 워닝을 띄웠음.
        for path_tuple, cat in self.categories.items():
            subtree = self._collect_articles(cat)
            if not subtree:
                continue
            self._build_category_page(cat)

    # ── [8] Home page ─────────────────────────────────────────

    def _build_home(self):
        # v0.6.4: 홈도 자기 template 키 가능. 폴백 = home.html.
        home_meta_file = self.articles_dir / 'meta.yaml'
        tpl = self._resolve_template(
            self.home_meta.template, self.articles_dir,
            default_name='home.html',
            scope='home', target='',
            meta_file=home_meta_file,
        )

        # v0.4.6: 홈 전용 설정은 site.yaml 이 아니라 Articles/meta.yaml 에서.
        exclude_top = set(self.home_meta.excludes_categories)

        # category_path 는 _scan_articles 가 [..., article_folder] 형태로 채우므로
        # 항상 1+ 요소이며, [0] 은 (a) 톱레벨 카테고리 폴더명 (글이 카테고리 안에
        # 있을 때) 또는 (b) 톱레벨 글 폴더명 자체 (About 처럼). 두 경우 모두 같은
        # 검사 한 번으로 처리 — v0.4.7 에서 중복 검사 분기를 정리.
        home_articles = [
            a for a in self.articles
            if not (a.category_path and a.category_path[0] in exclude_top)
        ]

        home_articles.sort(key=lambda a: a.meta.date, reverse=True)

        # v0.4.6: Articles/meta.yaml 의 per_page 가 site 디폴트를 오버라이드.
        per_page = self._home_per_page()
        # v0.5.3: 홈도 layout: gallery 지원.
        home_layout = self.home_meta.layout
        if home_layout not in ('list', 'gallery'):
            home_layout = 'list'
        # v0.4.6: per_page 초과 항목은 SSR 단계에서 미리 hide (FOUC 방지).
        article_items = self._listup_items_html(
            home_articles, per_page, layout=home_layout,
        )

        # v0.4.6: 메인페이지 lang — Articles/meta.yaml 의 lang 우선, 없으면 site.lang.
        page_lang = self.home_meta.lang or self.site.lang

        # v0.6.2: 홈에도 글과 동일한 description 필수화 정책.
        # 누락/빈 문자열이면 BuildReport 의 issue 에 기록 (빌드는 통과).
        self._check_page_description(
            seo=self.home_meta.seo,
            page_kind='home',
            location=self.articles_dir / 'meta.yaml',
        )

        # v0.5.4 → v0.6.2: 홈 페이지의 SEO 메타 태그 출력.
        # 본문 = home_meta.title (override) > site.name (폴백).
        # 양옆 = home_meta.seo.title_prefix/suffix > site.default_title_prefix/suffix.
        # build_meta_tags 가 두 폴백 체인을 적용하고 description / og_* /
        # twitter_* 도 함께 만든다 (글과 동일 — v0.5.4 한계 표 해소).
        title_body = self.home_meta.title or self.site.name
        meta_tags, full_title = build_meta_tags(
            title=title_body,
            seo=self.home_meta.seo,
            site=self.site,
            canonical_path='/',
            page_kind='home',
        )
        page_title = full_title
        pagination_nav = _pagination_nav_html(
            'home-recent', len(home_articles), per_page,
        )

        section_class = 'paginated listup-gallery' if home_layout == 'gallery' else 'paginated'

        # v0.6.4: 홈도 글/카테고리와 같은 CSS 처리.
        page_stylesheets = render_stylesheet_links(
            self.home_meta.stylesheets, '/',
        )
        page_styles = render_inline_styles(self.home_meta.styles)
        tpl_local = self._apply_css_placeholders(
            tpl,
            use_common_css=self.home_meta.use_common_css,
            stylesheets_html=page_stylesheets,
        )
        # v1.1.3: ADSENSE_HEAD line-eating.
        # v1.1.5: page_url='/' — exclude_urls 매칭 시 placeholder 제거.
        tpl_local = self._apply_adsense_head_placeholder(tpl_local, '/')

        vars_ = {
            'LANG': escape_html(page_lang),
            'META_TAGS': meta_tags,
            'ADSENSE_HEAD': self.site.google_adsense.head_script,
            'PAGE_TITLE': escape_html(page_title),
            'MAIN_TITLE': escape_html(self.site.main_title),
            'NAV_LINKS': self._nav_links_html(),
            'HOME_SECTION_CLASS': section_class,
            'HOME_PER_PAGE': str(per_page),
            'ARTICLE_LIST': article_items,
            'PAGINATION_NAV': pagination_nav,
            'PAGE_STYLES': page_styles,
            'COPYRIGHT_YEAR': self._copyright_year(),
            'COPYRIGHT_HOLDER': escape_html(self.site.copyright_holder),
        }
        page_html = _render_template(
            tpl_local, vars_,
            content_vars={'ARTICLE_LIST'},
            warn_context=('home', '', home_meta_file),
            report=self.report,
        )
        self.dist.mkdir(parents=True, exist_ok=True)
        (self.dist / 'index.html').write_text(page_html, encoding='utf-8')

    # ── [9] Site assets ───────────────────────────────────────

    def _copy_site_assets(self):
        """assets/ → dist/assets/ 동기화.

        v0.5.1: assets/ 안의 raster 이미지도 webp 변환 대상. variants 는
        `/assets/{rel}` URL 키로 등록 — 템플릿/HTML 에서 `/assets/foo.png` 형태로
        참조되는 이미지가 후처리에서 webp 로 치환된다.

        v1.0.0 예외 — `site.default_og_image` 가 가리키는 자산(= 사이트
        기본 og:image)은 raster 여도 webp 변환·variant 등록을 건너뛰고
        원본을 그대로 복사한다. 이 자산의 소비자는 `<img srcset>` 후처리가
        아니라 SNS 링크 언퍼ler 다 — `og:image` 메타의 고정 URL 하나를
        그대로 가져가므로 다중 해상도/srcset 이 무의미하고, KakaoTalk·일부
        Facebook 크롤러는 WebP og:image 를 렌더하지 못한다. `seo.py` 의
        `resolve_og_image` 도 이 값을 문자열 그대로 쓰므로(webp 재매핑
        없음) 변환하면 그 URL 이 dist 에서 404 가 된다 (seo.py docstring 의
        "소비자가 다르다" 원칙과 같은 결). default_og_image 가 외부 URL
        이거나 assets/ 밖이면 매칭되는 자산이 없어 이 예외는 무동작.
        """
        if not self.assets_dir.is_dir():
            return
        dst_assets = self.dist / 'assets'
        dst_assets.mkdir(parents=True, exist_ok=True)
        default_og = self.site.default_og_image
        for src_file in self.assets_dir.rglob('*'):
            if not src_file.is_file():
                continue
            rel = src_file.relative_to(self.assets_dir)
            dst_file = dst_assets / rel
            # 사이트 기본 og:image 자산은 원본 그대로 (위 docstring 참조).
            is_default_og = ('/assets/' + rel.as_posix()) == default_og
            if self._should_optimize_image(src_file) and not is_default_og:
                self._optimize_and_register(
                    src_file=src_file,
                    dst_file=dst_file,
                    url_prefix='/assets/',
                    rel_path=rel,
                )
            else:
                _copy_if_newer(src_file, dst_file)

    # ── [6b] Home/Category page CSS sync (v0.6.4) ──────────────

    def _sync_page_css(self):
        """v0.6.4: 카테고리/홈 meta.yaml 이 선언한 외부 CSS 파일을 dist 에 복사.

        글 자산은 [5] `_sync_assets` 가 글 폴더를 통째로 복사하므로 별도
        처리 불필요. 카테고리/홈은 폴더 전체 복사 없이 *명시 선언* 된 CSS
        파일만 따로 복사 (자식 글 폴더를 휩쓸지 않으려는 의도).

        복사 매핑:
          - 홈: `Articles/<rel>` → `dist/<rel>` (URL = `/<rel>`).
          - 카테고리: `Articles/<path>/<rel>` → `dist/<slug_path>/<rel>`
            (URL = `/<slug_path>/<rel>`).

        validated_sheets 만 도착하므로 (`_parse_frontmatter` /
        `_parse_category_meta_file` 의 _validate_stylesheets 단계에서 파일
        존재 확인 완료) 여기서 src 가 사라졌으면 빌드 중간의 race — 조용히
        스킵 (issue 는 파싱 단계에서 이미 보고됨).
        """
        # 홈
        for rel in self.home_meta.stylesheets:
            src = self.articles_dir / rel
            if not src.is_file():
                continue
            dst = self.dist / rel
            _copy_if_newer(src, dst)
        # 카테고리 (톱레벨 + 모든 서브)
        for _path_tuple, cat in self.categories.items():
            if not cat.meta.stylesheets:
                continue
            cat_src_dir = self.articles_dir.joinpath(*cat.path)
            cat_dst_dir = self.dist.joinpath(*cat.slug_path)
            for rel in cat.meta.stylesheets:
                src = cat_src_dir / rel
                if not src.is_file():
                    continue
                dst = cat_dst_dir / rel
                _copy_if_newer(src, dst)

    # ── [10] 404 page ─────────────────────────────────────────

    def _build_404(self):
        tpl = _load_template(self.templates_dir, '404.html')
        # v1.1.3: ADSENSE_HEAD line-eating.
        # v1.1.5: page_url='/404.html' — exclude_urls 매칭 시 placeholder 제거.
        tpl = self._apply_adsense_head_placeholder(tpl, '/404.html')
        # v0.5.4: 404 <title> 폴백 체인. 본문 = DEFAULT_ERROR_404_TITLE 상수.
        # 양옆 = site.default_title_prefix/suffix (404 는 meta.yaml 이 없으므로
        # override 불가). v1.4.0: site.yaml error_404_title 키 폐기 — 'Not
        # Found' 외의 표현이 필요할 일이 없어 코드 상수로 흡수.
        page_title = self._wrap_page_title(self.DEFAULT_ERROR_404_TITLE)
        vars_ = {
            'LANG': escape_html(self.site.lang),
            'ADSENSE_HEAD': self.site.google_adsense.head_script,
            'PAGE_TITLE': escape_html(page_title),
            'MAIN_TITLE': escape_html(self.site.main_title),
            'NAV_LINKS': self._nav_links_html(),
            'COPYRIGHT_YEAR': self._copyright_year(),
            'COPYRIGHT_HOLDER': escape_html(self.site.copyright_holder),
        }
        page_html = _render_template(tpl, vars_, report=self.report)
        self.dist.mkdir(parents=True, exist_ok=True)
        (self.dist / '404.html').write_text(page_html, encoding='utf-8')

    # ── [11] robots.txt + ads.txt ────────────────────────────

    def _build_robots(self):
        self.dist.mkdir(parents=True, exist_ok=True)
        (self.dist / 'robots.txt').write_text(
            self.site.robots_txt_main, encoding='utf-8'
        )

    def _build_ads_txt(self):
        """v1.1.3: Google AdSense `dist/ads.txt` 생성.

        site.yaml 의 `google_adsense.ads_txt` 가 비어 있지 않으면 그 본문을
        그대로 `dist/ads.txt` 에 쓴다 (robots.txt 와 같은 패턴). 빈 문자열/
        키 부재 시에는 파일을 만들지 않고, 이전 빌드의 잔존 `dist/ads.txt`
        가 있으면 삭제 (설정을 비웠는데 옛 파일이 살아 있어 stale 정보가
        노출되는 사고 방지 — v0.5.2 의 옛 `dist/src/` 잔재 정리와 같은
        결).
        """
        ads_txt = self.site.google_adsense.ads_txt
        dst = self.dist / 'ads.txt'
        if ads_txt:
            self.dist.mkdir(parents=True, exist_ok=True)
            dst.write_text(ads_txt, encoding='utf-8')
        elif dst.exists():
            dst.unlink()

    # ── [12] sitemap.xml ──────────────────────────────────────

    def _build_sitemap(self):
        # v0.4.6: home_excludes_categories 가 site.yaml 에서 Articles/meta.yaml
        # 로 이전됨. sitemap.py 가 홈 lastmod 계산용으로 그 값을 필요로 하므로
        # home_meta 를 함께 넘긴다.
        xml = build_sitemap(
            self.articles, self.categories, self.site, self.home_meta,
        )
        self.dist.mkdir(parents=True, exist_ok=True)
        (self.dist / 'sitemap.xml').write_text(xml, encoding='utf-8')

    # ── [12b] feed.atom + feed.rss (v0.5.3) ───────────────────

    def _build_feeds(self):
        """v0.5.3: dist/feed.atom 과 dist/feed.rss 를 같은 entry 목록으로 생성.

        scripts/feed.py 가 Atom 1.0 기반 추상 모델 (FeedDocument / FeedEntry)
        과 두 직렬화 (render_atom / render_rss) 를 제공. 빌더는 articles +
        article_render_meta (글 단위 summary 캐시) 를 모아 FeedDocument 하나를
        만들고, 두 파일에 같은 내용을 다른 포맷으로 직렬화한다.

        feed 자체의 updated 는 entry 들 중 가장 최신 lastmod — 빌드 시각이 아닌
        콘텐츠 시각이라야 빌드를 반복해도 산출물이 동일 (결정성 보장).
        """
        def _top_folder(article):
            if article.category_path and len(article.category_path) >= 2:
                return article.category_path[0]
            return None

        # v0.8.2: 버전 디커플링 (B1). v0.8.1 까지 이 한 줄이 `__version__` 이
        # dist 로 새는 유일한 경로였다 — feed.atom/feed.rss 의 <generator>.
        # 그 때문에 문서·구조 전용 릴리스 (v0.7.2 → v0.8.0 → v0.8.1) 는
        # `__version__` 을 '0.7.2' 에 동결해야 byte-동일 검증이 성립했다.
        # generator 문자열에서 버전 토큰을 제거해 `__version__` 의 dist 영향을
        # 영구히 0 으로 만든다. 이후 `__version__` 은 cache global_hash /
        # 콘솔 / build-report.md 전용 (모두 dist 밖) 이고, 릴리스 버전을
        # 자유롭게 추종할 수 있다. 귀속(attribution) 은 그대로 유지.
        # (Atom RFC 4287 / RSS 2.0 모두 <generator> 는 optional — 스펙 유효.)
        generator = 'siheonlee.com — github.com/siheonlee'
        doc = build_feed_document(
            articles=self.articles,
            site=self.site,
            home_meta=self.home_meta,
            article_render_meta=self.article_render_meta,
            category_path_for_article=_top_folder,
            generator=generator,
        )

        self.dist.mkdir(parents=True, exist_ok=True)
        if doc is None:
            # 표시할 entry 가 0 개 — 빈 파일을 만들지 않고 옛 파일은 정리.
            for name in ('feed.atom', 'feed.rss'):
                p = self.dist / name
                if p.exists():
                    p.unlink()
            return

        (self.dist / 'feed.atom').write_text(render_atom(doc), encoding='utf-8')
        (self.dist / 'feed.rss').write_text(render_rss(doc), encoding='utf-8')

    # ── [13] Search index inlined into search.php ────────────
    #
    # v0.6.0: search-index.json 폐기 + search_tokenize.php / search_bm25.php
    # 의 require_once 폐기. 세 파일의 내용 (인덱스 정적 PHP 리터럴 + 토크나이저
    # 함수 + BM25 함수) 이 모두 dist/search.php 한 파일 안에 인라인된다.
    # OPcache 가 search.php 의 바이트코드를 캐시하면 인덱스도 메모리 상주.
    #
    # 결정성: scripts/search.py 의 build_search_index() 가 dict 키를 정렬해
    # 반환하고, php_array_literal() 는 결정적 직렬화를 보장한다. 두 번 빌드
    # 해도 dist/search.php 의 바이트가 동일.
    #
    # 옛 산출물 정리: v0.5.x dist 위에 그대로 빌드하면 search-index.json /
    # search_tokenize.php / search_bm25.php 가 남는다. _build_search 가
    # 이들을 명시적으로 unlink — _prune_orphans 의 슬러그 폴더 정리와 결이
    # 다르기 때문에 여기서 처리.

    def _build_search(self):
        index_data = build_search_index(
            self.articles,
            self.rendered_bodies,
            self.categories,
            self._top_category_for_article,
        )

        self.dist.mkdir(parents=True, exist_ok=True)

        # v0.5.x 의 잔존 파일 정리.
        for legacy in ('search-index.json', 'search_tokenize.php',
                       'search_bm25.php'):
            p = self.dist / legacy
            if p.exists():
                p.unlink()

        tpl_path = self.templates_dir / 'search.php'
        if not tpl_path.exists():
            abort('templates/search.php not found')
        tok_path = self.templates_dir / 'search_tokenize.php'
        if not tok_path.exists():
            abort('templates/search_tokenize.php not found')
        bm25_path = self.templates_dir / 'search_bm25.php'
        if not bm25_path.exists():
            abort('templates/search_bm25.php not found')

        tpl = tpl_path.read_text(encoding='utf-8')
        tok_body = self._inline_php_body(
            tok_path.read_text(encoding='utf-8'),
            strip_cli_block=True,
        )
        bm25_body = self._inline_php_body(
            bm25_path.read_text(encoding='utf-8'),
            strip_cli_block=False,
        )
        index_literal = php_array_literal(index_data)

        # 세 sentinel 코멘트를 정확한 문자열로 치환 (정규식 불필요).
        # 템플릿 파일은 sentinel 이 valid PHP comment 라 IDE 진단 통과.
        tpl = tpl.replace('/* INLINE: SEARCH_TOKENIZE */', tok_body)
        tpl = tpl.replace('/* INLINE: SEARCH_BM25 */', bm25_body)
        # 인덱스 자리는 `/* INLINE: SEARCH_INDEX */ []` 형태로, 기본값 `[]`
        # 까지 한꺼번에 교체 — 인덱스 리터럴은 빈 dict 면 `[]` 이고 아니면
        # `[...]` 이라 어쨌든 expression context 유효.
        tpl = tpl.replace(
            '/* INLINE: SEARCH_INDEX */ []',
            index_literal,
        )

        # v0.5.4: search <title> 폴백 체인. 404 와 동일 — DEFAULT_SEARCH_TITLE
        # 상수 + site.default_title_prefix/suffix. v1.4.0: site.yaml search_title
        # 키 폐기 (404 와 같은 사유 — 'Search' 외의 표현이 필요할 일이 없음).
        search_title = self._wrap_page_title(self.DEFAULT_SEARCH_TITLE)
        # v1.1.3: ADSENSE_HEAD line-eating (search.php 도 사용자가 방문하는
        # dist 페이지이므로 자동광고 스크립트 주입 대상).
        # v1.1.5: page_url='/search.php' — exclude_urls 매칭 시 placeholder 제거.
        tpl = self._apply_adsense_head_placeholder(tpl, '/search.php')
        vars_ = {
            'LANG': escape_html(self.site.lang),
            'ADSENSE_HEAD': self.site.google_adsense.head_script,
            'PAGE_TITLE': escape_html(search_title),
            'MAIN_TITLE': escape_html(self.site.main_title),
            'NAV_LINKS': self._nav_links_html(),
            'COPYRIGHT_YEAR': self._copyright_year(),
            'COPYRIGHT_HOLDER': escape_html(self.site.copyright_holder),
        }
        page = _render_template(tpl, vars_, report=self.report)
        (self.dist / 'search.php').write_text(page, encoding='utf-8')

    _PHP_OPEN_RE = re.compile(r'^\s*<\?php\s*\n')
    _PHP_CLOSE_RE = re.compile(r'\?>\s*$')
    _DECLARE_RE = re.compile(r'^\s*declare\s*\(\s*strict_types\s*=\s*1\s*\)\s*;\s*\n',
                              re.MULTILINE)
    _CLI_BLOCK_RE = re.compile(
        r'//\s*CLI[^\n]*\n\s*if\s*\(\s*PHP_SAPI\s*===\s*\'cli\'.*?\}\s*\n?',
        re.DOTALL,
    )
    # 인라인 시 strip 할 항목 두 개 (v0.6.0):
    #   - 선두의 ════ 배너 + 따라오는 //-주석 블록. 스탠드얼론 source 에선
    #     모듈을 설명하는 헤더지만, search.php 에 인라인되면 parent 의 (a)/(b)/(c)
    #     설명 직후에 같은 톤 헤더가 또 나와 가독성을 해친다.
    #   - search_bm25.php 의 `if (!function_exists('search_tokenize')) { require_once ... }`.
    #     스탠드얼론에서 search_tokenize.php 를 로드하기 위한 dev-time 가드인데,
    #     인라인 결과에선 search_tokenize 가 이미 같은 파일 위쪽에 인라인되어
    #     있으니 function_exists() 가 항상 참 → 가드 안쪽은 실행 자체가 안 됨.
    #     게다가 dist 에 search_tokenize.php 자체가 없어 require_once 가
    #     의미적으로 misleading. 둘 다 인라인 출력에서만 제거하고 source 는 그대로.
    _LEADING_HEADER_BANNER_RE = re.compile(
        r'\A(?:\s*\n)*'                 # 선두 공백 줄
        r'//\s*═{5,}[^\n]*\n'           # 여는 배너 ──── 일정 개수 이상의 ═
        r'(?://[^\n]*\n)*',             # 이어지는 //-주석 줄 전부
    )
    _DEAD_TOKENIZE_REQUIRE_RE = re.compile(
        r'\n?if\s*\(\s*!function_exists\(\s*[\'"]search_tokenize[\'"]\s*\)\s*\)\s*\{\s*\n'
        r'\s*require_once[^\n]*\n'
        r'\s*\}\s*\n',
    )

    @classmethod
    def _inline_php_body(cls, src: str, *, strip_cli_block: bool) -> str:
        """search_tokenize.php / search_bm25.php 의 본문을 search.php 안에
        인라인 가능한 형태로 정리.

        - 선두의 `<?php` 헤더 제거 (이미 parent search.php 가 PHP 컨텍스트).
        - `declare(strict_types=1);` 제거 (parent 에 이미 선언됨).
        - 선두의 ════ 배너 + 따라오는 //-주석 블록 제거 (parent 가 이미 같은
          내용을 설명하므로 인라인 결과에 두 번 등장하면 가독성 저하).
        - `if (!function_exists('search_tokenize')) { require_once ... }` 제거.
          스탠드얼론 source 의 dev-time 가드인데 인라인 결과에선 dead code.
        - 옵션: CLI 모드 if-block 제거 (search_tokenize.php 하단).
        - 끝의 `?>` 가 있으면 제거.
        """
        s = cls._PHP_OPEN_RE.sub('', src, count=1)
        s = cls._DECLARE_RE.sub('', s, count=1)
        s = cls._LEADING_HEADER_BANNER_RE.sub('', s, count=1)
        s = cls._DEAD_TOKENIZE_REQUIRE_RE.sub('\n', s, count=1)
        if strip_cli_block:
            s = cls._CLI_BLOCK_RE.sub('', s)
        s = cls._PHP_CLOSE_RE.sub('', s)
        return s.strip() + '\n'

    # ── v1.4.0: 내부 링크 검증 (post-build) ───────────────────
    #
    # 빌드 후 dist 에 떨어진 글 페이지(글의 index.html / index.php) 의 본문
    # <a href="..."> 를 훑어 site-relative 내부 링크 (`/...` 로 시작) 가
    # 실제로 dist 에 대응 파일/디렉터리 인덱스를 가지는지 확인. 외부 URL
    # (http://·https://·//·mailto:·tel:) 과 순수 앵커(#)·쿼리(?) 시작은 면제.
    # 깨진 링크는 글 단위 issue 로 보고 — 산출물 자체는 빌드 통과지만
    # 클릭 결과가 404 라서 작성자 보완이 필요한 항목 (`<a>` 후속 단계의
    # warn_on_underscore_ref 와 같은 결).
    #
    # 캐시 hit 글에도 동일하게 검사 (cache.lookup 이후의 dist 파일을 읽기
    # 때문) — 따라서 매 빌드마다 결과가 결정적이다.
    #
    # 스코프 v1.4.0 = 글 페이지만. 홈/카테고리/404/search 는 빌더가 직접
    # 만든 링크라 깨질 가능성이 사실상 0 (글 slug 가 _validate 에서 이미
    # 검증). 후속 릴리스에서 필요 시 확장.

    # v1.4.1: 진짜 href 만 잡도록 `\s+href=` (앞에 공백 필수). v1.4.0 의
    # `\bhref=` 는 `-` / `h` 사이도 워드 경계라 `data-href` 같은 데이터 속성을
    # 오매칭했고 (greedy `[^>]*` 가 마지막 hit 를 가져가) `<a href="/A"
    # data-href="/B">` 에서 진짜 href 가 아닌 `/B` 를 추출했다. `\s+` 로 바꾸면
    # 속성 경계를 정확히 인식해 data-* 류는 자동 제외, 진짜 href 만 잡힌다.
    _LINK_HREF_RE = re.compile(
        r'<a\b[^>]*?\s+href=[\'"]([^\'"]+)[\'"]',
        re.IGNORECASE,
    )

    @staticmethod
    def _normalize_link_path(path: str) -> str:
        """링크 path 를 비교 정규형으로. URL-decode + NFC normalize.

        href 는 브라우저가 fetch 할 때 URL-decode 한 뒤 운영체제 파일시스템
        에 묻는다. valid_urls set 은 디스크에서 직접 모은 literal path (NFC
        통일 — 운영체제별 정규화 차이 흡수) 라 비교 정합성을 위해 양쪽 모두
        같은 변환을 거친다.
        """
        from urllib.parse import unquote
        return unicodedata.normalize('NFC', unquote(path))

    def _collect_dist_urls(self) -> set:
        """dist 산출물의 모든 파일을 site-relative URL set 으로. 디렉터리
        인덱스 파일(`index.html` / `index.php`) 은 그 디렉터리의 trailing
        slash URL 도 set 에 추가 — 글/카테고리 링크가 `/blog/` 형태로
        들어오므로. 결과는 NFC 정규화된 literal 경로 (URL-decoded 와 같은
        형태) — _validate_internal_links 가 href 도 같은 변환을 거쳐 비교.
        """
        urls = set()
        if not self.dist.is_dir():
            return urls
        for f in self.dist.rglob('*'):
            if not f.is_file():
                continue
            rel = unicodedata.normalize(
                'NFC', f.relative_to(self.dist).as_posix(),
            )
            urls.add('/' + rel)
            if f.name in ('index.html', 'index.php'):
                parent = unicodedata.normalize(
                    'NFC', f.parent.relative_to(self.dist).as_posix(),
                )
                if parent == '.':
                    urls.add('/')
                else:
                    urls.add('/' + parent + '/')
        return urls

    @staticmethod
    def _is_internal_link(href: str) -> bool:
        if not href:
            return False
        if href.startswith((
            'http://', 'https://', '//',
            'mailto:', 'tel:', 'javascript:', 'data:',
        )):
            return False
        if href.startswith(('#', '?')):
            return False
        return href.startswith('/')

    def _validate_internal_links(self):
        """글 페이지의 <a href> 내부 링크 깨짐을 BuildReport issue 로 보고."""
        if not self.dist.is_dir():
            return
        valid_urls = self._collect_dist_urls()
        broken_total = 0
        for art in self.articles:
            out_dir = self.dist / art.meta.slug
            seen_broken = set()
            for ext in ('html', 'php'):
                p = out_dir / f'index.{ext}'
                if not p.is_file():
                    continue
                try:
                    html = p.read_text(encoding='utf-8')
                except OSError:
                    continue
                for mtch in self._LINK_HREF_RE.finditer(html):
                    href = mtch.group(1)
                    if not self._is_internal_link(href):
                        continue
                    # fragment / query 분리
                    path = href.split('#', 1)[0].split('?', 1)[0]
                    if not path:
                        # 순수 fragment-only 였던 경우 (이미 위에서 컷되지만 안전)
                        continue
                    # URL-decode + NFC 정규화 — 디스크 literal 경로와 비교 정합.
                    norm = self._normalize_link_path(path)
                    if norm in valid_urls:
                        continue
                    if norm in seen_broken:
                        continue
                    seen_broken.add(norm)
                    broken_total += 1
                    self._issue(
                        'article', art.meta.slug,
                        f'본문 내부 링크 깨짐: {href!r} '
                        f'(dist 에 대상 페이지/파일이 없음).',
                        p,
                    )
        if broken_total:
            self._emit(f'        내부 링크 검증: {broken_total} 건 깨짐.')

    # ── [15] Global orphan pruning ────────────────────────────

    def _prune_orphans(self):
        current_slugs = {a.meta.slug for a in self.articles}
        current_cat_slug_paths = {tuple(c.slug_path) for c in self.categories.values()}

        # v0.5.2: 옛 빌드의 `dist/src/` 트리 (v0.5.1 까지의 글 자산 위치) 가
        # 남아 있으면 통째로 제거. v0.5.2 부터 src 는 reserved slug 도 아니다.
        legacy_src_tree = self.dist / 'src'
        if legacy_src_tree.is_dir():
            shutil.rmtree(legacy_src_tree)

        if self.dist.is_dir():
            for d in self.dist.iterdir():
                if not d.is_dir():
                    continue
                name = d.name
                if name == 'assets':
                    continue
                if (d / 'index.html').exists() or (d / 'index.php').exists():
                    if name not in current_slugs:
                        is_cat = any(sp[0] == name for sp in current_cat_slug_paths
                                     if sp)
                        if not is_cat:
                            shutil.rmtree(d)

        # v0.4.5: 서브카테고리 인덱스 페이지가 신설되면서, 서브카테고리 폴더의
        # 잔재도 정리할 필요가 생김. 톱레벨 카테고리 dir 안쪽을 재귀적으로
        # 확인해 현재 self.categories 에 없는 slug_path 의 서브카테고리 인덱스
        # 폴더를 삭제한다.
        for sp in list(current_cat_slug_paths):
            if len(sp) < 1:
                continue
            top_dir = self.dist / sp[0]
            if not top_dir.is_dir():
                continue
            # top_dir 의 직속 자식 폴더 중, 인덱스가 있고 sub_slug_path 에 없으면 삭제.
            for sub in top_dir.iterdir():
                if not sub.is_dir():
                    continue
                expected = (sp[0], sub.name)
                if any(tuple(c.slug_path) == expected
                       for c in self.categories.values()):
                    continue
                # 폴더 안에 index.html 하나만 남아 있는 경우에만 stale 로 간주.
                # (다른 콘텐츠가 있으면 함부로 삭제하지 않음.)
                try:
                    items = list(sub.iterdir())
                except OSError:
                    continue
                if len(items) == 1 and items[0].name == 'index.html':
                    shutil.rmtree(sub)

    # ── Build entry point ─────────────────────────────────────

    def build(self):
        # v0.7.2: 진행 트랜스크립트는 build() 호출마다 새로 시작 (한 인스턴스를
        # 재사용해 build() 를 두 번 불러도 누적되지 않도록 — _report 의
        # reset_report() 와 같은 의도).
        self._console = []
        self._live_pending = False
        self._live_lastlen = 0
        # v1.3.0: 단계별 timing 초기화 (build() 멱등성).
        self._step_times = []
        self._step_current = ()
        self._build_started = datetime.datetime.now()
        self._emit(f'빌드 시작 - siheonlee.com v{_SITE_VERSION} '
                   f'({self._build_started.strftime("%Y-%m-%d %H:%M:%S")})')
        if not self.cache.enabled:
            self._emit('  (증분 캐시 비활성 - --no-cache)')

        # v0.8.2: per-Builder 리포트로 전환 (모듈 전역 폐지). 한 인스턴스를
        # 재사용해 build() 를 여러 번 호출해도 issue/warning 이 누적되지
        # 않도록 빌드 시작 시 새 BuildReport 로 교체. v0.6.5 ~ v0.8.1 의
        # 모듈 전역 reset_report() 와 같은 의도지만, 이제 인스턴스 단위라
        # 두 Builder 가 상태를 공유하지 않는다 (동시 빌드 가능). v0.6.4
        # 까지는 호출자가 명시적으로 reset 을 호출해야 했다 (tests/
        # run_diagnostics.py 의 결정성 섹션처럼).
        self.report = BuildReport()

        # v0.8.2: build() 멱등성 — 빌드 누적 상태 전부 초기화. v0.6.5 가
        # _report 를, v0.7.2 가 _console 을 build() 진입 시 리셋하면서
        # "한 인스턴스를 재사용해 build() 를 여러 번 불러도 누적되지
        # 않는다" 는 의도를 세웠지만, 데이터 컬렉션 (articles /
        # slug_to_article / categories / ...) 은 __init__ 에서만 초기화돼
        # 재사용 시 누적됐다. 그래서 같은 인스턴스로 두 번째 build() 를
        # 하면 _validate 가 같은 slug 를 'slug 중복' 으로 잘못 보고하는
        # 잠복 결함이 있었다 (옛 테스트가 매번 새 Builder 를 써서 가려짐 —
        # v0.8.2 의 BuildReportResetTests.test_same_instance_reuse_… 가
        # 노출). 캐시(self.cache)의 디스크 매니페스트는 빌드 간 의도적으로
        # 영속하므로 여기서 리셋하지 않는다 (별도 설계 — 범위 밖).
        self.site = None
        self.articles = []
        self.slug_to_article = {}
        self.categories = {}
        self.rendered_bodies = {}
        self.home_meta = CategoryMeta()
        self.image_variants = {}
        self.article_render_meta = {}
        self._cache_hits = 0
        self._cache_misses = 0
        # v1.1.5: AdSense exclude_urls 검증용 — 매 페이지 렌더 시
        # _apply_adsense_head_placeholder 가 자기 URL 을 적재한다. 빌드
        # 종료 시점 _check_exclude_urls 가 exclude_urls - seen 차집합을
        # warning 으로 보고 (오타·삭제된 글 감지).
        self._adsense_seen_urls = set()

        # v0.5.1: 이미지 최적화 도입으로 asset 단계가 article render 보다
        # 먼저 와야 한다. asset 단계가 raster 이미지를 webp 변종으로 만들고
        # self.image_variants 를 채우면, _render_articles 가 그 정보로
        # 글 본문 HTML 의 <img> 를 webp + srcset + lazy 로 치환한다.
        # v0.7.2: 16 단계 헤더를 단계 직전에 _emit. 단계 안의 무거운 루프
        # (_sync_assets / _render_articles) 는 _live() 로 in-place 카운터를
        # 추가로 보여준다. `# [n]` 주석은 v0.4.x ~ v0.6.4 의 역사적 파이프라인
        # id (재배치 흔적) 라 그대로 두고, 사용자 대상 진행 번호는 1..16 으로
        # 단조 증가한다.
        self._step(1, '설정 로드 (site.yaml / 토크나이저 패리티)')
        self._load_config()                    # [1]
        self._step(2, '글 폴더 스캔 (Articles/)')
        self._scan_articles()                  # [2]
        self._step(3, 'meta.yaml 파싱')
        self._parse_frontmatter()              # [3]
        self._step(4, '검증 / 카테고리 트리 구축')
        self._validate()                       # [4]
        self._step(5, '자산 동기화 / 이미지 최적화 (WebP)')
        self._sync_assets()                    # [5] (v0.5.1: 옛 [6])
        self._step(6, '사이트 공통 자산 복사')
        self._copy_site_assets()               # [6] (v0.5.1: 옛 [9])
        self._step(7, '카테고리/홈 CSS 복사')
        self._sync_page_css()                  # [6b] (v0.6.4) 카테고리/홈 CSS
        self._step(8, '글 렌더링')
        self._render_articles()                # [7] (v0.5.1: 옛 [5])
        self._step(9, '카테고리 페이지')
        self._build_categories()               # [8]
        self._step(10, '홈 페이지')
        self._build_home()                     # [9]
        self._step(11, '404 페이지')
        self._build_404()                      # [10]
        self._step(12, 'robots.txt / ads.txt')
        self._build_robots()                   # [11]
        self._build_ads_txt()                  # [11b] (v1.1.3) Google AdSense
        self._step(13, 'sitemap.xml')
        self._build_sitemap()                  # [12]
        self._step(14, 'RSS / Atom 피드')
        self._build_feeds()                    # [12b] (v0.5.3) RSS/Atom
        self._step(15, '검색 인덱스 (dist/search.php)')
        self._build_search()                   # [13]
        # v1.1.5: exclude_urls 의 매칭 안 되는 entry 를 warning 으로 보고.
        # 5 페이지 렌더가 모두 끝난 직후라 self._adsense_seen_urls 가 완성된
        # 상태. _step 번호를 추가하지 않는 quiet check — 산출물에 영향 없음.
        self._check_exclude_urls()
        self._step(16, '고아 산출물 정리')
        self._prune_orphans()                  # [14]
        # v1.4.0: 내부 링크 검증 — 글 페이지의 <a href="..."> 가 dist 에 실제
        # 대응 파일/디렉터리를 가지는지 확인. 깨진 링크는 글 단위 issue 로
        # 보고. 단계 번호를 더하지 않는 quiet check (dist 산출물 무영향 — 캐시
        # 히트 글도 동일하게 검사하므로 결정적).
        self._validate_internal_links()
        # v1.3.0: 16 단계 모두 종료 — 마지막 단계 timing 닫기.
        self._step_close()

        # v0.7.0: 캐시 매니페스트 commit. 캐시 비활성 시 no-op.
        self.cache.commit(current_version=_SITE_VERSION)

        art_count = len(self.articles)
        cat_count = len(self.categories)
        issue_count = self.report.issue_count()
        warn_count = self.report.warning_count()
        php_built_count = self.report.php_built_count()
        elapsed = (datetime.datetime.now() - self._build_started).total_seconds()
        self._emit()
        # v1.4.0: PHP 빌드 글 수도 끝줄에 표시 (작성자가 한눈에).
        php_segment = (
            f', PHP 빌드 {php_built_count}건' if php_built_count else ''
        )
        self._emit(
            f'빌드 완료: {art_count} 글, {cat_count} 카테고리, '
            f'{issue_count} 보완 필요, {warn_count} 살펴볼 사항'
            f'{php_segment}. ({elapsed:.1f}s)'
        )
        if self.cache.enabled:
            total_attempts = self._cache_hits + self._cache_misses
            if total_attempts > 0:
                self._emit(
                    f'증분 캐시: {self._cache_hits} 히트 / '
                    f'{self._cache_misses} 미스 (글 {total_attempts}건).'
                )
        self._emit('산출물: dist/ (siheonlee.com).')

        # v0.5.5: 빌드 종료 시 일원화 리포트 출력. meta.yaml 의 필드 부족 /
        # 빈 문자열 / 형식 오류 등 모든 콘텐츠 결함이 여기 모아진다.
        self.report.render()

        # v0.7.2: 터미널에만 뜨던 안내를 파일로도 — build.py 가 있는 폴더
        # (self.base) 에 build-report.md 를 생성. 진행 트랜스크립트 + 요약 +
        # 보완 필요/살펴볼 사항을 마크다운으로 서식화. dist/ 밖이라 빌드
        # 결정성 (run_diagnostics [2]) 과 무관.
        self._write_build_report(art_count, cat_count, elapsed)

    # ── 빌드 리포트 문서 (v0.7.2) ──────────────────────────────

    def _write_build_report(self, art_count: int, cat_count: int,
                            elapsed: float):
        """build-report.md 를 self.base 에 작성.

        구성:
          # siheonlee.com 빌드 리포트
          - 메타 (버전 / 시각 / 소요 / 글·카테고리 수 / 캐시)
          ## 빌드 진행            — _emit 트랜스크립트 (코드 블록)
          ## 보완이 필요한 항목   — BuildReport.render_markdown() 의 issue 절
          ## 살펴볼 사항          — 〃 warning 절
        파일 쓰기 실패는 빌드를 중단시키지 않는다 (리포트 부재는 콘텐츠
        결함이 아니므로 — abort 가 아니라 stderr 경고 + 진행).
        """
        report_path = self.base / 'build-report.md'
        finished = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cache_line = '비활성 (--no-cache)'
        if self.cache.enabled:
            attempts = self._cache_hits + self._cache_misses
            if attempts:
                cache_line = (f'{self._cache_hits} 히트 / '
                              f'{self._cache_misses} 미스 (글 {attempts}건)')
            else:
                cache_line = '활성 (대상 글 없음)'

        lines = []
        lines.append('# siheonlee.com 빌드 리포트')
        lines.append('')
        lines.append(f'- **버전**: v{_SITE_VERSION}')
        lines.append(f'- **빌드 시각**: {finished}')
        lines.append(f'- **소요**: {elapsed:.1f}s')
        lines.append(f'- **결과**: {art_count} 글 · {cat_count} 카테고리')
        meta_line = (
            f'- **보완 필요**: {self.report.issue_count()}건 · '
            f'**살펴볼 사항**: {self.report.warning_count()}건'
        )
        # v1.4.0: PHP 빌드 글 수 노출 (있을 때만).
        if self.report.php_built_count():
            meta_line += f' · **PHP 빌드**: {self.report.php_built_count()}건'
        lines.append(meta_line)
        lines.append(f'- **증분 캐시**: {cache_line}')
        lines.append('')
        lines.append('## 빌드 진행')
        lines.append('')
        lines.append('```')
        lines.extend(self._console)
        lines.append('```')
        lines.append('')
        # v1.3.0: 단계별 시간 표. _step() / _step_close() 가 채운
        # self._step_times 로 16 단계 시간을 직렬화. 빈 경우 (build() 미호출)
        # 생략. 단계 시간은 매 빌드 다른 값이므로 결정성 검증 대상 아님 —
        # build-report.md 자체가 dist 밖이라 무관.
        if self._step_times:
            lines.append('## 단계별 시간')
            lines.append('')
            lines.append('| 단계 | 설명 | 시간(s) |')
            lines.append('|---:|---|---:|')
            for n, label, secs in self._step_times:
                lines.append(f'| {n} | {label} | {secs:.2f} |')
            lines.append('')
        lines.append(self.report.render_markdown())
        lines.append('')
        lines.append('---')
        lines.append('')
        lines.append('_이 문서는 매 빌드마다 자동 생성·갱신됩니다 '
                     '(build.py 가 있는 폴더). dist/ 산출물에는 포함되지 '
                     '않습니다._')
        doc = '\n'.join(lines) + '\n'

        try:
            report_path.write_text(doc, encoding='utf-8')
            self._emit(f'리포트 문서: {report_path.name} 생성 '
                       f'({report_path}).')
        except OSError as e:
            # 파일 쓰기 실패는 콘텐츠 결함이 아니므로 abort 하지 않는다.
            print(f'[경고] build-report.md 작성 실패: {e}',
                  file=sys.stderr, flush=True)

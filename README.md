# siheonlee.com v1.4.1 — 사용설명서

**글마다 폴더 하나**를 만들어 본문·첨부를 관리하고, `python build.py` 한 번으로 사이트를 만드는 **PHP 기반 경량 웹 사이트 생성기**입니다.

| 핵심 가치 | 보장 방법 |
|---|---|
| **URL 영구성** | 글 URL(`slug`)은 카테고리·폴더명과 분리. 글을 옮겨도 URL 불변. |
| **운영 의존성 최소** | 빌드 = Python 3 stdlib (+ Pillow), 런타임 = Apache+PHP. `composer`·클라이언트 JS 없음. |
| **이미지 자동 최적화** | raster → WebP 다중 해상도 srcset + `loading="lazy"` 자동. |
| **서버·콘텐츠 분리** | `.htaccess` 미사용. 라우팅은 Apache VirtualHost 에 한 번만 등록. |
| **페이지 단위 표현 제어** | `meta.yaml` 의 `styles` 로 인라인 미세 조정 + 외부 CSS 파일 + 자기 템플릿까지. |
| **글 단위 색인 제어** | 기본 색인 허용. 빼고 싶은 글만 `noindex: true` 한 줄. |
| **사이트 내 검색** | 클라이언트 JS 0. BM25 + 토크나이저 + 인덱스가 `search.php` 한 파일에 인라인 (OPcache 전제). |
| **다크 모드** | `prefers-color-scheme` 자동 적용. 토글 UI 없음 — OS 설정을 그대로 신뢰. |
| **이전/다음 글** | 같은 부모 폴더 형제를 date 순으로. 사이트 전역 토글. |

> **v1.4.1 한 줄 요약** — v1.4.0 의 안정화 패치. 내부 링크 검증의 `_LINK_HREF_RE` 정규식이 `\bhref=` 워드 경계상 `data-href` 까지 오매칭 + greedy `[^>]*` 가 마지막 매치를 가져가 진짜 `href` 가 아닌 `data-href` 값을 추출하던 결함을 `\s+href=` 로 교정. dist byte-불변 (정규식은 리포트 전용). 단위 425→**429** (회귀 가드 4 추가) · 진단 6/6. 누적 기능은 [§ 16](#16-업데이트-로그) 표.

## 목차

1. [빠른 시작](#1-빠른-시작)
2. [시스템 개요](#2-시스템-개요)
3. [폴더 구조](#3-폴더-구조)
4. [글 작성하기](#4-글-작성하기)
5. [카테고리](#5-카테고리)
6. [글 관리 — 비공개·이동·삭제](#6-글-관리--비공개이동삭제)
7. [빌드](#7-빌드)
8. [산출물 구조와 URL](#8-산출물-구조와-url)
9. [마크다운 문법](#9-마크다운-문법)
10. [SEO 설정](#10-seo-설정)
11. [사이트 전역 설정 — site.yaml](#11-사이트-전역-설정--siteyaml)
12. [내부 구현 — 파서 / 검색 / 피드](#12-내부-구현--파서--검색--피드)
13. [배포](#13-배포)
14. [트러블슈팅](#14-트러블슈팅)
15. [설계 원칙과 한계](#15-설계-원칙과-한계)
16. [업데이트 로그](#16-업데이트-로그)
17. [로컬 글쓰기 — admin.php](#17-로컬-글쓰기--adminphp)
18. [추가 업데이트 제안](#18-추가-업데이트-제안)

---

## 1. 빠른 시작

**준비물**

- **Python 3.x** (3.8+ 권장).
- **Pillow** — raster 이미지를 WebP 다중 해상도로 변환. `pip install Pillow`. 회피하려면 `site.yaml` 의 `images.enabled: false`.
- **PHP CLI** (선택) — 있으면 빌드 시 Python↔PHP 토크나이저 패리티를 자동 검증. 없으면 워닝 후 건너뜀.

**빌드** — 이 폴더에서 터미널을 열고:

```bash
python build.py                # 평소 빌드 (증분 캐시 사용)
python build.py --clean        # dist/, .build_cache/ 모두 폐기 후 빌드
python build.py --clean-cache  # 캐시만 폐기, dist 유지
python build.py --no-cache     # 캐시 비활성
```

성공 시 출력 형태:

```
빌드 시작 - siheonlee.com v1.4.1 (...)
[ 1/16] 설정 로드 (site.yaml / 토크나이저 패리티)
[ 2/16] 글 폴더 스캔 (Articles/)
   …  (각 단계 [ n/16] 헤더, 무거운 단계는 \r 라이브 카운터)
[16/16] 고아 산출물 정리

빌드 완료: 47 글, 19 카테고리, 0 보완 필요, 0 살펴볼 사항, PHP 빌드 N건.
증분 캐시: 0 히트 / 47 미스 (글 47건).
리포트 문서: build-report.md 생성.
```

첫 빌드는 모든 글 miss (캐시 비어있음). 이후 변경 안 된 글은 hit. site.yaml/템플릿/빌더 코드 변경 시 전부 invalidate.

"PHP 빌드 N건" 은 v1.4.0 신설 — `imgBox`/`imgSlideBox` 외에 살아 있는 PHP 구문을 포함해 `index.php` 로 떨어진 글의 수다. 시스템 결함이 아니라 작성자(웹 개발자) 의도 (배포 서버에 PHP 7.4+ 가 깔린다는 전제). 어느 글인지는 `build-report.md` 의 "PHP 로 빌드된 글" 절 참조.

**결과 확인** — 절대경로(`/assets/...`) 라 더블클릭으로는 CSS 가 깨집니다. 로컬 서버로:

```bash
cd dist && python -m http.server 8000   # → http://localhost:8000/
```

---

## 2. 시스템 개요

글마다 폴더 하나를 만들면 `python build.py` 가 정적 HTML + 검색 PHP 를 만들고, Apache 가 그대로 서빙합니다.

```
운영자  빌드 → dist/ 업로드
방문자  ├─ 일반 페이지       → Apache 가 정적 HTML 응답 (빠름)
        └─ /search.php?q=…  → PHP 가 인라인 정적 인덱스로 BM25 검색 → 결과 HTML
```

- **운영 의존성 최소** — Python 3 stdlib (빌드) + PHP (런타임 검색·`.php` 출력 글).
- **글 폴더 = 자율 단위** — 본문·이미지·보조파일을 글 폴더 안에서 자유 관리.
- **URL 영구성** — `slug` 가 곧 URL. 카테고리를 옮겨도 불변.
- **글 단위 스타일·색인** — `meta.yaml` 에서 글마다 독립 제어.

**빌드 파이프라인 (16 단계)** — 빌드 콘솔의 `[ n/16]` 헤더와 `build-report.md` 단계별 timing 표가 같은 번호 체계.

| # | 내용 |
|---|---|
| 1 | `site.yaml` 읽기 + 토크나이저 패리티 검증 (PHP 있으면) |
| 2 | `Articles/` 트리 스캔 |
| 3 | 각 글 `meta.yaml` 파싱 |
| 4 | 검증 (slug 중복/예약어/형식) + 카테고리 트리 구축. 문제 글은 issue 기록 + 그 글만 산출물 제외, 빌드는 계속 |
| 5 | 글별 자산 → `dist/{slug}/` 복사. raster 이미지는 Pillow 로 WebP 변환 (멀티프로세스) |
| 6 | `src/assets/` → `dist/assets/` 복사 (사이트 공통 자산) |
| 7 | 카테고리/홈 외부 CSS 파일 dist 복사 |
| 8 | 글 본문 렌더 (.md 는 파서, .html 은 그대로) → `<img>` 후처리 → styles inject → 템플릿 결합 |
| 9 | 카테고리 색인 (톱레벨 + 서브) |
| 10 | 홈 페이지 |
| 11 | 404 페이지 |
| 12 | `robots.txt` (Sitemap 디렉티브 포함) + `dist/ads.txt` (`google_adsense.ads_txt` 비어있으면 미생성·잔존 자동 삭제) |
| 13 | `sitemap.xml` |
| 14 | `feed.atom` / `feed.rss` (같은 entry 목록) |
| 15 | `dist/search.php` — 3-필드 BM25 인덱스 + 토크나이저 + 점수기 인라인 |
| 16 | 고아 산출물 정리 |

---

## 3. 폴더 구조

```
siheonlee.com_v1.4.1/
│
├── Articles/                ← ★ 모든 글
│   ├── About/                   ← 톱레벨 글 (meta.yaml + content.html + 자산)
│   └── Blog/                    ← 카테고리 폴더
│       └── Hello World/         ← 글 폴더 (폴더명 = 화면 표시명)
│           ├── meta.yaml        ← slug/제목/날짜/styles
│           ├── content.md       ← 본문 (또는 content.html)
│           └── imgs/            ← 첨부 (선택)
│
├── dist/                    ← 빌드 산출물 (배포 대상 / 직접 수정 금지)
│
├── src/                     ← ★ 빌더 일체
│   ├── scripts/                 ← build.py 내부 모듈 (Python 패키지)
│   │   ├── __init__.py             ← __version__ (전역 버전 단일 source)
│   │   ├── yaml_parser.py          ← stdlib only YAML 부분 구현
│   │   ├── models.py               ← dataclass 정의
│   │   ├── slugs.py                ← 폴더명 → URL slug
│   │   ├── parsedown.py            ← Parsedown 1.7.4 Python 포팅
│   │   ├── markdown.py             ← 본문 전·후처리 + PHP 함수 시뮬레이션
│   │   ├── seo.py                  ← <meta> + JSON-LD 빌더
│   │   ├── search.py               ← 토크나이저 / BM25 인덱스 / Py↔PHP 패리티
│   │   ├── sitemap.py              ← sitemap.xml
│   │   ├── feed.py                 ← RSS / Atom 피드 (FeedDocument)
│   │   ├── images.py               ← WebP 변환 + <img> 후처리
│   │   ├── cache.py                ← 글 단위 증분 캐시 (BuildCache)
│   │   ├── report.py               ← BuildReport (issue/warning, render_markdown)
│   │   └── builder.py              ← 빌드 파이프라인 (Builder 클래스)
│   │
│   ├── admin/                   ← ★ 로컬 글쓰기 admin — § 17
│   │   ├── render_one.py            ← 단일 글 본문 렌더 (scripts.markdown 재사용)
│   │   ├── slug_one.py              ← 폴더명 → slug (scripts.slugs 재사용)
│   │   ├── lib/                     ← fs · proc · metayaml · articles (PHP)
│   │   └── views/                   ← layout · list · new · edit · build (PHP)
│   │
│   ├── templates/               ← 페이지 HTML 틀 + PHP 모듈
│   │   ├── article.html / category.html / home.html / 404.html
│   │   ├── search.php              ← 런타임 검색 (라우팅/필터/렌더)
│   │   ├── search_tokenize.php     ← Py↔PHP 공통 토크나이저 (단일 진실원)
│   │   └── search_bm25.php         ← BM25 점수 + 스니펫 (단일 진실원)
│   │                                 (위 둘은 빌드 시 search.php 에 인라인)
│   ├── assets/                  ← 사이트 전역 자산 (/assets/ 로 로드)
│   │   ├── common_template.css / imgslidebox.js / pagination.js
│   │
│   └── tests/                   ← 단위 테스트 (390) + run_diagnostics.py (6 항목)
│
├── admin.php                ← 로컬 글쓰기 진입점 (얇은 라우터 — § 17, dist 미포함)
├── build.py                 ← 빌드 진입점 (자기 폴더의 src/ 를 sys.path 에 올림)
├── README.md                ← 이 문서
└── site.yaml                ← 사이트 전역 설정

빌드 시 프로젝트 루트에 자동 생성 (.gitignore 권장):
  build-report.md   ← 진행 트랜스크립트 + 요약 + 보완 항목 + 단계별 timing (dist/ 밖)
  .build_cache/     ← 글 단위 증분 캐시 + tokenizer parity 캐시
```

> **중요:** `dist/` 안의 파일은 매 빌드마다 덮어씌워집니다. 수정은 `Articles/`·`src/templates/`·`src/assets/`·`site.yaml` 에서 하고 다시 빌드하세요.

---

## 4. 글 작성하기

### 4-1. 글 폴더 만들기

`Articles/` 안의 카테고리 폴더 아래에 새 폴더를 만들고 `meta.yaml` + `content.md`(또는 `content.html`) 를 둡니다.

- 폴더명: 한국어·영어·공백·특수문자 모두 가능. **폴더명이 화면 표시명** (링크 텍스트).
- 폴더명은 URL 에 쓰이지 않음 — URL 은 `meta.yaml` 의 `slug` 가 결정.

### 4-2. meta.yaml

```yaml
# ── 필수 ──
slug: my-first-post          # URL 식별자. 사이트 전역 유일
title: 나의 첫 번째 글        # 본문 상단 + <title>
date: 2026-05-07             # 최초 발행일 YYYY-MM-DD

# ── 선택 ──
updated: 2026-06-01          # 수정일. date 이후여야 함
noindex: true                # 이 글만 검색엔진 제외
tags: [intro, sample]        # 주제어 (feed <category> 에 사용)
use_common_css: false        # 사이트 공통 CSS link 끊기 (기본 true)
lang: en                     # 이 글만 <html lang> 오버라이드 (비면 site.lang)

seo:                         # 모든 하위 키 선택
  title_prefix:              #   <title> 앞/뒤. 비면 site 디폴트
  title_suffix:
  description:               #   검색·SNS·피드 summary (사실상 필수)
  author:                    #   비면 site.default_author
  canonical:                 #   비면 자동 생성
  og_title:                  #   비면 <title>
  og_description:            #   비면 description
  og_image:                  #   비면 site.default_og_image
  og_image_alt:
  og_type: article
  twitter_card: summary_large_image
  twitter_image:
  jsonld:                    #   글 단위 JSON-LD opt-out (false 면 미출력)
                             #   비면 site.yaml jsonld.enabled 따름

styles:                      # § 4-6 — 인라인 미세 + 외부 CSS 두 채널
  # 1: style.css             #   정수 키 = 외부 CSS 파일 (글 폴더 안)
  p:                         #   문자열 키 = 인라인 룰
    text-indent: 0
    line-height: 1.7em
```

**slug 규칙** — 영어 소문자·숫자·하이픈만, 시작/끝은 영숫자, 사이트 전역 유일, 예약어(`assets`/`search`) 불가, 카테고리와 무관.

`seo.description` 은 누락/빈 문자열 시 빌드는 통과하지만 BuildReport issue 에 기록됩니다 (사실상 필수). 단 `noindex: true` 글은 SERP·피드 미노출이라 검사 면제. `<meta name="keywords">` 는 제공하지 않습니다 (검색엔진이 무시).

`seo.jsonld` — 글 단위 JSON-LD 토글. 비우면 `site.yaml` 의 `jsonld.enabled` (기본 켜짐) 를 따름. `false` 면 이 글만 `<script type="application/ld+json">` 미출력. 사이트를 끄면 글 단위 `true` 로 되살릴 수 없음 (사이트 토글이 마스터). § 10 참조.

**메타데이터에 `{{대문자}}` placeholder 금지** — `title` · `seo.description` · `tags` · `seo.author` 는 빌더 템플릿 치환(`_render_template`)을 거쳐 `<meta>` · OG · Twitter · JSON-LD 로 동일하게 흘러갑니다. 이 네 필드에 **공백 없는 리터럴 `{{이름}}`** (이름이 대문자/언더스코어로 시작·구성 — 정규식 `{{[A-Z_][A-Z0-9_]*}}`) 을 쓰지 마세요. 빌더 변수명(`{{COPYRIGHT_YEAR}}` · `{{PAGE_TITLE}}` · `{{MAIN_TITLE}}` · `{{NAV_LINKS}}` · `{{BODY}}` 등)과 정확히 일치하면 그 변수 값이 산출물에 조용히 끼어들고, 변수 아닌 대문자 토큰이면 빈 문자열로 strip + 빌드 리포트에 경고가 납니다. 안전한 형태 — 소문자 `{{foo}}` · 안쪽 공백 `{{ FOO }}` · 홑 중괄호 `{NAME}` · 숫자 시작 `{{1A}}` · 비-ASCII `{{변수}}` 는 전부 무해. 그 외 문자(`"` `\` `<` `>` `&` · 개행 · 한글 · 이모지)는 자동 이스케이프.

### 4-3. content.md (마크다운)

파서는 [src/scripts/parsedown.py](src/scripts/parsedown.py) (Parsedown 1.7.4 Python 포팅). 표준 CommonMark 에 가까운 문법 + 이 시스템 전용 문법 (§ 9).

**이미지 경로** — 글 폴더 기준 상대경로. 빌드 시 절대경로로 자동 변환:

```markdown
![photo](./imgs/photo.jpg)   →   <img src="/my-slug/imgs/photo.jpg" alt="photo">
![외부](https://example.com/i.jpg)   ← 외부 URL 은 변환 안 함
```

**섹션 마커** — 본문을 `<div class='gap'><p>부제</p></div><section>…</section>` 패턴으로 나눕니다:

- `===텍스트===` (라인 단독) — 이전 섹션 닫기 + 새 갭(텍스트) + 새 섹션 열기.
- `======` (등호 정확히 6개) — 현재 섹션 명시적 닫기 (그 뒤 본문은 어느 섹션에도 안 속함).
- 코드 블록 안의 `===` 는 무시. 본문 시작에는 항상 자동 첫 갭(글 `title`) + 첫 섹션. 닫힘 누락은 빌더가 자동 보정.

### 4-4. content.html (HTML 본문)

`<html>/<head>/<body>` 없이 본문 조각만 씁니다. 기존 HTML 글 마이그레이션용.

> **갭+섹션은 직접 작성.** content.html 은 작성한 HTML 이 **그대로** 들어갑니다 — 마크다운의 자동 wrap·섹션 마커가 작동하지 않습니다. 예: [Articles/About/content.html](Articles/About/content.html).

> **content.md / content.html 동시 존재 금지** (빌드 중단).

**PHP 함수 자동 변환** — 두 함수를 HTML 로 변환:

```html
<?php imgBox("./imgs/p.jpg", "캡션", "alt") ?>
  → <div class="imgBox"><img src="/my-slug/imgs/p.jpg" alt="alt"><p class="caption">캡션</p></div>

<?php imgSlideBox("./src_slide") ?>
  → src_slide/ 안 이미지를 알파벳 순 슬라이드로 (하단 중앙 dot 인디케이터, JS 런타임 생성)
```

다중 구문 `<?php … imgBox(); imgBox(); … ?>` 블록도 imgBox/imgSlideBox 만 들어 있고 그 외 살아있는 구문이 없으면 통째로 정적 HTML 로 시뮬레이션 (주석·`global` 선언·`;` 무시). 다른 함수 호출이 섞여 있으면 블록 원문 보존 → 글이 `.php` 확장자로 출력 (§ 8 PHP 자동 감지).

캡션 안의 `{$name}` 은 `site.yaml` 의 `php_globals` 로 빌드 시 치환 (§ 11). 캡션은 raw HTML 보존 (`<br>`·`&nbsp;`·`<a>` 사용 가능), `alt` 는 속성값이라 이스케이프.

### 4-5. 자산 첨부

- **글 단위 자산** — 글 폴더 안에 둡니다. `meta.yaml`/`content.*` 와 `_`·`.` 접두 항목을 제외한 모든 파일·폴더가 `dist/{slug}/` 로 복사 (URL `/{slug}/imgs/…`). `_`·`.` 접두 파일/하위폴더는 비공개로 보고 복사하지 않습니다 (§ 6).
- **사이트 전역 자산** — 여러 글이 공유하는 CSS/JS/파비콘/로고/기본 OG 이미지는 `src/assets/` 에. `dist/assets/` 로 복사되어 `/assets/{경로}` 로 로드.

### 4-6. styles — 글 단위 CSS

`meta.yaml` 의 같은 `styles:` 키 아래 **두 채널**이 *키 타입*으로 자동 분기됩니다:

| 채널 | 키 형태 | 값 | 출력 | 의도 |
|---|---|---|---|---|
| 인라인 룰 | 문자열 (태그/선택자) | dict | head `<style>` | 자주 쓰는 속성 미세 override |
| 외부 CSS | 정수 (1,2,3…) | 글 폴더 안 상대경로 | head `<link>` | 자기 CSS 파일 (정수 오름차순) |

**로드 순서:** `common_template.css` → 외부 CSS (정수 키 순) → 인라인 `<style>`. 인라인이 마지막 발언권.

```yaml
styles:
  1: layout.css                     # 외부 CSS
  p: { text-indent: 0 }             # 인라인 (자동으로 section p 로 wrap)
  "section p > strong": { color: "#d33" }   # 복합 선택자는 wrap 안 함
  "p:hover": { color: "#0172d5" }   # :, #, ', " 는 YAML 인용 필요
```

- 태그 키(p, h3, ul, blockquote, a, code …)는 자동으로 `section TAG` 선택자로 wrap → `common_template.css` 의 같은 선택자를 source order 로 덮음.
- 공백·`>`·`+`·`~`·`,`·`.`·`[attr]` 가 키에 있으면 그대로 선택자로 사용.
- **인라인 채널 한계 (의도된 제약 — 외부 CSS 로 승격):** `@media`/`@keyframes`/`@font-face` 등 at-rule, CSS 중첩, 한 속성 다줄 작성, 값 옆 인라인 주석.
- **`use_common_css: false`** — 사이트 공통 CSS link 자체를 끊음 (랜딩페이지/단일 서비스용). 기본 `true`.
- **specificity 함정** — `common_template.css` 에 더 구체적인 규칙(예 `body section p`)이 있으면 더 구체적 셀렉터를 쓰거나 `!important`.

---

## 5. 카테고리

`Articles/` 아래 폴더 구조가 그대로 카테고리. 별도 설정 없이 **폴더 = 카테고리**. 빌더는 `content.md`/`content.html` 유무로 글 폴더와 카테고리 폴더를 구분 (둘 다 없으면 카테고리).

**폴더명 → slug 변환:** 비ASCII 문자 → 4자리 hex 코드포인트, NFKD 정규화, 영숫자·공백·하이픈만 유지, 괄호 제거, 공백·연속 하이픈 → 단일 하이픈, 소문자.

```
Blog               → blog
3D Printing        → 3d-printing
Research Notes (CS) → research-notes-cs
블로그              → be94-b85c-adf8   (비ASCII → hex, 빌드 워닝. ASCII 폴더명 권장)
```

**색인 페이지** — 모든 카테고리(대·소분류)가 자기 인덱스 생성. 톱레벨은 자식 서브카테고리를 section 으로 임베드 + 직속 글 section. 톱레벨 카테고리 페이지의 자식 소분류 헤더는 그 소분류 페이지로 가는 링크(`color: inherit; text-decoration: none`, 호버 효과 없음 — 링크지만 본문 글씨와 동일 외양). 글 없는 카테고리는 인덱스 미생성 + 빌드 경고.

**카테고리 폴더의 meta.yaml** (모두 선택, 글과 형식 다름 — `slug`/`date` 없음):

| 필드 | 기본 | 설명 |
|---|---|---|
| `per_page` | site `category_per_page` (20) | 자기 인덱스 페이지의 페이지당 글 수 |
| `preview_per_page` | site `category_preview_per_page` (5) | 상위에 section 임베드될 때 글 수 |
| `layout` | `list` | `list` / `gallery` (이미지 타일). 그 외는 list 폴백 |
| `styles` | {} | 글 `styles` 와 동일 두 채널 |
| `use_common_css` | `true` | |
| `template` | `category.html` | `name.html`→`src/templates/`, `./name.html`→폴더 |
| `lang` | site `lang` | `<html lang>` 오버라이드 |
| `title` | 폴더명 | 인덱스 `<title>` 본문 |
| `seo` | {} | 글 `seo:` 와 동일 (메타 태그 출력) |
| `priority` | `0` | 상위 인덱스 내 형제 section 정렬 (큰 값 먼저) |
| `nav_priority` | `0` | 톱레벨 nav 정렬 (priority 와 별개 축) |

**`layout: gallery`** — 글 목록을 이미지 타일로 (CSS Grid `auto-fill, minmax(220px,1fr)`, 4:3 크롭, subtle hover, 모바일 2열). 썸네일: `seo.og_image` → `site.default_og_image` → 빈 플레이스홀더. WebP srcset 자동 부착.

추가 layout 이 필요하면 [src/scripts/builder.py](src/scripts/builder.py) 의 `_listup_items_html`/`_render_section` 분기 + [src/assets/common_template.css](src/assets/common_template.css) 의 `section.listup-{layout}` + pagination.js selector 에 직접 등록.

---

## 6. 글 관리 — 비공개·이동·삭제

- **비공개** — 파일/폴더명 앞에 `_` 또는 `.`. 경로의 어느 세그먼트든 `_`·`.` 접두면 그 아래 전체가 글·카테고리·nav·자산에서 모두 제외. 빌드 시 `dist/{slug}/` 자동 삭제. `_` = 의도적 비공개·편집 중, `.` = OS/VCS 숨김(`.git`·`.DS_Store`) **그리고** `.draft` 처럼 작성자가 "숨겼다" 고 믿는 폴더가 실수로 공개되는 길을 막음.
- **이동** — 글 폴더를 다른 카테고리로 옮겨도 `slug` 가 같으면 URL 불변.
- **삭제** — 글 폴더 삭제 후 빌드하면 `dist/{slug}/` 자동 정리 (고아 정리).

위 작업을 파일 탐색기 대신 브라우저로 하려면 [§ 17 admin.php](#17-로컬-글쓰기--adminphp). 같은 규약을 그대로 따른다 (이동=폴더 rename·slug 불변, 비공개=`_` 접두, 삭제=`.trash` 이동으로 빌드 자동 제외·복구 가능).

---

## 7. 빌드

```bash
python build.py            # 일반 빌드 (증분 캐시)
python build.py --clean    # dist/ + .build_cache/ 폐기 후 빌드
```

**빌드 리포트** — 콘텐츠 결함은 빌드를 중단시키지 않고 *글 단위로 산출물 일부 누락* 후 완성. 종료 시 stderr 에 묶음별로 정렬 + `build-report.md` 영속:

| 분류 | 의미 | 사례 |
|---|---|---|
| **issue** (보완 필요) | 작성자가 손볼 글 단위 문제. 그 글만 부분 누락 | `seo.description` 누락(noindex 글은 면제), slug 정규식/예약어/중복 충돌, date 형식 오류, `tags` 비-list, **본문 내부 링크 깨짐**(v1.4.0 — `<a href="/...">` 가 dist 에 대응 파일/디렉터리 인덱스 없음) |
| **warning** (살펴볼 사항) | 산출물 정상, 한 번 볼 가치 | 비ASCII 폴더명 hex 변환, 자산 누락, 빈 카테고리, 이미지 최적화 실패, AdSense `exclude_urls` 매칭 0 entry, `_` 접두 자산 참조(v1.4.0 부터 항상 경고 — 옛 `warn_on_underscore_ref` 토글 폐기) |
| **PHP 로 빌드된 글** (v1.4.0) | issue/warning 이 아니라 *의도된 출력 보고*. 어느 글이 `.php` 로 떨어졌는지 한눈에 — 작성자(웹 개발자)의 명시적 PHP 사용 추적용 | `imgBox`/`imgSlideBox` 외에 살아 있는 `<?php`/`<?=` 구문이 본문에 남은 글 |

`build-report.md` 에는 단계별 timing 표도 직렬화되어 어느 단계가 시간을 먹는지 한눈에 보인다 (리포트는 `dist/` 밖이라 결정성 무관).

**빌드 중단 (시스템 결함만)** — 콘텐츠 작성자가 통제 못 하는 결함만 즉시 중단:

```
[ABORT] templates/article.html 을 찾을 수 없습니다
빌드 중단 (시스템 결함).
```

**위 경우 (시스템 결함):** 템플릿 누락 / `Articles/` 디렉터리 없음 / `site.yaml` 부재·파싱 실패 / `images.enabled: true` 인데 Pillow 미설치 — *단 변환할 raster 이미지가 실제로 존재할 때만* 중단 (raster 가 한 장도 없으면 워닝 후 빌드 통과).

---

## 8. 산출물 구조와 URL

```
dist/
├── index.html  404.html  robots.txt  ads.txt  sitemap.xml  feed.atom  feed.rss
├── assets/                  ← 사이트 전역 자원
├── {slug}/                  ← 글 페이지 + 글 자산 (같은 폴더)
│   ├── index.html  (또는 index.php)
│   └── imgs/ …
├── blog/                    ← 카테고리 색인
│   ├── index.html
│   └── tutorials/index.html ← 서브카테고리
└── search.php               ← 인덱스+토크나이저+BM25 모두 인라인
```

| 페이지 | URL | 예시 |
|---|---|---|
| 홈 | `/` | `https://siheonlee.com/` |
| 글 | `/{slug}/` | `/mask-intake-3d-printing/` |
| 카테고리 톱레벨 | `/{cat}/` | `/blog/` |
| 카테고리 서브 | `/{top}/{sub}/` | `/blog/tutorials/` |
| 글 첨부 | `/{slug}/{경로}` | `/mask-intake-3d-printing/imgs/p.jpg` |
| 전역 자산 | `/assets/{경로}` | `/assets/common_template.css` |
| 시스템 | `/404.html` `/robots.txt` `/sitemap.xml` `/ads.txt` | |

- 모든 글·카테고리 URL 은 `/` 로 끝남. 슬래시 없는 URL 은 Apache 가 301 리다이렉트.
- 글 URL 은 카테고리와 독립. 단 slug 예약어(`assets`/`search` — v1.4.0 부터 `Builder.RESERVED_SLUGS` 코드 상수)는 불가.
- **PHP 자동 감지** — 렌더 결과에 `<?php`/`<?=` 가 남으면 `index.php` 로 출력. URL 은 `/{slug}/` 동일, Apache `DirectoryIndex` 가 처리. v1.4.0 부터 BuildReport 가 "PHP 로 빌드된 글" 별도 카테고리로 명시 표시 — 시스템 결함이 아니라 작성자(웹 개발자) 의도 (배포 서버에 PHP 7.4+ 가 전제).

---

## 9. 마크다운 문법

표준 CommonMark 에 가까움 — 헤딩(`#`~`######`, Setext), 인라인(`**굵게**` `*이탤릭*` `~~취소선~~` `` `코드` ``), 링크/이미지/참조링크/자동링크, 목록(중첩), 인용(중첩), 표(`:---`/`:---:`/`---:` 정렬), 구분선, 블록 레벨 HTML 통과. 코드 블록 안의 `<>&` 자동 escape (`<?php` 실행 안 됨).

**이 시스템 전용 문법:**

```markdown
===섹션 제목===          섹션 마커 (§ 4-3). ======(등호 6개)는 명시적 닫기
![[이미지 설명]](./imgs/p.jpg) {캡션}   → <div class="imgBox"><img …><p class="caption">캡션</p></div>
```

캡션이 필요 없으면 `{...}` 생략. 이미지 박스 문법은 빌드 직전 raw HTML 로 변환 후 파서로 전달.

---

## 10. SEO 설정

글/홈/카테고리가 같은 폴백 체인을 공유 (한 함수 [`build_meta_tags`](src/scripts/seo.py)). 본문 title: 글=`meta.title`, 홈=`Articles/meta.yaml title`>`site.name`, 카테고리=`meta.title`>폴더명.

| 출력 태그 | 1순위 | 2순위 | 3순위 |
|---|---|---|---|
| ◆ `<title>` | `{prefix}{title}{suffix}` | site 디폴트 prefix/suffix | — |
| ● `meta description` | `seo.description` | — | 생략 + issue 기록 (noindex 글 면제) |
| `meta author` | `seo.author` | `site.default_author` | 생략 |
| ■ `link canonical` | `seo.canonical` | 자동 (글 `/{slug}/`, 홈 `/`, 카테고리 `/{top}/{sub}/`) | — |
| ◆ `og:title` | `seo.og_title` | `<title>` 결과 | — |
| ● `og:description` | `seo.og_description` | `meta description` 결과 | 생략 |
| ▲ `og:image` | `seo.og_image` | `site.default_og_image` | 생략 |
| ◆ `og:image:alt` | `seo.og_image_alt` | 페이지 title | 생략 |
| `og:type` | `seo.og_type` | 글=`article`, 홈/카테고리=`website` | — |
| ■ `og:url` / `og:site_name` | canonical / `site.name` | — | — |
| `article:published/modified_time` | 글 `date` / `updated`(없으면 date) — 글에만 | — | — |
| `twitter:card` | `seo.twitter_card` | `summary_large_image` | — |
| ◆●▲ `twitter:title/description/image` | (og 와 동일) / `seo.twitter_image`→og:image | — | 생략 |

**기호 그룹** — 같은 기호 = 최종적으로 같은 값으로 수렴하는 체인: ◆ = `<title>` 값 · ● = `meta description` 값 · ▲ = `og:image` 값 · ■ = `canonical` 값.

**폴백 결과가 빈 문자열이면 태그 자체를 출력 안 함.** `seo.description` 만 `''` 를 작성자 실수로 간주해 BuildReport 에 기록 (단 `noindex: true` 글은 검사 면제 — SERP·피드 미노출이라 무의미).

**색인 정책** — 기본 색인 허용. `noindex: true` 글만 그 페이지 `<head>` 에 `<meta robots noindex>`. search.php 만 `noindex,follow` 별도 차단. `noindex: true` 글은 sitemap.xml·`search.php` 인덱스 + (피드 윈도우 안이면) RSS/Atom 피드에서도 제외.

**기본 og:image 자산** — `site.default_og_image` 가 가리키는 자산은 raster 여도 빌드가 webp 변환·srcset 등록을 **건너뛰고 원본 그대로** `dist/` 에 낸다 (`_copy_site_assets` 예외). og:image 소비자는 `<img>` 후처리가 아니라 SNS 링크 언퍼ler — `og:image` 메타의 고정 URL 하나만 가져가므로 다중 해상도가 무의미하고, KakaoTalk·일부 Facebook 은 WebP og:image 를 렌더하지 못한다. 기본 자산은 `src/assets/default-og.png` (1200×630, 표준 OG 규격). `default_og_image` 가 외부 URL 이거나 `assets/` 밖이면 이 예외는 무동작 (파일 배치는 작성자 책임).

**JSON-LD 구조화 데이터** — **글 페이지**의 `<head>` 에 `<script type="application/ld+json">` 한 줄. `@graph` 로 두 노드:

- `Article` — `headline`(글 title) / `datePublished`(date) / `dateModified`(updated>date) / `description`(`seo.description`, 부재 시 키 생략) / `author`(`seo.author`>`site.default_author`, Person) / `publisher`(`site.name`, Organization) / `image`(`og:image` 와 같은 해석) / `keywords`(`tags`) / `inLanguage`(글 lang) / `url`·`mainEntityOfPage`(canonical).
- `BreadcrumbList` — 사이트 nav-tracker 와 **단일 공유 소스** (같은 라벨·경로, 어긋날 수 없음). 각 조상 카테고리는 자기 중첩 인덱스 URL (`/{top}/…/{cat}/`) 로 링크. 마지막(현재 글)은 글 **제목**(= `Article.headline`) 을 이름으로 쓰고 schema.org 권장대로 `item` 생략. crumb 가 2개 미만(톱레벨 글)이면 노드 자체 생략.

기존 `<meta>`/OG/Twitter 를 **대체하지 않고 보강** — 소비자가 다르다 (SNS 언퍼ler=OG, SERP 스니펫=`meta description`, 색인 제어=`robots` meta, 검색 엔진 리치 결과=JSON-LD). `description`/`image`/`author` 는 `build_meta_tags` 와 같은 폴백을 공유. **off**: `site.yaml`→`jsonld.enabled: false` (전역) 또는 글 `seo.jsonld: false`. 홈/카테고리에는 출력하지 않는다 (`article.html` 만 `{{JSONLD}}` 보유).

---

## 11. 사이트 전역 설정 — site.yaml

*진짜 전역* (여러 페이지 공통) 만 둡니다. **페이지 한 종 전용 설정은 그 페이지의 meta.yaml 에:**

| 위치 | 설정 |
|---|---|
| `site.yaml` | 도메인·name·copyright·lang·default_og_image / `category_per_page`·`category_preview_per_page` / robots.txt / `description_truncate` / `images:` / `jsonld:` / `prev_next:` (v1.4.0) / `php_globals:` / `google_adsense:` |
| `Articles/meta.yaml` | 홈 전용 — `per_page` `excludes_categories` `lang` `layout` `styles` `title` `seo:` |
| `Articles/<cat>/meta.yaml` | 카테고리 전용 (§ 5 표) |
| `Articles/<cat>/<글>/meta.yaml` | 글 전용 (§ 4-2) |

> **v1.4.0 폐기** — `reserved_slugs` · `warn_on_underscore_ref` · `warn_on_missing_asset` · `error_404_title` · `search_title` 다섯 키는 코드 상수로 승격됐다 (`src/scripts/builder.py`의 `RESERVED_SLUGS` / `DEFAULT_ERROR_404_TITLE` / `DEFAULT_SEARCH_TITLE`, 그리고 항상-경고 행동 고정 + dead config 정리). 옛 site.yaml 에 키가 남아 있어도 파서가 silently 무시한다.

```yaml
domain: siheonlee.com
base_url: https://siheonlee.com
name: Lama
main_title: Lama
default_author: 이시헌
default_og_image: /assets/default-og.png
lang: ko                              # 모든 페이지 <html lang> 디폴트
default_title_prefix: ""              # 모든 페이지 <title> prefix/suffix
default_title_suffix: ""
copyright_holder: 이시헌
copyright_year_start: 2025
category_per_page: 20                 # 카테고리 페이지네이션 디폴트
category_preview_per_page: 5
description_truncate: 150             # 피드 summary 절단 최대 글자 (단어 경계 존중)
robots_txt_main: |
  User-agent: *
  Allow: /

  Sitemap: https://siheonlee.com/sitemap.xml
images:                               # 이미지 자동 최적화 (생략 시 아래 기본값)
  enabled: true                       #   false 면 Pillow 없이 빌드 통과
  widths: [400, 800, 1600]            #   생성할 WebP 변종 너비
  max_width: 1600
  quality: 85
  lazy_loading: true                  #   enabled=false 여도 독립 동작
  default_sizes: "(max-width: 800px) 100vw, 800px"
jsonld:                               # schema.org JSON-LD (생략 시 켜짐)
  enabled: true                       #   false 면 모든 글에서 ld+json 미출력
                                      #   (글 단위는 meta.yaml seo.jsonld: false)
prev_next:                            # v1.4.0: 글 푸터 이전/다음 글 nav (생략 시 켜짐)
  enabled: true                       #   sibling 풀 = 같은 부모 폴더의 non-noindex
                                      #   글, date asc 정렬. 글 단위 끄기 없음.
php_globals:                          # PHP 서명 변수 (생략 시 보간 없음)
  reference_hanbyeol: "Character illustration by 김한별 (kakao ID: zzang767401)"
  reference_hanbyeol_webDesign: "Illustration and Web Design by 김한별 (kakao ID: zzang767401)"
#   정본 lama.pe.kr 의 PHP/GlobalVariables.php(auto_prepend) 가 런타임에
#   채우던 서명 변수. 정적 빌드엔 그 런타임이 없으므로 여기 옮겨 적으면
#   글 본문 imgBox 캡션 안의 {$reference_hanbyeol} 등을 빌드 시 치환한다
#   (미정의 변수 = 빈 문자열, PHP 미정의 echo 동등). 변수명 앞 $ 는 생략.
google_adsense:                       # Google AdSense
  ads_txt: |                          #   빈 문자열 → dist/ads.txt 미생성·잔존 자동 삭제
    google.com, pub-XXXXXXXXXXXXXXXX, DIRECT, fXXXXXXXXXXXXXXXX
  head_script: |                      #   빈 문자열 → 5 페이지 head 에 미주입(라인 자체 strip)
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXXXXXXXX"
         crossorigin="anonymous"></script>
  exclude_urls: ['/404.html', '/search.php', '/about/']   # 비주입할 URL / [] 면 5 페이지 전체 주입
#   ads_txt 는 dist/ads.txt 로 그대로 기록 (robots.txt 와 같은 패턴);
#   head_script 는 5 템플릿 (article·home·category·404·search.php) <head>
#   에 raw 그대로 주입 (escape 없음). 둘 다 빈 문자열/키 부재 시 자동 비활성
#   — SeoMeta 의 3-state 원칙 일관이며 별도 enabled 마스터 토글 없음.
#   admin.php·src/admin/ 은 빌더가 Articles/ 만 스캔하므로 자연 제외.
#   exclude_urls: site-relative 절대 URL ('/' 로 시작) 리스트. 매칭된
#   URL 의 페이지 head 에 로더 스크립트가 들어가지 않음 = Google auto-ads JS
#   미로드 = 광고 원천 차단. 매칭은 case-sensitive · trailing-slash 포함 정확
#   일치 — canonical URL 형식: 홈=/, 글=/<slug>/, 카테고리=/<slug_path>/,
#   404=/404.html, 검색=/search.php. 매칭 안 되는 entry (오타·삭제된 글) 는
#   build-report.md "살펴볼 사항" 으로 자동 보고. 글 단위 차단도 가능 (예: /about/).
```

**Articles/meta.yaml** (홈 전용, 선택 — 없으면 `per_page=10`, `excludes_categories=[]`):

```yaml
per_page: 5                  # 메인 Recent posts 페이지당 글 수
excludes_categories: [About] # Recent 에서 제외할 톱레벨 (About 등)
layout: list                 # list / gallery
# lang: ko
# styles: { 1: home.css, p: { line-height: 1.7em } }
# use_common_css: true
# template: my_landing.html   # templates/ 또는 ./Articles/ 안
```

> 카테고리 meta.yaml 과 같은 스키마를 공유 — 홈에서 `preview_per_page`/`priority` 는 임베드 대상이 없어 무시 (의도된 비대칭).

---

## 12. 내부 구현 — 파서 / 검색 / 피드

### 마크다운 파서 — Parsedown 1.7.4 Python 포팅

단일 구현 [src/scripts/parsedown.py](src/scripts/parsedown.py) 만 사용.

```
content.md → preprocess (![[...]]{...} → HTML) → Parsedown().text()
           → finalize (asset 경로 재작성, PHP 시뮬레이션) → RenderResult(html)
```

- 원본: [Parsedown](http://parsedown.org) 1.7.4 (c) Emanuil Rusev, MIT. 포팅은 메서드명·dispatch·dict 키까지 원본과 일대일. 외부 의존성 없음 (stdlib `re`/`typing`).
- PHP Parsedown 과 79/79 fixture 바이트 일치 (합성 46 + 실 글 33).
- **운영 정책 — 포크.** 이 포팅이 단일 진실원. 원본 신버전을 따라가지 않으며 모든 수정은 이 포팅에 직접. PHP 비교 대상(Parsedown.php)은 트리에 동봉하지 않음. [src/tests/test_parsedown.py](src/tests/test_parsedown.py) 는 Python 포트 회귀 가드 한정.
- PHP↔Python 정규식 차이는 포팅에서 처리 (`\w` `re.ASCII`, `(?R)` 수동 bracket matcher, possessive → `+`/`*`, single quote `&#039;`).

### YAML 파서 — 의도된 부분집합

site.yaml/meta.yaml 파서는 자체 구현 ([src/scripts/yaml_parser.py](src/scripts/yaml_parser.py)). *실제 사용하는 문법의 부분집합* 만.

- **지원:** 평면 key-value, nested mapping, block list (`- a`), inline list (`[a,b]` — multi-line `[\n  a,\n  b\n]` 도 가능), 따옴표 문자열, 정수·진릿값·null, 라인 단위 `#` 주석.
- **미지원 (의도):** anchor/alias, folded scalar `>`, block scalar chomping 변형, flow mapping `{...}`, 인라인 주석(`key: val # comment` 의 trailing 주석), multi-document.
- **PyYAML 도입 계획 없음** — 부분집합으로 충분, 외부 의존성 부담 회피. 새 문법은 이 파서에 직접 추가.

### 검색 — search.php

클라이언트 JS 0, 외부 검색엔진 0. **메타데이터 3-필드 (title / seo.description / tags) 만 색인** (본문 검색 미지원 — 본문 평문은 앞 1500 자만 `body_snippet` 으로 스니펫용 보존).

```
[빌드] 모든 글 (title/desc/tags) 토크나이즈 → BM25 인덱스 (v4) + PHP 정적 배열로 직렬화
       → dist/search.php 한 파일에 토크나이저 + BM25 함수 + 인덱스 모두 인라인.
       noindex 글 제외 (sitemap/feed 와 일관).
[검색] nav 검색창 → /search.php?q=… → OPcache 에서 로드 (인덱스 메모리 상주)
       → 같은 토크나이저로 3 필드 BM25 가중합 → phrase 부스트 → 스니펫 → 결과 렌더.
```

- **UI** — 홈·카테고리 인덱스 nav 우측에만. 카테고리 페이지는 `?cat=<slug>` 자동 첨부 → 그 톱레벨 내부로 한정 (화이트리스트 검증, 잘못된 cat 은 전체 폴백). 결과 헤더에 범위 + 전체 토글. 결과 스니펫은 매치 밀도 80자 윈도우 + `<mark>` 강조.
- **토크나이저** — 영문/숫자 = 단어 단위 소문자 (정확 매치), 한글 = 음절 2-gram (부분 검색 자연 지원), **1글자 한국어 제외**. [src/scripts/search.py](src/scripts/search.py) `search_tokenize()` ↔ [src/templates/search_tokenize.php](src/templates/search_tokenize.php) 가 단일 진실원, 빌드마다 18 fixture 패리티 자동 검증 (PHP 없으면 워닝 후 skip). `.build_cache/parity.json` 에 결과 캐싱 (키 = `sha256(search.py + search_tokenize.php + php -v)`), `--no-cache` 시 매 빌드 풀 검증.
- **점수** — 필드별 Okapi BM25 (`IDF·tf(k1+1)/(tf+k1(1-b+b·dl/avgdl))`, Robertson-Spärck Jones IDF). 가중합 w_title=3.0 / w_desc=1.5 / w_tags=2.0. phrase 부스트(곱셈): title ×2.0, desc ×1.5, tags 정확매치 ×2.5. params 가 인덱스에 박혀 점수 결정적. `tests/test_bm25.py` + run_diagnostics 가 Py↔PHP 패리티 검증.
- **보안** — 쿼리 100자 제한, 모든 출력 `htmlspecialchars` escape (강조는 escape 후), 결과 페이지 `noindex,follow`.
- **서버** — PHP 7.4+ + `mbstring`. 추가 확장 불필요.
- **OPcache 전제 (v1.4.0 명문화)** — 본 시스템의 검색은 **OPcache 가 켜진 단일 PHP 파일** 을 전제로 설계됐다. 인덱스가 `search.php` 안의 정적 PHP 배열 리터럴로 인라인되어 첫 요청에만 PHP 가 파싱되고, **OPcache 가 그 바이트코드를 메모리에 상주** 시켜 두 번째 요청부터 디스크 I/O 0 / JSON 파싱 0 / `require_once` 0 으로 답한다. 47 글 인덱스가 메모리에서 처리되므로 한 자릿수 ms 응답이 가능 — 정적 사이트 대비 *체감 즉답* 의 검색 UX 가 이 구조에 직접 기인한다. **클라이언트 JS 로 옮기지 않는다** — 첫 로드에 인덱스 JSON 다운로드(수십 KB) + JS 파싱·실행이 누적되어 사용자 첫 검색 응답이 크게 느려진다 (Cloudflare CDN 캐싱으로도 첫 진입자에겐 무의미). 운영 의존성으로 PHP 7.4+ 가 추가되지만, 그 비용으로 *모든 방문자에게 즉답* 을 보장한다. 호스팅이 OPcache 를 비활성화한 경우 응답 시간이 50~100ms 대로 떨어지지만 여전히 클라이언트-JS 보다 빠르고 정확하다 (인덱스 다운로드 없음).
- **비활성화** — `src/templates/search.php` 삭제 (경고 후 search.php 미생성) + [src/templates/home.html](src/templates/home.html)·[src/templates/category.html](src/templates/category.html) 의 `<form class='nav-search'>` 제거.

### RSS / Atom 피드

`dist/feed.atom` (Atom 1.0) + `dist/feed.rss` (RSS 2.0) 가 같은 entry 목록. 모델은 [src/scripts/feed.py](src/scripts/feed.py) 의 `FeedDocument`/`FeedEntry`.

- **포함:** non-noindex 글, `excludes_categories` 제외, 최신 N개 (기본 20, `DEFAULT_MAX_ENTRIES`), `updated`(없으면 `date`) 내림차순.
- **entry:** title=`meta.title`, link/id=절대 URL, published=`date`, updated=`updated`, summary/description=`seo.description` (부재 시 누락+issue), author=`seo.author`>`site.default_author` (RSS 는 생략), category=톱레벨 폴더명 + `tags`.
- **자동 발견** — 페이지 `<head>` 에 `<link rel='alternate' type='application/atom+xml'>` / `rss+xml` 삽입.
- **결정성** — `date`/`updated` 는 모두 `00:00:00 UTC`. 피드 `updated`/`lastBuildDate` 도 빌드 시각이 아닌 entry 최신 lastmod → 콘텐츠 변경 없으면 매 빌드 같은 바이트.
- **비활성화** — [src/scripts/builder.py](src/scripts/builder.py) `build()` 의 `self._build_feeds()` 주석 처리 (site.yaml 토글 없음).

### 증분 캐시

글 단위 캐시는 `.build_cache/articles/` 에. 글 입력 (meta.yaml + content.* + 자산 mtime/size + 전역 해시) 가 같으면 hit → 산출물 replay. site.yaml/템플릿/빌더 코드/전역 자산이 바뀌면 전 글 invalidate (전역 해시). 검색/sitemap/feed/홈/카테고리/assets 는 모든 글이 입력이라 매 빌드 재구축 (의도된 범위).

### 이미지 멀티프로세스

raster 변환은 `ProcessPoolExecutor(workers=min(cpu_count, len(jobs)))` 로 fan-out, 워커는 모듈-레벨 자유 함수 `_image_worker` (Windows spawn 도 OK). 결과 처리(`image_variants` 등록·에러 BuildReport 라우팅)는 메인 `_handle_image_result` 헬퍼로. raster_jobs<4 또는 worker≤1 이면 시리얼 폴백 (Windows Pillow import 비용 절약).

---

## 13. 배포

빌드 후 `dist/` 를 서버 DocumentRoot 에 올리고 Apache VirtualHost 를 **한 번** 등록. 이후 글 추가/삭제해도 서버 설정 불변. `.htaccess` 미사용 — 공유 호스팅에서 메인 설정 접근이 안 되면 호스팅 사업자에 등록 요청.

```bash
rsync -avz --delete dist/ user@siheonlee.com:/var/www/siheonlee.com/
```

```apache
<VirtualHost *:443>
    ServerName siheonlee.com
    ServerAlias www.siheonlee.com
    DocumentRoot /var/www/siheonlee.com         # ← dist/ 내용 배포

    SSLEngine on
    SSLCertificateFile    /etc/letsencrypt/live/siheonlee.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/siheonlee.com/privkey.pem

    <Directory /var/www/siheonlee.com>
        AllowOverride None                      # .htaccess 무시
        DirectoryIndex index.html index.php
        DirectorySlash On                       # /slug → /slug/ 자동 리다이렉트
        Options -Indexes -MultiViews +FollowSymLinks
        Require all granted
    </Directory>

    AddType application/x-httpd-php .php
    ErrorDocument 404 /404.html
    AddDefaultCharset UTF-8
</VirtualHost>

<VirtualHost *:80>                              # HTTP → HTTPS (선택)
    ServerName siheonlee.com
    ServerAlias www.siheonlee.com
    RewriteEngine On
    RewriteRule ^.*$ https://siheonlee.com%{REQUEST_URI} [L,R=301]
</VirtualHost>
```

- **빌드 머신**에는 PHP 불필요. PHP CLI 있으면 토크나이저 패리티 자동 검증.
- **배포 서버**는 **PHP 7.4+ + mbstring** 필요 (search.php + `.php` 출력 글). 이것은 한계가 아니라 전제.
- ⚠️ **`admin.php`·`src/admin/` 은 절대 배포하지 말 것.** 위 `rsync` 는 `dist/` 만 올리므로 자연히 빌드 머신을 벗어나지 않는다 — admin 은 로컬 전용 단일 사용자 저작 도구다. 추가 방어로 `admin.php` 는 PHP 내장 서버(`cli-server`)+루프백이 아니면 스스로 403 을 낸다 ([§ 17](#17-로컬-글쓰기--adminphp)). DocumentRoot 는 `dist/` 뿐이라 `.php` 라우터가 그 안에 없기도 하다.

**배포 검증:**

```bash
curl -I https://siheonlee.com/                # 200
curl -I https://siheonlee.com/hello-world     # 301 → /hello-world/
curl -I https://siheonlee.com/hello-world/    # 200
curl -I https://siheonlee.com/sitemap.xml     # 200 application/xml
```

---

## 14. 트러블슈팅

| 증상 | 원인 / 해결 |
|---|---|
| 빌드 성공인데 CSS 깨짐 | 절대경로(`/assets/...`). 더블클릭 말고 `cd dist && python -m http.server 8000`. |
| PHP 없이 빌드 가능? | 가능 (파서 순수 Python). PHP CLI 없으면 패리티 검증만 워닝 후 skip. 배포 서버는 PHP 필요. |
| styles 가 적용 안 됨 | ① styles·외부 CSS 는 글·홈·카테고리 모두 동일하게 inject — 홈은 `Articles/meta.yaml`, 카테고리는 그 카테고리 `meta.yaml` 에 작성. ② 템플릿에 `{{PAGE_STYLES}}`/`{{PAGE_STYLESHEETS}}` 있는지. ③ specificity 충돌 → 구체 셀렉터/`!important`. ④ `:hover`/`#id`/`::before` 는 YAML 인용. |
| styles 에 `@media` | 인라인 채널은 평면 규칙만. 글 폴더에 진짜 CSS 파일 + `styles: {1: my.css}`. |
| `slug 충돌` | 같은 slug 두 글. 한쪽 변경. |
| URL 이 `/be94-…/` | 비ASCII 폴더명 → hex 자동 변환. 폴더명을 ASCII 로 (`블로그`→`Blog`). |
| 이미지 안 보임 | 글 폴더 안에 있는지 / `./imgs/p.jpg` 상대경로 / `missing asset` 경고 / `dist/{slug}/imgs/` 복사 확인. |
| `.php` 안 나오고 `.html` | 처리 안 된 `<?php` 가 남아야 `.php`. imgBox/imgSlideBox 는 HTML 변환되므로 `.html`. |
| `dist/` 새로 빌드 | `python build.py --clean`. |

---

## 15. 설계 원칙과 한계

**설계 원칙**

1. **URL 영구성** — slug 가 안 바뀌는 한 카테고리 이동·폴더명 변경과 무관하게 영구.
2. **표시명 ↔ URL slug 분리** — 화면=한국어 폴더명, URL=ASCII slug.
3. **운영 의존성 명시** — 빌드 Python 3 + Pillow, 런타임 PHP. "외부 의존성 0" 이 아니라 솔직히 명시 + 끄는 옵션 제공.
4. **서버 ↔ 콘텐츠 분리** — `.htaccess` 없음. 글을 늘려도 서버 설정 불변.
5. **빌드 안전성** — `Articles/` 를 읽기만. 소스 자동 수정 안 함.
6. **파서 단일화** — Parsedown Python 포팅 하나로 통일.
7. **글 단위 표현 제어** — meta.yaml 에서 선언적으로.
8. **글 단위 색인** — 기본 허용, `noindex: true` 글만 제외.
9. **단일 진실원 토크나이저** — Py/PHP 패리티 빌드마다 자동 검증.
10. **본문 ↔ 메타데이터 분리** — SEO/OG/피드 카피는 본문이 아니라 author 가 `seo:` 블록에 직접 쓴 값에서만. 본문=독자용, 메타=SERP/소셜용 — 다른 글이어야 함. SSG 는 추측하지 않음. `og_image` 부재 시 본문 추출이 아니라 `site.default_og_image`.
11. **`template:` 가로지르기 — 허용하되 알린다** — 페이지 종류와 다른 템플릿 지정 가능. 빌더가 못 채우는 placeholder 는 strip + warning (자동 거부도 silent strip 도 아닌, 알림 + author 판정).

**현재 한계** — 두 부류. ⓐ 현 능력의 *내재적* 한계, ⓑ *의도적으로 보류한* 확장.

**ⓐ 내재적 한계**

| 한계 | 내용 |
|---|---|
| 이미지 최적화는 정적 단일 프레임 | animated GIF 는 첫 프레임만 WebP. 보존하려면 webp 직접 첨부/외부 URL. 글·이미지 단위 토글 없음 (전역 `images.enabled` 만). |
| 증분 캐싱은 글 페이지만 | 검색/sitemap/feed/홈/카테고리/assets 는 모든 글이 입력이라 매 빌드 재구축 (의도된 범위). |
| 내부 링크 검증 = 글 페이지만 (v1.4.0) | post-build 단계가 `dist/<slug>/index.{html,php}` 의 `<a href>` 만 훑는다. 홈·카테고리·404·search 도 자동으로 만드는 링크라 깨질 가능성이 사실상 0 (글 slug 가 `_validate` 단계에서 이미 검증). 자산(`<img src>`) 도 빌더 자체 후처리에서 다루므로 별도 검증 안 함. |
| admin 미리보기 = 본문 충실도 | 같은 파서·확장이라 *본문* 은 산출물과 byte-동일하나, 헤더/nav/푸터·`<meta>`·JSON-LD 같은 풀페이지 chrome 은 만들지 않는다 (그건 템플릿 채움 단계). 풀페이지 정확본은 원클릭 빌드 후 `dist/` 확인 — 의도된 분담. 패리티는 `test_render_one` 으로 게이트. |
| admin 은 로컬 단일 사용자·인증 없음 | PHP 내장 서버(`cli-server`)+루프백 가드만 (그 외 즉시 403). 다중 사용자/동시 편집/원격 접근 비대상. raw `meta.yaml` 폼 저장은 부분집합 파서가 인라인 주석을 보존 못 함 — 커스텀 주석 유지하려면 raw 칸으로 저장 (raw 가 진실원). |

**ⓑ 의도적으로 보류한 확장**

| 확장 후보 | 현재 | 보류 이유 |
|---|---|---|
| 홈/카테고리 JSON-LD | 글 페이지만 (`article.html` 만 `{{JSONLD}}`). `seo.jsonld` 는 홈/카테고리 `meta.yaml` 에서도 파싱되나 forward-compat (미사용) | 홈 `WebSite`+`SearchAction` 은 검색 URL 계약을 구조화데이터에 고정(추측 리스크), 카테고리 `ItemList` 은 페이지네이션과 얽혀 열거 diff 표면이 크고 리치결과 효용 낮음 |
| 태그 색인 페이지 `/tag/<slug>/` | `tags` 는 feed `<category>`·BM25·JSON-LD `keywords` 에만 쓰임. 탐색 페이지 없음 | URL 영구성 약속이 늘고 `tags` 가 1급 분류 축으로 승격 → "카테고리가 분류 축" 설계와 충돌 (의도적으로 `CategoryMeta` 에서 `tags` 제외). 도입 전 분류 축 정의를 먼저 결정해야 함 |
| 글 렌더 병렬화 | 순차 | 47글·빌드 ~3s, 지배적인 이미지 변환은 이미 멀티프로세스 → ROI 낮음. 결정성·캐시 replay·리포트 순서 제약 비용이 큼. 글이 수백 단위가 되면 재검토 |

---

## 16. 업데이트 로그

> changelog 본문의 `scripts/…`·`templates/…`·`tests/…` 경로는 도입 시점의 역사 기록 — v0.8.1 부터 실제 위치는 모두 `src/` 접두 (§ 3).
> 코드 정합성: **문서 전용 릴리스** = 정본 클린 재빌드 후 dist sha256 == 직전 코드 복사본. **코드 릴리스** = 결정성(2회 빌드 동일) + 직전 코드 릴리스 기준 열거 diff.

| 버전 | 날짜 | 요약 |
|---|---|---|
| **v1.4.1** | 2026-05-28 | **v1.4.0 안정화 패치** (코드 릴리스, dist byte-불변) — v1.4.0 신설 내부 링크 검증의 `Builder._LINK_HREF_RE` 정규식 결함 수정. `\bhref=` 는 `-` ↔ `h` 사이도 워드 경계라 `data-href` 같은 데이터 속성을 href 로 오매칭하고, greedy `[^>]*` 가 마지막 매치를 가져가 `<a href="/real" data-href="/fake">` 에서 진짜 href 가 아닌 `/fake` 를 추출했다. v1.4.1 에서 `\s+href=` (속성 경계로 공백 필수) 로 교정해 `data-*` 류 자동 제외 + 진짜 href 만 잡힘. 정규식은 reporting validator 만 사용해 **dist 영향 0** (v1.4.0 dist 와 `diff -r` 빈 출력, sha256 동일). 단위 425→**429** (test_v140.py `InternalLinkValidationTests` 에 회귀 가드 4 추가: data-href 단독 시 추출 없음, 두 속성 공존 시 진짜 href 추출, 줄바꿈/대문자 매칭, 통합 검증에서 data-href 미보고) · 진단 6/6 승계. |
| v1.4.0 | 2026-05-28 | **여섯 묶음 기능·정리 릴리스** — (A) 글 푸터 이전/다음 글 nav (사이트 전역 `prev_next.enabled`, 같은 부모 폴더 형제, date asc, noindex 풀에서 제외), (B) 글 끝 발행/수정 메타 한 줄 (`.article-end-meta`, 작고 모던, 마지막 section 아래), (D) 다크 모드 (`prefers-color-scheme: dark`, 토글 UI 없음, CSS only), (E) 내부 링크 검증 (post-build 글 페이지 `<a href>` 스캔, 깨진 site-relative 링크 issue), (F+G+I) site.yaml 다섯 키 코드 상수 승격 (`reserved_slugs` → `RESERVED_SLUGS`, `warn_on_underscore_ref` → 항상 경고, `warn_on_missing_asset` → dead config 폐기, `error_404_title`·`search_title` → `DEFAULT_*_TITLE`), (J) BuildReport 에 "PHP 로 빌드된 글" 별도 카테고리 신설 (`.php` fallback 은 작성자(웹 개발자) 의도라 issue/warning 이 아니라 의도된 출력 보고). README §12 검색 절에 **OPcache 전제** 명문화 (단일 PHP 파일 + OPcache 메모리 상주가 즉답 UX 의 직접 원인, 클라이언트 JS 로 옮기지 않는 사유). 새 §18 "추가 업데이트 제안" — 자동 TOC 후보 + `description_truncate` 사용처 해설. 단위 390→**425** · 진단 6/6 승계. |
| v1.3.0 | 2026-05-28 | 빌드 속도 향상 (코드 릴리스, dist byte-불변) — 단계별 timing 계측, 이미지 멀티프로세스, 자산 패스 통합, tokenizer parity 캐시. cold 270s→33s, warm 5.2s→2.7s. dist v1.2.2 와 byte 동일. 단위 374→**390** (`test_v130_speed.py`: StepTiming + ImageWorker + PrunePassUnification + ParityCacheKey + ParityCacheRoundTrip) · 진단 6/6 승계. |
| v1.2.2 | 2026-05-21 | `yaml_parser` multi-line inline list 지원 — `[` 로 시작·같은 줄에 `]` 없으면 후속 줄을 누적해 `]` 까지 파싱. multi-line `exclude_urls` 가 그대로 발효. 단위 367→**374** (`MultilineInlineListTests`) · 진단 6/6 승계. |
| v1.2.1 | 2026-05-21 | 운영 잡음 정리 — `noindex: true` 글의 `seo.description` 필수 검사 면제, `warn_on_stale_updated` 워닝 폐기. dist byte-불변. 단위 364→**367** · 진단 6/6 승계. |
| v1.2.0 | 2026-05-21 | v1.1.5 문서 안정화. dist 동일. |
| v1.1.5 | 2026-05-20 | AdSense URL 기반 광고 차단 — `exclude_urls` 가 사이트 내 임의 URL 목록(정확 일치, 개별 글 차단 가능). 빈 리스트=전체 주입. v1.1.4 의 `exclude_pages` 폐기. 단위/진단 승계. |
| v1.1.4 | 2026-05-20 | AdSense 페이지 타입 제외 (`exclude_pages: [article/home/category/404/search]`). v1.1.5 에서 URL 기반으로 통합. |
| v1.1.3 | 2026-05-20 | Google AdSense 통합 (`google_adsense.ads_txt`·`head_script`) + 기본 `default-og.png` 1200×630 표준 OG 규격으로 교체. |
| v1.1.2 | 2026-05-20 | imgSlideBox 배포 사고 수정 + 페이지네이션형 재디자인 — 누락 CSS `.slide{display:none}` 복구 + 하단 중앙 dot 인디케이터 (런타임 JS 생성, 정적 HTML 불변). |
| v1.1.1 | 2026-05-20 | imgBox 배포 사고 수정 — 다중 구문 PHP 블록의 시뮬레이트 실패로 원본 PHP leak. `simulate_php_in_html` 블록 스캐너 재작성 + `site.yaml php_globals` 신설 + 캡션 raw 보존. 단위 313→**337**. |
| v1.1.0 | 2026-05-19 | 로컬 글쓰기 `admin.php` 추가 — `build.py` 패턴 미러, 작성/수정·이동·비공개·삭제·미리보기·원클릭 빌드. dist byte-불변 (admin 은 빌드 앞단). 단위 313→**317** ([§ 17](#17-로컬-글쓰기--adminphp)). |
| v1.0.2 | 2026-05-19 | 홈 기본 출력 개수 디폴트 5→10 (정본 `Articles/meta.yaml` 가 `per_page: 10` 명시라 dist 영향 0). |
| v1.0.1 | 2026-05-19 | 소분류 헤더 링크화 — 화살표 폐지, 소분류명 자체가 자기 페이지 링크 (`color: inherit; text-decoration: none`). |
| v1.0.0 | 2026-05-19 | 첫 정식 릴리스 — 기본 og:image 자산 패스스루 (raster 보존), `Articles/About` noindex. |
| v0.8.4 | 2026-05-19 | v0.8.3 문서 안정화. dist v0.8.3 과 byte 동일. |
| v0.8.3 | 2026-05-18 | schema.org JSON-LD + 정확 빵부스러기 — 글 페이지 `<head>` 에 `Article` + (crumb 2개↑) `BreadcrumbList`. 기존 메타 보강. off 스위치 (`jsonld.enabled` · `seo.jsonld`). 빌드 제외 접두 `_`·`.` 일원화. 단위 266→313. |
| v0.8.2 | 2026-05-18 | 코드 건전성 — `__version__` 디커플링 (feed `<generator>` 가 버전-free), argparse 엄격화, 빌드 리포트 per-Builder. 단위 258→266. |
| v0.8.1 | 2026-05-17 | 폴더 구조 정리 — 빌더 일체를 `src/` 아래로. 코드 동작·산출물 불변. |
| v0.8.0 | 2026-05-17 | README 코드 정합성 정정. 코드·dist 무변경. |
| v0.7.2 | 2026-05-17 | 16 단계 진행 헤더 + 라이브 카운터 + `build-report.md` 영속. 산출 로직 무변경. |
| v0.7.1 | 2026-05-16 | 안정화. 코드 동작 무변경. |
| v0.7.0 | 2026-05-16 | 빌드 증분 캐싱 (글 단위). `--no-cache`/`--clean-cache` 추가. 테스트 231→258. |
| v0.6.5 | 2026-05-15 | 안정화 — reset_report 자동 호출 / `_render_template` 3-pass / og_type 강제 디폴트 제거. |
| v0.6.4 | 2026-05-15 | 홈/카테고리 CSS 일원화 + `template:` 키. |
| v0.6.3 | 2026-05-15 | 글 단위 외부 CSS 파일 (정수 키) + `use_common_css` 토글. |
| v0.6.2 | 2026-05-15 | 홈/카테고리 SEO 메타 태그 출력. |
| v0.6.1 | 2026-05-15 | 문서·주석·산출물 가독성 안정화. 코드 동작 무변경. |
| v0.6.0 | 2026-05-15 | 검색 메타데이터 3-필드 색인 (v4) + search.php 단일 파일 인라인. 진단 스크립트 신설. |
| v0.5.5 | 2026-05-15 | 본문 ↔ 메타데이터 분리 원칙 + 빌드 리포트 일원화 (`report.py`). |
| v0.5.4 | 2026-05-14 | `<title>` 폴백 체인 일반화 + 단어 경계 truncate + `nav_priority`. |
| v0.5.3 | 2026-05-14 | `tags` + `layout: gallery` + RSS/Atom 피드. |
| v0.5.2 | 2026-05-14 | 자산 경로 일원화 (`dist/src/{slug}/` → `dist/{slug}/`). |
| v0.5.1 | 2026-05-14 | 이미지 자동 최적화 (WebP 다중 해상도) + lazy loading. |
| v0.5.0 | 2026-05-14 | Okapi BM25 검색 (TF 합산 → BM25 + phrase boost). 인덱스 v3. |
| v0.4.7 | 2026-05-14 | 문서·코드 정합성 회복. dist v0.4.6 과 byte 동일. |
| v0.4.6 | 2026-05-14 | 페이지네이션 FOUC 제거 + `Articles/meta.yaml` + `priority` + 설정 일원화. |
| v0.4.5 | 2026-05-14 | 페이지네이션 + 다국어 + 서브카테고리 인덱스 + 카테고리 meta.yaml. |
| v0.4.4 | 2026-05-14 | `sitemap.xml` 자동 생성 + robots.txt Sitemap 디렉티브. |
| v0.4.3 | 2026-05-14 | `<title>` 정상화 + 마크다운 섹션 마커 + SEO `seo:` 그룹화. |
| v0.4.2 | 2026-05-14 | 정합성 갭 정리 (slug↔카테고리 충돌 사전 차단, search.php noindex,follow). |
| v0.4.1 | 2026-05-14 | 빌드 PHP 의존 제거 — Parsedown 1.7.4 Python 포팅. dist v0.4.0 과 byte 동일. |
| v0.4.0 | 2026-05-13 | 캐치프레이즈 정직화 + 색인 정책 정상화 (전역 noindex 제거) + 모듈 분할. |
| v0.3.2 | 2026-05-10 | 검색 UI 정리 + 카테고리 스코프 검색. 인덱스 v2. |
| v0.3.1 | 2026-05-09 | 사이트 내 검색 (`search-index.json` + search.php). |
| v0.3 | 2026-05-09 | Parsedown 도입 + 글 단위 styles 오버라이드. |
| v0.2 | 2026-05-09 | 이전 사이트 UI/UX 보존. About 일반 글 통합. |
| v0.1 | — | Python stdlib only SSG 첫 동작. 핵심 설계 원칙 확립. |

---

## 17. 로컬 글쓰기 — admin.php

글 작성·수정·카테고리 이동·비공개·삭제와 **실시간 본문 미리보기**·**원클릭 빌드**를 파일 탐색기 대신 브라우저로 하는 **로컬 전용 단일 사용자** 도구. `build.py` 패턴을 그대로 미러한다 — 버전 폴더 루트의 얇은 진입점 `admin.php` + 로직 일체 `src/admin/`. 빌더는 `Articles/` 만 스캔하므로 이 둘은 **`dist/` 에 새지 않고** 빌드 결정성·산출물과 무관하다 (admin 은 빌드 *앞단* 의 저작 도구 — `Articles/` 를 쓰고, `build.py` 는 여전히 읽기만: 설계 원칙 5 무손상).

### 17-1. 실행

버전 폴더에서:

```bash
php -S 127.0.0.1:8001 admin.php
```

브라우저로 `http://127.0.0.1:8001/`. 빌드 머신 기준 **PHP 7.4+** (개발은 8.x 권장) + **Python 3** (미리보기·slug·빌드가 실제 `scripts.*` 를 부른다). 종료는 터미널 `Ctrl+C`.

### 17-2. 보안 — 절대 공개 서버에 두지 말 것

로컬 단일 사용자 전제. 다층 가드:

- **SAPI+루프백 가드** — `admin.php` 는 PHP 내장 서버(`cli-server`) + `127.0.0.1`/`::1` 이 아니면 스스로 **403**. Apache `mod_php`/`php-fpm` 에 얹혀도 열리지 않는다.
- **배포 비포함** — § 13 의 `rsync` 는 `dist/` 만 올린다. `admin.php`·`src/admin/` 은 빌드 머신을 떠나지 않으며, DocumentRoot 도 `dist/` 라 라우터가 그 안에 없다.
- **CSRF** — 상태 변경(저장/생성/이동/삭제/빌드)은 세션 토큰 검증. 인증은 두지 않는다 (로컬 단일 사용자라 불필요 — 한계로 § 15 ⓐ 명시).

### 17-3. 기능

- **목록** (`/`) — 글 트리. 각 글: 편집 · 카테고리 이동(드롭다운) · 공개/비공개 토글 · 삭제. `.trash` 내용도 표시.
- **새 글** (`?a=new`) — 카테고리 선택 + 폴더명(한국어 가능) → `slug_one.py` 가 빌드와 **같은** 규칙으로 slug 자동 제안(비ASCII면 hex 경고). 폴더 + `content.md`(또는 `.html`) + `meta.yaml`(정본 헤더 주석 포함) 생성.
- **편집** (`?a=edit&id=…`) — **2분할**: 좌=본문(`content.md`/`.html`, frontmatter 금지 — 본문↔메타 분리 원칙), 우=메타 폼 + 접이식 **raw `meta.yaml`** + 실시간 미리보기. 핵심 입력칸(title·slug·date·updated·tags·`seo.description`·noindex)은 *보조* — 바꾸면 raw YAML 을 패치한다. **저장은 raw `meta.yaml` 기준**(주석·고급 키·`styles` 보존), 서버는 헤더 주석 한 줄만 보장. 즉 raw 가 진실원.
- **이동** — 폴더 rename. `slug` 불변이라 **URL 영구**(설계 원칙 1). **비공개** — 폴더명 `_` 접두 토글. **삭제** — `Articles/.trash/` 로 이동: `.` 접두라 빌드 자동 제외, 파일은 남아 복구 가능(영구 삭제 UI 는 의도적으로 두지 않음 — 복구는 파일 탐색기에서 `.trash` 밖으로).
- **원클릭 빌드** — 상단 버튼이 `python build.py`(`--clean` 체크 가능)를 버전 폴더 cwd 로 실행하고 출력을 표시. 사이트(`dist/`)에 반영하는 단계.

### 17-4. 미리보기 = 본문 충실도 (파서 단일화)

별도 마크다운 엔진을 두지 않는다. `src/admin/render_one.py` 가 빌더가 글 본문을 만들 때 쓰는 **그 `scripts.markdown` 경로**를 그대로 재사용 — `.md` 는 `resolve_section_markers(render_article_md(…))`, `.html` 은 `process_html(…)` 로 빌더 `_render_articles` 와 1:1 동일. 따라서 미리보기 *본문* 은 산출물과 byte-동일(같은 imgBox/imgSlideBox·같은 자산 경로 재작성). 미리보기 창은 사이트 공통 CSS 를 입히고 자산을 소스 폴더에서 프록시해 보여 준다. 헤더/nav/푸터·`<meta>`·JSON-LD 등 풀페이지 chrome 은 만들지 않으므로 — 그건 템플릿 채움 단계 — **풀페이지 정확본은 빌드 후 `dist/`** 로 확인한다(의도된 분담). 이 패리티는 `src/tests/test_render_one.py` 가 빌더 경로와 byte 비교로 잠근다(누가 다른 엔진/경로로 바꾸면 깨짐).

### 17-5. 제약 (§ 15 ⓐ 와 동일)

본문↔메타 분리는 강제(폼이 frontmatter 를 본문에 섞지 않음). 부분집합 YAML 파서는 인라인 주석을 보존 못 하므로 폼 저장 시 헤더 외 커스텀 주석은 유실 — 유지하려면 raw 칸으로 저장. 로컬 단일 사용자·인증 없음·동시 편집 비대상. Windows 비ASCII 폴더명은 PHP 8.x 의 UTF-8 파일시스템 처리에 의존(PHP 8.3 검증) — 폴더명은 출력 무관이라(slug 가 URL) 사이트 산출물에는 영향 없다.

---

## 18. 추가 업데이트 제안

v1.4.0 검토 중 함께 논의됐으나 *이 릴리스에 구현하지는 않은* 후보들. 차후 결정의 출발점이지 약속은 아니다. (사용자가 명시적으로 보류한 항목 — 홈/카테고리 JSON-LD, 태그 색인, 글 렌더 병렬화 — 은 여기 두지 않는다. [§ 15](#15-설계-원칙과-한계) ⓑ 표 참조.)

### 18-1. 자동 목차 (TOC) — 긴 글 한정 자동 또는 `meta.yaml toc: true`

**무엇** — 본문 헤딩(h2/h3)으로 사이드(데스크탑)·인라인(모바일) TOC 자동 생성. 임계 = 본문 어절 1500↑ AND h2 ≥ 3 일 때 자동 ON, `toc: false` 강제 OFF / `toc: true` 강제 ON. 토글이 3-상태인 이유 = noindex 같은 *기본 자동, 명시 override* 패턴.

**왜 보류** — 정본 글들 대부분이 짧고 헤딩 수가 적어 즉시 효용이 크지 않다. 도입 시 ① Parsedown 포팅에 헤딩 anchor 부착(현재 `<h2>제목</h2>` → `<h2 id="제목">제목</h2>`), ② 후처리에서 `<nav class="toc">` 빌드, ③ CSS 두 레이아웃(사이드 vs 인라인), ④ 임계 알고리즘 + 토글 3-상태 — 작은 기능이 아니라 적정 릴리스 분량의 한 묶음. *연구 노트/논문 리뷰* 류 글이 늘면 우선순위 상승.

**구현 시 손댈 파일** — `src/scripts/parsedown.py` (헤딩 ID), `src/scripts/markdown.py` (TOC 추출+렌더), `src/scripts/models.py` (`ArticleMeta.toc: Optional[bool]`), `src/assets/common_template.css` (`.toc` 두 레이아웃), `README.md` (§4-2 메타 표 + §9 마크다운 절). 단위 테스트 신설 1식.

### 18-2. `description_truncate` 사용처 해설 + 코드 상수 승격 후보

**현재 어디 쓰이는가** — site.yaml 의 `description_truncate: 150` 은 *단 한 곳* 에만 쓰인다 — **피드(Atom `<summary>` / RSS `<description>`) 의 요약 텍스트 절단 최대 글자 수**. `seo.description` 본문이 이 길이를 넘으면 *영문 단어 경계를 존중* 하며 잘리고 끝에 `…` 가 붙는다 (구현 = `src/scripts/seo.py` 의 `truncate_description`, 호출은 `src/scripts/builder.py` `_render_articles` 두 곳에서 `summary = truncate_description(desc_val, self.site.description_truncate)`).

| 통로 | description_truncate 적용? |
|---|---|
| `<meta name="description">` (글 head) | **❌ 미적용** — `seo.description` 본문 전체 그대로. |
| `<meta property="og:description">` · `<meta name="twitter:description">` | **❌ 미적용** — 본문 그대로. |
| schema.org JSON-LD `Article.description` | **❌ 미적용** — 본문 그대로. |
| 갤러리 타일 / 홈 / 카테고리 listing 의 요약 | **❌ 표시 안 함** (현재 디자인). |
| **피드 `<summary>` (Atom) / `<description>` (RSS)** | **✅ 적용** — `description_truncate` 문자 캡. |

즉 *피드 reader 의 작은 화면을 위한 1줄 요약 캡* 한 가지 목적. 검색엔진의 SERP 스니펫(`<meta description>`) 은 무관 (검색엔진이 자기 로직으로 절단).

**왜 코드 상수 승격을 보류했는가** — 사용자가 피드 reader 별 표시 폭(가령 모바일 reader 의 좁은 카드) 에 맞춰 70~200 사이로 *조정할 가치가 있을 수* 있다. 한 번도 안 바꿔봤다면 코드 상수 승격이 정답이지만, 운영 1년이 지나 한 번도 안 만진 게 확인되면 그때 옮긴다 (F·G·I 의 다섯 키와 같은 기준).

**대안 — 작성자가 직접 짧게 쓰기** — 피드용 요약을 짧게 유지하면 `description_truncate` 가 발동할 일이 없어진다 (운영 정책). 그 경우 키는 dormant 가 되어 자연 폐기 후보가 된다.

### 18-3. 향후 결정 보관

작성 시점에 위 둘 외에도 *논의는 됐으나 v1.4.0 결정에서 빠진* 후보가 더 있을 수 있다. 추가될 항목은 같은 형식(무엇·왜 보류·구현 시 손댈 곳)으로 이 절에 누적한다. 한 번 보류된 후보를 풀 때는 이 절의 사유와 함께 재검토 — 사유가 바뀌었는가, 아니면 같은 사유가 여전한가.

---

*siheonlee.com v1.4.1 — 빌드 Python + Pillow, 런타임 PHP (OPcache 권장). 누적 릴리스 내역은 [§ 16](#16-업데이트-로그).*

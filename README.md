# siheonlee.com v0.8.3 — 사용설명서

**글마다 폴더 하나**를 만들어 본문·첨부를 관리하고, `python build.py` 한 번으로 사이트를 만드는 **PHP 기반 경량 웹 사이트 생성기**입니다.

| 핵심 가치 | 보장 방법 |
|---|---|
| **URL 영구성** | 글 URL(`slug`)은 카테고리·폴더명과 분리. 글을 옮겨도 URL 불변. |
| **운영 의존성 최소** | 빌드 = Python 3 stdlib (+ Pillow), 런타임 = Apache+PHP. `composer`·클라이언트 JS 없음. |
| **이미지 자동 최적화** | raster → WebP 다중 해상도 srcset + `loading="lazy"` 자동. |
| **서버·콘텐츠 분리** | `.htaccess` 미사용. 라우팅은 Apache VirtualHost 에 한 번만 등록. |
| **페이지 단위 표현 제어** | `meta.yaml` 의 `styles` 로 인라인 미세 조정 + 외부 CSS 파일 + 자기 템플릿까지. |
| **글 단위 색인 제어** | 기본 색인 허용. 빼고 싶은 글만 `noindex: true` 한 줄. |
| **사이트 내 검색** | 클라이언트 JS 0. BM25 + 토크나이저 + 인덱스가 `search.php` 한 파일에 인라인. |

> **v0.8.3 한 줄 요약:** *schema.org JSON-LD 구조화 데이터 (additive 기능).* 글 페이지 `<head>` 에 `<script type="application/ld+json">` 한 줄 — `@graph` 로 `Article` + (breadcrumb 2개↑이면) `BreadcrumbList`. 기존 OG/Twitter/canonical/robots `<meta>` 를 **대체하지 않고 보강** (소비자가 다름: SNS=OG, SERP=description, 색인=robots, 리치결과=JSON-LD). off 스위치: `site.yaml`→`jsonld.enabled` (전역) + `meta.yaml`→`seo.jsonld:false` (글 단위, 사이트 토글이 마스터). `build_jsonld`/`jsonld_enabled` 신설, canonical/og_image/author 해석을 `build_meta_tags` 와 공유 헬퍼로 추출 (메타 태그 산출물 byte 불변). **코드 릴리스** — dist 는 v0.8.2 대비 글 페이지 47 개가 각 ld+json 한 줄 추가, 그 외 738 파일 byte-동일 (0 missing/extra), 결정성 2회 동일. 단위 266→297. 자세한 내역은 [§ 16](#16-업데이트-로그).

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

성공 시 출력 형태 (글/카테고리/소요는 `Articles/` 에 따라 다름):

```
빌드 시작 - siheonlee.com v0.8.3 (2026-05-18 02:55:00)
[ 1/16] 설정 로드 (site.yaml / 토크나이저 패리티)
[ 2/16] 글 폴더 스캔 (Articles/)
   …  (각 단계 [ n/16] 헤더, 무거운 단계는 \r 라이브 카운터)
[16/16] 고아 산출물 정리

빌드 완료: 47 글, 19 카테고리, 0 보완 필요, 0 살펴볼 사항. (261.5s)
증분 캐시: 0 히트 / 47 미스 (글 47건).
리포트 문서: build-report.md 생성.
```

첫 빌드는 모든 글 miss (캐시 비어있음). 이후 변경 안 된 글은 hit. site.yaml/템플릿/빌더 코드 변경 시 전부 invalidate.

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

- **운영 의존성 최소** — Python 3 stdlib (빌드) + PHP (런타임 검색). v0.4.1 부터 빌드 머신에 PHP 불필요.
- **글 폴더 = 자율 단위** — 본문·이미지·보조파일을 글 폴더 안에서 자유 관리.
- **URL 영구성** — `slug` 가 곧 URL. 카테고리를 옮겨도 불변.
- **글 단위 스타일·색인** — `meta.yaml` 에서 글마다 독립 제어.

**빌드 파이프라인 (16 단계)**

| # | 내용 |
|---|---|
| 1 | `site.yaml` 읽기 + 토크나이저 패리티 검증 (PHP 있으면) |
| 2 | `Articles/` 트리 스캔 |
| 3 | 각 글 `meta.yaml` 파싱 |
| 4 | 검증 (slug 중복/예약어/형식). 문제 글은 issue 기록 + 그 글만 산출물 제외, 빌드는 계속 |
| 5 | 글별 자산 → `dist/{slug}/` 복사. raster 이미지는 Pillow 로 WebP 변환 |
| 6 | `src/assets/` → `dist/assets/` 복사 |
| 6b | 카테고리/홈 외부 CSS 파일 dist 복사 |
| 7 | 글 본문 렌더 (.md 는 파서, .html 은 그대로) → `<img>` 후처리 → styles inject → 템플릿 결합 |
| 8 | 카테고리 색인 (톱레벨 + 서브) |
| 9 | 홈 페이지 |
| 10 | 404 페이지 |
| 11 | `robots.txt` (Sitemap 디렉티브 포함) |
| 12 | `sitemap.xml` |
| 12b | `feed.atom` / `feed.rss` (같은 entry 목록) |
| 13 | `dist/search.php` — 3-필드 BM25 인덱스 + 토크나이저 + 점수기 인라인 |
| 14 | 고아 산출물 정리 |

---

## 3. 폴더 구조

```
siheonlee.com_v0.8.3/        ← 보이는 것은 아래 6 개뿐
│
├── Articles/                ← ★ 모든 글 (최초엔 참고 자료)
│   ├── About/                   ← 톱레벨 글 (meta.yaml + content.html + 자산)
│   └── Blog/                    ← 카테고리 폴더
│       └── Hello World/         ← 글 폴더 (폴더명 = 화면 표시명)
│           ├── meta.yaml        ← slug/제목/날짜/styles
│           ├── content.md       ← 본문 (또는 content.html)
│           └── imgs/            ← 첨부 (선택)
│
├── dist/                    ← 빌드 산출물 (배포 대상 / 직접 수정 금지)
│
├── src/                     ← ★ 빌더 일체 (v0.8.1 정리)
│   ├── scripts/                 ← build.py 내부 모듈 (Python 패키지)
│   │   ├── __init__.py             ← __version__ (전역 버전 단일 source)
│   │   ├── yaml_parser.py          ← stdlib only YAML 부분 구현
│   │   ├── models.py               ← dataclass 정의
│   │   ├── slugs.py                ← 폴더명 → URL slug
│   │   ├── parsedown.py            ← Parsedown 1.7.4 Python 포팅
│   │   ├── markdown.py             ← 본문 전·후처리 + PHP 함수 시뮬레이션
│   │   ├── seo.py                  ← <meta> 태그 빌더
│   │   ├── search.py               ← 토크나이저 / BM25 인덱스 / Py↔PHP 패리티
│   │   ├── sitemap.py              ← sitemap.xml
│   │   ├── images.py               ← WebP 변환 + <img> 후처리
│   │   ├── cache.py                ← 글 단위 증분 캐시 (BuildCache)
│   │   ├── report.py               ← BuildReport (issue/warning, render_markdown)
│   │   └── builder.py              ← 빌드 파이프라인 (Builder 클래스)
│   │
│   ├── templates/               ← 페이지 HTML 틀 + PHP 모듈
│   │   ├── article.html / category.html / home.html / 404.html
│   │   ├── search.php              ← 런타임 검색 (라우팅/필터/렌더)
│   │   ├── search_tokenize.php     ← Py↔PHP 공통 토크나이저 (단일 진실원)
│   │   └── search_bm25.php         ← BM25 점수 + 스니펫 (단일 진실원)
│   │                                 (위 둘은 v0.6.0 부터 search.php 에 인라인)
│   ├── assets/                  ← 사이트 전역 자산 (/assets/ 로 로드)
│   │   ├── common_template.css / imgslidebox.js / pagination.js
│   │
│   └── tests/                   ← 단위 테스트 (297) + run_diagnostics.py (5 항목)
│
├── build.py                 ← 빌드 진입점 (자기 폴더의 src/ 를 sys.path 에 올림)
├── README.md                ← 이 문서
└── site.yaml                ← 사이트 전역 설정

빌드 시 프로젝트 루트에 자동 생성 (.gitignore 권장):
  build-report.md   ← 진행 트랜스크립트 + 요약 + 보완 항목 (dist/ 밖)
  .build_cache/     ← 글 단위 증분 캐시 (manifest.json + articles/)
```

> **v0.8.1:** 빌더 일체를 `src/` 한 폴더로 옮겨 최상위는 6 개뿐. `build.py` 가 자기 폴더의 `src/` 를 `sys.path` 맨 앞에 올리므로 `import scripts...` 가 그대로 동작. 아래 [§ 16](#16-업데이트-로그) changelog 의 `scripts/…`·`templates/…` 경로는 도입 시점의 역사 기록 — v0.8.1 부터 실제 위치는 모두 `src/` 접두.
>
> **v0.8.3:** schema.org JSON-LD 기능 릴리스 (구조 동일). 글 페이지 `<head>` 에 `<script type="application/ld+json">` 한 줄 추가 — `@graph` 로 `Article` + (crumb 2개↑이면) `BreadcrumbList`. 기존 OG/Twitter/canonical/robots `<meta>` 를 **대체하지 않고 보강** (additive). off 스위치: `site.yaml`→`jsonld.enabled` (전역) + `meta.yaml`→`seo.jsonld:false` (글 단위). 코드 릴리스라 dist 가 바뀐다 — v0.8.2 대비 글 페이지 47개가 각 ld+json 한 줄 추가, 그 외 738 파일 byte-동일 (0 missing/extra), 결정성 2회 동일.

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
lang: en                     # 이 글만 <html lang> 오버라이드 (v0.4.5, 비면 site.lang)

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
  jsonld:                    #   JSON-LD opt-out: false 면 이 글만 ld+json 미출력
                             #   (v0.8.3, 비면 site.yaml jsonld.enabled 따름)

styles:                      # § 4-6 — 인라인 미세 + 외부 CSS 두 채널
  # 1: style.css             #   정수 키 = 외부 CSS 파일 (글 폴더 안)
  p:                         #   문자열 키 = 인라인 룰
    text-indent: 0
    line-height: 1.7em
```

**slug 규칙** — 영어 소문자·숫자·하이픈만, 시작/끝은 영숫자, 사이트 전역 유일, 예약어(`assets`/`search`) 불가, 카테고리와 무관.

`seo.description` 은 누락/빈 문자열 시 빌드는 통과하지만 BuildReport issue 에 기록됩니다 (사실상 필수). `<meta name="keywords">` 는 제공하지 않습니다 (검색엔진이 무시).

`seo.jsonld` *(v0.8.3)* — 글 단위 JSON-LD 토글. 비우면 `site.yaml` 의 `jsonld.enabled` (기본 켜짐) 를 따름. `false` 면 이 글만 `<script type="application/ld+json">` 미출력. 사이트를 끄면 글 단위 `true` 로 되살릴 수 없음 (사이트 토글이 마스터). § 10 참조.

**메타데이터에 `{{대문자}}` placeholder 금지** — `title` · `seo.description` · `tags` · `seo.author` 는 빌더 템플릿 치환(`_render_template`)을 거쳐 `<meta>` · OG · Twitter · JSON-LD 로 동일하게 흘러갑니다. 이 네 필드에 **공백 없는 리터럴 `{{이름}}`** (이름이 대문자/언더스코어로 시작·구성 — 정규식 `{{[A-Z_][A-Z0-9_]*}}`) 을 쓰지 마세요. 빌더 변수명(`{{COPYRIGHT_YEAR}}` · `{{PAGE_TITLE}}` · `{{MAIN_TITLE}}` · `{{NAV_LINKS}}` · `{{BODY}}` 등)과 정확히 일치하면 그 변수 값이 산출물에 조용히 끼어들고(경고 없음), 변수 아닌 대문자 토큰이면 빈 문자열로 strip + 빌드 리포트에 경고가 납니다. 안전한 형태 — 소문자 `{{foo}}` · 안쪽 공백 `{{ FOO }}` · 홑 중괄호 `{NAME}` · 숫자 시작 `{{1A}}` · 비-ASCII `{{변수}}` 는 전부 무해(정규식·치환 모두 불일치). 그 외 문자(`"` `\` `<` `>` `&` · 개행 · 한글 · 이모지)는 자동 이스케이프되므로 신경 쓸 필요 없습니다. (`_render_template` 의 단순 문자열 치환 + `{`·`}` 미이스케이프에서 비롯 — JSON-LD 전용이 아니라 같은 경로의 메타 태그에도 동일 적용.)

### 4-3. content.md (마크다운)

파서는 [src/scripts/parsedown.py](src/scripts/parsedown.py) (Parsedown 1.7.4 Python 포팅). 표준 CommonMark 에 가까운 문법 + 이 시스템 전용 문법 (§ 9).

**이미지 경로** — 글 폴더 기준 상대경로. 빌드 시 절대경로로 자동 변환:

```markdown
![photo](./imgs/photo.jpg)   →   <img src="/my-slug/imgs/photo.jpg" alt="photo">
![외부](https://example.com/i.jpg)   ← 외부 URL 은 변환 안 함
```

**섹션 마커 (v0.4.3)** — 본문을 `<div class='gap'><p>부제</p></div><section>…</section>` 패턴으로 나눕니다:

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
  → src_slide/ 안 이미지를 알파벳 순 슬라이드로
```

이 둘 외의 `<?php ... ?>` 는 보존되며, 그 경우 글이 `.php` 확장자로 출력됩니다 (§ 8 PHP 자동 감지).

### 4-5. 자산 첨부

- **글 단위 자산** — 글 폴더 안에 둡니다. `meta.yaml`/`content.*` 와 `_`·`.` 접두 항목을 제외한 모든 파일·폴더가 `dist/{slug}/` 로 복사 (URL `/{slug}/imgs/…`). `_`·`.` 접두 파일/하위폴더는 비공개로 보고 복사하지 않습니다 (§ 6).
- **사이트 전역 자산** — 여러 글이 공유하는 CSS/JS/파비콘/로고/기본 OG 이미지는 `src/assets/` 에. `dist/assets/` 로 복사되어 `/assets/{경로}` 로 로드.

### 4-6. styles — 글 단위 CSS

`meta.yaml` 의 같은 `styles:` 키 아래 **두 채널**이 *키 타입*으로 자동 분기됩니다:

| 채널 | 키 형태 | 값 | 출력 | 의도 |
|---|---|---|---|---|
| 인라인 룰 | 문자열 (태그/선택자) | dict | head `<style>` | 자주 쓰는 속성 미세 override |
| 외부 CSS *(v0.6.3)* | 정수 (1,2,3…) | 글 폴더 안 상대경로 | head `<link>` | 자기 CSS 파일 (정수 오름차순) |

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

**폴더명 → slug 변환 (v0.4.0):** 비ASCII 문자 → 4자리 hex 코드포인트, NFKD 정규화, 영숫자·공백·하이픈만 유지, 괄호 제거, 공백·연속 하이픈 → 단일 하이픈, 소문자.

```
Blog               → blog
3D Printing        → 3d-printing
Research Notes (CS) → research-notes-cs
블로그              → be94-b85c-adf8   (비ASCII → hex, 빌드 워닝. ASCII 폴더명 권장)
```

**색인 페이지** — v0.4.5 부터 모든 카테고리(대·소분류)가 자기 인덱스 생성. 톱레벨은 자식 서브카테고리를 section 으로 임베드 + 직속 글 section. 글 없는 카테고리는 인덱스 미생성 + 빌드 경고.

**카테고리 폴더의 meta.yaml** (모두 선택, 글과 형식 다름 — `slug`/`date` 없음):

| 필드 | 기본 | 설명 |
|---|---|---|
| `per_page` | site `category_per_page` (20) | 자기 인덱스 페이지의 페이지당 글 수 |
| `preview_per_page` | site `category_preview_per_page` (5) | 상위에 section 임베드될 때 글 수 |
| `layout` | `list` | `list` / `gallery` (이미지 타일). 그 외는 list 폴백 |
| `styles` | {} | 글 `styles` 와 동일 두 채널 (v0.6.4) |
| `use_common_css` | `true` | v0.6.4 |
| `template` | `category.html` | v0.6.4. `name.html`→`src/templates/`, `./name.html`→폴더 |
| `lang` | site `lang` | `<html lang>` 오버라이드 |
| `title` | 폴더명 | v0.5.4. 인덱스 `<title>` 본문 |
| `seo` | {} | v0.5.4. 글 `seo:` 와 동일 (v0.6.2 부터 메타 태그 출력) |
| `priority` | `0` | v0.4.6. 상위 인덱스 내 형제 section 정렬 (큰 값 먼저) |
| `nav_priority` | `0` | v0.5.4. 톱레벨 nav 정렬 (priority 와 별개 축) |

**`layout: gallery`** — 글 목록을 이미지 타일로 (CSS Grid `auto-fill, minmax(220px,1fr)`, 4:3 크롭, subtle hover, 모바일 2열). 썸네일: `seo.og_image` → `site.default_og_image` → 빈 플레이스홀더 (v0.5.5: 본문 첫 이미지 폴백 폐기). WebP srcset 자동 부착.

추가 layout 이 필요하면 [src/scripts/builder.py](src/scripts/builder.py) 의 `_listup_items_html`/`_render_section` 분기 + [src/assets/common_template.css](src/assets/common_template.css) 의 `section.listup-{layout}` + pagination.js selector 에 직접 등록.

---

## 6. 글 관리 — 비공개·이동·삭제

- **비공개** — 파일/폴더명 앞에 `_` 또는 `.`. 경로의 어느 세그먼트든 `_`·`.` 접두면 그 아래 전체가 글·카테고리·nav·자산에서 모두 제외. 빌드 시 `dist/{slug}/` 자동 삭제. `_` = 의도적 비공개·편집 중, `.` = OS/VCS 숨김(`.git`·`.DS_Store`) **그리고** `.draft` 처럼 작성자가 "숨겼다" 고 믿는 폴더가 실수로 공개되는 길을 막음 *(v0.8.3 일원화 — 정본 `Articles/` 에 `.` 접두 항목이 없어 산출물 byte 영향 0)*.
- **이동** — 글 폴더를 다른 카테고리로 옮겨도 `slug` 가 같으면 URL 불변.
- **삭제** — 글 폴더 삭제 후 빌드하면 `dist/{slug}/` 자동 정리 (고아 정리).

---

## 7. 빌드

```bash
python build.py            # 일반 빌드 (증분 캐시)
python build.py --clean    # dist/ + .build_cache/ 폐기 후 빌드
```

**빌드 리포트 (v0.5.5)** — 콘텐츠 결함은 빌드를 중단시키지 않고 *글 단위로 산출물 일부 누락* 후 완성. 종료 시 stderr 에 두 묶음으로 정렬 + `build-report.md` 영속:

| 분류 | 의미 | 사례 |
|---|---|---|
| **issue** (보완 필요) | 작성자가 손볼 글 단위 문제. 그 글만 부분 누락 | `seo.description` 누락, slug 정규식/예약어/중복 충돌, date 형식 오류, `tags` 비-list |
| **warning** (살펴볼 사항) | 산출물 정상, 한 번 볼 가치 | 비ASCII 폴더명 hex 변환, stale `updated`, 자산 누락, 빈 카테고리, 이미지 최적화 실패 |

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
├── index.html  404.html  robots.txt  sitemap.xml  feed.atom  feed.rss
├── assets/                  ← 사이트 전역 자원
├── {slug}/                  ← 글 페이지 + 글 자산 (같은 폴더, v0.5.2)
│   ├── index.html  (또는 index.php)
│   └── imgs/ …
├── blog/                    ← 카테고리 색인
│   ├── index.html
│   └── tutorials/index.html ← 서브카테고리 (v0.4.5)
└── search.php               ← 인덱스+토크나이저+BM25 모두 인라인 (v0.6.0)
```

| 페이지 | URL | 예시 |
|---|---|---|
| 홈 | `/` | `https://siheonlee.com/` |
| 글 | `/{slug}/` | `/mask-intake-3d-printing/` |
| 카테고리 톱레벨 | `/{cat}/` | `/blog/` |
| 카테고리 서브 | `/{top}/{sub}/` | `/blog/tutorials/` |
| 글 첨부 | `/{slug}/{경로}` | `/mask-intake-3d-printing/imgs/p.jpg` |
| 전역 자산 | `/assets/{경로}` | `/assets/common_template.css` |
| 시스템 | `/404.html` `/robots.txt` `/sitemap.xml` | |

- 모든 글·카테고리 URL 은 `/` 로 끝남. 슬래시 없는 URL 은 Apache 가 301 리다이렉트.
- 글 URL 은 카테고리와 독립. 단 slug 예약어(`assets`/`search`)는 불가.
- **PHP 자동 감지** — 렌더 결과에 `<?php`/`<?=` 가 남으면 `index.php` 로 출력. URL 은 `/{slug}/` 동일, Apache `DirectoryIndex` 가 처리.

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

글/홈/카테고리가 같은 폴백 체인을 공유 (v0.6.2 부터 한 함수 [`build_meta_tags`](src/scripts/seo.py)). 본문 title: 글=`meta.title`, 홈=`Articles/meta.yaml title`>`site.name`, 카테고리=`meta.title`>폴더명.

| 출력 태그 | 1순위 | 2순위 | 3순위 |
|---|---|---|---|
| ◆ `<title>` | `{prefix}{title}{suffix}` | site 디폴트 prefix/suffix | — |
| ● `meta description` | `seo.description` | *본문 폴백 폐기 (v0.5.5)* | 생략 + issue 기록 |
| `meta author` | `seo.author` | `site.default_author` | 생략 |
| ■ `link canonical` | `seo.canonical` | 자동 (글 `/{slug}/`, 홈 `/`, 카테고리 `/{top}/{sub}/`) | — |
| ◆ `og:title` | `seo.og_title` | `<title>` 결과 | — |
| ● `og:description` | `seo.og_description` | `meta description` 결과 | 생략 |
| ▲ `og:image` | `seo.og_image` | `site.default_og_image` | 생략 *(본문 폴백 폐기)* |
| ◆ `og:image:alt` | `seo.og_image_alt` | 페이지 title | 생략 |
| `og:type` | `seo.og_type` | 글=`article`, 홈/카테고리=`website` | — |
| ■ `og:url` / `og:site_name` | canonical / `site.name` | — | — |
| `article:published/modified_time` | 글 `date` / `updated`(없으면 date) — 글에만 | — | — |
| `twitter:card` | `seo.twitter_card` | `summary_large_image` | — |
| ◆●▲ `twitter:title/description/image` | (og 와 동일) / `seo.twitter_image`→og:image | — | 생략 |

**기호 그룹** — 같은 기호 = 최종적으로 같은 값으로 수렴하는 체인: ◆ = `<title>` 값 · ● = `meta description` 값 · ▲ = `og:image` 값 · ■ = `canonical` 값. (기호 없는 행은 독립 / `twitter:*` 는 og 경유라 ◆●▲ 셋 다 해당.)

**폴백 결과가 빈 문자열이면 태그 자체를 출력 안 함.** `''` 와 `None` 은 산출물에선 동일(태그 누락)하나, `seo.description` 만 `''` 를 작성자 실수로 간주해 BuildReport 에 기록.

**색인 정책 (v0.4.0)** — 기본 색인 허용. `noindex: true` 글만 그 페이지 `<head>` 에 `<meta robots noindex>`. search.php 만 `noindex,follow` 별도 차단.

**JSON-LD 구조화 데이터 (v0.8.3)** — **글 페이지**의 `<head>` 에 `<script type="application/ld+json">` 한 줄. `@graph` 로 두 노드:

- `Article` — `headline`(글 title) / `datePublished`(date) / `dateModified`(updated>date) / `description`(`seo.description`, 부재 시 키 생략) / `author`(`seo.author`>`site.default_author`, Person) / `publisher`(`site.name`, Organization) / `image`(`og:image` 와 같은 해석) / `keywords`(`tags`) / `inLanguage`(글 lang) / `url`·`mainEntityOfPage`(canonical).
- `BreadcrumbList` — 사이트 nav-tracker 와 **단일 공유 소스** (같은 라벨·경로, 어긋날 수 없음). 각 조상 카테고리는 *자기 중첩* 인덱스 URL (`/{top}/…/{cat}/`) 로 링크. 마지막(현재 글)은 글 **제목**(= `Article.headline`) 을 이름으로 쓰고 schema.org 권장대로 `item` 생략. crumb 가 2개 미만(톱레벨 글)이면 노드 자체 생략.

기존 `<meta>`/OG/Twitter 를 **대체하지 않고 보강** — 소비자가 다릅니다 (SNS 언퍼ler=OG, SERP 스니펫=`meta description`, 색인 제어=`robots` meta, 검색 엔진 리치 결과=JSON-LD). `description`/`image`/`author` 는 `build_meta_tags` 와 같은 폴백을 공유 (어긋남 없음). canonical/og_image/author 미해석 시에도 본문 추출 폴백은 없음 (설계 원칙 10 동일). **off**: `site.yaml`→`jsonld.enabled: false` (전역) 또는 글 `seo.jsonld: false`. 홈/카테고리에는 출력하지 않습니다 (`article.html` 만 `{{JSONLD}}` 보유 — `seo.jsonld` 는 파싱만, forward-compat).

---

## 11. 사이트 전역 설정 — site.yaml

*진짜 전역* (여러 페이지 공통) 만 둡니다. **페이지 한 종 전용 설정은 그 페이지의 meta.yaml 에:**

| 위치 | 설정 |
|---|---|
| `site.yaml` | 도메인·name·copyright·lang·default_og_image / `category_per_page`·`category_preview_per_page` / robots.txt / reserved_slugs / warn_on_* / `description_truncate` / `images:` / `jsonld:` / `error_404_title`·`search_title` |
| `Articles/meta.yaml` | 홈 전용 — `per_page` `excludes_categories` `lang` `layout` `styles` `title` `seo:` |
| `Articles/<cat>/meta.yaml` | 카테고리 전용 (§ 5 표) |
| `Articles/<cat>/<글>/meta.yaml` | 글 전용 (§ 4-2) |

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
error_404_title: Not Found            # 시스템 페이지 <title> 본문 (v0.5.4)
search_title: Search
copyright_holder: 이시헌
copyright_year_start: 2025
reserved_slugs:                       # 글 slug 금지어
  - assets    # /assets/    전역 자산
  - search    # /search.php  검색
category_per_page: 20                 # 카테고리 페이지네이션 디폴트 (v0.4.5)
category_preview_per_page: 5
description_truncate: 150             # 피드 summary 의 seo.description 절단 최대 글자 (단어 경계 존중; 본문 자동추출 아님)
warn_on_underscore_ref: true          # `_` 접두 경로 참조 시 워닝
warn_on_missing_asset: true           # meta.yaml 지정 자산 누락 시 워닝
warn_on_stale_updated: true           # updated 가 date 보다 과거면 워닝
robots_txt_main: |
  User-agent: *
  Allow: /

  Sitemap: https://siheonlee.com/sitemap.xml
images:                               # 이미지 자동 최적화 (v0.5.1, 생략 시 아래 기본값)
  enabled: true                       #   false 면 Pillow 없이 빌드 통과
  widths: [400, 800, 1600]            #   생성할 WebP 변종 너비
  max_width: 1600
  quality: 85
  lazy_loading: true                  #   enabled=false 여도 독립 동작
  default_sizes: "(max-width: 800px) 100vw, 800px"
jsonld:                               # schema.org JSON-LD (v0.8.3, 생략 시 켜짐)
  enabled: true                       #   false 면 모든 글에서 ld+json 미출력
                                      #   (글 단위는 meta.yaml seo.jsonld: false)
```

**Articles/meta.yaml** (홈 전용, 선택 — 없으면 `per_page=5`, `excludes_categories=[]`):

```yaml
per_page: 5                  # 메인 Recent posts 페이지당 글 수
excludes_categories: [About] # Recent 에서 제외할 톱레벨 (About 등)
layout: list                 # list / gallery
# lang: ko
# styles: { 1: home.css, p: { line-height: 1.7em } }   # v0.6.4
# use_common_css: true        # v0.6.4
# template: my_landing.html   # v0.6.4 (templates/ 또는 ./Articles/ 안)
```

> 카테고리 meta.yaml 과 같은 스키마를 공유 — 홈에서 `preview_per_page`/`priority` 는 임베드 대상이 없어 무시 (의도된 비대칭). 톱레벨 카테고리에서도 `preview_per_page` 는 사실상 무의미.

---

## 12. 내부 구현 — 파서 / 검색 / 피드

### 마크다운 파서 — Parsedown 1.7.4 Python 포팅

v0.4.1 부터 단일 구현 [src/scripts/parsedown.py](src/scripts/parsedown.py) 만 사용 (옛 `MarkdownRenderer` 추상화 / `markdown_parser:` 옵션 폐지).

```
content.md → preprocess (![[...]]{...} → HTML) → Parsedown().text()
           → finalize (asset 경로 재작성, PHP 시뮬레이션) → RenderResult(html)
```

- 원본: [Parsedown](http://parsedown.org) 1.7.4 (c) Emanuil Rusev, MIT. 포팅은 메서드명·dispatch·dict 키까지 원본과 일대일. 외부 의존성 없음 (stdlib `re`/`typing`).
- 출시 시점 PHP Parsedown 과 **79/79 fixture 바이트 일치** (합성 46 + 실 글 33), v0.4.0↔v0.4.1 dist 동일 확인.
- **운영 정책 — 포크.** 이 포팅이 단일 진실원. 원본 신버전을 따라가지 않으며 모든 수정은 이 포팅에 직접. PHP 비교 대상(Parsedown.php)은 트리에 동봉하지 않음. [src/tests/test_parsedown.py](src/tests/test_parsedown.py) 는 Python 포트 회귀 가드 한정.
- PHP↔Python 정규식 차이는 포팅에서 처리 (`\w` `re.ASCII`, `(?R)` 수동 bracket matcher, possessive → `+`/`*`, single quote `&#039;`).

### YAML 파서 — 의도된 부분집합

site.yaml/meta.yaml 파서는 자체 구현 ([src/scripts/yaml_parser.py](src/scripts/yaml_parser.py)). *실제 사용하는 문법의 부분집합* 만.

- **지원:** 평면 key-value, nested mapping, block list (`- a`), inline list (`[a,b]`), 따옴표 문자열, 정수·진릿값·null, 라인 단위 `#` 주석.
- **미지원 (의도):** anchor/alias, folded scalar `>`, block scalar chomping 변형, flow mapping `{...}`, 인라인 주석, multi-document.
- **PyYAML 도입 계획 없음** — 부분집합으로 충분, 외부 의존성 부담 회피. 새 문법은 이 파서에 직접 추가.

### 검색 — search.php

클라이언트 JS 0, 외부 검색엔진 0. **메타데이터 3-필드 (title / seo.description / tags) 만 색인** (v0.6.0; 본문 검색 미지원 — 본문 평문은 앞 1500 자만 `body_snippet` 으로 스니펫용 보존).

```
[빌드] 모든 글 (title/desc/tags) 토크나이즈 → BM25 인덱스 (v4) + PHP 정적 배열로 직렬화
       → dist/search.php 한 파일에 토크나이저 + BM25 함수 + 인덱스 모두 인라인.
       noindex 글 제외 (sitemap/feed 와 일관).
[검색] nav 검색창 → /search.php?q=… → OPcache 에서 로드 (인덱스 메모리 상주)
       → 같은 토크나이저로 3 필드 BM25 가중합 → phrase 부스트 → 스니펫 → 결과 렌더.
```

- **UI** — 홈·카테고리 인덱스 nav 우측에만. 카테고리 페이지는 `?cat=<slug>` 자동 첨부 → 그 톱레벨 내부로 한정 (화이트리스트 검증, 잘못된 cat 은 전체 폴백). 결과 헤더에 범위 + 전체 토글. 결과 스니펫은 매치 밀도 80자 윈도우 + `<mark>` 강조.
- **토크나이저** — 영문/숫자 = 단어 단위 소문자 (정확 매치), 한글 = 음절 2-gram (부분 검색 자연 지원), **1글자 한국어 제외** (v0.4.0). [src/scripts/search.py](src/scripts/search.py) `search_tokenize()` ↔ [src/templates/search_tokenize.php](src/templates/search_tokenize.php) 가 단일 진실원, 빌드마다 18 fixture 패리티 자동 검증 (PHP 없으면 워닝 후 skip).
- **점수** — 필드별 Okapi BM25 (`IDF·tf(k1+1)/(tf+k1(1-b+b·dl/avgdl))`, Robertson-Spärck Jones IDF). 가중합 w_title=3.0 / w_desc=1.5 / w_tags=2.0. phrase 부스트(곱셈): title ×2.0, desc ×1.5, tags 정확매치 ×2.5. params 가 인덱스에 박혀 점수 결정적. `tests/test_bm25.py` (31) + run_diagnostics 가 Py↔PHP 패리티 검증.
- **보안** — 쿼리 100자 제한, 모든 출력 `htmlspecialchars` escape (강조는 escape 후), 결과 페이지 `noindex,follow`.
- **서버** — PHP 7.4+ + `mbstring`. 추가 확장 불필요.
- **비활성화** — `src/templates/search.php` 삭제 (경고 후 search.php 미생성) + [src/templates/home.html](src/templates/home.html)·[src/templates/category.html](src/templates/category.html) 의 `<form class='nav-search'>` 제거.

### RSS / Atom 피드 (v0.5.3)

`dist/feed.atom` (Atom 1.0) + `dist/feed.rss` (RSS 2.0) 가 같은 entry 목록. 모델은 [src/scripts/feed.py](src/scripts/feed.py) 의 `FeedDocument`/`FeedEntry`.

- **포함:** non-noindex 글, `excludes_categories` 제외, 최신 N개 (기본 20, `DEFAULT_MAX_ENTRIES`), `updated`(없으면 `date`) 내림차순.
- **entry:** title=`meta.title`, link/id=절대 URL, published=`date`, updated=`updated`, summary/description=`seo.description` (본문 폴백 폐기, 부재 시 누락+issue), author=`seo.author`>`site.default_author` (RSS 는 생략), category=톱레벨 폴더명 + `tags`.
- **자동 발견** — 페이지 `<head>` 에 `<link rel='alternate' type='application/atom+xml'>` / `rss+xml` 삽입.
- **결정성** — `date`/`updated` 는 모두 `00:00:00 UTC`. 피드 `updated`/`lastBuildDate` 도 빌드 시각이 아닌 entry 최신 lastmod → 콘텐츠 변경 없으면 매 빌드 같은 바이트.
- **비활성화** — [src/scripts/builder.py](src/scripts/builder.py) `build()` 의 `self._build_feeds()` 주석 처리 (site.yaml 토글 없음).

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

- **빌드 머신**에는 PHP 불필요 (v0.4.1). PHP CLI 있으면 토크나이저 패리티 자동 검증.
- **배포 서버**는 **PHP 7.4+ + mbstring** 필요 (search.php + `.php` 출력 글). 이것은 한계가 아니라 전제.

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
| PHP 없이 빌드 가능? | v0.4.1 부터 가능 (파서 순수 Python). PHP CLI 없으면 패리티 검증만 워닝 후 skip. 배포 서버는 PHP 필요. |
| styles 가 적용 안 됨 | ① styles·외부 CSS 는 글·홈·카테고리 모두 동일하게 inject (v0.6.4 일원화) — 홈은 `Articles/meta.yaml`, 카테고리는 그 카테고리 `meta.yaml` 에 작성. ② 템플릿에 `{{PAGE_STYLES}}`/`{{PAGE_STYLESHEETS}}` 있는지. ③ specificity 충돌 → 구체 셀렉터/`!important`. ④ `:hover`/`#id`/`::before` 는 YAML 인용. |
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
6. **파서 단일화 (v0.4.1)** — Parsedown Python 포팅 하나로 통일.
7. **글 단위 표현 제어** — meta.yaml 에서 선언적으로.
8. **글 단위 색인 (v0.4.0)** — 기본 허용, `noindex: true` 글만 제외.
9. **단일 진실원 토크나이저 (v0.4.0)** — Py/PHP 패리티 빌드마다 자동 검증.
10. **본문 ↔ 메타데이터 분리 (v0.5.5)** — SEO/OG/피드 카피는 본문이 아니라 author 가 `seo:` 블록에 직접 쓴 값에서만. 본문=독자용, 메타=SERP/소셜용 — 다른 글이어야 함. SSG 는 추측하지 않음. `seo.description` 필수(누락 시 issue, 빌드는 통과). `og_image` 부재 시 본문 추출이 아니라 `site.default_og_image`.
11. **`template:` 가로지르기 — 허용하되 알린다 (v0.6.4)** — 페이지 종류와 다른 템플릿 지정 가능. 빌더가 못 채우는 placeholder 는 strip + warning (자동 거부도 silent strip 도 아닌, 알림 + author 판정).

**현재 한계 (v0.8.3)** — 두 부류. ⓐ 현 능력의 *내재적* 한계, ⓑ *의도적으로 보류한* 확장. **둘 다 현 상황에서는 도입하지 않는다** (사용자 합의 2026-05-18 — 사유가 유효한 동안 유지, 필요해질 때 재검토).

**ⓐ 내재적 한계**

| 한계 | 내용 |
|---|---|
| 이미지 최적화는 정적 단일 프레임 | animated GIF 는 첫 프레임만 WebP. 보존하려면 webp 직접 첨부/외부 URL. 글·이미지 단위 토글 없음 (전역 `images.enabled` 만). |
| 증분 캐싱은 글 페이지만 (v0.7.0) | 검색/sitemap/feed/홈/카테고리/assets 는 모든 글이 입력이라 매 빌드 재구축 (의도된 범위). |

**ⓑ 의도적으로 보류한 확장** (도입 금지 — 아래 사유 유효한 동안)

| 확장 후보 | 현재 | 지금 도입 안 하는 이유 |
|---|---|---|
| 홈/카테고리 JSON-LD | 글 페이지만 (`article.html` 만 `{{JSONLD}}`). `seo.jsonld` 는 홈/카테고리 `meta.yaml` 에서도 파싱되나 forward-compat (미사용) | 합의 범위 = 글 `Article`+`BreadcrumbList`. 홈 `WebSite`+`SearchAction` 은 검색 URL 계약을 구조화데이터에 고정(추측 리스크), 카테고리 `ItemList` 은 페이지네이션과 얽혀 열거 diff 표면이 크고 리치결과 효용 낮음 |
| 태그 색인 페이지 `/tag/<slug>/` | `tags` 는 feed `<category>`·BM25·JSON-LD `keywords` 에만 쓰임. 탐색 페이지 없음 | URL 영구성 약속이 늘고 `tags` 가 1급 분류 축으로 승격 → "카테고리가 분류 축" 설계와 충돌 (이 프로젝트는 의도적으로 `CategoryMeta` 에서 `tags` 제외). 도입 전 분류 축 정의를 먼저 결정해야 함 |
| 글 렌더 병렬화 | 순차. v0.8.2 per-Builder 는 *동시 빌드 구조적 봉쇄만* 해제 (실제 병렬화 아님) | 47글·빌드 ~3–4s, 지배적인 이미지 변환은 이미 별도 단계 → ROI 낮음. 결정성(2회 빌드 byte 동일)·캐시 replay·리포트 순서 제약 비용이 큼. 글이 수백 단위가 되면 재검토 |

---

## 16. 업데이트 로그

> changelog 본문의 `scripts/…`·`templates/…`·`tests/…` 경로는 도입 시점 역사 기록. v0.8.1 부터 실제 위치는 모두 `src/` 접두 (§ 3).
> 코드 정합성 검증 관례: **문서 전용 릴리스** 는 정본 `Articles/` 클린 재빌드 후 `dist/` sha256 이 직전 코드 복사본과 동일함을 확인. **코드 릴리스** 는 결정성(2회 빌드 동일) + *직전 코드 릴리스* 기준 *열거된* diff 로 검증 (비변경 산출물 byte-동일 + 변경 명시).
> v0.8.2 가 버전 디커플링 분기점 — 이전엔 `__version__` bump 이 feed `<generator>` 를 통해 dist 를 바꿔 문서 릴리스가 `__version__` 을 동결해야 했으나, v0.8.2 부터 generator 가 버전-free 라 `__version__` 의 dist 영향이 0. 따라서 v0.8.2 이후 문서 릴리스는 진짜 byte-동일 (무비용).
> v0.8.3 은 *기능* 릴리스라 dist 를 바꾼다 — 글 페이지 `<head>` 에 schema.org JSON-LD (`@graph`: `Article` + crumb 2개↑ 시 `BreadcrumbList`) 추가. 빵부스러기는 처음부터 정확한 의미로 출시 — nav-tracker HTML 과 `BreadcrumbList` 가 단일 공유 소스(`_crumb_parts_for`)를 먹어 중간 조상 = 자기 중첩 카테고리 URL (`/{top}/…/{cat}/`), 글 말단 = 글 **제목**(= `Article.headline`, 폴더명 아님). 게이트도 함께 — `run_diagnostics` 에 JSON-LD 의미 검증 [6] 신설 (position 단조·비말단 item distinct·dist 실재·말단 name==headline) 으로 additive·결정성-only 게이트가 놓치는 *의미* 결함 부류를 가드 (§ 15 ⓑ "추측 리스크" 의 거울 — 추측이 아니라 *미검사* 누락). v0.8.2 대비 변경은 **글 렌더 페이지에 한정** (ld+json 추가 + 빵부스러기 정확 라벨·링크) — 비-글 산출물(피드/사이트맵/검색/홈/카테고리/자산/이미지) byte-불변, 0 missing/extra, 결정성 2회 동일, 단위 266→313. `meta.yaml` 스키마·명시 `slug:` 불변, 폴더명은 출력 무관 자유 (마이그레이션 아님). `__version__` 자체의 dist 누수는 0 (B1 유지) — dist 변경은 JSON-LD 기능·정확 빵부스러기 때문. 같은 릴리스에서 빌드 제외 접두도 `_` 단독 → `_`·`.` 로 일원화 (`is_excluded_path`) — `.draft`·`.git`·`.DS_Store` 같은 숨김 항목이 글/카테고리/nav/자산으로 새지 않게 가드; 정본 `Articles/` 에 `.` 접두 항목이 없어 위 byte-불변 주장과 무모순.

| 버전 | 날짜 | 요약 |
|---|---|---|
| **v0.8.3** | 2026-05-18 | schema.org JSON-LD + 정확 빵부스러기 (코드 릴리스) — 글 페이지 `<head>` 에 `<script type="application/ld+json">` 한 줄 (`@graph`: `Article` + crumb 2개↑ 시 `BreadcrumbList`). 기존 OG/Twitter/canonical/robots `<meta>` 보강 (대체 아님). off: `site.yaml`→`jsonld.enabled` + `meta.yaml`→`seo.jsonld`. `seo.py` `build_jsonld`/`jsonld_enabled` 신설, canonical/og_image/author 해석을 `build_meta_tags` 와 공유 헬퍼로 추출 (메타 태그 byte 불변). 빵부스러기 의미 정확 — nav-tracker HTML 과 `BreadcrumbList` 는 단일 공유 소스(`_crumb_parts_for`): 각 중간 조상은 자기 중첩 카테고리 URL (`/{top}/…/{cat}/`), 글 말단 = 글 **제목**(= `Article.headline`, 폴더명 아님). 명시 `slug:` 유지·`meta.yaml` 스키마 불변 (폴더명은 출력 무관 자유). 게이트: `run_diagnostics` JSON-LD 의미 검증 [6] 신설 (position 단조·비말단 item distinct·dist 실재·말단 name==headline) — additive·결정성-only 게이트가 놓치는 의미 부류 가드. dist 는 v0.8.2 대비 글 렌더 페이지만 변경 (ld+json + 빵부스러기 정확 라벨·링크), 비-글 산출물 byte-동일, 결정성 2회 동일. 부수로 빌드 제외 접두를 `_` 단독 → `_`·`.` 로 일원화 (`slugs.is_excluded_path`/`is_excluded_name` 신설, 스캔·nav·자산 동기화가 단일 진실원 공유) — `.draft`·`.git`·`.DS_Store` 등 숨김 항목이 글·카테고리·nav·자산으로 새지 않음 (§ 6); 정본 `Articles/` 에 `.` 접두 항목이 없어 dist byte 영향 0. 단위 266→313. |
| v0.8.2 | 2026-05-18 | 코드 건전성 — (1) `__version__` 디커플링: feed `<generator>` 에서 버전 토큰 제거 → `__version__` 의 dist 영향 0, `'0.7.2'`→`'0.8.2'`. (2) `build.py` argparse: `--help` + 미지/오타 인자 거부. (3) 빌드 리포트 모듈 전역 → per-Builder + `build()` 멱등성 결함 1건 수정. dist 는 v0.8.0 과 `feed.atom`/`feed.rss` generator 한 줄만 차이 (의도). 단위 258→266. |
| v0.8.1 | 2026-05-17 | 폴더 구조 정리 — 빌더 일체를 `src/` 아래로, 최상위 6 항목. 코드 동작·산출물 불변 (dist v0.8.0 과 byte 동일, `__version__` 0.7.2). |
| v0.8.0 | 2026-05-17 | README 코드 정합성 정정 (문서 결함 5건: §5 카테고리 필드 / §8 서브 URL 행 / §10 sitemap 회고 / 빌드 출력 예시 / 버전 표기). 코드·dist 무변경. |
| v0.7.2 | 2026-05-17 | 16 단계 진행 헤더 + 무거운 루프 라이브 카운터 + `build-report.md` 영속 리포트. 산출 로직 무변경. |
| v0.7.1 | 2026-05-16 | 안정화 — 파이프라인 docstring/§2 표/본문 폴백 잔존/§ cross-ref 정정. 코드 동작 무변경. |
| v0.7.0 | 2026-05-16 | 빌드 증분 캐싱 (글 단위). `--no-cache`/`--clean-cache` 추가. `cache.py` 신설. 테스트 231→258. |
| v0.6.5 | 2026-05-15 | 안정화 — reset_report 자동 호출 / `_render_template` 3-pass / og_type 강제 디폴트 제거. 회귀 4건. |
| v0.6.4 | 2026-05-15 | 홈/카테고리 CSS 일원화 + `template:` 키. placeholder 통일 + `_sync_page_css`. |
| v0.6.3 | 2026-05-15 | 글 단위 외부 CSS 파일 (정수 키) + `use_common_css` 토글. |
| v0.6.2 | 2026-05-15 | 홈/카테고리 SEO 메타 태그 출력 (description/og_*/twitter_*/canonical). |
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

*siheonlee.com v0.8.3 — 빌드 Python + Pillow, 런타임 PHP. 검색 Okapi BM25 메타데이터 3-필드 인라인 인덱스, 이미지 WebP 다중 해상도 자동, 글/홈/카테고리 통일 SEO 메타 + 외부 CSS·`template:` 지원, schema.org JSON-LD (글 페이지 `Article`+`BreadcrumbList`, 기존 메타 태그 보강·off 스위치 동반). 빵부스러기는 정확한 의미로 출시 — 중간 조상=자기 중첩 URL, 글 말단=글 제목 (nav-tracker/JSON-LD 단일 공유 소스); JSON-LD 의미 게이트 [6] 동반. (2026-05-18)*

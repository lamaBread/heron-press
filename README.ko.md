# Heron v1.14.4 — 사용설명서

**Heron** 은 **글마다 폴더 하나**를 만들어 본문·첨부를 관리하고, `python Heron.py` 한 번으로 사이트를 만드는 **PHP 기반 경량 웹 사이트 생성기**입니다.

> 🇬🇧 The English guide is at [README.md](README.md). 두 문서는 같은 시스템을 같은 깊이로 다룹니다 (이중언어 동등).

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
17. [로컬 글쓰기 — Pond.php](#17-로컬-글쓰기--pondphp)
18. [추가 업데이트 제안](#18-추가-업데이트-제안)

---

## 1. 빠른 시작

**준비물**

- **Python 3.x** (3.8+ 권장).
- **Pillow** — raster 이미지를 WebP 다중 해상도로 변환. `pip install Pillow`. 회피하려면 `site.yaml` 의 `images.enabled: false`.
- **PHP CLI** (선택) — 있으면 빌드 시 Python↔PHP 토크나이저 패리티를 자동 검증. 없으면 워닝 후 건너뜀.

**빌드** — 이 폴더에서 터미널을 열고:

```bash
python Heron.py                # 평소 빌드 (증분 캐시 사용)
python Heron.py --clean        # dist/, .build_cache/ 모두 폐기 후 빌드
python Heron.py --clean-cache  # 캐시만 폐기, dist 유지
python Heron.py --no-cache     # 캐시 비활성
```

성공 시 출력 형태:

```
빌드 시작 - Heron v1.8.0 (...)
[ 1/16] 설정 로드 (site.yaml / 토크나이저 패리티)
[ 2/16] 글 폴더 스캔 (user/articles/)
   …  (각 단계 [ n/16] 헤더, 무거운 단계는 \r 라이브 카운터)
[16/16] 고아 산출물 정리

빌드 완료: 47 글, 19 카테고리, 0 보완 필요, 0 살펴볼 사항, PHP 빌드 N건.
증분 캐시: 0 hit / 47 miss (글 47건).
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

글마다 폴더 하나를 만들면 `python Heron.py` 가 정적 HTML + 검색 PHP 를 만들고, Apache 가 그대로 서빙합니다.

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
| 2 | `user/articles/` 트리 스캔 |
| 3 | 각 글 `meta.yaml` 파싱 |
| 4 | 검증 (slug 중복/예약어/형식) + 카테고리 트리 구축. 문제 글은 issue 기록 + 그 글만 산출물 제외, 빌드는 계속 |
| 5 | 글별 자산 → `dist/{slug}/` 복사. raster 이미지는 Pillow 로 WebP 변환 (멀티프로세스) |
| 6 | `user/styles`·`user/branding`·`system/runtime`(*.js) → `dist/assets/` 복사 (사이트 공통 자산) |
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

v1.5.0 부터 루트가 **`user/` (네가 편집) 와 `system/` (프로그램) 로 갈렸다:**

```
heron-press/
│
├── user/                    ← ★ 네가 소유·편집하는 모든 것
│   ├── articles/                ← 모든 글 (바로 빌드되는 예시 글 세트 포함 — § 4-7)
│   │   ├── About/                   ← 톱레벨 글 (meta.yaml + content.html + 자산)
│   │   └── Blog/                    ← 카테고리 폴더
│   │       └── Welcome to Heron/    ← 글 폴더 (폴더명 = 화면 표시명)
│   │           ├── meta.yaml        ← slug/제목/날짜/styles
│   │           ├── content.md       ← 본문 (또는 content.html)
│   │           └── imgs/            ← 첨부 (선택)
│   ├── site.yaml                ← 사이트 전역 설정 (§ 11)
│   ├── templates/               ← 페이지 레이아웃 HTML (헤더/nav/푸터/구조)
│   │   └── article.html · category.html · home.html · 404.html
│   ├── styles/                  ← 전역 스타일시트
│   │   └── common_template.css      ← /assets/common_template.css 로 로드
│   ├── branding/                ← 사이트 정체성 자산
│   │   └── default-og.png           ← 기본 og:image (향후 favicon·logo 도 여기)
│   └── .heron/                  ← (v1.6.0) 기계 관리 인스턴스 상태 — 손으로 편집 금지
│       ├── version                  ← 스키마 버전 스탬프 (§ 17-6; system/ 교체에도 생존)
│       ├── update.json              ← 업데이트 체크 캐시 (Pond 배너; .gitignore)
│       ├── deploy.example.json      ← (v1.7.0) 배포 설정 견본 (커밋; § 17-7)
│       ├── deploy.json              ← (v1.7.0) 실제 배포 좌표·키 경로 (.gitignore)
│       └── backups/                 ← 마이그레이션/업데이트 직전 스냅샷 (.gitignore)
│
├── system/                  ← ★ 프로그램 (사이트 운영에는 손대지 않음)
│   ├── MANIFEST.json            ← (v1.6.0) 프로그램 표면 파일 목록 + sha256 (무결성 / 안전 오버레이)
│   ├── scripts/                 ← 빌드타임 Python 패키지 (Heron.py 내부 모듈)
│   │   ├── __init__.py             ← __version__ (프로그램 버전 단일 source)
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
│   │   ├── i18n.py                 ← (v1.9.0) 로케일 문자열 lookup (Surface 1/3; en 정본 + 파서)
│   │   ├── version.py              ← (v1.6.0) 스키마 버전 스탬프 + semver 비교
│   │   ├── migrations/             ← (v1.6.0) 마이그레이션 엔진 (순서 스텝, user/ 만 변형)
│   │   ├── update.py               ← (v1.6.0) GitHub 자가 업데이트 (다운로드/검증/오버레이)
│   │   ├── make_manifest.py        ← (v1.6.0) MANIFEST.json 생성/검증
│   │   ├── rclone_bin.py           ← (v1.7.0) rclone 바이너리 확보 (다운로드/SHA256 검증/추출)
│   │   ├── deploy.py               ← (v1.7.0) dist 서버 배포 오케스트레이션 (rclone SFTP)
│   │   └── builder.py              ← 빌드 파이프라인 (Builder 클래스)
│   ├── runtime/                 ← 서브타임 코드 (방문자 요청 시 실행)
│   │   ├── search.php               ← 런타임 검색 (라우팅/필터/렌더)
│   │   ├── search_tokenize.php      ← Py↔PHP 공통 토크나이저 (단일 진실원)
│   │   ├── search_bm25.php          ← BM25 점수 + 스니펫 (위 둘은 빌드 시 search.php 인라인)
│   │   ├── pagination.js            ← 페이지네이션 (런타임 nav 생성)
│   │   └── imgslidebox.js           ← 이미지 슬라이드 (런타임 nav 생성)
│   ├── admin/                   ← Pond — 로컬 글쓰기 도구 로직 (§ 17)
│   │   ├── render_one.py            ← 단일 글 본문 렌더 (scripts.markdown 재사용)
│   │   ├── slug_one.py              ← 폴더명 → slug (scripts.slugs 재사용)
│   │   ├── lib/                     ← fs · proc · metayaml · articles · i18n (PHP)
│   │   └── views/                   ← layout · list · new · edit · build · deploy (PHP)
│   ├── locales/                 ← (v1.9.0) i18n 문자열 팩 (en 정본 + ko; 로더 = i18n.py / i18n.php)
│   │   └── en/ · ko/                ← admin.yaml · site.yaml · build.yaml · cli.yaml (Surface 2 / 1 / 3 + CLI)
│   │                                  (v1.9.7: --new-locale 로 스캐폴딩 · --check-locale 로 키 패리티 검증)
│   └── tests/                   ← 단위 테스트 (514) + run_diagnostics.py (6 항목)
│
├── dist/                    ← 빌드 산출물 (배포 대상 / 직접 수정 금지)
│
├── Heron.py                 ← 빌드 진입점 (자기 폴더의 system/ 를 sys.path 에 올림)
├── Pond.php                 ← 로컬 글쓰기 진입점 (얇은 라우터 — § 17, dist 미포함)
├── README.md                ← 영문 문서
└── README.ko.md             ← 이 문서 (국문)

빌드/운영 시 자동 생성 (.gitignore 권장):
  build-report.md          ← 진행 트랜스크립트 + 요약 + 보완 항목 + 단계별 timing (dist/ 밖)
  .build_cache/            ← 글 단위 증분 캐시 + tokenizer parity 캐시
  user/.heron/update.json  ← (v1.6.0) 업데이트 체크 캐시 (스탬프 version 은 커밋, 캐시·백업은 제외)
  user/.heron/backups/     ← (v1.6.0) 마이그레이션/업데이트 직전 스냅샷
  user/.heron/deploy.json  ← (v1.7.0) 실제 배포 설정 (견본 deploy.example.json 은 커밋)
  system/runtime/bin/      ← (v1.7.0) 다운로드된 rclone 바이너리 (<os>-<arch>/; MANIFEST 표면 제외)
```

> **`dist/assets/` 는 어디서 오나** — `user/styles/*.css` + `user/branding/*` + `system/runtime/*.js` 세 곳을 빌더가 `dist/assets/` 한 곳으로 모은다 (`/assets/{경로}` URL 은 v1.4.x 와 불변). `system/runtime/*.php` 는 서브타임 코드라 `dist/search.php` 로 따로 인라인된다.

> **중요:** `dist/` 안의 파일은 매 빌드마다 덮어씌워집니다. 수정은 `user/` 안 (`articles/`·`site.yaml`·`templates/`·`styles/`·`branding/`) 에서 하고 다시 빌드하세요. `system/` 은 프로그램이라 사이트 운영에는 건드릴 일이 없습니다.

---

## 4. 글 작성하기

### 4-1. 글 폴더 만들기

`user/articles/` 안의 카테고리 폴더 아래에 새 폴더를 만들고 `meta.yaml` + `content.md`(또는 `content.html`) 를 둡니다.

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

파서는 [system/scripts/parsedown.py](system/scripts/parsedown.py) (Parsedown 1.7.4 Python 포팅). 표준 CommonMark 에 가까운 문법 + 이 시스템 전용 문법 (§ 9).

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

> **갭+섹션은 직접 작성.** content.html 은 작성한 HTML 이 **그대로** 들어갑니다 — 마크다운의 자동 wrap·섹션 마커가 작동하지 않습니다. 예: [user/articles/About/content.html](user/articles/About/content.html).

> **content.md / content.html 동시 존재 금지** (빌드 중단).

**PHP 함수 자동 변환** — 두 함수를 HTML 로 변환:

```html
<?php imgBox("./imgs/p.jpg", "캡션", "alt") ?>
  → <figure class="imgBox"><img src="/my-slug/imgs/p.jpg" alt="alt"><figcaption><small>캡션</small></figcaption></figure>

<?php imgSlideBox("./src_slide") ?>
  → src_slide/ 안 이미지를 알파벳 순 슬라이드로 (하단 중앙 dot 인디케이터, JS 런타임 생성)
```

다중 구문 `<?php … imgBox(); imgBox(); … ?>` 블록도 imgBox/imgSlideBox 만 들어 있고 그 외 살아있는 구문이 없으면 통째로 정적 HTML 로 시뮬레이션 (주석·`global` 선언·`;` 무시). 다른 함수 호출이 섞여 있으면 블록 원문 보존 → 글이 `.php` 확장자로 출력 (§ 8 PHP 자동 감지).

캡션 안의 `{$name}` 은 `site.yaml` 의 `php_globals` 로 빌드 시 치환 (§ 11). 캡션은 raw HTML 보존 (`<br>`·`&nbsp;`·`<a>` 사용 가능), `alt` 는 속성값이라 이스케이프.

### 4-5. 자산 첨부

- **글 단위 자산** — 글 폴더 안에 둡니다. `meta.yaml`/`content.*` 와 `_`·`.` 접두 항목을 제외한 모든 파일·폴더가 `dist/{slug}/` 로 복사 (URL `/{slug}/imgs/…`). `_`·`.` 접두 파일/하위폴더는 비공개로 보고 복사하지 않습니다 (§ 6).
- **사이트 전역 자산** — 공유 CSS 는 `user/styles/`, 파비콘/로고/기본 OG 이미지는 `user/branding/`, 런타임 JS 는 `system/runtime/` 에. 셋 다 `dist/assets/` 로 모여 `/assets/{경로}` 로 로드.

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

### 4-7. 예시 콘텐츠 (이 저장소에 동봉)

`user/articles/` 에는 작고 **그대로 빌드되는** 데모 사이트가 들어 있다. 실행 가능한 문서를 겸한다 — 각 예시가 서로 다른 기능을 시연하므로, 갓 clone 한 상태에서 `python Heron.py` 만 돌려도 브라우저로 읽을 수 있는 사이트가 나온다. 자기 사이트를 시작할 때 폴더째 지우면 된다 (레퍼런스로 남겨도 좋다).

| 예시 글 (폴더) | URL | 시연하는 기능 |
|---|---|---|
| `About` | `/about/` | `content.html` 본문 · `imgBox()` PHP 시뮬레이션 · `php_globals` 의 `{$site_credit}` 보간 |
| `Blog/Welcome to Heron` | `/welcome-to-heron/` | 기본 마크다운 · 섹션 마커(`===t===` / `======`) · 이미지 박스 `![[alt]](경로){캡션}` · 정렬 표 · `og_image` |
| `Blog/Markdown Syntax Reference` | `/markdown-syntax/` | 마크다운 총정리 — ATX·Setext 제목, 참조 링크, 중첩 리스트, 3중 인용, 펜스 코드 |
| `Blog/Per-Article Styling` | `/per-article-styling/` | `styles` 두 채널: 외부 CSS(정수 키) + 인라인 규칙(문자열 키), 로드 순서대로 |
| `Blog/Internationalization` | `/i18n/` | 글 단위 `lang:` 오버라이드 + `updated:` 수정일 |
| `Blog/Tutorials/Working with Images` | `/working-with-images/` | **서브카테고리** · `imgBox()` + `imgSlideBox()` · raster → 다중 해상도 WebP `srcset` |
| `Gallery/*` (Sunset · Mountains · Ocean) | `/gallery-*/` | 카테고리 `layout: gallery` (이미지 타일) |
| `Notes/Scratchpad` | `/scratchpad/` | `noindex: true` (sitemap/검색/피드 제외) + `seo.description` 면제 |
| `Notes/Landing Page` | `/landing/` | `use_common_css: false` 자기완결형 페이지 |
| `Lab/Dynamic Year` | `/dynamic-year/` | 살아있는 `<?php … ?>` 가 남아 `index.php` 로 출력 ("PHP 빌드 글" 로 보고) |

카테고리(`Blog`·`Gallery`·`Notes`·`Lab`) 자체는 `nav_priority`·`priority`·`layout`·`preview_per_page` 를 보여준다. 이 세트를 클린 빌드하면 **보완 0 / 살펴볼 사항 0 / PHP 빌드 1건**(Dynamic Year, 의도)으로 보고된다.

---

## 5. 카테고리

`user/articles/` 아래 폴더 구조가 그대로 카테고리. 별도 설정 없이 **폴더 = 카테고리**. 빌더는 `content.md`/`content.html` 유무로 글 폴더와 카테고리 폴더를 구분 (둘 다 없으면 카테고리).

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
| `template` | `category.html` | `name.html`→`user/templates/`, `./name.html`→폴더 |
| `lang` | site `lang` | `<html lang>` 오버라이드 |
| `title` | 폴더명 | 인덱스 `<title>` 본문 |
| `seo` | {} | 글 `seo:` 와 동일 (메타 태그 출력) |
| `priority` | `0` | 상위 인덱스 내 형제 section 정렬 (큰 값 먼저) |
| `nav_priority` | `0` | 톱레벨 nav 정렬 (priority 와 별개 축) |

**`layout: gallery`** — 글 목록을 이미지 타일로 (CSS Grid `auto-fill, minmax(220px,1fr)`, 4:3 크롭, subtle hover, 모바일 2열). 썸네일: `seo.og_image` → `site.default_og_image` → 빈 플레이스홀더. WebP srcset 자동 부착.

추가 layout 이 필요하면 [system/scripts/builder.py](system/scripts/builder.py) 의 `_listup_items_html`/`_render_section` 분기 + [user/styles/common_template.css](user/styles/common_template.css) 의 `section.listup-{layout}` + pagination.js selector 에 직접 등록.

---

## 6. 글 관리 — 비공개·이동·삭제

- **비공개** — 파일/폴더명 앞에 `_` 또는 `.`. 경로의 어느 세그먼트든 `_`·`.` 접두면 그 아래 전체가 글·카테고리·nav·자산에서 모두 제외. 빌드 시 `dist/{slug}/` 자동 삭제. `_` = 의도적 비공개·편집 중, `.` = OS/VCS 숨김(`.git`·`.DS_Store`) **그리고** `.draft` 처럼 작성자가 "숨겼다" 고 믿는 폴더가 실수로 공개되는 길을 막음.
- **이동** — 글 폴더를 다른 카테고리로 옮겨도 `slug` 가 같으면 URL 불변.
- **삭제** — 글 폴더 삭제 후 빌드하면 `dist/{slug}/` 자동 정리 (고아 정리).

위 작업을 파일 탐색기 대신 브라우저로 하려면 [§ 17 Pond.php](#17-로컬-글쓰기--pondphp). 같은 규약을 그대로 따른다 (이동=폴더 rename·slug 불변, 비공개=`_` 접두, 삭제=`.trash` 이동으로 빌드 자동 제외·복구 가능).

---

## 7. 빌드

```bash
python Heron.py            # 일반 빌드 (증분 캐시)
python Heron.py --clean    # dist/ + .build_cache/ 폐기 후 빌드
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

**위 경우 (시스템 결함):** 템플릿 누락 / `user/articles/` 디렉터리 없음 / `site.yaml` 부재·파싱 실패 / `images.enabled: true` 인데 Pillow 미설치 — *단 변환할 raster 이미지가 실제로 존재할 때만* 중단 (raster 가 한 장도 없으면 워닝 후 빌드 통과).

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
| 홈 | `/` | `https://your-domain.com/` |
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
![[이미지 설명]](./imgs/p.jpg) {캡션}   → <figure class="imgBox"><img …><figcaption><small>캡션</small></figcaption></figure>
```

캡션이 필요 없으면 `{...}` 생략. 이미지 박스 문법은 빌드 직전 raw HTML 로 변환 후 파서로 전달.

---

## 10. SEO 설정

글/홈/카테고리가 같은 폴백 체인을 공유 (한 함수 [`build_meta_tags`](system/scripts/seo.py)). 본문 title: 글=`meta.title`, 홈=`user/articles/meta.yaml title`>`site.name`, 카테고리=`meta.title`>폴더명.

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

**기본 og:image 자산** — `site.default_og_image` 가 가리키는 자산은 raster 여도 빌드가 webp 변환·srcset 등록을 **건너뛰고 원본 그대로** `dist/` 에 낸다 (`_copy_site_assets` 예외). og:image 소비자는 `<img>` 후처리가 아니라 SNS 링크 언퍼ler — `og:image` 메타의 고정 URL 하나만 가져가므로 다중 해상도가 무의미하고, KakaoTalk·일부 Facebook 은 WebP og:image 를 렌더하지 못한다. 기본 자산은 `user/branding/default-og.png` (1200×630, 표준 OG 규격). `default_og_image` 가 외부 URL 이거나 자산 소스 폴더(`user/styles`·`user/branding`·`system/runtime`) 밖이면 이 예외는 무동작 (파일 배치는 작성자 책임).

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
| `user/articles/meta.yaml` | 홈 전용 — `per_page` `excludes_categories` `lang` `layout` `styles` `title` `seo:` |
| `user/articles/<cat>/meta.yaml` | 카테고리 전용 (§ 5 표) |
| `user/articles/<cat>/<글>/meta.yaml` | 글 전용 (§ 4-2) |

> **v1.4.0 폐기** — `reserved_slugs` · `warn_on_underscore_ref` · `warn_on_missing_asset` · `error_404_title` · `search_title` 다섯 키는 코드 상수로 승격됐다 (`system/scripts/builder.py`의 `RESERVED_SLUGS` / `DEFAULT_ERROR_404_TITLE` / `DEFAULT_SEARCH_TITLE`, 그리고 항상-경고 행동 고정 + dead config 정리). 옛 site.yaml 에 키가 남아 있어도 파서가 silently 무시한다.

```yaml
domain: your-domain.com
base_url: https://your-domain.com
name: Heron Demo
main_title: Heron Demo
default_author: Your Name
default_og_image: /assets/default-og.png
lang: ko                              # 모든 페이지 <html lang> 디폴트
default_title_prefix: ""              # 모든 페이지 <title> prefix/suffix
default_title_suffix: ""
copyright_holder: Your Name
copyright_year_start: 2025
category_per_page: 20                 # 카테고리 페이지네이션 디폴트
category_preview_per_page: 5
description_truncate: 150             # 피드 summary 절단 최대 글자 (단어 경계 존중)
robots_txt_main: |
  User-agent: *
  Allow: /

  Sitemap: https://your-domain.com/sitemap.xml
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
  site_credit: "Illustrations by the Heron Demo team"
#   원본 PHP 서버의 PHP/GlobalVariables.php(auto_prepend) 가 런타임에
#   채우던 서명 변수. 정적 빌드엔 그 런타임이 없으므로 여기 옮겨 적으면
#   글 본문 imgBox 캡션 안의 {$site_credit} 등을 빌드 시 치환한다
#   (미정의 변수 = 빈 문자열, PHP 미정의 echo 동등). 변수명 앞 $ 는 생략.
google_adsense:                       # Google AdSense (기본 비활성)
  ads_txt: ""                         #   예: google.com, pub-0000000000000000, DIRECT, 0000000000000000
  head_script: ""                     #   예: <script async src="…adsbygoogle.js?client=ca-pub-0000…"></script>
  exclude_urls: []                    #   비주입할 URL / [] 면 (활성 시) 5 페이지 전체 주입
#   ads_txt 는 dist/ads.txt 로 그대로 기록 (robots.txt 와 같은 패턴);
#   head_script 는 5 템플릿 (article·home·category·404·search.php) <head>
#   에 raw 그대로 주입 (escape 없음). 둘 다 빈 문자열/키 부재 시 자동 비활성
#   — SeoMeta 의 3-state 원칙 일관이며 별도 enabled 마스터 토글 없음.
#   Pond.php·system/admin/ 은 빌더가 user/articles/ 만 스캔하므로 자연 제외.
#   exclude_urls: site-relative 절대 URL ('/' 로 시작) 리스트. 매칭된
#   URL 의 페이지 head 에 로더 스크립트가 들어가지 않음 = Google auto-ads JS
#   미로드 = 광고 원천 차단. 매칭은 case-sensitive · trailing-slash 포함 정확
#   일치 — canonical URL 형식: 홈=/, 글=/<slug>/, 카테고리=/<slug_path>/,
#   404=/404.html, 검색=/search.php. 매칭 안 되는 entry (오타·삭제된 글) 는
#   build-report.md "살펴볼 사항" 으로 자동 보고. 글 단위 차단도 가능 (예: /about/).
```

**user/articles/meta.yaml** (홈 전용, 선택 — 없으면 `per_page=10`, `excludes_categories=[]`):

```yaml
per_page: 5                  # 메인 Recent posts 페이지당 글 수
excludes_categories: [About] # Recent 에서 제외할 톱레벨 (About 등)
layout: list                 # list / gallery
# lang: ko
# styles: { 1: home.css, p: { line-height: 1.7em } }
# use_common_css: true
# template: my_landing.html   # user/templates/ 또는 ./ (홈 폴더) 안
```

> 카테고리 meta.yaml 과 같은 스키마를 공유 — 홈에서 `preview_per_page`/`priority` 는 임베드 대상이 없어 무시 (의도된 비대칭).

---

## 12. 내부 구현 — 파서 / 검색 / 피드

### 마크다운 파서 — Parsedown 1.7.4 Python 포팅

단일 구현 [system/scripts/parsedown.py](system/scripts/parsedown.py) 만 사용.

```
content.md → preprocess (![[...]]{...} → HTML) → Parsedown().text()
           → finalize (asset 경로 재작성, PHP 시뮬레이션) → RenderResult(html)
```

- 원본: [Parsedown](http://parsedown.org) 1.7.4 (c) Emanuil Rusev, MIT. 포팅은 메서드명·dispatch·dict 키까지 원본과 일대일. 외부 의존성 없음 (stdlib `re`/`typing`).
- PHP Parsedown 과 79/79 fixture 바이트 일치 (합성 46 + 실 글 33).
- **운영 정책 — 포크.** 이 포팅이 단일 진실원. 원본 신버전을 따라가지 않으며 모든 수정은 이 포팅에 직접. PHP 비교 대상(Parsedown.php)은 트리에 동봉하지 않음. [system/tests/test_parsedown.py](system/tests/test_parsedown.py) 는 Python 포트 회귀 가드 한정.
- PHP↔Python 정규식 차이는 포팅에서 처리 (`\w` `re.ASCII`, `(?R)` 수동 bracket matcher, possessive → `+`/`*`, single quote `&#039;`).

### YAML 파서 — 의도된 부분집합

site.yaml/meta.yaml 파서는 자체 구현 ([system/scripts/yaml_parser.py](system/scripts/yaml_parser.py)). *실제 사용하는 문법의 부분집합* 만.

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
- **토크나이저** — 영문/숫자 = 단어 단위 소문자 (정확 매치), 한글 = 음절 2-gram (부분 검색 자연 지원), **1글자 한국어 제외**. [system/scripts/search.py](system/scripts/search.py) `search_tokenize()` ↔ [system/runtime/search_tokenize.php](system/runtime/search_tokenize.php) 가 단일 진실원, 빌드마다 18 fixture 패리티 자동 검증 (PHP 없으면 워닝 후 skip). `.build_cache/parity.json` 에 결과 캐싱 (키 = `sha256(search.py + search_tokenize.php + php -v)`), `--no-cache` 시 매 빌드 풀 검증.
- **점수** — 필드별 Okapi BM25 (`IDF·tf(k1+1)/(tf+k1(1-b+b·dl/avgdl))`, Robertson-Spärck Jones IDF). 가중합 w_title=3.0 / w_desc=1.5 / w_tags=2.0. phrase 부스트(곱셈): title ×2.0, desc ×1.5, tags 정확매치 ×2.5. params 가 인덱스에 박혀 점수 결정적. `tests/test_bm25.py` + run_diagnostics 가 Py↔PHP 패리티 검증.
- **보안** — 쿼리 100자 제한, 모든 출력 `htmlspecialchars` escape (강조는 escape 후), 결과 페이지 `noindex,follow`.
- **서버** — PHP 7.4+ + `mbstring`. 추가 확장 불필요.
- **OPcache 전제 (v1.4.0 명문화)** — 본 시스템의 검색은 **OPcache 가 켜진 단일 PHP 파일** 을 전제로 설계됐다. 인덱스가 `search.php` 안의 정적 PHP 배열 리터럴로 인라인되어 첫 요청에만 PHP 가 파싱되고, **OPcache 가 그 바이트코드를 메모리에 상주** 시켜 두 번째 요청부터 디스크 I/O 0 / JSON 파싱 0 / `require_once` 0 으로 답한다. 47 글 인덱스가 메모리에서 처리되므로 한 자릿수 ms 응답이 가능 — 정적 사이트 대비 *체감 즉답* 의 검색 UX 가 이 구조에 직접 기인한다. **클라이언트 JS 로 옮기지 않는다** — 첫 로드에 인덱스 JSON 다운로드(수십 KB) + JS 파싱·실행이 누적되어 사용자 첫 검색 응답이 크게 느려진다 (Cloudflare CDN 캐싱으로도 첫 진입자에겐 무의미). 운영 의존성으로 PHP 7.4+ 가 추가되지만, 그 비용으로 *모든 방문자에게 즉답* 을 보장한다. 호스팅이 OPcache 를 비활성화한 경우 응답 시간이 50~100ms 대로 떨어지지만 여전히 클라이언트-JS 보다 빠르고 정확하다 (인덱스 다운로드 없음).
- **비활성화** — `system/runtime/search.php` 삭제 (경고 후 search.php 미생성) + [user/templates/home.html](user/templates/home.html)·[user/templates/category.html](user/templates/category.html) 의 `<form class='nav-search'>` 제거.

### RSS / Atom 피드

`dist/feed.atom` (Atom 1.0) + `dist/feed.rss` (RSS 2.0) 가 같은 entry 목록. 모델은 [system/scripts/feed.py](system/scripts/feed.py) 의 `FeedDocument`/`FeedEntry`.

- **포함:** non-noindex 글, `excludes_categories` 제외, 최신 N개 (기본 20, `DEFAULT_MAX_ENTRIES`), `updated`(없으면 `date`) 내림차순.
- **entry:** title=`meta.title`, link/id=절대 URL, published=`date`, updated=`updated`, summary/description=`seo.description` (부재 시 누락+issue), author=`seo.author`>`site.default_author` (RSS 는 생략), category=톱레벨 폴더명 + `tags`.
- **자동 발견** — 페이지 `<head>` 에 `<link rel='alternate' type='application/atom+xml'>` / `rss+xml` 삽입.
- **결정성** — `date`/`updated` 는 모두 `00:00:00 UTC`. 피드 `updated`/`lastBuildDate` 도 빌드 시각이 아닌 entry 최신 lastmod → 콘텐츠 변경 없으면 매 빌드 같은 바이트.
- **비활성화** — [system/scripts/builder.py](system/scripts/builder.py) `build()` 의 `self._build_feeds()` 주석 처리 (site.yaml 토글 없음).

### 증분 캐시

글 단위 캐시는 `.build_cache/articles/` 에. 글 입력 (meta.yaml + content.* + 자산 mtime/size + 전역 해시) 가 같으면 hit → 산출물 replay. site.yaml/템플릿/빌더 코드/전역 자산이 바뀌면 전 글 invalidate (전역 해시). 검색/sitemap/feed/홈/카테고리/assets 는 모든 글이 입력이라 매 빌드 재구축 (의도된 범위).

### 이미지 멀티프로세스

raster 변환은 `ProcessPoolExecutor(workers=min(cpu_count, len(jobs)))` 로 fan-out, 워커는 모듈-레벨 자유 함수 `_image_worker` (Windows spawn 도 OK). 결과 처리(`image_variants` 등록·에러 BuildReport 라우팅)는 메인 `_handle_image_result` 헬퍼로. raster_jobs<4 또는 worker≤1 이면 시리얼 폴백 (Windows Pillow import 비용 절약).

---

## 13. 배포

빌드 후 `dist/` 를 서버 DocumentRoot 에 올리고 Apache VirtualHost 를 **한 번** 등록. 이후 글 추가/삭제해도 서버 설정 불변. `.htaccess` 미사용 — 공유 호스팅에서 메인 설정 접근이 안 되면 호스팅 사업자에 등록 요청.

```bash
rsync -avz --delete dist/ user@your-domain.com:/var/www/your-domain.com/
```

```apache
<VirtualHost *:443>
    ServerName your-domain.com
    ServerAlias www.your-domain.com
    DocumentRoot /var/www/your-domain.com         # ← dist/ 내용 배포

    SSLEngine on
    SSLCertificateFile    /etc/letsencrypt/live/your-domain.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/your-domain.com/privkey.pem

    <Directory /var/www/your-domain.com>
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
    ServerName your-domain.com
    ServerAlias www.your-domain.com
    RewriteEngine On
    RewriteRule ^.*$ https://your-domain.com%{REQUEST_URI} [L,R=301]
</VirtualHost>
```

- **빌드 머신**에는 PHP 불필요. PHP CLI 있으면 토크나이저 패리티 자동 검증.
- **배포 서버**는 **PHP 7.4+ + mbstring** 필요 (search.php + `.php` 출력 글). 이것은 한계가 아니라 전제.
- ⚠️ **`Pond.php`·`system/admin/` 은 절대 배포하지 말 것.** 위 `rsync` 는 `dist/` 만 올리므로 자연히 빌드 머신을 벗어나지 않는다 — Pond 은 로컬 전용 단일 사용자 저작 도구다. 추가 방어로 `Pond.php` 는 PHP 내장 서버(`cli-server`)+루프백이 아니면 스스로 403 을 낸다 ([§ 17](#17-로컬-글쓰기--pondphp)). DocumentRoot 는 `dist/` 뿐이라 `.php` 라우터가 그 안에 없기도 하다.

**배포 검증:**

```bash
curl -I https://your-domain.com/                # 200
curl -I https://your-domain.com/hello-world     # 301 → /hello-world/
curl -I https://your-domain.com/hello-world/    # 200
curl -I https://your-domain.com/sitemap.xml     # 200 application/xml
```

### 13-1. Pond 원클릭 배포 (rclone, v1.7.0)

위 `rsync` 는 수동 경로다. v1.7.0 부터 **Pond 상단 [배포]** 가 같은 일을 버튼으로 한다 — rclone 의 SFTP 백엔드로 `dist/` 를 서버에 **증분 동기화**(바뀐 파일만 전송 + 서버에만 남은 고아 파일 삭제). rsync 가 Windows 네이티브가 아닌 문제를 **rclone**(MIT, DLL 0 의 단일 정적 바이너리)으로 푼다 — 핀 버전(v1.74.2)을 처음 한 번 받아 `system/runtime/bin/<os>-<arch>/` 에 두고 다운로드 아카이브 SHA256 을 소스 핀과 대조해 공급망을 차단한다. 바이너리는 머신 종속물이라 커밋·MANIFEST·dist 어디에도 새지 않는다.

- **설정** — `user/.heron/deploy.json` (gitignore): `host`/`user`/`port`/`remote_path`/`ssh_key_path` (+ 선택 `known_hosts_path`). 견본 `deploy.example.json` 을 복사해 채운다. **개인키 자체는 저장소 밖** OS 표준 위치에 두고 deploy.json 엔 *경로만*.
- **2단계 게이트** — ① 미리보기(`--dry-run`)로 “보낼/지울” 목록을 확인한 뒤 ② 적용. `sync` 는 원격을 *삭제*하므로 `remote_path` 오타가 엉뚱한 디렉터리를 비우지 않도록 막는 안전장치다.
- **호스트키 검증** — 최초 1회 `ssh user@host` 로 접속해 `known_hosts` 에 등록(rclone sftp 기본은 미검증이라 강제 = MITM 방어). 서버는 **SFTP 만** 쓰므로 추가 설치 0.
- **첫 전송은 느림** — 전체 자산(~157MB) 첫 동기화는 수 분 걸릴 수 있고, Pond 는 진행 로그를 실시간 스트리밍한다. 이후는 증분이라 빠름.
- CLI: `python Heron.py --fetch-rclone` / `--deploy --dry-run` / `--deploy`. 상세·안전장치는 [§ 17-7](#17-7-배포-rclone-v170).
- 비목표: 다중 타깃(staging/prod)·비밀번호 인증·무중단 원자 교체는 이번 범위 밖(단일 타깃·키파일·in-place). `Pond.php`·`system/` 자체 배포는 절대 금지 — dist 만 올린다.

---

## 14. 트러블슈팅

| 증상 | 원인 / 해결 |
|---|---|
| 빌드 성공인데 CSS 깨짐 | 절대경로(`/assets/...`). 더블클릭 말고 `cd dist && python -m http.server 8000`. |
| PHP 없이 빌드 가능? | 가능 (파서 순수 Python). PHP CLI 없으면 패리티 검증만 워닝 후 skip. 배포 서버는 PHP 필요. |
| styles 가 적용 안 됨 | ① styles·외부 CSS 는 글·홈·카테고리 모두 동일하게 inject — 홈은 `user/articles/meta.yaml`, 카테고리는 그 카테고리 `meta.yaml` 에 작성. ② 템플릿에 `{{PAGE_STYLES}}`/`{{PAGE_STYLESHEETS}}` 있는지. ③ specificity 충돌 → 구체 셀렉터/`!important`. ④ `:hover`/`#id`/`::before` 는 YAML 인용. |
| styles 에 `@media` | 인라인 채널은 평면 규칙만. 글 폴더에 진짜 CSS 파일 + `styles: {1: my.css}`. |
| `slug 충돌` | 같은 slug 두 글. 한쪽 변경. |
| URL 이 `/be94-…/` | 비ASCII 폴더명 → hex 자동 변환. 폴더명을 ASCII 로 (`블로그`→`Blog`). |
| 이미지 안 보임 | 글 폴더 안에 있는지 / `./imgs/p.jpg` 상대경로 / `missing asset` 경고 / `dist/{slug}/imgs/` 복사 확인. |
| `.php` 안 나오고 `.html` | 처리 안 된 `<?php` 가 남아야 `.php`. imgBox/imgSlideBox 는 HTML 변환되므로 `.html`. |
| `dist/` 새로 빌드 | `python Heron.py --clean`. |

---

## 15. 설계 원칙과 한계

**설계 원칙**

1. **URL 영구성** — slug 가 안 바뀌는 한 카테고리 이동·폴더명 변경과 무관하게 영구.
2. **표시명 ↔ URL slug 분리** — 화면=한국어 폴더명, URL=ASCII slug.
3. **운영 의존성 명시** — 빌드 Python 3 + Pillow, 런타임 PHP. "외부 의존성 0" 이 아니라 솔직히 명시 + 끄는 옵션 제공.
4. **서버 ↔ 콘텐츠 분리** — `.htaccess` 없음. 글을 늘려도 서버 설정 불변.
5. **빌드 안전성** — `user/articles/` 를 읽기만. 소스 자동 수정 안 함.
6. **파서 단일화** — Parsedown Python 포팅 하나로 통일.
7. **글 단위 표현 제어** — meta.yaml 에서 선언적으로.
8. **글 단위 색인** — 기본 허용, `noindex: true` 글만 제외.
9. **단일 진실원 토크나이저** — Py/PHP 패리티 빌드마다 자동 검증.
10. **본문 ↔ 메타데이터 분리** — SEO/OG/피드 카피는 본문이 아니라 author 가 `seo:` 블록에 직접 쓴 값에서만. 본문=독자용, 메타=SERP/소셜용 — 다른 글이어야 함. SSG 는 추측하지 않음. `og_image` 부재 시 본문 추출이 아니라 `site.default_og_image`.
11. **`template:` 가로지르기 — 허용하되 알린다** — 페이지 종류와 다른 템플릿 지정 가능. 빌더가 못 채우는 placeholder 는 strip + warning (자동 거부도 silent strip 도 아닌, 알림 + author 판정).
12. **(v1.5.0) user / system 분리** — `user/` 는 네가 소유·편집하는 전부, `system/` 은 프로그램. 표현 표면(템플릿·CSS·정체성 자산)은 빌더 안이 아니라 `user/` 에 산다.
13. **(v1.6.0) 마이그레이션·자가 업데이트 — 빌드는 읽기 전용 유지** — 업그레이드는 프로그램 표면(`system/` + 진입점)만 교체하고 `user/` 는 절대 건드리지 않는다. 기록된 스키마 스탬프(`user/.heron/version`)가 멱등·`user/`-한정 마이그레이션 체인을 구동한다. 빌드 자체는 `user/` 에 쓰지 않으며(원칙 5 무손상), `--migrate`/`--update` 만 writer 이고 그것도 백업 후 쓴다.

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

> changelog 본문의 `scripts/…`·`templates/…`·`assets/…`·`tests/…` 경로는 도입 시점의 역사 기록 — v0.8.1~v1.4.x 는 `src/` 접두였고, v1.5.0 부터 실제 위치는 `system/scripts`·`system/runtime`·`user/templates`·`user/styles`·`user/branding`·`system/tests` 로 갈렸다 (§ 3). `build.py`→`Heron.py`·`admin.php`→`Pond.php` 도 v1.5.0.
> 코드 정합성: **문서 전용 릴리스** = 정본 클린 재빌드 후 dist sha256 == 직전 코드 복사본. **코드 릴리스** = 결정성(2회 빌드 동일) + 직전 코드 릴리스 기준 열거 diff.

| 버전 | 날짜 | 요약 |
|---|---|---|
| **v1.14.4** | 2026-06-09 | **imgBox 캡션을 HTML 표준 시맨틱 마크업으로 — 비표준 `<div>` + `<p><small><b>` 조합을 `<figure class="imgBox">` + `<figcaption><small>` 로 교체했다.** `markdown.py` 의 두 출력부(마크다운형 `![[alt]](url) {캡션}` · 시뮬레이션 PHP `imgBox()`)가 이제 이미지를 `<figure class="imgBox">` 로, 캡션을 `<figcaption><small>…</small></figcaption>` 로 감싼다 — `<figcaption>` 은 HTML 표준상 `<figure>` 의 자식일 때만 유효하므로 컨테이너도 `div`→`figure` 로 함께 올려 표준 유효성을 지킨다. `.imgBox` / `.imgBox img` / `.imgBox small` 규칙은 전부 클래스·자손 선택자라 마이그레이션·user CSS 수정 없이 그대로 적용되고(좌측 여백 유지), 캡션은 `<b>` 제거로 더는 굵지 않다(의도된 변경). 두 출력부가 여전히 byte 동일이라 Pond 미리보기와 빌드가 일치한다; 캡션 있는 imgBox 의 dist HTML 이 그에 맞춰 바뀐다(의도된 변경이라 byte 동일 아님). 스키마 무변경(스탬프 1.14.3 → 1.14.4); MANIFEST 89; 단위 606. |
| v1.14.3 | 2026-06-09 | 문서 한 편만 고쳐도 사이트 전체가 재업로드되던 문제 정정 — 빌더가 이제 `dist/` 텍스트 산출물을 바이트가 실제로 바뀔 때만 쓰고(신설 `_write_text_if_changed()`), 같으면 mtime 을 보존한다. 이전엔 매 빌드가 모든 텍스트 산출물을 무조건 다시 써 mtime 이 갱신됐고, `rclone sync` 기본 비교(modtime+size)가 이를 전부 *수정됨* 으로 잡아 한 글 편집이 사이트 전체 재업로드로 번졌다. 스키마 무변경(스탬프 1.14.2 → 1.14.3); MANIFEST 89; 단위 599 → 606. |
| v1.14.2 | 2026-06-09 | imgBox 캡션 스타일 복원 — `markdown.py` 의 두 출력부(마크다운형 `![[alt]](url) {캡션}` · 시뮬레이션 PHP `imgBox()`)가 이제 캡션을 `<p><small><b>…</b></small></p>` 로 감싸 캡션이 다시 작고 굵게 렌더되고, 기존 `.imgBox small` 규칙이 원래 좌측 여백을 준다. 수정이 user CSS 가 아니라 (self-update 가 오버레이하는) 빌더 `system/` 에 있어 기존 사이트도 다음 빌드에서 마이그레이션·user CSS 수정 없이 적용된다 — 캡션 있는 imgBox 의 dist HTML 이 그에 맞춰 바뀐다(의도된 변경이라 byte 동일 아님). 스키마 무변경(스탬프 1.14.1 → 1.14.2); MANIFEST 88; 단위 599. |
| v1.14.1 | 2026-06-09 | imgBox 파싱 안정화: 마크다운형 `![[alt]](url) {캡션}` 이 URL·alt·캡션 속 `)`·`[`·`]`·`{`·`}` 를 품어도 매치가 끊기지 않고(탭·공백 들여쓰기도 `<pre><code>` 대신 컬럼0 div 로 나옴), 마크다운 캡션을 더는 이스케이프하지 않아 두 형식 산출물이 일치한다. `simulate_php_in_html`/`has_live_php` 가 `<?= imgBox(…) ?>` 와 대문자 `<?PHP …` 를 라이브 PHP 로 인식한다(후자는 이전엔 `.html` 에 평문으로 샜다). Pond 미리보기와 빌드가 이 파서를 공유해 byte 동일하다. 스키마 무변경(스탬프 1.14.0 → 1.14.1); MANIFEST 88; 단위 589 → 599. |
| v1.14.0 | 2026-06-07 | Pond 관리자 목록: 행별 카테고리 드롭다운이 글의 실제 카테고리를 보여주고(현재 부모 `selected`) 값을 바꾸면 즉시 이동한다 — 별도 *이동* 버튼은 사라졌고, confirm 1회·취소 시 `data-cur` 복원·휠 스크롤 가드·서버 no-op 가드를 둔다. 이동 성공 후 목록은 해당 행 경로를 1회 강조(~1.8s)하고 `#moved` 로 스크롤한다. 관리자 UI 한정 — 빌더·dist 산출물은 byte 불변. 스키마 무변경(스탬프 1.13.1 → 1.14.0); MANIFEST 88; 단위 589. |
| v1.13.1 | 2026-06-06 | 배포 미리보기에 다섯 번째 **변경 없음** 카드 추가 — 그대로 두는(전송 안 하는) 파일을 보여줘, 빌드·배포 판단 시 추가/수정/삭제로부터 "안 바뀐 것"을 역산하지 않아도 된다. dry-run 은 *바뀌는* 파일만 출력하므로 '변경 없음'은 로컬 `dist/` 워크에서 (추가 ∪ 수정)을 뺀 나머지로 계산하며 추가 네트워크가 없다; 요약 JSON 은 가산적이고 적용 경로는 byte 불변. 스키마 무변경(스탬프 1.13.0 → 1.13.1); MANIFEST 88; 단위 583 → 589. |
| v1.13.0 | 2026-06-06 | 배포 미리보기: 추가 / 수정 / 삭제 / 경고 클릭형 아코디언 카드(v1.12.0 의 단일 업로드 카드를 분할), 수정 파일은 파일별 unified diff — *diff 보기* 클릭 시 **그 파일 하나만** 새 `Heron.py --deploy-diff`(상대경로 → `rclone cat`, Python `difflib`)로 라이브로 받아 렌더하며, POST+CSRF `?a=deploy_diff` 엔드포인트는 `dist/` 하위 realpath 로 경계 짓고 텍스트 전용·512 KiB·줄 클램프 안전장치를 둔다. 요약 JSON 은 **가산적**(`upload` 유지; `added`/`modified`/`*_files`/`*_more`/`remote_path` 추가)이라 v1.12.0 CLI 한 줄·기존 테스트가 전부 그대로이고, 적용 경로는 byte 불변. 스키마 무변경(스탬프 1.12.0 → 1.13.0); MANIFEST 88; 단위 568 → 583. |
| v1.12.0 | 2026-06-06 | 배포 미리보기: 스트리밍 중 꼬리를 자동 추적하는 접이식 ~10행 라이브 로그 + dry-run 결과 파싱 요약 — 업로드 / 삭제 / 디렉터리 작업 / 경고 카드, 상위 디렉터리별 표, 경고 목록 — 으로 수백 줄 `<pre>` 의 가독성 문제를 해소. 파싱은 `deploy.py` 단일 출처로 **항상** 한 줄 사람용 요약을 내고(CLI 도 이득), Pond 가 `HERON_DEPLOY_SUMMARY=json` 을 줄 때만 RS sentinel 뒤 기계용 JSON 한 줄을 추가로 내보내 `deploy_run.php` 가 가로채 카드·표로 렌더한다. dry-run 전용; 적용 경로는 byte 불변. 스키마 무변경(스탬프 1.11.4 → 1.12.0); MANIFEST 88; 단위 555 → 568. |
| v1.11.4 | 2026-06-06 | rclone 배포 `ssh_alias` 위임 모드 (opt-in) — 패스프레이즈 키·호스트키 미스매치 배포 실패 정정: 값이 있으면 `build_argv` 가 host/user/port/key/known_hosts 플래그를 버리고 `--sftp-ssh "ssh <alias>"` + `--sftp-disable-hashcheck` 만 내보내, 인증·호스트키 검증을 시스템 ssh(`~/.ssh/config`·Keychain·ssh-agent·`known_hosts`)에 위임한다. **완전 하위호환** — `ssh_alias` 가 없으면 키파일 경로는 byte 불변(Windows 기본 무변경; alias 모드는 macOS/Linux opt-in). 또 (릴리스 도구): `make_manifest` 가 `.DS_Store`/`Thumbs.db` 를 어느 깊이서든 제외 — 매니페스트 재생성 시 타 플랫폼 `--check` 가 `missing` 으로 보던 유령 항목이 안 낀다. 스키마 무변경(스탬프 1.11.3 → 1.11.4); MANIFEST 88; 단위 546 → 555. |
| v1.11.3 | 2026-06-04 | 글 끝 발행/수정 메타 라벨("발행"/"수정")을 사이트 언어로 현지화 — 한국어 하드코딩이라 v1.9.x 스윕에서 누락돼 `lang=en` 빌드에서도 그 푸터만 한국어로 새던 드리프트를 정정. `self.site_tr` 로 라우팅하고 신설 `site.article.published`/`updated` 키 추가; `lang=ko` 출력은 byte 불변. |
| v1.11.2 | 2026-06-04 | rclone PATH 폴백 무결성 경고 (보안 백로그 B3). 핀 바이너리 실패로 PATH 의 rclone 으로 폴백할 때 그 바이너리가 **미검증** 임을 명시하도록 메시지 강화(다운로드 sha256 불일치는 여전히 즉시 중단). 메시지 전용. |
| v1.11.1 | 2026-06-04 | 자가업데이트 공급망 강건화 (B1·B2) — 다운로드 트리에 `system/MANIFEST.json` 이 없으면 `self_update` 가 즉시 중단하고, 신설 `_trusted_zipball()` 이 GitHub `zipball_url` 을 `lamaBread/heron-press` 출처로 고정. |
| v1.11.0 | 2026-06-04 | 보안 감사 라운드 — 4개 도메인 점검에서 확인된 결함만 정정: 검색 스니펫 이중 인코딩 해소(`html.unescape`), Pond 공개/비공개 토글이 언더스코어 한 개만 제거, `highlight_html` 의 PCRE-null 500 방어, `admin_safe_rel` 의 NUL 바이트 거부. by-design·공급망 항목은 백로그로 분리. |
| v1.10.0 | 2026-06-04 | 배포 핫픽스 — `build_argv` 가 rclone 에 없는 플래그 `--sftp-known-hosts` 를 넘겨 모든 배포가 즉사하던 것을 `--sftp-known-hosts-file` 로 교정. 내보내는 모든 플래그를 실제 rclone `help flags` 와 대조하는 재발 가드 신설. |
| v1.9.7 | 2026-06-03 | 도구·사이트 기본 언어 한국어→영어 전환 (v1.9.x 언어팩 라인) — i18n 정본/기본/폴백을 `ko`→`en` 으로(기존 설치는 선택 유지, Pond ▸ 설정에서 변경), 방문자 사이트 `lang` 기본도 신규 클론/데모에 한해 전환. 신설 `--check-locale`(패리티 CI 게이트)·`--new-locale`(스캐폴딩). |
| v1.9.6 | 2026-06-03 | 마지막으로 한국어 주석이 남아 있던 `user/site.yaml` 주석만 영문으로 통일; 설정값·구조·키 순서·인코딩 불변, 로케일 팩은 미변경. |
| v1.9.5 | 2026-06-03 | `ko` 로케일 팩 적정화 — 정착 기술용어를 영문으로 통일(캐시 hit/miss·raster·Actions 컬럼)하고 Pond 403 SAPI/루프백 가드를 영문화; 작성자 대면 issue/warning 본문은 한국어 유지. |
| v1.9.4 | 2026-06-02 | 글 단위 콘텐츠-결함 `_issue`/`_warning` 본문(builder 29곳)과 이미지 인코딩-실패 메시지를 `build.issue.*` / `build.label.*` / `build.warn.*` 로 현지화. |
| v1.9.3 | 2026-06-02 | argparse `--help`(description·epilog·옵션 help → `cli.help.*`)와 잔여 `images.*` 검증 abort·패리티-실패 메시지(→ `build.abort.*` / `build.parity.*`)를 현지화. |
| v1.9.2 | 2026-06-02 | 빌드 콘솔과 `build-report.md` 전체(16단계 진행·마일스톤·라이브 카운터·`[search]` 라인·리포트 표)를 현지화 — 도구=`en` 빌드 패널은 완전 영문, `ko` 는 byte-동일. |
| v1.9.1 | 2026-06-02 | 언어팩 안정화 — PHP/Python 로케일 로더를 바이트 동일 단일 파서로 통일(escape 처리, v1.9.0 렌더링 버그 둘 수정)하고, 신설 `cli.yaml` 로 배포/업데이트/마이그레이션/CLI 운영자 출력을 팩에 편입. |
| v1.9.0 | 2026-06-01 | 도구 다국어 — 한국어 기반 도구를 `system/locales/<locale>/*.yaml` 로 현지화. 빌드 시점의 *사이트 언어*(`site.yaml: lang`)와 런타임 *도구 언어*(`user/.heron/locale`, 설정 드롭다운) 두 선택자를 두고, `ko` 정본 겸 폴백 + `en` 동봉; `ko` 출력은 v1.8.0 과 byte-동일. |
| v1.8.0 | 2026-06-01 | Pond **설정**(`?a=settings`) + 시스템 개요 **홈**(`?a=home`) — `deploy.json` 구조화 폼과 `site.yaml` 원문 편집기(저장 시 `Heron.py --check-config` 검증·백업), Pond 브랜드가 파이프라인 시각화 홈으로 링크(글 목록은 `?a=list`). dist byte-동일 to v1.7.0. |
| v1.7.2 | 2026-06-01 | 핫픽스 — 자가 업데이트 후 캐시 미갱신으로 "업데이트 가능" 배너가 잔존하던 것을, 오버레이 직후 새 버전 상태로 갱신해 수정하고 `list.php` 의 `vv` 중복 표시도 제거. |
| v1.7.1 | 2026-06-01 | 핫픽스 — 자가 업데이트 백업이 스키마 스탬프 복사 시 목적지 부모 디렉터리를 안 만들어 `FileNotFoundError` 로 죽던 것을 `_backup_program` 에서 수정(`test_full_flow` 가 분기 커버). |
| v1.7.0 | 2026-06-01 | rclone 원클릭 dist 배포(§ 13-1 · § 17-7) — Pond **[배포]** 가 빌드된 `dist/` 를 rclone(SFTP)로 서버에 증분 동기화(2단계 dry-run 게이트로 원격 삭제 방어). 핀 rclone(v1.74.2)을 온디맨드로 받아 SHA256 검증, 인증은 `known_hosts` 검증을 강제하는 SSH 키파일(gitignore 된 `user/.heron/deploy.json` 설정). dist byte-동일 to v1.6.2. |
| v1.6.2 | 2026-06-01 | 이중언어 README 동등화 — 영문을 한국어 깊이로 맞추고(축약 디스클레이머 제거, § 4-7·§ 18 복원, § 3·10·11·12·13·15·17 확장), 한국어도 changelog 압축·설계원칙 13개 정렬. 문서 전용(코드 무변경); 스탬프 1.6.1 → 1.6.2; dist byte-동일 (57파일). |
| v1.6.1 | 2026-06-01 | 마이그레이션 충실도 수정(실제 v1.2.2 `site.yaml` 재현으로 발견) — 이제 개행(LF/CRLF)을 bytes 읽기/쓰기로 그대로 보존하고, 변형 전 모든 위험 파일을 스냅샷 백업한다. 스키마 변경 없음; 스탬프 1.6.0 → 1.6.1 전진. dist 무변경(57파일); 단위 464 + 진단 6/6. |
| v1.6.0 | 2026-05-31 | 마이그레이션 · 원클릭 업데이트 시스템 (§ 17-6) — 스키마 버전 스탬프(`user/.heron/version`) + `user/`-한정 멱등 마이그레이션 엔진 + `MANIFEST.json` 무결성 + Pond/CLI 원클릭 GitHub 업데이트. 빌드는 `user/` 읽기 전용 유지, dist byte-동일 to v1.5.3 (57파일). |
| v1.5.3 | 2026-05-30 | 데모 콘텐츠 레이아웃 수정 — 예시 `content.html` 3건이 HTML 본문이 직접 넣어야 하는 `<div class='gap'>` + `<section>` 래퍼를 빠뜨려(§ 4-4) 스타일 없이 렌더되던 것을 `.md` 글 구조와 동일하게 감쌌다. 엔진 무변경; dist 결정적(57파일). |
| v1.5.2 | 2026-05-30 | 데모 콘텐츠 + 중립 기본값 — `user/articles/` 에 모든 기능을 시연하는 바로 빌드되는 예시 세트 동봉; 사이트 식별 정보 중립화(`your-domain.com` / `Your Name`), AdSense 기본 비활성; 중립 `default-og.png`; `.gitignore` 를 좁혀 `user/articles/` 추적. |
| v1.5.1 | 2026-05-30 | v1.5.0 안정화 리팩터링(코드 릴리스, dist byte-동일) — import 정리, 모듈 경계 캡슐화(`images.split_url`/`build_srcset` 공개), DRY(`_seo_from_dict`/`_int_meta_field`), 사문 제거, stale 명칭 정정. dist 787파일 sha256 == v1.5.0. |
| v1.5.0 | 2026-05-29 | 루트를 `user/`(편집 대상)·`system/`(프로그램)으로 분리하고 진입점을 `Heron.py`·`Pond.php`로 명명한 구조 릴리스. 순수 소스 레이아웃 변경이라 dist 는 v1.4.2 와 byte-동일. |
| v1.4.1 | 2026-05-28 | v1.4.0 내부 링크 검증 정규식(`\bhref=`→`\s+href=`) 결함 수정 — `data-href` 오매칭 제거. dist byte-불변. |
| v1.4.0 | 2026-05-28 | 여섯 묶음 — 이전/다음 글 nav, 글 끝 발행/수정 메타 줄, 다크 모드, 내부 링크 검증, site.yaml 5키 코드 상수 승격, BuildReport "PHP 빌드 글" 분류. |
| v1.3.0 | 2026-05-28 | 빌드 속도 향상 — 단계별 timing, 이미지 멀티프로세스, 자산 패스 통합, tokenizer parity 캐시. dist byte-불변. |
| v1.2.2 | 2026-05-21 | `yaml_parser` multi-line inline list 지원 (`[`~`]` 후속 줄 누적 파싱). dist 동일. |
| v1.2.1 | 2026-05-21 | 운영 잡음 정리 — `noindex: true` 글의 `seo.description` 필수 검사 면제, `warn_on_stale_updated` 워닝 폐기. dist byte-불변. 단위 364→**367** · 진단 6/6 승계. |
| v1.2.0 | 2026-05-21 | v1.1.5 문서 안정화. dist 동일. |
| v1.1.5 | 2026-05-20 | AdSense URL 기반 광고 차단 — `exclude_urls` 가 사이트 내 임의 URL 목록(정확 일치, 개별 글 차단 가능). 빈 리스트=전체 주입. v1.1.4 의 `exclude_pages` 폐기. 단위/진단 승계. |
| v1.1.4 | 2026-05-20 | AdSense 페이지 타입 제외 (`exclude_pages: [article/home/category/404/search]`). v1.1.5 에서 URL 기반으로 통합. |
| v1.1.3 | 2026-05-20 | Google AdSense 통합 (`google_adsense.ads_txt`·`head_script`) + 기본 `default-og.png` 1200×630 표준 OG 규격으로 교체. |
| v1.1.2 | 2026-05-20 | imgSlideBox 배포 사고 수정 + 페이지네이션형 재디자인 — 누락 CSS `.slide{display:none}` 복구 + 하단 중앙 dot 인디케이터 (런타임 JS 생성, 정적 HTML 불변). |
| v1.1.1 | 2026-05-20 | imgBox 배포 사고 수정 — 다중 구문 PHP 블록의 시뮬레이트 실패로 원본 PHP leak. `simulate_php_in_html` 블록 스캐너 재작성 + `site.yaml php_globals` 신설 + 캡션 raw 보존. 단위 313→**337**. |
| v1.1.0 | 2026-05-19 | 로컬 글쓰기 `admin.php` 추가 — `build.py` 패턴 미러, 작성/수정·이동·비공개·삭제·미리보기·원클릭 빌드. dist byte-불변 (admin 은 빌드 앞단). 단위 313→**317** ([§ 17](#17-로컬-글쓰기--pondphp)). |
| v1.0.2 | 2026-05-19 | 홈 기본 출력 개수 디폴트 5→10 (정본 `articles/meta.yaml` 가 `per_page: 10` 명시라 dist 영향 0). |
| v1.0.1 | 2026-05-19 | 소분류 헤더 링크화 — 화살표 폐지, 소분류명 자체가 자기 페이지 링크 (`color: inherit; text-decoration: none`). |
| v1.0.0 | 2026-05-19 | 첫 정식 릴리스 — 기본 og:image 자산 패스스루 (raster 보존), `articles/About` noindex. |
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
| v0.4.6 | 2026-05-14 | 페이지네이션 FOUC 제거 + `articles/meta.yaml` + `priority` + 설정 일원화. |
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

## 17. 로컬 글쓰기 — Pond.php

글 작성·수정·카테고리 이동·비공개·삭제와 **실시간 본문 미리보기**·**원클릭 빌드**를 파일 탐색기 대신 브라우저로 하는 **로컬 전용 단일 사용자** 도구 **Pond**. `Heron.py` 패턴을 그대로 미러한다 — 버전 폴더 루트의 얇은 진입점 `Pond.php` + 로직 일체 `system/admin/`. 빌더는 `user/articles/` 만 스캔하므로 이 둘은 **`dist/` 에 새지 않고** 빌드 결정성·산출물과 무관하다 (Pond 은 빌드 *앞단* 의 저작 도구 — `user/articles/` 를 쓰고, `Heron.py` 는 여전히 읽기만: 설계 원칙 5 무손상).

### 17-1. 실행

버전 폴더에서:

```bash
php -S 127.0.0.1:8001 Pond.php
```

브라우저로 `http://127.0.0.1:8001/`. 빌드 머신 기준 **PHP 7.4+** (개발은 8.x 권장) + **Python 3** (미리보기·slug·빌드가 실제 `scripts.*` 를 부른다). 종료는 터미널 `Ctrl+C`.

### 17-2. 보안 — 절대 공개 서버에 두지 말 것

로컬 단일 사용자 전제. 다층 가드:

- **SAPI+루프백 가드** — `Pond.php` 는 PHP 내장 서버(`cli-server`) + `127.0.0.1`/`::1` 이 아니면 스스로 **403**. Apache `mod_php`/`php-fpm` 에 얹혀도 열리지 않는다.
- **배포 비포함** — § 13 의 `rsync` 는 `dist/` 만 올린다. `Pond.php`·`system/admin/` 은 빌드 머신을 떠나지 않으며, DocumentRoot 도 `dist/` 라 라우터가 그 안에 없다.
- **CSRF** — 상태 변경(저장/생성/이동/삭제/빌드)은 세션 토큰 검증. 인증은 두지 않는다 (로컬 단일 사용자라 불필요 — 한계로 § 15 ⓐ 명시).

### 17-3. 기능

- **홈** (`/`, v1.8.0) — Heron+Pond 전체 흐름(작성→빌드→`dist/`→배포→서빙)을 시각화한 시스템 개요. 좌상단 브랜드 **Pond admin** 클릭 시 도착하는 기본 화면(설치 버전 배지 포함). 글 수·카테고리 수·`deploy.json`/`site.yaml` 상태 + 주요 화면 바로가기.
- **목록** (`?a=list`) — 글 트리. 각 글: 편집 · 카테고리 이동(드롭다운) · 공개/비공개 토글 · 삭제. `.trash` 내용도 표시.
- **새 글** (`?a=new`) — 카테고리 선택 + 폴더명(한국어 가능) → `slug_one.py` 가 빌드와 **같은** 규칙으로 slug 자동 제안(비ASCII면 hex 경고). 폴더 + `content.md`(또는 `.html`) + `meta.yaml`(정본 헤더 주석 포함) 생성.
- **편집** (`?a=edit&id=…`) — **2분할**: 좌=본문(`content.md`/`.html`, frontmatter 금지 — 본문↔메타 분리 원칙), 우=메타 폼 + 접이식 **raw `meta.yaml`** + 실시간 미리보기. 핵심 입력칸(title·slug·date·updated·tags·`seo.description`·noindex)은 *보조* — 바꾸면 raw YAML 을 패치한다. **저장은 raw `meta.yaml` 기준**(주석·고급 키·`styles` 보존), 서버는 헤더 주석 한 줄만 보장. 즉 raw 가 진실원.
- **이동** — 폴더 rename. `slug` 불변이라 **URL 영구**(설계 원칙 1). **비공개** — 폴더명 `_` 접두 토글. **삭제** — `user/articles/.trash/` 로 이동: `.` 접두라 빌드 자동 제외, 파일은 남아 복구 가능(영구 삭제 UI 는 의도적으로 두지 않음 — 복구는 파일 탐색기에서 `.trash` 밖으로).
- **원클릭 빌드** — 상단 버튼이 `python Heron.py`(`--clean` 체크 가능)를 버전 폴더 cwd 로 실행하고 출력을 표시. 사이트(`dist/`)에 반영하는 단계.
- **업데이트 확인 / 원클릭 업데이트** (v1.6.0) — 헤더 **업데이트 확인** 이 GitHub 최신 태그를 조회하고, 새 버전이 있으면 목록 배너의 **지금 업데이트** 가 다운로드→검증→오버레이→마이그레이션을 수행한 뒤 재시작을 안내한다 (§ 17-6).
- **배포** (v1.7.0) — 헤더/네비의 **배포** 가 빌드된 `dist/` 를 서버에 rclone(SFTP) 증분 동기화한다. ① 미리보기(dry-run)로 보낼·지울 목록 확인 → ② 적용의 2단계, 진행 로그 실시간 스트리밍 (§ 17-7).
- **설정** (v1.8.0) — 헤더/네비의 **설정** 이 ① 배포 대상(`deploy.json`) 폼 + ② 사이트 전역(`site.yaml`) 원문 편집을 한 화면에서 다룬다. site.yaml 은 저장 시 빌드와 동일 검증을 통과해야 기록된다 (§ 17-8).

### 17-4. 미리보기 = 본문 충실도 (파서 단일화)

별도 마크다운 엔진을 두지 않는다. `system/admin/render_one.py` 가 빌더가 글 본문을 만들 때 쓰는 **그 `scripts.markdown` 경로**를 그대로 재사용 — `.md` 는 `resolve_section_markers(render_article_md(…))`, `.html` 은 `process_html(…)` 로 빌더 `_render_articles` 와 1:1 동일. 따라서 미리보기 *본문* 은 산출물과 byte-동일(같은 imgBox/imgSlideBox·같은 자산 경로 재작성). 미리보기 창은 사이트 공통 CSS 를 입히고 자산을 소스 폴더에서 프록시해 보여 준다. 헤더/nav/푸터·`<meta>`·JSON-LD 등 풀페이지 chrome 은 만들지 않으므로 — 그건 템플릿 채움 단계 — **풀페이지 정확본은 빌드 후 `dist/`** 로 확인한다(의도된 분담). 이 패리티는 `system/tests/test_render_one.py` 가 빌더 경로와 byte 비교로 잠근다(누가 다른 엔진/경로로 바꾸면 깨짐).

### 17-5. 제약 (§ 15 ⓐ 와 동일)

본문↔메타 분리는 강제(폼이 frontmatter 를 본문에 섞지 않음). 부분집합 YAML 파서는 인라인 주석을 보존 못 하므로 폼 저장 시 헤더 외 커스텀 주석은 유실 — 유지하려면 raw 칸으로 저장. 로컬 단일 사용자·인증 없음·동시 편집 비대상. Windows 비ASCII 폴더명은 PHP 8.x 의 UTF-8 파일시스템 처리에 의존(PHP 8.3 검증) — 폴더명은 출력 무관이라(slug 가 URL) 사이트 산출물에는 영향 없다.

### 17-6. 업데이트 / 마이그레이션 (v1.6.0)

v1.6.0 의 목표는 **사이트가 앞으로의 버전업을 편안하게 따라오는 것**이다. v1.5.0 의 `user/` ↔ `system/` 분리 위에 세운다 — 업그레이드 시 **프로그램 표면**(`system/` + `Heron.py` + `Pond.php`)을 통째 교체하고 `user/` 는 보존하며, 작은 **마이그레이션 엔진**이 스키마 변경을 `user/` 에 반영한다.

**스키마 버전 스탬프.** `user/.heron/version` 은 `user/` 트리가 따르는 스키마 버전을 기록한다 — 프로그램 `__version__` 과는 별개. `user/` 아래 두어 `system/` 교체에도 생존하고 콘텐츠와 함께 이동하며, `.` 접두라 빌드에서 자동 제외된다(§ 6). 스탬프가 없으면 pre-1.6.0 베이스라인으로 간주한다(그래서 fresh 설치는 스탬프만 찍히고, 모든 마이그레이션 스텝은 멱등이다).

**Pond 에서 원클릭 업데이트 (의도된 경로 — 터미널 0줄).**

1. 헤더 **업데이트 확인** → GitHub 의 최신 태그를 조회(결과는 `user/.heron/update.json` 캐시). 새 버전이 있으면 목록 상단에 배너.
2. **지금 업데이트** → 최신 릴리스 다운로드 → `MANIFEST.json`(sha256) 무결성 검증 → 프로그램 표면 + 스탬프를 `user/.heron/backups/` 에 백업 → 프로그램 표면**만** 오버레이(절대 `user/` 미접촉) → 마이그레이션 체인 실행 + 스탬프 갱신.
3. Pond 가 **재시작**을 안내(`Ctrl+C` → `php -S 127.0.0.1:8001 Pond.php`) — 실행 중인 PHP 프로세스가 옛 코드를 메모리에 들고 있어서다. 몰래 reload 흉내 내지 않는 self-update 의 정직한 처리.

로직은 Python(`system/scripts/update.py` + `migrations/`, stdlib `urllib`+`zipfile` 뿐)에 있고 Pond 는 원클릭 빌드와 똑같이 얇은 트리거다. 저장소는 고정(`lamaBread/heron-press`).

**CLI 탈출구 (전문 사용자 / CI).** `Heron.py` 직접 실행은 프로그래머의 몫으로 남기고, 일상 경로는 Pond 가 덮는다. 빌드 자체는 `user/` 에 대해 **읽기 전용**(설계원칙 5) — `--migrate`/`--update` 만 쓰며, 그것도 백업 후에 쓴다.

```bash
python Heron.py --check              # 프로그램/스키마 버전 + MANIFEST 무결성
python Heron.py --migrate --dry-run  # 적용 없이 마이그레이션 미리보기
python Heron.py --migrate            # user/ 를 프로그램 버전까지 마이그레이션 (백업 후 스탬프)
python Heron.py --check-update       # GitHub 조회 (Pond 배너 캐시 갱신)
python Heron.py --update             # 다운로드 → 검증 → 오버레이 → 마이그레이션
```

> **주의** — 업데이트는 HTTPS 로 GitHub 에 접속한다. 일부 Windows Python 설치는 TLS 검증을 위해 시스템 인증서 저장소 설정이 필요할 수 있다(인증서 검증을 끄지는 *않는다*). 인증서 오류로 확인이 실패하면 검증을 우회하지 말고 인증서 저장소를 바로잡을 것.

**마이그레이션 스텝 작성 규약 (앞으로의 버전).** 각 스텝은 `system/scripts/migrations/m_<버전>.py` 의 `Migration` 서브클래스로, `from_version`/`to_version`/`summary` 와 `plan(base)`/`apply(base)` 를 둔다. `apply()` 는 **오직 `user/` 만** 변형하고(프로그램 코드는 통째 교체라 손댈 일 없음) **멱등**이어야 한다(이미 반영된 트리엔 `[]` 반환). `site.yaml` 은 줄단위 텍스트 편집(`_yamledit`)으로 다뤄 주석·순서·`|` 블록을 보존한다(`yaml_parser` 는 읽기 전용). 스탬프 기록은 엔진이 중앙에서 하므로 스텝은 콘텐츠 편집에만 집중한다.

### 17-7. 배포 (rclone, v1.7.0)

빌드된 `dist/` 를 서버에 올리는 일을 Pond 의 **[배포]** 버튼으로 한다 ([§ 13-1](#13-1-pond-원클릭-배포-rclone-v170) 개요). 빌드/업데이트와 같은 **얇은 트리거** 철학 — PHP 는 `python Heron.py --deploy [--dry-run]` 을 띄울 뿐, 다운로드·검증·동기화 로직은 전부 Python(`system/scripts/deploy.py` + `rclone_bin.py`)에 있다.

**왜 rclone 인가.** dist 는 ~157MB 정적 사이트라 매번 전체 전송은 낭비 → 증분이 맞다. `scp -r` 은 고아(서버에만 남은 옛 파일)를 못 지우고, `ssh + rm -rf` 청소는 경로 변수 사고로 서버를 날릴 위험이라 기각. `rsync --delete` 가 정답에 가깝지만 **Windows 네이티브가 아니고 Git for Windows 에도 없다**. 동봉하려니 rsync 는 GPL(재배포 의무) — 그래서 **rclone(MIT, DLL 0 단일 정적 바이너리)**: 동봉/재배포 자유 + rsync 급 증분 + `--dry-run` + `sync` 고아 삭제 + **SFTP 백엔드로 기존 SSH/로컬 키 그대로**(서버 추가 설치 0).

**바이너리 확보 (`rclone_bin.ensure`).** 핀 버전 **v1.74.2** 가 `system/runtime/bin/<os>-<arch>/` 에 이미 있고 `rclone version` 이 일치하면 그대로 쓴다(멱등, 네트워크 0). 없으면 `https://downloads.rclone.org/<ver>/rclone-<ver>-<os>-<arch>.zip` 를 받아 **아카이브 SHA256 을 소스 핀(6개 플랫폼)과 대조** — 불일치면 폐기·중단(공급망 차단). 통과하면 `rclone(.exe)` 만 추출해 원자적으로 배치(임시파일→`os.replace`, POSIX 는 `chmod +x`). 네트워크 실패/오프라인이면 PATH 의 rclone 으로 폴백, 그래도 없으면 명확한 오류. 다운로드 바이너리는 머신 종속물이라 `.gitignore` + `make_manifest` 가 `system/runtime/bin/` 를 프로그램 표면에서 제외해 커밋·MANIFEST·dist 어디에도 새지 않는다.

**2단계 안전 게이트.** `sync` 는 원격을 *삭제*하므로 `remote_path` 오타가 엉뚱한 디렉터리를 비울 수 있다. 그래서 ① **미리보기**(`--dry-run`)로 “보낼/지울” 목록을 먼저 보이고 → ② 확인 버튼으로만 실제 `sync`. 미리보기도 서버에 접속해 양쪽을 비교하므로 사실상 **연결성·호스트키·키 권한 사전 점검**까지 겸한다. 첫 ~157MB 전송이 수 분 걸려도 Pond 는 자식 stdout 을 한 줄씩 받아 **실시간 스트리밍**한다(블로킹 일괄 출력이 아님).

**설정 (`user/.heron/deploy.json` — gitignore).**

```json
{
  "host": "your-domain.com",
  "user": "deployuser",
  "port": 22,
  "remote_path": "/var/www/your-domain.com",
  "ssh_key_path": "C:/Users/you/.ssh/id_ed25519",
  "known_hosts_path": "C:/Users/you/.ssh/known_hosts"
}
```

견본 `deploy.example.json` 을 복사해 채운다. `known_hosts_path` 는 선택(생략 시 `~/.ssh/known_hosts`). `port` 기본 22. **개인키 자체는 절대 deploy.json·저장소에 넣지 않는다 — 경로만.** `.` 접두 + gitignore 라 dist·커밋에 새지 않고 머신별 비공유. 견본은 커밋되지만, 자가 업데이트 오버레이는 `user/` 를 안 건드리므로 **기존 사용자에겐 `m_1_7_0` 마이그레이션이 견본을 시드**한다(멱등 — 이미 있으면 no-op).

**보안.** rclone sftp 백엔드는 기본이 호스트키 미검증(MITM 취약)이라 `--sftp-known-hosts-file` 로 검증을 **강제**한다 — 최초 1회 `ssh user@host` 로 known_hosts 에 등록(TOFU). 인증은 키파일(`--sftp-key-file`)뿐(비밀번호/rclone.conf 미사용). argv 리스트 + `bypass_shell` + Python `subprocess`(shell 미경유)로 인젝션을 막고, Pond 는 cli-server+루프백에서만 동작([§ 17-2](#17-2-보안--절대-공개-서버에-두지-말-것))하므로 키는 로컬을 떠나지 않고 dist 바이트만 암호화 SSH 로 간다. (암호 걸린 키는 ssh-agent 가 필요하다.)

```bash
python Heron.py --fetch-rclone        # rclone 바이너리 선확보 (검증 포함). 멱등.
python Heron.py --deploy --dry-run    # 미리보기: 보낼/지울 목록. 서버 변경 0.
python Heron.py --deploy              # 실제 증분 동기화 (삭제 포함).
```

### 17-8. 설정 — 배포 대상 + 사이트 전역 (v1.8.0)

헤더/네비의 **설정**(`?a=settings`) 은 두 층위의 설정을 한 화면에서 편집한다. 빌드/배포와 같은 **얇은 트리거** 철학 — Pond 는 폼·원문을 받아 검증·저장만 하고, 의미 해석은 Python 빌더에 맡긴다.

**① 배포 (`user/.heron/deploy.json`) — 구조화 폼.** 평평한 JSON 이라 폼이 적합. `deploy.json` 이 없으면 견본(`deploy.example.json`) 값으로 칸을 채워 최초 작성을 돕는다([§ 17-7](#17-7-배포-rclone-v170)). `host`·`user`·`port`·`remote_path`·`ssh_key_path` 필수, `known_hosts_path` 선택(비우면 생략 → `~/.ssh/known_hosts`). **개인키는 받지 않고 경로만** 저장하며, 키 경로의 실제 존재는 검증하지 않는다 — 다른 머신·아직 미생성일 수 있어 차단하면 footgun(정말 없으면 rclone 이 배포 시점에 명확히 실패). 저장 전 직전본을 `user/.heron/backups/settings/` 에 백업.

**② 사이트 (`user/site.yaml`) — 원문 편집기 + 빌드 동일 검증.** `site.yaml` 은 주석이 풍부한 YAML 이라 폼-덤프는 인라인 문서(주석)를 파괴한다(부분집합 파서는 round-trip 불가). 그래서 `meta.yaml` 편집처럼 **원문 그대로** 편집해 주석·순서를 보존하고, 저장 시 신설 `Heron.py --check-config` 로 **빌드와 동일한 검증**을 거친다 — 통과해야만 기록되고, 실패하면 디스크의 `site.yaml` 은 그대로 둔 채 빌더가 보고한 `[ABORT]`/경고를 보이며 편집 내용은 화면에 남는다. 직전본은 `backups/settings/` 에 백업. `--check-config` 는 후보를 stdin 으로 받아 빌드가 쓰는 그 `Builder._apply_site_config` 로 파싱·검증하므로 **'검증 통과 → 빌드 실패' 불일치가 구조적으로 불가능**하다(부수효과인 토크나이저 패리티·Pillow 점검은 `_post_config_checks` 로 분리해 `--check-config` 에선 건너뛴다). 저장은 글 저장과 같은 CRLF→LF 정규화를 적용한다.

```bash
python Heron.py --check-config        # stdin 의 site.yaml 후보를 빌드와 동일 검증 (Pond 저장 게이트).
```

좌상단 **Pond admin** 브랜드는 v1.8.0 부터 **시스템 개요 홈**(`?a=home`)으로 링크된다 — Heron+Pond 전체 흐름을 시각화한 기본 진입 화면([§ 17-3](#17-3-기능)). 글 목록은 nav 의 **목록**(`?a=list`) 으로 분리됐다. v1.9.0 부터 이 화면에 **도구 언어** 드롭다운이 추가됐다([§ 17-9](#17-9-도구-언어--언어팩-v190)).

---

### 17-9. 도구 언어 — 언어팩 (v1.9.0)

Heron+Pond 는 한국어로 설계됐지만 표시 문자열을 **로케일 팩**으로 외부화해 다른 언어로도 쓸 수 있다. 표시 언어는 두 갈래로 **독립**한다:

- **사이트 언어** — 방문자가 보는 `dist/` 의 chrome(검색 박스·푸터·페이지네이션·404·홈/카테고리 라벨). 기존 `site.yaml: lang` 으로 정해지며 **빌드 시점에 치환**된다(결정적 빌드 유지 — 같은 `lang` 이면 출력 byte 불변; `search.php` 는 BM25 인덱스처럼 문자열 테이블을 빌드 때 주입). v1.9.7 부터 `lang` 을 생략하면 **기본값이 영어(`en`)** 다(이전엔 `ko`); 동봉 데모 `user/site.yaml` 도 `lang: en` 으로 배포된다. 사이트 *콘텐츠*(글 본문)의 다국어와는 무관 — 도구가 만드는 UI chrome 의 언어다.
- **도구 언어** — 운영자가 보는 Pond admin UI 와 빌드/CLI 메시지(경고·abort). 신설 `user/.heron/locale` 한 줄(BCP 47 코드)로 정해지고 **설정**(`?a=settings`) 의 드롭다운에서 고른다. 런타임 lookup 이라 빌드와 무관. v1.9.7 부터 `user/.heron/locale` 이 없으면 **기본값이 영어(`en`)** 다(이전엔 `ko`). 이미 언어를 고른 기존 설치는 그 선택을 유지한다(1.8.0→1.9.0 마이그레이션이 1.9.0 이전 업그레이더에게 `ko` 를 시드했고 그대로라 계속 한국어).

**팩 형식.** `system/locales/<locale>/*.yaml` — 한 줄 `키: "값"` 의 플랫 닷(dot) 키. 한 폴더의 조각 파일(`admin.yaml`·`site.yaml`·`build.yaml`·`cli.yaml`)을 머지한다. v1.9.7 부터 `en` 이 정본 겸 모든 로케일의 폴백이라(이전엔 `ko`), 어떤 팩에 키가 없으면 **영어 값**으로 폴백한다 — 부분 번역된 팩은 누락분이 만국 공통으로 읽히는 영어로 떨어진다. `{name}` 자리표시자는 치환된다(예: `검색결과: {n}건`). 큰따옴표 값 안에서는 파서가 `\"` `\\` `\n` `\t` 를 해석하고(그 외 `\x` 는 백슬래시 보존), 작은따옴표 값은 리터럴이다 — 그래서 PHP·Python 로더가 **바이트 동일**하게 파싱한다(`system/admin/lib/i18n.php` / `system/scripts/i18n.py`, 둘 다 의존성 0; `test_i18n` 패리티 테스트가 강제).

**세 표면.** (1) **방문자 사이트 chrome** — *사이트 언어*(`site.yaml: lang`), 빌드 시점에 `dist/` 에 구움; (2) **Pond admin UI** — *도구 언어*, PHP 전역 `t()`; (3) **빌드/CLI 운영자 메시지** — *도구 언어*, Python 전역 `i18n.t()`(및 빌더의 `tool_tr`). 표면 3 은 deploy/update/migration/CLI 출력, v1.9.2 부터 빌더 자신의 **16단계 진행·마일스톤·요약·`build-report.md` 전체**, v1.9.3 부터 argparse `--help`(description·epilog·옵션 `help=`)와 `images.*` 검증·토크나이저 패리티-실패 abort, v1.9.4 부터 글 단위 `_issue`/`_warning` 콘텐츠-결함 본문과 이미지 인코딩-실패 메시지까지 포함한다 — 그래서 도구=`en` 설치는 **상시는 물론 조건부(콘텐츠 결함) 운영자 표면까지 전부 영문**으로 나온다(`--help` 는 파서가 텍스트를 생성 시점에 고정하므로 `Heron.py main()` 이 인자 파싱보다 먼저 도구 언어를 적재한다). 의도적 잔여는 저수준 Pond 보안 가드(403/405/CSRF)와 사용자 결정으로 보존한 일부 사이트 chrome 값뿐인데, 모두 영문이라 도구 언어와 무관하게 일관된다 (403 가드의 한·영 혼용은 v1.9.5 에서 영문 통일 — 403 은 부트스트랩 이전 실행이라 애초에 `t()` 불가).

**새 언어 추가.** v1.9.7 이 두 CLI 명령으로 워크플로를 도구화했다:

- `python Heron.py --new-locale <코드>` — `system/locales/<코드>/` 에 새 팩을 **스캐폴딩**한다. 영어 정본 `*.yaml` 을 그대로 복사하고(즉시 파싱되고 키 패리티를 통과 — 번역 전에는 영어로 표시) 엔도님(자기 언어 표기) 키 `admin.locale.name.<코드>` 를 모든 팩에 주입한다(그래서 **설정** 드롭다운에 바로 뜬다). 코드는 `^[A-Za-z][A-Za-z0-9-]*$` 로 검증해 경로 탐색을 막는다.
- 값을 번역한 뒤 `python Heron.py --check-locale <코드>` 로 **검증**한다. 읽기 전용 진단으로, 영어 정본과 대조해 **누락**(영어 폴백) 키·**잉여**(죽은/오타) 키·값 안의 **stray 백슬래시**(미해결 escape)를 보고하고, **미번역**(값이 아직 영어와 동일) 키 수를 정보성으로 센다. 누락·잉여·stray 백슬래시가 하나라도 있으면 종료 코드가 0 이 아니라서 CI/pre-commit 게이트로 쓸 수 있다. 코드를 생략하면 영어 정본을 뺀 동봉 로케일 전부를 검사한다.

**키 패리티 규칙은 엄격하다** — 동봉 팩은 영어 정본과 **정확히 같은 키 집합**을 가져야 하고 `system/tests/test_i18n.py` 가 강제한다. 누락된 키는 영어로 폴백한다.

---

## 18. 추가 업데이트 제안

v1.4.0 검토 중 함께 논의됐으나 *이 릴리스에 구현하지는 않은* 후보들. 차후 결정의 출발점이지 약속은 아니다. (사용자가 명시적으로 보류한 항목 — 홈/카테고리 JSON-LD, 태그 색인, 글 렌더 병렬화 — 은 여기 두지 않는다. [§ 15](#15-설계-원칙과-한계) ⓑ 표 참조.)

### 18-1. 자동 목차 (TOC) — 긴 글 한정 자동 또는 `meta.yaml toc: true`

**무엇** — 본문 헤딩(h2/h3)으로 사이드(데스크탑)·인라인(모바일) TOC 자동 생성. 임계 = 본문 어절 1500↑ AND h2 ≥ 3 일 때 자동 ON, `toc: false` 강제 OFF / `toc: true` 강제 ON. 토글이 3-상태인 이유 = noindex 같은 *기본 자동, 명시 override* 패턴.

**왜 보류** — 정본 글들 대부분이 짧고 헤딩 수가 적어 즉시 효용이 크지 않다. 도입 시 ① Parsedown 포팅에 헤딩 anchor 부착(현재 `<h2>제목</h2>` → `<h2 id="제목">제목</h2>`), ② 후처리에서 `<nav class="toc">` 빌드, ③ CSS 두 레이아웃(사이드 vs 인라인), ④ 임계 알고리즘 + 토글 3-상태 — 작은 기능이 아니라 적정 릴리스 분량의 한 묶음. *연구 노트/논문 리뷰* 류 글이 늘면 우선순위 상승.

**구현 시 손댈 파일** — `system/scripts/parsedown.py` (헤딩 ID), `system/scripts/markdown.py` (TOC 추출+렌더), `system/scripts/models.py` (`ArticleMeta.toc: Optional[bool]`), `user/styles/common_template.css` (`.toc` 두 레이아웃), `README.md` (§4-2 메타 표 + §9 마크다운 절). 단위 테스트 신설 1식.

### 18-2. `description_truncate` 사용처 해설 + 코드 상수 승격 후보

**현재 어디 쓰이는가** — site.yaml 의 `description_truncate: 150` 은 *단 한 곳* 에만 쓰인다 — **피드(Atom `<summary>` / RSS `<description>`) 의 요약 텍스트 절단 최대 글자 수**. `seo.description` 본문이 이 길이를 넘으면 *영문 단어 경계를 존중* 하며 잘리고 끝에 `…` 가 붙는다 (구현 = `system/scripts/seo.py` 의 `truncate_description`, 호출은 `system/scripts/builder.py` `_render_articles` 두 곳에서 `summary = truncate_description(desc_val, self.site.description_truncate)`).

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

*Heron v1.14.4 — 빌드 Python + Pillow, 런타임 PHP (OPcache 권장). 누적 릴리스 내역은 [§ 16](#16-업데이트-로그).*

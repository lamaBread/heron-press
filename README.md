# siheonlee.com v0.3.2 — 사용설명서 & 시스템 문서

> **이 문서는 처음 이 시스템을 접하는 사람을 위해 작성되었습니다.**
> 기술적인 사전 지식 없이도 읽을 수 있도록, 모든 개념을 처음 등장하는 시점에 설명합니다.

이 시스템은 **글마다 폴더 하나**를 만들어 본문과 첨부파일을 관리하고, `python build.py` 한 번으로 두 도메인 분량의 정적 사이트를 만들어내는 **정적 사이트 생성기(SSG)** 입니다.

| 핵심 가치 | 어떻게 보장하는가 |
|---|---|
| **URL 영구성** — 한 번 발급한 URL 은 절대 깨지지 않는다 | 글 URL(`slug`) 은 카테고리·폴더명과 분리. 글을 옮기거나 폴더명을 바꿔도 URL 불변. |
| **외부 의존성 최소** — 다른 사람도 쉽게 빌드할 수 있다 | Python 3 표준 라이브러리만 사용. 마크다운 파서로 PHP CLI 한 개 추가(불가 시 builtin 자체 파서로 폴백). |
| **서버 설정과 콘텐츠 분리** — 글을 추가해도 서버를 안 건든다 | `.htaccess` 미사용. 모든 라우팅 규칙은 Apache VirtualHost 메인 설정에 한 번만 등록. |
| **두 도메인 동시 관리** — 신규 도메인과 구 도메인 리다이렉트를 한 번에 | 빌드 산출물이 `dist/`(siheonlee.com)와 `dist-legacy/`(lama.pe.kr 301 리다이렉트)로 분리됨. |
| **글마다 표현 제어** — 사이트 전역 CSS 와 별도로 글 단위 미세 조정 가능 | `meta.yaml` 의 `styles:` 필드로 본문 태그(p, h3, ul 등)의 CSS 속성을 글마다 독립적으로 override. |
| **사이트 내 검색** — 클라이언트 JS 없이 한국어 친화 부분검색 (v0.3.1, v0.3.2) | 빌드 시 `dist/search-index.json` (한글 bigram + 영문 토큰 역색인) + `dist/search.php` 동시 생성. 홈/카테고리 인덱스 nav 우측의 미세한 검색 입력. 카테고리 페이지 검색은 자동으로 해당 카테고리 내부로 한정. |

---

## 목차

1. [빠른 시작](#1-빠른-시작)
2. [시스템 개요](#2-시스템-개요)
3. [폴더 구조](#3-폴더-구조)
4. [글 작성하기](#4-글-작성하기)
5. [카테고리 시스템](#5-카테고리-시스템)
6. [글 관리 — 비공개·이동·삭제](#6-글-관리--비공개이동삭제)
7. [빌드](#7-빌드)
8. [산출물 구조와 URL](#8-산출물-구조와-url)
9. [마크다운 문법 레퍼런스](#9-마크다운-문법-레퍼런스)
10. [SEO 설정 레퍼런스](#10-seo-설정-레퍼런스)
11. [사이트 전역 설정 — site.yaml](#11-사이트-전역-설정--siteyaml)
12. [마크다운 파서 교체 시스템](#12-마크다운-파서-교체-시스템)
13. [검색 기능 — search.php (v0.3.1, v0.3.2)](#13-검색-기능--searchphp-v031-v032)
14. [기존 글 마이그레이션 — migrate.py](#14-기존-글-마이그레이션--migratepy)
15. [배포 — 서버 업로드와 Apache 설정](#15-배포--서버-업로드와-apache-설정)
16. [트러블슈팅](#16-트러블슈팅)
17. [설계 원칙과 한계](#17-설계-원칙과-한계)
18. [업데이트 로그](#18-업데이트-로그)

---

## 1. 빠른 시작

### 준비물

- **Python 3.x** (3.8 이상 권장). 터미널에서 `python --version` 으로 확인.
- **PHP CLI** (기본 마크다운 파서가 PHP 의 Parsedown 을 사용함). `php --version` 으로 확인. 7.4 이상 권장.
  - PHP 가 없으면 `site.yaml` 의 `markdown_parser:` 를 `builtin` 으로 바꾸면 됩니다 (자체 파서로 폴백, § 12 참조).
- 그 외 패키지 설치 불필요.

### 빌드

이 폴더(`siheonlee.com_v0.3/`) 에서 터미널을 열고:

```bash
python build.py
```

성공하면 다음과 같이 출력됩니다:

```
빌드 시작...
[markdown] using parser: parsedown

빌드 완료: 2 글, 1 카테고리, 0 경고.
산출물: dist/ (siheonlee.com), dist-legacy/ (lama.pe.kr).
```

### 결과 확인

`dist/hello-world/index.html` 을 브라우저로 열면 샘플 글이 보입니다. CSS/JS 경로가 절대경로(`/assets/...`) 라 더블클릭으로 열면 스타일이 깨집니다 — 이건 정상입니다. 로컬 확인은 다음과 같이:

```bash
cd dist
python -m http.server 8000
# 브라우저로 http://localhost:8000/ 접속
```

---

## 2. 시스템 개요

### SSG 란?

**SSG(Static Site Generator, 정적 사이트 생성기)** 는 글을 미리 HTML 파일로 변환해두는 도구입니다.

```
[기존 PHP 방식]
방문자 요청 → 서버가 PHP 실행 → DB 조회 → HTML 생성 → 응답

[SSG 방식]
운영자 빌드 → HTML 파일 생성 → 서버에 업로드
방문자 요청 → 서버가 파일을 그냥 전달 → 응답  (빠름·단순)
```

### 이 시스템의 특징

- **외부 Python 의존성 0** — Python 3 표준 라이브러리만 사용. `pip install` 불필요.
- **빌드 시 PHP CLI 활용** — 마크다운 파싱은 원본 사이트의 `Parsedown.php` 에 위임. PHP 가 없으면 site.yaml 한 줄로 builtin 자체 파서로 폴백.
- **글 폴더 = 자율적인 단위** — 글마다 독립된 폴더에서 본문·이미지·보조파일을 자유롭게 관리.
- **URL 영구성 보장** — `slug` 가 곧 URL. 글을 다른 카테고리로 옮겨도 URL 이 안 바뀜.
- **글 단위 스타일 조정** — 본문의 p, h3, ul 등의 CSS 속성을 글마다 `meta.yaml` 에서 독립적으로 변경 가능.
- **두 도메인 동시 관리** — `siheonlee.com`(신규 도메인) 과 `lama.pe.kr`(구 도메인 → 301 리다이렉트) 를 한 번의 빌드로 처리.

### 전체 동작 원리

```
[작업 공간]
  Articles/               ← 글 원본 (마크다운 또는 HTML)
  templates/              ← 페이지 틀 (HTML 껍데기)
  assets/                 ← 사이트 공용 CSS, JS
  parsers/                ← 마크다운 파서 (Parsedown.php 등)
  site.yaml               ← 사이트 전체 설정
  legacy-map.yaml         ← 구 URL 매핑표

       │
       ▼
  python build.py         ← 빌드 실행
       │ (.md 파일은 PHP CLI 로 Parsedown 호출)
       ├─────────────────────────────────────┐
       ▼                                     ▼
  dist/                               dist-legacy/
  (siheonlee.com 에 배포)              (lama.pe.kr 에 배포)
```

빌드는 다음 순서로 처리됩니다:

| 단계 | 내용 |
|---|---|
| 1 | `site.yaml`, `legacy-map.yaml` 읽기. `markdown_parser:` 에 따라 파서 인스턴스 생성 |
| 2 | `Articles/` 트리를 뒤져 글 후보 수집 |
| 3 | 각 글의 `meta.yaml` 파싱 (제목, 날짜, SEO 설정, styles 등) |
| 4 | 검증: slug 중복 없는지, 날짜 형식이 맞는지 등 확인. 문제 있으면 빌드 중단 |
| 5 | 각 글의 본문 렌더 (.md 는 파서 호출, .html 은 그대로) → styles 블록 inject → 템플릿에 끼워 넣어 `dist/{slug}/index.html` 생성 |
| 6 | 글별 이미지/파일을 `dist/src/{slug}/` 로 복사 |
| 7 | 카테고리 색인 페이지 생성 |
| 8 | 홈 페이지 생성 |
| 9 | `assets/` → `dist/assets/` 복사 |
| 10 | 404 에러 페이지 생성 |
| 11 | `robots.txt` 생성 |
| 12 | `dist-legacy/redirect.php` 생성 (구 URL 리다이렉트) |
| 13 | 이전 빌드에서 삭제된 글의 파일 정리 (고아 정리) |

---

## 3. 폴더 구조

```
siheonlee.com_v0.3/
│
├── build.py              ← 빌드 스크립트 (이것을 실행합니다)
├── migrate.py            ← 기존 글 마이그레이션 스크립트 (§ 13)
├── site.yaml             ← 사이트 전역 설정
├── legacy-map.yaml       ← lama.pe.kr 구 URL → 신 slug 매핑표
│
├── Articles/             ← ★ 모든 글이 여기에 들어갑니다
│   ├── About/                   ← 톱레벨 글
│   │   ├── meta.yaml
│   │   ├── content.html
│   │   └── face_img.png
│   └── Blog/                    ← 카테고리 폴더
│       └── Hello World/         ← 글 폴더 (폴더명 = 화면 표시명)
│           ├── meta.yaml        ← 글 메타데이터 (slug, 제목, 날짜, styles)
│           ├── content.md       ← 본문 (마크다운 형식)
│           └── imgs/            ← 이미지 등 첨부 (선택)
│
├── templates/            ← 각 페이지 유형의 HTML 틀
│   ├── article.html      ← 글 페이지 틀 ({{ARTICLE_STYLES}} 변수 포함)
│   ├── category.html     ← 카테고리 목록 페이지 틀
│   ├── home.html         ← 홈 페이지 틀
│   └── 404.html          ← 404 에러 페이지 틀
│
├── assets/               ← 사이트 공용 파일 (CSS, JS, 파비콘 등)
│   ├── common_template.css
│   └── imgslidebox.js
│
├── parsers/              ← 마크다운 파서 모듈
│   └── parsedown/
│       ├── Parsedown.php    ← 원본 lama_website-main 그대로
│       ├── run.php          ← stdin → Parsedown → stdout shim
│       └── LICENSE.txt
│
├── dist/                 ← 빌드 산출물 (siheonlee.com 에 배포)
│   └── ...               ← build.py 가 자동 생성. 직접 수정 금지.
│
└── dist-legacy/          ← 빌드 산출물 (lama.pe.kr 에 배포)
    └── ...               ← build.py 가 자동 생성. 직접 수정 금지.
```

> **중요:** `dist/` 와 `dist-legacy/` 안의 파일은 `python build.py` 를 실행할 때마다 덮어씌워집니다. 직접 수정하지 마세요. 수정이 필요하면 `Articles/`, `templates/`, `assets/`, `site.yaml` 을 고치고 다시 빌드하세요.

---

## 4. 글 작성하기

### 4-1. 글 폴더 만들기

글은 `Articles/` 안의 적당한 카테고리 폴더 아래에 **새 폴더를 만드는 것** 으로 시작합니다.

```
Articles/
└── Blog/
    └── 나의 첫 글/        ← 이 폴더를 만듭니다
        ├── meta.yaml      ← 반드시 있어야 합니다
        └── content.md     ← 또는 content.html
```

**폴더명 규칙:**

- 한국어, 영어, 공백, 특수문자 모두 사용 가능.
- 폴더명이 화면에 표시되는 글 이름(링크 텍스트) 이 됩니다.
- 폴더명은 URL 에 쓰이지 않습니다. URL 은 `meta.yaml` 의 `slug` 가 결정합니다.

```
폴더명: "마스크 흡기구 3D 프린팅"   → 화면에는 "마스크 흡기구 3D 프린팅" 으로 표시
slug:  "mask-intake-3d-printing"   → URL: https://siheonlee.com/mask-intake-3d-printing/
```

### 4-2. meta.yaml 작성하기

`meta.yaml` 은 글의 메타데이터 파일입니다. 글 폴더 안에 반드시 있어야 합니다.

```yaml
# ── 필수 항목 ───────────────────────────────────────
slug: my-first-post
title: 나의 첫 번째 글
date: 2026-05-07

# ── 선택 항목 (없어도 됩니다) ──────────────────────
updated: 2026-06-01

seo_title_prefix:
seo_title_suffix:

seo_description:
seo_keywords: []
seo_author:
seo_canonical:

seo_og_title:
seo_og_description:
seo_og_image:
seo_og_image_alt:
seo_og_type: article
seo_twitter_card: summary_large_image
seo_twitter_image:

# 본문 태그의 CSS 속성을 이 글에서만 override (자세한 내용은 § 4-6)
styles:
  p:
    text-indent: 0
    line-height: 1.7em
  h3:
    margin-top: 1.4em
```

#### slug — 가장 중요한 필드

`slug` 는 이 글의 **영구적인 식별자**이자 **URL** 입니다.

```
slug: my-first-post
→ URL: https://siheonlee.com/my-first-post/
```

**slug 규칙:**
- 영어 소문자, 숫자, 하이픈(`-`) 만 허용.
- 시작과 끝은 영숫자여야 함.
- 사이트 전체에서 **유일** 해야 함. 같은 slug 가 두 글에 있으면 빌드 중단.
- 카테고리와 무관. 글을 다른 카테고리로 옮겨도 slug 가 같으면 URL 이 안 바뀜.

**좋은 예:**
```
slug: mask-intake-3d-printing
slug: my-first-post
slug: cpp-template-meta-programming
```

**나쁜 예:**
```
slug: 마스크프린팅       ← 한국어 불가
slug: My_First_Post      ← 대문자, 언더스코어 불가
slug: -first             ← 하이픈으로 시작 불가
slug: blog               ← 예약어 (site.yaml 의 reserved_slugs 참조)
```

#### 전체 필드 설명

| 필드 | 필수 | 설명 | 예시 |
|---|---|---|---|
| `slug` | ✓ | URL 식별자. 사이트 전역 유일 | `mask-intake-3d-printing` |
| `title` | ✓ | 글 제목. `<h1>` 태그에 들어감 | `마스크 흡기구 3D 프린팅` |
| `date` | ✓ | 최초 발행일 (YYYY-MM-DD) | `2021-04-12` |
| `updated` | — | 마지막 수정일 (YYYY-MM-DD). `date` 이후여야 함 | `2025-08-30` |
| `seo_title_prefix` | — | `<title>` 앞에 붙는 문자열 | `"[특집] "` |
| `seo_title_suffix` | — | `<title>` 뒤에 붙는 문자열 | `" - 내 블로그"` |
| `seo_description` | — | 검색엔진에 표시되는 설명. 비면 본문 첫 문단 자동 추출 | `"3D 프린터로 만든 기록"` |
| `seo_keywords` | — | 키워드 목록 | `[3D프린팅, 마스크, 메이커]` |
| `seo_author` | — | 저자명. 비면 site.yaml 의 `default_author` | `이시헌` |
| `seo_canonical` | — | 표준 URL 강제 지정. 비면 자동 생성 | `https://siheonlee.com/my-slug/` |
| `seo_og_image` | — | SNS 공유 시 표시되는 이미지. 비면 본문 첫 이미지 | `./imgs/thumb.jpg` |
| `seo_og_type` | — | OG 타입. 기본값 `article` | `article` |
| `seo_twitter_card` | — | 트위터 카드 타입 | `summary_large_image` |
| `styles` | — | 본문 태그의 CSS 속성을 이 글에서만 override (§ 4-6) | (아래 참조) |

### 4-3. content.md 로 본문 쓰기

`content.md` 는 마크다운 형식으로 본문을 작성하는 파일입니다.

```markdown
# 글 제목 (h1 헤딩)

본문 첫 문단입니다. 빈 줄로 문단을 구분합니다.

두 번째 문단입니다.

## 소제목 (h2)

**굵은 글씨**, *이탤릭*, `인라인 코드` 를 사용할 수 있습니다.

### 표

| 항목 | 값 |
|---|---|
| 이름 | 시헌 |
| 직업 | 공학도 |

### 이미지 첨부 (일반)

![이미지 설명](./imgs/photo.jpg)

### 이미지 첨부 (캡션 포함 — 이 시스템의 특별 문법)

![[이미지 설명]](./imgs/photo.jpg) {캡션 텍스트}
```

기본 마크다운 파서는 [Parsedown.php](parsers/parsedown/Parsedown.php) (PHP CLI). 표·중첩 목록·자동 링크 등 표준 CommonMark 문법을 폭넓게 지원합니다. 자세한 문법은 § 9 참조.

#### 이미지 경로 작성법

이미지 경로는 글 폴더를 기준으로 **상대 경로** 로 씁니다.

```markdown
![photo](./imgs/photo.jpg)
![photo](imgs/photo.jpg)     ← ./ 생략도 가능
```

빌드하면 자동으로 절대 경로로 변환됩니다:

```html
<!-- 빌드 후 -->
<img src="/src/my-slug/imgs/photo.jpg" alt="photo">
```

외부 URL 은 그대로 유지됩니다:

```markdown
![외부 이미지](https://example.com/image.jpg)  ← 변환 안 함
```

### 4-4. content.html 로 본문 쓰기

마크다운 대신 HTML 파일로 본문을 작성할 수 있습니다. 기존 HTML 글을 마이그레이션할 때 주로 사용합니다.

`content.html` 은 `<html>`, `<head>`, `<body>` 없이 본문 HTML 조각만 씁니다:

```html
<p>첫 문단입니다.</p>

<div class="imgBox">
  <img src="./imgs/photo.jpg" alt="사진">
  <p class="caption">캡션 텍스트</p>
</div>

<p>두 번째 문단입니다.</p>
```

> **중요:** `content.md` 와 `content.html` 이 동시에 있으면 빌드가 중단됩니다. 둘 중 하나만 사용하세요. `content.html` 은 마크다운 파서를 거치지 않으므로 파서 선택의 영향을 받지 않습니다.

#### PHP 함수 자동 변환

기존 PHP 기반 글에서 사용하던 두 가지 함수를 자동으로 HTML 로 변환합니다:

**imgBox — 캡션 있는 이미지:**
```html
<!-- content.html 에 이렇게 쓰면 -->
<?php imgBox("./imgs/photo.jpg", "캡션 텍스트", "alt 텍스트") ?>

<!-- 빌드 후 이렇게 변환됩니다 -->
<div class="imgBox">
  <img src="/src/my-slug/imgs/photo.jpg" alt="alt 텍스트">
  <p class="caption">캡션 텍스트</p>
</div>
```

**imgSlideBox — 슬라이드 이미지:**
```html
<!-- content.html 에 이렇게 쓰면 -->
<?php imgSlideBox("./src_slide") ?>

<!-- 빌드 후: src_slide/ 안의 이미지를 알파벳 순으로 슬라이드로 만듦 -->
<div class="imgSlideBox" data-slug="my-slug">
  <img src="/src/my-slug/src_slide/01.jpg" class="slide active">
  <img src="/src/my-slug/src_slide/02.jpg" class="slide">
  <button class="prev">‹</button>
  <button class="next">›</button>
</div>
```

이 두 함수 외의 `<?php ... ?>` 코드는 그대로 보존됩니다. 이 경우 빌드는 해당 글을 `.html` 이 아닌 `.php` 확장자로 출력합니다 (PHP 자동 감지, § 8 참조).

### 4-5. 이미지/파일 첨부하기

글 폴더 안에 `imgs/`, `files/` 등 원하는 이름의 폴더를 만들고 파일을 넣으면 됩니다.

```
Articles/Blog/나의 첫 글/
├── meta.yaml
├── content.md
├── imgs/
│   ├── 사진1.jpg
│   └── 사진2.jpg
├── files/
│   └── 자료.pdf
└── design.f3d     ← 단일 파일도 가능
```

`meta.yaml`, `content.md`, `content.html` 을 제외한 **모든 파일과 폴더** 는 그대로 `dist/src/{slug}/` 로 복사됩니다.

접근 URL:
```
https://siheonlee.com/src/my-first-post/imgs/사진1.jpg
https://siheonlee.com/src/my-first-post/files/자료.pdf
```

#### 보조 HTML/PHP 페이지도 그대로 보존됩니다

```
Articles/Blog/프로젝트/
├── meta.yaml
├── content.md
└── log/
    ├── day1.html    ← 자체 <html><head><body> 있는 독립 HTML
    └── day2.html
```

이 경우 `https://siheonlee.com/src/project-slug/log/day1.html` 로 직접 접근할 수 있습니다.

### 4-6. styles — 글 단위 CSS 오버라이드

**본문 태그의 CSS 속성을 글마다 독립적으로 변경** 할 수 있습니다.

#### 동작 원리

`meta.yaml` 의 `styles:` 필드에 적은 내용이 article.html 의 head 영역에 `<style>` 블록으로 inject 됩니다.

```yaml
# meta.yaml
styles:
  p:
    text-indent: 0
    line-height: 1.7em
  h3:
    margin-top: 1.4em
```

빌드 결과 (생성된 글 페이지의 head):
```html
<link href='/assets/common_template.css' rel='stylesheet'>
<style>
    section p { text-indent: 0; line-height: 1.7em; }
    section h3 { margin-top: 1.4em; }
</style>
```

선택자가 자동으로 `section TAG` 로 wrap 되어 `common_template.css` 의 같은 선택자(specificity 동일) 를 source order 로 덮습니다. 다른 글에는 영향이 없습니다.

#### 기본 사용법 — 태그명을 키로

다음 태그는 자동으로 `section TAG` 선택자로 변환됩니다:

```
p, h1, h2, h3, h4, h5, h6,
ul, ol, li,
blockquote, a,
pre, code,
table, th, td,
img, strong, em, small, hr, div, section
```

```yaml
styles:
  p:
    text-indent: 0
    line-height: 1.5em
    margin-top: 0.4em
    margin-bottom: 0.4em
  ul:
    padding-left: 1em
  blockquote:
    border-left: 3px solid #0172d5
    font-size: 0.85em
  a:
    text-decoration: underline
  code:
    background-color: "#fff3cd"
```

#### 복합 선택자도 가능

키에 공백·`>`·`+`·`~`·`,`·`.`·`[attr]` 가 들어가면 그대로 CSS 선택자로 사용됩니다 (자동 wrap 안 함):

```yaml
styles:
  "section p > strong":          # 자손 + 자식 결합자
    color: "#d33"
  ".note, .info":                # 클래스, 셀렉터 리스트
    background-color: "#eef"
  "ul li:first-child":           # 가상 클래스 (: 때문에 quote 필요)
    margin-top: 0
```

#### 어떤 CSS 든 가능한가? — 정직한 답

**가능한 것:**
- 모든 표준 CSS 속성 (`color`, `transition`, `transform`, `grid-*`, `--my-var` 등).
- 값에 `!important`, `var(...)`, `url(...)`, `calc(...)`, 콤마 (`font-family: "Arial, sans-serif"`).
- 벤더 프리픽스 (`-webkit-*`, `-moz-*`).
- 복합 선택자: 자손 ` `, 자식 `>`, 형제 `+`/`~`, 콤마 리스트, 클래스 `.foo`, 속성 `[a=b]`.

**YAML 인용이 필요한 것** — 키 안의 `:`, `#`, `'`, `"` 가 메타문자이기 때문:
```yaml
styles:
  "#face_img":               # ID 선택자 — # 때문에 quote
    width: 50%
  "p:hover":                 # 가상 클래스 — : 때문에 quote
    color: "#0172d5"
  "p::before":               # 가상 요소
    content: '"→ "'
  "input[type='text']":      # 작은따옴표가 들어간 속성 셀렉터
    border: 1px solid black
```

**근본적으로 안 되는 것:**

| 한계 | 이유 / 회피 |
|---|---|
| `@media` 쿼리 | 현재 직렬화는 `selector { decls }` 평면 규칙만 생성. 반응형은 `content.html` 에 `<style>` 블록을 직접 쓰거나 빌더 확장 필요. |
| `@keyframes`, `@supports`, `@font-face`, `@import` | 위와 동일 — 모든 at-rule 미지원. |
| 한 속성을 여러 줄에 나눠 쓰기 | YAML 한 줄로 작성. (`box-shadow: 0 1px 2px rgba(0,0,0,.1), 0 2px 4px rgba(...)`) |
| 값 라인 옆 인라인 주석 (`text-indent: 0  # 들여쓰기 제거`) | 주석이 값에 포함됨. 주석은 별도 줄에. |

#### 미묘한 함정 — specificity

`section TAG` 선택자는 specificity (0,0,2). 만약 `common_template.css` 에 `body section p` 같은 (0,0,3) 규칙이 더 구체적이면 meta.yaml 의 override 가 안 먹습니다. 그 경우 다음 둘 중 하나로 해결:

- 메타에 더 구체적인 셀렉터로 명시: `"body section p": { text-indent: 0 }`.
- 값에 `!important` 추가: `text-indent: 0 !important`.

About 페이지(content.html) 가 인라인 `<style>` 로 `section p { text-indent: revert; ... }` 를 쓰는 이유도 source order 로 이기기 위함입니다.

#### 권장 사용 사례

- **수필/시 글**: p 의 `text-indent: 0` 으로 들여쓰기 제거, `line-height` 키워서 가독성 향상.
- **레퍼런스 문서**: ul 의 `padding-left` 줄여 인라인 코드와 정렬, `code` 의 배경색 조정.
- **인용 강조**: blockquote 의 `border-left-color` 변경.
- **링크 스타일**: a 의 `text-decoration: underline` 으로 가시성 강조.

---

## 5. 카테고리 시스템

### 카테고리는 폴더입니다

`Articles/` 아래의 폴더 구조가 그대로 카테고리가 됩니다. 별도 설정 파일 없이, **폴더를 만들면 카테고리가 생깁니다.**

```
Articles/
├── Blog/                  → /blog/ 카테고리
│   ├── 3D Printing/       → /blog/3d-printing/ 하위 카테고리
│   │   └── 마스크 흡기구/  → 글 (URL: /mask-intake-3d-printing/)
│   └── Cinema/            → /blog/cinema/ 하위 카테고리
└── Project/               → /project/ 카테고리
    └── My Website/        → /project/my-website/ 하위 카테고리
```

### 카테고리 폴더명 → URL 변환 규칙

카테고리의 URL slug 는 폴더명에서 자동으로 만들어집니다:

| 폴더명 | URL slug |
|---|---|
| `Blog` | `blog` |
| `3D Printing` | `3d-printing` |
| `01 - Side Project` | `01-side-project` |
| `Research Notes (CS)` | `research-notes-cs` |

변환 과정:
1. 영문자, 숫자, 공백, 하이픈, 괄호만 남기고 나머지 제거
2. 괄호 `()` 제거
3. 공백과 연속 하이픈 → 단일 하이픈
4. 양 끝 하이픈 제거
5. 소문자 변환

**주의:** 한국어 폴더명은 변환 결과가 빈 문자열이 되어 빌드가 중단됩니다. 한국어 카테고리가 필요하면 아래의 override 방법을 사용하세요.

### 카테고리 slug override — `_meta.yaml`

카테고리 폴더 안에 `_meta.yaml` 파일을 두면 slug 를 직접 지정할 수 있습니다:

```
Articles/
└── 연구 노트/              ← 한국어 폴더명 (자동 변환 불가)
    └── _meta.yaml          ← slug override 파일
```

```yaml
# Articles/연구 노트/_meta.yaml
slug: research-notes-kr
```

이렇게 하면 `https://siheonlee.com/research-notes-kr/` 카테고리 URL 이 생성됩니다.

> `_meta.yaml` 은 파일명이 `_` 로 시작하지만, 카테고리 메타 파일로서 예외적으로 처리됩니다. 빌드에서 제외되지 않습니다.

### 카테고리 색인 페이지

**톱레벨 카테고리만 색인 페이지를 생성합니다.** 서브카테고리는 톱레벨 페이지에서 그룹으로 표시됩니다 (원본 사이트 동작 보존).

- `dist/blog/index.html` — Blog 카테고리 (모든 서브카테고리 그룹 포함)
- 서브카테고리 (`/blog/3d-printing/`) 는 별도 인덱스 없음.

글이 없는 카테고리도 페이지는 생성되지만 빌드 경고가 출력됩니다.

---

## 6. 글 관리 — 비공개·이동·삭제

### 글 비공개 처리 — `_` 접두

파일이나 폴더 이름 앞에 `_` (언더스코어) 를 붙이면 빌드에서 제외됩니다.

```bash
# 글 폴더 비공개
mv "Articles/Blog/나의 첫 글"  "Articles/Blog/_나의 첫 글"

# 또는 Git 으로
git mv "Articles/Blog/나의 첫 글" "Articles/Blog/_나의 첫 글"
```

그 후 `python build.py` 를 실행하면:
- `dist/my-first-post/` 폴더가 자동으로 삭제됩니다.
- 카테고리·홈 목록에서 사라집니다.
- `lama.pe.kr` 디스패처는 영향받지 않습니다 (legacy-map.yaml 은 영구 고정).

**`_` 접두의 전파 규칙:** 경로의 어느 폴더든 `_` 로 시작하면 그 아래 모든 파일도 제외됩니다.

```
Articles/_drafts/                 ← 이 아래 전체 제외
Articles/Blog/_old-article/       ← 이 글 제외
Articles/Blog/글/imgs/            ← 글 폴더 안 자원 전체 포함
Articles/Blog/글/_secret.jpg      ← 이 파일만 제외 (글 자체는 포함)
```

### 글 이동 (카테고리 변경)

글 폴더를 다른 카테고리로 이동해도 URL(`slug`) 이 바뀌지 않습니다:

```bash
git mv "Articles/Blog/나의 첫 글" "Articles/Project/나의 첫 글"
python build.py
# /my-first-post/ URL 은 그대로 유지됩니다
```

### 글 영구 삭제

```bash
rm -rf "Articles/Blog/나의 첫 글"
# 또는 선택적으로 legacy-map.yaml 의 해당 항목을 null 로 변경 (410 Gone 응답)
python build.py
# dist/my-first-post/ 가 자동으로 삭제됩니다
```

---

## 7. 빌드

### 명령어

```bash
# 일반 빌드
python build.py

# dist/ 와 dist-legacy/ 를 완전히 지우고 새로 빌드
python build.py --clean
```

### 빌드 성공 예시

```
빌드 시작...
[markdown] using parser: parsedown

빌드 완료: 5 글, 3 카테고리, 0 경고.
산출물: dist/ (siheonlee.com), dist-legacy/ (lama.pe.kr).
```

`[markdown] using parser:` 줄에 어떤 파서가 사용되었는지 표시됩니다.

### 빌드 경고 (계속 진행)

경고는 빌드를 중단하지 않고 표준 에러(`stderr`) 로 출력됩니다:

```
[WARN] my-slug: meta updated may be stale (file mtime 2026-06-01 > updated 2026-05-07)
[WARN] my-slug: missing asset imgs/missing.jpg
[WARN] empty category: Blog/Archive
```

| 경고 | 의미 | 대처 |
|---|---|---|
| `meta updated may be stale` | 본문 파일이 수정됐는데 `updated` 날짜가 옛날임 | `meta.yaml` 의 `updated` 갱신 |
| `missing asset` | 본문에 참조했는데 파일이 없음 | 파일 추가 또는 참조 수정 |
| `referenced excluded asset` | `_` 접두 파일을 본문에서 참조 | 참조 제거 또는 파일 공개 |
| `empty category` | 글이 없는 카테고리 | 글 추가 또는 카테고리 폴더 삭제 |

### 빌드 중단 (오류)

중단 조건에 걸리면 빌드가 멈추고 메시지가 출력됩니다:

```
[FAIL] slug 충돌: 'my-first-post'
       at Articles/Blog/나의 첫 글/meta.yaml
          Articles/Project/다른 글/meta.yaml
빌드 중단.
```

| 오류 | 원인 | 대처 |
|---|---|---|
| `slug 충돌` | 같은 slug 가 두 글에 있음 | 한쪽의 slug 변경 |
| `slug 정규식 불일치` | slug 에 한국어·대문자 등이 포함 | 소문자 영숫자 하이픈으로 수정 |
| `slug 예약어` | `blog`, `src` 등 예약된 이름 | site.yaml 의 reserved_slugs 확인 후 변경 |
| `title is empty` | meta.yaml 의 title 비어 있음 | title 입력 |
| `date 형식 오류` | YYYY-MM-DD 형식이 아님 | 날짜 형식 수정 |
| `updated < date` | 수정일이 발행일보다 이전임 | 날짜 확인 후 수정 |
| `content.md and content.html both exist` | 본문 파일이 두 개 | 하나 삭제 |
| `카테고리 slug 빈 문자열` | 한국어 카테고리 폴더에 slug 없음 | `_meta.yaml` 에 slug 추가 |
| `PHP 실행 파일을 찾을 수 없음` | `markdown_parser: parsedown` 인데 PATH 에 php 없음 | PHP 설치 또는 site.yaml 의 markdown_parser 를 builtin 으로 |
| `Parsedown 실패` | PHP 서브프로세스가 0 이 아닌 exit code 반환 | stderr 메시지 확인 |

---

## 8. 산출물 구조와 URL

### dist/ 구조 (siheonlee.com 에 배포)

```
dist/
├── index.html                       ← 홈 페이지 (/)
├── 404.html                         ← 404 에러 페이지 (Apache 가 라우팅)
├── robots.txt                       ← 검색엔진 크롤 정책
│
├── assets/
│   ├── common_template.css          ← 공용 스타일시트
│   ├── imgslidebox.js               ← 슬라이드 이미지 스크립트
│   └── default-og.png               ← 기본 OG 이미지 (직접 추가 필요)
│
├── src/                             ← 글별 첨부 파일
│   └── {slug}/                      ← 글의 slug 이름으로 된 폴더
│       └── imgs/ ...                ← 글 폴더의 파일이 그대로 복사됨
│
├── {slug}/                          ← 글 페이지
│   └── index.html  (또는 index.php) ← PHP 토큰이 있으면 .php
│
├── blog/                            ← 카테고리 색인 페이지
│   └── index.html
│
└── project/
    └── index.html
```

### dist-legacy/ 구조 (lama.pe.kr 에 배포)

```
dist-legacy/
├── redirect.php    ← 구 URL 을 siheonlee.com 의 새 URL 로 301 리다이렉트
└── robots.txt      ← 검색엔진이 리다이렉트를 따라가도록 허용
```

### URL 구조

| 페이지 | URL 형식 | 예시 |
|---|---|---|
| 홈 | `/` | `https://siheonlee.com/` |
| 글 | `/{slug}/` | `https://siheonlee.com/mask-intake-3d-printing/` |
| 카테고리 (톱레벨만) | `/{cat-slug}/` | `https://siheonlee.com/blog/` |
| 글 첨부파일 | `/src/{slug}/{경로}` | `https://siheonlee.com/src/mask-intake-3d-printing/imgs/photo.jpg` |
| 공용 자원 | `/assets/{파일명}` | `https://siheonlee.com/assets/common_template.css` |
| 404 | `/404.html` | Apache 가 미존재 경로에 자동 응답 |

**모든 글·카테고리 URL 은 슬래시(`/`) 로 끝납니다.** 슬래시 없는 URL(`/my-slug`) 로 접근하면 Apache 가 자동으로 슬래시 있는 URL 로 301 리다이렉트합니다.

**글 URL 은 카테고리와 독립입니다.** 같은 이름의 카테고리가 있어도(`/blog/` 카테고리 존재), 글 slug 가 `blog` 가 아니라면 충돌이 없습니다. 단, slug 예약어(`blog`, `project` 등) 로는 글 slug 를 만들 수 없습니다.

### PHP 자동 감지

빌드가 글 본문을 렌더링한 뒤, 결과 HTML 에 `<?php` 또는 `<?=` 가 남아 있으면 해당 글을 `.php` 확장자로 출력합니다:

```
has_live_php = False  →  dist/my-slug/index.html
has_live_php = True   →  dist/my-slug/index.php
```

URL 은 `/{slug}/` 로 동일하고, Apache 의 `DirectoryIndex index.html index.php` 설정이 알아서 처리합니다.

---

## 9. 마크다운 문법 레퍼런스

기본 파서는 [Parsedown.php](parsers/parsedown/Parsedown.php) 입니다. 표준 CommonMark 에 매우 가까운 문법을 지원합니다.

### 헤딩

```markdown
# H1 제목
## H2 제목
### H3 제목
#### H4 제목
##### H5 제목
###### H6 제목

Setext 형식도 가능
==================

이건 H2
-------
```

### 인라인 서식

```markdown
**굵게** 또는 __굵게__
*이탤릭* 또는 _이탤릭_
~~취소선~~
`인라인 코드`
```

### 링크와 이미지

```markdown
[링크 텍스트](https://example.com)
[내부 파일](./document.pdf)
[참조 링크][ref]

[ref]: https://example.com  "선택적 title"

![이미지 설명](./imgs/photo.jpg)
![외부 이미지](https://example.com/img.jpg)

자동 링크: <https://example.com>
```

### 이미지 박스 (캡션 포함) — 이 시스템 전용 문법

```markdown
![[이미지 설명]](./imgs/photo.jpg) {캡션 텍스트가 여기에}
```

결과:
```html
<div class="imgBox">
  <img src="/src/{slug}/imgs/photo.jpg" alt="이미지 설명">
  <p class="caption">캡션 텍스트가 여기에</p>
</div>
```

캡션이 필요 없으면 `{...}` 부분을 생략합니다:
```markdown
![[이미지 설명]](./imgs/photo.jpg)
```

> 이 문법은 빌드 직전 단계에서 raw HTML 로 변환된 후 마크다운 파서로 전달됩니다. 그래서 Parsedown 이든 builtin 이든 동일하게 작동합니다.

### 코드 블록

````markdown
```python
def hello():
    print("Hello, World!")
```
````

코드 블록 안의 `<`, `>`, `&` 는 자동으로 HTML escape 됩니다. `<?php` 같은 코드를 코드 블록에 쓰면 PHP 로 실행되지 않습니다.

### 목록

```markdown
- 항목 A
- 항목 B
  - 중첩 항목
    - 더 깊은 중첩
- 항목 C

1. 첫 번째
   1. 1.1
   2. 1.2
2. 두 번째
3. 세 번째
```

### 인용

```markdown
> 인용 텍스트입니다.
> 여러 줄도 가능합니다.
>
> > 중첩 인용도 됩니다.
```

### 표

```markdown
| 항목 | 값  | 설명          |
|------|----:|---------------|
| 이름 |  3  | 가운데 정렬    |
| 값   | 100 | 오른쪽 정렬    |
```

정렬 표시:
- `:---` 왼쪽
- `:---:` 가운데
- `---:` 오른쪽

### 구분선

```markdown
---
또는 ___ 또는 ***
```

### HTML 직접 사용

마크다운 본문 안에 HTML 태그를 그대로 쓸 수 있습니다. Parsedown 은 블록 레벨 HTML 을 그대로 통과시킵니다.

```markdown
<div class="custom-box">
  <p>이 안의 마크다운은 처리되지 않습니다.</p>
</div>
```

---

## 10. SEO 설정 레퍼런스

`meta.yaml` 의 SEO 필드를 모두 비워도 빌드는 정상 동작합니다. 빌드는 다음 순서로 폴백합니다:

| 출력 태그 | 1순위 | 2순위 | 3순위 |
|---|---|---|---|
| `<title>` | `{prefix}{title}{suffix}` | (원본 사이트는 페이지마다 단순 "Lama" 사용) | — |
| `meta description` | `seo_description` | 본문 첫 문단 (최대 150자) | 출력 생략 |
| `meta keywords` | `seo_keywords` | — | 출력 생략 |
| `meta author` | `seo_author` | `site.yaml 의 default_author` | 출력 생략 |
| `link canonical` | `seo_canonical` | 자동 생성 (`/{slug}/`) | — |
| `og:title` | `seo_og_title` | `<title>` 결과 | — |
| `og:description` | `seo_og_description` | `meta description` 결과 | 출력 생략 |
| `og:image` | `seo_og_image` | 본문 첫 `<img>` | `default_og_image` |
| `twitter:image` | `seo_twitter_image` | `og:image` 결과 | — |

**폴백 결과가 빈 문자열이면 해당 태그 자체를 출력하지 않습니다.** `<meta name="description" content="">` 같은 빈 태그는 절대 생성되지 않습니다.

> **SEO 메타 태그 vs `<meta robots noindex>`**: 글 페이지는 원본 사이트의 `<meta name='robots' content='noindex'>` 를 그대로 보존합니다. SEO 메타 태그는 추가되지만 `noindex` 가 우선이라 검색 엔진 노출은 동일합니다.

---

## 11. 사이트 전역 설정 — site.yaml

`site.yaml` 은 사이트 전체에 적용되는 설정 파일입니다. 잘 변경할 일이 없지만, 사이트 정보가 바뀌면 여기를 수정합니다.

```yaml
# 도메인
domain: siheonlee.com
base_url: https://siheonlee.com

# 사이트 이름 (og:site_name 에 사용)
name: Lama
main_title: Lama

# 기본 저자 (meta.yaml 에서 seo_author 가 없으면 이 값 사용)
default_author: 이시헌

# SNS 공유 시 이미지가 없을 때 사용하는 기본 이미지 경로
default_og_image: /assets/default-og.png

# <title> 기본 서식
default_title_prefix: ""
default_title_suffix: ""

# 저작권 표시
copyright_holder: 이시헌
copyright_year_start: 2025

# 글 slug 로 사용 금지된 예약어 목록
reserved_slugs:
  - src
  - assets
  - blog
  - project
  - research
  - study
  # ...

# 홈 페이지 글 목록에서 제외할 카테고리
home_excludes_categories: [About]

# meta description 자동 추출 시 최대 글자 수
description_truncate: 150

# 마크다운 파서 선택
#   parsedown — lama_website-main 의 Parsedown.php (PHP CLI 필요).
#   builtin   — Python stdlib 자체 파서 (PHP 불필요, 일부 문법 제한).
markdown_parser: parsedown
```

### 새 최상위 카테고리 추가 시

예를 들어 `Articles/Lab/` 이라는 새 카테고리를 만들면, `reserved_slugs` 에 `lab` 을 추가해야 합니다:

```yaml
reserved_slugs:
  - src
  - assets
  - lab      ← 추가
  # ...
```

이렇게 하면 글 slug 가 `lab` 이 되는 실수를 방지합니다.

---

## 12. 마크다운 파서 교체 시스템

마크다운 파서가 추상화되어 있어 site.yaml 한 줄로 교체할 수 있습니다.

### 동작 구조

```
content.md
   │
   ▼
preprocess_md_custom_syntax()        ← 사용자 정의 문법 (![[...]] {...}) → HTML
   │
   ▼
MarkdownRenderer.parse(text) → str   ← 실제 파서 (parsedown 또는 builtin)
   │
   ▼
finalize_md_html()                   ← 후처리: asset 경로 재작성, PHP 시뮬레이션,
   │                                          first_paragraph/first_image 추출
   ▼
RenderResult(html, first_paragraph, first_image)
```

`MarkdownRenderer` 는 `parse(text) -> str` 만 구현하면 되는 단순 인터페이스입니다. 사용자 정의 문법 전처리와 후처리는 어떤 파서에서도 공통으로 적용됩니다.

### 파서 교체

`site.yaml` 의 `markdown_parser:` 한 줄만 변경:

```yaml
markdown_parser: parsedown   # 기본값. PHP CLI 필요.
markdown_parser: builtin     # PHP 불필요. 자체 파서.
```

### 두 파서 비교

| 항목 | parsedown (기본) | builtin |
|---|---|---|
| 의존성 | PHP CLI 필요 | Python 만 |
| 표 (`\| col \|`) | ✓ | ✗ |
| 중첩 목록 | ✓ | ✗ (들여쓴 항목이 별도 단락) |
| 자동 URL 링크 | ✓ | ✗ |
| Setext 헤딩 | ✓ | ✗ |
| 참조 링크 (`[txt][ref]`) | ✓ | ✗ |
| 인라인 서식 | full CommonMark | bold/italic/code/link/image |
| 빌드 속도 | 글당 ~50ms PHP 실행 비용 | 매우 빠름 (in-process) |
| 원본 동작 호환성 | lama_website-main 과 1:1 동일 | 미묘하게 다름 |

### 새 파서 추가

[build.py](build.py) 의 `MarkdownRenderer` 를 상속하고, `make_markdown_renderer()` 팩토리에 분기 한 줄을 추가하면 됩니다.

```python
class MyCustomRenderer(MarkdownRenderer):
    name = 'mycustom'

    def parse(self, text: str) -> str:
        # 여기서 markdown → html 변환
        return rendered_html


def make_markdown_renderer(name: str, base_dir: Path) -> MarkdownRenderer:
    n = (name or 'builtin').strip().lower()
    if n in ('builtin', 'python', ''):
        return BuiltinRenderer()
    if n in ('parsedown', 'php'):
        return ParsedownRenderer(base_dir)
    if n == 'mycustom':                    # ← 여기 추가
        return MyCustomRenderer()
    _die(f"알 수 없는 markdown_parser: '{name}'")
```

### Parsedown.php 업데이트

파서 자체 파일은 [parsers/parsedown/Parsedown.php](parsers/parsedown/Parsedown.php) 에 있습니다. 원본 `lama_website-main/PHP/parsedown/` 에서 그대로 복사한 파일이며, Parsedown 신버전이 나오면 이 파일만 교체하면 됩니다.

PHP shim 인 [parsers/parsedown/run.php](parsers/parsedown/run.php) 는 단순히 stdin → Parsedown → stdout 만 합니다.

---

## 13. 검색 기능 — search.php (v0.3.1, v0.3.2)

사이트 내 글 검색을 제공합니다. 클라이언트 JS 0줄, 외부 검색엔진 의존도 0. 한국어/영어 혼용 본문에서 부분 일치까지 잡아내는 자체 역색인 + 서버측 PHP 검색 엔드포인트로 동작합니다.

### 동작 방식 한눈에

```
[빌드 시점 — Python]
  build.py 가 모든 글의 평문 본문을 토크나이즈 →
  dist/search-index.json (역색인) + dist/search.php (검색 엔드포인트) 생성

[방문자 검색]
  사용자가 nav 우측 검색창에 입력 → form GET → /search.php?q=...
  PHP 가 search-index.json 을 메모리에 로드 →
  쿼리도 같은 토크나이저로 쪼갠 뒤 점수 합산 → 결과 페이지 렌더
```

### UI/UX (v0.3.2 정리)

- **노출 위치** — 홈 (`/`) 과 카테고리 인덱스 (`/blog/` 등) 페이지의 nav 우측 상단에만 표시. 개별 글, About, 404 에서는 노출하지 않음 (그곳에서 굳이 검색을 시작할 일이 없으므로).
- **미관** — 배경색·테두리 없이 nav 의 회색 톤(#AFAFAF)에 녹아드는 italic placeholder "검색" 만 보이고, 클릭(focus) 시 가로로 부드럽게 확장 + 텍스트가 짙어지며 입력 가능 상태가 됨. lama 의 미니멀 톤을 깨지 않도록 의도된 디자인.
    - **input 의 우측 padding 이 비대칭(좌 0.2em / 우 0.6em)인 이유** — Windows 의 한글 fallback 폰트(Malgun Gothic 등)는 진짜 italic 글리프가 없어 브라우저가 faux italic (skew transform) 으로 합성한다. skew 는 마지막 글자의 우측 상단을 컨텐츠 박스 너머로 밀어내므로, 균형 padding 이면 placeholder "색" 의 오른쪽이 잘려 보였다. 우측 padding 을 늘려 그 overflow 를 흡수한다. 줄이지 말 것.
- **모든 뷰포트에서 노출** — 모바일 (≤600px) 포함. 좁은 폭에서는 시작/확장 폭만 줄어듦.
- **검색 결과 페이지 (`/search.php?q=...`)** — 기존 글 목록 (`listup_module_div`) 과 동일 마크업으로 결과를 표시. 각 결과 아래에 매치 위치 ±40 글자 스니펫. 매치된 부분은 `<mark>` (배경 #fff3cd) 로 강조.

### 검색 범위 — 카테고리 스코핑 (v0.3.2)

| 검색 시작 위치 | 보내는 파라미터 | 검색 대상 |
|---|---|---|
| 홈 페이지 (`/`) | `?q=...` | **전체 글** |
| 카테고리 인덱스 (`/blog/` 등) | `?q=...&cat=blog` | 해당 톱레벨 카테고리 내부의 글만 |

- 카테고리 페이지의 nav-search 폼이 hidden `<input name='cat' value='<카테고리 slug>'>` 를 자동 포함합니다.
- 결과 헤더는 검색 범위를 명시합니다:
    - 전체 검색 — `검색결과: N건 — 전체에서 검색`
    - 스코프 검색 — `검색결과: N건 — Blog 카테고리에서 검색 (전체에서 검색)` (괄호 안 링크는 같은 쿼리를 전체로 토글)
- search.php 는 cat 값을 인덱스에 등록된 카테고리 slug 목록으로 화이트리스트 검증합니다 (잘못된 cat 은 전체 검색으로 폴백).

### 토크나이저 — 한국어 친화 bigram

```
입력:  "Hello 마스크 3D프린팅"
토큰:  ['hello', '마스', '스크', '3d', '프린', '린팅']
```

- 영문/숫자 → 단어 단위 (lowercase). 정확 매치.
- 한글 → 음절 2-gram. 한 글자만 있으면 그대로.
- 그 외 문자 → 토큰 분리자.

bigram 인덱스이므로 **부분 검색이 자연스럽게 됩니다.** "프린" 만 입력해도 "프린팅", "프린터", "프린트" 모두 매치. 영어는 정확 단어 매치.

### Python ↔ PHP 토크나이저 일관성 — 핵심 불변식

빌드 측 [build.py](build.py) 의 `_search_tokenize()` 와 런타임 측 [templates/search.php](templates/search.php) 의 `search_tokenize()` 는 **반드시 동일한 입력에 동일한 출력** 을 내야 합니다. 이 규칙이 깨지면 인덱스에는 있지만 검색에서 못 찾는 토큰이 생깁니다.

수정 시 양쪽을 함께 바꾸세요. 두 함수 모두 다음과 동등한 정규식을 사용합니다:

| 패턴 | Python | PHP |
|---|---|---|
| 영문/숫자 | `[a-z0-9]+` | `[a-z0-9]+` |
| 한글 | `[가-힣]+` | `[\x{AC00}-\x{D7A3}]+` (= 같은 범위) |
| 소문자화 | `text.lower()` | `mb_strtolower($text, 'UTF-8')` |

### 인덱스 포맷 (v2)

[dist/search-index.json](dist/search-index.json) 파일 (빌드 산출물):

```json
{
  "version": 2,
  "docs": [
    {"slug":"hello-world","title":"Hello, World!","date":"2026-05-07",
     "category":"Blog","category_slug":"blog","body":"평문 본문 (최대 5000자)..."}
  ],
  "categories":  {"blog": "Blog"},
  "index":       {"마스": [[0, 3]], "프린": [[0, 1]], ...},
  "title_index": {"hello": [[0, 1]], ...}
}
```

- `docs[doc_id]` — 표시용 메타데이터 + 스니펫 추출용 평문. v0.3.2 부터 `category_slug` 추가 (스코프 필터링 키).
- `categories` — 톱레벨 카테고리 slug → folder_name. PHP 가 결과 헤더 라벨 표시 + cat 화이트리스트 검증에 사용.
- `index[token]` — 본문 토큰 → `[[doc_id, term_frequency], ...]`.
- `title_index[token]` — 제목 토큰 (점수 가중치 ×5).
- 톱레벨 카테고리에 속하지 않은 글 (예: About) 은 `category_slug=""` — 전체 검색에는 잡히지만 어떤 카테고리 스코프 검색에도 잡히지 않습니다.

### 점수 계산

```
score(doc) = Σ (본문 매치 tf) + 5 × Σ (제목 매치 tf)
```

쿼리를 토큰화 → 각 토큰의 posting list 를 순회하며 누적. 제목 매치는 ×5 가중치. 동점이면 PHP `arsort` 의 안정성에 따라 doc_id 작은 순.

### 인덱스 크기 (실측)

| 글 수 | 평균 본문 | search-index.json | gzip 후 |
|---|---|---|---|
| 2 (현재) | ~3KB | ~10KB | ~3KB |
| 50 | ~5KB | ~250KB | ~80KB |
| 200 | ~5KB | ~900KB | ~280KB |

PHP 가 매 요청마다 인덱스를 읽으므로 글이 매우 많아지면 다음 최적화 검토:
- PHP `opcache` + `apcu_store()` 로 인덱스 메모리 캐시
- 인덱스 분할 (카테고리별)
- 또는 SQLite 등 정식 인덱스로 이주

### 보안·악용 방지

- 쿼리 길이 100 글자 제한 (`mb_substr($q_raw, 0, 100, 'UTF-8')`).
- 모든 출력은 `htmlspecialchars($x, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8')` 로 escape.
- 강조 (`<mark>`) 는 escape 후에 적용해 XSS 방지.
- 검색 결과 페이지에도 `<meta name='robots' content='noindex'>` 유지 — 외부 검색엔진이 검색 결과 페이지를 색인하는 것을 방지.

### 빌드 산출물

```
dist/
├── search.php            ← 검색 엔드포인트 (PHP)
├── search-index.json     ← 검색 인덱스 (Python 이 생성)
└── ...
```

`reserved_slugs` 에 `search` 가 포함되어 있어 글의 slug 가 `search` 일 수 없음 ([site.yaml](site.yaml) 참조).

### 서버 요구사항

- PHP 7.4 이상 (`mb_*` 함수, arrow function 사용).
- `mbstring` 확장 (대부분 PHP 기본 포함).
- 추가 PHP 확장이나 라이브러리 불필요.

### 고급 — 검색 비활성화

`templates/search.php` 파일을 삭제하면 build.py 가 경고만 출력하고 인덱스 파일은 만들지만 search.php 는 만들지 않습니다. 또한 [templates/home.html](templates/home.html), [templates/category.html](templates/category.html) 의 `<form class='nav-search'>...</form>` 블록을 제거하면 UI 도 사라집니다.

---

## 14. 기존 글 마이그레이션 — migrate.py

기존 `lama_website-main` 의 PHP 기반 글을 이 SSG 시스템으로 옮기는 **일회성 작업** 을 돕는 스크립트입니다.

### 마이그레이션 흐름

```
1. python migrate.py
   → 각 글의 data.json을 읽어 meta.yaml 스캐폴드 생성
   → legacy-map.yaml 초안 생성
   → todo 파일 생성 (어떤 작업이 남았는지 안내)

2. (수동) todo 파일 보면서:
   - 각 글의 meta.yaml 에 slug 채우기
   - legacy-map.yaml 에 slug 채우기
   - HTML 글의 PHP 호출 검토

3. python migrate.py --check
   → 빌드 가능 여부 확인. 문제가 없을 때까지 2-3 반복

4. python build.py
```

### 명령어

```bash
# 1차 변환 (Articles.backup-YYYYMMDD-HHMMSS/ 자동 백업 포함)
python migrate.py

# 검증 모드 (파일 수정 없음, 현재 상태만 평가)
python migrate.py --check

# 시뮬레이트 (파일 수정 없이 무엇을 할지만 출력)
python migrate.py --dry-run
```

### 생성되는 파일

| 파일 | 내용 |
|---|---|
| `migrate-todo-slugs.txt` | slug 를 아직 채우지 않은 글 목록 |
| `migrate-todo-php.txt` | HTML 글 안의 PHP 함수 호출 목록 |
| `migrate-todo-pre-php.txt` | `<pre>` 안에 raw `<?php` 가 있는 경우 |
| `migrate-YYYYMMDD-HHMMSS.log` | 변환 작업 전체 로그 |

### 멱등성 (안전한 재실행)

`migrate.py` 는 재실행해도 안전합니다. `meta.yaml` 이 이미 있고 `data.json` 이 없는 글은 건드리지 않습니다 (스킵). 작업을 며칠에 나눠 해도 됩니다.

---

## 15. 배포 — 서버 업로드와 Apache 설정

빌드 후 생성된 폴더를 서버에 올리고, Apache VirtualHost 를 한 번 등록하면 끝입니다. 이후 글을 추가/삭제해도 서버 설정은 건드릴 필요가 없습니다.

이 시스템은 `.htaccess` 파일을 사용하지 않습니다. 모든 서버 규칙은 Apache 메인 설정(VirtualHost 또는 httpd.conf) 에 등록합니다.

### 14-1. siheonlee.com (신규 도메인)

`dist/` 폴더의 내용을 서버의 DocumentRoot 에 업로드합니다:

```bash
# rsync 예시
rsync -avz --delete dist/ user@siheonlee.com:/var/www/siheonlee.com/

# FTP 클라이언트 (FileZilla 등) 로 dist/ 내용 업로드
# Git push → CI/CD 자동화 (GitHub Actions 등)
```

#### siheonlee.com VirtualHost

```apache
<VirtualHost *:443>
    ServerName siheonlee.com
    ServerAlias www.siheonlee.com

    DocumentRoot /var/www/siheonlee.com
    # ↑ dist/ 의 내용을 이 경로에 배포

    SSLEngine on
    SSLCertificateFile    /etc/letsencrypt/live/siheonlee.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/siheonlee.com/privkey.pem

    <Directory /var/www/siheonlee.com>
        AllowOverride None          # .htaccess 무시
        DirectoryIndex index.html index.php
        DirectorySlash On           # /slug → /slug/ 자동 리다이렉트
        Options -Indexes -MultiViews +FollowSymLinks
        Require all granted
    </Directory>

    AddType application/x-httpd-php .php
    ErrorDocument 404 /404.html     # 없는 페이지 → dist/404.html
    AddDefaultCharset UTF-8
</VirtualHost>

# HTTP → HTTPS 리다이렉트 (선택)
<VirtualHost *:80>
    ServerName siheonlee.com
    ServerAlias www.siheonlee.com
    RewriteEngine On
    RewriteRule ^.*$ https://siheonlee.com%{REQUEST_URI} [L,R=301]
</VirtualHost>
```

### 14-2. lama.pe.kr (구 도메인 — 리다이렉트 전용)

`dist-legacy/` 폴더의 내용을 서버에 **한 번만** 올립니다. 이후에는 수정할 일이 없습니다:

```bash
rsync -avz dist-legacy/ user@lama.pe.kr:/var/www/lama.pe.kr/
```

`dist-legacy/` 에는 두 파일만 있습니다:
- `redirect.php` — 모든 구 URL 을 siheonlee.com 의 새 URL 로 301 리다이렉트
- `robots.txt` — 검색엔진이 리다이렉트를 따라가게 허용

#### lama.pe.kr VirtualHost (리다이렉트 전용)

```apache
<VirtualHost *:443>
    ServerName lama.pe.kr
    ServerAlias www.lama.pe.kr

    DocumentRoot /var/www/lama.pe.kr
    # ↑ dist-legacy/ 의 내용을 이 경로에 배포

    SSLEngine on
    SSLCertificateFile    /etc/letsencrypt/live/lama.pe.kr/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/lama.pe.kr/privkey.pem

    <Directory /var/www/lama.pe.kr>
        AllowOverride None
        Options -Indexes -MultiViews +FollowSymLinks
        Require all granted
    </Directory>

    AddType application/x-httpd-php .php

    # 라우팅: robots.txt 와 redirect.php 자체는 직접, 그 외 모두 redirect.php 로
    RewriteEngine On
    RewriteRule ^/robots\.txt$ - [L]
    RewriteRule ^/redirect\.php$ - [L]
    RewriteRule ^.*$ /redirect.php [L]
</VirtualHost>
```

### 14-3. 빌드 머신 vs 배포 서버의 PHP

> **빌드 머신과 배포 서버의 PHP 는 별개입니다.** 빌드 머신에서 Parsedown 호출을 위해 PHP CLI 가 필요하지만, 배포 서버에는 PHP 가 필요 없습니다 (산출물이 정적 HTML 이므로). 단, 글에 처리되지 않은 `<?php` 가 남아 `.php` 로 출력되는 경우는 배포 서버도 PHP 모듈이 필요합니다.

### 14-4. 배포 검증 체크리스트

배포 후 다음을 확인하세요:

```bash
curl -I https://siheonlee.com/                    # 200 OK
curl -I https://siheonlee.com/hello-world         # 301 → /hello-world/
curl -I https://siheonlee.com/hello-world/        # 200 OK
curl -I https://siheonlee.com/없는페이지/           # 404 (본문은 /404.html)
curl -I https://siheonlee.com/robots.txt          # 200 OK, text/plain

curl -I https://lama.pe.kr/Articles/Blog/Hello%20World/   # 301 → siheonlee.com/hello-world/
curl -I https://lama.pe.kr/robots.txt             # 200 OK (redirect 우회)
curl -I https://lama.pe.kr/없는경로/               # 302 → siheonlee.com/404.html
```

---

## 16. 트러블슈팅

### Q: 빌드는 성공했는데 페이지 CSS 가 깨져 보입니다.

빌드 산출물을 로컬에서 직접 열면(파일 더블클릭) CSS 경로(`/assets/...`) 가 절대 경로라 로드되지 않습니다. 이는 정상입니다. 서버에 올리거나, 로컬에서 간단한 HTTP 서버를 통해 확인하세요:

```bash
# Python 내장 HTTP 서버 (dist/ 폴더에서 실행)
cd dist
python -m http.server 8000
# 브라우저에서 http://localhost:8000/ 접속
```

### Q: `[FAIL] PHP 실행 파일을 찾을 수 없음` 오류가 납니다.

`markdown_parser: parsedown` (기본값) 으로 빌드하려면 PHP CLI 가 PATH 에 있어야 합니다. 두 가지 해결책:

1. PHP 설치 (https://www.php.net/downloads). 설치 후 `php --version` 으로 확인.
2. PHP 가 없는 환경이면 `site.yaml` 에서 `markdown_parser: builtin` 으로 변경. 자체 파서로 빌드됩니다 (일부 문법 제한 있음 — § 12 비교표 참조).

### Q: meta.yaml 에 styles 를 썼는데 적용이 안 됩니다.

다음을 차례로 확인:

1. **글이 .md 또는 .html 든 styles 는 head 의 `<style>` 블록으로 모든 글 페이지에 inject 됩니다.** 카테고리/홈 페이지에는 inject 되지 않음 (article.html 템플릿 전용).
2. **templates/article.html 에 `{{ARTICLE_STYLES}}` 변수가 있는지 확인.** 직접 커스텀한 사용자라면 head 영역에 추가해야 합니다.
3. **specificity 충돌.** common_template.css 에 더 구체적인 선택자가 있으면 override 가 안 됩니다. 메타에서 더 구체적인 셀렉터를 쓰거나 `!important` 추가.
4. **YAML 인용 누락.** `:hover`, `#id`, `::before` 같은 키는 YAML 에서 따옴표로 감싸야 함.

### Q: meta.yaml 의 styles 에서 `@media` 쿼리를 쓰고 싶습니다.

현재 시스템은 평면 규칙만 직렬화하므로 at-rule 미지원입니다. 회피책:

- `content.html` 에 `<style>` 블록을 직접 넣어 거기서 `@media` 작성.
- 또는 build.py 의 `render_article_styles()` 를 확장하여 nested at-rule 직렬화 추가.

### Q: `slug 충돌` 오류가 납니다.

같은 slug 를 두 글에서 쓰고 있습니다. 오류 메시지에 나온 두 파일 중 하나의 slug 를 변경하세요.

### Q: 새 카테고리를 만들었는데 URL 이 이상합니다.

카테고리 폴더명에 영어가 없으면 slug 가 빈 문자열이 되어 빌드가 중단됩니다. 해당 카테고리 폴더 안에 `_meta.yaml` 을 만들고 slug 를 지정하세요 (§ 5 참조).

### Q: 이미지가 표시되지 않습니다.

1. 이미지 파일이 글 폴더 안에 있는지 확인하세요.
2. `content.md` 에서 경로를 글 폴더 기준 상대경로로 쓰셨나요? (`./imgs/photo.jpg` 형식)
3. 빌드 경고에 `missing asset` 이 나오지 않는지 확인하세요.
4. `dist/src/{slug}/imgs/` 안에 파일이 복사되어 있는지 확인하세요.

### Q: 기존 PHP 글인데 `.php` 확장자로 출력되지 않고 `.html` 로 나옵니다.

`content.html` 안에 처리되지 않은 `<?php` 가 남아 있어야 `.php` 로 출력됩니다. `imgBox`, `imgSlideBox` 는 빌드가 자동으로 HTML 로 변환하기 때문에 그 결과에는 `<?php` 가 없어서 `.html` 로 출력됩니다. 실제로 서버에서 실행해야 하는 PHP 코드가 있어야 `.php` 로 출력됩니다.

### Q: `dist/` 를 지웠다 다시 빌드하고 싶습니다.

```bash
python build.py --clean
```

### Q: migrate.py 를 실행했더니 Articles/ 가 통째로 복사됐습니다.

정상입니다. `Articles.backup-YYYYMMDD-HHMMSS/` 라는 이름으로 자동 백업된 것입니다. 마이그레이션 중 실수가 있어도 복구할 수 있도록 보호장치로 만들어두는 폴더입니다.

---

## 17. 설계 원칙과 한계

### 설계 원칙

1. **URL 영구성** — 글의 URL 은 카테고리 이동, 폴더명 변경과 무관하게 slug 가 바뀌지 않는 한 영구 유지. ("Cool URIs don't change")

2. **표시명과 URL slug 분리** — 화면에 보이는 이름은 한국어 폴더명, URL 은 영문 ASCII slug 로 독립 관리.

3. **외부 Python 의존성 0** — 새 환경에서 Python 3 만 있으면 기본 동작 가능. Parsedown 사용은 PHP CLI 추가 의존이지만 builtin 폴백 가능.

4. **서버 설정과 콘텐츠 분리** — `.htaccess` 가 없어 서버 설정과 콘텐츠가 완전히 분리. 글을 아무리 많이 추가해도 서버 설정을 건드릴 필요가 없음.

5. **빌드의 안전성** — 빌드 스크립트는 `Articles/` 를 **읽기만** 함. 소스 파일을 자동으로 수정하지 않음. migrate.py 만 파일을 수정.

6. **파서 교체성** — 마크다운 파싱은 추상화된 인터페이스 뒤에 숨겨져 있어, 더 좋은 파서를 쓰고 싶을 때 한 줄 설정으로 교체 가능.

7. **글 단위 표현 제어** — 사이트 전역 CSS 와는 별도로, 글마다 독립적인 표현 결정을 meta.yaml 에서 선언적으로 관리.

### 현재 버전(v0.3.2) 의 한계

| 한계 | 내용 |
|---|---|
| 태그 없음 | meta.yaml 에 tags 필드가 없습니다. |
| 페이지네이션 없음 | 카테고리에 글이 많아지면 한 페이지에 전부 나열됩니다. |
| RSS 없음 | RSS/Atom 피드가 없습니다. |
| styles 의 @-rule 미지원 | `@media`, `@keyframes` 등은 inject 안 됨. content.html 의 인라인 `<style>` 로 회피. |
| 서브카테고리 인덱스 없음 | 톱레벨 카테고리에서 그룹으로만 표시 (원본 동작 보존). |
| Apache 메인 설정 접근 필요 | 공유 호스팅에서 메인 설정 접근이 안 되면 호스팅 사업자에게 요청해야 함. |
| PHP 호스팅 전제 (조건부) | 글에 처리되지 않은 PHP 가 있으면 `.php` 로 출력 — 배포 서버에 PHP 모듈 필요. |
| 빌드 PHP 의존 (조건부) | parsedown 사용 시 빌드 머신에 PHP CLI 필요. builtin 으로 폴백 가능. |

---

## 18. 업데이트 로그

다섯 버전의 차이를 한눈에:

| 영역 | v0.1 | v0.2 | v0.3 | v0.3.1 | v0.3.2 (현재) |
|---|---|---|---|---|---|
| 출력 UI/UX | v0.1 자체 디자인 | 원본 `lama_website-main` 와 동일 | 원본 + 글마다 스타일 오버라이드 가능 | (동일) + 모든 페이지 nav 우측 검색창 + Recent posts 위 inline 폼 | (동일) — nav-search 만 (홈/카테고리 인덱스 한정), 카테고리별 스코프 검색 |
| 마크다운 파서 | Python stdlib 자체 파서 | (동일) | **Parsedown.php (PHP CLI)** — 자체 파서는 fallback | (동일) | (동일) |
| meta.yaml 필드 | slug, title, date, seo_* | (동일) | + **`styles:` (글 단위 CSS 오버라이드)** | (동일) | (동일) |
| YAML 파서 | flat 매핑만 | (동일) | + **nested mapping (styles 트리용)** | (동일) | (동일) |
| 검색 | — | — | — | **dist/search.php + search-index.json (한글 bigram 역색인)** | + **카테고리 스코프 (?cat=) + 결과 헤더 범위 표기** (인덱스 v2) |
| 외부 의존성 | Python 3 | (동일) | Python 3 + (parsedown 사용 시) PHP CLI | Python 3 + PHP CLI (빌드) + PHP runtime (검색) | (동일) |

### v0.3.2 (2026-05-10) — 검색 UI 정리 + 카테고리 스코프 검색

| 개선 | 내용 |
|---|---|
| home-search 제거 | 메인 페이지 section 상단의 inline `[input] [검색]` 폼을 완전히 제거. nav-search 만 남겨 lama 의 미니멀 톤을 회복. |
| nav-search 노출 정책 | 홈 / 카테고리 인덱스 페이지에만 노출. 개별 글, About, 404 에서는 미노출. |
| nav-search 미관 | 배경/테두리 없이 nav 회색 톤(#AFAFAF)에 녹아드는 italic placeholder. focus 시 가로로 확장 + 텍스트가 짙어짐. |
| 모바일 노출 | ≤600px 에서도 노출 (v0.3.1 은 숨김). 좁은 화면에서는 시작/확장 폭만 축소. |
| 카테고리 스코프 검색 | 카테고리 인덱스의 nav-search 가 `?cat=<slug>` 를 자동 첨부. search.php 가 해당 카테고리 내부 글로 한정. |
| 결과 헤더 범위 표기 | `검색결과: N건 — Blog 카테고리에서 검색 (전체에서 검색)` / `… — 전체에서 검색`. 토글 링크로 쉽게 확장. |
| 인덱스 포맷 v2 | `docs[i].category_slug` 추가, 톱레벨 카테고리 slug→folder_name 의 `categories` map 추가. |

#### v0.3.1 → v0.3.2 마이그레이션 시 주의

- **템플릿 직접 커스텀했던 사용자** — home.html / category.html 의 `<form class='nav-search'>` 만 유지. category.html 에는 `<input type='hidden' name='cat' value='{{NAV_SEARCH_CAT}}'>` 한 줄 추가 필요. article.html / 404.html / home.html section 안의 search form 은 모두 제거.
- **CSS** — `.home-search` 관련 스타일 전체 제거. `.nav-search` 의 배경/테두리 제거 + `.search-scope` 클래스 추가 ([assets/common_template.css](assets/common_template.css) 의 v0.3.2 섹션 참조).
- **인덱스 포맷 변경** — `version` 1 → 2. PHP 측은 후방 호환을 위한 `?? ''` 폴백을 두지만, 새 빌드 직후 인덱스 재생성 권장 (`python build.py --clean`).
- **검색 비활성화** — 같은 방법: `templates/search.php` 삭제 + 두 템플릿의 `nav-search` 폼 제거.

### v0.3.1 (2026-05-09) — 사이트 내 검색

| 개선 | 내용 |
|---|---|
| 검색 인덱스 빌드 | build.py 에 `_build_search()` 추가 (pipeline step [13]). 모든 글의 평문 본문 + 제목을 한글 bigram + 영문 토큰으로 토크나이즈해 [dist/search-index.json](dist/search-index.json) 생성. |
| 검색 엔드포인트 | [templates/search.php](templates/search.php) — 인덱스를 메모리에 로드하고 점수 계산 후 결과 HTML 렌더. 클라이언트 JS 0줄. |
| UI | nav 우측 작은 검색창 (모든 페이지) + 메인 페이지 section 상단 inline 폼. lama 미학 그대로 유지. 모바일에서는 nav 검색창 숨김. |
| Python ↔ PHP 일관성 | `_search_tokenize()` (Python) 와 `search_tokenize()` (PHP) 가 같은 입력에 같은 출력을 내야 함. § 13 참조. |
| reserved_slugs | `search` 추가. |

#### v0.3 → v0.3.1 마이그레이션 시 주의

- **PHP runtime 필요** — 빌드뿐 아니라 운영 서버에도 PHP 가 동작해야 함 (이 프로젝트는 dist-legacy/redirect.php 때문에 이미 PHP 사용 중이므로 추가 요구 없음).
- **템플릿 직접 커스텀했던 사용자** — home.html / category.html / article.html / 404.html 의 `<nav>` 안에 `<form class='nav-search'>...</form>` 1블록을 추가해야 nav 검색창이 표시됨. home.html 의 section 안쪽에는 `<form class='home-search'>` 도 별도로 추가.
- **검색 비활성화** — `templates/search.php` 를 삭제하면 검색 페이지는 안 만들어짐. 템플릿의 `nav-search` / `home-search` form 도 빼면 UI 도 사라짐.

### v0.3 (2026-05-09) — 원본 마크다운 파서 + 글 단위 스타일 오버라이드

| 개선 | 내용 |
|---|---|
| 마크다운 파서 교체 | 자체 파서 대신 원본 `lama_website-main` 의 [Parsedown.php](parsers/parsedown/Parsedown.php) 를 PHP CLI 로 호출. 표·중첩 목록·자동 링크 등 풍부한 마크다운 문법 지원. 미묘한 파싱 차이로 인한 원본과의 시각적 불일치가 사라짐. |
| 글 단위 스타일 오버라이드 | `meta.yaml` 의 `styles:` 필드로 본문 태그(p, h3, ul, blockquote, a 등) 의 CSS 속성을 글마다 독립적으로 조정. 결과는 head 의 `<style>` 블록으로 inject 되어 `section TAG` 선택자로 적용. |
| 파서 추상화 (확장점) | `MarkdownRenderer` 베이스 클래스를 두고 site.yaml 의 `markdown_parser:` 한 줄로 파서 교체 가능 (`parsedown` ↔ `builtin`). 새 파서 추가는 클래스 1개 + 팩토리 분기 1줄. |
| YAML 파서 확장 | nested mapping 지원. styles: 의 `tag → {prop: value}` 트리 파싱용. |

#### 파서 차이로 인한 출력 변화 — 좋은 쪽

| 입력 | v0.2 builtin 출력 | v0.3 Parsedown 출력 |
|---|---|---|
| 중첩 ordered list | 깨짐 (들여쓴 항목이 별도 단락으로) | 정상 `<ol><li>...<ol>...</ol></li></ol>` |
| 마크다운 표 (`\| col \|`) | 미지원 (단순 텍스트로) | `<table>` 변환 |
| 자동 URL 링크 | 미지원 | `https://...` 자동 `<a>` 변환 |
| `> 인용` 여러 줄 | `' '.join` 한 한 줄 | 줄바꿈 보존 |

#### v0.2 → v0.3 마이그레이션 시 주의

- **PHP CLI 추가 필요** — `markdown_parser: parsedown` (기본값) 으로 빌드하려면 `php` 명령이 PATH 에 있어야 함. `php --version` 으로 확인. PHP 가 없으면 `site.yaml` 의 `markdown_parser:` 를 `builtin` 으로 바꾸면 v0.2 와 동일하게 동작.
- **글 본문**: 변경 불필요. v0.2 에서 작동하던 `content.md` / `content.html` 은 그대로 작동. Parsedown 이 v0.2 자체 파서보다 표준 CommonMark 에 가까워 일부 글의 출력이 미묘하게 좋아짐.
- **meta.yaml**: `styles:` 필드는 선택 사항. 안 써도 v0.2 와 동일하게 동작.
- **article.html 템플릿**: `{{ARTICLE_STYLES}}` 변수가 head 영역에 추가됨. 직접 커스텀한 사용자는 head 의 적당한 위치에 `{{ARTICLE_STYLES}}` 를 추가해야 함 (없어도 빌드는 성공하지만 styles 필드를 사용해도 적용 안 됨).

### v0.2 (2026-05-09) — 원본 UI/UX 보존

v0.1 의 SSG 내부 시스템은 그대로 유지하면서, 출력 HTML/CSS 만 원본 `lama_website-main` 의 UI/UX 와 동일하도록 변경한 버전.

| 영역 | v0.1 | v0.2 (= 원본) |
|---|---|---|
| 헤더 | `siheonlee.com` 사이트 타이틀 + nav 통합 | `Lama` 헤더 + nav 분리 |
| 네비게이션 순서 | `Blog \| Project \| Research \| Study \| About` | `About \| Blog \| Project \| Research \| Study` |
| Breadcrumb | `Home › Blog › 글` (chevron) | `Home / Blog / 글` (slash, nav 안에 nav-tracker) |
| 홈 글 목록 | `<ul class="article-list"><li>` | `<div class="listup_module_div">` + `<span class="listup_module_title/date">` |
| 카테고리 인덱스 | 모든 카테고리·서브카테고리에 인덱스 페이지 생성 | 톱레벨 카테고리에서 서브카테고리 그룹으로 표시 |
| 푸터 | `© 2026 이시헌` | `Copyright© 2026. 이시헌. All rights reserved.` |
| `<title>` | `{글제목} \| siheonlee` | `Lama` (원본은 페이지마다 단순 "Lama") |
| `<meta name="robots">` | 없음 (검색엔진 인덱스) | `noindex` (원본 그대로) |
| CSS | v0.1 자체 디자인 | 원본 `common_template.css` 그대로 (30% 양 마진, sticky nav 등) |

**기존 lama.pe.kr 방문자 입장에서는 URL 만 새 slug 형식(`/{slug}/`) 으로 바뀌고, 그 외 화면 구성은 모두 동일하게 보입니다.**

#### v0.1 → v0.2 마이그레이션 시 주의

- About 페이지는 `Articles/About/meta.yaml` + `content.html` 의 일반 글로 통합 (slug=about). `reserved_slugs` 에서 `about` 제거함.
- 톱레벨 카테고리 (Blog/Project/Research/Study) 만 `dist/{cat}/index.html` 생성됨. 서브카테고리는 별도 인덱스 없음 (원본 quirk 그대로 보존).
- 네비게이션 링크는 `Articles/` 직속 폴더를 자동 스캔. About 우선, 나머지는 알파벳 정렬 (원본 PHP `generateNavLinks()` 와 동일).
- `site.yaml` 에 `main_title` 추가 (헤더 좌상단 큰 글씨, 기본값 "Lama").
- 푸터의 연도는 빌드 시점의 현재 연도. 시작 연도 범위 표시 안 함 (원본은 단일 "2025" 로 하드코딩).

#### 원본과의 의도적 차이 (내부 개선 — 화면에는 영향 없음)

- 글 본문 head 에 `description / og:* / twitter:*` 등 SEO meta 태그 추가 (원본은 noindex 만). `noindex` 가 우선이므로 검색 노출은 동일.
- CSS·JS 가 `/assets/` 경로로 정리됨 (원본은 `/common_template.css` 루트). 화면 렌더 결과는 동일.
- 글 폴더 안의 파일은 `/src/{slug}/` 로 복사됨 (원본은 글 폴더 절대경로). 글 본문 안의 상대 경로 `./imgs/x.jpg` 는 자동 변환.

### v0.1 — SSG 시스템 자체 완성

- Python stdlib only 로 구현된 SSG 의 첫 동작 버전. YAML 파서·마크다운 파서·HTML 처리·라우팅·legacy 리다이렉트 등 핵심 시스템 완비.
- 출력 HTML/CSS 는 v0.1 자체 디자인 (siheonlee.com 브랜드, chevron breadcrumb, ul/li 글 목록, h1 article-title 등). 원본 lama 사이트와 화면이 다름.
- 핵심 설계 원칙: URL 영구성, 표시명과 URL slug 분리, 외부 의존성 0, 서버 설정과 콘텐츠 분리, 빌드의 안전성.

---

*이 문서는 siheonlee.com SSG v0.3.2 기준으로 작성되었습니다. (2026-05-10)*

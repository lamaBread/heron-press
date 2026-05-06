# siheonlee.com — 사용설명서 & 시스템 문서

> **이 문서는 처음 이 시스템을 접하는 사람을 위해 작성되었습니다.**  
> 기술적인 사전 지식 없이도 읽을 수 있도록, 모든 개념을 처음 등장하는 시점에 설명합니다.

---

## 목차

1. [이 시스템은 무엇인가](#1-이-시스템은-무엇인가)
2. [전체 동작 원리](#2-전체-동작-원리)
3. [폴더 구조](#3-폴더-구조)
4. [빠른 시작 — 5분 안에 빌드해보기](#4-빠른-시작--5분-안에-빌드해보기)
5. [글 작성하기](#5-글-작성하기)
   - 5-1. 글 폴더 만들기
   - 5-2. meta.yaml 작성하기
   - 5-3. content.md 로 본문 쓰기
   - 5-4. content.html 로 본문 쓰기
   - 5-5. 이미지/파일 첨부하기
6. [카테고리 시스템](#6-카테고리-시스템)
7. [글 관리 — 비공개, 이동, 삭제](#7-글-관리--비공개-이동-삭제)
8. [빌드 명령어 레퍼런스](#8-빌드-명령어-레퍼런스)
9. [산출물 구조 — dist/ 와 dist-legacy/](#9-산출물-구조--dist-와-dist-legacy)
10. [URL 구조](#10-url-구조)
11. [마크다운 문법 레퍼런스](#11-마크다운-문법-레퍼런스)
12. [SEO 설정 레퍼런스](#12-seo-설정-레퍼런스)
13. [사이트 전역 설정 — site.yaml](#13-사이트-전역-설정--siteyaml)
14. [기존 글 마이그레이션 — migrate.py](#14-기존-글-마이그레이션--migratepy)
15. [배포하기](#15-배포하기)
16. [Apache 서버 설정](#16-apache-서버-설정)
17. [트러블슈팅](#17-트러블슈팅)
18. [설계 원칙과 한계](#18-설계-원칙과-한계)

---

## 1. 이 시스템은 무엇인가

### SSG란?

**SSG(Static Site Generator, 정적 사이트 생성기)** 는 글을 미리 HTML 파일로 변환해두는 도구입니다.

기존의 PHP 기반 사이트는 방문자가 페이지를 요청할 때마다 서버가 코드를 실행해서 HTML을 그때그때 만들어냅니다. 반면 SSG를 쓰면 **글을 업데이트할 때만 HTML을 한 번 만들어두고**, 방문자에게는 그 파일을 그냥 전달합니다.

```
[기존 PHP 방식]
방문자 요청 → 서버가 PHP 실행 → DB 조회 → HTML 생성 → 응답

[SSG 방식]
운영자 빌드 → HTML 파일 생성 → 서버에 업로드
방문자 요청 → 서버가 파일을 그냥 전달 → 응답 (빠름, 단순함)
```

### 이 시스템의 특징

- **외부 의존성 0** — Python 3 표준 라이브러리만 사용합니다. `pip install` 이 필요 없습니다.
- **글 폴더 = 자율적인 단위** — 글마다 독립된 폴더에서 본문·이미지·보조파일을 자유롭게 관리합니다.
- **URL 영구성 보장** — 글의 URL(`slug`)은 카테고리와 분리되어 있어, 글을 다른 카테고리로 옮겨도 URL이 바뀌지 않습니다.
- **두 도메인 동시 관리** — `siheonlee.com`(신규 정식 도메인)과 `lama.pe.kr`(구 도메인 → 301 redirect) 를 한 번의 빌드로 처리합니다.

---

## 2. 전체 동작 원리

```
[작업 공간]
  Articles/               ← 글 원본 (마크다운 또는 HTML)
  templates/              ← 페이지 틀 (HTML 껍데기)
  assets/                 ← 사이트 공용 CSS, JS
  site.yaml               ← 사이트 전체 설정
  legacy-map.yaml         ← 구 URL 매핑표

       │
       ▼
  python build.py         ← 빌드 실행
       │
       ├─────────────────────────────────────┐
       ▼                                     ▼
  dist/                               dist-legacy/
  (siheonlee.com 에 배포)              (lama.pe.kr 에 배포)
```

빌드가 실행되면 다음 순서로 처리됩니다:

| 단계 | 내용 |
|---|---|
| 1 | `site.yaml`, `legacy-map.yaml` 설정 읽기 |
| 2 | `Articles/` 트리를 뒤져 글 후보 수집 |
| 3 | 각 글의 `meta.yaml` 파싱 (제목, 날짜, SEO 설정 등) |
| 4 | 검증: slug 중복 없는지, 날짜 형식이 맞는지 등 확인. 문제 있으면 빌드 중단 |
| 5 | 각 글의 본문 렌더 → 템플릿에 끼워 넣어 `dist/{slug}/index.html` 생성 |
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
siheonlee.com_v0.1/
│
├── build.py              ← 빌드 스크립트 (이것을 실행합니다)
├── migrate.py            ← 기존 글 마이그레이션 스크립트 (§ 14)
├── site.yaml             ← 사이트 전역 설정
├── legacy-map.yaml       ← lama.pe.kr 구 URL → 신 slug 매핑표
│
├── Articles/             ← ★ 모든 글이 여기에 들어갑니다
│   ├── Blog/             ← 카테고리 폴더
│   │   ├── Hello World/  ← 글 폴더 (폴더명 = 화면에 표시되는 글 이름)
│   │   │   ├── meta.yaml    ← 글의 메타데이터 (slug, 제목, 날짜 등)
│   │   │   ├── content.md   ← 본문 (마크다운 형식)
│   │   │   └── imgs/        ← 이미지 등 첨부 파일 (선택)
│   │   └── ...
│   └── Project/
│       └── ...
│
├── templates/            ← 각 페이지 유형의 HTML 틀
│   ├── article.html      ← 글 페이지 틀
│   ├── category.html     ← 카테고리 목록 페이지 틀
│   ├── home.html         ← 홈 페이지 틀
│   └── 404.html          ← 404 에러 페이지 틀
│
├── assets/               ← 사이트 공용 파일 (CSS, JS, 파비콘 등)
│   ├── common_template.css
│   └── imgslidebox.js
│
├── dist/                 ← 빌드 산출물 (siheonlee.com 에 배포)
│   └── ...               ← build.py 가 자동 생성. 직접 수정 금지.
│
└── dist-legacy/          ← 빌드 산출물 (lama.pe.kr 에 배포)
    └── ...               ← build.py 가 자동 생성. 직접 수정 금지.
```

> **중요:** `dist/` 와 `dist-legacy/` 안의 파일은 `python build.py` 를 실행할 때마다 덮어씌워집니다. 이 폴더 안을 직접 수정하지 마세요. 수정이 필요하면 `Articles/`, `templates/`, `assets/`, `site.yaml` 을 고치고 다시 빌드하세요.

---

## 4. 빠른 시작 — 5분 안에 빌드해보기

### 준비물

- Python 3.x (3.8 이상 권장). 터미널에서 `python --version` 으로 확인.
- 다른 설치 필요 없음.

### 빌드 실행

이 폴더(`siheonlee.com_v0.1/`)에서 터미널을 열고:

```bash
python build.py
```

성공하면 다음과 같이 출력됩니다:

```
빌드 완료: 1 글, 1 카테고리, 0 경고.
산출물: dist/ (siheonlee.com), dist-legacy/ (lama.pe.kr).
```

### 결과 확인

빌드 후 `dist/` 폴더를 열면 다음 파일들이 생성됩니다:

- `dist/index.html` — 홈 페이지
- `dist/hello-world/index.html` — 샘플 글 페이지
- `dist/blog/index.html` — Blog 카테고리 목록
- `dist/404.html` — 에러 페이지
- `dist/robots.txt` — 검색엔진 크롤 정책

`dist/hello-world/index.html` 을 브라우저로 열면 샘플 글이 보입니다 (CSS/JS 경로가 절대 경로라 로컬에서는 스타일이 깨지지만, 서버에 올리면 정상입니다).

---

## 5. 글 작성하기

### 5-1. 글 폴더 만들기

글은 `Articles/` 안의 적당한 카테고리 폴더 아래에 **새 폴더를 만드는 것**으로 시작합니다.

```
Articles/
└── Blog/
    └── 나의 첫 글/        ← 이 폴더를 만듭니다
        ├── meta.yaml      ← 반드시 있어야 합니다
        └── content.md     ← 또는 content.html
```

**폴더명 규칙:**

- 한국어, 영어, 공백, 특수문자 모두 사용 가능합니다.
- 폴더명이 화면에 표시되는 글 이름(링크 텍스트)이 됩니다.
- 폴더명은 URL에 쓰이지 않습니다. URL은 `meta.yaml` 의 `slug` 가 결정합니다.

예시:
```
폴더명: "마스크 흡기구 3D 프린팅"   → 화면에는 "마스크 흡기구 3D 프린팅" 으로 표시
slug:  "mask-intake-3d-printing"   → URL: https://siheonlee.com/mask-intake-3d-printing/
```

### 5-2. meta.yaml 작성하기

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
```

#### slug — 가장 중요한 필드

`slug` 는 이 글의 **영구적인 식별자**이자 **URL** 입니다.

```
slug: my-first-post
→ URL: https://siheonlee.com/my-first-post/
```

**slug 규칙:**
- 영어 소문자, 숫자, 하이픈(`-`)만 허용합니다.
- 시작과 끝은 영숫자여야 합니다.
- 사이트 전체에서 **유일**해야 합니다. 같은 slug 가 두 글에 있으면 빌드가 중단됩니다.
- 카테고리와 무관합니다. 글을 다른 카테고리로 옮겨도 slug 가 같으면 URL이 바뀌지 않습니다.

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
slug: blog               ← 예약어 (site.yaml 의 reserved_slugs 목록 참조)
```

#### 전체 필드 설명

| 필드 | 필수 | 설명 | 예시 |
|---|---|---|---|
| `slug` | ✓ | URL 식별자. 사이트 전역 유일 | `mask-intake-3d-printing` |
| `title` | ✓ | 글 제목. `<h1>` 태그에 들어감 | `마스크 흡기구 3D 프린팅` |
| `date` | ✓ | 최초 발행일 (YYYY-MM-DD) | `2021-04-12` |
| `updated` | — | 마지막 수정일 (YYYY-MM-DD). `date` 이후여야 함 | `2025-08-30` |
| `seo_title_prefix` | — | `<title>` 앞에 붙는 문자열. 비면 site.yaml 기본값 사용 | `"[특집] "` |
| `seo_title_suffix` | — | `<title>` 뒤에 붙는 문자열. 빈 문자열(`""`)로 명시하면 suffix 없음 | `" - 내 블로그"` |
| `seo_description` | — | 검색엔진에 표시되는 설명. 비면 본문 첫 문단 자동 추출 | `"3D 프린터로 마스크 부품을 만든 기록"` |
| `seo_keywords` | — | 키워드 목록 | `[3D프린팅, 마스크, 메이커]` |
| `seo_author` | — | 저자명. 비면 site.yaml 의 `default_author` | `이시헌` |
| `seo_canonical` | — | 표준 URL 강제 지정. 비면 자동 생성 | `https://siheonlee.com/my-slug/` |
| `seo_og_image` | — | SNS 공유 시 표시되는 이미지. 비면 본문 첫 이미지 | `./imgs/thumb.jpg` |
| `seo_og_type` | — | OG 타입. 기본값 `article` | `article` |
| `seo_twitter_card` | — | 트위터 카드 타입. 기본값 `summary_large_image` | `summary_large_image` |

#### `<title>` 태그가 만들어지는 방식

기본 설정(`site.yaml` 의 `default_title_suffix: " | siheonlee"`)에서:

```
title: "마스크 흡기구 3D 프린팅"
→ <title>마스크 흡기구 3D 프린팅 | siheonlee</title>
```

suffix를 이 글에서만 바꾸고 싶으면:
```yaml
seo_title_suffix: " - 메이커 로그"
→ <title>마스크 흡기구 3D 프린팅 - 메이커 로그</title>
```

suffix를 완전히 없애고 싶으면:
```yaml
seo_title_suffix: ""
→ <title>마스크 흡기구 3D 프린팅</title>
```

`seo_title_suffix:` 를 아예 쓰지 않거나 `null` 이면 site.yaml 기본값을 사용합니다.

### 5-3. content.md 로 본문 쓰기

`content.md` 는 마크다운 형식으로 본문을 작성하는 파일입니다.

```markdown
# 글 제목 (h1 헤딩)

본문 첫 문단입니다. 빈 줄로 문단을 구분합니다.

두 번째 문단입니다.

## 소제목 (h2)

**굵은 글씨**, *이탤릭*, `인라인 코드` 를 사용할 수 있습니다.

### 이미지 첨부 (일반)

![이미지 설명](./imgs/photo.jpg)

### 이미지 첨부 (캡션 포함 — 이 시스템의 특별 문법)

![[이미지 설명]](./imgs/photo.jpg) {캡션 텍스트}
```

**지원하는 마크다운 문법:**

| 문법 | 결과 |
|---|---|
| `# 제목` ~ `###### 제목` | h1 ~ h6 헤딩 |
| `**굵게**` | **굵게** |
| `*이탤릭*` | *이탤릭* |
| `` `인라인 코드` `` | 코드 서식 (내용 자동 escape) |
| ` ```언어` ... ` ``` ` | 코드 블록 (내용 자동 escape) |
| `[링크 텍스트](URL)` | 링크 |
| `![alt](이미지경로)` | 이미지 |
| `![[alt]](이미지경로) {캡션}` | 캡션 있는 이미지 박스 (이 시스템 전용) |
| `> 인용` | 인용문 |
| `---` | 구분선 |
| `- 항목` | 순서 없는 목록 |
| `1. 항목` | 순서 있는 목록 |

> **HTML 직접 사용:** 마크다운 본문 안에 HTML 태그를 그냥 쓰면 그대로 통과됩니다. 필요하면 `<div>`, `<table>` 등을 직접 쓸 수 있습니다.

#### 이미지 경로 작성법

이미지 경로는 글 폴더를 기준으로 **상대 경로**로 씁니다.

```markdown
![photo](./imgs/photo.jpg)
![photo](imgs/photo.jpg)     ← ./ 생략도 가능
```

빌드하면 자동으로 절대 경로로 변환됩니다:

```html
<!-- 빌드 후 -->
<img src="/src/my-slug/imgs/photo.jpg" alt="photo">
```

외부 URL은 그대로 유지됩니다:

```markdown
![외부 이미지](https://example.com/image.jpg)  ← 변환 안 함
```

### 5-4. content.html 로 본문 쓰기

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

**중요:** `content.md` 와 `content.html` 이 동시에 있으면 빌드가 중단됩니다. 둘 중 하나만 사용하세요.

#### PHP 함수 자동 변환

기존 PHP 기반 글에서 사용하던 두 가지 함수를 자동으로 HTML로 변환합니다:

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

이 두 함수 외의 `<?php ... ?>` 코드는 그대로 보존됩니다. 이때 빌드는 해당 글을 `.html` 이 아닌 `.php` 확장자로 출력합니다 (§ PHP 자동 감지 참조).

### 5-5. 이미지/파일 첨부하기

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

`meta.yaml`, `content.md`, `content.html` 을 제외한 **모든 파일과 폴더**는 그대로 `dist/src/{slug}/` 로 복사됩니다.

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

---

## 6. 카테고리 시스템

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

이렇게 하면 `https://siheonlee.com/research-notes-kr/` 카테고리 URL이 생성됩니다.

> `_meta.yaml` 은 파일명이 `_`로 시작하지만, 카테고리 메타 파일로서 예외적으로 처리됩니다. 빌드에서 제외되지 않습니다.

### 카테고리 색인 페이지

카테고리마다 자동으로 목록 페이지가 생성됩니다:

- `dist/blog/index.html` — Blog 카테고리의 모든 글 목록
- `dist/blog/3d-printing/index.html` — 3D Printing 하위 카테고리의 글 목록

글이 없는 카테고리도 페이지는 생성되지만 빌드 경고가 출력됩니다.

---

## 7. 글 관리 — 비공개, 이동, 삭제

### 글 비공개 처리 — `_` 접두

파일이나 폴더 이름 앞에 `_` (언더스코어)를 붙이면 빌드에서 제외됩니다.

```bash
# 글 폴더 비공개
mv Articles/Blog/나의 첫 글  Articles/Blog/_나의 첫 글

# 또는 Git으로
git mv "Articles/Blog/나의 첫 글" "Articles/Blog/_나의 첫 글"
```

그 후 `python build.py` 를 실행하면:
- `dist/my-first-post/` 폴더가 자동으로 삭제됩니다.
- 카테고리·홈 목록에서 사라집니다.
- `lama.pe.kr` 디스패처는 영향받지 않습니다 (legacy-map.yaml 은 영구 고정).

**`_` 접두의 전파 규칙:** 경로의 어느 폴더든 `_`로 시작하면 그 아래 모든 파일도 제외됩니다.

```
Articles/_drafts/                 ← 이 아래 전체 제외
Articles/Blog/_old-article/       ← 이 글 제외
Articles/Blog/글/imgs/            ← 글 폴더 안 자원 전체 포함
Articles/Blog/글/_secret.jpg      ← 이 파일만 제외 (글 자체는 포함)
```

### 글 이동 (카테고리 변경)

글 폴더를 다른 카테고리로 이동해도 URL(`slug`)이 바뀌지 않습니다:

```bash
git mv "Articles/Blog/나의 첫 글" "Articles/Project/나의 첫 글"
python build.py
# /my-first-post/ URL은 그대로 유지됩니다
```

### 글 영구 삭제

```bash
rm -rf "Articles/Blog/나의 첫 글"
# 또는 선택적으로 legacy-map.yaml 의 해당 항목을 null 로 변경 (410 Gone 응답)
python build.py
# dist/my-first-post/ 가 자동으로 삭제됩니다
```

---

## 8. 빌드 명령어 레퍼런스

```bash
# 일반 빌드
python build.py

# dist/ 와 dist-legacy/ 를 완전히 지우고 새로 빌드
python build.py --clean
```

### 빌드 성공 예시

```
빌드 시작...
빌드 완료: 5 글, 3 카테고리, 0 경고.
산출물: dist/ (siheonlee.com), dist-legacy/ (lama.pe.kr).
```

### 빌드 경고 (계속 진행)

경고는 빌드를 중단하지 않고 표준 에러(`stderr`)로 출력됩니다:

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

---

## 9. 산출물 구조 — dist/ 와 dist-legacy/

빌드 후 생성되는 `dist/` 폴더의 구조입니다:

```
dist/
├── index.html                       ← 홈 페이지 (/)
├── 404.html                         ← 404 에러 페이지 (Apache가 라우팅)
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
│   ├── index.html
│   └── 3d-printing/
│       └── index.html
│
└── project/
    └── index.html
```

`dist-legacy/` 는 `lama.pe.kr` 전용입니다:

```
dist-legacy/
├── redirect.php    ← 구 URL을 siheonlee.com 의 새 URL로 301 리다이렉트
└── robots.txt      ← 검색엔진이 리다이렉트를 따라가도록 허용
```

---

## 10. URL 구조

| 페이지 | URL 형식 | 예시 |
|---|---|---|
| 홈 | `/` | `https://siheonlee.com/` |
| 글 | `/{slug}/` | `https://siheonlee.com/mask-intake-3d-printing/` |
| 카테고리 | `/{cat-slug}/` | `https://siheonlee.com/blog/` |
| 하위 카테고리 | `/{cat-slug}/{sub-slug}/` | `https://siheonlee.com/blog/3d-printing/` |
| 글 첨부파일 | `/src/{slug}/{경로}` | `https://siheonlee.com/src/mask-intake-3d-printing/imgs/photo.jpg` |
| 공용 자원 | `/assets/{파일명}` | `https://siheonlee.com/assets/common_template.css` |
| 404 | `/404.html` | Apache가 미존재 경로에 자동 응답 |

**모든 글·카테고리 URL은 슬래시(`/`)로 끝납니다.** 슬래시 없는 URL(`/my-slug`)로 접근하면 Apache가 자동으로 슬래시 있는 URL로 301 리다이렉트합니다.

**글 URL은 카테고리와 독립입니다.** 같은 이름의 카테고리가 있어도(`/blog/` 카테고리 존재), 글 slug 가 `blog` 가 아니라면 충돌이 없습니다. 단, slug 예약어(`blog`, `project` 등)로는 글 slug 를 만들 수 없습니다.

### PHP 자동 감지

빌드가 글 본문을 렌더링한 뒤, 결과 HTML에 `<?php` 또는 `<?=` 가 남아 있으면 해당 글을 `.php` 확장자로 출력합니다:

```
has_live_php = False  →  dist/my-slug/index.html
has_live_php = True   →  dist/my-slug/index.php
```

URL은 `/{slug}/` 로 동일하고, Apache의 `DirectoryIndex index.html index.php` 설정이 알아서 처리합니다.

---

## 11. 마크다운 문법 레퍼런스

### 헤딩

```markdown
# H1 제목
## H2 제목
### H3 제목
#### H4 제목
##### H5 제목
###### H6 제목
```

### 인라인 서식

```markdown
**굵게**
*이탤릭*
`인라인 코드`
```

### 링크와 이미지

```markdown
[링크 텍스트](https://example.com)
[내부 파일](./document.pdf)

![이미지 설명](./imgs/photo.jpg)
![외부 이미지](https://example.com/img.jpg)
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

### 코드 블록

````markdown
```python
def hello():
    print("Hello, World!")
```
````

코드 블록 안의 `<`, `>`, `&` 는 자동으로 HTML escape 됩니다. `<?php` 같은 코드를 코드 블록에 쓰면 PHP로 실행되지 않습니다.

### 목록

```markdown
- 항목 A
- 항목 B
  - 중첩 (미지원, 일반 목록으로 처리)

1. 첫 번째
2. 두 번째
3. 세 번째
```

### 인용

```markdown
> 인용 텍스트입니다.
> 여러 줄도 가능합니다.
```

### 구분선

```markdown
---
```

---

## 12. SEO 설정 레퍼런스

`meta.yaml` 의 SEO 필드를 모두 비워도 빌드는 정상 동작합니다. 빌드는 다음 순서로 폴백합니다:

| 출력 태그 | 1순위 | 2순위 | 3순위 |
|---|---|---|---|
| `<title>` | `{prefix}{title}{suffix}` (prefix/suffix는 meta→site 폴백) | — | (필수) |
| `meta description` | `seo_description` | 본문 첫 문단 (최대 150자) | 출력 생략 |
| `meta keywords` | `seo_keywords` | — | 출력 생략 |
| `meta author` | `seo_author` | `site.yaml 의 default_author` | 출력 생략 |
| `link canonical` | `seo_canonical` | 자동 생성 (`/{slug}/`) | — |
| `og:title` | `seo_og_title` | `<title>` 결과 | — |
| `og:description` | `seo_og_description` | `meta description` 결과 | 출력 생략 |
| `og:image` | `seo_og_image` | 본문 첫 `<img>` | `default_og_image` |
| `twitter:image` | `seo_twitter_image` | `og:image` 결과 | — |

**폴백 결과가 빈 문자열이면 해당 태그 자체를 출력하지 않습니다.** `<meta name="description" content="">` 같은 빈 태그는 절대 생성되지 않습니다.

---

## 13. 사이트 전역 설정 — site.yaml

`site.yaml` 은 사이트 전체에 적용되는 설정 파일입니다. 잘 변경할 일이 없지만, 사이트 정보가 바뀌면 여기를 수정합니다.

```yaml
# 도메인
domain: siheonlee.com
base_url: https://siheonlee.com

# 사이트 이름 (og:site_name 에 사용)
name: siheonlee.com

# 기본 저자 (meta.yaml 에서 seo_author 가 없으면 이 값 사용)
default_author: 이시헌

# SNS 공유 시 이미지가 없을 때 사용하는 기본 이미지 경로
default_og_image: /assets/default-og.png

# <title> 기본 서식
default_title_prefix: ""            # 빈 문자열 = prefix 없음
default_title_suffix: " | siheonlee"

# 저작권 표시
copyright_holder: 이시헌
copyright_year_start: 2020          # 푸터에 "2020–현재연도" 로 표시

# 글 slug 로 사용 금지된 예약어 목록
# (카테고리 최상위 slug 추가 시 여기에도 추가)
reserved_slugs:
  - src
  - assets
  - blog
  - project
  - research
  - study
  - about
  # ... 등

# 홈 페이지 글 목록에서 제외할 카테고리 (About 페이지 등)
home_excludes_categories: [About]

# meta description 자동 추출 시 최대 글자 수
description_truncate: 150
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

## 14. 기존 글 마이그레이션 — migrate.py

기존 `lama_website-main` 의 PHP 기반 글을 이 SSG 시스템으로 옮기는 **일회성 작업**을 돕는 스크립트입니다.

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
| `migrate-todo-slugs.txt` | slug 를 아직 채우지 않은 글 목록. 폴더명·제목·후보 slug 포함 |
| `migrate-todo-php.txt` | HTML 글 안의 PHP 함수 호출 목록. 시뮬레이트 또는 escape 결정 필요 |
| `migrate-todo-pre-php.txt` | `<pre>` 안에 raw `<?php` 가 있는 경우. escape 처리 권장 |
| `migrate-YYYYMMDD-HHMMSS.log` | 변환 작업 전체 로그 |

### 멱등성 (안전한 재실행)

`migrate.py` 는 재실행해도 안전합니다. `meta.yaml` 이 이미 있고 `data.json` 이 없는 글은 건드리지 않습니다 (스킵). 작업을 며칠에 나눠 해도 됩니다.

---

## 15. 배포하기

빌드 후 생성된 폴더를 서버에 올리면 됩니다.

### siheonlee.com (신규 도메인)

`dist/` 폴더의 내용을 서버의 DocumentRoot 에 업로드합니다:

```bash
# rsync 예시
rsync -avz --delete dist/ user@siheonlee.com:/var/www/siheonlee.com/

# FTP 클라이언트 (FileZilla 등)로 dist/ 내용 업로드
# Git push → CI/CD 자동화 (GitHub Actions 등)
```

### lama.pe.kr (구 도메인 — 리다이렉트 전용)

`dist-legacy/` 폴더의 내용을 서버에 **한 번만** 올립니다. 이후에는 수정할 일이 없습니다:

```bash
rsync -avz dist-legacy/ user@lama.pe.kr:/var/www/lama.pe.kr/
```

`dist-legacy/` 에는 두 파일만 있습니다:
- `redirect.php` — 모든 구 URL을 siheonlee.com 의 새 URL로 301 리다이렉트
- `robots.txt` — 검색엔진이 리다이렉트를 따라가게 허용

---

## 16. Apache 서버 설정

`dist/` 의 파일을 올리는 것만으로는 부족합니다. 서버에서 404 처리, 슬래시 리다이렉트 등이 제대로 동작하려면 Apache 설정을 한 번 등록해야 합니다.

> **이 설정은 한 번만 하면 됩니다.** 글을 추가하거나 삭제해도 서버 설정을 바꿀 필요가 없습니다.

이 시스템은 `.htaccess` 파일을 사용하지 않습니다. 모든 서버 규칙은 Apache 메인 설정(VirtualHost 또는 httpd.conf)에 등록합니다.

### siheonlee.com VirtualHost

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

### lama.pe.kr VirtualHost (리다이렉트 전용)

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

### 배포 검증 체크리스트

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

## 17. 트러블슈팅

### Q: 빌드는 성공했는데 페이지 CSS 가 깨져 보입니다.

빌드 산출물을 로컬에서 직접 열면(파일 더블클릭) CSS 경로(`/assets/...`)가 절대 경로라 로드되지 않습니다. 이는 정상입니다. 서버에 올리거나, 로컬에서 간단한 HTTP 서버를 통해 확인하세요:

```bash
# Python 내장 HTTP 서버 (dist/ 폴더에서 실행)
cd dist
python -m http.server 8000
# 브라우저에서 http://localhost:8000/ 접속
```

### Q: `slug 충돌` 오류가 납니다.

같은 slug 를 두 글에서 쓰고 있습니다. 오류 메시지에 나온 두 파일 중 하나의 slug 를 변경하세요.

### Q: 새 카테고리를 만들었는데 URL 이 이상합니다.

카테고리 폴더명에 영어가 없으면 slug 가 빈 문자열이 되어 빌드가 중단됩니다. 해당 카테고리 폴더 안에 `_meta.yaml` 을 만들고 slug 를 지정하세요 (§ 6 참조).

### Q: 이미지가 표시되지 않습니다.

1. 이미지 파일이 글 폴더 안에 있는지 확인하세요.
2. `content.md` 에서 경로를 글 폴더 기준 상대경로로 쓰셨나요? (`./imgs/photo.jpg` 형식)
3. 빌드 경고에 `missing asset` 이 나오지 않는지 확인하세요.
4. `dist/src/{slug}/imgs/` 안에 파일이 복사되어 있는지 확인하세요.

### Q: 기존 PHP 글인데 `.php` 확장자로 출력되지 않고 `.html` 로 나옵니다.

`content.html` 안에 처리되지 않은 `<?php` 가 남아 있어야 `.php` 로 출력됩니다. `imgBox`, `imgSlideBox` 는 빌드가 자동으로 HTML로 변환하기 때문에 그 결과에는 `<?php` 가 없어서 `.html` 로 출력됩니다. 실제로 서버에서 실행해야 하는 PHP 코드가 있어야 `.php` 로 출력됩니다.

### Q: `dist/` 를 지웠다 다시 빌드하고 싶습니다.

```bash
python build.py --clean
```

### Q: migrate.py 를 실행했더니 Articles/ 가 통째로 복사됐습니다.

정상입니다. `Articles.backup-YYYYMMDD-HHMMSS/` 라는 이름으로 자동 백업된 것입니다. 마이그레이션 중 실수가 있어도 복구할 수 있도록 보호장치로 만들어두는 폴더입니다.

---

## 18. 설계 원칙과 한계

### 설계 원칙

1. **URL 영구성** — 글의 URL은 카테고리 이동, 폴더명 변경과 무관하게 slug 가 바뀌지 않는 한 영구 유지됩니다. ("Cool URIs don't change")

2. **표시명과 URL slug 분리** — 화면에 보이는 이름은 한국어 폴더명, URL은 영문 ASCII slug 로 독립 관리됩니다.

3. **외부 의존성 0** — 새 환경에서 Python 3 만 있으면 빌드할 수 있습니다. 패키지 매니저나 빌드 툴체인이 필요 없습니다.

4. **서버 설정과 콘텐츠 분리** — `.htaccess` 가 없어 서버 설정과 콘텐츠가 완전히 분리됩니다. 글을 아무리 많이 추가해도 서버 설정을 건드릴 필요가 없습니다.

5. **빌드의 안전성** — 빌드 스크립트는 `Articles/` 를 **읽기만** 합니다. 소스 파일을 자동으로 수정하지 않습니다. migrate.py 만 파일을 수정합니다.

### 현재 버전(v0.1)의 한계

| 한계 | 내용 |
|---|---|
| 검색 없음 | 사이트 내 검색 기능이 없습니다. 후속 작업에서 별도 추가 예정. |
| 태그 없음 | meta.yaml 에 tags 필드가 없습니다. |
| 페이지네이션 없음 | 카테고리에 글이 많아지면 한 페이지에 전부 나열됩니다. |
| RSS 없음 | RSS/Atom 피드가 없습니다. |
| 표(table) 마크다운 미지원 | `| col | col |` 형식의 마크다운 표를 지원하지 않습니다. HTML 로 직접 쓰세요. |
| Apache 메인 설정 접근 필요 | 공유 호스팅에서 메인 설정 접근이 안 되면 호스팅 사업자에게 요청해야 합니다. |
| PHP 호스팅 전제 | 일부 글이 PHP로 출력될 수 있습니다. 정적 전용 호스팅(Cloudflare Pages 등)에서는 PHP 글이 텍스트로 노출됩니다. |

---

*이 문서는 siheonlee.com SSG v0.1 기준으로 작성되었습니다. (2026-05)*

# siheonlee.com v0.4.7 — 사용설명서 & 시스템 문서

> **이 문서는 처음 이 시스템을 접하는 사람을 위해 작성되었습니다.**
> 기술적인 사전 지식 없이도 읽을 수 있도록, 모든 개념을 처음 등장하는 시점에 설명합니다.

이 시스템은 **글마다 폴더 하나**를 만들어 본문과 첨부파일을 관리하고, `python build.py` 한 번으로 두 도메인 분량의 사이트를 만들어내는 **PHP 기반 경량 웹 사이트 생성기** 입니다.

> **v0.4.7 의 위치:** v0.4.6 까지의 변경 결과물을 점검해 *문서·코드의 정합성 갭만* 채운 안정화 버전. 회귀 0, dist 산출물은 v0.4.6 과 바이트 단위로 동일합니다. 차이는 (a) build.py 와 scripts/ 모듈 docstring 의 v0.4.x 버전 표기 일괄 갱신, (b) README §1·§3 의 폴더명 표기 (`siheonlee.com_v0.4.1/` → `siheonlee.com_v0.4.7/`), (c) §11 (site.yaml) 의 옛 `home_*` 키 예시 제거 + 설정 책임 분리표를 §11 본문으로 끌어올림, (d) §17 "한계 표" 를 v0.4.6 기준으로 전면 재작성 (v0.4.5 에서 해결된 항목 제거 + v0.4.5/v0.4.6 에서 새로 명시화된 한계 추가), (e) `_build_home` 의 카테고리 path 분기 dead branch 정리. 새 기능 / 출력 변화 / 동작 변화는 없습니다 — v0.5.0 의 큰 변경에 들어가기 전 마지막 점검.
>
> **v0.4.6 의 위치:** v0.4.5 의 페이지네이션 UX 와 카테고리 meta.yaml 스키마를 다듬은 점진 버전. 다섯 갈래 변경:
>
> 1. **페이지네이션 nav 여백 축소.** `.pagination-nav` 의 상단 padding 을 제거하고 음수 margin-top 으로 위 section 과 더 가깝게. 하단 padding 도 약간 축소. ([assets/common_template.css](assets/common_template.css))
> 2. **SSR 시점의 첫 페이지 상태 정적 생성.** v0.4.5 까지는 페이지 로드 직후 모든 항목이 잠깐 보였다가 JS 가 hide 하는 FOUC (Flash Of Unstyled Content) 가 있었습니다. v0.4.6 부터는 빌드 시 `data-per-page` 를 넘는 항목에 `style='display:none'` 을 inline 으로 부착해 둠. 페이지네이션 버튼은 SSR 단계에서 렌더되지만 클릭 핸들러는 [assets/pagination.js](assets/pagination.js) 가 나중에 부착합니다 — 표면적 변동 없음.
> 3. **`Articles/meta.yaml` 신설.** 메인페이지 (사이트 루트) 의 카테고리-격 설정 파일. 다른 카테고리 meta.yaml 과 동일 스키마. `per_page` 로 메인페이지 Recent posts 의 페이지당 글 수 오버라이드, `excludes_categories` 로 Recent posts 에서 제외할 톱레벨 카테고리 지정.
> 4. **`priority` 필드 신설.** 모든 카테고리 meta.yaml (`Articles/meta.yaml` 포함) 에 `priority: <정수>` 를 둘 수 있습니다. **값이 클수록 먼저** 등장. 같은 값끼리는 폴더명 알파벳 순. 0 을 포함한 임의의 정수 (1, 2, 100, 1000 등 자유). 적용 위치: (a) 부모 카테고리의 인덱스 페이지에 section 으로 임베드될 때의 순서, (b) 톱레벨 nav 링크의 순서 (About 은 그대로 최상단 고정).
> 5. **설정 일원화 — site.yaml = 전역만, meta.yaml = 각자 자기 페이지.** 옛 `site.yaml` 에 있던 메인페이지 전용 키 (`home_per_page` / `home_excludes_categories` / 빌더가 사용한 적 없는 `home_sort`) 를 모두 `Articles/meta.yaml` 로 이전. site.yaml 은 이제 진짜 전역 (사이트 메타, lang 디폴트, 카테고리 디폴트, SEO 폴백 등) 만 보유 — 페이지 한 종에만 적용되는 설정은 그 페이지의 meta.yaml 에 둔다는 규약이 모든 페이지(글/카테고리/홈)에 통일적으로 적용됩니다.
>
> **v0.4.5 의 위치:** 인덱스 페이지의 형식과 다국어 표현을 보강한 점진 버전. 다섯 갈래 변경이 한데 묶여 있습니다.
>
> 1. **페이지네이션.** 메인페이지 Recent / 카테고리 인덱스 (대분류·소분류) / 상위 카테고리에 임베드된 서브카테고리 section 마다 독립적인 페이지 컨트롤이 부착됩니다. 모든 항목은 서버에서 렌더되고 (SEO 친화), [assets/pagination.js](assets/pagination.js) 가 클라이언트에서 DOM 을 hide/show 합니다. 디자인은 사이트의 nav-search 입력과 톤을 맞춘 미니멀한 회색 회전 화살표 + 페이지 번호.
> 2. **다국어 지원.** 템플릿의 `<html lang='ko'>` 하드코딩 제거. site.yaml 의 `lang:` 이 사이트 전역 디폴트가 되고, 글 meta.yaml 의 `lang:` 으로 글마다, 카테고리 meta.yaml 의 `lang:` 으로 카테고리 인덱스마다 오버라이드 가능합니다.
> 3. **서브카테고리 인덱스 페이지.** v0.4.4 까지는 원본 lama.pe.kr quirk 를 보존해 톱레벨 카테고리만 자기 인덱스 페이지를 가졌습니다. v0.4.5 에서 서브카테고리도 자기 인덱스 페이지 (`/{top-slug}/{sub-slug}/`) 를 갖습니다. 톱레벨 페이지는 그대로 유지 (서브카테고리들이 section 으로 임베드되는 점도 그대로). sitemap.xml 도 서브카테고리 URL 을 포함합니다.
> 4. **카테고리 meta.yaml.** 각 카테고리 폴더 (대분류·소분류) 마다 `meta.yaml` 을 둘 수 있습니다 — 글의 meta.yaml 과 형식이 다릅니다 (slug/title/date 없음). 현재 지원 필드: `per_page` (이 카테고리의 자기 인덱스 페이지의 페이지당 글 수), `preview_per_page` (이 카테고리가 상위 카테고리의 인덱스 페이지에 section 으로 임베드될 때의 페이지당 글 수), `layout` (`list` 기본; 'gallery' 등 미래 확장 예정), `styles` (이 카테고리 인덱스 페이지에만 적용할 CSS), `lang`. 빌더는 폴더에 content.md / content.html 이 있으면 글, 없으면 카테고리로 구분합니다.
> 5. **비ASCII 폴더명 워닝 메시지 보강.** v0.4.0 부터 `Articles/` 의 한국어 폴더명은 자동으로 hex 코드포인트 slug 로 변환되었지만, 빌드 로그의 메시지가 다소 모호했습니다. v0.4.5 의 메시지는 *어떤 폴더가 어떤 slug 로 변환되었는지* 를 명시하고, ASCII rename 권장을 한 번 더 강조합니다.
>
> **v0.4.4 의 위치:** sitemap.xml 자동 생성. v0.4.0 의 전역 noindex 폐기로 글이 검색엔진에 색인되기 시작한 뒤, 검색엔진이 사이트 구조를 더 빠르고 정확하게 파악하도록 sitemap 을 제공합니다. [scripts/sitemap.py](scripts/sitemap.py) 가 글·톱레벨 카테고리·홈 URL 을 sitemaps.org 0.9 스키마로 빌드하고, robots.txt 의 `Sitemap:` 디렉티브가 더 이상 주석 처리되지 않습니다. meta.yaml 의 `noindex: true` 글은 sitemap 에서도 제외되며, lastmod 는 `updated` (없으면 `date`) 를 사용합니다. (v0.4.5: 서브카테고리 URL 도 포함.)
>
> **v0.4.3 의 위치:** 글 페이지의 `<title>` 정상화 + 마크다운 본문의 섹션 분할 문법 + meta.yaml 의 SEO 필드 그룹화. 세 변경의 공통 동기는 *글의 의미 단위 표현* 을 일관되게 만드는 것입니다.
>
> 1. **`<title>` = 글 제목.** v0.3.x ~ v0.4.2 에선 글마다 `<title>` 이 항상 `Lama` 로 고정되어 있었습니다 (원본 lama.pe.kr 의 quirk 보존). v0.4.0 에서 전역 noindex 가 풀려 글이 실제로 검색 결과에 뜨기 시작하면서 이 quirk 가 부적합해졌고, v0.4.3 에서 `<title>` 이 `{seo.title_prefix}{title}{seo.title_suffix}` 형태로 출력되도록 정상화했습니다.
> 2. **섹션 마커 문법.** 마크다운 본문 안에서 `===제목===` / `======` 라인으로 본문 구조를 명시적으로 나눌 수 있습니다. content.html (raw HTML) 로 글을 쓰면 `<div class='gap'><p>제목</p></div><section>...</section>` 패턴을 자유롭게 여러 번 둘 수 있는데, 마크다운에서는 그게 안 됐습니다 — 마크다운 글의 본문은 자동으로 한 번의 갭 + 한 번의 섹션으로만 wrap 되었기 때문입니다. v0.4.3 의 새 문법으로 이 비대칭이 해소됩니다.
> 3. **SEO 필드 그룹화.** meta.yaml 의 `seo_title_prefix`, `seo_description`, `seo_og_title` 등 12 개 평면 필드를 `seo:` 하위 블록으로 묶었습니다 (`styles:` 필드와 동일한 구조). 키 이름이 짧아지고 (`seo.description`, `seo.og_title`) frontmatter 가 한눈에 들어옵니다.
>
> **v0.4.2 의 위치:** v0.4.1 검토에서 드러난 여섯 가지 정합성 갭을 채운 점진 버전. 글 산출물의 바이트 단위 출력은 v0.4.1 과 동일했습니다 (회귀 0). 차이는 (a) slug ↔ 카테고리 slug 충돌의 명시 검증, (b) 레거시 redirect.php 의 도메인 하드코딩 제거, (c) search.php 의 noindex,follow, (d) imgBox/imgSlideBox 인자 파서의 nested parens 처리, (e) {{ROBOTS_META}} placeholder 들여쓰기 일반화, (f) README §15 하위 번호 보정.
>
> **v0.4.1 의 위치:** v0.4.0 의 "PHP 기반" 캐치프레이즈가 정당화된 PHP 사용처는 (1) 마크다운 파서 (Parsedown), (2) 검색 엔드포인트 (search.php), (3) 구 도메인 리다이렉트 (redirect.php) 셋이었습니다. v0.4.1 에서 (1) 이 **순수 Python** 으로 바뀌었습니다 (Parsedown.php 를 [scripts/parsedown.py](scripts/parsedown.py) 로 충실 포팅). 빌드 머신에는 더 이상 PHP 가 필요하지 않습니다. 런타임 PHP 의존성 (검색·리다이렉트) 은 여전히 남아 있으므로 캐치프레이즈는 그대로 유지합니다.

| 핵심 가치 | 어떻게 보장하는가 |
|---|---|
| **URL 영구성** — 한 번 발급한 URL 은 절대 깨지지 않는다 | 글 URL(`slug`) 은 카테고리·폴더명과 분리. 글을 옮기거나 폴더명을 바꿔도 URL 불변. |
| **운영 의존성 최소** — 빌드 환경은 Python 만, 런타임은 Apache+PHP 만 | Python 3 표준 라이브러리. `pip install` 없음, `composer` 없음, 클라이언트 JS 의존성 없음. (v0.4.1 부터 빌드 PHP 의존 제거) |
| **서버 설정과 콘텐츠 분리** — 글을 추가해도 서버를 안 건든다 | `.htaccess` 미사용. 모든 라우팅 규칙은 Apache VirtualHost 메인 설정에 한 번만 등록. |
| **두 도메인 동시 관리** — 신규 도메인과 구 도메인 리다이렉트를 한 번에 | 빌드 산출물이 `dist/`(siheonlee.com)와 `dist-legacy/`(lama.pe.kr 301 리다이렉트)로 분리됨. |
| **글마다 표현 제어** — 사이트 전역 CSS 와 별도로 글 단위 미세 조정 가능 | `meta.yaml` 의 `styles:` 필드로 본문 태그(p, h3, ul 등)의 CSS 속성을 글마다 독립적으로 override. |
| **글마다 색인 정책** (v0.4.0) — 전역으론 검색 가능, 필요시 개별 비공개 | 전역 `<meta robots noindex>` 폐지. 비공개로 두려는 글은 그 글의 `meta.yaml` 에 `noindex: true` 한 줄. |
| **사이트 내 검색** — 클라이언트 JS 없이 한국어 친화 부분검색 | 빌드 시 `dist/search-index.json` (한글 bigram + 영문 토큰 역색인) + `dist/search.php` 동시 생성. 카테고리 페이지 검색은 자동으로 해당 카테고리 내부로 한정. v0.4.0 부터 1글자 한국어는 인덱싱/쿼리 대상에서 제외, Python↔PHP 토크나이저 패리티를 빌드마다 자동 검증. |

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
12. [마크다운 파서 — Parsedown Python 포팅](#12-마크다운-파서--parsedown-174-python-포팅)
13. [검색 기능 — search.php](#13-검색-기능--searchphp)
14. [기존 글 마이그레이션 — scripts/migrate.py](#14-기존-글-마이그레이션--scriptsmigratepy)
15. [배포 — 서버 업로드와 Apache 설정](#15-배포--서버-업로드와-apache-설정)
16. [트러블슈팅](#16-트러블슈팅)
17. [설계 원칙과 한계](#17-설계-원칙과-한계)
18. [업데이트 로그](#18-업데이트-로그)

---

## 1. 빠른 시작

### 준비물

- **Python 3.x** (3.8 이상 권장). 터미널에서 `python --version` 으로 확인.
- **PHP CLI** (선택) — 빌드 시 search.php 의 토크나이저가 Python 토크나이저와 동등한지 자동 검증하는 데 사용됩니다. 없으면 패리티 검증만 워닝으로 건너뛰고 나머지 빌드는 정상 진행. (v0.4.0 까지는 마크다운 파싱에도 PHP 가 필수였지만 v0.4.1 부터는 마크다운도 순수 Python.)
- 그 외 패키지 설치 불필요.

### 빌드

이 폴더(`siheonlee.com_v0.4.7/`) 에서 터미널을 열고:

```bash
python build.py
```

성공하면 다음과 같이 출력됩니다 (실제 글 수/카테고리 수는 `Articles/` 트리에 따라 다름):

```
빌드 시작...
[search] tokenizer parity OK (18 fixtures)

빌드 완료: <N> 글, <M> 카테고리, 0 경고.
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

### 이 시스템은 무엇인가

**"PHP 기반 경량 웹 사이트 생성기"** 입니다. 글마다 폴더 하나를 만들어두면 `python build.py` 한 번으로 두 도메인 분량의 정적 HTML + PHP 엔드포인트 셋을 만들어내고, Apache 가 그걸 그대로 서빙합니다.

```
[기존 PHP 동적 사이트 (lama.pe.kr)]
방문자 요청 → 서버가 PHP 실행 → DB 조회 → HTML 생성 → 응답

[이 시스템 (siheonlee.com)]
운영자 빌드 → 정적 HTML 파일 + 검색 PHP + 리다이렉트 PHP 생성 → 서버 업로드
방문자 요청
   ├─ 일반 페이지       → Apache 가 정적 HTML 그대로 응답  (빠름)
   ├─ /search.php?q=… → PHP 가 인덱스 JSON 읽고 결과 HTML 렌더
   └─ lama.pe.kr/…    → PHP 가 legacy-map 보고 301 리다이렉트
```

### 이 시스템의 특징

- **운영 의존성 최소** — Python 3 표준 라이브러리 (빌드) + PHP (런타임). `pip install`/`composer install` 없음, 클라이언트 JS 의존성 없음. v0.4.1 부터 빌드 머신에는 PHP 가 필요하지 않음 (마크다운 파서를 Python 으로 포팅).
- **PHP 활용 범위 (v0.4.1)** — 런타임 검색 엔드포인트 (search.php), 구 도메인 리다이렉트 (redirect.php). 마크다운 파싱은 빌드 시점에 [scripts/parsedown.py](scripts/parsedown.py) (Parsedown 1.7.4 Python 포팅) 가 수행.
- **글 폴더 = 자율적인 단위** — 글마다 독립된 폴더에서 본문·이미지·보조파일을 자유롭게 관리.
- **URL 영구성 보장** — `slug` 가 곧 URL. 글을 다른 카테고리로 옮겨도 URL 이 안 바뀜.
- **글 단위 스타일 조정** — 본문의 p, h3, ul 등의 CSS 속성을 글마다 `meta.yaml` 에서 독립적으로 변경 가능.
- **글 단위 색인 제어** — 전역 noindex 없음. 검색엔진에서 빼고 싶은 글만 그 글의 `meta.yaml` 에 `noindex: true`.
- **두 도메인 동시 관리** — `siheonlee.com`(신규 도메인) 과 `lama.pe.kr`(구 도메인 → 301 리다이렉트) 를 한 번의 빌드로 처리.

### 전체 동작 원리

```
[작업 공간]
  Articles/               ← 글 원본 (마크다운 또는 HTML)
  templates/              ← 페이지 틀 (HTML 껍데기)
  assets/                 ← 사이트 공용 CSS, JS
  scripts/parsedown.py    ← 마크다운 파서 (Parsedown 1.7.4 Python 포팅)
  site.yaml               ← 사이트 전체 설정
  legacy-map.yaml         ← 구 URL 매핑표

       │
       ▼
  python build.py         ← 빌드 실행 (외부 의존성 없음)
       ├─────────────────────────────────────┐
       ▼                                     ▼
  dist/                               dist-legacy/
  (siheonlee.com 에 배포)              (lama.pe.kr 에 배포)
```

빌드는 다음 순서로 처리됩니다:

| 단계 | 내용 |
|---|---|
| 1 | `site.yaml`, `legacy-map.yaml` 읽기. (v0.4.1) 토크나이저 패리티 검증 — PHP CLI 가 있으면 자동 검증, 없으면 워닝 후 통과 |
| 2 | `Articles/` 트리를 뒤져 글 후보 수집 |
| 3 | 각 글의 `meta.yaml` 파싱 (제목, 날짜, SEO 설정, styles 등) |
| 4 | 검증: slug 중복 없는지, 날짜 형식이 맞는지 등 확인. 문제 있으면 빌드 중단 |
| 5 | 각 글의 본문 렌더 (.md 는 파서 호출, .html 은 그대로) → styles 블록 inject → 템플릿에 끼워 넣어 `dist/{slug}/index.html` 생성 |
| 6 | 글별 이미지/파일을 `dist/src/{slug}/` 로 복사 |
| 7 | 카테고리 색인 페이지 생성 |
| 8 | 홈 페이지 생성 |
| 9 | `assets/` → `dist/assets/` 복사 |
| 10 | 404 에러 페이지 생성 |
| 11 | `robots.txt` 생성 (Sitemap 디렉티브 포함, v0.4.4) |
| 12 | `sitemap.xml` 생성 (v0.4.4) |
| 13 | `dist-legacy/redirect.php` 생성 (구 URL 리다이렉트) |
| 14 | 검색 인덱스 + `search.php` 생성 |
| 15 | 이전 빌드에서 삭제된 글의 파일 정리 (고아 정리) |

---

## 3. 폴더 구조

```
siheonlee.com_v0.4.7/
│
├── build.py              ← 빌드 진입점 (이것을 실행합니다)
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
├── scripts/              ← build.py 의 내부 구현 모듈 (패키지)
│   ├── __init__.py
│   ├── yaml_parser.py        ← stdlib only YAML 부분 구현
│   ├── models.py             ← dataclass 정의
│   ├── slugs.py              ← 폴더명 → URL slug 변환
│   ├── parsedown.py          ← (v0.4.1) Parsedown 1.7.4 Python 포팅
│   ├── markdown.py           ← 본문 전·후처리 + PHP 함수 시뮬레이션 (Parsedown 호출)
│   ├── seo.py                ← <meta> 태그 빌더
│   ├── search.py             ← 토크나이저, 인덱스 빌드, Py↔PHP 패리티 테스트
│   ├── builder.py            ← 빌드 파이프라인 (Builder 클래스)
│   └── migrate.py            ← 기존 글 마이그레이션 (§ 14, 일회성)
│
├── templates/            ← 각 페이지 유형의 HTML 틀 + PHP 모듈
│   ├── article.html          ← 글 페이지 틀 ({{ROBOTS_META}}, {{ARTICLE_STYLES}} 등 변수 포함)
│   ├── category.html         ← 카테고리 목록 페이지 틀
│   ├── home.html             ← 홈 페이지 틀
│   ├── 404.html              ← 404 에러 페이지 틀
│   ├── search.php            ← 검색 결과 페이지 틀 (런타임 PHP)
│   └── search_tokenize.php   ← Python↔PHP 공통 토크나이저 (single source of truth)
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

> **v0.4.1 변경:** `parsers/parsedown/` (Parsedown.php + run.php) 디렉터리가 사라지고, 그 자리에 `scripts/parsedown.py` (Parsedown 1.7.4 Python 포팅) 가 추가됐습니다. 빌드 머신의 PHP 의존성이 제거되었습니다.

> **v0.4.0 모듈 분할:** 직전 버전 (v0.3.2) 까지 2000+ 줄짜리 단일 `build.py` 였던 것이 `scripts/` 패키지로 분할되었습니다. 루트의 `build.py` 는 진입점일 뿐이고, 모든 실제 로직은 `scripts/` 안에 거주합니다. 마이그레이션 스크립트도 `scripts/migrate.py` 로 옮겨졌습니다 (`python scripts/migrate.py` 로 실행).

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

# v0.4.0: 이 글만 검색엔진에서 빼고 싶을 때
noindex: true

# v0.4.3: SEO 관련 필드는 모두 `seo:` 하위 블록.
seo:
  title_prefix:
  title_suffix:
  description:
  author:
  canonical:
  og_title:
  og_description:
  og_image:
  og_image_alt:
  og_type: article
  twitter_card: summary_large_image
  twitter_image:

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
slug: search             ← 예약어 (site.yaml 의 reserved_slugs 참조)
```

#### 전체 필드 설명

| 필드 | 필수 | 설명 | 예시 |
|---|---|---|---|
| `slug` | ✓ | URL 식별자. 사이트 전역 유일 | `mask-intake-3d-printing` |
| `title` | ✓ | 글 제목. 본문 상단 갭 박스 + `<title>` 태그 양쪽에 사용 (v0.4.3) | `마스크 흡기구 3D 프린팅` |
| `date` | ✓ | 최초 발행일 (YYYY-MM-DD) | `2021-04-12` |
| `updated` | — | 마지막 수정일 (YYYY-MM-DD). `date` 이후여야 함 | `2025-08-30` |
| `noindex` (v0.4.0) | — | `true` 면 이 글 한 페이지만 `<meta robots noindex>` 부착 → 검색엔진 제외 | `true` |
| `seo:` (v0.4.3) | — | SEO 관련 필드의 그룹. 모든 하위 키 선택 사항. 아래 표 참조 | (아래 참조) |
| `styles` | — | 본문 태그의 CSS 속성을 이 글에서만 override (§ 4-6) | (아래 참조) |

**`seo:` 하위 키 (v0.4.3 — 모두 선택 사항):**

| 키 | 설명 | 예시 |
|---|---|---|
| `title_prefix` | `<title>` 앞에 붙는 문자열. 비면 site.yaml 의 `default_title_prefix` | `"[특집] "` |
| `title_suffix` | `<title>` 뒤에 붙는 문자열. 비면 site.yaml 의 `default_title_suffix` | `" - 내 블로그"` |
| `description` | 검색엔진에 표시되는 설명. 비면 본문 첫 문단 자동 추출 | `"3D 프린터로 만든 기록"` |
| `author` | 저자명. 비면 site.yaml 의 `default_author` | `이시헌` |
| `canonical` | 표준 URL 강제 지정. 비면 자동 생성 | `https://siheonlee.com/my-slug/` |
| `og_title` / `og_description` | OG 태그 override. 비면 글의 title/description 사용 | — |
| `og_image` | SNS 공유 시 표시되는 이미지. 비면 본문 첫 이미지 → site.default_og_image 폴백 | `./imgs/thumb.jpg` |
| `og_image_alt` | og:image 의 alt. 비면 글 title | — |
| `og_type` | OG 타입. 기본값 `article` | `article` |
| `twitter_card` | 트위터 카드 타입 | `summary_large_image` |
| `twitter_image` | 트위터 카드 이미지. 비면 og_image 사용 | — |

> **v0.4.2 → v0.4.3 마이그레이션:** 기존 글의 `seo_*` 평면 필드 (예: `seo_description: ...`) 를 `seo:` 블록 하위로 옮기면 됩니다. 키 이름에서 `seo_` 접두만 제거 (`seo_description` → `seo.description`). v0.4.3 은 평면 필드 폴백을 제공하지 않으므로 (즉 backward compat 없음) meta.yaml 을 직접 갱신해야 합니다.
>
> **v0.3.x 까지 있던 `seo_keywords` 필드는 v0.4.0 에서 폐기되었습니다.** `<meta name="keywords">` 는 1990년대 이래 주요 검색엔진이 무시하는 태그입니다.

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

마크다운 파서는 [scripts/parsedown.py](scripts/parsedown.py) (Parsedown 1.7.4 Python 포팅). 표·중첩 목록·자동 링크 등 표준 CommonMark 문법을 폭넓게 지원합니다. 자세한 문법은 § 9 참조.

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

#### 섹션 마커 (v0.4.3)

마크다운 본문을 여러 *섹션* 으로 나누어 각 섹션에 부제목을 다는 문법입니다. 빌드 결과 HTML 의 `<div class='gap'><p>부제목</p></div><section>...</section>` 패턴에 직접 대응합니다.

```markdown
도입부 문단. 이 부분은 본문 시작에 자동으로 들어가는
첫 갭 박스(글 제목) + 첫 섹션 안에 위치합니다.

===소개글===

이전 섹션이 자동으로 닫히고, 새 갭 박스("소개글") 와 새 섹션이 열립니다.

소개글 섹션의 두 번째 문단.

===주요 내용===

다시 새 섹션. `===제목===` 라인 하나로 이전 섹션 닫기 + 새 섹션 열기가
한 번에 일어납니다.

======

`======` (등호 정확히 6개) 라인은 현재 섹션을 명시적으로 닫습니다.
이 줄 다음의 본문은 어느 섹션에도 속하지 않습니다.
```

**문법 규칙:**

- `===텍스트===` (라인 단독): 이전 섹션 닫기 + 새 갭(텍스트) + 새 섹션 열기. 텍스트 안에 등호가 있으면 안 됨.
- `======` (라인 단독, 등호 정확히 6개): 현재 섹션을 명시적으로 닫기. 그 뒤에 또 새 섹션을 열려면 다음 줄에 `===새 제목===` 을 두면 됩니다.
- 코드 블록 (` ``` ` 또는 `~~~` 사이) 안에서는 매칭하지 않습니다 — 코드 예시 안에 `===` 가 등장해도 안전합니다.
- 마크다운 본문 시작 부분에는 항상 자동 첫 갭 (글 `title`) + 첫 섹션이 들어갑니다. 본문 안에 마커가 없는 글도 동일합니다.

**섹션 닫힘 — 짝맞춤은 빌더가 알아서 처리합니다:**

- **다음 `===새 제목===` 이 오면 자동 닫힘.** 직전 섹션이 열려 있는 상태에서 새 OPEN 마커가 등장하면 빌더가 먼저 `</section>` 을 출력한 뒤 새 갭+섹션을 엽니다. → 즉 본문 중간에서 *섹션을 단순 전환만* 하고 싶다면 `======` 없이 곧장 다음 `===새 제목===` 만 적어도 충분합니다.
- **본문 끝까지 안 닫혔으면 자동 닫힘.** 마지막 마커가 OPEN 이었거나 마커가 하나도 없었던 경우, 빌더가 본문 끝에 `</section>` 을 자동으로 붙입니다. → 닫힘 누락 걱정 없이 마크다운을 끝내도 됩니다.
- **명시적 `======` 은 "이 다음 본문은 어느 섹션에도 속하지 않게 두고 싶을 때" 만 필요.** 그렇지 않으면 굳이 적을 필요가 없습니다. ([Section Markers Demo](Articles/Blog/Section%20Markers%20Demo/content.md) 글 마지막의 단락 ([결과 HTML](dist/section-markers-demo/index.html)) 이 그 케이스입니다 — `======` 다음 단락이 `<section>` 밖의 `<p>` 로 출력됨.)

**왜 필요한가:** v0.4.2 까지는 마크다운 본문이 자동으로 단 한 번의 `<div gap><p>title</p></div><section>전체본문</section>` 으로만 wrap 되었습니다. `content.html` 로 작성된 글 (예: About 페이지) 은 갭+섹션 패턴을 본문 안에 여러 번 둘 수 있었지만, 마크다운에는 그 자유가 없었습니다. v0.4.3 의 마커는 이 비대칭을 해소합니다.

### 4-4. content.html 로 본문 쓰기

마크다운 대신 HTML 파일로 본문을 작성할 수 있습니다. 기존 HTML 글을 마이그레이션할 때 주로 사용합니다.

`content.html` 은 `<html>`, `<head>`, `<body>` 없이 본문 HTML 조각만 씁니다:

```html
<div class="gap">
    <p>첫 섹션 제목</p>
</div>
<section>
    <p>첫 문단입니다.</p>

    <div class="imgBox">
      <img src="./imgs/photo.jpg" alt="사진">
      <p class="caption">캡션 텍스트</p>
    </div>
</section>

<div class="gap">
    <p>다음 섹션 제목</p>
</div>
<section>
    <p>두 번째 섹션의 본문.</p>
</section>
```

> **중요 — 갭+섹션은 직접 작성해야 합니다.** `content.html` 은 작성한 HTML 이 본문에 **그대로** 들어갑니다. 마크다운 케이스에서 자동으로 박히던 `<div class='gap'><p>글 제목</p></div><section>...</section>` 의 자동 wrap 도, `===제목===` / `======` 섹션 마커도 작동하지 않습니다. 본문의 갭+섹션 패턴을 원하면 위 예시처럼 직접 적어야 합니다. meta.yaml 의 `title` 은 본문에는 사용되지 않고 `<title>` 태그·SEO 메타·검색 인덱스에만 사용됩니다.
>
> 실제 사용 예시: [Articles/About/content.html](Articles/About/content.html) — `About me` / `About this website` / `Contact` 세 갭+섹션이 모두 작성자가 직접 적은 것입니다.

> **content.md / content.html 동시 존재 금지:** 둘 다 있으면 빌드가 중단됩니다. 둘 중 하나만 사용하세요. `content.html` 은 마크다운 파서를 거치지 않으므로 파서 선택의 영향도 받지 않습니다.

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

변환 과정 (v0.4.0):
1. **비ASCII 문자 → hex 코드포인트**. 폴더명의 한국어/한자/일본어 등 각 문자를 4자리 lowercase hex 로 치환하고 `-` 를 붙입니다 (예: `블` → `be94-`, `로` → `b85c-`, `그` → `adf8-`).
2. NFKD 정규화.
3. 영문자, 숫자, 공백, 하이픈, 괄호만 남기고 나머지 제거.
4. 괄호 `()` 제거.
5. 공백과 연속 하이픈 → 단일 하이픈, 양 끝 하이픈 제거, 소문자 변환.

```
폴더명: 블로그             → slug: be94-b85c-adf8
폴더명: 연구 (Research)     → slug: c5f0-ad6c-research
폴더명: 01 - Side Project   → slug: 01-side-project
```

> **v0.4.5 변경:** 비ASCII 폴더명 워닝 메시지가 보강되었습니다. 어떤 폴더명이 어떤 slug 로 변환되었는지를 빌드 로그에 명시합니다 — 예: `[WARN] URL slug 에 비ASCII 문자 포함: '블로그' → 'be94-b85c-adf8'`. 결과 URL 이 사람이 읽기 어려운 형태가 되므로, URL 가독성/공유성을 위해 가능하면 ASCII 폴더명을 권장합니다.
>
> **v0.4.0 변경:** v0.3 까지 지원되던 카테고리별 **`_meta.yaml` 슬러그 오버라이드는 v0.4.0 에서 폐기**되었습니다. 한국어 폴더명도 결정론적으로 slug 가 생성되므로 오버라이드 메커니즘이 불필요해졌습니다. 기존에 `_meta.yaml` 을 두었던 카테고리는 오버라이드가 무시되고 자동 변환된 hex slug 가 적용됩니다 (URL 변경 가능 — 영향 받는 카테고리는 폴더명을 ASCII 로 바꾸어 안정된 slug 를 확보하는 것이 좋습니다).

### 카테고리 색인 페이지

**v0.4.5 부터 모든 카테고리 (대분류·소분류) 가 자기 인덱스 페이지를 생성합니다.**

- `dist/blog/index.html` — Blog 톱레벨 카테고리 (자식 서브카테고리들이 section 으로 임베드 + Blog 직속 글들 section).
- `dist/blog/3d-printing/index.html` — Blog/3D Printing 서브카테고리 (자기 글들만 표시).

톱레벨 페이지의 각 서브카테고리 section 우측 상단에는 `→` 화살표가 붙어, 클릭하면 해당 서브카테고리의 자기 페이지로 이동합니다.

> **v0.4.4 까지의 동작 (참고):** 원본 lama.pe.kr quirk 보존을 위해 톱레벨만 인덱스 페이지가 있었고, 서브카테고리 URL 은 404 였습니다. v0.4.5 에서 이 quirk 를 해제했습니다. sitemap.xml 도 서브카테고리 URL 을 포함합니다.

글이 없는 카테고리는 인덱스 페이지가 생성되지 않으며 빌드 경고가 출력됩니다.

### 카테고리 폴더의 meta.yaml (v0.4.5 신설)

각 카테고리 폴더 (대분류·소분류) 마다 `meta.yaml` 을 둘 수 있습니다. **글의 meta.yaml 과 형식이 다릅니다** (slug/title/date 없음).

```
Articles/
├── Blog/
│   ├── meta.yaml             ← Blog 톱레벨 카테고리 설정
│   ├── Tutorials/
│   │   ├── meta.yaml         ← Blog/Tutorials 서브카테고리 설정
│   │   └── Hello World/
│   │       ├── meta.yaml     ← 글 meta.yaml (slug/title/date 필수)
│   │       └── content.md
│   └── Some Article/
│       ├── meta.yaml
│       └── content.html
```

빌더는 `content.md` 나 `content.html` 의 존재 여부로 글 폴더와 카테고리 폴더를 구분합니다 — 둘 다 없으면 카테고리 폴더로 간주.

지원 필드 (모두 선택사항):

| 필드 | 기본값 | 설명 |
|---|---|---|
| `per_page` | site.yaml `category_per_page` (20) | 이 카테고리의 *자기 인덱스 페이지* 에서 한 페이지에 보여 줄 글 수. |
| `preview_per_page` | site.yaml `category_preview_per_page` (5) | 이 카테고리가 *상위 카테고리의 인덱스 페이지* 에 section 으로 임베드될 때의 페이지당 글 수. |
| `layout` | `list` | `list` 만 구현됨. `gallery` 등은 미래 확장용 자리표시. |
| `styles` | 빈 매핑 | 이 카테고리 인덱스 페이지에만 적용할 추가 CSS (글의 `styles:` 와 동일 포맷). |
| `lang` | site.yaml `lang` | 이 카테고리 인덱스 페이지의 `<html lang>` 오버라이드. |

`per_page > preview_per_page` 가 자연스러운 사용법입니다 — 소분류의 자기 페이지는 글을 더 많이 보여주고, 상위에 임베드된 section 은 미리보기 수준으로 적게 보여주는 정책.

**예시 (서브카테고리 meta.yaml):**

```yaml
per_page: 20         # /blog/tutorials/ 자기 페이지 — 페이지당 20개
preview_per_page: 5  # /blog/ 의 Tutorials section 임베드 시 — 페이지당 5개
layout: list
```

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
[search] tokenizer parity OK (18 fixtures)

빌드 완료: 5 글, 3 카테고리, 0 경고.
산출물: dist/ (siheonlee.com), dist-legacy/ (lama.pe.kr).
```

v0.4.1 부터 마크다운 파서는 [scripts/parsedown.py](scripts/parsedown.py) 하나만 사용되므로 별도 표기는 없습니다. (v0.4.0 까지의 `[markdown] using parser: parsedown` 줄은 사라졌습니다.)

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
| `slug 예약어` | `src`, `assets`, `search` 등 예약된 이름 | site.yaml 의 reserved_slugs 확인 후 변경 |
| `title is empty` | meta.yaml 의 title 비어 있음 | title 입력 |
| `date 형식 오류` | YYYY-MM-DD 형식이 아님 | 날짜 형식 수정 |
| `updated < date` | 수정일이 발행일보다 이전임 | 날짜 확인 후 수정 |
| `content.md and content.html both exist` | 본문 파일이 두 개 | 하나 삭제 |
| `non-ASCII folder name '...'` | 한국어/한자 등 비ASCII 카테고리 폴더 | (워닝) 자동으로 hex 코드포인트 slug 로 변환됨. 가독성 위해 ASCII 폴더명 권장 |

---

## 8. 산출물 구조와 URL

### dist/ 구조 (siheonlee.com 에 배포)

```
dist/
├── index.html                       ← 홈 페이지 (/)
├── 404.html                         ← 404 에러 페이지 (Apache 가 라우팅)
├── robots.txt                       ← 검색엔진 크롤 정책 (Sitemap 디렉티브 포함, v0.4.4)
├── sitemap.xml                      ← 사이트맵 (v0.4.4)
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
| robots.txt | `/robots.txt` | `https://siheonlee.com/robots.txt` (Sitemap 디렉티브 포함) |
| 사이트맵 (v0.4.4) | `/sitemap.xml` | `https://siheonlee.com/sitemap.xml` |

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

파서는 [scripts/parsedown.py](scripts/parsedown.py) 입니다 (Parsedown 1.7.4 의 Python 포팅; v0.4.1 부터). 표준 CommonMark 에 매우 가까운 문법을 지원합니다.

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

### 섹션 마커 — 이 시스템 전용 문법 (v0.4.3)

```markdown
도입부.

===섹션 제목===

섹션 본문.

===다음 섹션===

다음 섹션의 본문. 새 마커가 등장할 때마다 이전 섹션이 자동으로 닫히고
새 갭 박스 + 새 섹션이 열립니다.

======

현재 섹션을 명시적으로 닫습니다. 이 라인은 등호 6개로만 구성.
다음 본문은 어느 섹션에도 속하지 않습니다.
```

매칭 규칙:

- 시작 마커: `^===텍스트===$` (시작/끝 등호 3개, 텍스트 안에 등호 없음)
- 종료 마커: `^======$` (등호 정확히 6개)
- 코드 블록 (` ``` ` / `~~~`) 안의 같은 패턴은 무시.

자세한 동작은 § 4-3 "섹션 마커" 항목 참조.

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
| `<title>` | `{seo.title_prefix}{title}{seo.title_suffix}` (v0.4.3) | site.name 폴백 (full_title 이 빈 문자열일 때만) | — |
| `meta description` | `seo.description` | 본문 첫 문단 (최대 150자) | 출력 생략 |
| `meta author` | `seo.author` | `site.yaml 의 default_author` | 출력 생략 |
| `link canonical` | `seo.canonical` | 자동 생성 (`/{slug}/`) | — |
| `og:title` | `seo.og_title` | `<title>` 결과 | — |
| `og:description` | `seo.og_description` | `meta description` 결과 | 출력 생략 |
| `og:image` | `seo.og_image` | 본문 첫 `<img>` | `default_og_image` |
| `twitter:image` | `seo.twitter_image` | `og:image` 결과 | — |

**폴백 결과가 빈 문자열이면 해당 태그 자체를 출력하지 않습니다.** `<meta name="description" content="">` 같은 빈 태그는 절대 생성되지 않습니다.

> **v0.4.0 색인 정책:** 사이트 전체 페이지는 검색엔진 색인이 **기본 허용** 입니다. 글마다 `meta.yaml` 에 `noindex: true` 를 추가하면 그 한 페이지의 `<head>` 에만 `<meta name='robots' content='noindex'>` 가 들어가 검색엔진에서 빠집니다. 홈/카테고리/404/search 같은 전역 페이지에는 noindex 가 없습니다.
>
> v0.3.x 까지는 모든 페이지에 noindex 가 박혀 있어 위 SEO 폴백 체인이 출력만 되고 실효는 없는 dead code 였습니다. v0.4.0 부터는 실제로 검색 노출에 영향을 줍니다.
>
> **v0.4.3 변경:** 글 페이지의 `<title>` 이 이제 글의 `title` 을 정상 사용합니다. v0.3.x ~ v0.4.2 까지는 `<title>` 이 항상 site.name (`Lama`) 으로 고정되어 있었습니다 (원본 lama.pe.kr 보존 quirk). v0.4.0 에서 noindex 가 풀려 글이 검색 결과에 뜨기 시작하면서 이 quirk 가 부적합해졌고, v0.4.3 에서 정상화되었습니다.
>
> **v0.4.3 변경:** SEO 필드들이 `seo:` 하위 블록으로 그룹화되었습니다 (예: `seo_description` → `seo.description`). meta.yaml frontmatter 가 한눈에 보입니다.
>
> `<meta name="keywords">` 는 v0.4.0 에서 제거되었습니다 — 주요 검색엔진이 무시하는 태그입니다.
>
> **v0.4.4 변경:** [sitemap.xml](sitemap.xml) 자동 생성. 모든 non-noindex 글 + 톱레벨 카테고리 + 홈을 sitemaps.org 0.9 스키마로 출력합니다. lastmod 는 `updated` (없으면 `date`). robots.txt 의 `Sitemap:` 디렉티브가 자동 활성화되어 검색엔진이 sitemap 을 자동 발견합니다.

---

## 11. 사이트 전역 설정 — site.yaml

`site.yaml` 은 *진짜 전역* (= 여러 페이지에 공통 적용되는 설정) 만 둡니다. 잘 변경할 일이 없지만, 사이트 정보가 바뀌면 여기를 수정합니다.

### 11-1. 설정 책임 분리 (v0.4.6 의 규약)

**페이지 한 종에만 적용되는 설정은 site.yaml 에 두지 않고 그 페이지의 meta.yaml 에 둡니다.** 글·카테고리·홈 전체에 일관적으로 적용되는 원칙:

| 어디에 설정 두는가 | 어떤 설정 |
|---|---|
| `site.yaml` | 사이트 전역 (도메인, name, copyright, lang 디폴트, default_og_image 등) / 여러 페이지에 공통 적용되는 디폴트 (`category_per_page`, `category_preview_per_page`) / robots.txt 본문 / reserved_slugs / warn_on_* / `description_truncate` |
| `Articles/meta.yaml` (v0.4.6) | 메인페이지 (= 사이트 루트, 홈) 전용 — `per_page`, `excludes_categories`, `lang`, `layout`, `styles` |
| `Articles/<카테고리>/meta.yaml` (v0.4.5) | 그 카테고리 인덱스 페이지 전용 — `per_page`, `preview_per_page`, `priority` (v0.4.6), `lang`, `layout`, `styles` |
| `Articles/<카테고리>/<글>/meta.yaml` | 그 글 페이지 전용 — `slug`, `title`, `date`, `updated`, `noindex`, `lang`, `seo:`, `styles` |

> **v0.4.6 의 변경:** 옛 site.yaml 의 메인페이지 전용 키 3개 (`home_per_page` / `home_excludes_categories` / `home_sort`) 가 모두 `Articles/meta.yaml` 로 이전되었습니다 (`home_sort` 는 빌더가 사용한 적 없는 dead field 라 그대로 폐기). 옛 키를 site.yaml 에 그대로 두면 빌드는 진행되지만 무시되며 워닝이 출력됩니다.

### 11-2. site.yaml 예시 (v0.4.6 기준)

```yaml
# 도메인
domain: siheonlee.com
base_url: https://siheonlee.com

# 사이트 이름 (og:site_name 에 사용)
name: Lama
main_title: Lama

# 기본 저자 (meta.yaml 의 seo.author 가 없으면 이 값 사용)
default_author: 이시헌

# SNS 공유 시 이미지가 없을 때 사용하는 기본 이미지 경로
default_og_image: /assets/default-og.png

# v0.4.5: 다국어 — 모든 페이지 <html lang> 디폴트.
# 글 meta.yaml / 카테고리 meta.yaml / Articles/meta.yaml 의 `lang:` 으로 페이지별 오버라이드.
lang: ko

# <title> 기본 서식
default_title_prefix: ""
default_title_suffix: ""

# 저작권 표시
copyright_holder: 이시헌
copyright_year_start: 2025

# 글 slug 로 사용 금지된 예약어 목록 (v0.4.0 정리)
# 실제 디렉터리/엔드포인트와 충돌할 수 있는 항목만 유지.
reserved_slugs:
  - src       # /src/{slug}/ — 글 자원 디렉터리
  - assets    # /assets/    — 사이트 공용 자원 디렉터리
  - search    # /search.php — 검색 엔드포인트

# v0.4.5: 카테고리 페이지네이션 디폴트 (카테고리 폴더의 meta.yaml 로 오버라이드).
#   category_per_page         — 카테고리 인덱스가 자기 자신의 글 목록을 표시할 때
#   category_preview_per_page — 그 카테고리가 상위 카테고리 페이지에 section 으로 임베드될 때
# (메인페이지의 페이지당 글 수는 Articles/meta.yaml 의 per_page.)
category_per_page: 20
category_preview_per_page: 5

# meta description 자동 추출 시 최대 글자 수
description_truncate: 150

# 빌드 경고 옵션
warn_on_underscore_ref: true
warn_on_missing_asset: true
warn_on_stale_updated: true

# robots.txt 본문 (v0.4.4: Sitemap 디렉티브 자동 활성화)
robots_txt_main: |
  User-agent: *
  Allow: /

  Sitemap: https://siheonlee.com/sitemap.xml

robots_txt_legacy: |
  User-agent: *
  Allow: /

# v0.4.1: markdown_parser 옵션 폐지. 마크다운 파서는 단일 (scripts/parsedown.py)
# 로 통일되어 사이트 설정에서 선택할 필요가 없습니다. 기존 설정은 무시됩니다.
```

### 11-3. Articles/meta.yaml — 메인페이지 (= 홈) 전용 설정 (v0.4.6)

메인페이지 (사이트 루트) 의 카테고리-격 설정 파일입니다. 카테고리 폴더의 meta.yaml 과 동일 스키마 — 빌더는 이 둘을 같은 코드 경로 (`_parse_category_meta_file`) 로 파싱합니다. 단 일부 필드는 루트라는 위치 때문에 적용 대상이 없습니다.

```yaml
# 메인페이지 Recent posts 의 페이지당 글 수.
# 비우면 빌더의 코드 디폴트 (= Builder.HOME_PER_PAGE_DEFAULT, 현재 5).
per_page: 5

# Recent posts 에서 제외할 톱레벨 카테고리 폴더명 (리스트).
# 비우면 [] — 모든 톱레벨이 Recent 에 포함됨. About 처럼 글 목록에 섞여서는
# 안 되는 카테고리를 적어 두는 자리. (v0.4.5 까지는 site.yaml 의
# home_excludes_categories.)
excludes_categories: [About]

# 'list' (기본) / 'gallery' / 향후 확장. 현재 메인페이지는 'list' 만 지원.
layout: list

# 메인페이지의 <html lang> 오버라이드 (비우면 site.yaml 의 lang).
# lang: ko

# (참고용 — 루트는 상위가 없어 임베드되지 않음.)
# preview_per_page: 5

# (참고용 — 홈은 톱레벨들과 한 페이지에 함께 표시되지 않음.)
# priority: 0
```

**Articles/meta.yaml 은 선택 사항입니다.** 두지 않으면 코드 디폴트 (`per_page=5`, `excludes_categories=[]`) 가 사용됩니다.

### 11-4. 옛 reserved_slugs 정리 노트 (v0.3.x → v0.4.0)

v0.3.x 의 `reserved_slugs` 에는 카테고리 폴더명 변형 (`blog`, `project`, `research`, `study`) 과 잠재적 충돌 후보 (`c`, `p`, `api`, `file`, `status`) 가 함께 들어 있었지만, 실제로는 글 slug 와 카테고리 slug 가 서로 다른 네임스페이스에서 살아가므로 충돌할 수 없습니다 (글: `/{slug}/index.html`, 카테고리: `/{cat_slug}/index.html` — 같은 디렉터리에서 부딪히면 `slug 충돌` 검증이 따로 잡아냄). v0.4.0 에서는 실제로 실패할 수 있는 세 항목만 남기고 모두 제거했습니다.

새 최상위 카테고리를 만들 때 별도로 `reserved_slugs` 에 추가할 필요는 없습니다. 만약 글 slug 가 우연히 카테고리 slug 와 같다면 dist 산출물의 디렉터리 충돌이 발생하므로 build.py 의 검증 단계에서 명확히 실패합니다 (v0.4.2 부터).

---

## 12. 마크다운 파서 — Parsedown 1.7.4 Python 포팅

v0.4.1 부터 마크다운 파서는 단일 구현 [scripts/parsedown.py](scripts/parsedown.py) 만 사용합니다. v0.3 부터 v0.4.0 까지의 `MarkdownRenderer` 추상화 / `BuiltinRenderer` ↔ `ParsedownRenderer` 분기 / `site.yaml` 의 `markdown_parser:` 옵션은 모두 폐지되었습니다.

### 동작 구조

```
content.md
   │
   ▼
preprocess_md_custom_syntax()        ← 사용자 정의 문법 (![[...]] {...}) → HTML
   │
   ▼
Parsedown().text(text) → str         ← scripts/parsedown.py — Parsedown 1.7.4 Python 포팅
   │
   ▼
finalize_md_html()                   ← 후처리: asset 경로 재작성, PHP 시뮬레이션,
   │                                          first_paragraph/first_image 추출
   ▼
RenderResult(html, first_paragraph, first_image)
```

### 파서 원본과 라이센스

- 원본: [Parsedown](http://parsedown.org) 1.7.4, (c) Emanuil Rusev, MIT 라이센스.
- 포팅: [scripts/parsedown.py](scripts/parsedown.py) — 메서드명·블록/인라인 dispatch 구조·Block/Element dict 키 이름까지 원본 PHP 와 일대일 매핑되도록 작성. 외부 의존성 없음 (Python stdlib `re`, `typing` 만 사용).

### 출력 동등성 검증 (출시 시점)

v0.4.1 출시 시점에 PHP Parsedown 1.7.4 와 [scripts/parsedown.py](scripts/parsedown.py) 의 출력을 다음 두 corpus 로 바이트 단위 비교했습니다:

- 합성 fixture 46개 (헤더/단락/링크/이미지/표/코드블록/리스트/HTML/Korean/엣지케이스).
- `lama_website-main/Articles/` 의 실제 글 33편.

**총 79/79 fixture 가 PHP 출력과 바이트 단위로 일치**, 그리고 v0.4.0 의 `dist/` 와 v0.4.1 의 `dist/` 도 바이트 단위로 동일함을 확인했습니다.

검증에 사용한 일회성 스크립트는 v0.4.1 트리에 동봉하지 않습니다 — v0.4.1 만으로는 PHP 측 비교 대상 (Parsedown.php) 이 존재하지 않아 의미 있는 재실행이 불가능하기 때문입니다. 향후 Parsedown 1.8+ 동기화 등 재검증이 필요한 시점에 다시 작성하는 편이 환경 조건에 맞춰 더 깔끔합니다.

### PHP 와의 미묘한 차이 (포팅 시 주의)

PHP 와 Python 의 정규표현식 의미 차이로 인해, 같은 패턴을 그대로 옮기면 어긋나는 케이스가 있습니다. 포팅에서 처리한 주요 항목:

| 항목 | PHP | Python |
|---|---|---|
| `\w` (HTML 태그 이름) | ASCII 만 (no `/u`) | 기본은 Unicode — `re.ASCII` 플래그 필요 |
| `\b\s` (자동 URL 링크) | UTF-8 모드 (`/u`) | 기본 Unicode 와 동등 (플래그 없음 그대로 사용) |
| `(?R)` 재귀 매칭 (링크 텍스트의 중첩 `[ ]`) | PCRE 지원 | 수동 bracket matcher |
| `++` / `*+` possessive | PCRE 지원 | `+`/`*` 로 대체 (실제 입력에서 catastrophic backtracking 미발생) |
| `htmlspecialchars` single quote | `&#039;` | `_escape()` 가 동일하게 `&#039;` 출력 |

### Parsedown 업데이트

원본 Parsedown 이 새 버전을 내면 [scripts/parsedown.py](scripts/parsedown.py) 의 메서드를 직접 갱신해야 합니다. v0.4.0 의 "Parsedown.php 만 교체" 방식보다 비용이 높은 대신, 빌드 PHP 의존이 사라진 이득을 얻습니다. 포팅의 충실성을 유지하기 위해 메서드명·dispatch 구조·dict 키를 원본과 동일하게 두는 규칙을 지키세요.

---

## 13. 검색 기능 — search.php

사이트 내 글 검색을 제공합니다. 클라이언트 JS 0줄, 외부 검색엔진 의존도 0. 한국어/영어 혼용 본문에서 부분 일치까지 잡아내는 자체 역색인 + 서버측 PHP 검색 엔드포인트로 동작합니다.

### 동작 방식 한눈에

```
[빌드 시점 — Python]
  build.py 가 모든 글의 평문 본문을 토크나이즈 →
  dist/search-index.json (역색인) + dist/search.php + dist/search_tokenize.php 생성

[방문자 검색]
  사용자가 nav 우측 검색창에 입력 → form GET → /search.php?q=...
  PHP 가 search_tokenize.php 를 require_once 한 뒤 search-index.json 을
  메모리에 로드 → 쿼리를 같은 토크나이저로 쪼개 점수 합산 → 결과 페이지 렌더
```

### UI/UX (v0.4.0 정리)

- **노출 위치** — 홈 (`/`) 과 카테고리 인덱스 (`/blog/` 등) 페이지의 nav 우측 상단에만 표시. 개별 글, About, 404 에서는 노출하지 않음 (그곳에서 굳이 검색을 시작할 일이 없으므로).
- **미관 (v0.4.0)** — 배경색·테두리 없이 nav 의 회색 톤(#AFAFAF)에 녹아드는 placeholder "검색" 만 보이고, 클릭(focus) 시 가로로 부드럽게 확장 + 텍스트가 짙어지며 입력 가능 상태가 됨. lama 의 미니멀 톤을 깨지 않도록 의도된 디자인.
    - v0.3.2 까지 사용하던 italic placeholder 를 v0.4.0 에서 제거. faux italic skew 가 컨텐츠 박스를 넘쳐 발생하던 우측 클리핑 문제도 함께 사라졌고, 그래서 비대칭 padding (좌 0.2em / 우 0.6em) 도 단순한 0.3em 좌우 동일로 정리됨.
- **모든 뷰포트에서 노출** — 모바일 (≤600px) 포함. 좁은 폭에서는 시작/확장 폭만 줄어듦.
- **검색 결과 페이지 (`/search.php?q=...`)** — 기존 글 목록 (`listup_module_div`) 과 동일 마크업으로 결과를 표시. 각 결과 아래에 매치 위치 ±40 글자 스니펫. 매치된 부분은 `<mark>` (배경 #fff3cd) 로 강조.

### 검색 범위 — 카테고리 스코핑

| 검색 시작 위치 | 보내는 파라미터 | 검색 대상 |
|---|---|---|
| 홈 페이지 (`/`) | `?q=...` | **전체 글** |
| 카테고리 인덱스 (`/blog/` 등) | `?q=...&cat=blog` | 해당 톱레벨 카테고리 내부의 글만 |

- 카테고리 페이지의 nav-search 폼이 hidden `<input name='cat' value='<카테고리 slug>'>` 를 자동 포함합니다.
- 결과 헤더는 검색 범위를 명시합니다:
    - 전체 검색 — `검색결과: N건 — 전체에서 검색`
    - 스코프 검색 — `검색결과: N건 — Blog 카테고리에서 검색 (전체에서 검색)` (괄호 안 링크는 같은 쿼리를 전체로 토글)
- search.php 는 cat 값을 인덱스에 등록된 카테고리 slug 목록으로 화이트리스트 검증합니다 (잘못된 cat 은 전체 검색으로 폴백).

### 토크나이저 — 한국어 친화 bigram (v0.4.0 규칙)

```
입력:  "Hello 마스크 3D프린팅"
토큰:  ['hello', '3d', '마스', '스크', '프린', '린팅']

입력:  "한"            (한 글자 한국어)
토큰:  []              ← v0.4.0: 1글자 한국어는 인덱싱/쿼리 제외
```

- 영문/숫자 → 단어 단위 (lowercase). 정확 매치.
- 한글 → 음절 2-gram. **(v0.4.0) 길이가 1 인 한국어 시퀀스는 제외.**
- 그 외 문자 → 토큰 분리자.

bigram 인덱스이므로 **부분 검색이 자연스럽게 됩니다.** "프린" 만 입력해도 "프린팅", "프린터", "프린트" 모두 매치. 영어는 정확 단어 매치.

> **v0.4.0 의 1글자 한국어 제외 이유:** v0.3.x 까지는 한 글자 시퀀스 ("그", "에", "는" 등 조사·접속사) 가 그대로 토큰이 되어, 본문 거의 모든 글에 매치하는 노이즈 토큰이 인덱스에 쌓였습니다. 검색 측면에서도 "한 글자 쿼리" 는 의미 있는 결과를 거의 만들지 못합니다. v0.4.0 부터는 2글자 이상의 시퀀스만 bigram 토큰을 만들고, 1글자 쿼리는 빈 토큰 셋으로 자연스럽게 "결과 없음" 이 됩니다.

### Python ↔ PHP 토크나이저 일관성 — 빌드마다 자동 검증

토크나이저는 **단일 진실원 (single source of truth) 원칙** 으로 관리됩니다.

- **Python 측**: [scripts/search.py](scripts/search.py) 의 `search_tokenize()`.
- **PHP 측**: [templates/search_tokenize.php](templates/search_tokenize.php) — 빌드 시 `dist/search_tokenize.php` 로 복사되고 `dist/search.php` 가 `require_once` 합니다.

build.py 가 매 빌드의 `[1] _load_config` 단계에서 **18개 fixture 입력** 에 대해 두 토크나이저의 출력을 직접 비교합니다. 한 자라도 어긋나면 build 가 즉시 실패합니다:

```
$ python build.py
빌드 시작...
[search] tokenizer parity OK (18 fixtures)
```

fixture 셋은 다음 시나리오를 커버합니다 (자세한 목록은 `scripts/search.py` 의 `PARITY_FIXTURES`):

- 영문 단어, 숫자, 영숫자 혼합
- 한글 1글자 (토큰 0개 — v0.4.0 규칙 확인)
- 한글 2글자, 3글자 (bigram 1개, 2개)
- 영문+한글 혼합
- 구두점, 특수문자 (분리자 동작)
- 빈 문자열, 좌/우 공백, 대문자 정규화
- 한자, 일본어 (가-힣 범위 밖 — 토큰 0개)

PHP 가 PATH 에 없으면 패리티 테스트는 워닝 후 건너뜁니다 (`PHP not available — skipping tokenizer parity test.`).

| 패턴 | Python (`scripts/search.py`) | PHP (`templates/search_tokenize.php`) |
|---|---|---|
| 영문/숫자 | `[a-z0-9]+` | `[a-z0-9]+` |
| 한글 | `[가-힣]+` | `[\x{AC00}-\x{D7A3}]+` (= 같은 범위) |
| 소문자화 | `text.lower()` | `mb_strtolower($text, 'UTF-8')` |
| 한국어 길이 | `if len(word) < 2: continue` | `if ($len < 2) continue;` |

### 인덱스 포맷 (v2)

[dist/search-index.json](dist/search-index.json) 파일 (빌드 산출물):

```json
{
  "version": 2,
  "docs": [
    {"slug":"hello-world","title":"Hello, World!","date":"2026-05-07",
     "category":"Blog","category_slug":"blog","body":"평문 본문 전체..."}
  ],
  "categories":  {"blog": "Blog"},
  "index":       {"마스": [[0, 3]], "프린": [[0, 1]], ...},
  "title_index": {"hello": [[0, 1]], ...}
}
```

- `docs[doc_id]` — 표시용 메타데이터 + 스니펫 추출용 평문. v0.3.2 부터 `category_slug` 추가 (스코프 필터링 키). **v0.4.0 부터 body 길이 절단 폐지 — 글 본문 평문 전체가 저장됩니다.**
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
- 검색 결과 페이지에도 v0.3.x 까지는 `<meta name='robots' content='noindex'>` 가 있었으나, v0.4.0 의 "전역 noindex 제거" 정책에 따라 함께 제거되었습니다 (search.php 도 전역 템플릿이므로). 검색 결과 페이지가 외부 검색엔진에 색인될 가능성은 있지만, URL 파라미터 노이즈 패턴 때문에 실제 노출은 극히 낮습니다. 다시 막고 싶다면 templates/search.php 의 `<head>` 에 noindex 한 줄을 직접 추가하세요.

### 빌드 산출물

```
dist/
├── search.php             ← 검색 엔드포인트 (PHP)
├── search_tokenize.php    ← 토크나이저 함수 (v0.4.0; search.php 가 require_once)
├── search-index.json      ← 검색 인덱스 (Python 이 생성)
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

## 14. 기존 글 마이그레이션 — scripts/migrate.py

기존 `lama_website-main` 의 PHP 기반 글을 이 시스템으로 옮기는 **일회성 작업** 을 돕는 스크립트입니다. v0.4.0 부터 `scripts/migrate.py` 로 이동했습니다.

### 마이그레이션 흐름

```
1. python scripts/migrate.py
   → 각 글의 data.json을 읽어 meta.yaml 스캐폴드 생성
   → legacy-map.yaml 초안 생성
   → todo 파일 생성 (어떤 작업이 남았는지 안내)

2. (수동) todo 파일 보면서:
   - 각 글의 meta.yaml 에 slug 채우기
   - legacy-map.yaml 에 slug 채우기
   - HTML 글의 PHP 호출 검토

3. python scripts/migrate.py --check
   → 빌드 가능 여부 확인. 문제가 없을 때까지 2-3 반복

4. python build.py
```

### 명령어 (프로젝트 루트에서)

```bash
# 1차 변환 (Articles.backup-YYYYMMDD-HHMMSS/ 자동 백업 포함)
python scripts/migrate.py

# 검증 모드 (파일 수정 없음, 현재 상태만 평가)
python scripts/migrate.py --check

# 시뮬레이트 (파일 수정 없이 무엇을 할지만 출력)
python scripts/migrate.py --dry-run
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

### 15-1. siheonlee.com (신규 도메인)

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

### 15-2. lama.pe.kr (구 도메인 — 리다이렉트 전용)

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

### 15-3. 빌드 머신 vs 배포 서버의 PHP

> **(v0.4.1)** 빌드 머신에는 PHP 가 필요하지 않습니다. 마크다운 파서가 순수 Python 으로 포팅되었기 때문입니다. PHP CLI 가 있으면 빌드 시 토크나이저 패리티 검증이 자동 실행되고, 없으면 워닝과 함께 검증을 건너뜁니다.
>
> **배포 서버** 는 v0.4.0 과 동일하게 PHP 모듈이 필요합니다 — 검색 엔드포인트 (`search.php`) 와 구 도메인 리다이렉트 (`dist-legacy/redirect.php`) 가 런타임 PHP 를 사용하기 때문입니다. 또한 글에 처리되지 않은 `<?php` 가 남아 `.php` 로 출력되는 경우도 배포 서버 PHP 가 필요합니다.

### 15-4. 배포 검증 체크리스트

배포 후 다음을 확인하세요:

```bash
curl -I https://siheonlee.com/                    # 200 OK
curl -I https://siheonlee.com/hello-world         # 301 → /hello-world/
curl -I https://siheonlee.com/hello-world/        # 200 OK
curl -I https://siheonlee.com/없는페이지/           # 404 (본문은 /404.html)
curl -I https://siheonlee.com/robots.txt          # 200 OK, text/plain
curl -I https://siheonlee.com/sitemap.xml         # 200 OK, application/xml (v0.4.4)

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

### Q: PHP 가 없는 환경에서 빌드가 가능한가요?

**v0.4.1 부터 가능합니다.** 마크다운 파서가 순수 Python ([scripts/parsedown.py](scripts/parsedown.py)) 으로 바뀌어서, 빌드 머신에는 Python 3 만 있으면 됩니다. PHP CLI 가 있으면 빌드 시 토크나이저 패리티 검증을 자동 실행하고, 없으면 다음과 같은 워닝과 함께 검증만 건너뜁니다:

```
[WARN] PHP not available — skipping tokenizer parity test.
```

배포 서버에는 여전히 PHP 가 필요합니다 (search.php, redirect.php 가 런타임 PHP). 자세한 내용은 § 14-3 참조.

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

### Q: 새 카테고리를 만들었는데 URL 이 이상합니다 (예: `/be94-b85c-adf8/`).

v0.4.0 부터 한국어 등 비ASCII 폴더명은 각 문자의 hex 코드포인트로 자동 변환됩니다 (`블로그` → `be94-b85c-adf8`). 사람이 읽기 어려운 URL 이 만들어지므로, 카테고리 폴더명은 가능하면 ASCII 로 작성하세요 (`블로그` 대신 `Blog`). 빌드 시 워닝이 출력됩니다.

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

3. **운영 의존성 명시** — 빌드는 Python 3 만, 런타임은 PHP (검색·리다이렉트). `pip install`/`composer install`/클라이언트 JS 의존성은 없음. v0.4.0 부터 "외부 의존성 0" 이 아니라 "두 런타임 명시" 로 솔직히 표기하기 시작했고, v0.4.1 에서 빌드 PHP 의존이 제거되어 명시 대상이 더 줄었음.

4. **서버 설정과 콘텐츠 분리** — `.htaccess` 가 없어 서버 설정과 콘텐츠가 완전히 분리. 글을 아무리 많이 추가해도 서버 설정을 건드릴 필요가 없음.

5. **빌드의 안전성** — 빌드 스크립트는 `Articles/` 를 **읽기만** 함. 소스 파일을 자동으로 수정하지 않음. migrate.py 만 파일을 수정.

6. **파서 단일화 (v0.4.1)** — v0.3 ~ v0.4.0 의 추상화 (MarkdownRenderer + builtin/parsedown 분기) 가 폐지되고, 마크다운 파서는 [scripts/parsedown.py](scripts/parsedown.py) (Parsedown 1.7.4 Python 포팅) 하나로 통일. 다중 파서 인터페이스는 실제 필요가 없었다는 v0.4.0 회고의 결과.

7. **글 단위 표현 제어** — 사이트 전역 CSS 와는 별도로, 글마다 독립적인 표현 결정을 meta.yaml 에서 선언적으로 관리.

8. **글 단위 색인 정책 (v0.4.0)** — 기본은 모든 페이지 색인 허용. 비공개로 두고 싶은 글만 그 글의 meta.yaml 에 `noindex: true` 한 줄.

9. **단일 진실원의 토크나이저 (v0.4.0)** — Python/PHP 양쪽 토크나이저의 동등성을 빌드마다 fixture 패리티 테스트로 자동 검증.

### 현재 버전(v0.4.6) 의 한계

> v0.4.5 에서 페이지네이션 / 다국어 / 서브카테고리 인덱스 세 한계가 해소되었고, v0.4.6 에서 설정 책임 분리·페이지네이션 SSR 안정화가 들어갔습니다. 아래 표는 v0.4.7 시점에 여전히 유효한 한계만 모았습니다.

| 한계 | 내용 |
|---|---|
| 태그 없음 | meta.yaml 에 tags 필드가 없습니다. 분류 축은 카테고리 하나뿐. |
| RSS 없음 | RSS/Atom 피드가 없습니다. (sitemap.xml 은 v0.4.4 부터 자동 생성 — § 18 의 v0.4.4 참조.) |
| layout 은 `list` 만 구현 (v0.4.5) | 카테고리/홈 meta.yaml 의 `layout:` 필드는 `list` 외의 값 (`gallery` 등) 이 와도 빌드는 통과하되 'list' 로 폴백합니다. 갤러리·카드 등 다른 레이아웃은 미래 의제. |
| JS 비활성화 시 페이지 2+ 미표시 (v0.4.6) | 페이지네이션이 부착된 section 의 비활성 페이지 항목은 SSR 시점에 inline `style='display:none'` 으로 부착됩니다 (FOUC 제거 목적). 그래서 JS 가 비활성화된 환경에서는 첫 페이지만 보이고 페이지 2 이후 항목은 표시되지 않습니다. 콘텐츠 자체는 글 URL 직접 접근으로 접근 가능. `<noscript>` fallback 은 별도 의제. |
| `<head>` 의 `<title>` 폴백 체인이 글에만 적용 (v0.4.3) | 글 페이지는 `{seo.title_prefix}{title}{seo.title_suffix}` 로 정상 출력되지만, 홈·카테고리·404·search 페이지는 모두 `site.name` 한 값 — 페이지마다 다른 `<title>` 이 필요하면 템플릿에 변수를 추가해야 함. |
| description 폴백이 본문 전체에서 첫 `<p>` 검색 | `_FIRST_P_RE` 가 본문 첫 `<p>` 를 찾는데, 빌더가 본문을 `<div class='gap'><p>제목</p></div>` + `<section>…</section>` 로 감싸므로 결과적으로 갭 박스 안의 글 제목이 description 으로 빨릴 수 있습니다. `seo.description` 을 명시하면 덮어쓰이지만 폴백 시 SEO 신뢰도 손해 — v0.5.0 의제. |
| description_truncate 가 단어 경계 무시 | 150자 절단이 영어 단어 중간을 자를 수 있음. 한국어/영어 혼용이라 영향은 작지만 SEO 디테일 — v0.5.0 의제. |
| styles 의 @-rule 미지원 | `@media`, `@keyframes`, `@font-face`, `@supports`, `@import` 등 모든 at-rule 은 inject 안 됨 — [scripts/markdown.py](scripts/markdown.py) 의 `render_article_styles` 가 평면 `selector { decls }` 규칙만 직렬화. content.html 의 인라인 `<style>` 로 회피. |
| 이미지 자동 최적화 없음 | assets/ 와 글 첨부 이미지는 빌드가 그대로 복사. webp 변환·리사이즈·`loading="lazy"` 자동화 없음. 필요하면 글마다 직접 작성. |
| 글/카테고리 slug ASCII 만 허용 | 글 slug 정규식은 `^[a-z0-9][a-z0-9-]*[a-z0-9]$` (영소문자·숫자·하이픈). 카테고리 폴더가 한국어 등 비ASCII 면 hex 코드포인트로 자동 변환 + 워닝 (`블로그` → `/be94-b85c-adf8/`). 가독성 위해 ASCII 폴더명 권장. |
| 카테고리 meta.yaml 의 일부 필드는 위치별로 적용 대상 다름 (v0.4.5/v0.4.6) | `preview_per_page` 는 톱레벨 카테고리에는 사실상 의미 없음 (상위가 없으므로). `priority` / `preview_per_page` 는 `Articles/meta.yaml` (홈) 에선 적용 대상 없음. 같은 스키마를 두 위치가 공유하기 위한 의도된 비대칭이며 잘못된 값을 넣어도 빌드는 통과. |
| 톱레벨 nav 의 `About` 정렬 고정 (v0.4.6) | 톱레벨 nav 링크는 `About` 이 최상단 고정이고, 나머지는 (priority 내림차순, folder_name 오름차순) 입니다. About 의 위치를 priority 로 조절할 수 없음 — 원본 lama 의 nav 동선 보존이 의도. |
| Apache 메인 설정 접근 필요 | `.htaccess` 가 없는 게 설계 의도이므로 공유 호스팅에서 메인 설정 접근이 안 되면 호스팅 사업자에게 요청해야 함. |
| 배포 서버 PHP 전제 | 검색·리다이렉트가 PHP — 배포 서버에 PHP 7.4+ 와 mbstring 확장 필요 (§ 15-3). v0.4.1 부터 *빌드 머신* 의 PHP 의존은 사라져 PHP 부재 시 토크나이저 패리티 검증만 자동으로 건너뜀. |
| Parsedown 업데이트 비용 | 원본 Parsedown 신버전이 나오면 [scripts/parsedown.py](scripts/parsedown.py) 의 해당 메서드를 수동 동기화해야 함 — v0.3.x ~ v0.4.0 의 "Parsedown.php 만 교체" 보다 비용 증가. |
| YAML 파서 자체 구현 | [scripts/yaml_parser.py](scripts/yaml_parser.py) 는 이 프로젝트에서 실제 쓰는 문법 부분집합만 지원 — anchor/alias (`&`/`*`), folded scalar (`>`), flow-style mapping (`{...}`), 인라인 주석 (`key: val # comment` 의 주석이 value 로 빨려 들어감) 등은 미지원. PyYAML 도입 검토는 v0.4.1 단계에서 보류 — v0.5.0 재검토 의제. |
| 빌드 증분 캐싱 없음 | 매 빌드마다 전체 글 재렌더 + 검색 인덱스 재구축. 글 자원만 mtime 기준 skip ([builder.py](scripts/builder.py) 의 `_copy_if_newer`) 이며 그 외 캐시 없음. 글 ≤ 수십 건 규모에선 무시 가능. |
| 테스트 부족 | 단위 테스트 디렉터리 없음. 빌드 시 토크나이저 패리티 fixture (PHP 있을 때) 만 자동 실행. Parsedown 포팅의 PHP↔Python 동등성은 v0.4.1 출시 시점에 일회성 스크립트로 검증되었으나 재현 가능한 형태로 트리에 동봉되지 않음 (§ 12 참조). v0.5.0 의 PyYAML/인덱스 본문 분리 결정과 함께 도입 의제. |
| 정적 검색 인덱스 본문 포함 | search-index.json 에 모든 글의 평문 본문 전체가 들어 매 검색 요청마다 PHP 가 통째 로드. § 13 표 기준 글 50건 ~250KB, 200건 ~900KB. 글이 늘면 인덱스 본문 분리·카테고리별 분할·IDF 가중치·SQLite 이주 검토 ([scripts/search.py](scripts/search.py) 의 v0.5.0 의제 참조). |

---

## 18. 업데이트 로그

열한 버전의 차이를 한눈에:

| 버전 | 시스템 정체성 | 출력 UI/UX | 글 `<title>` | 마크다운 본문 구조 | 색인 정책 | sitemap.xml | 마크다운 파서 | meta.yaml 필드 | 검색 토크나이저 | 빌드 검증 | 레거시 dispatcher | PHP 함수 시뮬레이션 | 카테고리 한국어 폴더 | 빌드 모듈 구조 | 외부 의존성 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **v0.4.7 (현재)** | (동일) | (동일 — dist 바이트 동일) | (동일) | (동일) | (동일) | (동일) | (동일) | (동일) | (동일) | (동일) | (동일) | (동일) | (동일) | (동일) | (동일) |
| **v0.4.6** | (동일) | + **페이지네이션 nav 여백 축소 + SSR 시점의 첫 페이지 정적 생성 (FOUC 제거)** | (동일) | (동일) | (동일) | (동일) | (동일) | + **`Articles/meta.yaml` (홈 = 루트의 페이지 설정 — per_page / excludes_categories / ...)** / + **카테고리·홈 meta.yaml 의 `priority` (정수, 큰 값 먼저)** / **site.yaml 의 home_* 류 키 폐기 (전역 ↔ 페이지 설정 분리)** | (동일) | (동일) | (동일) | (동일) | (동일) | (동일) | (동일) |
| **v0.4.5** | (동일) | + **JS DOM 페이지네이션 컨트롤 (홈·카테고리 인덱스·서브카테고리 section). `<html lang>` 동적화** | (동일) | (동일) | (동일) | + **서브카테고리 URL 포함** | (동일) | + **글 `lang:`** / + **카테고리 meta.yaml (per_page / preview_per_page / layout / styles / lang)** | (동일) | (동일) | (동일) | (동일) | + **워닝 메시지에 슬러그 변환 결과 표기 + ASCII rename 권장** | + **assets/pagination.js** | (동일) |
| **v0.4.4** | (동일) | (동일) | (동일) | (동일) | (동일) | **자동 생성 (글·톱레벨 카테고리·홈, noindex 제외, lastmod=updated\|date). robots.txt Sitemap 디렉티브 활성화** | (동일) | (동일) | (동일) | (동일) | (동일) | (동일) | (동일) | + **scripts/sitemap.py** | (동일) |
| **v0.4.3** | (동일) | (동일) | **`{seo.title_prefix}{title}{seo.title_suffix}` 로 정상화** | + **섹션 마커 `===제목===` / `======`** | (동일) | 없음 (robots.txt 에 주석으로만 자리표시) | (동일) | **seo_* 평면 필드 → `seo:` 블록 그룹화** | (동일) | (동일) | (동일) | (동일) | (동일) | + **models.SeoMeta** | (동일) |
| **v0.4.2** | (동일) | (동일) | (동일) | (동일) | + **검색 결과 페이지에 noindex,follow** | 없음 | (동일) | (동일) | (동일) | + **slug ↔ 카테고리 slug 충돌 차단** | **site.yaml 의 base_url 사용** | **balanced parser — nested parens + quoted `)` 정상 처리** | (동일) | (동일) | (동일) |
| **v0.4.1** | (동일 — 빌드 PHP 의존만 사라짐) | (동일) | (동일) | (동일) | (동일) | 없음 | **scripts/parsedown.py — Parsedown 1.7.4 Python 포팅 (단일)** | (동일) | (동일 — PHP 없으면 워닝 후 건너뜀) | (동일) | (동일) | (동일) — 단순 정규식 (`[^)]*`) | (동일) | + scripts/parsedown.py | **Python 3 만 (빌드). PHP runtime 은 검색·리다이렉트용으로 여전 필요.** |
| **v0.4.0** | **"PHP 기반 경량 웹 사이트 생성기"** | (동일) — nav-search 의 italic placeholder 제거 | (동일) | (동일) | **전역 noindex 제거. 글마다 `noindex: true` 로 개별 차단** | 없음 | (동일) | + **`noindex:`** / − **`seo_keywords:` 폐기** | **1글자 한국어 제외 (bigram 만). 본문 길이 절단 폐지. Py↔PHP 패리티 자동 검증** | + 토크나이저 패리티 | (동일) | (동일) | **_meta.yaml 오버라이드 폐기. hex 코드포인트 자동 변환 + 워닝** | **build.py + scripts/ 패키지** | (동일, 다만 캐치프레이즈로 솔직 표기) |
| **v0.3.2** | (동일) | (동일) — nav-search 만, 카테고리별 스코프 검색 | (동일) | (동일) | (동일) | 없음 | (동일) | (동일) | (동일) | (동일) | (동일) | (동일) | (동일) | 단일 build.py (2085줄) | (동일) |
| **v0.3.1** | "SSG (런타임 PHP 검색 포함)" | (동일) + 모든 페이지 nav 우측 검색창 + Recent posts 위 inline 폼 | (동일) | (동일) | (동일) | 없음 | (동일) | (동일) | 1글자 한국어 그대로 인덱싱 | (동일) | (동일) | (동일) | (동일) | 단일 build.py | Python 3 + PHP CLI (빌드) + PHP runtime (검색) |
| **v0.3** | "SSG" | 원본 + 글마다 스타일 오버라이드 가능 | (동일) | (동일) | (동일) | 없음 | **Parsedown.php (PHP CLI)** — 자체 파서는 fallback | + **`styles:`** | — | (동일) | (동일) | (동일) | _meta.yaml 슬러그 오버라이드 | 단일 build.py | Python 3 + (parsedown 시) PHP CLI |
| **v0.2** | "SSG" | 원본 `lama_website-main` 와 동일 | (동일) | (동일) | 전역 noindex (원본 보존) | 없음 | (동일) | (동일) | — | (동일) | (동일) | imgBox/imgSlideBox | — | 단일 build.py | (동일) |
| **v0.1** | "SSG" | v0.1 자체 디자인 | 원본 quirk: 항상 site.name | 자동 단일 갭+섹션 wrap | 전역 noindex | 없음 | Python stdlib 자체 파서 | slug, title, date, seo_* | — | slug 정규식, 날짜 형식, slug 중복 | 도메인 하드코딩 | — | — | 단일 build.py | Python 3 |

### v0.4.7 (2026-05-14) — 문서·코드 정합성 회복 (회귀 0, dist 산출물은 v0.4.6 과 바이트 동일)

v0.4.6 까지의 변경 결과물을 점검해 *문서·코드 사이의 정합성 갭만* 채운 점진 안정화 버전입니다. v0.4.2 와 동질 — 새 기능, 출력 변화, 동작 변화는 없습니다. v0.5.0 의 큰 변경 (단위 테스트 도입, description 폴백 정리, PyYAML / 검색 인덱스 본문 분리 결정 등) 에 들어가기 전 마지막 점검.

| 개선 | 내용 |
|---|---|
| build.py docstring 갱신 | "siheonlee.com v0.4.5" 표기를 v0.4.7 로 정정. v0.4.6·v0.4.7 변경 사항 블록 추가. v0.4.6 출시 시점에 진입점 파일이 자기 버전을 잘못 표기하던 갭 해소. |
| README §1·§3 의 폴더명 표기 | "이 폴더(`siheonlee.com_v0.4.1/`)" → `siheonlee.com_v0.4.7/`. 폴더 구조 트리의 루트 이름도 동일하게 갱신. 빠른 시작 절의 빌드 출력 예시는 트리에 따라 변동되는 점을 반영해 `<N> 글, <M> 카테고리` 로 일반화. |
| README §11 (site.yaml 레퍼런스) 재작성 | v0.4.6 의 핵심 변경 (설정 일원화) 이 §11 본문에 반영되지 않은 채로 남아 옛 `home_per_page` / `home_excludes_categories` 가 site.yaml 예시에 그대로 살아 있던 갭 해소. (a) site.yaml 예시에서 옛 home_* 키 제거 + 빠진 robots_txt / warn_on_* 추가, (b) "설정 책임 분리표" (이전엔 §18 의 v0.4.6 본문에만 있던 사분표) 를 §11 본문으로 끌어올림, (c) `Articles/meta.yaml` 의 전용 절 (§11-3) 신설. |
| README §17 한계 표 전면 재작성 | "현재 버전(v0.4.4) 의 한계" 헤더로 두 버전 동안 미갱신이던 표를 v0.4.6 기준으로 재작성. v0.4.5 에서 해결된 3항목 (페이지네이션 / 다국어 i18n / 서브카테고리 인덱스) 제거. v0.4.5/v0.4.6 에서 새로 명시화된 한계 추가 — `layout: list` 만 구현, JS 비활성화 시 페이지 2+ 미표시 (v0.4.6 SSR FOUC 제거의 trade-off), 홈/카테고리 페이지의 `<title>` 폴백 미적용, `_FIRST_P_RE` 의 갭 박스 캡처, description_truncate 의 단어 경계 등. |
| README 말미 노트 갱신 | `v0.4.4 기준으로 작성됨` → `v0.4.7 기준으로 작성됨`. |
| builder._build_home dead branch 정리 | [scripts/builder.py](scripts/builder.py) 의 `_build_home` 에서 home 제외 카테고리 검사가 두 if 로 중복된 부분 (둘이 사실상 같은 케이스를 잡고 있었음) 을 list comprehension 한 줄로 정리. 동작 동일, 출력 동일. |
| 보조 파일 docstring 일괄 갱신 | site.yaml 헤더 주석, scripts/builder.py 의 docstring 의 v0.4.x 변경 사항 표기 일괄 갱신. |

**호환성 노트:**

- v0.4.6 의 dist/ 와 v0.4.7 의 dist/ 는 **바이트 단위로 동일** 합니다 (Hello World, About, Section Markers Demo, Pagination Demo One/Two/Three 의 글 페이지, 홈, /blog/, /blog/tutorials/, sitemap.xml, robots.txt, 404.html, search.php, redirect.php 모두). 회귀 가능성 0.
- 기존 글·카테고리 meta.yaml 변경 불필요.
- site.yaml 변경 불필요 (이미 v0.4.6 에서 옛 home_* 키가 제거되어 있다면 그대로 사용).

#### v0.4.6 → v0.4.7 마이그레이션 시 주의

- 마이그레이션 작업 없음. 새 폴더로 옮겨 빌드만 다시 돌리면 끝.
- 문서가 v0.4.6 의 변경을 더 명확히 반영했으므로, README §11 / §17 / §18 을 한 번 통독해 두면 향후 작업 시 참고가 됨.
- v0.4.2 로드맵의 미수용 B-1 / B-5 / B-6 항목 (단위 테스트, description 폴백 범위, 단어 경계) 은 v0.4.7 범위 밖. v0.5.0 으로 이월.

---

### v0.4.6 (2026-05-14) — 페이지네이션 여백·FOUC 개선 + `Articles/meta.yaml` + `priority` + 설정 일원화

v0.4.5 의 페이지네이션 UX, 카테고리 meta.yaml 스키마, 사이트 설정 표면을 다듬은 점진 버전. 다섯 갈래 변경 모두 *기존 콘텐츠의 출력 동작은 거의 그대로 유지하면서 사용성·유연성·설정 구조의 일관성을 보강* 하는 데 초점.

| 개선 | 내용 |
|---|---|
| 페이지네이션 nav 여백 축소 | `.pagination-nav` 의 상단 padding 을 제거하고 음수 margin-top (-0.45em) 으로 위 section 과 더 가깝게 붙임. 하단 padding 도 `0.6em → 0.3em`. ([assets/common_template.css](assets/common_template.css)) |
| SSR 시점의 첫 페이지 상태 정적 생성 (FOUC 제거) | v0.4.5 까지는 페이지 로드 직후 모든 항목이 잠깐 보였다가 JS 가 hide 하는 깜빡임이 있었습니다. v0.4.6 부터 빌더가 `data-per-page` 를 넘는 인덱스의 항목에 `style='display:none'` 을 inline 으로 부착해 초기 상태부터 페이지 1 만 보이도록 합니다. [assets/pagination.js](assets/pagination.js) 는 그 후에 클릭 핸들러를 부착 — 표면적 변동 없음. |
| `Articles/meta.yaml` 신설 | 메인페이지 (사이트 루트) 의 카테고리-격 설정. 카테고리 폴더의 meta.yaml 과 동일 스키마. `per_page` 로 메인페이지 Recent posts 의 페이지당 글 수, `excludes_categories` 로 Recent posts 에서 제외할 톱레벨 카테고리 목록 (옛 `site.home_excludes_categories` 의 이전 위치) 을 지정. `preview_per_page` / `priority` 는 루트이므로 적용 대상이 없지만 스키마 일관성을 위해 받아들임. |
| `priority` 필드 신설 | 모든 카테고리 meta.yaml 에 `priority: <0 이상 정수>` 를 둘 수 있습니다. **값이 클수록 먼저** (priority 100 → 1 → 0). 같은 값끼리는 폴더명 알파벳 순. 적용 위치: (a) 부모 카테고리의 인덱스 페이지에서 자식 카테고리들이 section 으로 나열될 때의 순서, (b) 메인페이지/카테고리 페이지 nav 의 톱레벨 카테고리 링크 순서 (About 은 그대로 최상단 고정). 기본값 0. |
| 설정 일원화 (site.yaml ↔ meta.yaml) | site.yaml = 진짜 전역, meta.yaml = 각자 자기 페이지 설정. 옛 site.yaml 의 메인페이지 전용 키 3개 (`home_per_page` / `home_excludes_categories` / `home_sort`) 를 `Articles/meta.yaml` 로 이전 (`home_sort` 는 빌더가 사용한 적 없는 dead field 라 그대로 폐기). site.yaml 은 이제 사이트 메타·전역 lang·카테고리 디폴트·SEO 폴백·robots.txt 본문 등 "여러 페이지에 공통 적용되는 설정" 만 보유. |

**예시 — Articles/meta.yaml** (메인페이지 = 홈 의 설정)

```yaml
# 메인페이지 Recent posts 의 페이지당 글 수.
per_page: 5

# Recent posts 에서 제외할 톱레벨 카테고리.
# (v0.4.5 까지는 site.yaml 의 home_excludes_categories 였음.)
excludes_categories: [About]

layout: list
# 루트는 상위가 없으므로 priority / preview_per_page 는 적용 대상 없음.
```

**예시 — 카테고리 priority 의 효과**

`Articles/Blog/meta.yaml` 에 `priority: 100`, `Articles/Diary/meta.yaml` 에 `priority: 0` 을 두면 (둘 다 톱레벨 카테고리), 메인페이지 nav 는 `About | Blog | Diary` 가 되고 (About 은 고정, Blog 가 priority 큼 → 먼저). 같은 priority 끼리는 폴더명 알파벳 순.

**설정의 책임 분리 (v0.4.6 의 규약):**

| 어디에 설정 두는가 | 어떤 설정 |
|---|---|
| `site.yaml` | 사이트 전역 (도메인, name, copyright, lang 디폴트, default_og_image 등) / 여러 페이지에 공통 적용되는 디폴트 (category_per_page, category_preview_per_page) / robots.txt 본문 |
| `Articles/meta.yaml` | 메인페이지 (홈) 전용 — per_page, excludes_categories, lang, layout, styles |
| `Articles/<카테고리>/meta.yaml` | 그 카테고리 인덱스 페이지 전용 — per_page, preview_per_page, priority, lang, layout, styles |
| `Articles/<카테고리>/<글>/meta.yaml` | 그 글 페이지 전용 — slug, title, date, updated, noindex, lang, seo:, styles |

원칙: 페이지 한 종에만 적용되는 설정은 site.yaml 에 두지 않고 그 페이지의 meta.yaml 에 둡니다.

**호환성 노트:**

- v0.4.6 의 dist/ 와 v0.4.5 의 dist/ 는 거의 동일하지만 일부 줄이 다릅니다 (회귀 아님, 의도된 변경):
  - 페이지네이션이 활성화된 section 의 두 번째 페이지 이후 `<div class='listup_module_div'>` 가 `style='display:none'` 을 inline 으로 부착.
  - `.pagination-nav` 의 CSS 속성 (padding/margin) 변경 — 마크업은 동일.
- **기존 글의 meta.yaml** — 변경 없이 그대로 빌드됩니다.
- **기존 카테고리 meta.yaml** — `priority` 를 명시하지 않으면 모두 기본값 0 으로 처리. v0.4.5 의 폴더명 알파벳 순 정렬과 동일한 결과.
- **graceful degradation** — JS 가 완전히 비활성화된 환경에서는 페이지 2 이후의 항목이 표시되지 않습니다 (이전 버전: 모두 표시됨, 페이지 컨트롤만 비기능). 현실적인 사용 환경에서 JS 비활성화는 매우 드물고 (`<noscript>` fallback 추가는 별도 의제), FOUC 제거의 이득이 더 크다는 판단.

#### v0.4.5 → v0.4.6 마이그레이션 시 주의

- **site.yaml 정리:** 옛 `home_per_page`, `home_excludes_categories`, `home_sort` 키는 site.yaml 에서 삭제하세요. 잔존해도 빌드는 진행되지만 무시되며 워닝이 출력됩니다. 같은 값은 `Articles/meta.yaml` 의 `per_page` / `excludes_categories` 에 옮겨 두세요 (`home_sort` 는 빌더에서 사용된 적이 없는 dead field 라 그대로 폐기).
- `Articles/meta.yaml` 은 선택 사항입니다. 두지 않으면 빌더의 코드 디폴트 (`per_page=5`, `excludes_categories=[]`) 가 사용됩니다.
- `priority` 는 정수만 허용합니다. 빈 문자열·문자열·소수는 빌드 실패 (`'priority' 는 정수여야 합니다`).
- `excludes_categories` 는 리스트여야 합니다 (문자열·매핑은 빌드 실패).
- 음수 priority 도 받아들여집니다 (예: priority: -5 는 priority: 0 보다 뒤). 보통은 0 이상 사용을 권장.

---

### v0.4.5 (2026-05-14) — 페이지네이션 + 다국어 + 서브카테고리 인덱스 + 카테고리 meta.yaml

다섯 갈래 변경이 한 버전에 묶여 있습니다. 모두 인덱스 페이지의 형식이나 글의 메타데이터 표현을 바꾸는 작업으로, 공통 동기는 *콘텐츠가 늘었을 때 사이트가 자연스럽게 확장되도록* 하는 것입니다.

| 개선 | 내용 |
|---|---|
| 페이지네이션 | 메인페이지 Recent / 카테고리 인덱스 (대분류·소분류) / 상위 카테고리에 임베드된 서브카테고리 section 마다 독립적인 페이지 컨트롤. JS DOM hide/show — 모든 항목은 서버에서 렌더되므로 SEO/접근성 영향 없음. UI 는 nav-search 와 톤을 맞춘 회색 좌/우 화살표 + 페이지 번호 ([assets/pagination.js](assets/pagination.js), [assets/common_template.css](assets/common_template.css) 의 `.pagination-nav`). |
| 다국어 지원 | 템플릿의 `<html lang='ko'>` 하드코딩 제거. site.yaml 의 `lang:` 이 사이트 전역 디폴트 (기본 ko), 글 meta.yaml 의 `lang:` 으로 글마다, 카테고리 meta.yaml 의 `lang:` 으로 카테고리 인덱스마다 오버라이드. |
| 서브카테고리 인덱스 페이지 | v0.4.4 까지는 원본 lama.pe.kr quirk 를 보존해 톱레벨 카테고리만 자기 인덱스 페이지를 가졌습니다. v0.4.5 부터 서브카테고리도 자기 인덱스 페이지 (`/{top-slug}/{sub-slug}/`) 를 갖습니다. 톱레벨 페이지는 그대로 유지 (서브카테고리들이 section 으로 임베드되는 점도 그대로). sitemap.xml 도 서브카테고리 URL 을 포함. |
| 카테고리 meta.yaml | 각 카테고리 폴더 (대분류·소분류) 마다 `meta.yaml` 을 둘 수 있습니다 — 글의 meta.yaml 과 형식이 다릅니다 (slug/title/date 없음). 빌더는 폴더에 content.md / content.html 이 있으면 글, 없으면 카테고리로 구분. 지원 필드: `per_page` (이 카테고리의 자기 인덱스 페이지의 페이지당 글 수), `preview_per_page` (이 카테고리가 상위 카테고리의 인덱스 페이지에 section 으로 임베드될 때의 페이지당 글 수), `layout` (`list` 기본; gallery 등 미래 확장 예정), `styles` (이 카테고리 인덱스 페이지에만 적용할 CSS), `lang`. |
| 비ASCII 폴더명 워닝 메시지 보강 | v0.4.0 부터 `Articles/` 의 한국어 폴더명은 자동으로 hex 코드포인트 slug 로 변환되었지만, 빌드 로그의 메시지가 다소 모호했습니다. v0.4.5 의 메시지는 *어떤 폴더가 어떤 slug 로 변환되었는지* 를 명시하고 ASCII rename 권장을 한 번 더 강조. `[WARN] URL slug 에 비ASCII 문자 포함: '블로그' → 'be94-b85c-adf8'` 와 같이 출력됩니다. |

**예시: 카테고리 meta.yaml (소분류 Blog/Tutorials)**

```yaml
# Tutorials 자기 페이지 (/blog/tutorials/) — 페이지당 글 수
per_page: 20

# Blog 톱레벨 (/blog/) 의 Tutorials section — 페이지당 글 수
preview_per_page: 5

# 'list' (기본) / 'gallery' / 향후 확장 예정
layout: list

# 이 카테고리 인덱스 페이지에만 적용할 추가 CSS
# styles:
#   .listup_module_title a:
#     font-weight: 600
```

`per_page > preview_per_page` 가 자연스러운 사용법입니다 — 소분류의 자기 페이지는 그 소분류 글을 더 많이 보여주고, 상위에 임베드된 section 은 미리보기 수준으로 적게 보여주는 정책.

**호환성 노트:**

- v0.4.5 의 dist/ 와 v0.4.4 의 dist/ 는 바이트 단위로 다릅니다 (회귀 아님, 의도된 변경). 차이는 다음과 같습니다:
  - 모든 페이지의 `<html lang>` 이 동적값 (site.yaml 의 `lang:` 디폴트).
  - 홈/카테고리 페이지에 `<section class="paginated" data-pagination-group=...>` 와 `<nav class="pagination-nav">` 마크업, `<script src="/assets/pagination.js">` 추가.
  - 카테고리 페이지 head 에 `{{CATEGORY_STYLES}}` 자리 (현재는 비어 있는 경우 빈 줄).
  - `dist/{top}/{sub}/index.html` 신규 (서브카테고리가 있는 경우).
  - `dist/assets/pagination.js` 신규.
  - sitemap.xml 에 서브카테고리 URL 추가.
- **기존 글의 meta.yaml** — 변경 없이 그대로 빌드됩니다. 글에 `lang:` 을 추가하지 않으면 site.lang (기본 ko) 가 적용됩니다.
- **기존 카테고리 폴더** — meta.yaml 이 없어도 정상 동작합니다 (모든 필드가 site.yaml 의 디폴트를 따름). 필요한 카테고리에만 meta.yaml 을 추가하면 됩니다.
- **글 폴더와 카테고리 폴더 구분** — 빌더는 폴더 안에 `content.md` 또는 `content.html` 이 있으면 글 폴더, 없으면 카테고리 폴더로 구분합니다. 글 폴더에는 meta.yaml 이 반드시 있고 (slug/title/date 필수), 카테고리 폴더의 meta.yaml 은 선택사항이며 slug/title/date 가 없어야 합니다.

#### v0.4.4 → v0.4.5 마이그레이션 시 주의

- **카테고리 폴더에 `meta.yaml` 신설 시** — 글 폴더의 meta.yaml 과 헷갈리지 않도록 `slug:` / `title:` / `date:` 키는 절대 넣지 마세요. 빌더는 이 셋 중 하나라도 보이면 카테고리 meta.yaml 로 인정하지 않고 무시합니다 (안전 가드).
- **`per_page` 와 `preview_per_page` 의미** — `per_page` 는 *그 카테고리의 자기 인덱스 페이지* 에 적용되고, `preview_per_page` 는 *그 카테고리가 상위 카테고리의 페이지에 section 으로 임베드될 때* 적용됩니다. 톱레벨 카테고리는 일반적으로 상위에 임베드되지 않으므로 `preview_per_page` 는 거의 사용되지 않습니다.
- **다국어 SEO** — 검색엔진은 `<html lang>` 을 신뢰합니다. 영어 글에 `lang: en` 을 명시하면 그 페이지가 영어 SERP 에 더 적합하게 분류됩니다. 한국어/영어 혼재 사이트라면 글마다 `lang:` 을 명시하는 것을 권장합니다.
- **pagination.js 비활성/실패 시** — JS 가 로드되지 않으면 모든 항목이 한 페이지에 펼쳐진 채로 표시됩니다 (graceful degradation). 페이지 컨트롤은 렌더되지만 클릭해도 반응 없음. 사용성은 떨어지지만 콘텐츠는 모두 접근 가능.

### v0.4.4 (2026-05-14) — sitemap.xml 자동 생성

v0.4.0 의 전역 noindex 폐기로 글이 실제로 검색엔진에 색인되기 시작한 뒤, 검색엔진이 사이트 구조를 더 빠르고 정확하게 파악하도록 sitemap 을 제공하는 것이 자연스러운 다음 단계였습니다. v0.4.2 에서 robots.txt 에 주석으로만 자리표시되어 있던 `Sitemap:` 디렉티브가 이제 실제 파일을 가리킵니다.

| 개선 | 내용 |
|---|---|
| sitemap.xml 자동 생성 | [scripts/sitemap.py](scripts/sitemap.py) 신설. [scripts/builder.py](scripts/builder.py) 의 파이프라인에 step [12] `_build_sitemap` 으로 통합. sitemaps.org 0.9 스키마. 클라이언트 측 처리 없는 정적 XML 파일. |
| 포함 URL | (1) 홈 (`/`), (2) 톱레벨 카테고리 인덱스 (`/{cat-slug}/`), (3) 모든 글 (`/{slug}/`). 서브카테고리는 인덱스 페이지가 없으므로 (원본 quirk — § 5 참조) 제외. `search.php` (noindex,follow) 와 `404.html`, `/src/`, `/assets/` 도 제외. |
| noindex 글 제외 | meta.yaml 의 `noindex: true` 가 있는 글은 sitemap 에서도 제외 — `<meta robots noindex>` 와 sitemap 동시 등장은 신호 충돌. |
| lastmod 규칙 | 글: `updated` 가 있으면 그 값, 없으면 `date`. 카테고리: 서브트리의 non-noindex 글 lastmod 중 최댓값. 홈: 홈에 실제로 노출되는 글 (즉 `home_excludes_categories` 가 아닌 non-noindex 글) lastmod 중 최댓값. |
| changefreq / priority | 일부러 비움. Google 은 두 필드를 공식적으로 무시한다고 밝혔고, 부정확한 priority 는 오히려 신뢰도를 떨어뜨립니다. |
| robots.txt Sitemap 디렉티브 | site.yaml 의 `robots_txt_main` 에서 `# Sitemap: ...` 의 `#` 제거. 빌드 산출물 `dist/robots.txt` 가 자동으로 `Sitemap: https://siheonlee.com/sitemap.xml` 라인을 포함. |
| 파이프라인 단계 수 | 14 → 15 단계. `_build_robots` 와 `_build_dispatcher` 사이에 `_build_sitemap` 삽입. |

**예시 출력 (현재 트리 기준):**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://siheonlee.com/</loc>
    <lastmod>2026-05-14</lastmod>
  </url>
  <url>
    <loc>https://siheonlee.com/blog/</loc>
    <lastmod>2026-05-14</lastmod>
  </url>
  <url>
    <loc>https://siheonlee.com/about/</loc>
    <lastmod>2025-01-01</lastmod>
  </url>
  <url>
    <loc>https://siheonlee.com/hello-world/</loc>
    <lastmod>2026-05-07</lastmod>
  </url>
  <url>
    <loc>https://siheonlee.com/section-markers-demo/</loc>
    <lastmod>2026-05-14</lastmod>
  </url>
</urlset>
```

**호환성 노트:** 글 산출물의 바이트 단위 출력은 v0.4.3 과 동일 (회귀 0). 추가되는 파일은 `dist/sitemap.xml` 한 개와 `dist/robots.txt` 의 한 줄 변경뿐입니다.

#### v0.4.3 → v0.4.4 마이그레이션 시 주의

- **base_url 검증** — sitemap 의 모든 URL 은 `site.yaml` 의 `base_url` 을 접두로 사용합니다. 배포 전에 `base_url: https://siheonlee.com` 이 정확한지 확인하세요. 잘못된 도메인이면 sitemap 도 같이 잘못됩니다.
- **robots.txt 수동 커스텀했던 사용자** — site.yaml 의 `robots_txt_main:` 블록을 직접 편집했다면, 그 블록에 `Sitemap: ...` 라인이 살아있는지 확인하세요. (v0.4.4 의 기본값은 `Sitemap: https://siheonlee.com/sitemap.xml` 한 줄을 포함합니다.)
- **검색엔진 등록** — Google Search Console / Naver Search Advisor 에 sitemap URL (`https://siheonlee.com/sitemap.xml`) 을 등록하면 색인 속도가 빨라집니다. robots.txt 의 `Sitemap:` 디렉티브로 자동 발견되긴 하지만, 직접 제출이 더 안정적입니다.
- **noindex 와 sitemap** — 어떤 글을 검색엔진에서 빼고 싶다면 meta.yaml 의 `noindex: true` 한 줄로 충분합니다. v0.4.4 부터는 이 글이 sitemap 에서도 자동으로 빠지므로 추가 작업 불필요.

### v0.4.3 (2026-05-14) — `<title>` 정상화 + 마크다운 섹션 마커 + SEO 그룹화

세 변경의 공통 동기는 *글의 의미 단위 표현* 을 일관되게 만드는 것. 출력은 v0.4.2 와 달라지지만, 모두 의도된 개선.

| 개선 | 내용 |
|---|---|
| 글 `<title>` 의 글 제목 사용 | [scripts/builder.py](scripts/builder.py) 의 `_render_articles` 가 이제 `build_meta_tags` 가 반환하던 `full_title` (`{seo.title_prefix}{title}{seo.title_suffix}`) 을 `<title>` 에 사용. v0.4.2 까지는 `page_title = self.site.name` 한 줄로 항상 `Lama` 로 덮어쓰던 quirk (`_full_title` 로 밑줄 접두 → 의도적 미사용 표시) 가 있었음. v0.4.0 에서 noindex 가 풀려 글이 검색 결과에 뜨기 시작하면서 이 quirk 가 부적합해진 상황을 해소. |
| 마크다운 본문의 섹션 마커 문법 | 마크다운 본문 안에서 `===제목===` (라인 단독, 시작/끝 등호 3개) / `======` (라인 단독, 등호 정확히 6개) 로 섹션을 명시적으로 나눌 수 있음. 빌더는 본문 시작에 자동으로 첫 갭 (`title`) + 첫 `<section>` 을 두고, 마커 만나면 state machine 으로 닫고 열기. 코드 펜스 (` ``` `, `~~~`) 안의 같은 패턴은 무시 (코드 예시 안전성). 구현은 [scripts/markdown.py](scripts/markdown.py) 의 `_preprocess_section_markers` (raw markdown → sentinel HTML 주석) + `resolve_section_markers` (Parsedown 출력 + sentinel → 실제 gap/section). |
| meta.yaml 의 SEO 필드 그룹화 | 평면 12 개 필드 (`seo_title_prefix`, `seo_description`, `seo_og_title` 등) → `seo:` 하위 블록. 키 이름에서 `seo_` 접두 제거 (`seo_description` → `seo.description`). [scripts/models.py](scripts/models.py) 에 `SeoMeta` dataclass 신설. backward compat 폴백 없음 — 기존 글의 meta.yaml 을 직접 마이그레이션해야 함. |

**호환성 노트:** v0.4.2 의 dist/ 와 v0.4.3 의 dist/ 는 바이트 단위로 다릅니다 (회귀 아님, 의도된 변경):

1. 모든 글 페이지의 `<title>` 이 글 제목으로 변경.
2. `og:title` 의 폴백이 `<title>` 결과를 받기 때문에 사실상 동일 (이전엔 우연히 같은 값이 들어가던 부분이 이제 같은 코드 경로로 들어감).
3. 기존 글의 meta.yaml 에 `seo_*` 평면 필드를 그대로 둔 채 빌드를 돌리면 그 필드들은 모두 무시되고 기본값 (또는 site.yaml 폴백) 으로 빌드됩니다. 새 `seo:` 블록으로 옮겨주세요.

**미수용 로드맵 항목:** v0.4.2 로드맵 의 B-5 (description 폴백의 추출 범위 제한) 와 B-6 (description_truncate 단어 경계) 는 본 버전 범위 밖. 사용자가 요청한 세 항목에만 집중. v0.4.4 로 미룸.

### v0.4.2 (2026-05-14) — 정합성 갭 정리 (회귀 0, 출력 동등)

v0.4.1 의 종합 검토에서 드러난 여섯 가지 작은 정합성 이슈를 한 번에 정리한 점진 버전. 글 페이지 출력은 v0.4.1 의 dist/ 와 바이트 단위로 동일 (Hello World + About 기준).

| 개선 | 내용 |
|---|---|
| 글 slug ↔ 카테고리 slug 충돌 검증 | [scripts/builder.py](scripts/builder.py) 의 `_validate()` 가 톱레벨 카테고리 slug 와 글 slug 의 충돌을 빌드 초입에서 차단. 이전엔 `_prune_orphans` 의 사후 정리에 맡겨져 무엇이 무엇을 덮어쓰는지 비결정적이었음. README §11 이 약속하던 동작을 실제 코드로 구현. |
| 레거시 dispatcher 의 base_url 사용 | `dist-legacy/redirect.php` 의 `Location:` 헤더에 박혀 있던 `https://siheonlee.com/` 리터럴 제거. 빌드 시 site.yaml 의 `base_url` 을 PHP 변수 `$BASE_URL` 로 내보내 사용. "사이트 전역 설정은 site.yaml 한 곳" 원칙과 동기화. |
| search.php 의 noindex,follow | 검색 결과 페이지가 `?q=…` 노이즈로 색인되는 것을 차단. v0.4.0 의 "전역 noindex 폐기" 정책에서 의도된 예외. follow 는 유지하므로 결과 링크는 외부 크롤러가 추적 가능. |
| imgBox/imgSlideBox 인자 파싱 강화 | 이전의 `<\?php\s+(\w+)\(([^)]*)\)\s*\?>` 정규식이 인자 안의 `)` 를 처리하지 못해 `imgBox("a(b).jpg", "caption")` 같은 입력이 깨졌음. balanced parser (`_scan_php_args`) 로 교체. 실제 운영 글에 그런 입력이 없어 회귀는 없지만 표면적 갭 해소. |
| {{ROBOTS_META}} placeholder 일반화 | article.html 의 들여쓰기 (4공백) 와 강결합되어 있던 라인 제거 패턴을 정규식으로 일반화. 누군가 템플릿 들여쓰기를 2공백으로 바꾸어도 빈 줄이 남지 않음. |
| README §15 하위 번호 보정 | "14-1, 14-2, 14-3, 14-4" → "15-1, 15-2, 15-3, 15-4". 문서 신뢰도. |

#### v0.4.1 → v0.4.2 마이그레이션 시 주의

- **출력 동등성** — Hello World 와 About 글의 `dist/` 산출물은 v0.4.1 과 바이트 단위로 동일합니다. 글 페이지 본문 렌더 결과의 후방 호환을 의미.
- **레거시 redirect.php 변화** — 출력에 `$BASE_URL = '...'` 한 줄이 추가됩니다. 배포 후 `curl -I https://lama.pe.kr/Articles/...` 로 301 위치가 의도대로 가는지 확인하세요.
- **검색 결과 페이지 색인** — `/search.php?q=...` 같은 URL 이 이미 외부 검색엔진에 색인돼 있었다면, 다음 크롤 때 자연스럽게 제외됩니다. 즉시 제거가 필요하면 Google Search Console 의 URL 제거 도구 사용.
- **카테고리/글 slug 충돌이 있던 사이트** — v0.4.1 까지는 어찌어찌 빌드가 되었지만 v0.4.2 에서는 빌드 실패합니다. 차단되면 카테고리 폴더명 또는 글 slug 를 변경하세요.

### v0.4.1 (2026-05-14) — 빌드 PHP 의존 제거 (Parsedown 의 Python 포팅)

v0.4.0 의 캐치프레이즈를 정당화한 PHP 사용처 셋 중 **마크다운 파서** 한 자리를 순수 Python 으로 옮긴 버전. v0.4.0 로드맵의 "PyYAML 도입 검토" 는 보류하고, 의존성 축소가 더 의미 있는 곳 — 빌드 PHP 의존 — 으로 방향을 전환한 결과.

| 개선 | 내용 |
|---|---|
| Parsedown.php → scripts/parsedown.py | 1712줄의 PHP Parsedown 1.7.4 를 ~770줄의 순수 Python 클래스로 포팅. 메서드명·블록/인라인 dispatch 구조·Block/Element dict 키 이름까지 원본과 일대일 매핑. Python stdlib (`re`, `typing`) 만 사용. |
| 빌드 PHP 의존 제거 | 마크다운 파싱이 더 이상 PHP subprocess 호출이 아니라 in-process Python. 빌드 머신에 `php` 명령이 없어도 빌드 성공. (토크나이저 패리티 검증은 PHP 있을 때만 자동 수행 — 없으면 워닝.) |
| 추상화 폐지 | scripts/markdown.py 의 MarkdownRenderer / BuiltinRenderer / ParsedownRenderer / make_markdown_renderer 팩토리 모두 삭제. 단일 파서이므로 인터페이스 불필요. |
| `markdown_parser:` 옵션 폐지 | site.yaml 의 해당 줄, SiteConfig.markdown_parser 필드, builder.py 의 분기 로직 모두 제거. |
| parsers/ 디렉터리 삭제 | Parsedown.php / run.php / LICENSE.txt 제거. Parsedown 의 MIT 라이센스 고지는 scripts/parsedown.py 의 docstring 으로 이전. |
| 마크다운 패리티 (출시 시점 검증) | v0.4.1 출시 시점에 PHP Parsedown 1.7.4 와 Python 포팅의 출력을 합성 fixture 46개 + lama_website-main 의 실제 33개 글로 바이트 단위 비교 → **79/79 일치**. 검증 스크립트는 v0.4.0/lama_website-main 이 옆에 함께 있어야만 의미 있게 동작하므로 트리에 동봉하지는 않음. |
| 출력 동등성 보장 | v0.4.0 의 dist/ 와 v0.4.1 의 dist/ 가 바이트 단위로 동일 (Hello World + About 글 기준). 글 본문 렌더 결과의 후방 호환을 의미. |

#### v0.4.0 → v0.4.1 마이그레이션 시 주의

- **빌드 시 PHP** — 없어도 됩니다. v0.4.0 까지 워닝/에러로 잡히던 "`PHP 실행 파일을 찾을 수 없음`" 은 v0.4.1 에서 더 이상 발생하지 않습니다.
- **`markdown_parser:` 설정** — site.yaml 에서 이 줄을 두어도 빌드 실패는 아닙니다 (무시됨). 정리하려면 줄을 삭제하세요.
- **parsers/ 디렉터리** — 더 이상 필요 없으므로 삭제됐습니다. 만약 직접 커스텀한 PHP 파서를 두려고 한다면 scripts/ 안의 모듈을 직접 수정해야 합니다 (추상화 폐지).
- **글 본문 렌더 결과** — 동일합니다. v0.4.0 의 빌드 산출물과 v0.4.1 의 빌드 산출물은 바이트 단위로 같습니다. 글을 새로 빌드해도 dist 의 변경은 없습니다.
- **배포 서버 PHP** — 변경 없음. search.php, redirect.php 가 여전히 런타임 PHP 를 필요로 합니다.

### v0.4.0 (2026-05-13) — 정직한 캐치프레이즈 + 색인 정책 정상화 + 모듈 분할

v0.3.2 의 종합 비판 (자기정체성 흐림 / dead SEO / 단일 거대 파일 / 미검증 토크나이저 동기화 등) 에 대한 답변 버전. 기능 추가보다 **약속과 현실의 동기화** 가 주 목표.

| 개선 | 내용 |
|---|---|
| 캐치프레이즈 정직화 | "SSG" → **"PHP 기반 경량 웹 사이트 생성기"**. 기본 마크다운 파서·검색·리다이렉트 셋이 PHP 를 필요로 한다는 사실을 첫 줄에서 인정. README §1·§2·§17 동기화. |
| 전역 noindex 폐기 | templates/article.html, home.html, category.html, 404.html, search.php 의 `<meta name='robots' content='noindex'>` 일괄 제거. 사이트 정책은 '검색 가능' 이 기본. v0.3.x 까지 dead code 였던 SEO 폴백 체인이 실효를 얻음. |
| 글 단위 noindex | meta.yaml 에 `noindex: true` 한 줄로 해당 글만 검색엔진 제외. article.html 의 `{{ROBOTS_META}}` placeholder 가 처리. |
| seo_keywords 필드 폐기 | `<meta name="keywords">` 는 검색엔진이 무시한 지 오래. ArticleMeta / build_meta_tags / README 표에서 제거. |
| 토크나이저 v0.4.0 규칙 | 1글자 한국어를 인덱싱/쿼리에서 제외 (bigram 만 의미 있는 토큰으로 인정). 본문 5000자 절단 폐지 — 글 전체 평문이 인덱스에 들어감. |
| 토크나이저 패리티 자동 검증 | templates/search_tokenize.php 가 단일 진실원. search.php 가 `require_once` 로 같은 파일을 사용. build.py 의 [1] 단계에서 18개 fixture 로 Py↔PHP 출력을 직접 비교. 한 자라도 어긋나면 빌드 즉시 실패. |
| _meta.yaml 카테고리 오버라이드 폐기 | 한국어 폴더명도 결정론적으로 slug 가 만들어지므로 오버라이드가 불필요해짐. slugs.category_slug_from_name 이 비ASCII 문자를 4자리 hex 코드포인트로 자동 치환 후 기존 5단계 변환을 통과시킴. 비ASCII 폴더에는 빌드 시 워닝 1회. |
| reserved_slugs 정리 | `c`, `p`, `api`, `file`, `status`, `blog`, `project`, `research`, `study` 일괄 제거. 실제 충돌 가능성이 있는 `src`, `assets`, `search` 셋만 유지. |
| nav-search 미관 정리 | italic placeholder 제거. faux italic skew 흡수용 비대칭 padding (좌 0.2em / 우 0.6em) 도 단순한 0.3em 좌우 동일로 회복. lama 회색 톤은 유지. |
| build.py 모듈 분할 | 2085줄 단일 파일을 `scripts/` 패키지로 분할: yaml_parser, models, slugs, markdown, seo, search, builder, migrate. 루트 `build.py` 는 진입점 40 줄. |
| migrate.py 이전 | `scripts/migrate.py` 로 이동. 실행은 `python scripts/migrate.py`. BASE 경로 `parent.parent` 로 조정. |
| 잡다한 dead code 청소 | builder._build_category_tree 의 `if sub in [...]: pass` 더미 분기, ArticleMeta 의 seo_keywords 필드 등 제거. |

#### v0.3.2 → v0.4.0 마이그레이션 시 주의

- **noindex 정책 변화** — v0.3.x 까지 모든 페이지가 검색엔진에서 제외돼 있었습니다. v0.4.0 으로 빌드한 사이트는 모든 페이지가 색인 허용으로 변합니다. 특정 글을 계속 비공개로 두려면 그 글의 meta.yaml 에 `noindex: true` 를 추가하세요.
- **카테고리 _meta.yaml 사용자** — 기존에 `_meta.yaml` 로 슬러그를 오버라이드하던 카테고리는 v0.4.0 에서 오버라이드가 무시되고 자동 변환된 hex slug 가 적용됩니다. 영향 받는 카테고리는 폴더명을 ASCII 로 바꾸어 안정된 slug 를 확보하는 것이 좋습니다 (URL 변경 가능성).
- **seo_keywords 사용자** — meta.yaml 의 `seo_keywords:` 줄을 그대로 둬도 무시될 뿐 빌드 실패는 아닙니다. 정리하려면 해당 줄을 삭제하세요.
- **build.py 를 직접 커스텀했던 사용자** — 함수가 모듈별로 흩어졌습니다. 시작점은 `scripts/builder.py` 의 `Builder.build()`. 같은 14단계 파이프라인이 유지됩니다.
- **search.php 직접 커스텀** — 인라인 `search_tokenize()` 함수가 `templates/search_tokenize.php` 로 분리되었습니다. search.php 는 첫 줄에서 `require_once __DIR__ . '/search_tokenize.php';`. 토크나이저를 수정하면 build.py 가 자동으로 Py↔PHP 패리티를 검증하므로 한쪽만 고치고 잊지 마세요.

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

- 글 본문 head 에 `description / og:* / twitter:*` 등 SEO meta 태그 추가 (원본은 noindex 만). v0.3.x 까지는 글에도 noindex 가 있어 출력만 되고 실효는 없었으나, v0.4.0 부터 noindex 전역 제거로 실효성 확보.
- CSS·JS 가 `/assets/` 경로로 정리됨 (원본은 `/common_template.css` 루트). 화면 렌더 결과는 동일.
- 글 폴더 안의 파일은 `/src/{slug}/` 로 복사됨 (원본은 글 폴더 절대경로). 글 본문 안의 상대 경로 `./imgs/x.jpg` 는 자동 변환.

### v0.1 — SSG 시스템 자체 완성

- Python stdlib only 로 구현된 SSG 의 첫 동작 버전. YAML 파서·마크다운 파서·HTML 처리·라우팅·legacy 리다이렉트 등 핵심 시스템 완비.
- 출력 HTML/CSS 는 v0.1 자체 디자인 (siheonlee.com 브랜드, chevron breadcrumb, ul/li 글 목록, h1 article-title 등). 원본 lama 사이트와 화면이 다름.
- 핵심 설계 원칙: URL 영구성, 표시명과 URL slug 분리, 외부 의존성 0, 서버 설정과 콘텐츠 분리, 빌드의 안전성.

---

*이 문서는 siheonlee.com v0.4.7 (PHP 기반 경량 웹 사이트 생성기 — 빌드는 Python 만, 런타임은 PHP) 기준으로 작성되었습니다. (2026-05-14)*

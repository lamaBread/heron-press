# siheonlee.com v0.7.2 — 사용설명서 & 시스템 문서

> **이 문서는 처음 이 시스템을 접하는 사람을 위해 작성되었습니다.**
> 기술적인 사전 지식 없이도 읽을 수 있도록, 모든 개념을 처음 등장하는 시점에 설명합니다.

이 시스템은 **글마다 폴더 하나**를 만들어 본문과 첨부파일을 관리하고, `python build.py` 한 번으로 사이트를 만들어내는 **PHP 기반 경량 웹 사이트 생성기** 입니다.

> **v0.7.2 한 줄 요약:** *빌드 진행 표시 + 빌드 리포트 문서화.* 빌드가 시작/완료 두 줄만 출력하던 v0.7.1 까지의 동작을 보완 — `build()` 가 16 단계 헤더 (`[ n/16] …`) 를 출력하고, 무거운 단계 (이미지 WebP 변환 / 글 렌더) 는 글·이미지마다 같은 줄을 `\r` 로 갱신하는 라이브 카운터를 보여준다 (사진 많은 사이트가 멈춘 듯 보이던 문제 해소). 또한 그동안 터미널에만 뜨던 보완 필요/살펴볼 사항을 `build.py` 가 있는 폴더의 **`build-report.md`** 로도 남긴다 — 진행 트랜스크립트 + 요약 + 보완 항목을 마크다운으로 서식화. 진행 출력·리포트 문서는 모두 `dist/` 밖이라 dist 산출물은 v0.7.1 과 **바이트 동일** (`feed.atom` / `feed.rss` generator 문자열만 v0.7.1 → v0.7.2 자동 갱신 — `__version__` 단일 source 효과). 단위 테스트 258 그대로. 자세한 내역은 [§ 17 업데이트 로그](#17-업데이트-로그) 참조.

> **v0.7.0 한 줄 요약:** *빌드 증분 캐싱 도입.* 매 빌드마다 모든 글을 재렌더하던 동작이, 변경되지 않은 글은 캐시된 HTML/PHP 를 그대로 dist 에 복원하는 방식으로 전환됩니다. 글이 많아질수록 빌드 시간이 *변경된 글 수* 에 비례 — 한 글의 content 만 바꾸면 그 글만 재렌더, 나머지는 캐시 hit. 캐시 키는 fine-grained 라 site.yaml / 템플릿 / 빌더 코드가 바뀌면 모든 글이 정확히 invalidate 됩니다. CLI 신설 3 종: `--no-cache` (캐시 비활성, v0.6.5 동작), `--clean-cache` (`.build_cache/` 만 폐기 후 빌드), `--clean` 확장 (dist/ 외에 `.build_cache/` 도 함께 폐기). 단위 테스트 231 → **258** (`tests/test_cache.py` 27 케이스 신설).

| 핵심 가치 | 어떻게 보장하는가 |
|---|---|
| **URL 영구성** — 한 번 발급한 URL 은 절대 깨지지 않는다 | 글 URL(`slug`) 은 카테고리·폴더명과 분리. 글을 옮기거나 폴더명을 바꿔도 URL 불변. |
| **운영 의존성 최소** — 빌드 환경은 Python (+ Pillow), 런타임은 Apache+PHP 만 | Python 3 표준 라이브러리 + **Pillow** (v0.5.1, 이미지 최적화 전용). `composer` 없음, 클라이언트 JS 의존성 없음. (v0.4.1 부터 빌드 PHP 의존 제거.) Pillow 가 부담되면 `images.enabled=false` 로 끄면 v0.5.0 처럼 stdlib 만으로 빌드 가능. |
| **이미지 자동 최적화** (v0.5.1) — SEO 직접 영향 항목을 빌드가 처리 | raster 이미지 자동 WebP 변환 + 다중 해상도 srcset + 모든 `<img>` 에 `loading="lazy"` 자동 부착. 글마다 별도 작업 없음. |
| **서버 설정과 콘텐츠 분리** — 글을 추가해도 서버를 안 건든다 | `.htaccess` 미사용. 모든 라우팅 규칙은 Apache VirtualHost 메인 설정에 한 번만 등록. |
| **페이지마다 표현 제어** — 사이트 전역 CSS 와 별도로 페이지 단위 미세 조정 + 본격 디자인 모두 가능 | `meta.yaml` 의 `styles:` 키 안의 *문자열 키* (태그/선택자) 로 본문 태그(p, h3, ul 등)의 CSS 속성을 페이지마다 독립적으로 미세 override. 더 큰 자유도 (at-rule / 중첩 / 변수 / 의사클래스 조합) 가 필요하면 페이지 폴더 안에 진짜 CSS 파일을 두고 같은 `styles:` 키 안의 *정수 키* (1, 2, 3, ...) 로 등록 (v0.6.3, **v0.6.4 부터 글/카테고리/홈 모두 지원**). 사이트 공통 톤에서 완전히 벗어나고 싶다면 `use_common_css: false` 로 공통 CSS link 자체를 끊고 (v0.6.3), 더 나아가 `template: 'mine.html'` 또는 `template: './mine.html'` 로 자기 템플릿 파일까지 골라 쓸 수 있습니다 (v0.6.4). |
| **글마다 색인 정책** (v0.4.0) — 전역으론 검색 가능, 필요시 개별 비공개 | 전역 `<meta robots noindex>` 폐지. 비공개로 두려는 글은 그 글의 `meta.yaml` 에 `noindex: true` 한 줄. |
| **사이트 내 검색** — 클라이언트 JS 없이 한국어 친화 부분검색 | 빌드 시 `dist/search.php` 한 파일에 검색 엔드포인트 + 토크나이저 + BM25 함수 + 정적 인덱스가 모두 인라인 (v0.6.0). 카테고리 페이지 검색은 자동으로 해당 카테고리 내부로 한정. v0.4.0 부터 1글자 한국어는 인덱싱/쿼리 대상에서 제외, Python↔PHP 토크나이저 패리티를 빌드마다 자동 검증. **v0.5.0 부터 Okapi BM25 + 필드 가중치 + phrase 부스트**, **v0.6.0 부터 메타데이터 3-필드 (title / description / tags) 만 색인** — 흔한 토큰 vs 희귀 토큰, 짧은 글 vs 긴 글, 흩어진 매치 vs 정확한 phrase 매치를 점수가 합리적으로 반영합니다. PHP OPcache 활성화 시 인덱스가 메모리에 상주해 JSON 파싱 / 디스크 IO 0. |

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
12b. [YAML 파서 — 의도된 부분집합](#12b-yaml-파서--의도된-부분집합-scriptsyaml_parserpy)
13. [검색 기능 — search.php](#13-검색-기능--searchphp)
13b. [RSS / Atom 피드](#13b-rss--atom-피드-v053)
14. [배포 — 서버 업로드와 Apache 설정](#14-배포--서버-업로드와-apache-설정)
15. [트러블슈팅](#15-트러블슈팅)
16. [설계 원칙과 한계](#16-설계-원칙과-한계)
17. [업데이트 로그](#17-업데이트-로그)

---

## 1. 빠른 시작

### 준비물

- **Python 3.x** (3.8 이상 권장). 터미널에서 `python --version` 으로 확인.
- **Pillow** (v0.5.1 신설) — 빌드 시 raster 이미지 (.jpg .jpeg .png .gif) 를 WebP 다중 해상도 변종으로 자동 변환합니다. `pip install Pillow` 한 줄. 회피하려면 `site.yaml` 의 `images.enabled: false` 로 두면 Pillow 없이도 빌드 통과 (단 v0.5.0 처럼 원본 raster 가 그대로 dist 에 떨어지며, `loading="lazy"` 부착은 `images.lazy_loading: true` 면 별도 동작).
- **PHP CLI** (선택) — 빌드 시 search.php 의 토크나이저가 Python 토크나이저와 동등한지 자동 검증하는 데 사용됩니다. 없으면 패리티 검증만 워닝으로 건너뛰고 나머지 빌드는 정상 진행. (v0.4.0 까지는 마크다운 파싱에도 PHP 가 필수였지만 v0.4.1 부터는 마크다운도 순수 Python.)

### 빌드

이 폴더(`siheonlee.com_v0.7.2/`) 에서 터미널을 열고:

```bash
python build.py                # 평소 빌드 (캐시 사용 — v0.7.0 신설)
python build.py --clean        # dist/, .build_cache/ 모두 폐기 후 빌드
python build.py --clean-cache  # 캐시만 폐기, dist 는 유지
python build.py --no-cache     # 캐시 비활성 (v0.6.5 동작)
```

성공하면 다음과 같이 출력됩니다 (실제 글 수/카테고리 수는 `Articles/` 트리에 따라 다름):

```
빌드 시작...
[search] tokenizer parity OK (18 fixtures)
빌드 리포트: 보완 필요 / 살펴볼 사항 없음.

빌드 완료: <N> 글, <M> 카테고리, 0 보완 필요, 0 살펴볼 사항.
증분 캐시: <H> 히트 / <M> 미스 (글 <N>건).
산출물: dist/ (siheonlee.com).
```

첫 빌드는 항상 모든 글이 miss (캐시 비어있음). 두 번째 빌드부터 변경되지 않은 글은 hit — `Articles/` 의 한 글 content.md 만 바꾸면 그 글만 miss, 나머지는 hit. site.yaml / 템플릿 / 빌더 코드 변경 시 모든 글 invalidate.

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

**"PHP 기반 경량 웹 사이트 생성기"** 입니다. 글마다 폴더 하나를 만들어두면 `python build.py` 한 번으로 정적 HTML + PHP 엔드포인트 셋을 만들어내고, Apache 가 그걸 그대로 서빙합니다.

```
[이 시스템 (siheonlee.com)]
운영자 빌드 → 정적 HTML 파일 + 검색 PHP 생성 → 서버 업로드
방문자 요청
   ├─ 일반 페이지       → Apache 가 정적 HTML 그대로 응답  (빠름)
   └─ /search.php?q=… → PHP 가 인라인 정적 배열 인덱스로 BM25 검색 → 결과 HTML 렌더
                         (v0.6.0: 인덱스가 search.php 안에 인라인되어 OPcache 가 캐시. JSON 파싱 / 디스크 IO 0)
```

### 이 시스템의 특징

- **운영 의존성 최소** — Python 3 표준 라이브러리 (빌드) + PHP (런타임). `pip install`/`composer install` 없음, 클라이언트 JS 의존성 없음. v0.4.1 부터 빌드 머신에는 PHP 가 필요하지 않음 (마크다운 파서를 Python 으로 포팅).
- **PHP 활용 범위 (v0.4.1)** — 런타임 검색 엔드포인트 (search.php). 마크다운 파싱은 빌드 시점에 [scripts/parsedown.py](scripts/parsedown.py) (Parsedown 1.7.4 Python 포팅) 가 수행.
- **글 폴더 = 자율적인 단위** — 글마다 독립된 폴더에서 본문·이미지·보조파일을 자유롭게 관리.
- **URL 영구성 보장** — `slug` 가 곧 URL. 글을 다른 카테고리로 옮겨도 URL 이 안 바뀜.
- **글 단위 스타일 조정** — 본문의 p, h3, ul 등의 CSS 속성을 글마다 `meta.yaml` 에서 독립적으로 변경 가능.
- **글 단위 색인 제어** — 전역 noindex 없음. 검색엔진에서 빼고 싶은 글만 그 글의 `meta.yaml` 에 `noindex: true`.

### 전체 동작 원리

```
[작업 공간]
  Articles/               ← 글 원본 (마크다운 또는 HTML)
  templates/              ← 페이지 틀 (HTML 껍데기)
  assets/                 ← 사이트 공용 CSS, JS
  scripts/parsedown.py    ← 마크다운 파서 (Parsedown 1.7.4 Python 포팅)
  site.yaml               ← 사이트 전체 설정

       │
       ▼
  python build.py         ← 빌드 실행 (외부 의존성 없음)
       │
       ▼
  dist/                   ← siheonlee.com 에 배포
```

빌드는 다음 순서로 처리됩니다:

| 단계 | 내용 |
|---|---|
| 1 | `site.yaml` 읽기. (v0.4.1) 토크나이저 패리티 검증 — PHP CLI 가 있으면 자동 검증, 없으면 워닝 후 통과 |
| 2 | `Articles/` 트리를 뒤져 글 후보 수집 |
| 3 | 각 글의 `meta.yaml` 파싱 (제목, 날짜, SEO 설정, styles 등) |
| 4 | 검증: slug 중복 없는지, 날짜 형식이 맞는지 등 확인. 문제 있으면 BuildReport 의 issue 로 기록 + 그 글만 산출물 제외 (v0.5.5 부터 빌드 자체는 계속) |
| 5 | 글별 이미지/파일을 `dist/{slug}/` 로 복사 (v0.5.2: 옛 `dist/src/{slug}/` 폐지). v0.5.1 부터 raster 이미지 (.jpg .jpeg .png .gif) 는 Pillow 로 WebP 다중 해상도 변종으로 변환 |
| 6 | `assets/` → `dist/assets/` 복사 (raster 이미지는 5단계와 동일하게 WebP 변환) |
| 6b | 카테고리/홈의 외부 CSS 파일을 dist 로 명시 복사 (v0.6.4. 글의 외부 CSS 는 5단계에서 글 폴더 통째 복사로 함께 처리) |
| 7 | 각 글의 본문 렌더 (.md 는 파서 호출, .html 은 그대로) → 5/6 단계의 image_variants 정보로 본문 `<img>` 후처리 (WebP src + srcset + loading="lazy", v0.5.1) → styles 블록 inject → 템플릿에 끼워 넣어 `dist/{slug}/index.html` 생성 |
| 8 | 카테고리 색인 페이지 생성 (톱레벨 + 서브카테고리, v0.4.5) |
| 9 | 홈 페이지 생성 |
| 10 | 404 에러 페이지 생성 |
| 11 | `robots.txt` 생성 (Sitemap 디렉티브 포함, v0.4.4) |
| 12 | `sitemap.xml` 생성 (v0.4.4) |
| 12b | `feed.atom` / `feed.rss` 생성 (v0.5.3. 두 파일이 같은 entry 목록을 공유) |
| 13 | `dist/search.php` 단일 파일 생성 — 메타데이터 3-필드 (title / description / tags) BM25 인덱스 + 토크나이저 + 점수 계산기를 한 파일에 PHP 정적 배열 / 함수로 인라인 (v0.6.0) |
| 14 | 이전 빌드에서 삭제된 글의 파일 정리 (고아 정리) |

---

## 3. 폴더 구조

```
siheonlee.com_v0.7.2/
│
├── build.py              ← 빌드 진입점 (이것을 실행합니다)
├── site.yaml             ← 사이트 전역 설정
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
│   ├── search.py             ← 토크나이저, BM25 인덱스 빌드, Python BM25 참조 구현, Py↔PHP 패리티 테스트
│   ├── sitemap.py            ← sitemap.xml 빌더 (v0.4.4)
│   ├── images.py             ← (v0.5.1) WebP 다중 해상도 변환 + <img> 후처리 (srcset, sizes, loading=lazy)
│   ├── cache.py              ← (v0.7.0) 글 단위 빌드 증분 캐시 (BuildCache)
│   ├── report.py             ← (v0.5.5) BuildReport — 보완 필요/살펴볼 사항 수집·렌더 (v0.7.2: render_markdown)
│   └── builder.py            ← 빌드 파이프라인 (Builder 클래스)
│
├── templates/            ← 각 페이지 유형의 HTML 틀 + PHP 모듈
│   ├── article.html          ← 글 페이지 틀 ({{ROBOTS_META}}, {{ARTICLE_STYLES}} 등 변수 포함)
│   ├── category.html         ← 카테고리 목록 페이지 틀
│   ├── home.html             ← 홈 페이지 틀
│   ├── 404.html              ← 404 에러 페이지 틀
│   ├── search.php            ← 검색 결과 페이지 틀 (런타임 PHP, 라우팅/필터/렌더)
│   ├── search_tokenize.php   ← Python↔PHP 공통 토크나이저 (single source of truth). v0.6.0 부터 search.php 안에 인라인되어 dist 로 별도 복사 안 됨 (Py↔PHP 패리티 CLI 진단용 단일 진실원으로 유지).
│   └── search_bm25.php       ← (v0.5.0) BM25 점수 + 매치 밀도 스니펫 + 하이라이트. v0.6.0 부터 search.php 안에 인라인되어 dist 로 별도 복사 안 됨 (진단/테스트용 단일 진실원으로 유지).
│
├── tests/                ← 단위 테스트 + 진단 (v0.6.0 본격 확장)
│   ├── __init__.py
│   ├── test_bm25.py          ← BM25 알고리즘 회귀 차단 (31개)
│   ├── test_builder.py       ← (v0.6.0) Builder._inline_php_body / _wrap_page_title
│   ├── test_markdown.py      ← (v0.6.0) asset path / imgBox / 섹션 마커 / styles
│   ├── test_seo.py           ← (v0.6.0) truncate_description / build_meta_tags
│   ├── test_sitemap.py       ← (v0.6.0) URL / noindex / lastmod / excludes_categories
│   ├── test_feed.py          ← (v0.6.0) Atom/RSS 직렬화 / build_feed_document
│   ├── test_yaml_parser.py   ← (v0.6.0) scalar / list / map / literal block / 주석
│   ├── test_slugs.py         ← (v0.6.0) ASCII / 비ASCII / 공백·하이픈 축약
│   ├── test_report.py        ← (v0.6.0) BuildReport / abort / group_by_target
│   ├── test_parsedown.py     ← (v0.6.0) Python 포트의 기본 마크다운 요소
│   ├── test_php_literal.py   ← (v0.6.0) PHP array literal 직렬화 + PHP CLI round-trip
│   ├── test_cache.py         ← (v0.7.0) BuildCache 해시/lookup/store + 통합 빌드 시나리오
│   └── run_diagnostics.py    ← (v0.6.0) 진단 스크립트 — 5 항목 + 리포트 파일 생성
│
├── assets/               ← ★ 사이트 전역 자산 보관 장소 (v0.5.2 명시화)
│   │                       사이트 어디서든 `/assets/{경로}` 로 로드 가능. CSS/JS/
│   │                       공용 이미지/파비콘 등 여러 글·페이지가 공유하는
│   │                       자산은 모두 이 폴더에 둡니다. 글 단위 자산은
│   │                       글 폴더 안 (= dist 출력에서는 `/{slug}/...`).
│   ├── common_template.css
│   ├── imgslidebox.js
│   └── pagination.js
│
├── dist/                 ← 빌드 산출물 (siheonlee.com 에 배포)
│   └── ...               ← build.py 가 자동 생성. 직접 수정 금지.
│
├── build-report.md       ← (v0.7.2) 매 빌드 자동 생성/갱신. 진행 트랜스크립트 +
│                            요약 + 보완 필요/살펴볼 사항을 마크다운으로 서식화.
│                            dist/ 밖이라 배포·결정성과 무관. .gitignore 권장.
│
└── .build_cache/         ← (v0.7.0) 글 단위 증분 캐시 — build.py 가 자동 관리
    ├── manifest.json         ← {version, global_hash, articles: {slug: {hash, ...}}}
    └── articles/             ← 캐시된 글 페이지 산출물 (= 변경 안 된 글의 dist 복원본)
        ├── about.html
        ├── hello-world.html
        └── ...               ← 글 추가/삭제 시 자동 정리. `--clean` / `--clean-cache` 로 폐기.
                                 .gitignore 에 추가 권장 (버전 관리 대상 아님).
```

> **v0.4.1 변경:** `parsers/parsedown/` (Parsedown.php + run.php) 디렉터리가 사라지고, 그 자리에 `scripts/parsedown.py` (Parsedown 1.7.4 Python 포팅) 가 추가됐습니다. 빌드 머신의 PHP 의존성이 제거되었습니다.

> **v0.4.0 모듈 분할:** 직전 버전 (v0.3.2) 까지 2000+ 줄짜리 단일 `build.py` 였던 것이 `scripts/` 패키지로 분할되었습니다. 루트의 `build.py` 는 진입점일 뿐이고, 모든 실제 로직은 `scripts/` 안에 거주합니다.

> **중요:** `dist/` 안의 파일은 `python build.py` 를 실행할 때마다 덮어씌워집니다. 직접 수정하지 마세요. 수정이 필요하면 `Articles/`, `templates/`, `assets/`, `site.yaml` 을 고치고 다시 빌드하세요.

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

# v0.5.3: 글의 주제어 태그. 작성자가 직접 적습니다 (리스트).
# inline 형태 [a, b, c] 또는 block 형태 (`- a` 단위) 모두 허용.
# 현재 빌드 산출물에서 직접 쓰이는 곳은 feed.atom / feed.rss 의
# <category> 뿐이며, 검색·관련 글 등 미래 기능을 위한 토대로 파싱만
# 됩니다 (값 자체는 자유 — 한국어 다어절 태그도 허용).
tags: [intro, sample]

# v0.6.3: 사이트 공통 CSS (assets/common_template.css) link 출력 여부.
# 기본 true (옛 글 변경 의무 없음). false 면 link 태그 자체가 head 에서
# 출력되지 않아 이 글은 사이트 공통 톤을 완전히 끊고 자기 디자인만 적용.
# 글에서 완전히 새로운 서비스/랜딩페이지를 제공할 때 사용.
# use_common_css: false

# 글 단위 표현 제어 (두 채널 공존, 자세한 내용은 § 4-6).
#   - 정수 키 (1, 2, 3, ...) — 글 폴더 안의 외부 CSS 파일 상대 경로 (v0.6.3).
#                              정수 오름차순으로 head 의 link 출력.
#   - 문자열 키 (태그/선택자) — 인라인 CSS 룰. head 의 <style> 블록.
# 로드 순서: common_template.css → 외부 CSS (정수 키 순) → 인라인 <style>.
styles:
  # 1: style.css      # 글 폴더에 style.css 를 두고 외부 CSS 로 등록한 예
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
| `tags` (v0.5.3) | — | 글의 주제어 태그 (문자열 리스트). 작성자가 직접 적음. 현재 feed.atom / feed.rss 의 `<category>` 에 포함. 빈 문자열·중복 자동 제거 | `[intro, sample]` |
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

> **`seo_keywords` 필드는 제공하지 않습니다.** `<meta name="keywords">` 는 1990년대 이래 주요 검색엔진이 무시하는 태그입니다.

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
<!-- 빌드 후 (v0.5.2: 글 자산이 글 폴더 안으로 일원화) -->
<img src="/my-slug/imgs/photo.jpg" alt="photo">
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

<!-- 빌드 후 이렇게 변환됩니다 (v0.5.2: 글 자산이 글 폴더 안으로 일원화) -->
<div class="imgBox">
  <img src="/my-slug/imgs/photo.jpg" alt="alt 텍스트">
  <p class="caption">캡션 텍스트</p>
</div>
```

**imgSlideBox — 슬라이드 이미지:**
```html
<!-- content.html 에 이렇게 쓰면 -->
<?php imgSlideBox("./src_slide") ?>

<!-- 빌드 후: src_slide/ 안의 이미지를 알파벳 순으로 슬라이드로 만듦 -->
<div class="imgSlideBox" data-slug="my-slug">
  <img src="/my-slug/src_slide/01.jpg" class="slide active">
  <img src="/my-slug/src_slide/02.jpg" class="slide">
  <button class="prev">‹</button>
  <button class="next">›</button>
</div>
```

이 두 함수 외의 `<?php ... ?>` 코드는 그대로 보존됩니다. 이 경우 빌드는 해당 글을 `.html` 이 아닌 `.php` 확장자로 출력합니다 (PHP 자동 감지, § 8 참조).

### 4-5. 이미지/파일 첨부하기

#### 글 단위 자산 — 글 폴더 안에 둡니다 (v0.5.2 일원화)

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

`meta.yaml`, `content.md`, `content.html` 을 제외한 **모든 파일과 폴더** 는 그대로 `dist/{slug}/` (= 글의 index.html 과 같은 폴더) 로 복사됩니다.

접근 URL:
```
https://siheonlee.com/my-first-post/imgs/사진1.jpg
https://siheonlee.com/my-first-post/files/자료.pdf
```

> **v0.5.2 변경:** v0.5.1 까지는 글 자산이 `dist/src/{slug}/` 하위 트리에 떨어졌고 URL 도 `/src/{slug}/...` 였습니다. v0.5.2 에서 자산 경로를 일원화하여 글의 index.html 과 같은 폴더에 두도록 변경했습니다.

#### 사이트 전역 자산 — `assets/` 에 둡니다

여러 글이 공유하는 자산 (공용 CSS, JS, 파비콘, 로고, 디폴트 OG 이미지 등) 은 프로젝트 루트의 `assets/` 폴더에 두면 빌드 시 `dist/assets/` 로 그대로 복사됩니다. 사이트 어디서든 `/assets/{경로}` 로 로드할 수 있습니다.

```
assets/
├── common_template.css   → /assets/common_template.css
├── pagination.js         → /assets/pagination.js
├── favicon.ico           → /assets/favicon.ico
└── default-og.png        → /assets/default-og.png
```

**언제 글 폴더에 두고 언제 `assets/` 에 두나:**

- 그 글에만 쓰이는 첨부 (글 본문의 이미지, 첨부 PDF, 한 글 전용 보조 HTML 등) → **글 폴더 안에**.
- 여러 글·페이지·템플릿이 공유하는 자산 (공용 CSS, JS, 사이트 로고, 파비콘, 디폴트 OG 이미지) → **`assets/` 에**.

이 이분법이 v0.5.2 의 자산 정책입니다 — `dist/src/` 라는 제3의 위치는 더 이상 없습니다.

#### 보조 HTML/PHP 페이지도 그대로 보존됩니다

```
Articles/Blog/프로젝트/
├── meta.yaml
├── content.md
└── log/
    ├── day1.html    ← 자체 <html><head><body> 있는 독립 HTML
    └── day2.html
```

이 경우 `https://siheonlee.com/project-slug/log/day1.html` 로 직접 접근할 수 있습니다.

### 4-6. styles — 글 단위 CSS 오버라이드 (인라인 미세 채널 + 외부 파일 채널)

**한 글의 표현을 두 채널로 제어** 할 수 있습니다 — 인라인 룰 (자주 쓰이는 작은 속성 override 의 미세 채널) 과 외부 CSS 파일 (글이 자기 CSS 파일을 가질 자격이 있을 때의 본격 디자인 채널, v0.6.3 부터). 두 채널은 `meta.yaml` 의 같은 `styles:` 키 아래 자유롭게 공존합니다 — *키의 타입* 으로 자동 분기됩니다.

| 채널 | 키 형태 | 값 | 출력 위치 | 의도 |
|---|---|---|---|---|
| 인라인 룰 | 문자열 (태그/선택자) | dict (속성:값) | head 의 `<style>` 블록 | *자주 사용되는 일부 속성의 미세 override*. at-rule / 중첩 / 변수 / 의사클래스 조합 등은 표현 불가 — 의도된 한계. |
| 외부 CSS 파일 *(v0.6.3)* | 정수 (1, 2, 3, ...) | 글 폴더 안의 상대 경로 문자열 | head 의 `<link rel='stylesheet'>` | 더 큰 자유도가 필요한 글이 자기 CSS 파일을 가진다. 정수 키 오름차순이 link 출력 순서. |

**로드 순서 (cascading)**: `assets/common_template.css` → 외부 CSS (정수 키 순) → 인라인 `<style>`. 인라인이 마지막 발언권 — 두 채널을 같은 글에서 동시에 쓰면 인라인이 외부 CSS 의 같은 규칙을 이깁니다. ("미세 override" 의도와 부합.)

```yaml
# meta.yaml — 두 채널 공존 예
styles:
  1: layout.css         # 외부: 글 폴더 안의 layout.css → head 에 <link>
  2: theme.css          # 외부: 두 번째로 출력 (정수 오름차순)
  p:                    # 인라인: p 태그 미세 override
    text-indent: 0
  blockquote:
    border-left: 3px solid #0172d5
```

**`use_common_css: false` 토글 (v0.6.3)** — 사이트 공통 CSS link 자체를 head 에서 끊습니다. 글에서 완전히 새로운 디자인 / 랜딩페이지 / 단일 페이지 서비스를 제공할 때 사용. 기본값 `true` 라 모든 옛 글은 변경 의무 없음. **카테고리/홈에는 이 토글이 없습니다** — 카테고리/홈은 사이트 공통 톤에서 벗어날 가능성이 매우 희박하다는 정책 (영구적).

```yaml
# meta.yaml — 완전히 새로운 디자인 제공
use_common_css: false   # 사이트 공통 CSS link 제거
styles:
  1: landing.css        # 이 글만의 디자인을 모두 담은 외부 CSS
```

> **이 절의 모든 후속 안내 (동작 원리 / 기본 사용법 / 복합 선택자 등) 는 *인라인 룰 채널* 기준입니다.** 외부 CSS 파일 채널은 글 폴더의 진짜 `.css` 파일에서 자유롭게 작성하면 되며, 빌더가 자동으로 `dist/{slug}/<rel>` 로 복사 + head 에 `<link href='/{slug}/<rel>'>` 출력합니다 (v0.5.2 자산 경로 일원화).

#### 동작 원리 (인라인 채널)

`meta.yaml` 의 `styles:` 키 *안의 문자열 키* (태그/선택자) 가 article.html 의 head 영역에 `<style>` 블록으로 inject 됩니다.

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

**인라인 채널에서 근본적으로 안 되는 것 (의도된 한계 — 외부 CSS 파일 채널로 자연 승격):**

| 한계 | 어떻게 풀까 |
|---|---|
| `@media` 쿼리 | 글 폴더 안에 진짜 CSS 파일을 두고 `styles: { 1: my.css }` 로 등록. (v0.6.3) |
| `@keyframes`, `@supports`, `@font-face`, `@import` | 위와 동일 — 모든 at-rule 은 외부 CSS 파일에서 자유롭게 작성. |
| CSS 중첩 / 변수 (`--foo`) 의 본격 활용 | 외부 CSS 파일 권장. 인라인 채널은 단순 키-값 dict 만 표현 가능 (의도된 제약). |
| 한 속성을 여러 줄에 나눠 쓰기 | YAML 한 줄로 작성. (`box-shadow: 0 1px 2px rgba(0,0,0,.1), 0 2px 4px rgba(...)`) |
| 값 라인 옆 인라인 주석 (`text-indent: 0  # 들여쓰기 제거`) | 주석이 값에 포함됨. 주석은 별도 줄에. |

> **인라인 채널의 표현력 한계는 결함이 아닙니다.** "자주 사용되는 일부 작은 속성을 사용자 편의성을 위해 YAML 에서 기술할 수 있도록 지원" 이 이 채널의 본분 — 더 큰 자유도가 필요한 글은 그 글의 폴더 안에 자기 CSS 파일을 두는 편이 자연스러운 위치 (v0.6.3 의 정수 키 채널 도입 동기).

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

> **v0.4.4 까지의 동작 (참고):** 톱레벨만 인덱스 페이지가 있었고, 서브카테고리 URL 은 404 였습니다. v0.4.5 에서 이 동작을 해제했습니다. sitemap.xml 도 서브카테고리 URL 을 포함합니다.

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
| `layout` | `list` | `list` (텍스트 한 줄) / `gallery` (이미지 타일, v0.5.3) 두 종을 기본 제공. 그 외 값은 빌드 통과 + `list` 로 폴백 — *추가 layout 이 필요하면 빌더 코드 (`_listup_items_html` / `_render_section` / CSS) 에 직접 등록*. |
| `styles` | 빈 매핑 | 이 카테고리 인덱스 페이지에만 적용할 CSS. 두 채널 — 정수 키 (1, 2, 3, ...) 는 카테고리 폴더 안의 외부 CSS 파일 상대 경로, 문자열 키 (tag/selector) 는 인라인 룰. 글의 `styles:` 와 같은 포맷 (v0.6.4 부터 통일). |
| `use_common_css` | `true` | v0.6.4. `false` 면 사이트 공통 CSS link 자체를 head 에서 끊고 외부/인라인만 적용. |
| `template` | 없음 (`category.html`) | v0.6.4. 이 카테고리 인덱스 페이지에 사용할 템플릿 파일. `name.html` → `templates/` 에서, `./name.html` → 이 카테고리 폴더에서. |
| `lang` | site.yaml `lang` | 이 카테고리 인덱스 페이지의 `<html lang>` 오버라이드. |

`per_page > preview_per_page` 가 자연스러운 사용법입니다 — 소분류의 자기 페이지는 글을 더 많이 보여주고, 상위에 임베드된 section 은 미리보기 수준으로 적게 보여주는 정책.

**예시 (서브카테고리 meta.yaml):**

```yaml
per_page: 20         # /blog/tutorials/ 자기 페이지 — 페이지당 20개
preview_per_page: 5  # /blog/ 의 Tutorials section 임베드 시 — 페이지당 5개
layout: list
```

#### `layout: gallery` — 이미지 타일 갤러리 (v0.5.3)

`layout: gallery` 로 두면 그 카테고리의 글 목록이 텍스트 한 줄이 아니라 **이미지 타일** 로 렌더됩니다. 각 타일은 `<a>` 한 개에 썸네일 + 제목 + 날짜를 담고, CSS Grid (`repeat(auto-fill, minmax(220px, 1fr))`) 로 컨테이너 폭에 따라 자동으로 칸 수가 조정됩니다.

```yaml
# Articles/Blog/Tutorials/meta.yaml
per_page: 6
preview_per_page: 4
layout: gallery
```

**썸네일 결정 규칙 (v0.5.5 의 본문 ↔ 메타데이터 분리 원칙, § 16 의 설계 원칙 10):**

1. 글의 `seo.og_image` 가 있으면 그 값.
2. 없으면 `site.yaml` 의 `default_og_image` (사이트 기본).
3. 둘 다 없으면 **빈 플레이스홀더** (옅은 그라데이션 배경).

> **v0.5.5 변경:** v0.5.4 까지 있던 "본문 첫 이미지" 폴백을 폐지. 빌더가 author 의 의도와 무관하게 본문에서 이미지를 긁어가는 동작 (SNS 미리보기가 본문 첫 이미지를 임의로 가져가는 행동의 자동화) 을 없애기 위한 정책.

빌드 시 이미지 자동 최적화 (v0.5.1) 와 자연스럽게 연동됩니다 — raster 썸네일이라면 webp 변종 + srcset + `sizes` + `loading="lazy"` 가 자동으로 부착됩니다. 별도 작업 없이 그대로 동작.

**디자인 메모:** modern minimal 톤. 흰 카드 (border-radius 6px) + 4:3 강제 크롭 (`aspect-ratio: 4/3; object-fit: cover`) + subtle hover (`translateY(-2px)` + 0.04 scale + soft shadow). 모바일 (`max-width: 600px`) 에서는 자동으로 2열 그리드로 좁아집니다. 이 톤은 nav-search / pagination 과 일치하도록 의도적으로 맞췄습니다 — 갤러리가 콘텐츠를 압도하지 않게.

**페이지네이션·서브카테고리 임베드 동작:** `list` 와 동일. `per_page` / `preview_per_page` 가 그대로 적용되며, 상위 카테고리에 section 으로 임베드될 때도 그 자식 카테고리의 `layout` 을 따릅니다 (Tutorials 가 gallery 면 Blog 페이지의 Tutorials section 도 gallery).

#### layout 을 더 늘리고 싶다면 (직접 등록)

기본 제공 `list` / `gallery` 두 종으로 일반 사용은 충분하다는 판단입니다. 표 형식·카드형 텍스트·매거진 그리드 등 다른 layout 이 필요하면 빌더 코드에 직접 등록하세요 — 핵심 진입점은 [scripts/builder.py](scripts/builder.py) 의 `_listup_items_html(..., layout=)` / `_render_section(..., layout=)` 분기와 새 타일 렌더 함수 (`_gallery_tile_html` 와 같은 형태) 추가, 그리고 [assets/common_template.css](assets/common_template.css) 의 `section.listup-{layout}` 와 짝이 되는 CSS 입니다. pagination.js 의 selector (`.listup-list > *, .gallery-tile`) 에도 새 타일 selector 를 추가하면 페이지네이션이 자동 동작합니다.

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
python build.py
# dist/my-first-post/ 가 자동으로 삭제됩니다
```

---

## 7. 빌드

### 명령어

```bash
# 일반 빌드
python build.py

# dist/ 를 완전히 지우고 새로 빌드
python build.py --clean
```

### 빌드 성공 예시

```
빌드 시작...
[search] tokenizer parity OK (18 fixtures)
빌드 리포트: 보완 필요 / 살펴볼 사항 없음.

빌드 완료: 5 글, 3 카테고리, 0 보완 필요, 0 살펴볼 사항.
산출물: dist/ (siheonlee.com).
```

v0.4.1 부터 마크다운 파서는 [scripts/parsedown.py](scripts/parsedown.py) 하나만 사용되므로 별도 표기는 없습니다. (v0.4.0 까지의 `[markdown] using parser: parsedown` 줄은 사라졌습니다.)

### 빌드 리포트 (v0.5.5 부터)

v0.5.5 부터 콘텐츠 측 문제는 빌드를 중단시키지 않고 *글 단위로 산출물 일부를 누락* 한 채 빌드를 완성합니다. 빌드 종료 시 stderr 에 다음과 같이 두 묶음으로 정렬되어 표시됩니다:

```
── 보완이 필요한 항목 (산출물 일부 누락 가능) ──
  [article] my-slug
      - seo.description 누락 — 검색 결과·SNS 미리보기·피드 summary 에서 이 글이 빠집니다.
        (Articles/Blog/나의 첫 글/meta.yaml)

── 살펴볼 사항 (산출물 정상) ──
  [category] Blog/Archive
      - 글이 없는 빈 카테고리.

빌드 리포트 요약: 보완 필요 1건, 살펴볼 사항 1건.
```

| 분류 | 의미 | 대표 사례 |
|---|---|---|
| **issue** (보완 필요) | 작성자가 손봐야 할 글 단위 문제. 빌드는 계속 진행되지만 해당 글의 산출물이 부분적으로 누락. | `seo.description` 누락/빈 문자열 (v0.5.5 부터 필수), slug 정규식 불일치, slug 예약어 충돌, slug 중복 (나중 발견된 쪽이 제외), slug ↔ 카테고리 폴더 슬러그 충돌 (글 쪽이 제외), date 형식 오류, `tags` 가 list 가 아님 |
| **warning** (살펴볼 사항) | 산출물 자체는 정상이지만 한 번 살펴볼 가치가 있는 사항. | 비ASCII 폴더명 → 자동으로 hex 코드포인트 slug 로 변환, `meta updated` 가 파일 mtime 보다 오래됨, 본문에 참조된 자산 누락, `_` 접두 자산 참조, 빈 카테고리, 이미지 최적화 실패 (원본 폴백) |

> **v0.5.5 변경:** v0.5.4 까지 abort 였던 slug 중복 / 정규식 불일치 / 형식 오류가 이제 모두 issue 입니다. 위반한 글만 산출물에서 제외하고 나머지 빌드는 정상 진행 — 한 번의 빌드로 모든 보완 지점을 파악할 수 있습니다.

### 빌드 중단 (시스템 결함만)

콘텐츠 작성자가 통제할 수 없는 *시스템 결함* 만 빌드를 즉시 중단시킵니다:

```
[ABORT] templates/article.html 을 찾을 수 없습니다
빌드 중단 (시스템 결함).
```

| 시스템 결함 | 원인 | 대처 |
|---|---|---|
| `templates/<...> 을 찾을 수 없습니다` | 템플릿 파일 누락 | 저장소 클론 상태 확인 |
| `Articles/ 디렉터리가 없습니다` | 작업 루트 잘못 잡힘 | 프로젝트 루트에서 `python build.py` 실행 |
| `Pillow 가 설치되어 있지 않습니다` | 이미지 최적화 활성 (`images.enabled: true`) 인데 Pillow 미설치 | `pip install Pillow` 또는 `site.yaml` 에서 `images.enabled: false` |
| `site.yaml 파싱 실패` | YAML 문법 오류 | 오류 라인의 들여쓰기 / 따옴표 확인 |

---

## 8. 산출물 구조와 URL

### dist/ 구조 (siheonlee.com 에 배포)

```
dist/
├── index.html                       ← 홈 페이지 (/)
├── 404.html                         ← 404 에러 페이지 (Apache 가 라우팅)
├── robots.txt                       ← 검색엔진 크롤 정책 (Sitemap 디렉티브 포함, v0.4.4)
├── sitemap.xml                      ← 사이트맵 (v0.4.4)
├── feed.atom                        ← Atom 1.0 피드 (v0.5.3)
├── feed.rss                         ← RSS 2.0 피드 (v0.5.3)
│
├── assets/                          ← 사이트 공용 자원 (전역)
│   ├── common_template.css          ← 공용 스타일시트
│   ├── imgslidebox.js               ← 슬라이드 이미지 스크립트
│   ├── pagination.js                ← 페이지네이션 스크립트 (v0.4.5)
│   └── default-og.png               ← 기본 OG 이미지 (직접 추가 필요)
│
├── {slug}/                          ← 글 페이지 + 글의 자산 (v0.5.2 부터 같은 폴더)
│   ├── index.html  (또는 index.php) ← PHP 토큰이 있으면 .php
│   └── imgs/ ...                    ← 글 폴더의 자산이 글 페이지 옆에 동거
│
├── blog/                            ← 카테고리 색인 페이지
│   ├── index.html
│   └── tutorials/                   ← 서브카테고리 색인 (v0.4.5)
│       └── index.html
│
└── search.php                       ← 검색 — 인덱스 + 토크나이저 + BM25 함수 모두 인라인 (v0.6.0)
```

### URL 구조

| 페이지 | URL 형식 | 예시 |
|---|---|---|
| 홈 | `/` | `https://siheonlee.com/` |
| 글 | `/{slug}/` | `https://siheonlee.com/mask-intake-3d-printing/` |
| 카테고리 (톱레벨만) | `/{cat-slug}/` | `https://siheonlee.com/blog/` |
| 글 첨부파일 (v0.5.2) | `/{slug}/{경로}` (글 index.html 과 같은 폴더) | `https://siheonlee.com/mask-intake-3d-printing/imgs/photo.jpg` |
| 사이트 전역 자산 | `/assets/{경로}` (CSS/JS/공용 이미지 등) | `https://siheonlee.com/assets/common_template.css` |
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

결과 (v0.5.2: 글 자산이 글 폴더 안으로 일원화):
```html
<div class="imgBox">
  <img src="/{slug}/imgs/photo.jpg" alt="이미지 설명">
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

글 / 홈 / 카테고리 페이지가 같은 폴백 체인을 공유합니다 (v0.6.2 부터 한 함수 [`build_meta_tags`](scripts/seo.py) 로 통일). `meta.yaml` 의 SEO 필드를 모두 비워도 빌드는 정상 동작하지만, `seo.description` 은 사실상 필수입니다 (누락/빈 문자열 시 BuildReport 의 issue 에 기록 — v0.5.5 도입, v0.6.2 에서 홈/카테고리에도 확장).

페이지별 본문 title 결정:
- **글** — `meta.yaml` 의 `title` 필드
- **홈** — `Articles/meta.yaml` 의 `title` > `site.name`
- **카테고리** — `Articles/<경로>/meta.yaml` 의 `title` > 카테고리 폴더명

| 출력 태그 | 1순위 | 2순위 | 3순위 |
|---|---|---|---|
| `<title>` | `{seo.title_prefix}{title}{seo.title_suffix}` (글 v0.4.3, 홈/카테고리 v0.5.4) | site 디폴트로 prefix/suffix 폴백 | — |
| `meta description` | `seo.description` | — *본문 폴백은 v0.5.5 에서 폐기* | 출력 생략 + BuildReport 의 issue 기록 |
| `meta author` | `seo.author` | `site.yaml 의 default_author` | 출력 생략 |
| `link canonical` | `seo.canonical` | 자동 생성 — 글 `/{slug}/`, 홈 `/`, 카테고리 `/{top}/{sub}/` | — |
| `og:title` | `seo.og_title` | `<title>` 결과 | — |
| `og:description` | `seo.og_description` | `meta description` 결과 | 출력 생략 |
| `og:image` | `seo.og_image` | `site.default_og_image` | 출력 생략 *(v0.5.5 부터 본문 폴백 폐기)* |
| `og:image:alt` | `seo.og_image_alt` | 페이지 본문 title | 출력 생략 |
| `og:type` | `seo.og_type` | 페이지 종류별 디폴트 — 글 `article`, 홈/카테고리 `website` *(v0.6.2)* | — |
| `og:url` | (canonical 과 동일) | — | — |
| `og:site_name` | `site.yaml 의 name` | — | — |
| `article:published_time` | 글의 `date` *(글에만 출력)* | — | — |
| `article:modified_time` | 글의 `updated` (없으면 `date`) *(글에만 출력)* | — | — |
| `twitter:card` | `seo.twitter_card` | `'summary_large_image'` | — |
| `twitter:title` | (og:title 과 동일) | — | — |
| `twitter:description` | (og:description 과 동일) | — | 출력 생략 |
| `twitter:image` | `seo.twitter_image` | `og:image` 결과 | 출력 생략 |

**폴백 결과가 빈 문자열이면 해당 태그 자체를 출력하지 않습니다.** `<meta name="description" content="">` 같은 빈 태그는 절대 생성되지 않습니다. `''` (빈 문자열) 과 `None` (키 부재) 은 산출물에서는 동일하게 태그 누락으로 처리되지만, `seo.description` 의 경우에 한해 `''` 는 작성자 실수로 간주하여 BuildReport 에도 기록됩니다 (자세한 의미는 [§ 16 의 설계 원칙 10](#16-설계-원칙과-한계) 참조).

> **v0.4.0 색인 정책:** 사이트 전체 페이지는 검색엔진 색인이 **기본 허용** 입니다. 글마다 `meta.yaml` 에 `noindex: true` 를 추가하면 그 한 페이지의 `<head>` 에만 `<meta name='robots' content='noindex'>` 가 들어가 검색엔진에서 빠집니다. 홈/카테고리/404 페이지에는 noindex 가 없으며 (= 색인 허용), search.php 만 `noindex,follow` 로 별도 차단됩니다.
>
> v0.3.x 까지는 모든 페이지에 noindex 가 박혀 있어 위 SEO 폴백 체인이 출력만 되고 실효는 없는 dead code 였습니다. v0.4.0 부터는 실제로 검색 노출에 영향을 줍니다.
>
> **v0.4.3 변경:** SEO 필드들이 `seo:` 하위 블록으로 그룹화되었습니다 (예: `seo_description` → `seo.description`). meta.yaml frontmatter 가 한눈에 보입니다.
>
> `<meta name="keywords">` 는 v0.4.0 에서 제거되었습니다 — 주요 검색엔진이 무시하는 태그입니다.
>
> **v0.4.4 변경:** [sitemap.xml](sitemap.xml) 자동 생성. 모든 non-noindex 글 + 톱레벨 카테고리 + 홈을 sitemaps.org 0.9 스키마로 출력합니다. lastmod 는 `updated` (없으면 `date`). robots.txt 의 `Sitemap:` 디렉티브가 자동 활성화되어 검색엔진이 sitemap 을 자동 발견합니다.
>
> **v0.5.5 변경:** SEO description / og_image / 갤러리 썸네일 / 피드 summary 의 **본문 폴백 폐기** ([§ 16 의 설계 원칙 10](#16-설계-원칙과-한계) 참조). author 가 `meta.yaml` 의 `seo:` 블록에 명시한 값만 사용. `seo.description` 누락 시 빌드는 통과하지만 BuildReport 의 issue 에 기록되어 작성자가 보완할 수 있도록 안내.
>
> **v0.6.2 변경:** 홈 / 톱레벨 카테고리 / 서브카테고리 페이지에도 글과 동일한 메타 태그 묶음이 출력됩니다 (description / og_* / twitter_* / link canonical). v0.5.4 부터 한계 표에 있던 항목 해소. 홈은 `Articles/meta.yaml` 의 `seo:` 블록, 카테고리는 `Articles/<카테고리>/meta.yaml` 의 `seo:` 블록을 사용하며, 폴백 체인은 위 표와 동일. `og:type` 의 디폴트만 페이지 종류 별로 갈라집니다 (글=article, 홈/카테고리=website — OGP 표준 권장). `article:published_time` / `article:modified_time` 는 글에만 출력됩니다.

---

## 11. 사이트 전역 설정 — site.yaml

`site.yaml` 은 *진짜 전역* (= 여러 페이지에 공통 적용되는 설정) 만 둡니다. 잘 변경할 일이 없지만, 사이트 정보가 바뀌면 여기를 수정합니다.

### 11-1. 설정 책임 분리 (v0.4.6 의 규약)

**페이지 한 종에만 적용되는 설정은 site.yaml 에 두지 않고 그 페이지의 meta.yaml 에 둡니다.** 글·카테고리·홈 전체에 일관적으로 적용되는 원칙:

| 어디에 설정 두는가 | 어떤 설정 |
|---|---|
| `site.yaml` | 사이트 전역 (도메인, name, copyright, lang 디폴트, default_og_image 등) / 여러 페이지에 공통 적용되는 디폴트 (`category_per_page`, `category_preview_per_page`) / robots.txt 본문 / reserved_slugs / warn_on_* / `description_truncate` / `images:` (v0.5.1, 이미지 최적화 정책) / `error_404_title` `search_title` (v0.5.4, meta.yaml 이 없는 시스템 페이지의 `<title>` 본문) |
| `Articles/meta.yaml` (v0.4.6) | 메인페이지 (= 사이트 루트, 홈) 전용 — `per_page`, `excludes_categories`, `lang`, `layout`, `styles`, `title` (v0.5.4), `seo:` (v0.5.4) |
| `Articles/<카테고리>/meta.yaml` (v0.4.5) | 그 카테고리 인덱스 페이지 전용 — `per_page`, `preview_per_page`, `priority` (v0.4.6), `nav_priority` (v0.5.4, 톱레벨 카테고리에서만 의미), `lang`, `layout`, `styles`, `title` (v0.5.4), `seo:` (v0.5.4) |
| `Articles/<카테고리>/<글>/meta.yaml` | 그 글 페이지 전용 — `slug`, `title`, `date`, `updated`, `noindex`, `lang`, `seo:`, `styles` (v0.6.3 부터 외부 CSS 파일 매핑도 같은 키), `tags` (v0.5.3), `nav_priority` (v0.5.4, 톱레벨 글에서만 의미 — 예: About), `use_common_css` (v0.6.3, 사이트 공통 CSS link 출력 여부 — 기본 true) |

> **v0.4.6 의 변경:** 옛 site.yaml 의 메인페이지 전용 키 3개 (`home_per_page` / `home_excludes_categories` / `home_sort`) 가 모두 `Articles/meta.yaml` 로 이전되었습니다 (`home_sort` 는 빌더가 사용한 적 없는 dead field 라 그대로 폐기). 옛 키를 site.yaml 에 그대로 두면 빌드는 진행되지만 무시되며 워닝이 출력됩니다.

### 11-2. site.yaml 예시 (v0.7.2 기준)

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

# 모든 페이지 <title> 의 기본 prefix/suffix (글, 홈, 카테고리, 404, search).
# v0.5.4 부터 홈/카테고리/404/search 도 같은 폴백 체인 적용.
# 페이지 단위 override:
#   - 글 / 홈 / 카테고리: 그 페이지의 meta.yaml `seo.title_prefix` / `seo.title_suffix`
#   - 404 / search: 페이지 단위 override 불가능 (시스템 페이지, meta.yaml 없음)
default_title_prefix: ""
default_title_suffix: ""

# v0.5.4 신설: 시스템 페이지 (404 / search) 의 <title> 본문 텍스트.
# 양옆은 위의 default_title_prefix / default_title_suffix 로 감싸진다.
# 비우면 각각 "Not Found" / "Search" 디폴트.
error_404_title: Not Found
search_title: Search

# 저작권 표시
copyright_holder: 이시헌
copyright_year_start: 2025

# 글 slug 로 사용 금지된 예약어 목록.
# v0.4.0 정리: 실제 디렉터리/엔드포인트와 충돌할 수 있는 항목만 유지.
# v0.5.2: 글 자산이 `/src/{slug}/` → `/{slug}/` 로 옮겨가면서 `src` 는 더
#         이상 충돌 가능 디렉터리가 아니라 reserved 에서 제거. 두 항목만 남음.
reserved_slugs:
  - assets    # /assets/    — 사이트 전역 자산 디렉터리
  - search    # /search.php — 검색 엔드포인트

# v0.4.5: 카테고리 페이지네이션 디폴트 (카테고리 폴더의 meta.yaml 로 오버라이드).
#   category_per_page         — 카테고리 인덱스가 자기 자신의 글 목록을 표시할 때
#   category_preview_per_page — 그 카테고리가 상위 카테고리 페이지에 section 으로 임베드될 때
# (메인페이지의 페이지당 글 수는 Articles/meta.yaml 의 per_page.)
category_per_page: 20
category_preview_per_page: 5

# meta description 자동 추출 시 최대 글자 수.
# v0.5.4 부터 영문 단어 경계 존중 — 절단 지점이 ASCII 영문/숫자 시퀀스
# 한가운데이면 직전 공백까지 backup. 한국어 등 CJK 는 글자 단위가 의미
# 단위라 그대로 절단 가능.
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

# v0.5.1: 이미지 자동 최적화 정책. 전체를 생략해도 아래 기본값으로 동작.
#   enabled       — 전체 토글. false 면 Pillow 없이 빌드 통과 (raster 이미지는
#                   v0.5.0 처럼 그대로 dist 에 복사). lazy_loading 만 따로 켤 수
#                   있어, Pillow 없는 환경에서도 loading="lazy" 는 부착 가능.
#   widths        — 생성할 WebP 변종 너비 (px). 원본 width 이하만 실제 파일이 생성됨.
#   max_width     — 원본이 이보다 크면 다운스케일. widths 의 max 와 동기화면 충분.
#   quality       — WebP 인코더 quality (0~100). Google 권장 85.
#   lazy_loading  — 모든 <img> 에 loading="lazy" 자동 부착. enabled=false 여도 독립.
#   default_sizes — srcset 과 짝이 되는 sizes 디폴트. siheonlee.com main column 800px 기준.
images:
  enabled: true
  widths: [400, 800, 1600]
  max_width: 1600
  quality: 85
  lazy_loading: true
  default_sizes: "(max-width: 800px) 100vw, 800px"

# v0.4.1: markdown_parser 옵션 폐지. 마크다운 파서는 단일 (scripts/parsedown.py)
# 로 통일되어 사이트 설정에서 선택할 필요가 없습니다. 기존 설정은 무시됩니다.
```

### 11-3. Articles/meta.yaml — 메인페이지 (= 홈) 전용 설정 (v0.4.6)

메인페이지 (사이트 루트) 의 카테고리-격 설정 파일입니다. 카테고리 폴더의 meta.yaml 과 동일 스키마 — 빌더는 이 둘을 같은 코드 경로 (`_parse_category_meta_file`) 로 파싱합니다. 단 같은 스키마를 두 위치가 공유하다 보니 *위치 때문에 의미가 없어지는 필드* 가 있습니다 — `preview_per_page` 는 홈이 어디에도 임베드되지 않으므로 적용 대상이 없고, `priority` 도 홈이 톱레벨 카테고리들과 같은 페이지에 함께 표시되지 않아 무시됩니다. 이 비대칭은 의도된 설계 (한 스키마를 공유) 이며 잘못된 값을 적어도 빌드는 통과합니다.

같은 비대칭이 카테고리 meta.yaml 에도 한 갈래 더 있습니다 — `preview_per_page` 는 *톱레벨 카테고리* 에는 사실상 의미가 없습니다 (상위가 없어 어디에도 임베드되지 않으므로). 서브카테고리에서만 실제 효과가 나타납니다.

```yaml
# 메인페이지 Recent posts 의 페이지당 글 수.
# 비우면 빌더의 코드 디폴트 (= Builder.HOME_PER_PAGE_DEFAULT, 현재 5).
per_page: 5

# Recent posts 에서 제외할 톱레벨 카테고리 폴더명 (리스트).
# 비우면 [] — 모든 톱레벨이 Recent 에 포함됨. About 처럼 글 목록에 섞여서는
# 안 되는 카테고리를 적어 두는 자리. (v0.4.5 까지는 site.yaml 의
# home_excludes_categories.)
excludes_categories: [About]

# 'list' (기본) / 'gallery'. v0.5.3 부터 메인페이지도 gallery 지원
# (썸네일 규칙·반응형 동작 모두 카테고리와 동일 — § 5 의 layout: gallery 절 참조).
layout: list

# 메인페이지의 <html lang> 오버라이드 (비우면 site.yaml 의 lang).
# lang: ko

# v0.6.4: 메인페이지의 외부 CSS / 인라인 룰 — 글·카테고리와 같은 styles 두 채널.
# 정수 키 = 외부 CSS 파일 (위치: Articles/<filename>, URL: /<filename>),
# 문자열 키 = 인라인 룰 (글의 styles 와 동일 포맷).
# styles:
#   1: home.css
#   p:
#     line-height: 1.7em

# v0.6.4: 사이트 공통 CSS link 출력 여부. 기본 true.
# use_common_css: true

# v0.6.4: 메인페이지에 사용할 템플릿 파일. 비우면 home.html.
# template: my_landing.html      # templates/ 에서 검색.
# template: ./local_home.html    # Articles/ 안의 파일에서 검색.

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
finalize_md_html()                   ← 후처리: asset 경로 재작성, PHP 시뮬레이션
   ▼
RenderResult(html)                   ← v0.5.5 부터 html 한 필드. 옛
                                       first_paragraph / first_image 는
                                       본문 ↔ 메타데이터 분리 원칙으로 폐기.
```

### 파서 원본과 라이센스

- 원본: [Parsedown](http://parsedown.org) 1.7.4, (c) Emanuil Rusev, MIT 라이센스.
- 포팅: [scripts/parsedown.py](scripts/parsedown.py) — 메서드명·블록/인라인 dispatch 구조·Block/Element dict 키 이름까지 원본 PHP 와 일대일 매핑되도록 작성. 외부 의존성 없음 (Python stdlib `re`, `typing` 만 사용).

### 출력 동등성 검증 (출시 시점)

v0.4.1 출시 시점에 PHP Parsedown 1.7.4 와 [scripts/parsedown.py](scripts/parsedown.py) 의 출력을 다음 두 corpus 로 바이트 단위 비교했습니다:

- 합성 fixture 46개 (헤더/단락/링크/이미지/표/코드블록/리스트/HTML/Korean/엣지케이스).
- 실제 글 corpus 33편.

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

### 운영 정책 — Parsedown 1.7.4 의 포크

[scripts/parsedown.py](scripts/parsedown.py) 는 **이 사이트가 쓰는 마크다운을 파싱하기 위해 PHP Parsedown 1.7.4 를 포크하여 Python 으로 새로 포팅한 구현** 입니다. 즉 "PHP 원본을 충실히 추종하는 백엔드" 가 아니라, 포크된 시점의 Parsedown 1.7.4 가 출발점이었던 author 의 마크다운 처리기입니다. 앞으로의 모든 수정·기능 추가는 이 포팅 위에서 직접 진행하며 원본 Parsedown 의 신버전 업데이트를 따라가지 않습니다. 메서드명·dispatch 구조·dict 키를 원본 1.7.4 와 동일하게 둔 것은 출시 시점의 패리티 검증 (위 절) 을 가능하게 하기 위함이지, 미래의 동기화를 전제로 하지 않습니다. 따라서 "원본 업데이트가 나오면 무엇을 해야 하나" 라는 질문 자체가 이 시스템에서는 해당되지 않습니다 — 필요한 마크다운 처리는 이 포팅에 직접 추가합니다.

같은 이유로 트리에는 PHP 측 비교 대상 (Parsedown.php) 을 동봉하지 않으며, v0.6.0 의 [tests/test_parsedown.py](tests/test_parsedown.py) 는 Python 포트의 기본 마크다운 요소를 회귀 가드하는 데에 한정되어 있고 PHP 측 출력과의 대조는 포함하지 않습니다. PHP 원본은 포팅 시점의 일회성 패리티 검증 (위 절의 79/79 비교) 에서 역할을 다했고, 이후로는 이 포크가 단일 진실원입니다.

---

## 12b. YAML 파서 — 의도된 부분집합 ([scripts/yaml_parser.py](scripts/yaml_parser.py))

site.yaml / 각종 meta.yaml 을 읽는 파서는 자체 구현입니다. *이 프로젝트에서 실제 사용하는 YAML 문법의 부분집합* 만 지원하며, 그 외는 의도적으로 구현하지 않습니다.

**지원:** 평면 key-value, nested mapping (들여쓰기 기반), block-style list (`- a`), inline list (`[a, b]`), 따옴표 문자열 (`'...'` / `"..."`), 정수·진릿값·null, `#` 주석 (라인 단위 — 즉 라인 첫 비공백이 `#` 일 때만).

**미지원 (의도):** anchor / alias (`&` / `*`), folded scalar (`>`), block scalar (`|`) 의 chomping 변형, flow-style mapping (`{...}`), 인라인 주석 (`key: val # comment` 의 `#` 이 value 의 일부로 빨려 들어감), multi-document (`---` 구분).

**PyYAML 도입 계획 없음.** v0.4.1 단계의 "검토 보류" 가 v0.5.x 들어서 정책으로 굳어졌습니다 — 도입하지 않습니다. 이 시스템의 YAML 사용 면적은 시스템 자체와 함께 진화하므로, 부분집합으로 충분하고 외부 의존성 부담을 만들 가치가 없다는 판단입니다. 새 문법이 필요해지면 이 파서에 직접 추가합니다.

---

## 13. 검색 기능 — search.php

사이트 내 글 검색을 제공합니다. 클라이언트 JS 0줄, 외부 검색엔진 의존도 0. 메타데이터 3-필드 (title / seo.description / tags) 만 색인하며 **글 본문에 대한 검색은 현재 지원하지 않습니다** (v0.6.0 부터; 본문 평문은 검색 결과 미리보기 스니펫 추출용으로 앞 1500 자만 `body_snippet` 으로 보존). 한국어/영어 혼용 입력에서 부분 일치까지 잡아내는 자체 역색인 + 서버측 PHP **BM25 검색** 엔드포인트로 동작합니다.

> **v0.6.0 핵심 변경 (한 줄)**: 본문 색인 폐기, 메타데이터 3-필드 (title / description / tags) 만 BM25 색인. 인덱스 + 토크나이저 + BM25 함수가 `dist/search.php` 한 파일에 PHP 정적 배열 리터럴로 인라인 → OPcache 가 바이트코드와 함께 캐시 (JSON 파싱 / 디스크 IO 0).

### 동작 방식 한눈에

```
[빌드 시점 — Python]
  build.py 가 모든 글의 (title / seo.description / tags) 를 토크나이즈
  → BM25 인덱스 (포맷 v4) 빌드 + PHP 정적 배열 리터럴로 직렬화
  → dist/search.php 한 파일 안에 (토크나이저 + BM25 함수 + 인덱스) 모두 인라인.
  본문 평문은 docs[].body_snippet 으로 앞 1500 자만 보존 (검색 결과 미리보기용).
  noindex 글은 인덱스에서 제외 (sitemap / feed 와 일관).

[방문자 검색]
  사용자가 nav 우측 검색창에 입력 → form GET → /search.php?q=...
  PHP 가 search.php 한 파일을 OPcache 에서 로드 (인덱스도 함께 메모리 상주) →
  쿼리를 같은 토크나이저로 쪼개 세 필드 (title / desc / tags) BM25 점수를
  가중합 → 원본 쿼리가 substring 으로 매치되면 phrase 부스트 (title ×2.0,
  desc ×1.5, tags 정확매치 ×2.5) → docs[].body_snippet 의 매치 밀도 윈도우로
  스니펫 추출 → 결과 렌더.
```

### UI/UX (v0.4.0 정리)

- **노출 위치** — 홈 (`/`) 과 카테고리 인덱스 (`/blog/` 등) 페이지의 nav 우측 상단에만 표시. 개별 글, About, 404 에서는 노출하지 않음 (그곳에서 굳이 검색을 시작할 일이 없으므로).
- **미관 (v0.4.0)** — 배경색·테두리 없이 nav 의 회색 톤(#AFAFAF)에 녹아드는 placeholder "검색" 만 보이고, 클릭(focus) 시 가로로 부드럽게 확장 + 텍스트가 짙어지며 입력 가능 상태가 됨. 사이트의 미니멀 톤을 깨지 않도록 의도된 디자인.
    - v0.3.2 까지 사용하던 italic placeholder 를 v0.4.0 에서 제거. faux italic skew 가 컨텐츠 박스를 넘쳐 발생하던 우측 클리핑 문제도 함께 사라졌고, 그래서 비대칭 padding (좌 0.2em / 우 0.6em) 도 단순한 0.3em 좌우 동일로 정리됨.
- **모든 뷰포트에서 노출** — 모바일 (≤600px) 포함. 좁은 폭에서는 시작/확장 폭만 줄어듦.
- **검색 결과 페이지 (`/search.php?q=...`)** — 기존 글 목록 (`listup_module_div`) 과 동일 마크업으로 결과를 표시. 각 결과 아래에 **매치 밀도가 가장 높은 80자 윈도우** 의 스니펫 (v0.5.0). 매치된 부분은 `<mark>` (배경 #fff3cd) 로 강조.

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
- **PHP 측**: [templates/search_tokenize.php](templates/search_tokenize.php) — v0.6.0 부터 빌드 시 함수 본문이 `dist/search.php` 안에 직접 인라인됩니다 (별도 `dist/search_tokenize.php` 파일 없음, require_once 없음). 템플릿은 진단·테스트용 단일 진실원으로 유지되며, build.py / tests/run_diagnostics.py 가 CLI 로 직접 실행해 Python 측과 패리티를 검증합니다.

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

### 인덱스 포맷 (v4, v0.6.0)

`dist/search.php` 안에 PHP 정적 배열 리터럴로 인라인됨 (별도 `.json` 파일 없음). 개념적 구조:

```
{
  "version": 4,
  "params": {
    "k1_title": 1.2, "b_title": 0.5,    "w_title": 3.0, "phrase_boost_title": 2.0,
    "k1_desc":  1.5, "b_desc":  0.75,   "w_desc":  1.5, "phrase_boost_desc":  1.5,
    "k1_tags":  1.2, "b_tags":  0.3,    "w_tags":  2.0, "phrase_boost_tags":  2.5
  },
  "stats":   {"N": 6, "avgdl_title": 4.17, "avgdl_desc": 9.50, "avgdl_tags": 2.00},
  "docs": [
    {"slug":"hello-world", "title":"Hello, World!", "date":"2026-05-07",
     "category":"Blog", "category_slug":"blog",
     "description":"A short intro to the site.",
     "tags":["intro","sample"],
     "body_snippet":"평문 본문 앞 1500 자...",
     "dl_title":2, "dl_desc":6, "dl_tags":2}
  ],
  "categories": {"blog": "Blog"},
  "df_title":   {"hello": 1, ...},
  "df_desc":    {"intro": 1, ...},
  "df_tags":    {"intro": 1, "sample": 1, ...},
  "tf_title":   {"hello": [[0, 1]], ...},
  "tf_desc":    {"intro": [[0, 1]], ...},
  "tf_tags":    {"intro": [[0, 1]], "sample": [[0, 1]], ...}
}
```

- `params` — BM25 하이퍼파라미터. 인덱스에 박혀 있으므로 같은 빌드의 점수가 결정적.
- `stats.N` — 문서 수. `stats.avgdl_*` — 필드별 평균 토큰 수.
- `docs[doc_id].dl_*` — 그 문서의 필드별 토큰 수 (길이 정규화 분모).
- `docs[doc_id].body_snippet` — 평문 본문 앞 1500 자 (글자 단위). 검색 결과 미리보기 스니펫 추출 전용 — BM25 점수 계산에는 들어가지 않음.
- `df_*[token]` — 그 토큰이 등장한 문서 수 (IDF 계산용).
- `tf_*[token]` — `[[doc_id, term_frequency], ...]` posting list.
- 톱레벨 카테고리에 속하지 않은 글 (예: About) 은 `category_slug=""` — 전체 검색에는 잡히지만 어떤 카테고리 스코프 검색에도 잡히지 않습니다.
- **noindex 글은 인덱스에서 제외** (v0.6.0). sitemap / feed 와 일관된 정책.

> **v0.5.x 의 v3 포맷과 비호환**: 본문 색인 (`df_body` / `tf_body` / `dl_body` / `avgdl_body`) 제거, `df_desc` / `df_tags` / `tf_desc` / `tf_tags` 추가, `body` 필드가 `body_snippet` 으로 이름 변경 + 앞 1500 자로 자름.

### 점수 계산 — BM25 + 필드 가중치 + phrase 부스트 (v0.6.0)

#### 한 필드 BM25 (필드 무관 공식)

```
bm25_f(Q, D) = Σ IDF_f(t) · ( tf_f(t,D) · (k1+1) ) /
                            ( tf_f(t,D) + k1 · (1 - b + b · dl_f / avgdl_f) )

IDF(t)       = ln( (N - df + 0.5) / (df + 0.5) + 1 )    (Robertson-Spärck Jones)
```

- **k1 (TF 포화 강도)** — 제목 1.2 / description 1.5 / tags 1.2. 작을수록 두 번째 매치부터의 한계 이득이 작아짐.
- **b (길이 정규화 강도)** — 제목 0.5 / description 0.75 / tags 0.3. tags 는 author 가 직접 적은 단어 모음이라 길이 정규화 거의 끔.

#### 세 필드 합산

```
score(Q, D) = w_title · bm25_title(Q, D)
            + w_desc  · bm25_desc(Q, D)
            + w_tags  · bm25_tags(Q, D)
            (w_title=3.0, w_desc=1.5, w_tags=2.0)
```

#### Phrase 부스트 (곱셈)

원본 쿼리 문자열 (trim 후 길이 ≥ 2) 이 매치되면:

```
title       : 연속 substring 매치 시   score *= 2.0
description : 연속 substring 매치 시   score *= 1.5
tags        : 한 tag 와 정확히 일치 시 score *= 2.5  (substring 은 부스트 안 함 — 노이즈 방지)
```

곱셈이므로 score=0 (토큰 미매치) 은 그대로 0 — 의미 있는 점수만 부스팅됩니다.

#### v0.5.x → v0.6.0 결함 해소표

| v0.5.x 결함/한계 | v0.6.0 해소 |
|---|---|
| 인덱스 안에 모든 글의 평문 본문 전체 — 매 검색 요청마다 PHP 가 통째 로드 | 본문 색인 폐기. 본문 평문은 docs[].body_snippet 으로 앞 1500 자만 보존 (스니펫 추출 전용). |
| search-index.json 별도 파일 — 매 요청마다 JSON 파싱 + 디스크 IO | PHP 정적 배열 리터럴로 search.php 안에 인라인. OPcache hit 시 메모리 상주 + JSON 파싱 비용 0. |
| 토크나이저·BM25 함수가 별도 PHP 파일 (require_once 3 회) | 한 파일에 인라인. OPcache 캐시 엔트리 1 개. |
| noindex 글이 본문 매치로 검색에 노출 | 인덱스에서 제외 (sitemap / feed 와 일관). |
| 본문에만 나오는 단어가 검색되는 동작 | 본문 색인 폐기로 사라짐 — author 가 title/description/tags 에 핵심어 명시해야 발견 가능 (트레이드오프). |

#### Python ↔ PHP 점수 패리티

`scripts/search.py` 의 `bm25_score()` 는 Python 참조 구현입니다. 런타임 PHP (`dist/search.php` 안에 인라인된 `bm25_search()`) 와 동일 공식. `tests/test_bm25.py` (31 개) 가 Python 측 회귀를, `tests/run_diagnostics.py` 가 양측 패리티를 동시에 검증합니다 (개발 환경에서 PHP 8.3 로 8 개 쿼리·12 개 매치에 대해 소수점 6 자리 일치 확인 — 항목 4 참조).

### 인덱스 크기 (실측)

v0.5.5 → v0.6.0 의 변화:

| 글 수 | v0.5.5 합계 (search.php + json + tokenize + bm25) | v0.6.0 합계 (search.php 단일) |
|---|---|---|
| 6 (현재 트리) | ~33 KB | ~28 KB (-15%) |

요청 수준에서는 매번 4 개 파일 → 1 개 파일 + JSON 파싱 → PHP 바이트코드 캐시. 글 수 증가 시도 본문 색인이 빠졌기 때문에 글당 크기 증가가 본문 색인 시절보다 훨씬 완만합니다.

### 보안·악용 방지

- 쿼리 길이 100 글자 제한 (`mb_substr($q_raw, 0, 100, 'UTF-8')`).
- 모든 출력은 `htmlspecialchars($x, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8')` 로 escape.
- 강조 (`<mark>`) 는 escape 후에 적용해 XSS 방지.
- 검색 결과 페이지는 `<meta name='robots' content='noindex,follow'>` 를 출력합니다 (v0.4.2 부터). `?q=…` 노이즈 URL 이 외부 검색엔진에 색인되는 것을 차단하면서, follow 는 유지해 결과 링크는 크롤러가 따라갈 수 있게 합니다 — v0.4.0 의 "전역 noindex 제거" 정책에서 의도된 예외.

### 빌드 산출물

```
dist/
├── search.php   ← 검색 엔드포인트 + 토크나이저 + BM25 함수 + 정적 인덱스 (v0.6.0: 모두 인라인)
└── ...
```

v0.5.x 까지 있던 `search-index.json` / `search_tokenize.php` / `search_bm25.php` 는 더 이상 생성되지 않습니다. v0.5.x dist 위에 v0.6.0 빌드를 돌리면 빌더가 옛 세 파일을 명시적으로 정리합니다.

`reserved_slugs` 에 `search` 가 포함되어 있어 글의 slug 가 `search` 일 수 없음 ([site.yaml](site.yaml) 참조).

### 서버 요구사항

- PHP 7.4 이상 (`mb_*` 함수, arrow function 사용).
- `mbstring` 확장 (대부분 PHP 기본 포함).
- 추가 PHP 확장이나 라이브러리 불필요.

### 고급 — 검색 비활성화

`templates/search.php` 파일을 삭제하면 build.py 가 경고만 출력하고 인덱스 파일은 만들지만 search.php 는 만들지 않습니다. 또한 [templates/home.html](templates/home.html), [templates/category.html](templates/category.html) 의 `<form class='nav-search'>...</form>` 블록을 제거하면 UI 도 사라집니다.

---

## 13b. RSS / Atom 피드 (v0.5.3)

빌드 시 `dist/feed.atom` (Atom 1.0) 과 `dist/feed.rss` (RSS 2.0) 두 파일이 같은 entry 목록으로 생성됩니다. 추상 모델은 [scripts/feed.py](scripts/feed.py) 의 `FeedDocument` / `FeedEntry` dataclass — Atom 1.0 이 RSS 2.0 의 사실상 슈퍼셋이라 한 모델에서 두 직렬화 (`render_atom` / `render_rss`) 를 동시에 만듭니다.

### 포함 정책

- non-noindex 글만. 글 meta.yaml 의 `noindex: true` 는 sitemap 과 동일하게 제외.
- `Articles/meta.yaml` 의 `excludes_categories` (= 홈 Recent posts 에서 빠지는 카테고리) 도 피드에서 제외. About 처럼 정적 페이지가 RSS 구독자에게 노출되는 사고를 막습니다.
- 최신 N 개 (기본 20, `scripts/feed.py` 의 `DEFAULT_MAX_ENTRIES`).
- 정렬은 `updated` (없으면 `date`) 내림차순, 동순위는 slug 알파벳.

### entry 내용

| Atom | RSS | 출처 |
|---|---|---|
| `<title>` | `<title>` | 글 meta.yaml 의 `title` |
| `<link rel="alternate" href=>` | `<link>` | `https://siheonlee.com/{slug}/` |
| `<id>` | `<guid isPermaLink="true">` | 글의 절대 URL (= 영구 식별자) |
| `<published>` | `<pubDate>` | meta.yaml 의 `date` |
| `<updated>` | (없음) | meta.yaml 의 `updated` (없으면 `date`) |
| `<summary>` | `<description>` | seo.description (v0.5.5 부터 본문 첫 단락 폴백 폐기 — § 16 의 설계 원칙 10). site.yaml 의 `description_truncate` 적용. 부재/빈 문자열 시 entry 의 summary/description 자체 누락 + BuildReport issue. |
| `<author>` | (생략) | seo.author > site.default_author. RSS 의 `<author>` 는 email 형식 강제라 dc:creator 없이는 표현 한계 — 생략. |
| `<category term=>` | `<category>` | 톱레벨 카테고리 폴더명 + 글의 `tags` (v0.5.3). 중복 제거. |

### 자동 발견 (`<link rel="alternate">`)

홈/카테고리/글 페이지 `<head>` 에 두 피드의 `<link rel='alternate' type='application/atom+xml'>` / `<link rel='alternate' type='application/rss+xml'>` 가 삽입됩니다. 모던 브라우저와 RSS 리더 (Feedly, Inoreader 등) 가 페이지 URL 만으로 자동 발견합니다.

### 날짜 정책

meta.yaml 의 `date` / `updated` 는 YYYY-MM-DD 만 — 시각 정보가 없습니다. 직렬화 시 모두 `00:00:00 UTC` 로 통일합니다 (Atom 은 ISO 8601 `T00:00:00Z`, RSS 는 RFC 822 `Wed, 14 May 2026 00:00:00 +0000`). 같은 입력 → 같은 출력 = 결정성 보장. 피드 자체의 `updated` / `lastBuildDate` 도 빌드 시각이 아니라 entry 중 가장 최신 lastmod 를 사용하므로, 콘텐츠 변경 없이는 매 빌드마다 같은 바이트가 출력됩니다.

### 비활성화

[scripts/builder.py](scripts/builder.py) 의 `build()` 메서드에서 `self._build_feeds()` 한 줄을 주석 처리하면 됩니다. 두 파일이 이미 dist 에 있으면 다음 `--clean` 빌드에서 사라집니다 (또는 수동 삭제). 별도 site.yaml 토글은 없음 — 추가 의제.

---

## 14. 배포 — 서버 업로드와 Apache 설정

빌드 후 생성된 폴더를 서버에 올리고, Apache VirtualHost 를 한 번 등록하면 끝입니다. 이후 글을 추가/삭제해도 서버 설정은 건드릴 필요가 없습니다.

이 시스템은 `.htaccess` 파일을 사용하지 않습니다. 모든 서버 규칙은 Apache 메인 설정(VirtualHost 또는 httpd.conf) 에 등록합니다 — 이것이 설계 의도이므로 공유 호스팅에서 메인 설정 접근이 안 되면 호스팅 사업자에게 등록을 요청해야 합니다.

### 14-1. siheonlee.com — 서버 업로드

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

### 14-2. 빌드 머신 vs 배포 서버의 PHP

> **(v0.4.1)** 빌드 머신에는 PHP 가 필요하지 않습니다. 마크다운 파서가 순수 Python 으로 포팅되었기 때문입니다. PHP CLI 가 있으면 빌드 시 토크나이저 패리티 검증이 자동 실행되고, 없으면 워닝과 함께 검증을 건너뜁니다.
>
> **배포 서버** 는 **PHP 7.4+ 와 mbstring 확장** 이 필요합니다 — 검색 엔드포인트 (`search.php`) 가 런타임 PHP 를 사용하기 때문입니다. 또한 글에 처리되지 않은 `<?php` 가 남아 `.php` 로 출력되는 경우도 배포 서버 PHP 가 필요합니다. PHP 와 Apache 메인 설정 접근은 이 시스템의 **기본 동작 환경** 입니다 (한계가 아니라 전제).

### 14-3. 배포 검증 체크리스트

배포 후 다음을 확인하세요:

```bash
curl -I https://siheonlee.com/                    # 200 OK
curl -I https://siheonlee.com/hello-world         # 301 → /hello-world/
curl -I https://siheonlee.com/hello-world/        # 200 OK
curl -I https://siheonlee.com/없는페이지/           # 404 (본문은 /404.html)
curl -I https://siheonlee.com/robots.txt          # 200 OK, text/plain
curl -I https://siheonlee.com/sitemap.xml         # 200 OK, application/xml (v0.4.4)
```

---

## 15. 트러블슈팅

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

배포 서버에는 여전히 PHP 가 필요합니다 (search.php 가 런타임 PHP). 자세한 내용은 § 14-2 참조.

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
4. `dist/{slug}/imgs/` 안에 파일이 복사되어 있는지 확인하세요. (v0.5.1 까지는 `dist/src/{slug}/imgs/`. v0.5.2 에서 자산 경로 일원화.)

### Q: 기존 PHP 글인데 `.php` 확장자로 출력되지 않고 `.html` 로 나옵니다.

`content.html` 안에 처리되지 않은 `<?php` 가 남아 있어야 `.php` 로 출력됩니다. `imgBox`, `imgSlideBox` 는 빌드가 자동으로 HTML 로 변환하기 때문에 그 결과에는 `<?php` 가 없어서 `.html` 로 출력됩니다. 실제로 서버에서 실행해야 하는 PHP 코드가 있어야 `.php` 로 출력됩니다.

### Q: `dist/` 를 지웠다 다시 빌드하고 싶습니다.

```bash
python build.py --clean
```

---

## 16. 설계 원칙과 한계

### 설계 원칙

1. **URL 영구성** — 글의 URL 은 카테고리 이동, 폴더명 변경과 무관하게 slug 가 바뀌지 않는 한 영구 유지. ("Cool URIs don't change")

2. **표시명과 URL slug 분리** — 화면에 보이는 이름은 한국어 폴더명, URL 은 영문 ASCII slug 로 독립 관리.

3. **운영 의존성 명시** — 빌드는 Python 3 + Pillow (v0.5.1), 런타임은 PHP (검색). 클라이언트 JS 의존성·composer 의존성 없음. v0.4.0 부터 "외부 의존성 0" 이 아니라 "런타임 명시" 로 솔직히 표기하기 시작했고, v0.4.1 에서 빌드 PHP 의존이 제거되어 명시 대상이 줄었음. v0.5.1 에서 Pillow 가 새로 도입되었지만 "SEO 직접 영향" 예외로 도입한 단일 의존성이며 `images.enabled=false` 로 끄면 v0.5.0 처럼 stdlib 만으로 빌드 가능 — "필요한 만큼만, 끄는 옵션 함께 제공" 정책으로 유지.

4. **서버 설정과 콘텐츠 분리** — `.htaccess` 가 없어 서버 설정과 콘텐츠가 완전히 분리. 글을 아무리 많이 추가해도 서버 설정을 건드릴 필요가 없음.

5. **빌드의 안전성** — 빌드 스크립트는 `Articles/` 를 **읽기만** 함. 소스 파일을 자동으로 수정하지 않음.

6. **파서 단일화 (v0.4.1)** — v0.3 ~ v0.4.0 의 추상화 (MarkdownRenderer + builtin/parsedown 분기) 가 폐지되고, 마크다운 파서는 [scripts/parsedown.py](scripts/parsedown.py) (Parsedown 1.7.4 Python 포팅) 하나로 통일. 다중 파서 인터페이스는 실제 필요가 없었다는 v0.4.0 회고의 결과.

7. **글 단위 표현 제어** — 사이트 전역 CSS 와는 별도로, 글마다 독립적인 표현 결정을 meta.yaml 에서 선언적으로 관리.

8. **글 단위 색인 정책 (v0.4.0)** — 기본은 모든 페이지 색인 허용. 비공개로 두고 싶은 글만 그 글의 meta.yaml 에 `noindex: true` 한 줄.

9. **단일 진실원의 토크나이저 (v0.4.0)** — Python/PHP 양쪽 토크나이저의 동등성을 빌드마다 fixture 패리티 테스트로 자동 검증.

10. **본문 ↔ 메타데이터 분리 원칙 (v0.5.5)** — SEO description, OpenGraph 카피, 피드 summary, og:image 같이 외부에 노출되는 메타데이터는 본문이 아니라 author 가 `meta.yaml` 의 `seo:` 블록에 직접 작성한 값에서만 가져온다. 본문은 독자용 narrative, 메타데이터는 SERP / 소셜 카드 / aggregator 용 카피이며, 둘은 다른 글이어야 한다. SSG 는 어느 쪽으로도 추측하지 않는다.

    **필드의 세 상태:**
    - **키 부재 또는 값 부재** (`description:` 또는 키 없음) — opt-out. 해당 메타 태그를 출력하지 않는다.
    - **빈 문자열** (`description: ""`) — author 의 실수로 간주. 산출물에는 태그를 출력하지 않고, 빌드 종료 후 미완성 글 리포트에 기록한다.
    - **값 있음** — 그대로 출력. `og_description` / `twitter_description` 같은 파생 필드가 부재하면 `description` 을 폴백으로 쓴다 (author 가 직접 쓴 값이므로 본문 추출이 아니다 — author-authored fallback).

    **필수 필드: `seo.description`.** 빠지거나 빈 문자열이면 빌드 종료 후 미완성 글 리포트에 기록되지만 **빌드를 중단시키지는 않는다**. 빌드는 어떤 콘텐츠 결함에도 끝까지 완성되며, 종료 시 터미널에 "보완해야 할 글 목록" 을 몰아서 표시한다. 기존 빌드 과정의 모든 경고/실패 신호는 이 일원화 리포트 ([scripts/report.py](scripts/report.py)) 로 통합되었다 — 빌드 도중에 abort 하는 경로는 시스템 결함 (템플릿 누락, `Articles/` 없음, Pillow 미설치 등) 이외에는 두지 않는다.

    **`og_image` 의 본문 추출 폴백을 두지 않는 이유:** SNS / 메신저 미리보기는 `og:image` 가 없을 때 본문 첫 이미지나 favicon 을 임의로 긁어가 카드를 조합한다. 이는 author 의 의도와 무관한 부작용이며, 같은 행동을 SSG 가 빌드 시점에 자동화하는 것은 동일하게 무례한 일이다. `meta.yaml` 에 `og_image` 가 없으면 `site.default_og_image` 를 무조건 사용한다 — author 가 명시적으로 선택한 사이트 기본값이라는 점에서 본문 추출과 본질이 다르다.

11. **`template:` 의 페이지 종류 가로지르기 — 허용하되 알린다 (v0.6.4)** — 글/카테고리/홈은 각각 자기 기본 템플릿 (`article.html` / `category.html` / `home.html`) 을 갖지만, `meta.yaml` 의 `template:` 키로 author 는 다른 페이지 종류의 템플릿이나 직접 작성한 임의의 템플릿을 지정할 수 있다. 빌더는 *page_kind ↔ template 의 정합성을 자동 거부하지 않는다.* 빌더가 채울 줄 모르는 placeholder (예: 글 페이지에 `{{SUBCATEGORY_SECTIONS}}` 가 있는 템플릿) 는 [scripts/builder.py](scripts/builder.py) 의 `_render_template` 후처리에서 빈 문자열로 strip 되고, 미치환 이름마다 BuildReport warning 한 줄이 남는다 (시스템 페이지 — 404/search — 는 빌더가 직접 컨트롤하므로 strip 만 적용, warning 없음).

    **issue (보완해야 할 결함) 가 아니라 warning (의도 확인) 인 이유:** 가로지름은 author 의 의도일 수 있다 — 예를 들어 어떤 카테고리에 글 템플릿을 입혀 인덱스 섹션을 의도적으로 비운 랜딩 페이지를 만들거나, 글 하나에 홈 템플릿을 빌려 와 최근 글 목록이 빠진 정적 페이지를 만드는 등. 빌더가 정합성을 자동 거부하면 이 의도된 가로지름이 막힌다. 그래서 SSG 는 **알리기만 하고 판정은 author 의 몫으로 둔다** — 본문 ↔ 메타데이터 분리 (#10) 와 같은 톤의 "추측 안 함" 원칙. silent strip 도 (의도와 무관하게 산출물이 조용히 깨지므로), 자동 거부도 (의도된 사용을 막으므로) 아닌, *알림 + author 확인* 이 정답.

### 현재 버전(v0.7.2) 의 한계

> 아래 표는 v0.7.2 시점에 여전히 유효한 한계만 모았습니다. v0.6.5 에서 해소된 항목 — *사용자 본문의 `{{XXX}}` placeholder silent strip* / *_report 누적* / *og_type 디폴트 강제* — 은 모두 안정화 패치로 사라졌습니다. v0.6.4 의 *카테고리/홈 외부 CSS 미지원* 비대칭도 해소된 상태 (글/카테고리/홈 모두 같은 메커니즘). v0.7.0 에서 새로 해소된 항목 — *빌드 증분 캐싱 없음* — 도 한계 표에서 빠집니다. 글 단위 캐시 (`.build_cache/`) 가 도입되어 변경되지 않은 글은 캐시 hit 로 재렌더 없이 dist 에 복원됩니다 (검색 인덱스 / sitemap / feed / 홈 / 카테고리는 모든 글이 입력이라 매 빌드 재구축 — 의도된 범위). v0.7.1 까지 한계로 잡혀 있던 *빌드 진행 표시 없음 (시작/완료 두 줄뿐) / 보완 안내가 터미널 휘발성* 은 **v0.7.2 에서 해소** — 16 단계 헤더 + 무거운 루프 라이브 카운터 + `build-report.md` 영속 리포트. 진행 출력·리포트는 모두 dist/ 밖이라 산출물·결정성에는 변동이 없습니다.

| 한계 | 내용 |
|---|---|
| 이미지 최적화는 정적 단일 프레임만 (v0.5.1) | animated GIF 는 첫 프레임만 WebP 로 인코딩되어 애니메이션이 사라집니다. 애니메이션을 보존하려면 그 글의 첨부를 webp 로 직접 만들거나, `<img>` 의 src 를 외부 URL 로 두면 후처리에서 src 가 변경되지 않습니다. 한 글 / 한 이미지에 대해서만 최적화를 끄는 옵션은 아직 없음 (사이트 전역 토글만). |
| 증분 캐싱은 글 페이지만 (v0.7.0) | `_render_articles` 단계의 글 페이지 HTML/PHP 만 캐시. 검색 인덱스 / sitemap / RSS·Atom 피드 / 홈 / 카테고리 인덱스 / assets 는 모든 글이 입력 (또는 전역 데이터) 이라 invalidate 빈도가 높고 계산 비용이 낮아 매 빌드 재구축. 글 수가 수백 ~ 수천 건 규모에서 의미 있는 차이가 생기면 차기 의제. |

---

## 17. 업데이트 로그

### v0.7.2 (2026-05-17) — 빌드 진행 표시 + 빌드 리포트 문서화

v0.7.1 까지 `build()` 는 `빌드 시작...` 과 완료 요약 두 줄만 출력했다. 사진이 많은 글을 실제로 빌드하면 이미지 WebP 변환 (`_sync_assets`) 에서 수십 초~분 단위로 아무 출력 없이 멈춘 듯 보였고, 보완이 필요한 항목 (`BuildReport`) 도 터미널에만 휘발성으로 떠 빌드 후 다시 확인할 수 없었다. v0.7.2 는 두 가지를 보완한다 — **진행 표시** 와 **빌드 리포트 문서화**. 빌더 *산출 로직* 은 무변경 — `dist/` 의 모든 파일이 v0.7.1 과 byte 동일 (`feed.atom` / `feed.rss` 의 generator 문자열만 `v0.7.1` → `v0.7.2` 자동 갱신, `__version__` 단일 source 효과).

- **16 단계 진행 헤더.** [scripts/builder.py](scripts/builder.py) 의 `build()` 가 각 파이프라인 단계 직전에 `[ n/16] <설명>` 한 줄을 출력 (`Builder._step`). 16 단계는 docstring 의 파이프라인 표와 동일 순서 (`# [n]` 주석은 v0.4.x~v0.6.4 의 역사적 재배치 id 라 그대로 두고, 사용자 대상 진행 번호만 1..16 단조 증가).
- **무거운 루프의 라이브 카운터.** 이미지 변환 (`_sync_assets`) / 글 렌더 (`_render_articles`) 가 글·이미지마다 같은 줄을 `\r` 로 in-place 갱신 (`Builder._live`). `sys.stdout.isatty()` 가 False 인 환경 (`tests/run_diagnostics.py` / 단위 테스트는 stdout 을 `StringIO` 로 redirect) 에서는 no-op 이라 캡처 로그가 깨끗하고 결정성·테스트에 영향이 없다. 단계 요약 한 줄은 TTY 여부와 무관하게 항상 남는다.
- **`build-report.md` 자동 생성.** 빌드 완료 시 [build.py](build.py) 가 있는 폴더 (`Builder.base`) 에 마크다운 리포트를 쓴다 (`Builder._write_build_report`). 구성 — 메타 (버전 / 시각 / 소요 / 글·카테고리 수 / 캐시) + `## 빌드 진행` 트랜스크립트 (코드 블록) + `## 보완이 필요한 항목` / `## 살펴볼 사항` 절. 새 [scripts/report.py](scripts/report.py) 의 `BuildReport.render_markdown()` 가 기존 `render()` 와 1:1 구조로 마크다운 직렬화 (issue 절 → warning 절 → 요약). 파일 쓰기 실패는 콘텐츠 결함이 아니므로 `abort` 하지 않고 stderr 경고 후 빌드 정상 종료. 매 빌드 덮어쓰기 (누적 안 함), `dist/` 밖이라 배포·결정성과 무관 — `.gitignore` 권장.
- **버전 표기 일괄 갱신.** [scripts/\_\_init\_\_.py](scripts/__init__.py) 의 `__version__` `0.7.1` → `0.7.2`. README 헤더 / 빠른 시작 폴더 예시 / 폴더 트리 / §11-2 site.yaml 예시 헤더 / 현재 한계 표 / 푸터 캡션 + [build.py](build.py)·[scripts/builder.py](scripts/builder.py) docstring 헤더·usage·의존성 표기도 v0.7.2 로 갱신. 단 *changelog 본문* 안의 옛 버전 표기는 *기능 도입 시점* 을 가리키는 역사 기록이라 그대로 보존.

**검증:** 단위 테스트 258 / 0 (v0.7.1 과 동일 — 진행 출력은 stdout, 리포트는 dist/ 밖이라 기존 단언 무영향). 빌드 진단 (`tests/run_diagnostics.py`) 5/5 PASS. `python build.py --clean` 1 회 + 2 회차 빌드 sha256 동일 (결정성). v0.7.1/dist 대비 byte 차이는 feed.atom / feed.rss 2 파일 한정 (generator 문자열만 갱신).

### v0.7.1 (2026-05-16) — 안정화 패치 (정합성 회복, 코드 동작 변경 0)

v0.7.0 의 lama.pe.kr 마이그레이션 인프라 일괄 제거 직후 면밀 재감사에서 드러난 문서·주석·README 정합성 갭 정리. 빌더 로직 무변경 — dist 의 모든 파일이 v0.7.0 과 byte 단위 동등 (`feed.atom` / `feed.rss` 의 generator 문자열만 `v0.7.0` → `v0.7.1` 자동 갱신, `__version__` 단일 source 효과).

- **빌더 파이프라인 헤더 정정.** [scripts/builder.py](scripts/builder.py) 의 docstring 이 "15단계 파이프라인" 으로 표기하면서 v0.6.4 에서 신설된 `_sync_page_css` ([6b]) 단계를 목록에서 빠뜨리고 있던 부분 갱신. 실 파이프라인 (`build()` 의 16 개 self._… 호출) 과 docstring 의 단계 표가 일치.
- **README §2 빌드 단계 표 재작성.** 표가 v0.4.x 시절의 (a) `_render_articles` 가 `_sync_assets` 보다 앞서던 옛 순서를 그대로 둔 부분 (v0.5.1 에서 image_variants 채우기 위해 역전됨), (b) v0.5.3 의 `_build_feeds` ([12b]) 누락, (c) v0.6.4 의 `_sync_page_css` ([6b]) 누락 세 부분을 한 번에 정정. 표가 실 파이프라인을 거꾸로 안내하던 사용자 혼선 해소.
- **본문 폴백 잔존 안내 정리.** §5 (`layout: gallery` 의 썸네일 결정 규칙) 가 v0.5.5 폐기된 "본문 첫 이미지" 폴백을 여전히 안내하던 부분 + §13b (RSS / Atom entry table 의 `<summary>` 폴백) 가 마찬가지로 폐기된 "본문 첫 단락" 폴백을 안내하던 부분을 일괄 정정. v0.5.5 의 본문 ↔ 메타데이터 분리 원칙 (§ 16 의 설계 원칙 10) 과 일관.
- **stale § cross-ref 정정.** v0.7.0 에서 마이그레이션 절 (구 §14) 을 제거하면서 후속 § 번호가 시프트됐는데, 코드 docstring 안의 README 참조 두어 곳이 따라오지 못한 부분 정정:
    - [build.py](build.py) 의 `§ 18 (업데이트 로그)` → `§ 17`.
    - [scripts/builder.py](scripts/builder.py) `_gallery_tile_html` 의 `§ 17 참조` → `§ 16 의 설계 원칙 10`.
    - [scripts/builder.py](scripts/builder.py) v0.5.5 변경 절 + [scripts/models.py](scripts/models.py) RenderResult 절의 옛 `§ 5-1 참조` (한 시점에 "본문 ↔ 메타데이터 분리 원칙" 절이 있던 §) → `§ 16 의 설계 원칙 10`.
- **버전 표기 일괄 갱신.** [scripts/\_\_init\_\_.py](scripts/__init__.py) 의 `__version__` `0.7.0` → `0.7.1`. README 헤더 / 빠른 시작 폴더 예시 / 폴더 트리 (`siheonlee.com_v0.7.0/` → `siheonlee.com_v0.7.1/`) / §11-2 site.yaml 예시 헤더 / 현재 한계 표 / 푸터 캡션도 모두 v0.7.1 로 갱신. 단 *changelog 본문* 안의 v0.7.0 표기는 *기능 도입 시점* 을 가리키는 역사 기록이라 그대로 보존.

**검증:** 단위 테스트 258 / 0 (v0.7.0 과 동일). 빌드 진단 (`tests/run_diagnostics.py`) 5/5 PASS. `python build.py --clean` 1 회 + 2 회차 빌드 sha256 동일 (결정성). v0.7.0/dist 대비 byte 차이는 feed.atom / feed.rss 2 파일 한정 (generator 문자열만 갱신).

### v0.7.0 (2026-05-16) — 빌드 증분 캐싱 (글 단위, fine-grained)

변경되지 않은 글은 캐시된 HTML/PHP 를 그대로 dist 에 복원, 변경된 글만 재렌더. `_render_articles` 단계만 캐시 — 검색 인덱스 / sitemap / feed / 홈 / 카테고리 / assets 는 매 빌드 재구축 (모든 글이 입력이라 효과 적음). `scripts/cache.py` 신설 (`BuildCache` + `compute_global_hash` + `compute_article_hash` + atomic manifest write). CLI 에 `--no-cache` / `--clean-cache` 추가 + `--clean` 의 wipe 대상에 `.build_cache/` 포함. `global_hash` = site.yaml + scripts/ + templates/ + 공통 CSS + 카테고리 meta.yaml + `__version__`; 글 고유 = content + 그 글 폴더 자산/CSS. 캐시는 *재렌더 여부* 만 결정하므로 sha256 결정성 유지.

**검증:** 빌드 6 글 / 2 카테고리. 두 번째 빌드 6 히트 / 0 미스, 한 글 수정 후 빌드 5 히트 / 1 미스. 단위 테스트 231 → 258 (`tests/test_cache.py` 신설 27 케이스). 진단 5/5 PASS. v0.6.5/dist 대비 byte 차이 2 파일 (feed.atom/rss generator 자동 갱신).

### v0.6.5 (2026-05-15) — 안정화 패치 (v0.6.0 ~ v0.6.4 누적 회귀 4 건)

(1) `Builder.build()` 진입 시 `reset_report()` 자동 호출 — 한 프로세스 다중 빌드 시 issue/warning 누적 해소. (2) `_render_template` 를 3-pass 로 (frame substitute → leftover strip/warn → content substitute) 재구성 — 사용자 본문 안의 `{{COPYRIGHT_YEAR}}` 같은 placeholder 가 v0.6.4 의 신설 leftover strip 에 silent 삭제되던 회귀 해소. (3) 두 frontmatter 파서의 `og_type` 강제 디폴트 (`or 'article'` / `or 'website'`) 제거 — v0.6.2 의 `page_kind` 분기가 dead code 였던 부분 복원 (산출물 동일).

**검증:** 단위 테스트 227 → 231. 진단 5/5 PASS. v0.6.4/dist 대비 byte 차이 2 파일 (feed.atom/rss generator).

### v0.6.4 (2026-05-15) — 홈/카테고리 CSS 일원화 + `template:` 키

v0.6.3 의 글 단위 외부 CSS / `use_common_css` 토글을 카테고리·홈에도 동일 적용 (영구 미지원 정책 폐기 — 글에만 풀어준 비일관성 해소). `template:` 키로 페이지가 자기 템플릿 직접 명시 (`name.html` → `templates/`, `./name.html` → meta.yaml 의 부모 폴더). placeholder 통일 — 세 템플릿 모두 `{{COMMON_CSS}}` / `{{PAGE_STYLESHEETS}}` / `{{PAGE_STYLES}}`. 새 빌드 단계 `_sync_page_css` 가 카테고리/홈의 외부 CSS 파일을 dist 에 복사. `_render_template` 가 미치환 placeholder 를 strip + warning (페이지 종류 가로지르기 가드).

**검증:** 단위 테스트 210 → 227. v0.6.3/dist 대비 3 파일 차이 (feed 2 + 홈 index.html 의 신설 `{{PAGE_STYLES}}` 빈 치환).

### v0.6.3 (2026-05-15) — 글 단위 외부 CSS 파일 + use_common_css 토글

`meta.yaml` 의 `styles:` 가 두 채널을 동시 수용 — *정수 키* (1, 2, 3, ...) 가 외부 CSS 파일 (글 폴더 안), *문자열 키* (태그/선택자) 가 기존 인라인 룰. 빌더가 head 의 `<link href='/{slug}/<rel>'>` 자동 출력. `use_common_css: false` 로 사이트 공통 CSS 끊기 가능. 명시 키 정책 (자동 발견 없음), 파일 누락은 BuildReport issue + link 미출력. 글 페이지만 — 카테고리/홈은 v0.6.4 에서 풀림.

**검증:** 단위 테스트 188 → 210. v0.6.2/dist 와 *바이트 동일* (데모 1 글의 link 추가 제외).

### v0.6.2 (2026-05-15) — 홈/카테고리 페이지 SEO 메타 태그 출력

v0.5.4 의 `<title>` 폴백 체인 일반화에 이어, description / og_* / twitter_* / canonical 도 홈·톱레벨/서브카테고리에 글과 동일한 폴백 규칙으로 출력. `build_meta_tags()` 시그니처를 글/홈/카테고리 공용 keyword-only 로 일반화 (`og:type` 디폴트만 페이지 종류별 차이 — 글=article, 홈/카테고리=website). `SeoMeta.og_type` 디폴트 `'article'` → `None` (page_kind 분기). `_check_page_description` 헬퍼로 홈/카테고리 description 누락도 BuildReport issue.

**검증:** 단위 테스트 179 → 188. v0.6.1/dist 대비 5 파일 차이 (홈 + 두 카테고리 = 새 메타 태그, feed 2).

### v0.6.1 (2026-05-15) — 문서·주석·산출물 가독성 안정화 (코드 동작 변경 0)

v0.5.0 → v0.6.0 누적 변경 이후 면밀 재감사에서 드러난 문서·주석·dist 가독성 drift 정리. 빌더 로직 무변경 — dist 의 모든 파일이 v0.6.0 과 바이트 동등 (search.php 헤더 주석의 placeholder 누수 정정만 텍스트 차이).

### v0.6.0 (2026-05-15) — 검색 메타데이터 3-필드 색인 + 정적 PHP 인라인 인덱스

색인 대상이 본문 → `(title, description, tags)` 3-필드 (인덱스 v4). 본문은 docs[].body_snippet 으로 앞 1500자만 보존 (BM25 점수 미포함, 스니펫 추출 전용). `dist/search-index.json` / `search_tokenize.php` / `search_bm25.php` 폐기 — search.php 안에 토크나이저 + BM25 함수 + PHP 정적 배열 인덱스를 인라인 (OPcache 가 바이트코드 캐시, 매 요청 JSON 파싱 0). BM25 가중치 — title `w=3.0 / phrase=2.0` / description `w=1.5 / phrase=1.5` / tags `w=2.0 / phrase=2.5` (정확매치만). 단위 테스트 25 → 179 (모든 빌드 모듈 커버). 진단 스크립트 `tests/run_diagnostics.py` 신설 (단위 테스트 + sha256 결정성 + `php -l` + Py↔PHP BM25 패리티 + 인덱스 v4 형식 5 항목).

### v0.5.5 (2026-05-15) — 본문 ↔ 메타데이터 분리 원칙 + 빌드 리포트 일원화

description / og_description / twitter_description / og_image 의 본문 폴백 제거 — 모두 `meta.yaml` 의 `seo:` 블록 값만 사용. `seo.description` 누락/빈 문자열은 미완성 글 리포트에 기록 (메타 태그는 누락 출력, 빌드는 통과). `og_image` 는 `meta.seo.og_image` > `site.default_og_image` > 누락 순. `scripts/report.py` (`BuildReport`) 신설 — 콘텐츠 측 결함은 모두 fail-soft issue 로, 시스템 결함만 `abort()`. `_parse_frontmatter` / `_validate` 가 글 단위로 폴백/제외 + 리포트.

설계 원칙으로 명문화 — § 16 의 설계 원칙 10 ("본문 ↔ 메타데이터 분리 원칙") 참조.

### v0.5.4 (2026-05-14) — `<title>` 폴백 체인 일반화 + 단어 경계 truncate + `nav_priority`

글에만 적용되던 `{prefix}{title}{suffix}` 체인이 홈·카테고리·404·search 에도 동일 적용. `CategoryMeta` 에 `title` + `seo` 추가, `SiteConfig` 에 `error_404_title` + `search_title` 추가. `truncate_description` 이 ASCII 영문 단어 한가운데에서는 자르지 않고 마지막 공백까지 backup (CJK 는 글자 단위 그대로). 톱레벨 nav 정렬 축으로 `nav_priority: int = 0` 신설 — About 최상단 하드코딩 제거, 기본 알파벳 순. `priority` (카테고리 페이지 내 section 정렬) 와 별개 축.

---

### v0.5.3 (2026-05-14) — `tags` + `layout: gallery` + RSS/Atom 피드

글 meta.yaml 의 `tags:` 리스트 (inline / block 둘 다 허용, 중복 제거). 카테고리/홈 `layout: gallery` — CSS Grid (`auto-fill, minmax(220px, 1fr)`) + 4:3 강제 크롭 + subtle hover. 썸네일은 `seo.og_image` > 본문 첫 이미지 > 그라데이션 플레이스홀더 (v0.5.1 의 webp srcset 자동 부착). `dist/feed.atom` (Atom 1.0) + `dist/feed.rss` (RSS 2.0) 자동 생성 — non-noindex + 홈 excludes 제외 + 최신 20 글, 페이지 `<head>` 에 `<link rel='alternate'>` 자동 삽입. 피드 자체의 `updated` 도 entry 최신 lastmod 라 빌드 시각이 산출물에 새지 않음 (결정성 유지). README 한계 표 정리 (한계 아닌 8개 항목 제거).

---

### v0.5.2 (2026-05-14) — 자산 경로 일원화 (글 자산은 글 폴더 안으로)

글 자산이 `dist/src/{slug}/...` → `dist/{slug}/...` (글 index.html 과 같은 폴더). URL 스킴 `/src/{slug}/foo.jpg` → `/{slug}/foo.jpg` (글 본문의 상대 경로는 자동 재작성). `reserved_slugs` 의 `src` 제거. `_prune_orphans` 가 옛 `dist/src/` 트리 자동 정리. `assets/` 는 사이트 공통 전역 자산만 (이분법 — 글 자산은 글 폴더 안).

---

### v0.5.1 (2026-05-14) — 이미지 자동 최적화 + lazy loading

raster 이미지 (.jpg .jpeg .png .gif) 를 Pillow 로 다중 해상도 WebP 변종 (`{stem}-{width}.webp`, 기본 `[400, 800, 1600]`, quality 85) 자동 생성 + `<img>` 후처리로 src / srcset / sizes / `loading="lazy"` 자동 부착. 외부 URL / SVG 는 src 보존 + lazy 만. 새 site.yaml 의 `images:` 블록 (enabled/widths/quality/lazy_loading/default_sizes). `images.enabled=false` 로 회피 가능 (Pillow 없이도 빌드 통과). `_prune_article_assets` 가 webp 자매 파일 인식.

---

### v0.5.0 (2026-05-14) — BM25 기반 검색 시스템

v0.4.x 의 단순 TF 합산 + 제목 매직 ×5 → **Okapi BM25** 로 전환. `score = bm25_body(k1=1.5,b=0.75) + 3.0 · bm25_title(k1=1.2,b=0.5)`. 원본 쿼리 (≥ 2자) 가 평문에 연속 substring 으로 매치되면 곱셈 phrase boost — 본문 ×1.5 / 제목 ×2.0 (score=0 은 그대로 0). 매치 밀도 슬라이딩 윈도우 (80자) 로 스니펫 선정. 점수 함수는 `templates/search_bm25.php` 로 분리, search.php 가 require_once. 인덱스 포맷 v3 (v2 와 비호환). `tests/test_bm25.py` 25개 신설. Python↔PHP 점수 패리티 1e-6 이하 확인.

---

### v0.4.7 (2026-05-14) — 문서·코드 정합성 회복 (회귀 0)

v0.4.6 까지의 변경 결과물의 문서·코드 정합성 갭만 정리. build.py docstring / README §1·§3·§11·§16 폴더명·예시·한계 표·설정 책임 분리표 갱신. `_build_home` 의 dead branch (중복 if) 정리. dist 산출물은 v0.4.6 과 바이트 동일.

---

### v0.4.6 (2026-05-14) — 페이지네이션 FOUC 제거 + `Articles/meta.yaml` + `priority` + 설정 일원화

SSR 시점에 페이지 1 외 항목에 `style='display:none'` 인라인 부착 — 페이지 로드 직후 깜빡임 제거. `.pagination-nav` 여백 축소. `Articles/meta.yaml` 신설 (메인페이지의 카테고리-격 설정 — `per_page` / `excludes_categories` / `layout` / `styles` / `lang`). 카테고리 meta.yaml 에 `priority` (큰 값 먼저, 같은 값끼리 알파벳 순) — 부모 인덱스 페이지의 자식 section 정렬 + nav 톱레벨 정렬에 적용. site.yaml 의 메인페이지 전용 키 3개 (`home_per_page` / `home_excludes_categories` / `home_sort`) 를 `Articles/meta.yaml` 로 이전 (`home_sort` 는 dead field — 폐기).

---

### v0.4.5 (2026-05-14) — 페이지네이션 + 다국어 + 서브카테고리 인덱스 + 카테고리 meta.yaml

메인페이지 Recent / 카테고리 인덱스 / 상위에 임베드된 서브카테고리 section 마다 독립 페이지네이션 (JS hide/show, 모든 항목 SSR — SEO/접근성 영향 없음). `<html lang='ko'>` 하드코딩 제거 — site.yaml → 카테고리 meta.yaml → 글 meta.yaml 순으로 동적 결정. 서브카테고리도 자기 인덱스 페이지 (`/{top}/{sub}/`) 보유 (sitemap 도 포함). 카테고리 meta.yaml 신설 — `per_page` (자기 페이지) / `preview_per_page` (상위에 임베드 section) / `layout` / `styles` / `lang`. 비ASCII 폴더명 워닝 메시지에 어떤 폴더 → 어떤 slug 명시.

### v0.4.4 (2026-05-14) — sitemap.xml 자동 생성

`scripts/sitemap.py` 신설 (sitemaps.org 0.9). 포함 URL: 홈 + 톱레벨 카테고리 인덱스 + 모든 글 (search.php / 404 / assets / noindex 글 제외). lastmod 는 글의 `updated` (없으면 `date`); 카테고리/홈은 서브트리 lastmod 최댓값. `changefreq` / `priority` 일부러 비움 (Google 이 무시 + 부정확 priority 는 신뢰도 감점). robots.txt 의 `Sitemap:` 디렉티브 자동 활성화.

### v0.4.3 (2026-05-14) — `<title>` 정상화 + 마크다운 섹션 마커 + SEO 그룹화

글 `<title>` 이 글 제목 사용 (v0.4.2 까지의 사이트 이름 하드코딩 해소 — v0.4.0 의 noindex 폐기로 검색 결과에 뜨기 시작하면서 부적합해진 quirk 정정). 본문에 `===제목===` (등호 3개) / `======` (등호 정확히 6개) 로 명시적 섹션 분리 — state machine 으로 gap/section 처리, 코드 펜스 내부는 무시. meta.yaml 의 평면 12개 SEO 필드 → `seo:` 하위 블록 (`seo_description` → `seo.description` 등). `SeoMeta` dataclass 신설.

### v0.4.2 (2026-05-14) — 정합성 갭 정리 (회귀 0, 출력 동등)

글 slug ↔ 톱레벨 카테고리 slug 충돌을 `_validate()` 초입에서 차단 (이전엔 `_prune_orphans` 의 비결정적 사후 정리). search.php 에 `noindex, follow` (`?q=...` 노이즈 색인 차단). imgBox/imgSlideBox 인자에 balanced parser (`_scan_php_args`) — 인자 안의 `)` 처리. `{{ROBOTS_META}}` placeholder 의 들여쓰기 비의존 라인 제거 패턴.

### v0.4.1 (2026-05-14) — 빌드 PHP 의존 제거 (Parsedown 의 Python 포팅)

PHP Parsedown 1.7.4 (1712줄) → `scripts/parsedown.py` (~770줄 순수 Python, stdlib `re`/`typing` 만). 빌드 머신에 `php` 없어도 빌드 성공 (단, 런타임은 여전히 PHP — search.php; 토크나이저 패리티 검증만 PHP 있을 때 자동 수행). `markdown_parser:` 옵션 / MarkdownRenderer 추상화 / parsers/ 디렉터리 모두 제거. 패리티 검증 79/79 fixture 일치 (합성 46 + 실 글 33). dist 는 v0.4.0 과 바이트 동일.

### v0.4.0 (2026-05-13) — 정직한 캐치프레이즈 + 색인 정책 정상화 + 모듈 분할

캐치프레이즈 "SSG" → **"PHP 기반 경량 웹 사이트 생성기"** (마크다운 파서·검색이 PHP 필요한 사실 인정). 전역 `<meta robots noindex>` 일괄 제거 — 색인 허용이 기본, 글 단위 `noindex: true` 만 제외. 토크나이저 규칙: 1글자 한국어 제외 (bigram 만), 본문 5000자 절단 폐지. `templates/search_tokenize.php` 가 단일 진실원 + build.py [1] 에서 Py↔PHP fixture 18개 자동 패리티 검증. `_meta.yaml` 카테고리 오버라이드 폐기 (한국어 폴더명은 hex 코드포인트로 결정적 변환). `seo_keywords` / 잡다한 `reserved_slugs` (`c`/`p`/`api`/`blog`/...) 폐기. build.py 2085줄 → `scripts/` 패키지 분할 (yaml_parser/models/slugs/markdown/seo/search/builder).

### v0.3.2 (2026-05-10) — 검색 UI 정리 + 카테고리 스코프 검색

메인페이지 inline 검색 폼 (home-search) 제거 — nav-search 만 유지 (홈/카테고리에만 노출, 모바일도 표시). 카테고리 인덱스의 nav-search 가 `?cat=<slug>` 자동 첨부 — search.php 가 해당 카테고리 내부로 한정 + 결과 헤더에 범위 표기 + 전체 토글. 인덱스 포맷 v2 (`docs[i].category_slug` + `categories` map 추가).

### v0.3.1 (2026-05-09) — 사이트 내 검색

`_build_search()` 가 모든 글의 평문 본문+제목을 한글 bigram + 영문 토큰으로 토크나이즈, `dist/search-index.json` 생성. `templates/search.php` 가 인덱스 로드 + 점수 계산 + HTML 렌더 (클라이언트 JS 0). nav 우측 검색창 + 메인페이지 inline 폼 (모바일 nav 검색창 숨김). Python `_search_tokenize()` ↔ PHP `search_tokenize()` 가 같은 입력에 같은 출력을 내야 함.

### v0.3 (2026-05-09) — Parsedown 도입 + 글 단위 스타일 오버라이드

자체 마크다운 파서 → `Parsedown.php` (PHP CLI 호출) — 표·중첩 목록·자동 링크 등 풍부한 문법 지원. `meta.yaml` 의 `styles:` 필드로 글마다 본문 태그 (p/h3/ul/blockquote/a 등) CSS 오버라이드 (head 의 `<style>` 블록, `section TAG` 선택자). `MarkdownRenderer` 추상화 + `markdown_parser:` 토글 (`parsedown` ↔ `builtin`). YAML 파서에 nested mapping 지원.

### v0.2 (2026-05-09) — UI/UX 보존

SSG 내부는 유지, 출력 HTML/CSS 만 이전 사이트의 UI/UX (헤더 + nav 분리, `Home / Blog / 글` slash breadcrumb, `<div class="listup_module_div">` 글 목록, `common_template.css`, `<title>=site.name`, `noindex` 등) 와 동일. About 을 일반 글로 통합 (slug=about). 톱레벨 카테고리만 인덱스 생성 (서브카테고리는 그룹으로 표시). 내부 개선: head 에 SEO meta 태그 (v0.4.0 부터 실효), `/assets/` 경로 정리.

### v0.1 — SSG 시스템 자체 완성

Python stdlib only SSG 첫 동작 버전. YAML 파서·마크다운 파서·HTML 처리·라우팅 등 핵심 완비. 핵심 설계 원칙: URL 영구성, 표시명과 URL slug 분리, 외부 의존성 0, 서버 설정과 콘텐츠 분리, 빌드의 안전성.

---

*이 문서는 siheonlee.com v0.7.2 (PHP 기반 경량 웹 사이트 생성기 — 빌드는 Python + Pillow, 런타임은 PHP; 검색은 Okapi BM25 메타데이터 3-필드 색인 + PHP 정적 배열 인라인; 이미지는 WebP 다중 해상도 자동 변환; 글/홈/카테고리 모두 통일된 SEO 메타 태그 묶음 출력; 글/카테고리/홈 모두 외부 CSS 파일 + `use_common_css` 토글 + `template:` 키 지원 v0.6.4; v0.6.4 의 큰 변경 직후 발견된 누적 회귀 4 건 안정화 v0.6.5; 빌드 증분 캐싱 (글 단위, fine-grained) 도입 v0.7.0; v0.7.0 직후 누적된 문서·주석·코드 정합성 회복 v0.7.1; **빌드 16 단계 진행 표시 + 무거운 루프 라이브 카운터 + `build-report.md` 영속 리포트 문서화 v0.7.2**) 기준으로 작성되었습니다. (2026-05-17)*

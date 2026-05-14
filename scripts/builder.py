"""빌드 파이프라인 (Builder 클래스).

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
  - templates/search.php 헤더 주석의 placeholder 누수 결함 해소. `(d) {{LANG}}
    / {{PAGE_TITLE}} / ...` 같이 안내 자체에 placeholder 토큰을 박아 두면
    `_render_template` 의 단순 문자열 치환이 주석 안에서도 동작해 dist 의
    헤더가 "이 자리에 ko / Search / Lama / <a ...>...</a> 가 들어간다" 라고
    자기 결과를 인용하는 메타-광경이 됐다. 템플릿 측에서 안내 줄에 plain
    변수명 (LANG, PAGE_TITLE, ...) 만 적도록 정리. 빌더 코드는 그대로.
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
  - 콘텐츠 측 (글/홈/카테고리/sitemap/robots/redirect/feed) 의 형식은
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
    원칙 (README § 5-1 참조).
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

16단계 파이프라인 (v0.5.3 에서 _build_feeds 추가):
  [1] _load_config           — site.yaml + legacy-map.yaml + 토크나이저 패리티 검증
  [2] _scan_articles         — Articles/ 트리 순회, _ 접두 제외
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
  [11] _build_robots         — robots.txt (main + legacy)
  [12] _build_sitemap        — dist/sitemap.xml (v0.4.4 신설, v0.4.5 에서
                                서브카테고리 URL 도 포함)
  [12b] _build_feeds         — dist/feed.atom + dist/feed.rss (v0.5.3 신설).
                                scripts/feed.py 의 추상 모델로 두 파일이 같은
                                entry 목록을 공유.
  [13] _build_dispatcher     — dist-legacy/redirect.php (301 매핑)
  [14] _build_search         — dist/search.php 단일 파일 생성 (v0.6.0).
                                메타데이터 3-필드 BM25 인덱스를 PHP 정적 배열
                                리터럴로, 토크나이저 + BM25 점수 계산기를
                                같은 파일에 인라인. 옛 search-index.json /
                                search_tokenize.php / search_bm25.php 가
                                dist 에 남아 있으면 명시적으로 unlink.
  [15] _prune_orphans        — 삭제된 슬러그/카테고리의 dist 잔재 정리 +
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
from datetime import date as Date
from pathlib import Path

from .yaml_parser import yaml_load
from .models import (
    SiteConfig, ArticleMeta, SeoMeta, CategoryMeta, Article, Category,
)
from .slugs import category_slug_from_name, is_underscore_path, has_non_ascii
from .markdown import (
    escape_html,
    render_article_md,
    render_article_styles,
    normalize_styles,
    process_html,
    has_live_php,
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
from .seo import build_meta_tags, truncate_description
from .search import (
    html_to_plain,
    build_search_index,
    php_array_literal,
    run_parity_test,
)
from .sitemap import build_sitemap
from .feed import build_feed_document, render_atom, render_rss
from .report import BuildReport, abort
from . import __version__ as _SITE_VERSION


# ════════════════════════════════════════════════════════════════
# Build / Error helpers
#
# v0.5.5: 모든 경고/검증 실패는 모듈 전역 BuildReport 로 라우팅된다.
# 빌드 종료 시 self.report.render() 가 정렬된 리포트를 stderr 에 표시.
#
#   - warn(msg)               → 사이트 전역 'warning' (산출물 정상, 조언).
#   - issue(scope, target, …) → 글/카테고리 단위 'issue' (산출물 일부 누락).
#                                호출자가 적절히 진행 (글 skip 등) 해야 함.
#   - abort(msg)              → 시스템 결함. 즉시 sys.exit(1).
#
# die() 는 더 이상 모듈 전역에 존재하지 않는다. abort() 로 의도가 명확한
# 호출만 시스템 결함 경로로 가고, 나머지는 issue() 로 분류된다.
# ════════════════════════════════════════════════════════════════

_report = BuildReport()


def warn(msg: str):
    """v0.5.5: 사이트 전역 조언으로 BuildReport 에 기록 (산출물 정상)."""
    _report.warning('site', '', msg)


def issue(scope: str, target: str, msg: str, location=None):
    """v0.5.5: 글/카테고리 단위 보완 항목으로 BuildReport 에 기록.

    호출자는 issue() 후 산출물에서 해당 글/카테고리를 적절히 처리해야 한다
    (글 단위 skip, 폴백 값 사용 등). issue() 자체는 빌드 흐름을 끊지 않는다.
    """
    _report.issue(scope, target, msg, location)


def report() -> BuildReport:
    """현재 빌드 세션의 BuildReport 인스턴스 접근자."""
    return _report


def warning_count() -> int:
    return _report.warning_count()


def reset_report():
    """단위 테스트 등에서 빌드를 여러 번 돌릴 때 리포트를 초기화."""
    global _report
    _report = BuildReport()


def _copy_if_newer(src: Path, dst: Path):
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


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


def _render_template(template: str, vars: dict) -> str:
    for k, v in vars.items():
        template = template.replace('{{' + k + '}}', str(v) if v is not None else '')
    return template


# ════════════════════════════════════════════════════════════════
# Builder
# ════════════════════════════════════════════════════════════════

class Builder:
    SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$')
    DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')

    def __init__(self, base_dir: Path):
        self.base = base_dir
        self.articles_dir = base_dir / 'Articles'
        self.assets_dir = base_dir / 'assets'
        self.templates_dir = base_dir / 'templates'
        self.dist = base_dir / 'dist'
        self.dist_legacy = base_dir / 'dist-legacy'

        self.site: SiteConfig = None
        self.legacy_map: dict = {}
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

    # ── [1] Config load ──────────────────────────────────────

    def _load_config(self):
        site_yaml = self.base / 'site.yaml'
        if not site_yaml.exists():
            abort(f'site.yaml not found at {site_yaml}')
        raw = yaml_load(site_yaml.read_text(encoding='utf-8'))

        def get(key, default=None):
            return raw.get(key, default)

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
            reserved_slugs=get('reserved_slugs') or [],
            warn_on_underscore_ref=bool(get('warn_on_underscore_ref', True)),
            warn_on_missing_asset=bool(get('warn_on_missing_asset', True)),
            warn_on_stale_updated=bool(get('warn_on_stale_updated', True)),
            description_truncate=int(get('description_truncate') or 150),
            robots_txt_main=get('robots_txt_main') or 'User-agent: *\nAllow: /\n',
            robots_txt_legacy=get('robots_txt_legacy') or 'User-agent: *\nAllow: /\n',
            # v0.4.5: i18n + 카테고리 페이지네이션 디폴트.
            # v0.4.6: home_* 류 (home_per_page / home_excludes_categories /
            # home_sort) 는 Articles/meta.yaml 로 이전됨 — 더 이상 site.yaml
            # 에서 읽지 않는다. 옛 site.yaml 에 잔존하더라도 조용히 무시.
            lang=str(get('lang') or 'ko'),
            category_per_page=int(get('category_per_page') or 20),
            category_preview_per_page=int(get('category_preview_per_page') or 5),
            # v0.5.4: 시스템 페이지(404 / search)의 `<title>` 본문 텍스트.
            # 양옆은 default_title_prefix / default_title_suffix 로 감싸진다.
            error_404_title=str(get('error_404_title') or 'Not Found'),
            search_title=str(get('search_title') or 'Search'),
            # v0.5.1: 이미지 자동 최적화 설정.
            images=self._parse_image_config(get('images') or {}),
        )

        # v0.4.6: 사용자가 옛 home_* 키를 site.yaml 에 그대로 두면 알아채지
        # 못한 채 무시될 수 있으므로 한 번 경고 — 마이그레이션 가이드 역할.
        for legacy_key in ('home_per_page', 'home_excludes_categories', 'home_sort'):
            if legacy_key in raw:
                warn(f"site.yaml: '{legacy_key}' 는 v0.4.6 부터 Articles/meta.yaml "
                     f"로 이전되었습니다. site.yaml 에서 제거하고 Articles/meta.yaml "
                     f"의 해당 필드를 사용하세요.")

        legacy_yaml = self.base / 'legacy-map.yaml'
        if legacy_yaml.exists():
            self.legacy_map = yaml_load(legacy_yaml.read_text(encoding='utf-8'))

        # 토크나이저 패리티 검증 (PHP 없으면 워닝만)
        # v0.5.5: 패리티 검증 실패는 시스템 결함 (Py/PHP 토크나이저 동등성
        # 위배 — 검색 인덱스 신뢰도에 직결) 이라 abort 경로로 보낸다.
        run_parity_test(self.templates_dir, php_bin='php',
                        warn_fn=warn, die_fn=abort)

        # v0.5.1: 이미지 최적화가 켜져 있는데 Pillow 가 없으면 워닝 (die 가 아닌
        # 워닝 — 이미지가 한 장도 없는 사이트는 빌드가 통과해야 하므로 _sync_assets
        # 단계에서 실제 raster 이미지를 만났을 때 die 한다).
        if self.site.images.enabled and not _HAS_PIL:
            warn('이미지 최적화가 켜져 있지만 Pillow 가 설치되지 않았습니다. '
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

    # ── [2] Content scan ──────────────────────────────────────

    def _scan_articles(self):
        if not self.articles_dir.is_dir():
            abort(f'Articles/ directory not found at {self.articles_dir}')

        for root, dirs, files in os.walk(self.articles_dir):
            root_path = Path(root)

            if is_underscore_path(root_path, self.articles_dir):
                dirs.clear()
                continue

            dirs[:] = [d for d in dirs if not d.startswith('_')]

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
                issue(
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
                issue(
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
                issue(
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
                issue(
                    'article', slug,
                    f"meta.yaml: 'seo' 는 매핑이어야 합니다 "
                    f"(받은 값: {seo_raw!r}) — 빈 seo 로 폴백.",
                    meta_file,
                )
                seo_raw = {}

            # v0.5.5: 빈 문자열을 None 으로 강제 변환하지 않는다.
            # SeoMeta 가 None/''/'text' 세 상태를 보존해 build_meta_tags 가
            # 적절히 처리한다 (None/'' → 메타 태그 누락, '' → 추가로 리포트).
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
                og_type=seo_raw.get('og_type') or 'article',
                twitter_card=seo_raw.get('twitter_card') or 'summary_large_image',
                twitter_image=seo_raw.get('twitter_image'),
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
                issue(
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
                    issue(
                        'article', slug,
                        f"meta.yaml: 'nav_priority' 는 정수여야 합니다 "
                        f"(받은 값: {nav_priority_raw!r}) — 0 으로 폴백.",
                        meta_file,
                    )
                    nav_priority = 0

            article.meta = ArticleMeta(
                slug=slug,
                title=title,
                date=date_str,
                updated=updated,
                noindex=noindex,
                lang=lang,
                seo=seo,
                styles=normalize_styles(raw.get('styles')),
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
                issue(
                    'article', m.slug,
                    f'slug 정규식 불일치: {m.slug!r} — 글이 빌드에서 제외됨.',
                    meta_path,
                )
                keep_this = False

            if m.slug in self.site.reserved_slugs:
                issue(
                    'article', m.slug,
                    f'slug 예약어: {m.slug!r} — 글이 빌드에서 제외됨.',
                    meta_path,
                )
                keep_this = False

            if m.slug in seen_slugs:
                other = seen_slugs[m.slug]
                issue(
                    'article', m.slug,
                    f"slug 중복: {m.slug!r} — 뒤늦게 발견된 쪽의 글이 "
                    f"빌드에서 제외됨 (먼저 발견된 글: {other}).",
                    meta_path,
                )
                keep_this = False
            else:
                seen_slugs[m.slug] = article.source_dir

            if not self.DATE_RE.match(m.date):
                issue(
                    'article', m.slug,
                    f'date 형식 오류: {m.date!r} (YYYY-MM-DD 형식 필요) '
                    f'— 글이 빌드에서 제외됨.',
                    meta_path,
                )
                keep_this = False

            if m.updated:
                if not self.DATE_RE.match(m.updated):
                    issue(
                        'article', m.slug,
                        f'updated 형식 오류: {m.updated!r} — updated 를 '
                        f'무시하고 진행.',
                        meta_path,
                    )
                    m.updated = None
                elif m.updated < m.date:
                    issue(
                        'article', m.slug,
                        f'updated ({m.updated}) 가 date ({m.date}) 보다 '
                        f'앞섭니다 — 그대로 진행하지만 의도 확인 권장.',
                        meta_path,
                    )

            if keep_this:
                kept.append(article)

        self.articles = kept

        for url_path, slug in self.legacy_map.items():
            if slug is not None and slug not in seen_slugs:
                issue(
                    'legacy-map', url_path,
                    f"legacy-map.yaml: slug {slug!r} 미존재 — "
                    f"'{url_path}' 항목을 건너뜁니다.",
                    self.base / 'legacy-map.yaml',
                )

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
                issue(
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
                _report.warning(
                    'category', '/'.join(cat.path),
                    '이 카테고리에 글이 하나도 없습니다 (빈 카테고리).',
                    self.articles_dir.joinpath(*cat.path),
                )

        if self.site.warn_on_stale_updated:
            for article in self.articles:
                if article.meta.updated and article.content_file:
                    try:
                        mtime = Date.fromtimestamp(
                            article.content_file.stat().st_mtime
                        ).isoformat()
                        if mtime > article.meta.updated:
                            _report.warning(
                                'article', article.meta.slug,
                                f'meta.yaml 의 updated ({article.meta.updated}) '
                                f'가 content 파일의 수정 시각 ({mtime}) 보다 '
                                f'오래되었습니다 — 갱신이 누락된 것은 아닌지 확인.',
                                article.content_file,
                            )
                    except Exception:
                        pass

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
                issue(
                    'category', '/'.join(full_path_for_warn),
                    f'카테고리 폴더명이 빈 slug 로 변환됩니다: {folder_name!r} '
                    f'— 카테고리가 빌드되지 않을 수 있습니다.',
                    self.articles_dir.joinpath(*full_path_for_warn),
                )
            if has_non_ascii(folder_name) and folder_name not in warned_folders:
                _report.warning(
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

    def _parse_category_meta_file(self, meta_file: Path) -> CategoryMeta:
        """임의 경로의 meta.yaml 을 CategoryMeta 로 파싱 (v0.4.6 helper).

        `Articles/meta.yaml` (루트 = 메인페이지) 와 카테고리 폴더의 meta.yaml
        둘 다에 동일한 파싱 로직 적용.

        v0.5.4: `title` / `seo` / `nav_priority` 도 파싱한다. `title` 은
        페이지 자체의 `<title>` 본문이고, `seo.title_prefix` / `seo.title_suffix`
        는 site 디폴트를 오버라이드한다. 글 폴더의 meta.yaml 이 우연히 이
        함수로 들어와도 (`_scan_articles` 가 미리 거른 경우만) `slug` / `date`
        가 있으면 빈 CategoryMeta 로 폴백 (안전망). 단 `title` 만 있는 경우는
        카테고리/홈 페이지의 정상적인 title override 로 취급한다.
        """
        if not meta_file.exists():
            return CategoryMeta()

        try:
            raw = yaml_load(meta_file.read_text(encoding='utf-8'))
        except Exception as e:
            issue(
                'category', str(meta_file.parent.name),
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
        cat_target = str(meta_file.parent.name)

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
                issue(
                    'category', cat_target,
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
            issue(
                'category', cat_target,
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
            issue(
                'category', cat_target,
                f"meta.yaml: 'seo' 는 매핑이어야 합니다 "
                f"(받은 값: {seo_raw!r}) — 빈 seo 로 폴백.",
                meta_file,
            )
            seo_raw = {}

        # v0.5.5: 빈 문자열 보존 (글 SeoMeta 와 동일 정책).
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
            og_type=seo_raw.get('og_type') or 'website',
            twitter_card=seo_raw.get('twitter_card') or 'summary_large_image',
            twitter_image=seo_raw.get('twitter_image'),
        )

        # v0.5.4: nav_priority — 톱레벨 nav 정렬 키 (priority 와 별개 축).
        nav_priority_raw = raw.get('nav_priority')
        if nav_priority_raw is None:
            nav_priority = 0
        else:
            try:
                nav_priority = int(nav_priority_raw)
            except (TypeError, ValueError):
                issue(
                    'category', cat_target,
                    f"meta.yaml: 'nav_priority' 는 정수여야 합니다 "
                    f"(받은 값: {nav_priority_raw!r}) — 0 으로 폴백.",
                    meta_file,
                )
                nav_priority = 0

        return CategoryMeta(
            per_page=int(per_page) if per_page is not None else None,
            preview_per_page=int(preview) if preview is not None else None,
            layout=str(layout),
            lang=str(lang_val) if lang_val else None,
            styles=normalize_styles(styles_raw),
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
            self.articles_dir / 'meta.yaml'
        )

    # v0.4.6: Articles/meta.yaml 이 통째로 없거나 per_page 가 비어 있을 때
    # 적용되는 코드 디폴트. site.yaml 에서 home_per_page 가 제거된 자리.
    HOME_PER_PAGE_DEFAULT = 5

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
            issue(
                page_kind, slug,
                "meta.yaml: 'seo.description' 필드가 없습니다 "
                "— 외부 노출용 한 줄 설명을 작성해주세요. "
                "(description / og:description / twitter:description 메타 "
                "태그가 누락됩니다.)",
                location,
            )
        elif desc_val == '':
            issue(
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
            if child.name.startswith('_'):
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

    def _render_articles(self):
        tpl = _load_template(self.templates_dir, 'article.html')
        nav_links = self._nav_links_html()

        for article in self.articles:
            m = article.meta
            content_path = article.content_file

            if not content_path or not content_path.exists():
                issue(
                    'article', m.slug,
                    'content 파일을 찾을 수 없어 글을 빌드하지 않습니다.',
                    article.source_dir,
                )
                continue

            content_text = content_path.read_text(encoding='utf-8')

            if content_path.suffix == '.md':
                rr = render_article_md(
                    content_text, m.slug, article.source_dir,
                )
                # v0.4.3: 본문 자동 첫 갭 + 섹션 마커 (===제목===, ======) 처리.
                body_html = resolve_section_markers(rr.html, m.title)
            else:
                rr = process_html(content_text, m.slug, article.source_dir)
                body_html = rr.html

            self.rendered_bodies[m.slug] = html_to_plain(rr.html)

            # v0.5.5: description 필수 정책 + 본문 ↔ 메타데이터 분리.
            #   - seo.description 이 None (키 부재/값 부재) → 작성자가 의도적
            #     으로 누락한 게 아니라 필수 필드를 빠뜨린 것으로 간주, issue.
            #   - seo.description 이 '' (빈 문자열) → 작성자 실수, issue.
            #   - 둘 다의 경우 summary 가 누락된다 (피드 <summary> /
            #     <description> 태그 자체가 출력되지 않음, gallery 도 description
            #     없이 그라데이션 플레이스홀더만).
            #   - 본문 폴백 없음. rr.first_paragraph / rr.first_image 참조 제거.
            desc_val = m.seo.description
            if desc_val is None:
                issue(
                    'article', m.slug,
                    "meta.yaml: 'seo.description' 필드가 없습니다 "
                    "— 외부 노출용 한 줄 설명을 작성해주세요. "
                    "(description / og:description / twitter:description / "
                    "피드 summary 가 모두 누락됩니다.)",
                    article.source_dir / 'meta.yaml',
                )
                summary = ''
            elif desc_val == '':
                issue(
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

            article_styles = render_article_styles(m.styles)

            if self.site.warn_on_underscore_ref:
                for pattern in [r'src="([^"]+)"', r'href="([^"]+)"']:
                    for url_match in re.finditer(pattern, rr.html):
                        ref = url_match.group(1)
                        if '/_' in ref or ref.startswith('_'):
                            _report.warning(
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

            crumb_parts = []
            top_cat = self._top_category_for_article(article)
            if top_cat:
                top_url = f"/{top_cat.slug}/"
                crumb_parts.append((top_cat.folder_name, top_url))
                middle_folders = article.category_path[1:-1]
                for folder in middle_folders:
                    crumb_parts.append((folder, top_url))
            crumb_parts.append((article.category_path[-1], None))
            nav_tracker = self._nav_tracker_for_path(crumb_parts)

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

            # v0.4.3: <title> 에 글 제목 사용. full_title 은
            # build_meta_tags 가 만든 `{prefix}{title}{suffix}` 문자열.
            page_title = full_title or self.site.name

            # v0.4.5: 글 단위 lang override (없으면 site.lang).
            page_lang = m.lang or self.site.lang

            vars_ = {
                'LANG': escape_html(page_lang),
                'META_TAGS': meta_tags,
                'ARTICLE_STYLES': article_styles,
                'PAGE_TITLE': escape_html(page_title),
                'MAIN_TITLE': escape_html(self.site.main_title),
                'NAV_TRACKER': nav_tracker,
                'NAV_LINKS': nav_links,
                'BODY': body_html,
                'COPYRIGHT_YEAR': self._copyright_year(),
                'COPYRIGHT_HOLDER': escape_html(self.site.copyright_holder),
            }
            page_html = _render_template(tpl_local, vars_)

            ext = 'php' if has_live_php(page_html) else 'html'

            out_dir = self.dist / m.slug
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f'index.{ext}'
            out_file.write_text(page_html, encoding='utf-8')

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

        SVG / WebP / 비이미지 파일은 v0.5.0 과 동일하게 그대로 복사.
        """
        for article in self.articles:
            m = article.meta
            src_root = article.source_dir
            dst_root = self.dist / m.slug

            for src_file in src_root.rglob('*'):
                if not src_file.is_file():
                    continue
                if is_underscore_path(src_file, src_root):
                    continue
                if src_file.name in ('meta.yaml', 'content.md', 'content.html'):
                    continue
                rel = src_file.relative_to(src_root)
                dst_file = dst_root / rel

                if self._should_optimize_image(src_file):
                    self._optimize_and_register(
                        src_file=src_file,
                        dst_file=dst_file,
                        url_prefix=f'/{m.slug}/',
                        rel_path=rel,
                    )
                else:
                    _copy_if_newer(src_file, dst_file)

            self._prune_article_assets(article)

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
                _report.warning('site', '', err, location=src_file)
            _copy_if_newer(src_file, dst_file)
            return

        # URL 등록 — HTML 의 <img src> 가 갖는 형태와 정확히 일치해야 함.
        rel_str = str(rel_path).replace('\\', '/')
        url = url_prefix + rel_str
        self.image_variants[url] = variants

    def _prune_article_assets(self, article: Article):
        m = article.meta
        src_root = article.source_dir
        dst_root = self.dist / m.slug
        if not dst_root.exists():
            return

        expected = set()
        # v0.5.2: 글 자산이 글의 index.html 과 같은 폴더에 동거하게 되어,
        # asset 정리에서 글 본체 산출물 (index.html / index.php) 을 보존해야
        # 한다. asset sync 단계가 article render 보다 먼저 돌긴 하지만,
        # 두 번째 빌드부터는 이전 빌드의 결과가 이미 존재한다.
        expected.add(dst_root / 'index.html')
        expected.add(dst_root / 'index.php')

        for src_file in src_root.rglob('*'):
            if not src_file.is_file():
                continue
            if is_underscore_path(src_file, src_root):
                continue
            if src_file.name in ('meta.yaml', 'content.md', 'content.html'):
                continue
            rel = src_file.relative_to(src_root)
            # v0.5.1: raster 이미지는 원본 자리에 webp 변종들이 떨어진다.
            # expected 에 변종 파일명들을 등록 (원본 파일명은 dist 에 없음).
            if self._should_optimize_image(src_file):
                stem = src_file.stem
                for w in self.site.images.widths:
                    expected.add(dst_root / rel.parent / f'{stem}-{w}.webp')
                # 더 큰 원본 width 변종도 있을 수 있으므로 (optimize_image 가
                # 원본 width 가 max(widths) 보다 크면 그 변종도 만든다),
                # dir 내의 같은 stem-*.webp 파일은 모두 보존 대상으로 간주.
                for sibling in (dst_root / rel.parent).glob(f'{stem}-*.webp'):
                    expected.add(sibling)
            else:
                expected.add(dst_root / rel)

        for existing in list(dst_root.rglob('*')):
            if existing.is_file() and existing not in expected:
                existing.unlink()

        _remove_empty_dirs(dst_root)

    # ── [7] Category indexes ──────────────────────────────────

    def _gallery_tile_html(self, article: 'Article', hidden: bool = False) -> str:
        """v0.5.3: 갤러리 레이아웃의 한 타일 HTML.

        v0.5.5: 썸네일 우선순위 = seo.og_image > site.default_og_image > 빈
        플레이스홀더 (그라데이션). 본문 폴백 (옛 `rr.first_image`) 제거 —
        본문 ↔ 메타데이터 분리 원칙 (README § 17 참조). 썸네일이 없는 타일은
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
        more_url 이 주어지면 section 우측 상단에 → 링크가 표시된다.
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
            label_html = (
                f"{escape_html(label)} "
                f"<a class='more-link' href='{more_url}'>→</a>"
            )
        else:
            label_html = escape_html(label)

        return (
            f"<div class='gap'><p>{label_html}</p></div>\n"
            f"<section {attrs}>\n{inner}\n</section>\n"
            f"{nav_html}"
        )

    def _category_styles_html(self, cat: Category) -> str:
        """카테고리 meta.yaml 의 styles → <style> 블록.

        section TAG 선택자로 글 styles 와 동일한 우선순위 정책 적용.
        """
        return render_article_styles(cat.meta.styles)

    def _build_category_page(self, cat: Category):
        """톱레벨/서브카테고리 공용 인덱스 페이지 빌더 (v0.4.5).

        - 톱레벨 카테고리: 자식 서브카테고리마다 section 한 개씩.
                          자식이 없으면 (이 카테고리의 직속 articles 만 있는 경우)
                          자기 자신을 한 section 으로.
        - 서브카테고리: 자기 자신을 한 section 으로. 만약 더 깊은 자식이
                       있다면 (3+ depth) 자식별 section 도 추가로.
        - 페이지네이션: section 마다 독립 (data-pagination-group 으로 짝지음).
        - styles: 이 카테고리의 meta.yaml 의 styles 가 head 의 <style> 로.
        - lang: 카테고리 meta.yaml 의 lang 우선, 없으면 site.lang.
        """
        tpl = _load_template(self.templates_dir, 'category.html')
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

        # breadcrumb: 톱레벨이면 [(folder, url)], 서브면 [(top, top_url), (sub, None)]
        if is_top:
            crumb_parts = [(cat.folder_name, url_prefix)]
        else:
            top_cat = self.categories.get((cat.path[0],))
            crumb_parts = []
            if top_cat is not None:
                crumb_parts.append((top_cat.folder_name, f"/{top_cat.slug}/"))
            # 중간 폴더들 (3+ depth) → 가장 가까운 톱레벨로 링크 (원본 quirk 와 일치).
            for mid_folder in cat.path[1:-1]:
                crumb_parts.append(
                    (mid_folder,
                     f"/{top_cat.slug}/" if top_cat else None)
                )
            crumb_parts.append((cat.folder_name, None))
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

        vars_ = {
            'LANG': escape_html(page_lang),
            'META_TAGS': meta_tags,
            'PAGE_TITLE': escape_html(page_title),
            'MAIN_TITLE': escape_html(self.site.main_title),
            'NAV_TRACKER': nav_tracker,
            'NAV_LINKS': nav_links,
            'NAV_SEARCH_CAT': escape_html(search_cat),
            'SUBCATEGORY_SECTIONS': subcategory_sections,
            'CATEGORY_STYLES': self._category_styles_html(cat),
            'COPYRIGHT_YEAR': self._copyright_year(),
            'COPYRIGHT_HOLDER': escape_html(self.site.copyright_holder),
        }
        page_html = _render_template(tpl, vars_)

        out_dir = self.dist.joinpath(*cat.slug_path)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / 'index.html').write_text(page_html, encoding='utf-8')

    def _build_categories(self):
        """v0.4.5: 톱레벨 + 모든 서브카테고리에 대해 인덱스 페이지 생성.

        v0.4.4 까지는 톱레벨만 인덱스가 있었음 (원본 lama.pe.kr quirk 보존).
        v0.4.5 에서 이 quirk 를 해제 — 서브카테고리도 자기 인덱스 페이지를 가짐.
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
        tpl = _load_template(self.templates_dir, 'home.html')

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

        vars_ = {
            'LANG': escape_html(page_lang),
            'META_TAGS': meta_tags,
            'PAGE_TITLE': escape_html(page_title),
            'MAIN_TITLE': escape_html(self.site.main_title),
            'NAV_LINKS': self._nav_links_html(),
            'HOME_SECTION_CLASS': section_class,
            'HOME_PER_PAGE': str(per_page),
            'ARTICLE_LIST': article_items,
            'PAGINATION_NAV': pagination_nav,
            'COPYRIGHT_YEAR': self._copyright_year(),
            'COPYRIGHT_HOLDER': escape_html(self.site.copyright_holder),
        }
        page_html = _render_template(tpl, vars_)
        self.dist.mkdir(parents=True, exist_ok=True)
        (self.dist / 'index.html').write_text(page_html, encoding='utf-8')

    # ── [9] Site assets ───────────────────────────────────────

    def _copy_site_assets(self):
        """assets/ → dist/assets/ 동기화.

        v0.5.1: assets/ 안의 raster 이미지도 webp 변환 대상. variants 는
        `/assets/{rel}` URL 키로 등록 — 템플릿/HTML 에서 `/assets/foo.png` 형태로
        참조되는 이미지가 후처리에서 webp 로 치환된다.
        """
        if not self.assets_dir.is_dir():
            return
        dst_assets = self.dist / 'assets'
        dst_assets.mkdir(parents=True, exist_ok=True)
        for src_file in self.assets_dir.rglob('*'):
            if not src_file.is_file():
                continue
            rel = src_file.relative_to(self.assets_dir)
            dst_file = dst_assets / rel
            if self._should_optimize_image(src_file):
                self._optimize_and_register(
                    src_file=src_file,
                    dst_file=dst_file,
                    url_prefix='/assets/',
                    rel_path=rel,
                )
            else:
                _copy_if_newer(src_file, dst_file)

    # ── [10] 404 page ─────────────────────────────────────────

    def _build_404(self):
        tpl = _load_template(self.templates_dir, '404.html')
        # v0.5.4: 404 <title> 폴백 체인.
        # 본문 = site.error_404_title. 양옆 = site.default_title_prefix/suffix
        # (404 는 meta.yaml 이 없으므로 override 불가능 — site.yaml 한 군데에서만).
        page_title = self._wrap_page_title(self.site.error_404_title)
        vars_ = {
            'LANG': escape_html(self.site.lang),
            'PAGE_TITLE': escape_html(page_title),
            'MAIN_TITLE': escape_html(self.site.main_title),
            'NAV_LINKS': self._nav_links_html(),
            'COPYRIGHT_YEAR': self._copyright_year(),
            'COPYRIGHT_HOLDER': escape_html(self.site.copyright_holder),
        }
        page_html = _render_template(tpl, vars_)
        self.dist.mkdir(parents=True, exist_ok=True)
        (self.dist / '404.html').write_text(page_html, encoding='utf-8')

    # ── [11] robots.txt ───────────────────────────────────────

    def _build_robots(self):
        self.dist.mkdir(parents=True, exist_ok=True)
        (self.dist / 'robots.txt').write_text(
            self.site.robots_txt_main, encoding='utf-8'
        )
        self.dist_legacy.mkdir(parents=True, exist_ok=True)
        (self.dist_legacy / 'robots.txt').write_text(
            self.site.robots_txt_legacy, encoding='utf-8'
        )

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

        generator = f'siheonlee.com v{_SITE_VERSION} — github.com/siheonlee'
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

    # ── [13] Legacy dispatcher ────────────────────────────────

    def _build_dispatcher(self):
        # v0.4.2: site.yaml 의 base_url 을 사용 (이전 버전은 도메인 하드코딩).
        base_url = self.site.base_url.rstrip('/')
        base_url_php = base_url.replace("'", "\\'")

        lines = ["<?php"]
        lines.append(f"$BASE_URL = '{base_url_php}';")
        lines.append("$map = [")
        for url_path, slug in self.legacy_map.items():
            key_escaped = url_path.replace("'", "\\'")
            if slug is None:
                lines.append(f"    '{key_escaped}' => null,")
            else:
                lines.append(f"    '{key_escaped}' => '{slug}',")
        lines.append("];")
        lines.append("")
        lines.append("$path = urldecode(parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH));")
        lines.append("$path = rtrim($path, '/') . '/';")
        lines.append("")
        lines.append("if (array_key_exists($path, $map)) {")
        lines.append("    $slug = $map[$path];")
        lines.append("    if ($slug === null) {")
        lines.append("        http_response_code(410);")
        lines.append("        echo '410 Gone';")
        lines.append("        exit;")
        lines.append("    }")
        lines.append("    header(\"Location: {$BASE_URL}/{$slug}/\", true, 301);")
        lines.append("    exit;")
        lines.append("}")
        lines.append("")
        lines.append("http_response_code(404);")
        lines.append("header(\"Location: {$BASE_URL}/404.html\", true, 302);")
        lines.append("exit;")

        self.dist_legacy.mkdir(parents=True, exist_ok=True)
        (self.dist_legacy / 'redirect.php').write_text(
            '\n'.join(lines), encoding='utf-8'
        )

    # ── [14] Search index inlined into search.php ────────────
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

        # v0.5.4: search <title> 폴백 체인. 404 와 동일 — site.search_title
        # + site.default_title_prefix/suffix. search 도 meta.yaml 이 없는 시스템
        # 페이지라 site.yaml 에서만 설정한다.
        search_title = self._wrap_page_title(self.site.search_title)
        vars_ = {
            'LANG': escape_html(self.site.lang),
            'PAGE_TITLE': escape_html(search_title),
            'MAIN_TITLE': escape_html(self.site.main_title),
            'NAV_LINKS': self._nav_links_html(),
            'COPYRIGHT_YEAR': self._copyright_year(),
            'COPYRIGHT_HOLDER': escape_html(self.site.copyright_holder),
        }
        page = _render_template(tpl, vars_)
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
        print('빌드 시작...', flush=True)

        # v0.5.1: 이미지 최적화 도입으로 asset 단계가 article render 보다
        # 먼저 와야 한다. asset 단계가 raster 이미지를 webp 변종으로 만들고
        # self.image_variants 를 채우면, _render_articles 가 그 정보로
        # 글 본문 HTML 의 <img> 를 webp + srcset + lazy 로 치환한다.
        self._load_config()                    # [1]
        self._scan_articles()                  # [2]
        self._parse_frontmatter()              # [3]
        self._validate()                       # [4]
        self._sync_assets()                    # [5] (v0.5.1: 옛 [6])
        self._copy_site_assets()               # [6] (v0.5.1: 옛 [9])
        self._render_articles()                # [7] (v0.5.1: 옛 [5])
        self._build_categories()               # [8]
        self._build_home()                     # [9]
        self._build_404()                      # [10]
        self._build_robots()                   # [11]
        self._build_sitemap()                  # [12]
        self._build_feeds()                    # [12b] (v0.5.3) RSS/Atom
        self._build_dispatcher()               # [13]
        self._build_search()                   # [14]
        self._prune_orphans()                  # [15]

        art_count = len(self.articles)
        cat_count = len(self.categories)
        issue_count = _report.issue_count()
        warn_count = _report.warning_count()
        print(
            f'\n빌드 완료: {art_count} 글, {cat_count} 카테고리, '
            f'{issue_count} 보완 필요, {warn_count} 살펴볼 사항.',
        )
        print(f'산출물: dist/ (siheonlee.com), dist-legacy/ (lama.pe.kr).')

        # v0.5.5: 빌드 종료 시 일원화 리포트 출력. meta.yaml 의 필드 부족 /
        # 빈 문자열 / 형식 오류 등 모든 콘텐츠 결함이 여기 모아진다.
        _report.render()

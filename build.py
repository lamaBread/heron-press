#!/usr/bin/env python3
"""siheonlee.com v0.5.4 — PHP 기반 경량 웹 사이트 생성기.

이 파일은 빌드의 진입점(entry point) 일 뿐, 모든 실제 로직은
`scripts/` 패키지 안에 모듈별로 나뉘어 있다.

Usage:
    python build.py           # full build
    python build.py --clean   # wipe dist/ + dist-legacy/ before build
    python -m unittest discover -s tests   # BM25 단위 테스트 (v0.5.0)

빌드 의존성 (v0.5.4):
    Python 3.10+ stdlib
    Pillow (PIL fork) — 이미지 자동 최적화 (`pip install Pillow`).
        site.yaml 의 images.enabled=false 로 두면 Pillow 없어도 동작.

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

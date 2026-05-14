#!/usr/bin/env python3
"""siheonlee.com v0.4.7 — PHP 기반 경량 웹 사이트 생성기.

이 파일은 빌드의 진입점(entry point) 일 뿐, 모든 실제 로직은
`scripts/` 패키지 안에 모듈별로 나뉘어 있다.

Usage:
    python build.py           # full build
    python build.py --clean   # wipe dist/ + dist-legacy/ before build

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

"""siheonlee.com v0.8.2 — 빌더 내부 모듈 묶음.

이 패키지는 v0.8.1 부터 `src/scripts/` 에 있다 (최상위 정리 — 빌더
일체가 src/ 아래로 이동). 프로젝트 루트의 build.py 가 자기 폴더의 src/
를 sys.path 에 올린 뒤 이 패키지를 import 한다.
모듈:
  - yaml_parser  — stdlib only YAML 부분 구현
  - models       — dataclass 정의 (SiteConfig, ArticleMeta, SeoMeta, ...)
  - slugs        — 카테고리/폴더명 → slug 변환
  - markdown     — 마크다운 본문 후처리 + PHP 함수 시뮬레이션 + per-article styles
  - parsedown    — Parsedown 1.7.4 의 Python 포팅 (v0.4.1)
  - seo          — <meta> 태그 빌더. v0.5.5 부터 본문 폴백 제거 (메타데이터 분리 원칙).
  - images       — 이미지 자동 최적화 (WebP + srcset + lazy loading, v0.5.1)
  - search       — 토크나이저, BM25 인덱스, PHP 정적 배열 직렬화 (v0.6.0 v4 포맷)
  - sitemap      — sitemap.xml 생성 (v0.4.4)
  - feed         — RSS / Atom 피드 생성 (v0.5.3)
  - report       — BuildReport / issue / warning / abort (v0.5.5)
  - cache        — 글 단위 빌드 증분 캐시 (v0.7.0 신설)
  - builder      — 빌드 파이프라인 (Builder 클래스)

__version__:
  사이트 전역 버전 문자열의 단일 source of truth.

  v0.8.2 의 버전 디커플링 (B1) 이전까지는 feed.atom/feed.rss 의
  <generator> 가 이 값을 표기해 dist 산출물에 새는 유일한 경로였다.
  그 때문에 문서·구조 전용 릴리스 (v0.7.2 → v0.8.0 → v0.8.1) 는 이
  값을 '0.7.2' 에 동결해야 dist byte-동일 검증이 성립했다.

  v0.8.2 부터 generator 문자열에서 버전 토큰이 제거돼 `__version__`
  은 **dist 산출물에 전혀 영향을 주지 않는다**. 남은 소비자는 모두
  dist 밖이다:
    - cache global_hash (`cache.py`) — 빌더 버전이 바뀌면 캐시 일괄
      무효화. 단 코드 릴리스는 `scripts/` 해시로 이미 무효화되므로
      실효는 거의 없고, 문서 릴리스는 캐시를 유지하는 게 옳다.
    - 빌드 콘솔 출력 / build-report.md (모두 dist 밖).
  따라서 이 값은 이제 릴리스 버전을 자유롭게 추종한다 — 더 이상
  byte-동일 검증을 위해 동결할 필요가 없다.
"""

__version__ = '0.8.2'

"""siheonlee.com v0.6.0 — 빌더 내부 모듈 묶음.

루트의 build.py 가 이 패키지를 import 한다.
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
  - builder      — 빌드 파이프라인 (Builder 클래스)
  - migrate      — 기존 글 마이그레이션 도구 (직접 실행)

__version__:
  사이트 전역 버전 문자열의 단일 source of truth. feed generator 등
  버전을 표기하는 모든 산출물이 이 값을 참조한다.
"""

__version__ = '0.6.0'

"""siheonlee.com v0.4.4 — 빌더 내부 모듈 묶음.

루트의 build.py 가 이 패키지를 import 한다.
모듈:
  - yaml_parser  — stdlib only YAML 부분 구현
  - models       — dataclass 정의 (SiteConfig, ArticleMeta, SeoMeta, ...)
  - slugs        — 카테고리/폴더명 → slug 변환
  - markdown     — 마크다운 본문 후처리 + PHP 함수 시뮬레이션 + per-article styles
  - parsedown    — Parsedown 1.7.4 의 Python 포팅 (v0.4.1)
  - seo          — <meta> 태그 빌더
  - search       — 토크나이저, 검색 인덱스, Py↔PHP 패리티 테스트
  - sitemap      — sitemap.xml 생성 (v0.4.4)
  - builder      — 빌드 파이프라인 (Builder 클래스)
  - migrate      — 기존 글 마이그레이션 도구 (직접 실행)
"""

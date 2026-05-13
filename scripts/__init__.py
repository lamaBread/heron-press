"""siheonlee.com v0.4.0 — 빌더 내부 모듈 묶음.

루트의 build.py 가 이 패키지를 import 한다.
모듈 분할 (v0.4.0):
  - yaml_parser  — stdlib only YAML 부분 구현
  - models       — dataclass 정의
  - slugs        — 카테고리/폴더명 → slug 변환
  - markdown     — 마크다운 파서 추상화 + 본문 후처리 + PHP 함수 시뮬레이션 + per-article styles
  - seo          — <meta> 태그 빌더
  - search       — 토크나이저, 검색 인덱스, Py↔PHP 패리티 테스트
  - builder      — 빌드 파이프라인 (Builder 클래스)
"""

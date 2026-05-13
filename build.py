#!/usr/bin/env python3
"""siheonlee.com v0.4.0 — PHP 기반 경량 웹 사이트 생성기.

이 파일은 빌드의 진입점(entry point) 일 뿐, 모든 실제 로직은
`scripts/` 패키지 안에 모듈별로 나뉘어 있다.

Usage:
    python build.py           # full build
    python build.py --clean   # wipe dist/ + dist-legacy/ before build

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

# siheonlee.com 빌드 리포트

- **버전**: v0.7.2
- **빌드 시각**: 2026-05-17 02:56:37
- **소요**: 3.3s
- **결과**: 6 글 · 2 카테고리
- **보완 필요**: 4건 · **살펴볼 사항**: 0건
- **증분 캐시**: 6 히트 / 0 미스 (글 6건)

## 빌드 진행

```
빌드 시작 - siheonlee.com v0.7.2 (2026-05-17 02:56:34)
[ 1/16] 설정 로드 (site.yaml / 토크나이저 패리티)
[ 2/16] 글 폴더 스캔 (Articles/)
[ 3/16] meta.yaml 파싱
[ 4/16] 검증 / 카테고리 트리 구축
[ 5/16] 자산 동기화 / 이미지 최적화 (WebP)
        6 글 자산 동기화 (이미지 2 변환).
[ 6/16] 사이트 공통 자산 복사
[ 7/16] 카테고리/홈 CSS 복사
[ 8/16] 글 렌더링
        6 글 처리 (캐시 6 hit / 0 miss).
[ 9/16] 카테고리 페이지
[10/16] 홈 페이지
[11/16] 404 페이지
[12/16] robots.txt
[13/16] sitemap.xml
[14/16] RSS / Atom 피드
[15/16] 검색 인덱스 (dist/search.php)
[16/16] 고아 산출물 정리

빌드 완료: 6 글, 2 카테고리, 4 보완 필요, 0 살펴볼 사항. (3.3s)
증분 캐시: 6 히트 / 0 미스 (글 6건).
산출물: dist/ (siheonlee.com).
```

## 보완이 필요한 항목 (산출물 일부 누락 가능)

### [article] about

- meta.yaml: 'seo.description' 필드가 없습니다 — 외부 노출용 한 줄 설명을 작성해주세요. (description / og:description / twitter:description / 피드 summary 가 모두 누락됩니다.)
  - 위치: `F:\lama.pe.kr to siheonlee.com\siheonlee.com_v0.7.2\Articles\About\meta.yaml`

### [category] blog

- meta.yaml: 'seo.description' 필드가 없습니다 — 외부 노출용 한 줄 설명을 작성해주세요. (description / og:description / twitter:description 메타 태그가 누락됩니다.)
  - 위치: `F:\lama.pe.kr to siheonlee.com\siheonlee.com_v0.7.2\Articles\Blog\meta.yaml`

### [category] blog/tutorials

- meta.yaml: 'seo.description' 필드가 없습니다 — 외부 노출용 한 줄 설명을 작성해주세요. (description / og:description / twitter:description 메타 태그가 누락됩니다.)
  - 위치: `F:\lama.pe.kr to siheonlee.com\siheonlee.com_v0.7.2\Articles\Blog\Tutorials\meta.yaml`

### [home]

- meta.yaml: 'seo.description' 필드가 없습니다 — 외부 노출용 한 줄 설명을 작성해주세요. (description / og:description / twitter:description 메타 태그가 누락됩니다.)
  - 위치: `F:\lama.pe.kr to siheonlee.com\siheonlee.com_v0.7.2\Articles\meta.yaml`

> **빌드 리포트 요약**: 보완 필요 4건, 살펴볼 사항 0건.

---

_이 문서는 매 빌드마다 자동 생성·갱신됩니다 (build.py 가 있는 폴더). dist/ 산출물에는 포함되지 않습니다._

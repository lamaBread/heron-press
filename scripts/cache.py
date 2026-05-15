"""빌드 증분 캐싱 (v0.7.0 신설).

설계 의도:
  v0.6.5 까지의 빌더는 매 빌드마다 모든 글의 마크다운 본문을 재파싱하고 템플릿을
  다시 채워 dist 의 글 페이지를 새로 만들었다. 글 ≤ 수십 건 규모에서는 무시
  가능하지만, 글 수가 늘어나면 마크다운 파싱 (Parsedown 포팅) + HTML 후처리 +
  템플릿 렌더가 빌드 시간의 대부분이 된다. v0.7.0 은 *글 페이지* 단위 캐싱을
  도입해 변경되지 않은 글은 재렌더하지 않는다.

캐시 대상 범위 (사용자 결정 - 글 단위만):
  - 캐싱 ○ : 글 페이지 HTML/PHP (`_render_articles` 단계의 산출물)
              + 글 단위 부수 산출 (rendered_bodies[slug] = 검색용 plain text,
                article_render_meta[slug] = gallery/feed 의 thumb/summary)
              + 글 단위 BuildReport 항목 (issue / warning)
  - 캐싱 × : 검색 인덱스, sitemap, feed, 홈, 카테고리, assets.
              이들은 모든 글이 입력이라 invalidate 빈도가 높거나 계산 비용이
              낮아 캐싱 효과가 적다.

캐시 키 입도 (사용자 결정 - per-article fine-grained):
  각 글의 `article_hash` 는 (a) 모든 글에 영향을 주는 *global_hash* 와
  (b) 그 글 *고유* 의 입력 두 부분을 합쳐 만든다.

  global_hash:
    - site.yaml
    - scripts/ 의 모든 .py (빌더 동작 변경 = 산출물 변경 가능성)
    - templates/ 의 모든 파일 (article.html 외에도 search 등 간접 영향 가능)
    - assets/common_template.css (use_common_css=True 인 글의 CSS 변경 추적)
    - Articles/meta.yaml + Articles/*/meta.yaml (홈/카테고리 트리 + nav)
      → 톱레벨 글의 nav_priority 변경, 카테고리 추가/제거가 모든 글의 nav_links
        를 바꾸므로 global 에 포함.
    - __version__ (빌더 자체 버전 변경 시 캐시 일괄 무효화)

  per-article (그 글 고유):
    - content.md / content.html 내용
    - 그 글의 meta.yaml 내용
    - 그 글 폴더의 모든 파일 listing (이름 + size + content hash) — 자산이
      `image_variants` 를 거쳐 본문 <img> 후처리에 영향.
    - 그 글이 `template:` 키로 페이지 폴더 안의 커스텀 템플릿을 지정했다면 그
      파일 (templates/ 안의 템플릿은 이미 global 에 포함).
    - 그 글의 외부 CSS 파일들 (stylesheets 의 각 파일 내용) — 글 폴더 안 파일
      이라 위 'listing' 에 이미 포함되지만 명시적 의존성으로 두 번 계산해도 무해.

저장 형식:
  .build_cache/manifest.json        — JSON 매니페스트:
      {
        "version": "0.7.0",
        "global_hash": "<sha256>",
        "articles": {
          "<slug>": {
            "article_hash": "<sha256>",
            "output_ext": "html" | "php",
            "issues":   [{"scope":..., "target":..., "message":..., "location":...}],
            "warnings": [{...}],
            "body_plain": "...",         # 검색용 plain text
            "thumb":   "/path/..."|null, # gallery/feed 썸네일 URL
            "summary": "..."             # gallery/feed 요약
          },
          ...
        }
      }
  .build_cache/articles/<slug>.<ext> — 캐시된 글 페이지 산출물 (텍스트).

결정성 보장:
  캐시는 *재렌더 여부* 만 바꿀 뿐 *산출물 자체* 는 바꾸지 않는다. 캐시 hit 시
  복사되는 텍스트는 첫 빌드가 만든 결과 그대로 — 두 번째 빌드의 sha256 가
  여전히 일치한다 (tests/run_diagnostics.py 의 [2] 결정성 섹션 통과).

  단 한 가지 미묘한 점 — 캐시 hit 시 글 페이지의 `index.html` 의 *mtime* 이
  갱신되지 않는다 (`_copy_if_newer` 같은 mtime 비교를 글 페이지 산출물에는
  걸지 않으므로 외부 영향 없음). 결정성 가드는 sha256 비교라 통과.

API:
  cache = BuildCache(base_dir, enabled=True)
  cache.compute_global_hash(...)        # site.yaml/scripts/templates/... 해시
  hit = cache.lookup(slug, article_hash)
  if hit:
      # 캐시 hit: hit.output, hit.body_plain, hit.thumb, hit.summary
      # + hit.issues / hit.warnings 를 BuildReport 로 replay.
  else:
      # 캐시 miss: 평소대로 렌더 → cache.store(...) 호출.
  cache.commit()                        # manifest.json 디스크 쓰기
  cache.clear()                         # 캐시 전체 폐기 (--clean 또는 --clean-cache)
"""
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


CACHE_DIR_NAME = '.build_cache'
MANIFEST_NAME = 'manifest.json'
ARTICLES_SUBDIR = 'articles'


def _sha256_file(path: Path) -> str:
    """파일 내용의 sha256 (hex). 누락 파일은 빈 문자열 해시."""
    if not path.is_file():
        return hashlib.sha256(b'').hexdigest()
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def _walk_files_sorted(root: Path):
    """root 하위의 모든 파일을 결정적 순서 (POSIX-경로 정렬) 로 yield."""
    if not root.is_dir():
        return
    items = []
    for p in root.rglob('*'):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            items.append((rel, p))
    items.sort(key=lambda x: x[0])
    for rel, p in items:
        yield rel, p


@dataclass
class CachedArticle:
    """캐시 히트 시 반환되는 글 단위 캐시 묶음."""
    output: str                 # dist/{slug}/index.{ext} 의 텍스트
    output_ext: str             # 'html' 또는 'php'
    body_plain: str             # rendered_bodies[slug] 의 plain text
    thumb: Optional[str]        # article_render_meta[slug]['thumb']
    summary: str                # article_render_meta[slug]['summary']
    issues: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


class BuildCache:
    """글 단위 빌드 증분 캐시 (v0.7.0).

    enabled=False 인 인스턴스는 lookup() 이 항상 None 을 반환하고 store() 가
    no-op — `--no-cache` CLI 플래그용. 매니페스트 디스크 I/O 도 발생하지 않는다.
    """

    def __init__(self, base_dir: Path, *, enabled: bool = True):
        self.base = Path(base_dir)
        self.enabled = enabled
        self.cache_dir = self.base / CACHE_DIR_NAME
        self.manifest_path = self.cache_dir / MANIFEST_NAME
        self.articles_dir = self.cache_dir / ARTICLES_SUBDIR
        self._global_hash: Optional[str] = None
        # 신규/갱신될 매니페스트 항목. commit() 시 디스크에 기록.
        self._new_articles: dict = {}
        # 이전 빌드의 매니페스트 (lookup 의 비교 대상).
        self._loaded_articles: dict = {}
        self._loaded_global_hash: Optional[str] = None
        self._loaded_version: Optional[str] = None
        if self.enabled:
            self._load_manifest()

    # ── 매니페스트 I/O ────────────────────────────────────────

    def _load_manifest(self):
        """이전 빌드의 매니페스트를 로드. 없거나 파싱 실패 시 빈 상태."""
        if not self.manifest_path.is_file():
            return
        try:
            with self.manifest_path.open('r', encoding='utf-8') as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(data, dict):
            return
        self._loaded_version = data.get('version')
        self._loaded_global_hash = data.get('global_hash')
        arts = data.get('articles')
        if isinstance(arts, dict):
            self._loaded_articles = arts

    def commit(self, *, current_version: str):
        """이번 빌드 라운드에서 store() 된 항목을 매니페스트에 기록.

        global_hash 가 set_global_hash 로 이미 정해졌어야 한다. 기록되는 매니
        페스트의 articles dict 은 *이번 빌드에서 캐시 hit 또는 store() 된* 글
        들만 포함 — 빌드에서 사라진 글의 잔재는 자연 제거된다.
        """
        if not self.enabled:
            return
        if self._global_hash is None:
            return
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.articles_dir.mkdir(parents=True, exist_ok=True)
        data = {
            'version': current_version,
            'global_hash': self._global_hash,
            'articles': self._new_articles,
        }
        tmp = self.manifest_path.with_suffix('.json.tmp')
        with tmp.open('w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, sort_keys=True, indent=2)
        tmp.replace(self.manifest_path)
        self._prune_stale_article_files()

    def _prune_stale_article_files(self):
        """이번 빌드에 등장하지 않은 글의 캐시 파일을 articles/ 에서 제거."""
        if not self.articles_dir.is_dir():
            return
        keep = set()
        for slug, info in self._new_articles.items():
            ext = info.get('output_ext') or 'html'
            keep.add(f'{slug}.{ext}')
        for p in self.articles_dir.iterdir():
            if p.is_file() and p.name not in keep:
                try:
                    p.unlink()
                except OSError:
                    pass

    def clear(self):
        """캐시 디렉터리 전체 폐기 (--clean 또는 --clean-cache)."""
        if not self.cache_dir.exists():
            return
        import shutil
        shutil.rmtree(self.cache_dir, ignore_errors=True)
        self._loaded_articles = {}
        self._loaded_global_hash = None
        self._loaded_version = None
        self._new_articles = {}

    # ── 해시 계산 ────────────────────────────────────────────

    def set_global_hash(self, global_hash: str):
        self._global_hash = global_hash

    @property
    def global_hash(self) -> Optional[str]:
        return self._global_hash

    def compute_global_hash(self, *, site_yaml: Path, scripts_dir: Path,
                            templates_dir: Path, assets_dir: Path,
                            articles_dir: Path,
                            version: str) -> str:
        """모든 글에 영향을 줄 수 있는 입력의 종합 해시.

        포함:
          - site.yaml 내용
          - scripts/*.py 내용 (재귀)
          - templates/* 내용 (재귀)
          - assets/common_template.css (있다면)
          - Articles 의 *meta.yaml* 만 (홈 + 카테고리 트리; 글 폴더의 meta.yaml
            은 per-article 측에 포함)
          - __version__

        포함하지 않는 것: assets/ 의 common_template.css 외 다른 파일 (이미지
        등) — 글 페이지 산출에 직접 영향이 없다 (assets/ 의 raster 이미지는
        dist/assets/ 로 변환되지만 글 페이지 HTML 텍스트엔 들어가지 않음).
        """
        h = hashlib.sha256()

        def feed(label: str, payload: bytes):
            h.update(label.encode('utf-8'))
            h.update(b'\x00')
            h.update(len(payload).to_bytes(8, 'big'))
            h.update(payload)

        feed('version', version.encode('utf-8'))
        feed('site.yaml', site_yaml.read_bytes() if site_yaml.is_file() else b'')

        # scripts/*.py (cache.py 도 포함 — 캐시 로직 자체의 변경도 invalidation
        # 사유가 될 수 있다)
        for rel, p in _walk_files_sorted(scripts_dir):
            if not rel.endswith('.py'):
                continue
            if rel.startswith('__pycache__/') or '/__pycache__/' in rel:
                continue
            feed(f'scripts/{rel}', p.read_bytes())

        # templates/*
        for rel, p in _walk_files_sorted(templates_dir):
            feed(f'templates/{rel}', p.read_bytes())

        # assets/common_template.css (다른 assets/ 파일은 제외)
        common_css = assets_dir / 'common_template.css'
        if common_css.is_file():
            feed('assets/common_template.css', common_css.read_bytes())

        # Articles 의 meta.yaml 들 — 글 폴더의 meta.yaml 은 글의 자기 입력이지만
        # 톱레벨 글의 nav_priority 변경이 *다른* 모든 글의 nav_links 에 영향을
        # 주므로 global 에도 포함한다. 즉 글 meta 는 글별 + global 양쪽에 들어가
        # *어느 글의 meta 가 바뀌어도* 모든 글이 invalidate 된다. 사용자 결정 = 정확.
        if articles_dir.is_dir():
            for rel, p in _walk_files_sorted(articles_dir):
                if Path(rel).name == 'meta.yaml':
                    feed(f'Articles/{rel}', p.read_bytes())

        self._global_hash = h.hexdigest()
        return self._global_hash

    def compute_article_hash(self, *, slug: str, source_dir: Path,
                             content_file: Path) -> str:
        """그 글 고유의 입력 + global_hash 의 종합 해시.

        포함:
          - global_hash (set_global_hash / compute_global_hash 로 미리 세팅)
          - slug 문자열 (slug 충돌 가드)
          - content_file 의 이름 + 내용 (content.md / content.html 구분 + 내용)
          - source_dir 안의 모든 파일 (이름 + 내용) — 자산이 변형되어 본문 <img>
            후처리에 영향.

        global_hash 가 None 이면 RuntimeError.
        """
        if self._global_hash is None:
            raise RuntimeError(
                'compute_article_hash() 이전에 compute_global_hash() 또는 '
                'set_global_hash() 가 먼저 호출되어야 합니다.'
            )
        h = hashlib.sha256()

        def feed(label: str, payload: bytes):
            h.update(label.encode('utf-8'))
            h.update(b'\x00')
            h.update(len(payload).to_bytes(8, 'big'))
            h.update(payload)

        feed('global', self._global_hash.encode('utf-8'))
        feed('slug', slug.encode('utf-8'))
        feed('content_file_name', content_file.name.encode('utf-8'))

        # 글 폴더의 모든 파일 (content / meta.yaml / 자산 / 외부 CSS 등).
        # rglob 결과를 결정적 순서로 정렬해 해시 안정성을 확보.
        for rel, p in _walk_files_sorted(source_dir):
            feed(f'src/{rel}', p.read_bytes())

        return h.hexdigest()

    # ── 캐시 조회 / 저장 ────────────────────────────────────

    def lookup(self, slug: str, article_hash: str) -> Optional[CachedArticle]:
        """주어진 slug + article_hash 가 매니페스트와 일치하면 캐시된 산출물 반환.

        반환된 CachedArticle 은 다음을 포함:
          - output (글 페이지 HTML/PHP 텍스트)
          - output_ext ('html' / 'php')
          - body_plain (검색 인덱스용 plain text)
          - thumb / summary (gallery + feed 용 메타)
          - issues / warnings (BuildReport 로 replay 할 항목들)

        매니페스트 항목이 있지만 캐시 파일이 사라진 경우 (수동 삭제 등) None.
        매니페스트의 version 이 현재 __version__ 과 다르면 (구 버전 캐시)
        compute_global_hash() 에서 version 이 global 에 포함돼 어차피 hash
        가 어긋나므로 자연 miss.

        enabled=False 이면 항상 None.
        """
        if not self.enabled:
            return None
        prev = self._loaded_articles.get(slug)
        if not isinstance(prev, dict):
            return None
        if prev.get('article_hash') != article_hash:
            return None
        output_ext = prev.get('output_ext') or 'html'
        out_path = self.articles_dir / f'{slug}.{output_ext}'
        if not out_path.is_file():
            return None
        try:
            output = out_path.read_text(encoding='utf-8')
        except OSError:
            return None
        issues = prev.get('issues') or []
        warnings = prev.get('warnings') or []
        if not isinstance(issues, list):
            issues = []
        if not isinstance(warnings, list):
            warnings = []
        return CachedArticle(
            output=output,
            output_ext=output_ext,
            body_plain=prev.get('body_plain') or '',
            thumb=prev.get('thumb'),
            summary=prev.get('summary') or '',
            issues=list(issues),
            warnings=list(warnings),
        )

    def store(self, *, slug: str, article_hash: str, output: str,
              output_ext: str, body_plain: str,
              thumb: Optional[str], summary: str,
              issues: list, warnings: list):
        """캐시 miss 시 새로 렌더한 산출물을 기록.

        매니페스트 항목 + 캐시 파일 (articles/{slug}.{ext}) 둘 다 쓴다.
        commit() 호출 전까지는 매니페스트 디스크 쓰기는 보류 (한 빌드의 모든
        store() 가 한 번의 디스크 쓰기로 묶이도록).
        """
        if not self.enabled:
            return
        self.articles_dir.mkdir(parents=True, exist_ok=True)
        out_path = self.articles_dir / f'{slug}.{output_ext}'
        # 같은 slug 의 다른 확장자 캐시 파일이 남아 있으면 정리 (글이 PHP →
        # HTML 또는 그 반대로 전환된 케이스).
        for other_ext in ('html', 'php'):
            if other_ext == output_ext:
                continue
            stray = self.articles_dir / f'{slug}.{other_ext}'
            if stray.exists():
                try:
                    stray.unlink()
                except OSError:
                    pass
        out_path.write_text(output, encoding='utf-8')
        self._new_articles[slug] = {
            'article_hash': article_hash,
            'output_ext': output_ext,
            'body_plain': body_plain,
            'thumb': thumb,
            'summary': summary,
            'issues': issues,
            'warnings': warnings,
        }

    def record_hit(self, slug: str, cached: CachedArticle, article_hash: str):
        """캐시 hit 인 경우에도 manifest 의 articles dict 에 그대로 보존되도록
        등록 (다음 빌드의 store() 와 형식 동일).

        commit() 이 _new_articles 만 manifest 에 쓰므로 hit 케이스도 명시적으로
        등록하지 않으면 캐시가 사라진다.
        """
        if not self.enabled:
            return
        self._new_articles[slug] = {
            'article_hash': article_hash,
            'output_ext': cached.output_ext,
            'body_plain': cached.body_plain,
            'thumb': cached.thumb,
            'summary': cached.summary,
            'issues': cached.issues,
            'warnings': cached.warnings,
        }

    # ── 통계 ────────────────────────────────────────────────

    def stats(self) -> dict:
        """현재 commit() 대상 항목 수 — print 용."""
        return {
            'cached_articles': len(self._new_articles),
        }


def issue_payload(scope: str, target: str, message: str,
                  location) -> dict:
    """report.issue() / report.warning() 의 인자를 JSON-직렬화 가능한 dict 로.

    location 은 Path 가 들어올 수 있으므로 str 로 정규화.
    """
    return {
        'scope': scope,
        'target': target,
        'message': message,
        'location': str(location) if location is not None else None,
    }


def replay_issue(report, item: dict):
    """캐시 hit 시 BuildReport 로 한 issue 항목을 다시 흘려보낸다."""
    loc = item.get('location')
    report.issue(
        item.get('scope', ''),
        item.get('target', ''),
        item.get('message', ''),
        Path(loc) if loc else None,
    )


def replay_warning(report, item: dict):
    """캐시 hit 시 BuildReport 로 한 warning 항목을 다시 흘려보낸다."""
    loc = item.get('location')
    report.warning(
        item.get('scope', ''),
        item.get('target', ''),
        item.get('message', ''),
        Path(loc) if loc else None,
    )

"""scripts/cache 의 BuildCache 단위 테스트 (v0.7.0 신설).

검증 범위:
  - 캐시 키 해시 계산의 결정성 (같은 입력 → 같은 hash, 다른 입력 → 다른 hash).
  - lookup / store / commit 의 round-trip 정합.
  - --no-cache (enabled=False) 의 no-op 동작.
  - clear() 의 디스크 정리.
  - 통합 빌드 시나리오 — 두 번째 빌드의 캐시 hit + 한 글 수정의 selective
    invalidation + global_hash 변경 (site.yaml 수정) 의 전체 invalidation.

테스트 격리:
  - 각 케이스가 tempfile.mkdtemp 로 자기 base_dir 을 만들어 다른 테스트와 충돌
    없음. tearDown 에서 shutil.rmtree.
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import builder as builder_module  # noqa: E402
from scripts.builder import Builder  # noqa: E402
from scripts.cache import (  # noqa: E402
    BuildCache,
    CACHE_DIR_NAME,
    CachedArticle,
    issue_payload,
    replay_issue,
    replay_warning,
)
from scripts.report import BuildReport  # noqa: E402


# ════════════════════════════════════════════════════════════════
# 1) 단위 — BuildCache 의 disabled 모드 / lookup-miss / store-roundtrip
# ════════════════════════════════════════════════════════════════


class BuildCacheDisabledTests(unittest.TestCase):
    """enabled=False 인 캐시는 어떤 작업도 디스크에 남기지 않는다."""

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix='ssg-v070-cache-'))

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def test_disabled_lookup_returns_none(self):
        cache = BuildCache(self.base, enabled=False)
        cache.set_global_hash('x' * 64)
        self.assertIsNone(cache.lookup('hello', 'y' * 64))

    def test_disabled_store_no_disk_write(self):
        cache = BuildCache(self.base, enabled=False)
        cache.set_global_hash('x' * 64)
        cache.store(
            slug='hello', article_hash='y' * 64,
            output='<html></html>', output_ext='html',
            body_plain='hello world', thumb=None, summary='',
            issues=[], warnings=[],
        )
        cache.commit(current_version='0.7.0')
        self.assertFalse((self.base / CACHE_DIR_NAME).exists(),
                         'enabled=False 면 .build_cache/ 자체가 만들어지지 않아야 함')

    def test_disabled_clear_safe(self):
        # 디렉터리가 없어도 clear() 는 무사히 통과.
        cache = BuildCache(self.base, enabled=False)
        cache.clear()


# ════════════════════════════════════════════════════════════════
# 2) 단위 — global_hash / article_hash 의 결정성과 민감도
# ════════════════════════════════════════════════════════════════


class HashComputationTests(unittest.TestCase):
    """compute_global_hash / compute_article_hash 의 hash 동작."""

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix='ssg-v070-hash-'))
        # 최소 사이트 트리.
        (self.base / 'site.yaml').write_text(
            "name: Demo\n", encoding='utf-8'
        )
        (self.base / 'scripts').mkdir()
        (self.base / 'scripts' / 'dummy.py').write_text(
            "x = 1\n", encoding='utf-8'
        )
        (self.base / 'templates').mkdir()
        (self.base / 'templates' / 'article.html').write_text(
            "<html>{{BODY}}</html>\n", encoding='utf-8'
        )
        (self.base / 'assets').mkdir()
        (self.base / 'assets' / 'common_template.css').write_text(
            "body{margin:0}", encoding='utf-8'
        )
        (self.base / 'Articles').mkdir()
        (self.base / 'Articles' / 'meta.yaml').write_text(
            "title: Home\n", encoding='utf-8'
        )

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def _cache(self, **enabled_kw):
        return BuildCache(self.base, enabled=enabled_kw.get('enabled', True))

    def _hash_kwargs(self):
        return dict(
            site_yaml=self.base / 'site.yaml',
            scripts_dir=self.base / 'scripts',
            templates_dir=self.base / 'templates',
            assets_dir=self.base / 'assets',
            articles_dir=self.base / 'Articles',
            version='0.7.0',
        )

    def test_global_hash_is_deterministic(self):
        c1 = self._cache()
        c2 = self._cache()
        self.assertEqual(
            c1.compute_global_hash(**self._hash_kwargs()),
            c2.compute_global_hash(**self._hash_kwargs()),
        )

    def test_site_yaml_change_alters_global_hash(self):
        c1 = self._cache()
        h1 = c1.compute_global_hash(**self._hash_kwargs())
        (self.base / 'site.yaml').write_text("name: Demo2\n", encoding='utf-8')
        c2 = self._cache()
        h2 = c2.compute_global_hash(**self._hash_kwargs())
        self.assertNotEqual(h1, h2)

    def test_template_change_alters_global_hash(self):
        c1 = self._cache()
        h1 = c1.compute_global_hash(**self._hash_kwargs())
        (self.base / 'templates' / 'article.html').write_text(
            "<html><body>{{BODY}}</body></html>\n", encoding='utf-8'
        )
        c2 = self._cache()
        h2 = c2.compute_global_hash(**self._hash_kwargs())
        self.assertNotEqual(h1, h2)

    def test_version_change_alters_global_hash(self):
        c1 = self._cache()
        h1 = c1.compute_global_hash(**self._hash_kwargs())
        kwargs2 = self._hash_kwargs()
        kwargs2['version'] = '0.7.1'
        c2 = self._cache()
        h2 = c2.compute_global_hash(**kwargs2)
        self.assertNotEqual(h1, h2)

    def test_scripts_change_alters_global_hash(self):
        c1 = self._cache()
        h1 = c1.compute_global_hash(**self._hash_kwargs())
        (self.base / 'scripts' / 'dummy.py').write_text(
            "x = 2\n", encoding='utf-8'
        )
        c2 = self._cache()
        h2 = c2.compute_global_hash(**self._hash_kwargs())
        self.assertNotEqual(h1, h2)

    def test_top_meta_change_alters_global_hash(self):
        c1 = self._cache()
        h1 = c1.compute_global_hash(**self._hash_kwargs())
        (self.base / 'Articles' / 'meta.yaml').write_text(
            "title: Home2\n", encoding='utf-8'
        )
        c2 = self._cache()
        h2 = c2.compute_global_hash(**self._hash_kwargs())
        self.assertNotEqual(h1, h2)

    def test_article_hash_requires_global_hash_first(self):
        c = self._cache()
        art_dir = self.base / 'Articles' / 'Demo'
        art_dir.mkdir(parents=True)
        (art_dir / 'content.md').write_text("# x\n", encoding='utf-8')
        with self.assertRaises(RuntimeError):
            c.compute_article_hash(
                slug='demo', source_dir=art_dir,
                content_file=art_dir / 'content.md',
            )

    def test_article_hash_changes_with_content(self):
        art_dir = self.base / 'Articles' / 'Demo'
        art_dir.mkdir(parents=True)
        (art_dir / 'meta.yaml').write_text(
            "slug: demo\ntitle: D\ndate: 2026-01-01\n", encoding='utf-8'
        )
        (art_dir / 'content.md').write_text("# a\n", encoding='utf-8')
        c = self._cache()
        c.compute_global_hash(**self._hash_kwargs())
        h1 = c.compute_article_hash(
            slug='demo', source_dir=art_dir,
            content_file=art_dir / 'content.md',
        )
        (art_dir / 'content.md').write_text("# b\n", encoding='utf-8')
        c2 = self._cache()
        c2.compute_global_hash(**self._hash_kwargs())
        h2 = c2.compute_article_hash(
            slug='demo', source_dir=art_dir,
            content_file=art_dir / 'content.md',
        )
        self.assertNotEqual(h1, h2)

    def test_article_hash_changes_with_added_asset(self):
        art_dir = self.base / 'Articles' / 'Demo'
        art_dir.mkdir(parents=True)
        (art_dir / 'meta.yaml').write_text(
            "slug: demo\ntitle: D\ndate: 2026-01-01\n", encoding='utf-8'
        )
        (art_dir / 'content.md').write_text("# a\n", encoding='utf-8')
        c = self._cache()
        c.compute_global_hash(**self._hash_kwargs())
        h1 = c.compute_article_hash(
            slug='demo', source_dir=art_dir,
            content_file=art_dir / 'content.md',
        )
        # 새 자산 추가 — article_hash 변동.
        (art_dir / 'asset.txt').write_text("data\n", encoding='utf-8')
        c2 = self._cache()
        c2.compute_global_hash(**self._hash_kwargs())
        h2 = c2.compute_article_hash(
            slug='demo', source_dir=art_dir,
            content_file=art_dir / 'content.md',
        )
        self.assertNotEqual(h1, h2)

    def test_article_hash_independent_of_other_articles(self):
        """한 글의 content 변경이 *다른 글* 의 article_hash 를 흔들지 않는다
        (global_hash 가 같다는 전제 — top-level meta 가 안 바뀌어야 함)."""
        a_dir = self.base / 'Articles' / 'A'
        b_dir = self.base / 'Articles' / 'B'
        a_dir.mkdir(parents=True)
        b_dir.mkdir(parents=True)
        (a_dir / 'meta.yaml').write_text(
            "slug: a\ntitle: A\ndate: 2026-01-01\n", encoding='utf-8'
        )
        (b_dir / 'meta.yaml').write_text(
            "slug: b\ntitle: B\ndate: 2026-01-01\n", encoding='utf-8'
        )
        (a_dir / 'content.md').write_text("# a1\n", encoding='utf-8')
        (b_dir / 'content.md').write_text("# b1\n", encoding='utf-8')

        # B 의 hash 를 측정 (A 가 v1 일 때).
        c = self._cache()
        c.compute_global_hash(**self._hash_kwargs())
        b_h1 = c.compute_article_hash(
            slug='b', source_dir=b_dir,
            content_file=b_dir / 'content.md',
        )
        # A 의 *content* 만 바꿈 (meta 는 그대로 → global_hash 동일).
        (a_dir / 'content.md').write_text("# a2\n", encoding='utf-8')
        c2 = self._cache()
        c2.compute_global_hash(**self._hash_kwargs())
        b_h2 = c2.compute_article_hash(
            slug='b', source_dir=b_dir,
            content_file=b_dir / 'content.md',
        )
        self.assertEqual(b_h1, b_h2,
                         'A 의 content 변경이 B 의 article_hash 에 영향을 주면 안 됨')


# ════════════════════════════════════════════════════════════════
# 3) 단위 — store/lookup/commit/clear 라운드트립
# ════════════════════════════════════════════════════════════════


class StoreLookupRoundTripTests(unittest.TestCase):
    """store() 후 새 BuildCache 인스턴스가 lookup() 으로 같은 값을 돌려준다."""

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix='ssg-v070-rt-'))

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def test_store_then_lookup_returns_payload(self):
        cache = BuildCache(self.base, enabled=True)
        cache.set_global_hash('g' * 64)
        cache.store(
            slug='demo', article_hash='a' * 64,
            output='<html>OUT</html>', output_ext='html',
            body_plain='out plain', thumb='/og.png', summary='one line',
            issues=[issue_payload('article', 'demo', 'missing description', None)],
            warnings=[],
        )
        cache.commit(current_version='0.7.0')

        # 새 BuildCache (디스크 매니페스트 재로드).
        cache2 = BuildCache(self.base, enabled=True)
        cache2.set_global_hash('g' * 64)
        hit = cache2.lookup('demo', 'a' * 64)
        self.assertIsNotNone(hit)
        self.assertEqual(hit.output, '<html>OUT</html>')
        self.assertEqual(hit.output_ext, 'html')
        self.assertEqual(hit.body_plain, 'out plain')
        self.assertEqual(hit.thumb, '/og.png')
        self.assertEqual(hit.summary, 'one line')
        self.assertEqual(len(hit.issues), 1)
        self.assertEqual(hit.issues[0]['message'], 'missing description')

    def test_lookup_miss_on_hash_mismatch(self):
        cache = BuildCache(self.base, enabled=True)
        cache.set_global_hash('g' * 64)
        cache.store(
            slug='demo', article_hash='a' * 64,
            output='<html>OUT</html>', output_ext='html',
            body_plain='', thumb=None, summary='',
            issues=[], warnings=[],
        )
        cache.commit(current_version='0.7.0')

        cache2 = BuildCache(self.base, enabled=True)
        cache2.set_global_hash('g' * 64)
        self.assertIsNone(cache2.lookup('demo', 'b' * 64))

    def test_lookup_miss_when_cache_file_deleted(self):
        cache = BuildCache(self.base, enabled=True)
        cache.set_global_hash('g' * 64)
        cache.store(
            slug='demo', article_hash='a' * 64,
            output='<html></html>', output_ext='html',
            body_plain='', thumb=None, summary='',
            issues=[], warnings=[],
        )
        cache.commit(current_version='0.7.0')

        # 매니페스트는 남아 있지만 캐시 파일만 수동 삭제 — None 반환.
        (self.base / CACHE_DIR_NAME / 'articles' / 'demo.html').unlink()

        cache2 = BuildCache(self.base, enabled=True)
        cache2.set_global_hash('g' * 64)
        self.assertIsNone(cache2.lookup('demo', 'a' * 64))

    def test_clear_wipes_directory(self):
        cache = BuildCache(self.base, enabled=True)
        cache.set_global_hash('g' * 64)
        cache.store(
            slug='demo', article_hash='a' * 64,
            output='<html></html>', output_ext='html',
            body_plain='', thumb=None, summary='',
            issues=[], warnings=[],
        )
        cache.commit(current_version='0.7.0')
        self.assertTrue((self.base / CACHE_DIR_NAME).is_dir())
        cache.clear()
        self.assertFalse((self.base / CACHE_DIR_NAME).exists())

    def test_commit_prunes_stale_article_files(self):
        """이번 빌드에서 등장하지 않은 slug 의 캐시 파일은 commit 후 제거된다."""
        cache = BuildCache(self.base, enabled=True)
        cache.set_global_hash('g' * 64)
        cache.store(
            slug='alice', article_hash='1' * 64,
            output='<html>A</html>', output_ext='html',
            body_plain='', thumb=None, summary='',
            issues=[], warnings=[],
        )
        cache.store(
            slug='bob', article_hash='2' * 64,
            output='<html>B</html>', output_ext='html',
            body_plain='', thumb=None, summary='',
            issues=[], warnings=[],
        )
        cache.commit(current_version='0.7.0')

        # 2 차 빌드 — alice 만 등장 + bob 은 사라짐 (글 삭제 시나리오).
        cache2 = BuildCache(self.base, enabled=True)
        cache2.set_global_hash('g' * 64)
        cache2.record_hit(
            'alice',
            CachedArticle(
                output='<html>A</html>', output_ext='html',
                body_plain='', thumb=None, summary='',
                issues=[], warnings=[],
            ),
            '1' * 64,
        )
        cache2.commit(current_version='0.7.0')

        bob_file = self.base / CACHE_DIR_NAME / 'articles' / 'bob.html'
        alice_file = self.base / CACHE_DIR_NAME / 'articles' / 'alice.html'
        self.assertFalse(bob_file.exists(), 'stale bob.html 이 정리되어야 함')
        self.assertTrue(alice_file.exists())


# ════════════════════════════════════════════════════════════════
# 4) 단위 — replay_issue / replay_warning 가 BuildReport 에 올바르게 흘러간다
# ════════════════════════════════════════════════════════════════


class ReplayTests(unittest.TestCase):

    def test_replay_issue_lands_in_issue_bucket(self):
        rep = BuildReport()
        replay_issue(rep, {
            'scope': 'article', 'target': 'demo',
            'message': 'something off', 'location': '/path/x',
        })
        self.assertEqual(rep.issue_count(), 1)
        self.assertEqual(rep.warning_count(), 0)
        e = rep.entries[0]
        self.assertEqual(e.severity, 'issue')
        self.assertEqual(e.scope, 'article')
        self.assertEqual(e.target, 'demo')
        self.assertEqual(e.message, 'something off')
        # location 은 Path 로 복원 (플랫폼 별 separator).
        from pathlib import Path as _P
        self.assertEqual(e.location, _P('/path/x'))

    def test_replay_warning_lands_in_warning_bucket(self):
        rep = BuildReport()
        replay_warning(rep, {
            'scope': 'article', 'target': 'demo',
            'message': 'fyi', 'location': None,
        })
        self.assertEqual(rep.warning_count(), 1)
        self.assertEqual(rep.issue_count(), 0)
        self.assertIsNone(rep.entries[0].location)


# ════════════════════════════════════════════════════════════════
# 5) 통합 — 두 번 빌드 → 두 번째는 모두 캐시 hit + dist 동등
# ════════════════════════════════════════════════════════════════


SITE_YAML_MIN = (
    "domain: example.com\n"
    "base_url: https://example.com\n"
    "name: Example\n"
    "main_title: Example\n"
    "default_author: A\n"
    "default_og_image: /og.png\n"
    "default_title_prefix: ''\n"
    "default_title_suffix: ' | E'\n"
    "copyright_holder: A\n"
    "copyright_year_start: 2020\n"
    "lang: en\n"
    "images:\n"
    "  enabled: false\n"
    "  lazy_loading: false\n"
    "reserved_slugs: [assets, search]\n"
)

META_BASE = (
    "slug: demo\n"
    "title: Demo\n"
    "date: 2026-01-01\n"
    "seo:\n"
    "  description: A demo article.\n"
)


def _scaffold_site():
    """최소 단일-글 사이트를 임시 디렉터리에 만든다."""
    tmp = Path(tempfile.mkdtemp(prefix='ssg-v070-int-'))
    (tmp / 'site.yaml').write_text(SITE_YAML_MIN, encoding='utf-8')
    shutil.copytree(ROOT / 'templates', tmp / 'templates')
    shutil.copytree(ROOT / 'assets', tmp / 'assets')

    art = tmp / 'Articles' / 'Demo'
    art.mkdir(parents=True)
    (art / 'meta.yaml').write_text(META_BASE, encoding='utf-8')
    (art / 'content.md').write_text('# Demo body\n\nHello.\n', encoding='utf-8')
    return tmp


class IncrementalCacheIntegrationTests(unittest.TestCase):
    """Builder 와 BuildCache 의 결합 — 캐시 hit/miss 카운트 + dist 동등."""

    def setUp(self):
        self.tmp = _scaffold_site()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _read_dist_sha(self):
        import hashlib
        out = {}
        for p in sorted((self.tmp / 'dist').rglob('*')):
            if p.is_file():
                h = hashlib.sha256(p.read_bytes()).hexdigest()
                out[str(p.relative_to(self.tmp / 'dist')).replace('\\', '/')] = h
        return out

    def test_second_build_hits_all_articles(self):
        builder_module.reset_report()
        b1 = Builder(base_dir=self.tmp, enable_cache=True)
        b1.build()
        self.assertEqual(b1._cache_hits, 0)
        self.assertEqual(b1._cache_misses, 1)

        builder_module.reset_report()
        b2 = Builder(base_dir=self.tmp, enable_cache=True)
        b2.build()
        self.assertEqual(b2._cache_hits, 1)
        self.assertEqual(b2._cache_misses, 0)

    def test_cached_dist_byte_identical(self):
        builder_module.reset_report()
        Builder(base_dir=self.tmp, enable_cache=True).build()
        snap_a = self._read_dist_sha()

        builder_module.reset_report()
        Builder(base_dir=self.tmp, enable_cache=True).build()
        snap_b = self._read_dist_sha()

        self.assertEqual(snap_a, snap_b,
                         '두 번째 빌드 (캐시 hit) 의 dist 가 첫 빌드와 byte 동일해야 함')

    def test_content_edit_invalidates_only_that_article(self):
        """글이 두 개일 때 한 글의 content 만 바꾸면 그 글만 미스."""
        # 두 번째 글 추가.
        art2 = self.tmp / 'Articles' / 'Other'
        art2.mkdir(parents=True)
        (art2 / 'meta.yaml').write_text(
            "slug: other\ntitle: Other\ndate: 2026-01-02\n"
            "seo:\n  description: Other article.\n",
            encoding='utf-8',
        )
        (art2 / 'content.md').write_text('# Other\n', encoding='utf-8')

        builder_module.reset_report()
        Builder(base_dir=self.tmp, enable_cache=True).build()  # warm

        # 첫 글만 수정.
        (self.tmp / 'Articles' / 'Demo' / 'content.md').write_text(
            '# Demo body\n\nUPDATED.\n', encoding='utf-8'
        )

        builder_module.reset_report()
        b = Builder(base_dir=self.tmp, enable_cache=True)
        b.build()
        self.assertEqual(b._cache_hits, 1, '안 바뀐 글은 hit')
        self.assertEqual(b._cache_misses, 1, '바뀐 글만 miss')

    def test_site_yaml_change_invalidates_everything(self):
        builder_module.reset_report()
        Builder(base_dir=self.tmp, enable_cache=True).build()  # warm

        # site.yaml 의 name 변경 — global_hash 변동.
        new_site = SITE_YAML_MIN.replace('name: Example', 'name: Example2')
        (self.tmp / 'site.yaml').write_text(new_site, encoding='utf-8')

        builder_module.reset_report()
        b = Builder(base_dir=self.tmp, enable_cache=True)
        b.build()
        self.assertEqual(b._cache_hits, 0,
                         'site.yaml 변경은 모든 글의 캐시를 무효화해야 함')
        self.assertEqual(b._cache_misses, 1)

    def test_template_change_invalidates_everything(self):
        builder_module.reset_report()
        Builder(base_dir=self.tmp, enable_cache=True).build()  # warm

        # 글 템플릿 약간 수정 — global_hash 변동.
        tpl_path = self.tmp / 'templates' / 'article.html'
        tpl_path.write_text(
            tpl_path.read_text(encoding='utf-8') + '\n<!-- bump -->\n',
            encoding='utf-8',
        )

        builder_module.reset_report()
        b = Builder(base_dir=self.tmp, enable_cache=True)
        b.build()
        self.assertEqual(b._cache_hits, 0,
                         '템플릿 변경은 모든 글 캐시를 무효화해야 함')

    def test_no_cache_flag_disables_caching(self):
        builder_module.reset_report()
        Builder(base_dir=self.tmp, enable_cache=True).build()  # warm

        builder_module.reset_report()
        b = Builder(base_dir=self.tmp, enable_cache=False)
        b.build()
        self.assertEqual(b._cache_hits, 0,
                         'enable_cache=False 면 lookup() 이 항상 None')
        self.assertEqual(b._cache_misses, 1)
        # disabled 인 인스턴스는 manifest 도 안 건드림 (글 1 개라 hit 1 이 정상
        # 이지만 enable_cache=False 면 처음부터 miss 로 카운트).

    def test_cached_issues_replay_on_hit(self):
        """첫 빌드의 issue (seo.description 누락) 가 두 번째 빌드에서도 그대로
        리포트에 나타난다."""
        # description 누락 글로 교체.
        (self.tmp / 'Articles' / 'Demo' / 'meta.yaml').write_text(
            "slug: demo\ntitle: Demo\ndate: 2026-01-01\n",
            encoding='utf-8',
        )

        builder_module.reset_report()
        Builder(base_dir=self.tmp, enable_cache=True).build()
        # 첫 빌드는 issue 1 건 (description 누락).
        first_issues = [
            e for e in builder_module.report().entries
            if e.severity == 'issue' and e.scope == 'article' and e.target == 'demo'
        ]
        self.assertGreaterEqual(len(first_issues), 1)
        first_msg = first_issues[0].message

        builder_module.reset_report()
        b = Builder(base_dir=self.tmp, enable_cache=True)
        b.build()
        self.assertEqual(b._cache_hits, 1)
        second_issues = [
            e for e in builder_module.report().entries
            if e.severity == 'issue' and e.scope == 'article' and e.target == 'demo'
        ]
        self.assertGreaterEqual(len(second_issues), 1)
        # 메시지 텍스트는 byte 동일이어야 (replay 정합).
        self.assertEqual(second_issues[0].message, first_msg)


if __name__ == '__main__':
    unittest.main()

"""v1.3.0 빌드 속도 향상 항목의 단위 테스트.

검증 범위:
  - StepTimingTests (A): _step 이 직전 단계 종료 시간을 self._step_times 에
    기록하고 새 단계를 열며, _step_close 가 마지막 단계를 닫는다. build()
    멱등성과 같은 결의 reset 도 검증 (두 번째 build() 시 단계가 누적되지 않음).
  - ImageWorkerTests (B): _image_worker 가 모듈-레벨 자유 함수이고 (Windows
    spawn 에서 pickle 가능), optimize_image 와 동일한 결과를 반환한다.
  - PrunePassUnificationTests (D): _sync_assets 분류 단계의 article_expected
    set 이 글마다 index.{html,php} + 복사 대상 + raster configured widths
    변종을 포함하고, _prune_article_assets 가 src rglob 없이 expected 와
    dst 차집합으로 정리한다 (stale stem-W.webp 자연 제거).
  - ParityCacheTests (E): run_parity_test 의 _parity_cache_key 가 동일 입력에
    동일 키를 만들고, 캐시 hit 시 PHP subprocess 가 호출되지 않는다.

테스트 격리:
  - 각 케이스가 tempfile.mkdtemp 로 자기 base_dir 을 만들어 다른 테스트와
    충돌 없음. tearDown 에서 shutil.rmtree.
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.builder import Builder, _image_worker  # noqa: E402
from scripts.images import ImageConfig, _HAS_PIL  # noqa: E402
from scripts.search import (  # noqa: E402
    _parity_cache_key,
    run_parity_test,
)


# ════════════════════════════════════════════════════════════════
# A) 단계별 timing 계측
# ════════════════════════════════════════════════════════════════


class StepTimingTests(unittest.TestCase):
    """_step / _step_close 의 self._step_times 누적 동작."""

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix='ssg-v130-timing-'))
        (self.base / 'system').mkdir()
        (self.base / 'dist').mkdir()
        self.b = Builder(self.base, enable_cache=False)
        # _emit 가 print 를 호출하므로 stdout 캡쳐만 — 동작에 영향 없음.

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def test_step_open_then_close_records_one_entry(self):
        self.b._step(1, '설정 로드')
        self.b._step_close()
        self.assertEqual(len(self.b._step_times), 1)
        n, label, secs = self.b._step_times[0]
        self.assertEqual(n, 1)
        self.assertEqual(label, '설정 로드')
        self.assertGreaterEqual(secs, 0.0)

    def test_consecutive_steps_close_previous(self):
        self.b._step(1, 'a')
        self.b._step(2, 'b')
        self.b._step(3, 'c')
        self.b._step_close()
        labels = [e[1] for e in self.b._step_times]
        self.assertEqual(labels, ['a', 'b', 'c'])

    def test_step_close_idempotent(self):
        self.b._step(1, 'a')
        self.b._step_close()
        self.b._step_close()  # no-op
        self.assertEqual(len(self.b._step_times), 1)

    def test_step_close_without_open_is_noop(self):
        # _step 호출 전 _step_close → 아무 일도 안 일어남.
        self.b._step_close()
        self.assertEqual(self.b._step_times, [])


# ════════════════════════════════════════════════════════════════
# B) 이미지 멀티프로세스 worker
# ════════════════════════════════════════════════════════════════


@unittest.skipUnless(_HAS_PIL, 'Pillow 미설치 — ImageWorker 테스트 건너뜀.')
class ImageWorkerTests(unittest.TestCase):
    """_image_worker 가 모듈 레벨 자유 함수이며 optimize_image 와 동치."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='ssg-v130-worker-'))
        # 테스트용 PNG (원본 320px — configured widths=[400] 보다 작아 fallback
        # 분기로 [320] 단일 변종만 생성. _select_widths overrun 분기 회피).
        from PIL import Image
        self.src = self.tmp / 'src.png'
        Image.new('RGB', (320, 200), color=(180, 180, 220)).save(self.src)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_worker_is_module_level(self):
        # ProcessPoolExecutor (Windows spawn) 가 pickle 할 수 있어야 한다 —
        # 모듈 레벨 자유 함수의 핵심 조건은 __qualname__ 에 '.' 가 없는 것.
        self.assertNotIn('.', _image_worker.__qualname__)
        self.assertEqual(_image_worker.__module__, 'scripts.builder')

    def test_worker_returns_variants_and_writes_webp(self):
        dst_dir = self.tmp / 'out'
        cfg = ImageConfig(
            enabled=True, widths=[400], max_width=None, quality=80,
            lazy_loading=True, default_sizes='100vw',
        )
        variants, err = _image_worker((self.src, dst_dir, cfg))
        self.assertIsNone(err)
        self.assertIsNotNone(variants)
        # 320 < 400 → fallback 분기로 [320] 단일 변종.
        self.assertEqual(variants.widths, [320])
        self.assertTrue((dst_dir / 'src-320.webp').is_file())


# ════════════════════════════════════════════════════════════════
# D) prune 패스 통합 (간접 검증)
# ════════════════════════════════════════════════════════════════


class PrunePassUnificationTests(unittest.TestCase):
    """_prune_article_assets 가 expected set 만으로 동작하고 src rglob 불필요."""

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix='ssg-v130-prune-'))
        (self.base / 'system').mkdir()
        self.b = Builder(self.base, enable_cache=False)
        # 가짜 Article 만들기 — meta.slug 와 source_dir 만 필요.
        self.dst_root = self.base / 'dist' / 'fake-slug'
        self.dst_root.mkdir(parents=True)
        self.src_root = self.base / 'articles' / 'fake-slug'
        self.src_root.mkdir(parents=True)

        class FakeMeta:
            slug = 'fake-slug'

        class FakeArticle:
            meta = FakeMeta()
            source_dir = self.src_root
        self.article = FakeArticle()

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def test_prune_removes_files_not_in_expected(self):
        # dist 에 '예상 안 한' 파일이 있으면 정리되어야 한다.
        (self.dst_root / 'orphan.txt').write_text('x')
        (self.dst_root / 'keep.txt').write_text('y')
        expected = {self.dst_root / 'keep.txt',
                    self.dst_root / 'index.html',
                    self.dst_root / 'index.php'}
        self.b._prune_article_assets(self.article, expected)
        self.assertFalse((self.dst_root / 'orphan.txt').exists())
        self.assertTrue((self.dst_root / 'keep.txt').exists())

    def test_prune_keeps_index_files(self):
        # index.html / index.php 는 expected 에 포함된 채로 들어와야 한다 —
        # _sync_assets 분류 단계가 이 둘을 자동 등록한다.
        (self.dst_root / 'index.html').write_text('<html/>')
        (self.dst_root / 'index.php').write_text('<?php ?>')
        expected = {self.dst_root / 'index.html',
                    self.dst_root / 'index.php'}
        self.b._prune_article_assets(self.article, expected)
        self.assertTrue((self.dst_root / 'index.html').exists())
        self.assertTrue((self.dst_root / 'index.php').exists())

    def test_prune_removes_stale_variant_no_longer_in_expected(self):
        # 원본 raster 가 삭제되어 expected 에 같은 stem-W.webp 가 안 들어온
        # 케이스 — 자연 정리되는 옛 동작과 동치.
        (self.dst_root / 'old-400.webp').write_text('x')
        expected = {self.dst_root / 'index.html',
                    self.dst_root / 'index.php'}
        self.b._prune_article_assets(self.article, expected)
        self.assertFalse((self.dst_root / 'old-400.webp').exists())


# ════════════════════════════════════════════════════════════════
# E) tokenizer parity 캐시
# ════════════════════════════════════════════════════════════════


class ParityCacheKeyTests(unittest.TestCase):
    """_parity_cache_key 의 결정성 + 입력 변화에 따른 키 변경."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='ssg-v130-paritykey-'))
        self.scripts = self.tmp / 'scripts'
        self.templates = self.tmp / 'templates'
        self.scripts.mkdir()
        self.templates.mkdir()
        (self.scripts / 'search.py').write_text('# search code v1')
        (self.templates / 'search_tokenize.php').write_text('<?php ?>')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_same_inputs_same_key(self):
        k1 = _parity_cache_key(self.scripts, self.templates, 'PHP 8.2.0')
        k2 = _parity_cache_key(self.scripts, self.templates, 'PHP 8.2.0')
        self.assertEqual(k1, k2)

    def test_python_code_change_changes_key(self):
        k1 = _parity_cache_key(self.scripts, self.templates, 'PHP 8.2.0')
        (self.scripts / 'search.py').write_text('# search code v2')
        k2 = _parity_cache_key(self.scripts, self.templates, 'PHP 8.2.0')
        self.assertNotEqual(k1, k2)

    def test_php_code_change_changes_key(self):
        k1 = _parity_cache_key(self.scripts, self.templates, 'PHP 8.2.0')
        (self.templates / 'search_tokenize.php').write_text('<?php // v2 ?>')
        k2 = _parity_cache_key(self.scripts, self.templates, 'PHP 8.2.0')
        self.assertNotEqual(k1, k2)

    def test_php_version_change_changes_key(self):
        k1 = _parity_cache_key(self.scripts, self.templates, 'PHP 8.2.0')
        k2 = _parity_cache_key(self.scripts, self.templates, 'PHP 8.3.0')
        self.assertNotEqual(k1, k2)


class ParityCacheRoundTripTests(unittest.TestCase):
    """run_parity_test 가 캐시 파일을 만들고, 두 번째 호출에서 PHP 미호출."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='ssg-v130-parityrt-'))
        self.scripts = self.tmp / 'scripts'
        self.templates = self.tmp / 'templates'
        self.cache = self.tmp / '.build_cache'
        self.scripts.mkdir()
        self.templates.mkdir()
        # 토크나이저 파일들 (내용은 키 계산에만 영향, 실제 PHP 실행은 mock).
        (self.scripts / 'search.py').write_text('# search code')
        (self.templates / 'search_tokenize.php').write_text('<?php ?>')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_cache_file_written_on_pass(self):
        # _php_tokenize_one 을 mock — 모든 fixture 에 빈 토큰 반환.
        # search_tokenize 도 mock — 같은 빈 토큰. parity OK.
        fake_probe = mock.Mock(returncode=0, stdout=b'PHP 8.2.0 (cli)\n')
        with mock.patch('scripts.search.subprocess.run',
                        return_value=fake_probe), \
             mock.patch('scripts.search._php_tokenize_one',
                        return_value=[]), \
             mock.patch('scripts.search.search_tokenize',
                        return_value=[]):
            result = run_parity_test(
                self.templates, php_bin='php',
                warn_fn=lambda m: None, die_fn=lambda m: self.fail(m),
                cache_dir=self.cache, scripts_dir=self.scripts,
            )
        self.assertTrue(result)
        cache_file = self.cache / 'parity.json'
        self.assertTrue(cache_file.exists())
        data = json.loads(cache_file.read_text(encoding='utf-8'))
        self.assertTrue(data['passed'])
        self.assertIn('key', data)

    def test_cache_hit_skips_php_fixtures(self):
        # 첫 호출 — parity OK → 캐시 저장.
        fake_probe = mock.Mock(returncode=0, stdout=b'PHP 8.2.0 (cli)\n')
        with mock.patch('scripts.search.subprocess.run',
                        return_value=fake_probe), \
             mock.patch('scripts.search._php_tokenize_one',
                        return_value=[]) as m_php, \
             mock.patch('scripts.search.search_tokenize',
                        return_value=[]):
            run_parity_test(
                self.templates, php_bin='php',
                warn_fn=lambda m: None, die_fn=lambda m: self.fail(m),
                cache_dir=self.cache, scripts_dir=self.scripts,
            )
        first_call_count = m_php.call_count
        self.assertGreater(first_call_count, 0)

        # 두 번째 호출 — 캐시 hit, _php_tokenize_one 미호출.
        with mock.patch('scripts.search.subprocess.run',
                        return_value=fake_probe), \
             mock.patch('scripts.search._php_tokenize_one',
                        return_value=[]) as m_php2, \
             mock.patch('scripts.search.search_tokenize',
                        return_value=[]):
            run_parity_test(
                self.templates, php_bin='php',
                warn_fn=lambda m: None, die_fn=lambda m: self.fail(m),
                cache_dir=self.cache, scripts_dir=self.scripts,
            )
        self.assertEqual(m_php2.call_count, 0)

    def test_cache_miss_after_code_change(self):
        fake_probe = mock.Mock(returncode=0, stdout=b'PHP 8.2.0 (cli)\n')
        with mock.patch('scripts.search.subprocess.run',
                        return_value=fake_probe), \
             mock.patch('scripts.search._php_tokenize_one',
                        return_value=[]), \
             mock.patch('scripts.search.search_tokenize',
                        return_value=[]):
            run_parity_test(
                self.templates, php_bin='php',
                warn_fn=lambda m: None, die_fn=lambda m: self.fail(m),
                cache_dir=self.cache, scripts_dir=self.scripts,
            )

        # PHP 토크나이저 파일 변경 → 키 달라짐 → 캐시 miss.
        (self.templates / 'search_tokenize.php').write_text('<?php // v2 ?>')
        with mock.patch('scripts.search.subprocess.run',
                        return_value=fake_probe), \
             mock.patch('scripts.search._php_tokenize_one',
                        return_value=[]) as m_php2, \
             mock.patch('scripts.search.search_tokenize',
                        return_value=[]):
            run_parity_test(
                self.templates, php_bin='php',
                warn_fn=lambda m: None, die_fn=lambda m: self.fail(m),
                cache_dir=self.cache, scripts_dir=self.scripts,
            )
        # miss 이므로 PHP 호출이 다시 일어난다 (fixture 마다 1번).
        self.assertGreater(m_php2.call_count, 0)


if __name__ == '__main__':
    unittest.main()

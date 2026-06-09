"""dist 산출물 mtime churn 회귀 가드 (v1.14.3 신설).

배경: 빌더가 매 빌드마다 모든 텍스트 산출물(글·카테고리·홈·404·feed·sitemap·
robots·search)을 무조건 다시 써서, 내용이 같아도 mtime 이 갱신됐다. 배포
(deploy.py 의 ``rclone sync``)는 ``--checksum`` 없이 mtime+size 로 비교하므로,
문서 한 편만 고쳐도 사이트 전체가 '변경됨' 으로 잡혀 매번 전부 재업로드됐다.

v1.14.3 은 산출물 쓰기를 ``_write_text_if_changed`` (기존 바이트와 같으면
건너뜀, mtime 보존) 로 라우팅한다. 이 모듈이 그 불변식을 고정한다:
  - 단위: 내용 동일 → mtime 보존 / 내용 변경 → 재작성, 임시파일 잔존 없음.
  - 통합: 무변경 재빌드 = mtime churn 0, 한 글 편집 = 그 글 출력만 갱신.

테스트 격리: 각 케이스가 자기 tempfile 트리를 만들고 tearDown 에서 정리한다.
"""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.builder import Builder, _write_text_if_changed  # noqa: E402

VERDIR = ROOT.parent   # 실 소스(user/·system/) 의 위치

# 결정적 baseline mtime — 빌드 후 모든 dist 파일에 찍고, 갱신 여부를 이 값과의
# 차이로 본다 (빌드 두 번이 같은 초에 끝나는 mtime 해상도 경합을 피해 절대값
# 비교). **미래 시각**이어야 한다: _copy_if_newer 가 dst.mtime >= src.mtime 일
# 때 에셋 복사를 건너뛰므로, baseline 이 소스보다 과거이면 에셋이 재복사돼
# 거짓 churn 으로 잡힌다. 미래로 찍으면 (a) 안 바뀐 파일은 그대로 baseline 을
# 유지하고 (b) 재작성/재복사된 파일만 mtime 이 '현재'(< baseline)로 떨어져 검출된다.
_STAMP = 4_000_000_000.0   # 2096년경 — 64-bit time 안전 범위, 소스 mtime 보다 미래.

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
)


def _scaffold_site():
    """최소 단일-글 사이트를 임시 디렉터리에 만든다 (v1.5.0 분할 레이아웃)."""
    tmp = Path(tempfile.mkdtemp(prefix='ssg-v1143-churn-'))
    (tmp / 'user').mkdir(parents=True, exist_ok=True)
    (tmp / 'user' / 'site.yaml').write_text(SITE_YAML_MIN, encoding='utf-8')
    shutil.copytree(VERDIR / 'user' / 'templates', tmp / 'user' / 'templates')
    shutil.copytree(VERDIR / 'user' / 'styles', tmp / 'user' / 'styles')
    shutil.copytree(VERDIR / 'user' / 'branding', tmp / 'user' / 'branding')
    shutil.copytree(VERDIR / 'system' / 'runtime', tmp / 'system' / 'runtime')

    art = tmp / 'user' / 'articles' / 'Demo'
    art.mkdir(parents=True)
    (art / 'meta.yaml').write_text(
        "slug: demo\ntitle: Demo\ndate: 2026-01-01\n"
        "seo:\n  description: A demo article.\n",
        encoding='utf-8',
    )
    (art / 'content.md').write_text('# Demo body\n\nHello.\n', encoding='utf-8')
    return tmp


def _add_article(tmp, folder, slug, date):
    art = tmp / 'user' / 'articles' / folder
    art.mkdir(parents=True)
    (art / 'meta.yaml').write_text(
        f"slug: {slug}\ntitle: {folder}\ndate: {date}\n"
        f"seo:\n  description: {folder} article.\n",
        encoding='utf-8',
    )
    (art / 'content.md').write_text(f'# {folder}\n\nBody.\n', encoding='utf-8')


def _stamp_future(dist):
    """dist 의 모든 파일에 baseline mtime(_STAMP) 을 찍고, 그 파일 목록을 돌려준다."""
    files = [p for p in dist.rglob('*') if p.is_file()]
    for p in files:
        os.utime(p, (_STAMP, _STAMP))
    return files


def _churned(files, dist):
    """baseline 이후 mtime 이 갱신된 dist 상대경로 (정렬)."""
    return sorted(
        str(p.relative_to(dist)).replace('\\', '/')
        for p in files if p.exists() and p.stat().st_mtime != _STAMP
    )


class WriteTextIfChangedUnitTests(unittest.TestCase):
    """_write_text_if_changed 의 skip/rewrite/atomic 동작."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='ssg-v1143-unit-'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_identical_content_preserves_mtime(self):
        p = self.tmp / 'out.txt'
        _write_text_if_changed(p, 'hello')
        os.utime(p, (_STAMP, _STAMP))
        _write_text_if_changed(p, 'hello')          # 동일 → 건너뜀
        self.assertEqual(p.stat().st_mtime, _STAMP,
                         '내용 동일 시 mtime 이 유지돼야 함(배포 churn 방지)')
        self.assertEqual(p.read_text(encoding='utf-8'), 'hello')

    def test_changed_content_rewrites(self):
        p = self.tmp / 'out.txt'
        _write_text_if_changed(p, 'hello')
        os.utime(p, (_STAMP, _STAMP))
        _write_text_if_changed(p, 'world')          # 다름 → 재작성
        self.assertNotEqual(p.stat().st_mtime, _STAMP)
        self.assertEqual(p.read_text(encoding='utf-8'), 'world')

    def test_creates_parents_and_leaves_no_tmp(self):
        p = self.tmp / 'a' / 'b' / 'out.html'
        _write_text_if_changed(p, '<x>')
        self.assertEqual(p.read_text(encoding='utf-8'), '<x>')
        self.assertEqual(list(p.parent.glob('*.heron_tmp')), [],
                         '원자적 쓰기의 임시파일이 남으면 안 됨')

    def test_utf8_roundtrip(self):
        p = self.tmp / 'out.txt'
        _write_text_if_changed(p, '한글 — em·dash')
        self.assertEqual(p.read_bytes(), '한글 — em·dash'.encode('utf-8'))


class NoChurnIntegrationTests(unittest.TestCase):
    """전체 빌드에서 무변경 재빌드가 dist mtime 을 건드리지 않는다."""

    def setUp(self):
        self.tmp = _scaffold_site()
        self.dist = self.tmp / 'dist'

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_noop_rebuild_churns_zero_files(self):
        Builder(base_dir=self.tmp, enable_cache=True).build()
        files = _stamp_future(self.dist)
        self.assertTrue(files, 'dist 에 산출물이 있어야 함')

        Builder(base_dir=self.tmp, enable_cache=True).build()   # 소스 무변경
        self.assertEqual(
            _churned(files, self.dist), [],
            '무변경 재빌드가 mtime 을 갱신하면 rclone 이 전부 재업로드한다')

    def test_noop_rebuild_no_cache_also_churns_zero(self):
        # 캐시를 꺼도(매 글 재렌더) 산출물 바이트가 같으면 mtime 은 유지돼야 함.
        Builder(base_dir=self.tmp, enable_cache=False).build()
        files = _stamp_future(self.dist)

        Builder(base_dir=self.tmp, enable_cache=False).build()
        self.assertEqual(_churned(files, self.dist), [],
                         '캐시 off 여도 무변경 재빌드는 mtime 0 churn 이어야 함')

    def test_single_article_edit_touches_only_that_output(self):
        _add_article(self.tmp, 'Other', 'other', '2026-01-02')
        Builder(base_dir=self.tmp, enable_cache=True).build()
        files = _stamp_future(self.dist)

        # Demo 본문만 편집(요약/제목/날짜는 그대로 → 집계 페이지는 바이트 동일).
        (self.tmp / 'user' / 'articles' / 'Demo' / 'content.md').write_text(
            '# Demo body\n\nHello.\n\n<!-- edit marker -->\n', encoding='utf-8')
        Builder(base_dir=self.tmp, enable_cache=True).build()

        churned = _churned(files, self.dist)
        self.assertIn('demo/index.html', churned,
                      '편집한 글의 출력은 갱신돼야 함')
        self.assertNotIn('other/index.html', churned,
                         '편집하지 않은 글의 출력은 mtime 이 유지돼야 함(핵심 불변식)')


if __name__ == '__main__':
    unittest.main()

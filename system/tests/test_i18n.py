"""v1.9.0 신설 — i18n 로케일 로더 + 로케일 팩 무결성 단위 테스트.

검증 (Surface 1 site.* / Surface 3 build.* / Surface 2 admin.* 전부):
  (a) 폴백 체인 — 없는 키 → 키 문자열 자체, 없는 로케일 → ko 폴백,
      비-ko 로케일이 ko 전용(미정의) 키를 ko 값으로 폴백.
  (b) 키 패리티 — system/locales/ 트리의 모든 로케일 폴더의 머지 키 집합이
      ko(정본) 의 머지 키 집합과 동일 (admin.yaml 포함 — 다른 에이전트의
      누락도 잡는다).
  (c) 자리표시자 치환 — site.search.result_count 가 n=3 으로 치환됨.
  (d) ko 정본 불변 — site/build 의 대표 키가 옛 하드코딩 한국어와 동일.
"""
import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from scripts import i18n  # noqa: E402


class FallbackChainTests(unittest.TestCase):
    """(a) 폴백 체인: locale → ko → 키 문자열."""

    def test_missing_key_returns_key_string(self):
        tr = i18n.load('ko')
        self.assertEqual(
            tr.t('site.does.not.exist'), 'site.does.not.exist'
        )

    def test_unknown_locale_falls_back_to_ko(self):
        # 존재하지 않는 로케일 → 팩이 비어 있고 모든 키가 ko 로 폴백.
        ko = i18n.load('ko')
        xx = i18n.load('xx-nonexistent')
        self.assertEqual(xx.locale, 'xx-nonexistent')
        for key in ('site.search.placeholder', 'site.footer.rights',
                    'build.warn.pillow_missing'):
            self.assertEqual(xx.t(key), ko.t(key))

    def test_non_ko_locale_falls_back_to_ko_for_undefined_key(self):
        # ko 에는 있으나 어떤 로케일 팩에도 *추가로* 없을 임의 키를 시뮬레이션:
        # 없는 로케일(xx) 의 admin 전용 키도 ko 값으로 폴백해야 한다.
        ko = i18n.load('ko')
        xx = i18n.load('xx-nonexistent')
        # admin.* 키 하나를 표본으로 — ko 팩에 존재하면 폴백이 그 값을 반환.
        sample = 'admin.nav.list'
        if ko.t(sample) != sample:  # ko 에 실제로 정의돼 있을 때만 의미 있음
            self.assertEqual(xx.t(sample), ko.t(sample))


class KeyParityTests(unittest.TestCase):
    """(b) system/locales/ 전체 트리의 키 패리티 (admin/site/build 포함)."""

    def test_every_locale_matches_ko_key_set(self):
        ko_keys = set(i18n._load_pack('ko'))
        self.assertTrue(ko_keys, 'ko 정본 팩이 비어 있습니다.')
        for locale in i18n.available_locales():
            if locale == i18n.CANONICAL:
                continue
            keys = set(i18n._load_pack(locale))
            missing = ko_keys - keys
            extra = keys - ko_keys
            self.assertEqual(
                missing, set(),
                f"로케일 '{locale}' 에 누락된 키: {sorted(missing)}",
            )
            self.assertEqual(
                extra, set(),
                f"로케일 '{locale}' 에 ko 에 없는 키: {sorted(extra)}",
            )


class PlaceholderTests(unittest.TestCase):
    """(c) 자리표시자 치환."""

    def test_result_count_substitution_ko(self):
        tr = i18n.load('ko')
        self.assertEqual(
            tr.t('site.search.result_count', n=3), '검색결과: 3건'
        )

    def test_result_count_substitution_en(self):
        tr = i18n.load('en')
        self.assertEqual(
            tr.t('site.search.result_count', n=3), '3 results'
        )

    def test_scoped_label_substitution(self):
        ko = i18n.load('ko')
        self.assertEqual(
            ko.t('site.search.scoped_label', cat='블로그'),
            '블로그 카테고리에서 검색',
        )
        en = i18n.load('en')
        self.assertEqual(
            en.t('site.search.scoped_label', cat='Blog'), 'Search in Blog'
        )


class CanonicalInvarianceTests(unittest.TestCase):
    """(d) ko 정본이 옛 하드코딩 한국어와 byte-동일 (회귀 가드)."""

    def test_site_canonical_values(self):
        tr = i18n.load('ko')
        self.assertEqual(tr.t('site.search.placeholder'), '검색')
        self.assertEqual(tr.t('site.search.scope_all'), '전체에서 검색')
        self.assertEqual(tr.t('site.search.hint_empty'), '검색어를 입력하세요.')
        self.assertEqual(tr.t('site.search.no_results'), '검색 결과가 없습니다.')
        self.assertEqual(tr.t('site.footer.rights'), 'All rights reserved.')
        self.assertEqual(tr.t('site.pagination.prev_aria'), 'Previous page')
        self.assertEqual(tr.t('site.pagination.next_aria'), 'Next page')
        self.assertEqual(tr.t('site.error_404.heading'), 'Not Found')

    def test_build_canonical_values(self):
        tr = i18n.load('ko')
        # legacy_home_key 의 {key} 치환이 옛 f-string 결과와 동일해야 한다.
        self.assertEqual(
            tr.t('build.warn.empty_category'),
            '이 카테고리에 글이 하나도 없습니다 (빈 카테고리).',
        )
        # unfilled_placeholder 는 {{NAME}} (이중 중괄호) 를 출력해야 한다.
        self.assertEqual(
            tr.t('build.warn.unfilled_placeholder', name='BODY'),
            '템플릿에 채우지 못한 placeholder 가 발견되어 빈 문자열로 '
            'strip 되었습니다: {{BODY}}.',
        )


if __name__ == '__main__':
    unittest.main()

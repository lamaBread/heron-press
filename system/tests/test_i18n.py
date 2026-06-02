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
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from scripts import i18n  # noqa: E402


class FallbackChainTests(unittest.TestCase):
    """(a) 폴백 체인: locale → en(CANONICAL) → 키 문자열."""

    def test_missing_key_returns_key_string(self):
        tr = i18n.load(i18n.CANONICAL)
        self.assertEqual(
            tr.t('site.does.not.exist'), 'site.does.not.exist'
        )

    def test_unknown_locale_falls_back_to_canonical(self):
        # 존재하지 않는 로케일 → 팩이 비어 있고 모든 키가 CANONICAL(en) 로 폴백.
        canon = i18n.load(i18n.CANONICAL)
        xx = i18n.load('xx-nonexistent')
        self.assertEqual(xx.locale, 'xx-nonexistent')
        for key in ('site.search.placeholder', 'site.footer.rights',
                    'build.warn.pillow_missing'):
            self.assertEqual(xx.t(key), canon.t(key))

    def test_non_canonical_locale_falls_back_to_canonical_for_undefined_key(self):
        # CANONICAL(en) 에는 있으나 어떤 로케일 팩에도 *추가로* 없을 임의 키를
        # 시뮬레이션: 없는 로케일(xx) 의 admin 전용 키도 en 값으로 폴백해야 한다.
        canon = i18n.load(i18n.CANONICAL)
        xx = i18n.load('xx-nonexistent')
        # admin.* 키 하나를 표본으로 — CANONICAL 팩에 존재하면 폴백이 그 값을 반환.
        sample = 'admin.nav.list'
        if canon.t(sample) != sample:  # CANONICAL 에 정의돼 있을 때만 의미 있음
            self.assertEqual(xx.t(sample), canon.t(sample))


class KeyParityTests(unittest.TestCase):
    """(b) system/locales/ 전체 트리의 키 패리티 (admin/site/build 포함)."""

    def test_every_locale_matches_canonical_key_set(self):
        ref_keys = set(i18n._load_pack(i18n.CANONICAL))
        self.assertTrue(ref_keys, f'{i18n.CANONICAL} 기준 팩이 비어 있습니다.')
        for locale in i18n.available_locales():
            if locale == i18n.CANONICAL:
                continue
            keys = set(i18n._load_pack(locale))
            missing = ref_keys - keys
            extra = keys - ref_keys
            self.assertEqual(
                missing, set(),
                f"로케일 '{locale}' 에 누락된 키: {sorted(missing)}",
            )
            self.assertEqual(
                extra, set(),
                f"로케일 '{locale}' 에 {i18n.CANONICAL} 에 없는 키: {sorted(extra)}",
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
    """(d) ko 팩 값이 옛 하드코딩 한국어와 byte-동일 (회귀 가드). v1.9.7 부터
    CANONICAL=en 이지만, ko 는 완전 번역으로 동봉되며 그 원본 값은 이 가드로 고정."""

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

    def test_build_console_report_canonical_values(self):
        # v1.9.2: 빌드 콘솔/리포트 신규 키의 ko 정본 — 옛 하드코딩과 byte-동일
        # (도구=ko 빌드 콘솔/build-report.md 가 v1.9.1 과 동일해야 한다).
        tr = i18n.load('ko')
        self.assertEqual(tr.t('build.step.1'),
                         '설정 로드 (site.yaml / 토크나이저 패리티)')
        self.assertEqual(tr.t('build.step.8'), '글 렌더링')
        self.assertEqual(tr.t('build.step.16'), '고아 산출물 정리')
        self.assertEqual(tr.t('build.console.output'), '산출물: dist/ (Heron).')
        self.assertEqual(
            tr.t('build.console.done', art=12, cat=5, issue=0, warn=1,
                 php='', elapsed=5.8),
            '빌드 완료: 12 글, 5 카테고리, 0 보완 필요, 1 살펴볼 사항. (5.8s)')
        self.assertEqual(tr.t('build.report.issues_header'),
                         '── 보완이 필요한 항목 (산출물 일부 누락 가능) ──')
        self.assertEqual(tr.t('build.report.abort_suffix'),
                         '빌드 중단 (시스템 결함).')
        self.assertEqual(tr.t('build.report.md_title'), '# Heron 빌드 리포트')

    def test_build_console_report_en_translated(self):
        # 신규 build.* 키가 en 으로 실제 번역됐는지(ko 폴백이 아닌지) 표본 확인.
        en = i18n.load('en')
        self.assertEqual(en.t('build.step.8'), 'Render articles')
        self.assertEqual(en.t('build.console.output'), 'Output: dist/ (Heron).')
        self.assertEqual(en.t('build.report.abort_suffix'),
                         'Build aborted (system fault).')

    def test_cli_help_abort_canonical_values(self):
        # v1.9.3: argparse --help + 잔여 abort 신규 키의 ko 정본 — 옛 하드코딩과
        # byte-동일 (도구=ko 의 --help / 이미지 abort / 패리티 출력이 불변).
        tr = i18n.load('ko')
        self.assertEqual(tr.t('cli.help.description'),
                         'Heron 정적 사이트 빌드 (런타임 PHP 대상).')
        self.assertEqual(
            tr.t('cli.help.clean'),
            'dist/ 와 .build_cache/ 를 모두 지운 뒤 빌드 (완전 재빌드).')
        # epilog 의 \n 은 개행으로 해석되고 # 라벨/정렬 공백이 보존돼야 한다.
        self.assertEqual(
            tr.t('cli.help.epilog'),
            '관련 명령:\n'
            '  python -m unittest discover -s system/tests   # 단위 테스트\n'
            '  python system/tests/run_diagnostics.py        # 통합 진단')
        # 이미지 abort: {received!r} 가 repr() 로 렌더 (옛 f-string {x!r} 보존).
        self.assertEqual(
            tr.t('build.abort.images_widths_type', received=['a']),
            "site.yaml: images.widths 는 양의 정수 리스트여야 합니다 "
            "(받은 값: ['a'])")
        self.assertEqual(
            tr.t('build.abort.images_quality_range', received=150),
            'site.yaml: images.quality 는 0~100 범위여야 합니다 (받은 값: 150)')
        self.assertEqual(tr.t('build.parity.fail_header'),
                         '토크나이저 패리티 실패 (Python ≠ PHP):')
        self.assertEqual(
            tr.t('build.parity.php_unavailable'),
            'PHP 실행 불가 — 토크나이저 패리티 검증을 건너뜁니다.')

    def test_cli_help_abort_en_translated(self):
        # v1.9.3: 신규 cli.help.* / abort 키가 en 으로 번역됐는지(ko 폴백 아닌지).
        en = i18n.load('en')
        self.assertEqual(en.t('cli.help.description'),
                         'Build a Heron static site (targets PHP at runtime).')
        self.assertEqual(
            en.t('build.abort.images_quality_range', received=150),
            'site.yaml: images.quality must be in the range 0-100 (got: 150)')
        self.assertEqual(en.t('build.parity.fail_header'),
                         'Tokenizer parity failed (Python ≠ PHP):')
        # php_unavailable 은 php_missing 과 같은 영문 텍스트(조건만 다름).
        self.assertEqual(en.t('build.parity.php_unavailable'),
                         'PHP not available — skipping tokenizer parity test.')

    def test_build_issue_canonical_values(self):
        # v1.9.4: 글/카테고리 단위 _issue/_warning 본문 신규 키의 ko 정본 —
        # 옛 하드코딩 f-string 과 byte-동일 (도구=ko 의 콘텐츠-결함 출력 불변).
        tr = i18n.load('ko')
        self.assertEqual(
            tr.t('build.issue.both_content'),
            'content.md 와 content.html 이 둘 다 존재합니다 (한 글에 하나만 두세요).')
        # {received!r}: 문자열은 repr() 로 따옴표가 붙어야 한다 (옛 {x!r} 보존).
        self.assertEqual(
            tr.t('build.issue.slug_regex', received='1bad'),
            "slug 정규식 불일치: '1bad' — 글이 빌드에서 제외됨.")
        # {received!r}: 리스트도 repr() — 따옴표 없이 [...] (seo_raw!r 보존).
        self.assertEqual(
            tr.t('build.issue.seo_not_mapping', received=['x']),
            "meta.yaml: 'seo' 는 매핑이어야 합니다 (받은 값: ['x']) — 빈 seo 로 폴백.")
        # 다중 파라미터 (repr + path), 그리고 plain {updated}/{date}.
        self.assertEqual(
            tr.t('build.issue.slug_reserved', received='search',
                 path='/search.php'),
            "slug 예약어: 'search' — 시스템 경로 (/search.php) 와 충돌. "
            '글이 빌드에서 제외됨.')
        self.assertEqual(
            tr.t('build.issue.updated_before_date',
                 updated='2026-01-01', date='2026-02-01'),
            'updated (2026-01-01) 가 date (2026-02-01) 보다 앞섭니다 — '
            '그대로 진행하지만 의도 확인 권장.')
        # {origin} 는 별도 label 키 — page_folder 라벨이 합성돼야 한다.
        self.assertEqual(
            tr.t('build.issue.template_file_missing',
                 origin=tr.t('build.label.origin_page_folder'),
                 received='x.html', default='article.html'),
            "meta.yaml: 'template' 에 명시한 파일이 페이지 폴더에 없습니다: "
            "'x.html' — 기본 article.html 로 폴백.")
        self.assertEqual(tr.t('build.label.origin_templates'), 'templates/')
        self.assertEqual(
            tr.t('build.issue.content_missing'),
            'content 파일을 찾을 수 없어 글을 빌드하지 않습니다.')
        self.assertEqual(
            tr.t('build.issue.seo_desc_missing_article'),
            "meta.yaml: 'seo.description' 필드가 없습니다 — 외부 노출용 한 줄 "
            '설명을 작성해주세요. (description / og:description / '
            'twitter:description / 피드 summary 가 모두 누락됩니다.)')
        # 이미지 인코딩 실패 warn (images.py → 전역 i18n.t()).
        self.assertEqual(
            tr.t('build.warn.image_optimize_failed', name='a.png', error='boom'),
            '이미지 최적화 실패 (a.png): boom')

    def test_build_issue_en_translated(self):
        # v1.9.4: 신규 build.issue.* / label / warn 키가 en 으로 번역됐는지
        # (ko 폴백이 아닌지) 표본 확인.
        en = i18n.load('en')
        self.assertEqual(
            en.t('build.issue.both_content'),
            'Both content.md and content.html exist (keep only one per article).')
        self.assertEqual(
            en.t('build.issue.slug_regex', received='1bad'),
            "slug regex mismatch: '1bad' — article excluded from the build.")
        self.assertEqual(en.t('build.label.origin_page_folder'), 'the page folder')
        self.assertEqual(
            en.t('build.issue.template_file_missing',
                 origin=en.t('build.label.origin_page_folder'),
                 received='x.html', default='article.html'),
            "meta.yaml: file specified in 'template' not found in the page "
            "folder: 'x.html' — falling back to default article.html.")
        self.assertEqual(
            en.t('build.warn.image_optimize_failed', name='a.png', error='boom'),
            'Image optimization failed (a.png): boom')


class EscapeDecodingTests(unittest.TestCase):
    """v1.9.1 — 큰따옴표 값 escape 해석 (\\" \\\\ \\n \\t), 작은따옴표는 리터럴."""

    def test_double_quote_escapes(self):
        self.assertEqual(i18n._unquote(r'"a\"b"'), 'a"b')
        self.assertEqual(i18n._unquote(r'"a\\b"'), 'a\\b')
        self.assertEqual(i18n._unquote(r'"a\nb"'), 'a\nb')
        self.assertEqual(i18n._unquote(r'"a\tb"'), 'a\tb')

    def test_unknown_escape_preserved(self):
        # 알 수 없는 escape 는 백슬래시째 보존 (예: Windows 경로 토큰).
        self.assertEqual(i18n._unquote(r'"a\xb"'), r'a\xb')

    def test_single_quote_is_literal(self):
        self.assertEqual(i18n._unquote(r"'a\nb'"), r'a\nb')
        self.assertEqual(i18n._unquote('"' + "class='k'" + '"'), "class='k'")

    def test_no_resolved_value_has_stray_backslash(self):
        # 회귀 가드: 모든 로케일의 모든 해석값에 백슬래시가 남지 않아야 한다.
        # (v1.9.0 의 `class=\\"k\\"` / pillow `\\n` 누수 버그 재발 방지. 어떤
        # 값이든 리터럴 백슬래시가 필요해지면 이 테스트를 의도적으로 갱신할 것.)
        for locale in i18n.available_locales():
            for k, v in i18n._load_pack(locale).items():
                self.assertNotIn(
                    '\\', v,
                    f"[{locale}] {k} 에 미해석 백슬래시가 남아 있습니다: {v!r}")


class CliPackTests(unittest.TestCase):
    """v1.9.1 — Surface 3 cli.* 팩 (운영자 CLI/배포/업데이트/마이그레이션)."""

    def test_cli_keys_present_and_translated(self):
        ko, en = i18n.load('ko'), i18n.load('en')
        self.assertEqual(ko.t('cli.deploy.done'), '완료.')
        self.assertEqual(en.t('cli.deploy.done'), 'Done.')
        self.assertEqual(ko.t('cli.checkupdate.uptodate', current='1.9.1'),
                         '최신입니다 (v1.9.1).')
        self.assertEqual(en.t('cli.checkupdate.uptodate', current='1.9.1'),
                         'You are up to date (v1.9.1).')

    def test_cli_newline_escape_decoded(self):
        # cli.deploy.config_error 의 \n 이 실제 개행으로 해석돼야 한다.
        self.assertIn('\n', i18n.load('ko').t('cli.deploy.config_error',
                                              error='X'))

    def test_global_t_switches_with_init(self):
        # 전역 i18n.t() 가 init() 으로 도구 언어를 바꾼다 (Heron.py 진입 패턴).
        try:
            i18n.init('en')
            self.assertEqual(i18n.t('cli.deploy.done'), 'Done.')
            i18n.init('ko')
            self.assertEqual(i18n.t('cli.deploy.done'), '완료.')
        finally:
            i18n.init(i18n.CANONICAL)   # 다른 테스트 오염 방지 — 기본값(en)으로 복원.


class LocaleNameParityTests(unittest.TestCase):
    """v1.9.1 — 설정 드롭다운 표시명: available 로케일마다 endonym 키가 있다."""

    def test_every_available_locale_has_display_name(self):
        ko = i18n.load('ko')
        for loc in i18n.available_locales():
            key = f'admin.locale.name.{loc}'
            self.assertNotEqual(
                ko.t(key), key,
                f'로케일 {loc} 의 표시명 키({key})가 없습니다.')


@unittest.skipUnless(shutil.which('php'), 'php 미설치 — PHP 파서 패리티 생략')
class PhpParserParityTests(unittest.TestCase):
    """v1.9.1 — PHP(i18n.php) 와 Python(i18n.py) 파서가 **바이트 동일** 맵을
    낸다 (Surface 2 admin UI 와 Surface 1/3 의 번역 누수/불일치 방지)."""

    def test_php_python_packs_identical(self):
        php_lib = (_SRC / 'admin' / 'lib' / 'i18n.php').as_posix()
        code = (f'require {json.dumps(php_lib)};'
                '$a=[];foreach(i18n_available_locales() as $l)'
                '$a[$l]=i18n_load_pack($l);'
                'echo json_encode($a, JSON_UNESCAPED_UNICODE);')
        out = subprocess.run(['php', '-r', code], capture_output=True,
                             text=True, encoding='utf-8')
        self.assertEqual(out.returncode, 0, out.stderr)
        php = json.loads(out.stdout)
        for locale in i18n.available_locales():
            self.assertEqual(
                i18n._load_pack(locale), php.get(locale, {}),
                f"로케일 '{locale}' 의 PHP/Python 파싱 결과가 다릅니다.")


if __name__ == '__main__':
    unittest.main()

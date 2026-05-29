"""scripts/builder Google AdSense 통합 단위 테스트 (v1.1.3·v1.1.5).

site.yaml `google_adsense:` 블록 파싱 + 5 페이지 head 의
`{{ADSENSE_HEAD}}` placeholder line-eating 헬퍼를 검증한다.

  - `_parse_adsense_config` : 두 문자열 필드(ads_txt·head_script)와
                              v1.1.5 의 exclude_urls 리스트 정규화
                              (str().strip() + leading `/` 보정 + frozenset).
  - `_apply_adsense_head_placeholder` : head_script 활성/비활성과
                              exclude_urls 매칭에 따른 placeholder
                              라인 strip 여부 (v1.1.5 의 page_url 분기).
                              호출 시 self._adsense_seen_urls 에 URL 적재.
  - `_check_exclude_urls` : 매칭 안 되는 exclude_urls entry 를
                              BuildReport warning 으로 보고 (v1.1.5).

`_parse_adsense_config` 는 self 를 쓰지 않으므로 unbound 로 호출
(`ParseJsonLdConfigTests` 와 같은 정신 — Builder 인스턴스 불필요).
`_apply_adsense_head_placeholder` 는 `self.site.google_adsense` +
`self._adsense_seen_urls` 만 참조하므로 SimpleNamespace 로 self 모킹.
"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.builder import Builder  # noqa: E402
from scripts.models import AdSenseConfig  # noqa: E402


# ════════════════════════════════════════════════════════════════
# site.yaml `google_adsense:` 블록 파싱 (_parse_adsense_config)
# ════════════════════════════════════════════════════════════════

class ParseAdSenseConfigTests(unittest.TestCase):
    """`_parse_adsense_config` 는 self 를 쓰지 않으므로 unbound 호출."""

    def _parse(self, raw):
        return Builder._parse_adsense_config(None, raw)

    def test_empty_defaults_disabled(self):
        cfg = self._parse({})
        self.assertEqual(cfg.ads_txt, '')
        self.assertEqual(cfg.head_script, '')
        self.assertEqual(cfg.exclude_urls, frozenset())

    def test_non_dict_falls_back_to_default(self):
        for raw in (None, 'string', 0, [], 'abc'):
            cfg = self._parse(raw)
            self.assertEqual(cfg.ads_txt, '')
            self.assertEqual(cfg.head_script, '')
            self.assertEqual(cfg.exclude_urls, frozenset())

    def test_ads_txt_preserved_with_trailing_newline(self):
        # YAML literal block `|` 이 보존하는 \n 을 그대로 유지 (텍스트 파일 표준).
        raw = {'ads_txt': 'google.com, pub-12345, DIRECT, abc\n'}
        cfg = self._parse(raw)
        self.assertEqual(cfg.ads_txt, 'google.com, pub-12345, DIRECT, abc\n')

    def test_head_script_strips_trailing_newline(self):
        # YAML literal block `|` 의 말미 \n 이 head 빈 줄을 만드는 것 방지.
        raw = {'head_script': '<script async src="…"></script>\n'}
        cfg = self._parse(raw)
        self.assertEqual(cfg.head_script, '<script async src="…"></script>')

    def test_none_values_become_empty_strings(self):
        cfg = self._parse({'ads_txt': None, 'head_script': None})
        self.assertEqual(cfg.ads_txt, '')
        self.assertEqual(cfg.head_script, '')


class ParseAdSenseExcludeUrlsTests(unittest.TestCase):
    """v1.1.5: exclude_urls 정규화 (str().strip() + leading `/` 보정 + frozenset)."""

    def _parse(self, exclude_urls):
        return Builder._parse_adsense_config(None, {
            'exclude_urls': exclude_urls,
        })

    def test_missing_key_defaults_empty_frozenset(self):
        cfg = Builder._parse_adsense_config(None, {})
        self.assertEqual(cfg.exclude_urls, frozenset())

    def test_none_value_defaults_empty(self):
        # `exclude_urls:` 로 적되 값이 없는 경우 (yaml 에서 None).
        cfg = self._parse(None)
        self.assertEqual(cfg.exclude_urls, frozenset())

    def test_empty_list_is_empty_frozenset(self):
        cfg = self._parse([])
        self.assertEqual(cfg.exclude_urls, frozenset())

    def test_absolute_url_passthrough(self):
        cfg = self._parse(['/', '/about/', '/404.html', '/search.php'])
        self.assertEqual(
            cfg.exclude_urls,
            frozenset({'/', '/about/', '/404.html', '/search.php'}),
        )

    def test_leading_slash_is_normalized(self):
        # `about/` → `/about/`, `blog/3d-printing/` → `/blog/3d-printing/`.
        cfg = self._parse(['about/', 'blog/3d-printing/'])
        self.assertEqual(
            cfg.exclude_urls,
            frozenset({'/about/', '/blog/3d-printing/'}),
        )

    def test_case_preserved_unlike_v114(self):
        # v1.1.4 의 page-type 식별자와 달리 URL 은 대소문자 보존
        # (사이트의 실제 slug 가 mixed-case 라면 그대로 매칭하기 위함).
        cfg = self._parse(['/About/', '/blog/Top-Picks/'])
        self.assertEqual(
            cfg.exclude_urls,
            frozenset({'/About/', '/blog/Top-Picks/'}),
        )

    def test_trailing_slash_preserved(self):
        # `/about` 과 `/about/` 는 서로 다른 entry — 운영자가 페이지의
        # canonical URL 과 정확히 일치시키도록 한다.
        cfg = self._parse(['/about', '/about/'])
        self.assertEqual(cfg.exclude_urls, frozenset({'/about', '/about/'}))

    def test_normalizes_whitespace(self):
        cfg = self._parse(['  /about/  ', '\t/clear/'])
        self.assertEqual(cfg.exclude_urls, frozenset({'/about/', '/clear/'}))

    def test_scalar_single_value_accepted(self):
        # `exclude_urls: /about/` 처럼 단일 스칼라도 흡수.
        cfg = self._parse('/about/')
        self.assertEqual(cfg.exclude_urls, frozenset({'/about/'}))

    def test_empty_string_and_none_items_skipped(self):
        cfg = self._parse(['/about/', '', None, '  ', '/clear/'])
        self.assertEqual(cfg.exclude_urls, frozenset({'/about/', '/clear/'}))


# ════════════════════════════════════════════════════════════════
# placeholder line-eating 헬퍼 (_apply_adsense_head_placeholder)
# ════════════════════════════════════════════════════════════════

def _self_with(head_script='', exclude_urls=frozenset()):
    """`self.site.google_adsense` + `self._adsense_seen_urls` 만 참조하는 self 모킹."""
    return SimpleNamespace(
        site=SimpleNamespace(
            google_adsense=AdSenseConfig(
                head_script=head_script,
                exclude_urls=exclude_urls,
            ),
        ),
        _adsense_seen_urls=set(),
    )


# 라인 자체가 strip 되어야 하는지 (= placeholder 가 사라지고 빈 줄도 없음)
# 를 검증하기 위한 5-라인 템플릿. ADSENSE_HEAD 라인이 통째로 제거되면
# 결과는 `before\n{{NEXT}}\n`.
_TPL = (
    '<head>\n'
    '<meta name="viewport" content="width=device-width">\n'
    '    {{ADSENSE_HEAD}}\n'
    '<title>x</title>\n'
    '</head>\n'
)


class ApplyAdSenseHeadPlaceholderTests(unittest.TestCase):
    """v1.1.3 의 head_script 빈 문자열 분기 + v1.1.5 의 page_url 분기."""

    def _call(self, tpl, page_url, **adsense):
        return Builder._apply_adsense_head_placeholder(
            _self_with(**adsense), tpl, page_url,
        )

    # ── v1.1.3: head_script 빈 문자열 → 5 페이지 모두 strip ──────

    def test_empty_head_script_strips_placeholder_line(self):
        out = self._call(_TPL, '/about/', head_script='')
        self.assertNotIn('{{ADSENSE_HEAD}}', out)
        self.assertNotIn('    \n', out)  # 빈 줄 잔재 없음

    def test_empty_head_script_strips_for_all_page_urls(self):
        # head_script 가 빈 문자열이면 exclude_urls 와 무관하게 5 페이지 모두 strip.
        for url in ('/about/', '/', '/blog/', '/404.html', '/search.php'):
            out = self._call(_TPL, url, head_script='')
            self.assertNotIn('{{ADSENSE_HEAD}}', out, f'page_url={url}')

    # ── 활성 (head_script 있고 exclude_urls 미매칭) → placeholder 유지 ──

    def test_active_keeps_placeholder_for_non_excluded(self):
        out = self._call(_TPL, '/about/', head_script='<s></s>')
        self.assertIn('{{ADSENSE_HEAD}}', out)

    def test_active_keeps_placeholder_when_exclude_urls_empty(self):
        out = self._call(_TPL, '/', head_script='<s></s>',
                         exclude_urls=frozenset())
        self.assertIn('{{ADSENSE_HEAD}}', out)

    # ── v1.1.5: exclude_urls 매칭 → placeholder 라인 strip ──

    def test_excluded_url_strips_placeholder_line(self):
        out = self._call(_TPL, '/404.html', head_script='<s></s>',
                         exclude_urls=frozenset({'/404.html'}))
        self.assertNotIn('{{ADSENSE_HEAD}}', out)
        # 라인 자체가 사라져 빈 줄 잔재 없음.
        self.assertNotIn('    \n', out)

    def test_unexcluded_url_keeps_placeholder_when_others_excluded(self):
        # exclude_urls 에 '/search.php' 가 있고 page_url='/about/' → 유지.
        out = self._call(_TPL, '/about/', head_script='<s></s>',
                         exclude_urls=frozenset({'/search.php', '/404.html'}))
        self.assertIn('{{ADSENSE_HEAD}}', out)

    def test_each_excluded_url_strips(self):
        excl = frozenset({'/404.html', '/search.php'})
        for url in ('/404.html', '/search.php'):
            out = self._call(_TPL, url, head_script='<s></s>',
                             exclude_urls=excl)
            self.assertNotIn('{{ADSENSE_HEAD}}', out, f'page_url={url}')
        for url in ('/about/', '/', '/blog/'):
            out = self._call(_TPL, url, head_script='<s></s>',
                             exclude_urls=excl)
            self.assertIn('{{ADSENSE_HEAD}}', out, f'page_url={url}')

    def test_url_matching_is_case_sensitive(self):
        # v1.1.5: URL 표준에 따라 대소문자 구분. '/About/' 와 '/about/' 는 다른 entry.
        out = self._call(_TPL, '/About/', head_script='<s></s>',
                         exclude_urls=frozenset({'/about/'}))
        # 대소문자 다르므로 매칭 안 됨 → placeholder 유지.
        self.assertIn('{{ADSENSE_HEAD}}', out)

    def test_url_matching_trailing_slash_strict(self):
        # '/about' 과 '/about/' 는 서로 다른 entry — 정확히 일치해야 매칭.
        out = self._call(_TPL, '/about/', head_script='<s></s>',
                         exclude_urls=frozenset({'/about'}))
        self.assertIn('{{ADSENSE_HEAD}}', out)  # trailing-slash 다르므로 미매칭.

    def test_individual_article_url_blocks_only_that_article(self):
        # v1.1.5 의 핵심 동기 — 개별 글 차단. '/clear/' 만 막고 다른 글은 유지.
        excl = frozenset({'/clear/'})
        out_clear = self._call(_TPL, '/clear/', head_script='<s></s>',
                               exclude_urls=excl)
        self.assertNotIn('{{ADSENSE_HEAD}}', out_clear)
        out_other = self._call(_TPL, '/picture-frame/', head_script='<s></s>',
                               exclude_urls=excl)
        self.assertIn('{{ADSENSE_HEAD}}', out_other)

    # ── v1.1.5: 호출 시 self._adsense_seen_urls 적재 검증 ──

    def test_seen_urls_populated_on_call(self):
        # 호출자 self 모킹에 set 이 살아있어야 한다.
        slf = _self_with(head_script='<s></s>')
        Builder._apply_adsense_head_placeholder(slf, _TPL, '/about/')
        Builder._apply_adsense_head_placeholder(slf, _TPL, '/clear/')
        self.assertEqual(slf._adsense_seen_urls, {'/about/', '/clear/'})

    def test_seen_urls_skip_empty_string(self):
        # 방어적 처리 — page_url='' 일 때 set 에 빈 문자열을 넣지 않음.
        slf = _self_with(head_script='<s></s>')
        Builder._apply_adsense_head_placeholder(slf, _TPL, '')
        self.assertEqual(slf._adsense_seen_urls, set())


if __name__ == '__main__':
    unittest.main()

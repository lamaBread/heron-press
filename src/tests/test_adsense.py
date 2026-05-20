"""scripts/builder Google AdSense 통합 단위 테스트 (v1.1.3·v1.1.4).

site.yaml `google_adsense:` 블록 파싱 + 5 페이지 head 의
`{{ADSENSE_HEAD}}` placeholder line-eating 헬퍼를 검증한다.

  - `_parse_adsense_config` : 두 문자열 필드(ads_txt·head_script)와
                              v1.1.4 의 exclude_pages 리스트 정규화
                              (str().strip().lower() + frozenset).
  - `_apply_adsense_head_placeholder` : head_script 활성/비활성과
                              exclude_pages 매칭에 따른 placeholder
                              라인 strip 여부 (v1.1.4 의 page_type 분기).

`_parse_adsense_config` 는 self 를 쓰지 않으므로 unbound 로 호출
(`ParseJsonLdConfigTests` 와 같은 정신 — Builder 인스턴스 불필요).
`_apply_adsense_head_placeholder` 는 `self.site.google_adsense` 만
참조하므로 SimpleNamespace 로 self 모킹.
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
        self.assertEqual(cfg.exclude_pages, frozenset())

    def test_non_dict_falls_back_to_default(self):
        for raw in (None, 'string', 0, [], 'abc'):
            cfg = self._parse(raw)
            self.assertEqual(cfg.ads_txt, '')
            self.assertEqual(cfg.head_script, '')
            self.assertEqual(cfg.exclude_pages, frozenset())

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


class ParseAdSenseExcludePagesTests(unittest.TestCase):
    """v1.1.4: exclude_pages 정규화 (str().strip().lower() + frozenset)."""

    def _parse(self, exclude_pages):
        return Builder._parse_adsense_config(None, {
            'exclude_pages': exclude_pages,
        })

    def test_missing_key_defaults_empty_frozenset(self):
        cfg = Builder._parse_adsense_config(None, {})
        self.assertEqual(cfg.exclude_pages, frozenset())

    def test_none_value_defaults_empty(self):
        # `exclude_pages:` 로 적되 값이 없는 경우 (yaml 에서 None).
        cfg = self._parse(None)
        self.assertEqual(cfg.exclude_pages, frozenset())

    def test_empty_list_is_empty_frozenset(self):
        cfg = self._parse([])
        self.assertEqual(cfg.exclude_pages, frozenset())

    def test_string_list_passthrough(self):
        cfg = self._parse(['article', 'home'])
        self.assertEqual(cfg.exclude_pages, frozenset({'article', 'home'}))

    def test_int_404_becomes_string(self):
        # yaml 의 `404` 는 int 로 파싱됨 — str() 캐스팅으로 흡수해야 한다.
        cfg = self._parse([404, 'search'])
        self.assertEqual(cfg.exclude_pages, frozenset({'404', 'search'}))

    def test_normalizes_case_and_whitespace(self):
        cfg = self._parse(['  Article  ', 'HOME', 'Search'])
        self.assertEqual(cfg.exclude_pages, frozenset({'article', 'home', 'search'}))

    def test_scalar_single_value_accepted(self):
        # `exclude_pages: 404` 처럼 단일 스칼라도 흡수.
        cfg = self._parse(404)
        self.assertEqual(cfg.exclude_pages, frozenset({'404'}))

    def test_scalar_single_string_accepted(self):
        cfg = self._parse('article')
        self.assertEqual(cfg.exclude_pages, frozenset({'article'}))

    def test_empty_string_and_none_items_skipped(self):
        cfg = self._parse(['article', '', None, '  ', 'home'])
        self.assertEqual(cfg.exclude_pages, frozenset({'article', 'home'}))

    def test_unknown_identifiers_preserved_for_forward_compat(self):
        # 모르는 식별자도 정규화 후 보존 — 헬퍼에서 매칭이 안 돼 자연 무시.
        # 빌더가 forward-compat 으로 spec 외 식별자를 거부하지 않는 정책.
        cfg = self._parse(['foobar', 'article'])
        self.assertEqual(cfg.exclude_pages, frozenset({'foobar', 'article'}))


# ════════════════════════════════════════════════════════════════
# placeholder line-eating 헬퍼 (_apply_adsense_head_placeholder)
# ════════════════════════════════════════════════════════════════

def _self_with(head_script='', exclude_pages=frozenset()):
    """`self.site.google_adsense` 만 참조하는 헬퍼용 self 모킹."""
    return SimpleNamespace(
        site=SimpleNamespace(
            google_adsense=AdSenseConfig(
                head_script=head_script,
                exclude_pages=exclude_pages,
            ),
        ),
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
    """v1.1.3 의 head_script 빈 문자열 분기 + v1.1.4 의 page_type 분기."""

    def _call(self, tpl, page_type, **adsense):
        return Builder._apply_adsense_head_placeholder(
            _self_with(**adsense), tpl, page_type,
        )

    # ── v1.1.3: head_script 빈 문자열 → 5 페이지 모두 strip ──────

    def test_empty_head_script_strips_placeholder_line(self):
        out = self._call(_TPL, 'article', head_script='')
        self.assertNotIn('{{ADSENSE_HEAD}}', out)
        self.assertNotIn('    \n', out)  # 빈 줄 잔재 없음

    def test_empty_head_script_strips_for_all_page_types(self):
        # head_script 가 빈 문자열이면 exclude_pages 와 무관하게 5 페이지 모두 strip.
        for pt in ('article', 'home', 'category', '404', 'search'):
            out = self._call(_TPL, pt, head_script='')
            self.assertNotIn('{{ADSENSE_HEAD}}', out, f'page_type={pt}')

    # ── 활성 (head_script 있고 exclude_pages 미매칭) → placeholder 유지 ──

    def test_active_keeps_placeholder_for_non_excluded(self):
        out = self._call(_TPL, 'article', head_script='<s></s>')
        self.assertIn('{{ADSENSE_HEAD}}', out)

    def test_active_keeps_placeholder_when_exclude_pages_empty(self):
        out = self._call(_TPL, 'home', head_script='<s></s>',
                         exclude_pages=frozenset())
        self.assertIn('{{ADSENSE_HEAD}}', out)

    # ── v1.1.4: exclude_pages 매칭 → placeholder 라인 strip ──

    def test_excluded_page_strips_placeholder_line(self):
        out = self._call(_TPL, '404', head_script='<s></s>',
                         exclude_pages=frozenset({'404'}))
        self.assertNotIn('{{ADSENSE_HEAD}}', out)
        # 라인 자체가 사라져 빈 줄 잔재 없음.
        self.assertNotIn('    \n', out)

    def test_unexcluded_page_keeps_placeholder_when_others_excluded(self):
        # exclude_pages 에 'search' 가 있고 page_type='article' → 유지.
        out = self._call(_TPL, 'article', head_script='<s></s>',
                         exclude_pages=frozenset({'search', '404'}))
        self.assertIn('{{ADSENSE_HEAD}}', out)

    def test_each_excluded_page_strips(self):
        excl = frozenset({'404', 'search'})
        for pt in ('404', 'search'):
            out = self._call(_TPL, pt, head_script='<s></s>',
                             exclude_pages=excl)
            self.assertNotIn('{{ADSENSE_HEAD}}', out, f'page_type={pt}')
        for pt in ('article', 'home', 'category'):
            out = self._call(_TPL, pt, head_script='<s></s>',
                             exclude_pages=excl)
            self.assertIn('{{ADSENSE_HEAD}}', out, f'page_type={pt}')

    def test_page_type_matching_is_case_insensitive(self):
        # exclude_pages 는 파서에서 lower-case 정규화. 호출자 page_type
        # 도 헬퍼가 .lower() 로 정규화하므로 매칭은 대소문자 무관.
        out = self._call(_TPL, 'ARTICLE', head_script='<s></s>',
                         exclude_pages=frozenset({'article'}))
        self.assertNotIn('{{ADSENSE_HEAD}}', out)

    def test_unknown_page_type_natural_no_op(self):
        # 모르는 식별자가 page_type 으로 와도 빌드는 통과 — 매칭이 안 돼
        # 그냥 활성 경로(placeholder 유지). forward-compat.
        out = self._call(_TPL, 'unknown_kind', head_script='<s></s>',
                         exclude_pages=frozenset({'404'}))
        self.assertIn('{{ADSENSE_HEAD}}', out)


if __name__ == '__main__':
    unittest.main()

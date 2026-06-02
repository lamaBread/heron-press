"""scripts/report.BuildReport 단위 테스트 (v0.6.0).

issue / warning 등록, count, render() 정렬, abort() 행동.
"""
import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.report import BuildReport, ReportEntry, abort  # noqa: E402
from scripts import i18n  # noqa: E402


class ReportTests(unittest.TestCase):

    def setUp(self):
        # v1.9.2: render()/render_markdown() 가 헤딩/요약을 전역 i18n.t() 로
        # 조회한다 — 다른 테스트가 도구 언어를 바꿔 둘 수 있으므로 ko(정본)로
        # 고정해 이 클래스의 한국어 단언이 실행 순서와 무관히 성립하게 한다.
        i18n.init('ko')

    def test_empty_renders_no_issue_message(self):
        r = BuildReport()
        buf = io.StringIO()
        r.render(out=buf)
        self.assertIn('보완 필요', buf.getvalue())
        self.assertEqual(r.issue_count(), 0)
        self.assertEqual(r.warning_count(), 0)

    def test_issue_added(self):
        r = BuildReport()
        r.issue('article', 'hello', 'description missing')
        self.assertEqual(r.issue_count(), 1)
        self.assertEqual(r.warning_count(), 0)

    def test_warning_added(self):
        r = BuildReport()
        r.warning('site', '', 'non-ascii folder')
        self.assertEqual(r.warning_count(), 1)
        self.assertEqual(r.issue_count(), 0)

    def test_render_groups_by_target(self):
        r = BuildReport()
        r.issue('article', 'a', 'm1')
        r.issue('article', 'a', 'm2')
        r.issue('article', 'b', 'm3')
        buf = io.StringIO()
        r.render(out=buf)
        text = buf.getvalue()
        # [article] a 헤더 다음에 m1, m2 가 같은 그룹으로
        self.assertIn('[article] a', text)
        self.assertIn('[article] b', text)
        # m1 과 m2 가 같은 헤더 아래
        i_header = text.index('[article] a')
        i_m1 = text.index('m1', i_header)
        i_m2 = text.index('m2', i_header)
        i_b = text.index('[article] b')
        self.assertLess(i_m1, i_b)
        self.assertLess(i_m2, i_b)

    def test_render_separates_issue_and_warning_sections(self):
        r = BuildReport()
        r.issue('article', 'a', 'i1')
        r.warning('site', '', 'w1')
        buf = io.StringIO()
        r.render(out=buf)
        text = buf.getvalue()
        # issues 섹션이 warnings 섹션보다 먼저 등장
        self.assertLess(text.index('보완이 필요'), text.index('살펴볼'))

    def test_summary_line_at_end(self):
        r = BuildReport()
        r.issue('article', 'a', 'm')
        r.warning('site', '', 'w')
        buf = io.StringIO()
        r.render(out=buf)
        text = buf.getvalue()
        self.assertIn('보완 필요 1건', text)
        self.assertIn('살펴볼 사항 1건', text)

    def test_location_path_rendered(self):
        r = BuildReport()
        r.issue('article', 'a', 'm', location=Path('meta.yaml'))
        buf = io.StringIO()
        r.render(out=buf)
        self.assertIn('meta.yaml', buf.getvalue())


class AbortTests(unittest.TestCase):

    def test_abort_exits_nonzero(self):
        with self.assertRaises(SystemExit) as ctx:
            abort('system failure test')
        self.assertEqual(ctx.exception.code, 1)


if __name__ == '__main__':
    unittest.main()

"""admin 미리보기 ↔ 빌드 본문 패리티 게이트 (v1.1.0 신설).

admin.php 실시간 미리보기는 별도 마크다운 엔진을 두지 않고
`src/admin/render_one.py` 가 빌더와 *같은* `scripts.markdown` 경로를
재사용한다는 게 v1.1.0 의 핵심 계약 (설계 원칙 6·9 — 파서 단일화).
이 테스트는 그 계약을 잠근다: render_one.py 의 출력이 빌더가 글 본문을
조립할 때 쓰는 식과 **byte 단위로 동일** 함을 검증한다. 누군가 나중에
render_one 을 다른 엔진/경로로 바꾸면 (미리보기≠산출물) 여기서 깨진다.

빌더의 본문 조립 (scripts/builder.py `_render_articles`) 기준식:
    .md   → resolve_section_markers(render_article_md(t, slug, dir).html, title)
    .html → process_html(t, slug, dir).html
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1]          # <verdir>/src
_ROOT = _SRC.parent                                  # <verdir>
_RENDER_ONE = _SRC / 'admin' / 'render_one.py'
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from scripts.markdown import (                        # noqa: E402
    render_article_md, process_html, resolve_section_markers,
    parse_php_globals,
)
from scripts.yaml_parser import yaml_load              # noqa: E402


def _site_php_globals() -> dict:
    """render_one.py 와 *같은* <verdir>/site.yaml php_globals.

    v1.1.1: 미리보기 본문 충실도 = 빌더와 같은 서명 변수 치환. 양쪽이
    동일 site.yaml 에서 읽으므로 패리티가 구성적으로 보장된다.
    """
    sy = _ROOT / 'user' / 'site.yaml'
    if not sy.is_file():
        return {}
    try:
        return parse_php_globals(
            (yaml_load(sy.read_text(encoding='utf-8')) or {})
            .get('php_globals'))
    except Exception:  # noqa: BLE001
        return {}


def _build_body(text: str, slug: str, title: str, src_dir: Path,
                ext: str) -> str:
    """빌더 _render_articles 와 1:1 동일한 본문 식."""
    g = _site_php_globals()
    if ext == 'html':
        return process_html(text, slug, src_dir, g).html
    rr = render_article_md(text, slug, src_dir, g)
    return resolve_section_markers(rr.html, title)


def _run_render_one(src_dir: Path, ext: str, text: str) -> str:
    proc = subprocess.run(
        [sys.executable, str(_RENDER_ONE), str(src_dir), '--ext', ext],
        input=text.encode('utf-8'),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=str(_ROOT),
    )
    if proc.returncode != 0:
        raise AssertionError(
            f'render_one.py exit {proc.returncode}: '
            f'{proc.stdout.decode("utf-8", "replace")}'
            f'{proc.stderr.decode("utf-8", "replace")}')
    return proc.stdout.decode('utf-8')


class RenderOneParity(unittest.TestCase):

    def _case(self, folder_name: str, slug: str, title: str,
              ext: str, text: str):
        with tempfile.TemporaryDirectory() as td:
            src_dir = Path(td) / folder_name
            src_dir.mkdir(parents=True)
            (src_dir / 'meta.yaml').write_text(
                f"# meta.yaml\nslug: {slug}\ntitle: {title}\n"
                f"date: 2026-05-19\n", encoding='utf-8')
            expected = _build_body(text, slug, title, src_dir, ext)
            actual = _run_render_one(src_dir, ext, text)
            self.assertEqual(actual, expected)

    def test_md_with_custom_syntax_and_sections(self):
        # imgBox + 섹션 마커 + 자산 경로(slug) 재작성을 모두 통과시킨다.
        text = (
            "본문 시작 **굵게**\n\n"
            "![[캡션 텍스트]](imgs/photo.jpg) {사진 설명}\n\n"
            "===둘째 절===\n\n"
            "절 안의 [링크](sub/page) 와 코드 `x`.\n\n"
            "======\n\n"
            "마커 밖 문단.\n"
        )
        self._case('글쓰기-folder', 'on-writing', '글쓰기', 'md', text)

    def test_md_minimal(self):
        self._case('p', 'p-slug', 'T', 'md', "# H1\n\n단락.\n")

    def test_html_php_simulation(self):
        # content.html 경로: <?php imgBox(...) ?> 시뮬레이션 + asset 재작성.
        text = ('<p>HTML 본문</p>\n'
                '<?php imgBox("imgs/a.png", "설명", "alt") ?>\n'
                '<img src="local/b.jpg">\n')
        self._case('htmlpost', 'html-post', 'HtmlPost', 'html', text)

    def test_non_ascii_slug_and_dir(self):
        # 비ASCII slug·폴더명에서도 파이프라인이 동일해야 한다.
        self._case('연구-노트', 'be94-note', '연구 노트', 'md',
                   "선행 문단.\n\n===섹션===\n\n내용.\n")


if __name__ == '__main__':
    unittest.main()

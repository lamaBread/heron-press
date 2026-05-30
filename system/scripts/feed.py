"""RSS / Atom 피드 생성기 (v0.5.3 신설).

설계 요약:
  - 추상 모델은 Atom 1.0 기반 (`FeedEntry` / `FeedDocument` dataclass).
    Atom 이 RSS 2.0 의 사실상 슈퍼셋이라 — RSS 의 모든 필드는 Atom 으로
    표현 가능하지만 그 반대는 아님 — 한 모델에서 두 직렬화 (Atom / RSS)
    를 동시에 만들 수 있다.
  - `render_atom(doc)` / `render_rss(doc)` 가 각각 utf-8 XML 문자열 반환.
    외부 의존성 없음 (stdlib `xml.sax.saxutils.escape` 만).
  - 빌드 시 호출자 (builder.Builder) 가 `dist/feed.atom` + `dist/feed.rss`
    두 파일을 같은 글 목록으로 생성. 두 파일은 시점·내용이 동일하고
    *직렬화 포맷만* 다르다.

v0.5.5 변경 — 본문 ↔ 메타데이터 분리 원칙:
  - `FeedEntry.summary` 의 폴백 소스를 본문 첫 단락에서 떼냄. 이제 entry 의
    summary 는 builder 가 `article_render_meta[slug]['summary']` 로 넘긴 값을
    그대로 쓰며, 그 값은 author 가 `meta.yaml` 의 `seo.description` 에 직접
    적은 값에서만 유래한다. description 이 부재한 글은 summary 도 자연스럽게
    누락 (`<summary>` / `<description>` 태그 자체가 출력되지 않음).
    Atom 은 `<content>` 가 없어도 summary 를 강제하지 않으며 (RFC 4287 §
    4.1.3.3 의 예외 조항), RSS 2.0 도 `<description>` 을 필수로 요구하지
    않는다 (item 은 title 또는 description 중 하나만 있어도 된다).

포함 정책:
  - non-noindex 글만. `meta.yaml` 의 `noindex: true` 는 sitemap 과 동일하게 제외.
  - `Articles/meta.yaml` 의 `excludes_categories` (= 홈에서 빠지는 카테고리)
    도 피드에서 제외. 사용자가 "홈에 안 띄우려는" 글은 RSS 구독자에게도
    안 띄우는 게 자연스러움. About 처럼 정적 페이지가 피드에 잡혀
    구독자에게 노출되는 사고를 막는다.
  - 최신 N 개 (기본 20). 너무 많아도 RSS 리더의 부담만 늘고 가치는 낮다.

날짜 정책:
  - meta.yaml 의 `date` / `updated` 는 YYYY-MM-DD 만 — 시각 정보는 없다.
    Atom 의 `published`/`updated` 는 ISO 8601 (`T00:00:00Z`) 로 직렬화.
    RSS 의 `pubDate` 는 RFC 822 (`Wed, 07 May 2026 00:00:00 +0000`) 로 직렬화.
    "00:00:00 UTC" 로 통일해 결정성 (= 같은 입력 → 같은 출력) 을 보장.
  - 피드 자체의 `updated` (Atom) / `lastBuildDate` (RSS) 는 *글 entry 의
    가장 최신 lastmod* 를 사용. 빌드 시각이 아니라 콘텐츠 시각이라야 빌드를
    무한 반복해도 산출물이 동일하다.

ID 정책:
  - entry id 는 글의 절대 URL (`https://your-domain.com/{slug}/`). 피드 ID 는
    사이트 base_url. 안정적이고 영구적인 식별자 — slug 가 살아있는 한 같은
    글에 같은 id 가 부여된다.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from xml.sax.saxutils import escape as _xml_escape


# ════════════════════════════════════════════════════════════════
# 추상 모델
# ════════════════════════════════════════════════════════════════

@dataclass
class FeedEntry:
    """피드의 한 항목 — 한 글에 대응.

    title       — 글 제목.
    link        — 글의 절대 URL.
    entry_id    — 안정적이고 영구적인 식별자. 보통 link 와 동일.
    published   — 최초 작성일 (YYYY-MM-DD).
    updated     — 마지막 수정일 (YYYY-MM-DD). 없으면 published 와 동일.
    summary     — 짧은 요약 (plain text). v0.5.5 부터 author 가
                  `meta.yaml` 의 `seo.description` 에 직접 적은 값에서만 유래
                  한다 (본문 폴백 없음). 비어 있으면 `<summary>` / `<description>`
                  태그 자체를 출력하지 않는다.
    author      — 글 단위 저자. 없으면 피드의 default_author.
    categories  — 글의 카테고리 + tags (Atom <category term=...>, RSS <category>).
    """
    title: str
    link: str
    entry_id: str
    published: str
    updated: str
    summary: str = ''
    author: Optional[str] = None
    categories: list = field(default_factory=list)


@dataclass
class FeedDocument:
    """피드 문서 — 채널 메타데이터 + entry 목록.

    title        — 피드 제목 (보통 사이트 이름).
    subtitle     — 부제 / 채널 설명.
    home_link    — 사이트 홈 URL (HTML).
    atom_self    — 피드 자신의 atom URL (`<link rel='self'>` 용).
    rss_self     — 피드 자신의 rss URL.
    doc_id       — 피드 문서 ID. 보통 home_link.
    updated      — 피드 자체의 lastmod (entry 중 가장 최신).
    language     — 피드 언어 (예: 'ko').
    default_author — entry 가 author 를 지정하지 않을 때 사용.
    generator     — `<generator>` 태그.
    entries       — FeedEntry 목록. 호출 측에서 이미 최신순으로 정렬해 넘긴다.
    """
    title: str
    subtitle: str
    home_link: str
    atom_self: str
    rss_self: str
    doc_id: str
    updated: str
    language: str
    default_author: str
    generator: str
    entries: list = field(default_factory=list)


# ════════════════════════════════════════════════════════════════
# 날짜 변환 — YYYY-MM-DD → ISO 8601 / RFC 822
# ════════════════════════════════════════════════════════════════

def _to_iso_z(date_str: str) -> str:
    """YYYY-MM-DD → 'YYYY-MM-DDT00:00:00Z' (Atom)."""
    return f'{date_str}T00:00:00Z'


_RFC822_DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
_RFC822_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def _to_rfc822(date_str: str) -> str:
    """YYYY-MM-DD → 'Wed, 07 May 2026 00:00:00 +0000' (RSS)."""
    dt = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    return (
        f'{_RFC822_DAYS[dt.weekday()]}, '
        f'{dt.day:02d} {_RFC822_MONTHS[dt.month - 1]} {dt.year} '
        f'00:00:00 +0000'
    )


def _xa(val) -> str:
    """attribute 값 escape — `"` 까지 처리."""
    return _xml_escape(str(val or ''), {'"': '&quot;'})


def _xt(val) -> str:
    """text content escape."""
    return _xml_escape(str(val or ''))


# ════════════════════════════════════════════════════════════════
# Atom 1.0
# ════════════════════════════════════════════════════════════════

def render_atom(doc: FeedDocument) -> str:
    """FeedDocument → Atom 1.0 XML 문자열."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="{_xa(doc.language)}">',
        f'  <title>{_xt(doc.title)}</title>',
    ]
    if doc.subtitle:
        lines.append(f'  <subtitle>{_xt(doc.subtitle)}</subtitle>')
    lines.append(
        f'  <link rel="self" type="application/atom+xml" '
        f'href="{_xa(doc.atom_self)}"/>'
    )
    lines.append(
        f'  <link rel="alternate" type="text/html" '
        f'href="{_xa(doc.home_link)}"/>'
    )
    lines.append(f'  <id>{_xt(doc.doc_id)}</id>')
    lines.append(f'  <updated>{_xt(_to_iso_z(doc.updated))}</updated>')
    if doc.generator:
        lines.append(f'  <generator>{_xt(doc.generator)}</generator>')
    if doc.default_author:
        lines.append('  <author>')
        lines.append(f'    <name>{_xt(doc.default_author)}</name>')
        lines.append('  </author>')

    for e in doc.entries:
        lines.append('  <entry>')
        lines.append(f'    <title>{_xt(e.title)}</title>')
        lines.append(
            f'    <link rel="alternate" type="text/html" '
            f'href="{_xa(e.link)}"/>'
        )
        lines.append(f'    <id>{_xt(e.entry_id)}</id>')
        lines.append(f'    <published>{_xt(_to_iso_z(e.published))}</published>')
        lines.append(f'    <updated>{_xt(_to_iso_z(e.updated))}</updated>')
        if e.author and e.author != doc.default_author:
            lines.append('    <author>')
            lines.append(f'      <name>{_xt(e.author)}</name>')
            lines.append('    </author>')
        for cat in e.categories:
            lines.append(f'    <category term="{_xa(cat)}"/>')
        if e.summary:
            lines.append(f'    <summary>{_xt(e.summary)}</summary>')
        lines.append('  </entry>')

    lines.append('</feed>')
    return '\n'.join(lines) + '\n'


# ════════════════════════════════════════════════════════════════
# RSS 2.0
# ════════════════════════════════════════════════════════════════

def render_rss(doc: FeedDocument) -> str:
    """FeedDocument → RSS 2.0 XML 문자열."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        '  <channel>',
        f'    <title>{_xt(doc.title)}</title>',
        f'    <link>{_xt(doc.home_link)}</link>',
        f'    <description>{_xt(doc.subtitle or doc.title)}</description>',
        f'    <language>{_xt(doc.language)}</language>',
        f'    <lastBuildDate>{_xt(_to_rfc822(doc.updated))}</lastBuildDate>',
    ]
    if doc.generator:
        lines.append(f'    <generator>{_xt(doc.generator)}</generator>')
    lines.append(
        f'    <atom:link href="{_xa(doc.rss_self)}" rel="self" '
        f'type="application/rss+xml"/>'
    )

    for e in doc.entries:
        lines.append('    <item>')
        lines.append(f'      <title>{_xt(e.title)}</title>')
        lines.append(f'      <link>{_xt(e.link)}</link>')
        lines.append(
            f'      <guid isPermaLink="true">{_xt(e.entry_id)}</guid>'
        )
        lines.append(f'      <pubDate>{_xt(_to_rfc822(e.published))}</pubDate>')
        # RSS 에는 author 가 email 형식이라 (RFC 4287 대비 좁음) — 작성자
        # 이름만 있는 현재 모델에서는 `<dc:creator>` 가 더 적합하지만, namespace
        # 추가 비용 대비 가치가 낮아 생략. Atom 쪽에는 정상 출력됨.
        for cat in e.categories:
            lines.append(f'      <category>{_xt(cat)}</category>')
        if e.summary:
            lines.append(
                f'      <description>{_xt(e.summary)}</description>'
            )
        lines.append('    </item>')

    lines.append('  </channel>')
    lines.append('</rss>')
    return '\n'.join(lines) + '\n'


# ════════════════════════════════════════════════════════════════
# Builder helper — articles → FeedDocument
# ════════════════════════════════════════════════════════════════

DEFAULT_MAX_ENTRIES = 20


def _article_lastmod(article) -> str:
    return article.meta.updated or article.meta.date


def build_feed_document(
    articles,
    site,
    home_meta,
    article_render_meta,
    category_path_for_article,
    *,
    max_entries: int = DEFAULT_MAX_ENTRIES,
    generator: str,
) -> Optional[FeedDocument]:
    """Builder 의 상태를 모아 FeedDocument 를 만든다.

    매개변수는 builder.Builder 의 self.articles / self.site / self.home_meta
    / self.article_render_meta / 톱레벨 카테고리 폴더명을 반환하는 콜백.

    빌드 시 호출자가 한 번 호출해 doc 을 받은 다음, render_atom(doc) /
    render_rss(doc) 로 두 직렬화를 모두 만든다. 두 파일이 같은 entry 목록을
    공유함을 보장.

    포함되는 entry 가 0 개면 None 반환 — 호출자가 빈 파일 작성을 건너뛸 수 있음.
    """
    base_url = site.base_url.rstrip('/')
    exclude_top = set(home_meta.excludes_categories)

    visible = [
        a for a in articles
        if not a.meta.noindex
        and not (a.category_path and a.category_path[0] in exclude_top)
    ]

    if not visible:
        return None

    visible.sort(
        key=lambda a: (_article_lastmod(a), a.meta.date, a.meta.slug),
        reverse=True,
    )
    visible = visible[:max_entries]

    entries = []
    for article in visible:
        m = article.meta
        rmeta = article_render_meta.get(m.slug, {})
        summary = rmeta.get('summary', '')
        link = f'{base_url}/{m.slug}/'

        # categories: 톱레벨 카테고리 폴더명 + tags (작성자 지정).
        cats = []
        top_folder = category_path_for_article(article)
        if top_folder:
            cats.append(top_folder)
        for tag in m.tags:
            if tag and tag not in cats:
                cats.append(tag)

        author = m.seo.author or site.default_author

        entries.append(FeedEntry(
            title=m.title,
            link=link,
            entry_id=link,
            published=m.date,
            updated=m.updated or m.date,
            summary=summary,
            author=author,
            categories=cats,
        ))

    feed_updated = max(e.updated for e in entries)

    return FeedDocument(
        title=site.name,
        subtitle=site.name,
        home_link=f'{base_url}/',
        atom_self=f'{base_url}/feed.atom',
        rss_self=f'{base_url}/feed.rss',
        doc_id=f'{base_url}/',
        updated=feed_updated,
        language=site.lang,
        default_author=site.default_author,
        generator=generator,
        entries=entries,
    )

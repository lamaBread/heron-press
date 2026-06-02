"""빌드 시 이미지 자동 최적화 (v0.5.1 신설).

v0.5.0 까지의 빌더는 원본 raster 이미지 (jpg/jpeg/png/gif) 를 그대로
`dist/src/{slug}/` 또는 `dist/assets/` 로 복사했다. v0.5.1 에서 SEO 영향
(LCP, Core Web Vitals, Google 모바일 검색 랭킹) 을 고려해 빌드 시 모든
raster 이미지를 WebP 로 변환하고 다중 해상도 변종을 생성한다. HTML 의
`<img>` 태그는 후처리 단계에서 WebP src + srcset + `loading="lazy"` 로
치환된다.

v0.5.2 부터 글 자산의 출력 위치가 `dist/src/{slug}/` → `dist/{slug}/`
(글 index.html 과 같은 폴더) 로 일원화. 이 모듈의 동작은 동일 — 호출자
(builder._sync_assets / _copy_site_assets) 가 새 dst_dir / url_prefix 를
넘기는 것만 다르다. 사이트 공용 이미지의 경로는 그대로 (`dist/assets/`).

v1.5.1 변경 — 안정화 (동작·산출물 불변):
  - `_split_url` / `_build_srcset` → `split_url` / `build_srcset` 로 공개화.
    builder 가 갤러리 썸네일 조립에서 이 둘을 모듈 경계 너머로 import 하므로
    (밑줄 접두 = 모듈 내부 전용 관례와 충돌), 모듈 공용 API 임을 이름으로
    드러낸다. `split_url` docstring 의 반환 튜플 표기도 실제 (4-튜플) 와
    일치하도록 정정.

외부 의존성:
  Pillow (PIL fork). v0.4.1 의 "빌드 PHP 의존 제거" 와 같은 보수적 의존성
  정책에도 불구하고, WebP 인코딩과 정확한 리샘플링은 stdlib 만으로는
  현실적으로 구현 불가. 의존성을 도입한 사유:
    1. WebP 는 SEO 직접 영향 (Google PageSpeed Insights / Lighthouse 가
       Modern image format 미사용을 명시적으로 감점).
    2. 다중 해상도 (`srcset`) 가 없으면 모바일에서 PC 사이즈 이미지를
       그대로 다운로드 — LCP 가 1~3 초 단위로 늘어남.
    3. 직접 PNG/JPEG 디코드 + 리샘플 + WebP 인코드는 수천 줄 코드.
  Pillow 는 PSF 라이선스 (BSD 호환), 거의 모든 Linux 배포판 / pip 에 기본
  포함되어 있어 도입 비용이 최소.

설계:
  - **SVG 는 건드리지 않는다** (벡터 — 해상도 무관). loading="lazy" 만 부착.
  - **외부 URL (http://, https://, //) 도 건드리지 않는다.** loading="lazy" 만 부착.
  - raster 이미지 (.jpg .jpeg .png .gif) 는 `{stem}-{w}.webp` 변종을 생성.
    원본 파일은 dist 로 복사하지 않음 (HTML 도 webp src 로 치환되므로).
  - 변종 너비는 site.yaml 의 `images.widths` (기본 [400, 800, 1600]). 원본
    width 보다 큰 변종은 만들지 않는다 (업스케일링 무의미). 원본보다 작은
    변종이 하나도 없으면 (= 원본이 400 미만이면) 원본 width 변종만 생성.
  - HTML 후처리 — `<img src="..." alt="...">` 를 `<img src="...-800.webp"
    srcset="...-400.webp 400w, ...-800.webp 800w, ...-1600.webp 1600w"
    sizes="..." loading="lazy" alt="...">` 로 치환.

캐시:
  variant 의 mtime 이 원본 mtime 보다 같거나 크면 재변환 건너뜀.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import re

from . import i18n  # v1.9.4: 인코딩 실패 메시지를 도구 언어로 (전역 t()).

try:
    from PIL import Image
    _HAS_PIL = True
except ImportError:
    Image = None
    _HAS_PIL = False


# ════════════════════════════════════════════════════════════════
# Configuration
# ════════════════════════════════════════════════════════════════

@dataclass
class ImageConfig:
    """site.yaml 의 `images:` 블록 (v0.5.1).

    enabled         — 이미지 최적화 전체 토글. False 면 모든 raster 이미지를
                      v0.5.0 처럼 그대로 복사하고 HTML 후처리도 안 함.
                      단 `lazy_loading` 은 별도 토글이라 enabled=False 여도
                      loading="lazy" 부착은 가능.
    widths          — 생성할 변종 너비 (px) 목록. 원본 width 이하인 것만 실제로
                      생성. 기본 [400, 800, 1600].
    max_width       — 원본이 이보다 크면 다운스케일. 0 또는 None 이면 안 함.
                      widths 의 max 와 동기화하면 충분하지만 명시적 옵션으로 둠.
    quality         — WebP 인코더 quality (0~100). 기본 85 (Google 권장).
    lazy_loading    — 모든 <img> 에 loading="lazy" 자동 부착. enabled=False
                      여도 이 옵션은 독립적으로 동작 (SEO 효과 따로).
    default_sizes   — srcset 과 짝이 되는 sizes 속성 디폴트. 기본
                      "(max-width: 800px) 100vw, 800px" — 모바일에선 viewport,
                      데스크탑에선 800px 가정 (the site main column 너비).
    """
    enabled: bool = True
    widths: list = field(default_factory=lambda: [400, 800, 1600])
    max_width: Optional[int] = 1600
    quality: int = 85
    lazy_loading: bool = True
    default_sizes: str = "(max-width: 800px) 100vw, 800px"


# raster 이미지 확장자 (WebP 변환 대상).
RASTER_EXTS = {'.jpg', '.jpeg', '.png', '.gif'}

# 이미지 전체 (HTML 후처리에서 인식할 확장자). SVG / WebP 는 변환하지 않지만
# loading="lazy" 부착 대상은 됨.
ALL_IMAGE_EXTS = RASTER_EXTS | {'.webp', '.svg'}


# ════════════════════════════════════════════════════════════════
# Image variant generation
# ════════════════════════════════════════════════════════════════

@dataclass
class VariantSet:
    """한 원본 이미지의 변종 정보. HTML 후처리에서 srcset 을 구성할 때 참조.

    primary_width  — `<img src=...>` 가 가리킬 기본 변종 너비. 원본 width
                     이하인 widths 중 가장 큰 값. 모바일 친화적으로 800 부근을
                     선호하지만, 원본이 작으면 그대로 사용.
    widths         — 생성된 변종 너비 목록 (오름차순).
    """
    primary_width: int
    widths: list


def _select_widths(orig_width: int, configured: list) -> list:
    """원본 width 와 configured widths 로부터 실제 생성할 변종 width 목록 결정.

    규칙:
      1. configured 중 orig_width 이하인 것만.
      2. 그게 비어 있으면 (= 원본이 모든 configured width 보다 작음) → [orig_width] 단일.
      3. 항상 정렬 + 중복 제거.
    """
    sel = sorted({w for w in configured if w <= orig_width})
    if not sel:
        return [orig_width]
    # 원본 width 자체가 configured 에 없고, 가장 큰 configured 변종이 원본보다
    # 작으면 — 원본 width 변종도 하나 추가 (시각 품질 최대값 보존).
    if sel[-1] < orig_width:
        # 단, sel[-1] 와 orig_width 차이가 10% 미만이면 (eg. 800 vs 820) 추가
        # 하지 않음 — 의미 없는 중복 변종 방지.
        if orig_width >= int(sel[-1] * 1.1):
            sel.append(orig_width)
    return sel


def _primary_width(widths: list, default_target: int = 800) -> int:
    """srcset 의 1x 디스플레이를 위해 `<img src>` 가 가리킬 width 선택.

    widths 중 default_target 에 가장 가까운 값. 800px 가 the site 의
    main column 표시 너비라 데스크탑/노트북에선 그 정도가 적당.
    """
    return min(widths, key=lambda w: (abs(w - default_target), -w))


def optimize_image(
    src: Path,
    dst_dir: Path,
    *,
    config: ImageConfig,
) -> tuple[Optional[VariantSet], Optional[str]]:
    """원본 raster 이미지 한 장을 dst_dir 에 WebP 변종들로 변환.

    원본은 dst_dir 에 복사하지 않는다 (HTML 후처리 가 webp src 로 바꾸므로).
    SVG / WebP 원본은 이 함수의 대상이 아니다 (호출 측에서 raster 만 넘김).

    캐시: dst_dir 의 각 변종이 src 보다 새것이면 재인코딩 건너뜀.

    반환: `(variants, error)` 튜플.
      - 성공:        (VariantSet, None)
      - 인코딩 실패: (None, '사람이 읽을 에러 메시지')
      - Pillow 미설치: (None, None) — 호출자가 abort() 로 먼저 처리하므로 도달 X.

    호출자는 error 가 있으면 BuildReport.warning 으로 라우팅하고, 원본을
    그대로 복사 (폴백) 한다. 산출물은 정상 — 사용자가 한 번 확인할 가치만 있음.
    """
    if not _HAS_PIL:
        return None, None

    try:
        with Image.open(src) as im:
            # GIF/PNG 의 알파/팔레트 모드를 WebP 가 처리할 수 있는 모드로 변환.
            if im.mode in ('P', 'LA'):
                im = im.convert('RGBA')
            elif im.mode == 'CMYK':
                im = im.convert('RGB')

            orig_w, orig_h = im.size
            widths = _select_widths(orig_w, config.widths)

            # max_width 가 widths 의 max 보다 작으면 추가 캡 적용.
            if config.max_width and config.max_width > 0:
                widths = [w for w in widths if w <= config.max_width]
                if not widths:
                    widths = [min(orig_w, config.max_width)]

            dst_dir.mkdir(parents=True, exist_ok=True)
            src_mtime = src.stat().st_mtime
            stem = src.stem

            for w in widths:
                out_path = dst_dir / f'{stem}-{w}.webp'
                # 캐시 — variant 가 원본보다 새것이면 건너뜀.
                if (out_path.exists()
                        and out_path.stat().st_mtime >= src_mtime):
                    continue
                # 비율 유지하며 width 에 맞춰 리샘플.
                if w == orig_w:
                    resized = im
                else:
                    h = max(1, round(orig_h * w / orig_w))
                    resized = im.resize((w, h), Image.LANCZOS)
                # 알파 채널이 있으면 WebP 도 알파를 보존 (RGB 만 있으면 RGB 로).
                save_kwargs = {'quality': config.quality, 'method': 6}
                if resized.mode in ('RGBA', 'LA'):
                    save_kwargs['lossless'] = False
                resized.save(out_path, 'WEBP', **save_kwargs)

            return VariantSet(
                primary_width=_primary_width(widths),
                widths=widths,
            ), None
    except Exception as e:
        # 인코딩 실패는 die 가 아닌 None — 호출 측에서 원본 복사로 폴백.
        # 워닝 메시지는 호출자가 BuildReport 로 라우팅한다 (v0.6.x 통합 리포트).
        return None, i18n.t(
            'build.warn.image_optimize_failed', name=src.name, error=e)


# ════════════════════════════════════════════════════════════════
# HTML post-processing — <img> 태그 치환
# ════════════════════════════════════════════════════════════════

# <img ... > 태그 자체를 통째로 매칭. self-closing 형태도 포함.
# multiline 안에서도 매칭되도록 DOTALL.
_IMG_TAG_RE = re.compile(r'<img\b([^>]*?)/?>', re.IGNORECASE | re.DOTALL)

# 한 속성 (`name="value"` 또는 `name='value'` 또는 `name=value` 또는 `name`).
_ATTR_RE = re.compile(
    r'''([a-zA-Z_:][\w:.-]*)        # 이름
        (?:                         # 선택적 값
          \s*=\s*
          (?:
            "([^"]*)"               # 큰따옴표
            |'([^']*)'              # 작은따옴표
            |([^\s"'=<>`]+)         # unquoted
          )
        )?
    ''',
    re.VERBOSE,
)


def _parse_img_attrs(attrs_str: str) -> list:
    """`<img ...>` 의 속성 문자열을 [(name, value_or_None, quote_char), ...] 로 파싱.

    순서 보존 + 따옴표 종류 보존. 후처리 후 다시 같은 양식으로 직렬화.
    """
    out = []
    for m in _ATTR_RE.finditer(attrs_str):
        name = m.group(1).lower()
        if m.group(2) is not None:
            out.append((name, m.group(2), '"'))
        elif m.group(3) is not None:
            out.append((name, m.group(3), "'"))
        elif m.group(4) is not None:
            out.append((name, m.group(4), ''))
        else:
            out.append((name, None, ''))
    return out


def _serialize_img(attrs: list) -> str:
    parts = []
    for name, value, q in attrs:
        if value is None:
            parts.append(name)
        elif q == '':
            parts.append(f'{name}={value}')
        else:
            parts.append(f'{name}={q}{value}{q}')
    if not parts:
        return '<img>'
    return '<img ' + ' '.join(parts) + '>'


def _is_external_url(url: str) -> bool:
    return url.startswith(('http://', 'https://', '//', 'data:'))


def split_url(url: str) -> tuple:
    """URL → (dir_part, stem, ext, tail).

    tail 은 쿼리/프래그먼트 (`?...#...`) 를 합친 꼬리 — 변종 webp 파일명을
    조립한 뒤 원래 쿼리/프래그먼트를 그대로 붙이기 위해 분리해 둔다.
    builder 의 갤러리 썸네일 조립이 같은 분해를 재사용한다 (모듈 공용 API).
    """
    # 쿼리/프래그먼트는 분리.
    base, sep, rest = url.partition('?')
    query = sep + rest if sep else ''
    base, sep2, frag = base.partition('#')
    fragment = sep2 + frag if sep2 else ''

    p = Path(base)
    return (
        str(p.parent).replace('\\', '/'),
        p.stem,
        p.suffix.lower(),
        query + fragment,
    )


def build_srcset(dir_part: str, stem: str, widths: list) -> str:
    """srcset 속성값. `{dir}/{stem}-{w}.webp {w}w, ...`"""
    items = []
    prefix = '' if dir_part in ('.', '') else dir_part + '/'
    for w in widths:
        items.append(f'{prefix}{stem}-{w}.webp {w}w')
    return ', '.join(items)


def transform_img_tags(
    html: str,
    *,
    variant_lookup,
    config: ImageConfig,
) -> str:
    """HTML 의 모든 `<img>` 를 후처리.

    variant_lookup: callable(src_url: str) -> Optional[VariantSet].
      builder 가 이미 생성한 variant 정보를 src URL → VariantSet 로 매핑.
      외부 URL / SVG / 변환되지 않은 이미지에 대해서는 None 반환.

    동작:
      - loading 속성이 없고 config.lazy_loading=True 면 추가.
      - variant_lookup 이 VariantSet 을 반환하면 src 를 primary webp 로 바꾸고
        srcset / sizes 추가.
      - 그 외 (외부 URL, SVG, raster 지만 변환 안 됨) 는 src 그대로 + lazy 만.
    """
    def replace(m):
        attrs_str = m.group(1)
        attrs = _parse_img_attrs(attrs_str)

        # src 찾기 — attr 이름은 lower-cased.
        src_idx = next(
            (i for i, (n, _v, _q) in enumerate(attrs) if n == 'src'),
            -1,
        )
        if src_idx < 0:
            # src 없는 img — 그냥 lazy 만 부착하고 끝.
            if config.lazy_loading and not any(n == 'loading' for n, _, _ in attrs):
                attrs.append(('loading', 'lazy', '"'))
            return _serialize_img(attrs)

        _name, src_val, _q = attrs[src_idx]

        variants = None
        if src_val and not _is_external_url(src_val):
            variants = variant_lookup(src_val)

        if variants is not None:
            dir_part, stem, _ext, tail = split_url(src_val)
            primary = variants.primary_width
            prefix = '' if dir_part in ('.', '') else dir_part + '/'
            new_src = f'{prefix}{stem}-{primary}.webp{tail}'
            srcset = build_srcset(dir_part, stem, variants.widths)

            attrs[src_idx] = ('src', new_src, '"')

            # srcset / sizes — 기존 값이 없으면 추가, 있으면 덮어쓰지 않음
            # (사용자가 명시적으로 지정한 경우 존중).
            if not any(n == 'srcset' for n, _, _ in attrs):
                attrs.append(('srcset', srcset, '"'))
            if (config.default_sizes
                    and not any(n == 'sizes' for n, _, _ in attrs)):
                attrs.append(('sizes', config.default_sizes, '"'))

        if config.lazy_loading and not any(n == 'loading' for n, _, _ in attrs):
            attrs.append(('loading', 'lazy', '"'))

        return _serialize_img(attrs)

    return _IMG_TAG_RE.sub(replace, html)

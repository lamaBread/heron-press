#!/usr/bin/env python3
"""폴더명 → URL slug 산출 — admin.php slug 제안 진입점 (v1.1.0).

admin.php 가 새 글 폴더명에서 slug 를 제안할 때 PHP 로 slug 규칙을
재구현하지 않고 이 스크립트를 부른다. 빌드가 실제로 쓰는
`scripts.slugs.category_slug_from_name` 그대로를 호출하므로 제안 slug 가
빌드 산출 slug 와 항상 일치한다 (설계 원칙 단일화 — 두 번째 slug 구현
금지). 비ASCII 폴더명이면 빌더가 매 빌드 띄우는 hex 자동변환 경고와
같은 상황이라 `non_ascii: true` 도 함께 알려 admin UI 가 사전 경고한다.

Usage:
    python slug_one.py <folder name>     # 인자(공백 포함 가능)
    echo -n "<name>" | python slug_one.py  # 또는 stdin

출력: JSON 한 줄 {"slug": "...", "non_ascii": true|false} (stdout, UTF-8).
"""
import json
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SRC))


def main(argv=None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv:
        name = ' '.join(argv)
    else:
        name = sys.stdin.buffer.read().decode('utf-8', errors='replace')
    name = name.strip()

    try:
        from scripts.slugs import category_slug_from_name, has_non_ascii
    except Exception as e:  # noqa: BLE001
        sys.stdout.write(json.dumps(
            {'slug': '', 'non_ascii': False, 'error': repr(e)},
            ensure_ascii=False))
        raise SystemExit(1)

    out = {
        'slug': category_slug_from_name(name),
        'non_ascii': bool(has_non_ascii(name)),
    }
    sys.stdout.reconfigure(encoding='utf-8', newline='')
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    sys.stdout.flush()


if __name__ == '__main__':
    main()

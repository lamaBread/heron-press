"""stdlib-only YAML 부분 구현.

지원 문법은 이 프로젝트에서 실제 사용되는 부분집합:
  - key: value  (string, int, bool, null)
  - "quoted key": value
  - key:        → null
  - key: "str" / 'str'
  - key: [a, b]  (inline list)
  - key: [\n  a,\n  b\n]  (multi-line inline list; v1.2.2 추가)
  - key:\n  - item  (block list)
  - key:\n  subkey: val  (block map; nested mapping)
  - key: |  (literal block scalar)
  - # comments

v1.2.2: `[` 로 시작하고 같은 줄에 `]` 가 없으면 후속 줄을 누적해 `]` 까지
        모은 뒤 inline list 로 파싱. 줄 단위 trailing comma 와 주석 줄 허용.
"""
import re


def yaml_load(text: str) -> dict:
    lines = text.splitlines()
    n = len(lines)
    i = [0]  # mutable index

    def get_indent(s: str) -> int:
        return len(s) - len(s.lstrip(' '))

    def parse_scalar(s: str):
        s = s.strip()
        if not s or s in ('null', '~', 'Null', 'NULL'):
            return None
        if s in ('true', 'True', 'TRUE'):
            return True
        if s in ('false', 'False', 'FALSE'):
            return False
        if (s.startswith('"') and s.endswith('"')) or \
           (s.startswith("'") and s.endswith("'")):
            return s[1:-1]
        try:
            return int(s)
        except ValueError:
            pass
        return s

    def parse_inline_list(inner: str) -> list:
        if not inner.strip():
            return []
        items = []
        cur = ''
        in_q = None
        for ch in inner:
            if in_q:
                if ch == in_q:
                    in_q = None
                cur += ch
            elif ch in ('"', "'"):
                in_q = ch
                cur += ch
            elif ch == ',':
                items.append(parse_scalar(cur.strip()))
                cur = ''
            else:
                cur += ch
        if cur.strip():
            items.append(parse_scalar(cur.strip()))
        return items

    def parse_inline_list_multiline(first_val: str) -> list:
        # first_val 은 '[' 로 시작하지만 같은 줄에 ']' 가 없는 경우.
        # 후속 줄을 ']' 가 나올 때까지 모아 inline list 로 파싱한다.
        # 종료 시 i[0] 은 ']' 가 포함된 줄을 가리킨다 (호출자가 +1).
        parts = []
        remainder = first_val[1:].strip().rstrip(',').strip()
        if remainder:
            parts.append(remainder)
        while True:
            i[0] += 1
            if i[0] >= n:
                break
            stripped = lines[i[0]].strip()
            if not stripped or stripped.startswith('#'):
                continue
            if stripped == ']':
                break
            if stripped.endswith(']'):
                body = stripped[:-1].strip().rstrip(',').strip()
                if body:
                    parts.append(body)
                break
            parts.append(stripped.rstrip(',').strip())
        return parse_inline_list(','.join(parts))

    def parse_literal_block(base_indent: int) -> str:
        result = []
        block_indent = None
        while i[0] < n:
            raw = lines[i[0]]
            if not raw.strip():
                result.append('')
                i[0] += 1
                continue
            indent = get_indent(raw)
            if block_indent is None:
                if indent <= base_indent:
                    break
                block_indent = indent
            if indent < block_indent:
                break
            result.append(raw[block_indent:])
            i[0] += 1
        while result and not result[-1]:
            result.pop()
        return '\n'.join(result) + '\n' if result else ''

    def parse_block_list(list_indent: int) -> list:
        items = []
        while i[0] < n:
            raw = lines[i[0]]
            stripped = raw.strip()
            if not stripped or stripped.startswith('#'):
                i[0] += 1
                continue
            indent = get_indent(raw)
            if indent < list_indent:
                break
            if indent == list_indent and stripped.startswith('- '):
                items.append(parse_scalar(stripped[2:]))
                i[0] += 1
            elif indent == list_indent and stripped == '-':
                items.append(None)
                i[0] += 1
            else:
                break
        return items

    def parse_block_map(map_indent: int) -> dict:
        out = {}
        while i[0] < n:
            raw = lines[i[0]]
            stripped = raw.strip()
            if not stripped or stripped.startswith('#'):
                i[0] += 1
                continue
            indent = get_indent(raw)
            if indent < map_indent:
                break
            if indent != map_indent:
                i[0] += 1
                continue
            parsed = parse_key_line(raw)
            if parsed is None:
                i[0] += 1
                continue
            k, v = parsed
            if v == '|':
                i[0] += 1
                out[k] = parse_literal_block(map_indent)
            elif v.startswith('['):
                if v.endswith(']'):
                    out[k] = parse_inline_list(v[1:-1])
                else:
                    out[k] = parse_inline_list_multiline(v)
                i[0] += 1
            elif v == '':
                i[0] += 1
                if i[0] < n:
                    nxt = lines[i[0]]
                    nxt_stripped = nxt.strip()
                    nxt_indent = get_indent(nxt)
                    if nxt_indent > map_indent:
                        if nxt_stripped.startswith('- ') or nxt_stripped == '-':
                            out[k] = parse_block_list(nxt_indent)
                        else:
                            out[k] = parse_block_map(nxt_indent)
                        continue
                out[k] = None
            else:
                out[k] = parse_scalar(v)
                i[0] += 1
        return out

    def parse_key_line(raw: str):
        s = raw.strip()
        for q in ('"', "'"):
            if s.startswith(q):
                end = s.find(q, 1)
                if end < 0:
                    return None
                key = s[1:end]
                rest = s[end + 1:].strip()
                if rest.startswith(':'):
                    return key, rest[1:].strip()
                return None
        m = re.match(r'^([^:#\'"]+?):\s*(.*)', s)
        if m:
            return m.group(1).strip(), m.group(2).strip()
        return None

    result = {}
    while i[0] < n:
        raw = lines[i[0]]
        stripped = raw.strip()
        if not stripped or stripped.startswith('#'):
            i[0] += 1
            continue

        parsed = parse_key_line(raw)
        if parsed is None:
            i[0] += 1
            continue

        key, val_str = parsed
        base_indent = get_indent(raw)

        if val_str == '|':
            i[0] += 1
            result[key] = parse_literal_block(base_indent)
        elif val_str.startswith('['):
            if val_str.endswith(']'):
                result[key] = parse_inline_list(val_str[1:-1])
            else:
                result[key] = parse_inline_list_multiline(val_str)
            i[0] += 1
        elif val_str == '':
            i[0] += 1
            if i[0] < n:
                next_raw = lines[i[0]]
                next_stripped = next_raw.strip()
                next_indent = get_indent(next_raw)
                if next_indent > base_indent and next_stripped:
                    if next_stripped.startswith('- ') or next_stripped == '-':
                        result[key] = parse_block_list(next_indent)
                        continue
                    result[key] = parse_block_map(next_indent)
                    continue
            result[key] = None
        else:
            result[key] = parse_scalar(val_str)
            i[0] += 1

    return result

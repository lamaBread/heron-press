"""Parsedown 1.7.4 — Python port.

원본:
  Parsedown (c) Emanuil Rusev — http://parsedown.org
  MIT License (LICENSE.txt 참조)

이 모듈은 PHP `Parsedown.php` (v1.7.4) 를 Python 3 stdlib 만으로
가능한 한 충실히 옮긴 포팅이다. 의도적으로:

  * 메서드명, 블록/인라인 dispatch 구조, 내부 데이터 구조 (Block/Element
    dict 의 키 이름) 를 원본과 동일하게 유지한다.
  * 출력은 원본 PHP Parsedown 의 출력과 바이트 단위로 일치하는 것을 목표로 한다.
    (parity 검증은 v0.4.1 이전에 18개 fixture 로 수행됨.)

PHP → Python 매핑 메모:

  * `chop($s)`            → `s.rstrip()`
  * `mb_strlen($s,'utf-8')` → `len(s)`           (Python str 은 코드포인트 단위)
  * `strpos($h,$n)`       → `h.find(n)` (-1 → False 의미)
  * `strpbrk($t,$chars)`  → 첫 marker 위치를 찾는 _strpbrk()
  * `htmlspecialchars(..,ENT_QUOTES,'UTF-8')`  → `_escape(t, allow_quotes=False)`
  * `htmlspecialchars(..,ENT_NOQUOTES,'UTF-8')` → `_escape(t, allow_quotes=True)`
    (single quote 는 `&#039;` 로 — PHP 와 동일)
  * `(?R)` PCRE recursive  → `_match_bracketed()` 수동 구현
  * `++` / `*+` possessive → 일반 `+` / `*` (catastrophic backtracking 위험은
    실제 마크다운 입력에서 미발생; 문제 시 별도 처리)
  * 메서드 동적 dispatch (`$this->{'block'.$Type}(...)`) → `getattr(self, ...)`
  * PHP 배열의 reference (`& $Block['li']`) → Python dict 객체 동일 참조

원본의 protected/private 접근 제어자는 Python 의 leading underscore 로 옮기지
않았다 — 원본 메서드명을 그대로 두는 편이 비교/디버깅에 유리하기 때문.
"""
from __future__ import annotations

import re
from typing import Optional


# ════════════════════════════════════════════════════════════════
# Helpers (PHP function shims)
# ════════════════════════════════════════════════════════════════

def _escape(text: str, allow_quotes: bool = False) -> str:
    """PHP `htmlspecialchars($text, ENT_QUOTES|ENT_NOQUOTES, 'UTF-8')` 와 동일.

    allow_quotes=True  → quote 는 변환하지 않음 (ENT_NOQUOTES).
    allow_quotes=False → " 는 &quot;, ' 는 &#039; 로 변환 (ENT_QUOTES).
    """
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    if not allow_quotes:
        text = text.replace('"', '&quot;').replace("'", '&#039;')
    return text


# inlineMarkerList: `!"*_&[:<>` ~ \\` 의 char class
_INLINE_MARKER_RE = re.compile(r'[!"*_&\[:<>`~\\]')


def _strpbrk(text: str, marker_re: re.Pattern) -> Optional[re.Match]:
    """PHP strpbrk 시뮬레이션: 첫 marker 의 Match 객체 (없으면 None)."""
    return marker_re.search(text)


def _match_bracketed(text: str) -> Optional[tuple]:
    """PCRE `\\[((?:[^][]++|(?R))*+)\\]` 의 수동 구현.

    text 가 '[' 로 시작할 때만 매칭. 짝이 맞는 첫 ']' 까지의 전체 매칭과
    안쪽 텍스트를 (full, inner) 로 돌려준다. 안 맞으면 None.
    """
    if not text or text[0] != '[':
        return None
    depth = 0
    for i, ch in enumerate(text):
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
            if depth == 0:
                return text[:i + 1], text[1:i]
    return None


# ════════════════════════════════════════════════════════════════
# Parsedown class
# ════════════════════════════════════════════════════════════════

class Parsedown:
    version = '1.7.4'

    # ── public entry point ─────────────────────────────────────

    def text(self, text: str) -> str:
        # make sure no definitions are set
        self.DefinitionData = {}

        # standardize line breaks
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # remove surrounding line breaks
        text = text.strip('\n')

        # split text into lines
        lines = text.split('\n')

        # iterate through lines to identify blocks
        markup = self.lines(lines)

        # trim line breaks
        markup = markup.strip('\n')

        return markup

    # ── Setters ────────────────────────────────────────────────

    def setBreaksEnabled(self, breaksEnabled):
        self.breaksEnabled = breaksEnabled
        return self

    def setMarkupEscaped(self, markupEscaped):
        self.markupEscaped = markupEscaped
        return self

    def setUrlsLinked(self, urlsLinked):
        self.urlsLinked = urlsLinked
        return self

    def setSafeMode(self, safeMode):
        self.safeMode = bool(safeMode)
        return self

    # ── Instance state ────────────────────────────────────────

    def __init__(self):
        self.breaksEnabled: bool = False
        self.markupEscaped: bool = False
        self.urlsLinked: bool = True
        self.safeMode: bool = False
        self.DefinitionData: dict = {}

    # ── Class fields (static, mirror PHP `protected` arrays) ──

    safeLinksWhitelist = (
        'http://', 'https://', 'ftp://', 'ftps://', 'mailto:',
        'data:image/png;base64,',
        'data:image/gif;base64,',
        'data:image/jpeg;base64,',
        'irc:', 'ircs:', 'git:', 'ssh:', 'news:', 'steam:',
    )

    BlockTypes = {
        '#': ['Header'],
        '*': ['Rule', 'List'],
        '+': ['List'],
        '-': ['SetextHeader', 'Table', 'Rule', 'List'],
        '0': ['List'], '1': ['List'], '2': ['List'], '3': ['List'],
        '4': ['List'], '5': ['List'], '6': ['List'], '7': ['List'],
        '8': ['List'], '9': ['List'],
        ':': ['Table'],
        '<': ['Comment', 'Markup'],
        '=': ['SetextHeader'],
        '>': ['Quote'],
        '[': ['Reference'],
        '_': ['Rule'],
        '`': ['FencedCode'],
        '|': ['Table'],
        '~': ['FencedCode'],
    }

    unmarkedBlockTypes = ['Code']

    InlineTypes = {
        '"':  ['SpecialCharacter'],
        '!':  ['Image'],
        '&':  ['SpecialCharacter'],
        '*':  ['Emphasis'],
        ':':  ['Url'],
        '<':  ['UrlTag', 'EmailTag', 'Markup', 'SpecialCharacter'],
        '>':  ['SpecialCharacter'],
        '[':  ['Link'],
        '_':  ['Emphasis'],
        '`':  ['Code'],
        '~':  ['Strikethrough'],
        '\\': ['EscapeSequence'],
    }

    inlineMarkerList = '!"*_&[:<>`~\\'

    specialCharacters = (
        '\\', '`', '*', '_', '{', '}', '[', ']',
        '(', ')', '>', '#', '+', '-', '.', '!', '|',
    )

    StrongRegex = {
        '*': re.compile(r'^[*]{2}((?:\\\*|[^*]|[*][^*]*[*])+?)[*]{2}(?![*])', re.DOTALL),
        '_': re.compile(r'^__((?:\\_|[^_]|_[^_]*_)+?)__(?!_)', re.UNICODE | re.DOTALL),
    }

    EmRegex = {
        '*': re.compile(r'^[*]((?:\\\*|[^*]|[*][*][^*]+?[*][*])+?)[*](?![*])', re.DOTALL),
        '_': re.compile(r'^_((?:\\_|[^_]|__[^_]*__)+?)_(?!_)\b', re.UNICODE | re.DOTALL),
    }

    regexHtmlAttribute = r'[a-zA-Z_:][\w:.-]*(?:\s*=\s*(?:[^"\'=<>`\s]+|"[^"]*"|\'[^\']*\'))?'

    voidElements = (
        'area', 'base', 'br', 'col', 'command', 'embed', 'hr',
        'img', 'input', 'link', 'meta', 'param', 'source',
    )

    textLevelElements = (
        'a', 'br', 'bdo', 'abbr', 'blink', 'nextid', 'acronym', 'basefont',
        'b', 'em', 'big', 'cite', 'small', 'spacer', 'listing',
        'i', 'rp', 'del', 'code', 'strike', 'marquee',
        'q', 'rt', 'ins', 'font', 'strong',
        's', 'tt', 'kbd', 'mark',
        'u', 'xm', 'sub', 'nobr',
        'sup', 'ruby',
        'var', 'span',
        'wbr', 'time',
    )

    # ════════════════════════════════════════════════════════════
    # Block dispatch core
    # ════════════════════════════════════════════════════════════

    def lines(self, lines: list, nonNestables=None) -> str:
        # nonNestables 는 PHP 처럼 handler dispatch 가 항상 같은 시그니처로
        # 호출하기 위해 받지만 lines 자체는 사용하지 않는다.
        CurrentBlock = None
        Blocks: list = []

        for line in lines:
            # blank line ?
            if line.rstrip() == '':
                if CurrentBlock is not None:
                    CurrentBlock['interrupted'] = True
                continue

            # tab expansion (PHP uses mb_strlen 'utf-8' which counts codepoints)
            if '\t' in line:
                parts = line.split('\t')
                line = parts[0]
                for part in parts[1:]:
                    shortage = 4 - len(line) % 4
                    line += ' ' * shortage
                    line += part

            indent = 0
            while indent < len(line) and line[indent] == ' ':
                indent += 1

            text = line[indent:] if indent > 0 else line

            Line = {'body': line, 'indent': indent, 'text': text}

            # continue current block ?
            if CurrentBlock and CurrentBlock.get('continuable'):
                cont = getattr(self, 'block' + CurrentBlock['type'] + 'Continue', None)
                Block = cont(Line, CurrentBlock) if cont else None
                if Block is not None:
                    CurrentBlock = Block
                    continue
                else:
                    if self.isBlockCompletable(CurrentBlock['type']):
                        comp = getattr(self, 'block' + CurrentBlock['type'] + 'Complete')
                        CurrentBlock = comp(CurrentBlock)

            # start a new block ?
            marker = text[0]
            blockTypes = list(self.unmarkedBlockTypes)
            if marker in self.BlockTypes:
                for bt in self.BlockTypes[marker]:
                    blockTypes.append(bt)

            matched = False
            for blockType in blockTypes:
                fn = getattr(self, 'block' + blockType)
                Block = fn(Line, CurrentBlock)
                if Block is not None:
                    Block['type'] = blockType
                    if 'identified' not in Block:
                        Blocks.append(CurrentBlock)
                        Block['identified'] = True
                    if self.isBlockContinuable(blockType):
                        Block['continuable'] = True
                    CurrentBlock = Block
                    matched = True
                    break
            if matched:
                continue

            # paragraph continuation or new paragraph
            if (CurrentBlock is not None
                    and 'type' not in CurrentBlock
                    and 'interrupted' not in CurrentBlock):
                CurrentBlock['element']['text'] += '\n' + text
            else:
                Blocks.append(CurrentBlock)
                CurrentBlock = self.paragraph(Line)
                CurrentBlock['identified'] = True

        # finalize last block
        if (CurrentBlock and CurrentBlock.get('continuable')
                and self.isBlockCompletable(CurrentBlock['type'])):
            comp = getattr(self, 'block' + CurrentBlock['type'] + 'Complete')
            CurrentBlock = comp(CurrentBlock)

        Blocks.append(CurrentBlock)
        # PHP: unset($Blocks[0]) — drop the leading None placeholder
        Blocks = Blocks[1:]

        markup = ''
        for Block in Blocks:
            if Block is None:
                continue
            if Block.get('hidden'):
                continue
            markup += '\n'
            if 'markup' in Block:
                markup += Block['markup']
            else:
                markup += self.element(Block['element'])
        markup += '\n'

        return markup

    def isBlockContinuable(self, Type: str) -> bool:
        return hasattr(self, 'block' + Type + 'Continue')

    def isBlockCompletable(self, Type: str) -> bool:
        return hasattr(self, 'block' + Type + 'Complete')

    # ════════════════════════════════════════════════════════════
    # Block: Code (indented code)
    # ════════════════════════════════════════════════════════════

    def blockCode(self, Line, Block=None):
        if Block is not None and 'type' not in Block and 'interrupted' not in Block:
            return None
        if Line['indent'] >= 4:
            text = Line['body'][4:]
            return {
                'element': {
                    'name': 'pre',
                    'handler': 'element',
                    'text': {
                        'name': 'code',
                        'text': text,
                    },
                },
            }
        return None

    def blockCodeContinue(self, Line, Block):
        if Line['indent'] >= 4:
            if 'interrupted' in Block:
                Block['element']['text']['text'] += '\n'
                del Block['interrupted']
            Block['element']['text']['text'] += '\n'
            text = Line['body'][4:]
            Block['element']['text']['text'] += text
            return Block
        return None

    def blockCodeComplete(self, Block):
        return Block

    # ════════════════════════════════════════════════════════════
    # Block: Comment
    # ════════════════════════════════════════════════════════════

    def blockComment(self, Line, Block=None):
        if self.markupEscaped or self.safeMode:
            return None
        t = Line['text']
        if len(t) > 3 and t[3] == '-' and t[2] == '-' and t[1] == '!':
            Block = {'markup': Line['body']}
            if re.search(r'-->$', t):
                Block['closed'] = True
            return Block
        return None

    def blockCommentContinue(self, Line, Block):
        if 'closed' in Block:
            return None
        Block['markup'] += '\n' + Line['body']
        if re.search(r'-->$', Line['text']):
            Block['closed'] = True
        return Block

    # ════════════════════════════════════════════════════════════
    # Block: Fenced Code
    # ════════════════════════════════════════════════════════════

    def blockFencedCode(self, Line, Block=None):
        t = Line['text']
        ch = t[0]
        m = re.match(r'^[' + re.escape(ch) + r']{3,}[ ]*([^`]+)?[ ]*$', t)
        if not m:
            return None
        Element = {'name': 'code', 'text': ''}
        if m.group(1) is not None:
            lang_full = m.group(1)
            language = re.split(r'[ \t\n\f\r]', lang_full, 1)[0]
            Element['attributes'] = {'class': 'language-' + language}
        return {
            'char': ch,
            'element': {
                'name': 'pre',
                'handler': 'element',
                'text': Element,
            },
        }

    def blockFencedCodeContinue(self, Line, Block):
        if 'complete' in Block:
            return None
        if 'interrupted' in Block:
            Block['element']['text']['text'] += '\n'
            del Block['interrupted']
        if re.match(r'^' + re.escape(Block['char']) + r'{3,}[ ]*$', Line['text']):
            # PHP: substr($text, 1) — drop leading "\n" inserted by first content line
            Block['element']['text']['text'] = Block['element']['text']['text'][1:]
            Block['complete'] = True
            return Block
        Block['element']['text']['text'] += '\n' + Line['body']
        return Block

    def blockFencedCodeComplete(self, Block):
        return Block

    # ════════════════════════════════════════════════════════════
    # Block: ATX Header (#…)
    # ════════════════════════════════════════════════════════════

    def blockHeader(self, Line, Block=None):
        t = Line['text']
        if len(t) < 2:
            return None
        level = 1
        while level < len(t) and t[level] == '#':
            level += 1
        if level > 6:
            return None
        text = t.strip('# ')
        return {
            'element': {
                'name': 'h' + str(min(6, level)),
                'text': text,
                'handler': 'line',
            },
        }

    # ════════════════════════════════════════════════════════════
    # Block: List (ordered/unordered)
    # ════════════════════════════════════════════════════════════

    def blockList(self, Line, Block=None):
        t = Line['text']
        if t[0] <= '-':
            name, pattern = 'ul', '[*+-]'
        else:
            name, pattern = 'ol', '[0-9]+[.]'

        m = re.match(r'^(' + pattern + r'[ ]+)(.*)', t)
        if not m:
            return None

        new_block = {
            'indent': Line['indent'],
            'pattern': pattern,
            'element': {
                'name': name,
                'handler': 'elements',
                'text': [],
            },
        }

        if name == 'ol':
            # PHP: stristr($matches[0], '.', true) — part before first '.'
            list_start = m.group(0).split('.', 1)[0]
            if list_start != '1':
                new_block['element']['attributes'] = {'start': list_start}

        li = {
            'name': 'li',
            'handler': 'li',
            'text': [m.group(2)],
        }
        new_block['li'] = li
        new_block['element']['text'].append(li)
        return new_block

    def blockListContinue(self, Line, Block):
        m = re.match(r'^' + Block['pattern'] + r'(?:[ ]+(.*)|$)', Line['text'])
        if Block['indent'] == Line['indent'] and m:
            if 'interrupted' in Block:
                Block['li']['text'].append('')
                Block['loose'] = True
                del Block['interrupted']
            text = m.group(1) if m.group(1) is not None else ''
            new_li = {
                'name': 'li',
                'handler': 'li',
                'text': [text],
            }
            Block['li'] = new_li
            Block['element']['text'].append(new_li)
            return Block

        if Line['text'][0] == '[' and self.blockReference(Line):
            return Block

        if 'interrupted' not in Block:
            text = re.sub(r'^[ ]{0,4}', '', Line['body'], count=1)
            Block['li']['text'].append(text)
            return Block

        if Line['indent'] > 0:
            Block['li']['text'].append('')
            text = re.sub(r'^[ ]{0,4}', '', Line['body'], count=1)
            Block['li']['text'].append(text)
            del Block['interrupted']
            return Block

        return None

    def blockListComplete(self, Block):
        if 'loose' in Block:
            for li in Block['element']['text']:
                if li['text'][-1] != '':
                    li['text'].append('')
        return Block

    # ════════════════════════════════════════════════════════════
    # Block: Quote (>)
    # ════════════════════════════════════════════════════════════

    def blockQuote(self, Line, Block=None):
        m = re.match(r'^>[ ]?(.*)', Line['text'])
        if not m:
            return None
        return {
            'element': {
                'name': 'blockquote',
                'handler': 'lines',
                'text': [m.group(1)],
            },
        }

    def blockQuoteContinue(self, Line, Block):
        if Line['text'][0] == '>':
            m = re.match(r'^>[ ]?(.*)', Line['text'])
            if m:
                if 'interrupted' in Block:
                    Block['element']['text'].append('')
                    del Block['interrupted']
                Block['element']['text'].append(m.group(1))
                return Block
        if 'interrupted' not in Block:
            Block['element']['text'].append(Line['text'])
            return Block
        return None

    # ════════════════════════════════════════════════════════════
    # Block: Rule (--- *** ___)
    # ════════════════════════════════════════════════════════════

    def blockRule(self, Line, Block=None):
        ch = Line['text'][0]
        if re.match(r'^([' + re.escape(ch) + r'])([ ]*\1){2,}[ ]*$', Line['text']):
            return {'element': {'name': 'hr'}}
        return None

    # ════════════════════════════════════════════════════════════
    # Block: Setext Header (=== / ---)
    # ════════════════════════════════════════════════════════════

    def blockSetextHeader(self, Line, Block=None):
        if Block is None or 'type' in Block or 'interrupted' in Block:
            return None
        # PHP: chop($text, $text[0]) — rtrim all of the leading char
        t = Line['text']
        if t.rstrip(t[0]) == '':
            Block['element']['name'] = 'h1' if t[0] == '=' else 'h2'
            return Block
        return None

    # ════════════════════════════════════════════════════════════
    # Block: Markup (raw HTML block)
    # ════════════════════════════════════════════════════════════

    def blockMarkup(self, Line, Block=None):
        if self.markupEscaped or self.safeMode:
            return None
        m = re.match(
            r'^<(\w[\w-]*)(?:[ ]*' + self.regexHtmlAttribute + r')*[ ]*(\/)?>',
            Line['text'], re.ASCII,
        )
        if not m:
            return None
        element = m.group(1).lower()
        if element in self.textLevelElements:
            return None
        new_block = {
            'name': m.group(1),
            'depth': 0,
            'markup': Line['text'],
        }
        length = len(m.group(0))
        remainder = Line['text'][length:]
        if remainder.strip() == '':
            if m.group(2) is not None or m.group(1) in self.voidElements:
                new_block['closed'] = True
                new_block['void'] = True
        else:
            if m.group(2) is not None or m.group(1) in self.voidElements:
                return None
            if re.search(r'</' + m.group(1) + r'>[ ]*$', remainder, re.IGNORECASE):
                new_block['closed'] = True
        return new_block

    def blockMarkupContinue(self, Line, Block):
        if 'closed' in Block:
            return None
        if re.match(
            r'^<' + Block['name'] + r'(?:[ ]*' + self.regexHtmlAttribute + r')*[ ]*>',
            Line['text'], re.IGNORECASE | re.ASCII,
        ):
            Block['depth'] += 1
        m_close = re.match(
            r'(.*?)</' + Block['name'] + r'>[ ]*$',
            Line['text'], re.IGNORECASE | re.DOTALL,
        )
        if m_close:
            if Block['depth'] > 0:
                Block['depth'] -= 1
            else:
                Block['closed'] = True
        if 'interrupted' in Block:
            Block['markup'] += '\n'
            del Block['interrupted']
        Block['markup'] += '\n' + Line['body']
        return Block

    # ════════════════════════════════════════════════════════════
    # Block: Reference  [id]: url "title"
    # ════════════════════════════════════════════════════════════

    def blockReference(self, Line, Block=None):
        m = re.match(
            r'^\[(.+?)\]:[ ]*<?(\S+?)>?(?:[ ]+["\'(](.+)["\')])?[ ]*$',
            Line['text'],
        )
        if not m:
            return None
        ident = m.group(1).lower()
        Data = {'url': m.group(2), 'title': None}
        if m.group(3) is not None:
            Data['title'] = m.group(3)
        self.DefinitionData.setdefault('Reference', {})[ident] = Data
        return {'hidden': True}

    # ════════════════════════════════════════════════════════════
    # Block: Table
    # ════════════════════════════════════════════════════════════

    def blockTable(self, Line, Block=None):
        if Block is None or 'type' in Block or 'interrupted' in Block:
            return None
        if '|' in Block['element']['text'] and Line['text'].rstrip(' -:|') == '':
            alignments = []
            divider = Line['text']
            divider = divider.strip()
            divider = divider.strip('|')
            divider_cells = divider.split('|')
            for dc in divider_cells:
                dc = dc.strip()
                if dc == '':
                    continue
                alignment = None
                if dc[0] == ':':
                    alignment = 'left'
                if dc[-1] == ':':
                    alignment = 'center' if alignment == 'left' else 'right'
                alignments.append(alignment)

            HeaderElements = []
            header = Block['element']['text']
            header = header.strip()
            header = header.strip('|')
            header_cells = header.split('|')
            for index, hc in enumerate(header_cells):
                hc = hc.strip()
                he = {
                    'name': 'th',
                    'text': hc,
                    'handler': 'line',
                }
                if index < len(alignments) and alignments[index] is not None:
                    he['attributes'] = {'style': 'text-align: ' + alignments[index] + ';'}
                HeaderElements.append(he)

            new_block = {
                'alignments': alignments,
                'identified': True,
                'element': {
                    'name': 'table',
                    'handler': 'elements',
                    'text': [],
                },
            }
            new_block['element']['text'].append({
                'name': 'thead',
                'handler': 'elements',
                'text': [],
            })
            new_block['element']['text'].append({
                'name': 'tbody',
                'handler': 'elements',
                'text': [],
            })
            new_block['element']['text'][0]['text'].append({
                'name': 'tr',
                'handler': 'elements',
                'text': HeaderElements,
            })
            return new_block
        return None

    def blockTableContinue(self, Line, Block):
        if 'interrupted' in Block:
            return None
        if Line['text'][0] == '|' or '|' in Line['text']:
            Elements = []
            row = Line['text'].strip().strip('|')
            # split row honoring escaped pipes and inline code spans
            cells = re.findall(r'(?:(?:\\[|])|[^|`]|`[^`]+`|`)+', row)
            for index, cell in enumerate(cells):
                cell = cell.strip()
                elem = {
                    'name': 'td',
                    'handler': 'line',
                    'text': cell,
                }
                if index < len(Block['alignments']) and Block['alignments'][index] is not None:
                    elem['attributes'] = {
                        'style': 'text-align: ' + Block['alignments'][index] + ';',
                    }
                Elements.append(elem)
            Block['element']['text'][1]['text'].append({
                'name': 'tr',
                'handler': 'elements',
                'text': Elements,
            })
            return Block
        return None

    # ════════════════════════════════════════════════════════════
    # Paragraph
    # ════════════════════════════════════════════════════════════

    def paragraph(self, Line):
        return {
            'element': {
                'name': 'p',
                'text': Line['text'],
                'handler': 'line',
            },
        }

    # ════════════════════════════════════════════════════════════
    # Inline dispatch
    # ════════════════════════════════════════════════════════════

    def line(self, text: str, nonNestables=None) -> str:
        if nonNestables is None:
            nonNestables = []
        markup = ''

        while True:
            m = _strpbrk(text, _INLINE_MARKER_RE)
            if not m:
                break
            markerPosition = m.start()
            marker = m.group(0)
            excerpt = text[markerPosition:]
            Excerpt = {'text': excerpt, 'context': text}

            matched = False
            for inlineType in self.InlineTypes[marker]:
                if nonNestables and inlineType in nonNestables:
                    continue
                fn = getattr(self, 'inline' + inlineType)
                Inline = fn(Excerpt)
                if Inline is None:
                    continue
                # makes sure that the inline belongs to "our" marker
                if 'position' in Inline and Inline['position'] > markerPosition:
                    continue
                if 'position' not in Inline:
                    Inline['position'] = markerPosition
                # propagate nonNestables
                if 'element' in Inline:
                    elem = Inline['element']
                    nn = elem.setdefault('nonNestables', [])
                    for non in nonNestables:
                        nn.append(non)

                unmarkedText = text[:Inline['position']]
                markup += self.unmarkedText(unmarkedText)
                if 'markup' in Inline:
                    markup += Inline['markup']
                else:
                    markup += self.element(Inline['element'])
                text = text[Inline['position'] + Inline['extent']:]
                matched = True
                break

            if matched:
                continue

            # the marker does not belong to an inline — consume up to and
            # including this marker char
            unmarkedText = text[:markerPosition + 1]
            markup += self.unmarkedText(unmarkedText)
            text = text[markerPosition + 1:]

        markup += self.unmarkedText(text)
        return markup

    # ── inline implementations ────────────────────────────────

    def inlineCode(self, Excerpt):
        marker = Excerpt['text'][0]
        m = re.match(
            r'^(' + re.escape(marker) + r'+)[ ]*(.+?)[ ]*(?<!'
            + re.escape(marker) + r')\1(?!' + re.escape(marker) + r')',
            Excerpt['text'], re.DOTALL,
        )
        if not m:
            return None
        text = m.group(2)
        text = re.sub(r'[ ]*\n', ' ', text)
        return {
            'extent': len(m.group(0)),
            'element': {
                'name': 'code',
                'text': text,
            },
        }

    def inlineEmailTag(self, Excerpt):
        if '>' not in Excerpt['text']:
            return None
        m = re.match(r'^<((mailto:)?\S+?@\S+?)>', Excerpt['text'], re.IGNORECASE)
        if not m:
            return None
        url = m.group(1)
        if m.group(2) is None:
            url = 'mailto:' + url
        return {
            'extent': len(m.group(0)),
            'element': {
                'name': 'a',
                'text': m.group(1),
                'attributes': {'href': url},
            },
        }

    def inlineEmphasis(self, Excerpt):
        if len(Excerpt['text']) < 2:
            return None
        marker = Excerpt['text'][0]
        if Excerpt['text'][1] == marker:
            m = self.StrongRegex[marker].match(Excerpt['text'])
            if m:
                emphasis = 'strong'
            else:
                m = self.EmRegex[marker].match(Excerpt['text'])
                if not m:
                    return None
                emphasis = 'em'
        else:
            m = self.EmRegex[marker].match(Excerpt['text'])
            if not m:
                return None
            emphasis = 'em'
        return {
            'extent': len(m.group(0)),
            'element': {
                'name': emphasis,
                'handler': 'line',
                'text': m.group(1),
            },
        }

    def inlineEscapeSequence(self, Excerpt):
        if len(Excerpt['text']) > 1 and Excerpt['text'][1] in self.specialCharacters:
            return {
                'markup': Excerpt['text'][1],
                'extent': 2,
            }
        return None

    def inlineImage(self, Excerpt):
        if len(Excerpt['text']) < 2 or Excerpt['text'][1] != '[':
            return None
        sub = Excerpt['text'][1:]
        Link = self.inlineLink({'text': sub, 'context': Excerpt.get('context', '')})
        if Link is None:
            return None
        Inline = {
            'extent': Link['extent'] + 1,
            'element': {
                'name': 'img',
                'attributes': {
                    'src': Link['element']['attributes']['href'],
                    'alt': Link['element']['text'],
                },
            },
        }
        # merge link attributes (without overwriting src/alt; drop href)
        link_attrs = dict(Link['element']['attributes'])
        link_attrs.pop('href', None)
        for k, v in link_attrs.items():
            Inline['element']['attributes'].setdefault(k, v)
        return Inline

    def inlineLink(self, Excerpt):
        Element = {
            'name': 'a',
            'handler': 'line',
            'nonNestables': ['Url', 'Link'],
            'text': None,
            'attributes': {
                'href': None,
                'title': None,
            },
        }
        extent = 0
        remainder = Excerpt['text']

        bracket = _match_bracketed(remainder)
        if bracket is None:
            return None
        full, inner = bracket
        Element['text'] = inner
        extent += len(full)
        remainder = remainder[extent:]

        m_inline = re.match(
            r'^[(]\s*((?:[^ ()]+|[(][^ )]+[)])+)(?:[ ]+("[^"]*"|\'[^\']*\'))?\s*[)]',
            remainder,
        )
        if m_inline:
            Element['attributes']['href'] = m_inline.group(1)
            if m_inline.group(2) is not None:
                Element['attributes']['title'] = m_inline.group(2)[1:-1]
            extent += len(m_inline.group(0))
        else:
            m_ref = re.match(r'^\s*\[(.*?)\]', remainder)
            if m_ref:
                definition = m_ref.group(1) if len(m_ref.group(1)) > 0 else Element['text']
                definition = definition.lower()
                extent += len(m_ref.group(0))
            else:
                definition = Element['text'].lower() if Element['text'] else ''
            refs = self.DefinitionData.get('Reference', {})
            if definition not in refs:
                return None
            Definition = refs[definition]
            Element['attributes']['href'] = Definition['url']
            Element['attributes']['title'] = Definition['title']

        return {'extent': extent, 'element': Element}

    def inlineMarkup(self, Excerpt):
        if self.markupEscaped or self.safeMode:
            return None
        if '>' not in Excerpt['text']:
            return None
        t = Excerpt['text']
        if t[1] == '/':
            m = re.match(r'^</\w[\w-]*[ ]*>', t, re.DOTALL | re.ASCII)
            if m:
                return {'markup': m.group(0), 'extent': len(m.group(0))}
        if t[1] == '!':
            m = re.match(r'^<!---?[^>-](?:-?[^-])*-->', t, re.DOTALL)
            if m:
                return {'markup': m.group(0), 'extent': len(m.group(0))}
        if t[1] != ' ':
            m = re.match(
                r'^<\w[\w-]*(?:[ ]*' + self.regexHtmlAttribute + r')*[ ]*\/?>',
                t, re.DOTALL | re.ASCII,
            )
            if m:
                return {'markup': m.group(0), 'extent': len(m.group(0))}
        return None

    def inlineSpecialCharacter(self, Excerpt):
        if Excerpt['text'][0] == '&' and not re.match(r'^&#?\w+;', Excerpt['text'], re.ASCII):
            return {'markup': '&amp;', 'extent': 1}
        SpecialCharacter = {'>': 'gt', '<': 'lt', '"': 'quot'}
        if Excerpt['text'][0] in SpecialCharacter:
            return {
                'markup': '&' + SpecialCharacter[Excerpt['text'][0]] + ';',
                'extent': 1,
            }
        return None

    def inlineStrikethrough(self, Excerpt):
        if len(Excerpt['text']) < 2:
            return None
        if Excerpt['text'][1] == '~':
            m = re.match(r'^~~(?=\S)(.+?)(?<=\S)~~', Excerpt['text'])
            if m:
                return {
                    'extent': len(m.group(0)),
                    'element': {
                        'name': 'del',
                        'text': m.group(1),
                        'handler': 'line',
                    },
                }
        return None

    def inlineUrl(self, Excerpt):
        if (self.urlsLinked is not True
                or len(Excerpt['text']) < 3
                or Excerpt['text'][2] != '/'):
            return None
        # PHP /ui — UTF-8 모드의 `\w`/`\b` 를 사용. 한국어 등 비ASCII 가
        # \w 로 취급되어, 한글 끝의 URL (예: `dbpedia.org/책`) 에서도 `\b`
        # 가 책↔공백 사이에서 매칭됨. Python str 의 default 모드 (Unicode)
        # 가 동일 의미.
        m = re.search(
            r'\bhttps?:[/]{2}[^\s<]+\b/*',
            Excerpt['context'], re.IGNORECASE,
        )
        if not m:
            return None
        url = m.group(0)
        return {
            'extent': len(url),
            'position': m.start(),
            'element': {
                'name': 'a',
                'text': url,
                'attributes': {'href': url},
            },
        }

    def inlineUrlTag(self, Excerpt):
        if '>' not in Excerpt['text']:
            return None
        m = re.match(r'^<(\w+:\/{2}[^ >]+)>', Excerpt['text'], re.IGNORECASE | re.ASCII)
        if not m:
            return None
        url = m.group(1)
        return {
            'extent': len(m.group(0)),
            'element': {
                'name': 'a',
                'text': url,
                'attributes': {'href': url},
            },
        }

    # ── unmarked text (handles line breaks) ───────────────────

    def unmarkedText(self, text: str) -> str:
        if self.breaksEnabled:
            text = re.sub(r'[ ]*\n', '<br />\n', text)
        else:
            text = re.sub(r'(?:[ ][ ]+|[ ]*\\)\n', '<br />\n', text)
            text = text.replace(' \n', '\n')
        return text

    # ════════════════════════════════════════════════════════════
    # Element rendering / handler dispatch
    # ════════════════════════════════════════════════════════════

    def element(self, Element, nonNestables=None) -> str:
        # `element` 는 handler 로도 쓰이므로 (pre>code 케이스) 추가 인자
        # 시그니처를 받지만 사용하지 않는다.
        if self.safeMode:
            Element = self.sanitiseElement(Element)

        markup = '<' + Element['name']

        if 'attributes' in Element:
            for name, value in Element['attributes'].items():
                if value is None:
                    continue
                markup += ' ' + name + '="' + _escape(value) + '"'

        permitRawHtml = False
        text = None
        if 'text' in Element and Element['text'] is not None:
            text = Element['text']
        elif 'rawHtml' in Element:
            text = Element['rawHtml']
            allowRawInSafe = bool(Element.get('allowRawHtmlInSafeMode'))
            permitRawHtml = (not self.safeMode) or allowRawInSafe

        if text is not None:
            markup += '>'
            if 'nonNestables' not in Element:
                Element['nonNestables'] = []
            if 'handler' in Element:
                handler = getattr(self, Element['handler'])
                markup += handler(text, Element['nonNestables'])
            elif not permitRawHtml:
                markup += _escape(text, allow_quotes=True)
            else:
                markup += text
            markup += '</' + Element['name'] + '>'
        else:
            markup += ' />'

        return markup

    def elements(self, Elements, nonNestables=None) -> str:
        """PHP `elements()` takes a single $Elements arg; the wrapper that
        invokes it through `handler` passes the array as $text. The PHP
        method signature is `protected function elements(array $Elements)`
        — but the element() dispatch passes `$Element['nonNestables']` too.
        PHP ignores the extra arg silently. We accept and ignore it.
        """
        markup = ''
        for Element in Elements:
            markup += '\n' + self.element(Element)
        markup += '\n'
        return markup

    def li(self, lines, nonNestables=None) -> str:
        markup = self.lines(lines)
        trimmed = markup.strip()
        if '' not in lines and trimmed.startswith('<p>'):
            markup = trimmed
            markup = markup[3:]
            position = markup.find('</p>')
            markup = markup[:position] + markup[position + 4:]
        return markup

    # ════════════════════════════════════════════════════════════
    # Deprecated / convenience
    # ════════════════════════════════════════════════════════════

    def parse(self, text: str) -> str:
        return self.text(text)

    # ════════════════════════════════════════════════════════════
    # Safe-mode sanitiser
    # ════════════════════════════════════════════════════════════

    _GOOD_ATTRIBUTE_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9-_]*$')
    _SAFE_URL_NAME_TO_ATT = {'a': 'href', 'img': 'src'}

    def sanitiseElement(self, Element):
        name = Element.get('name')
        if name in self._SAFE_URL_NAME_TO_ATT:
            Element = self.filterUnsafeUrlInAttribute(Element, self._SAFE_URL_NAME_TO_ATT[name])
        attrs = Element.get('attributes')
        if attrs:
            for att in list(attrs.keys()):
                if not self._GOOD_ATTRIBUTE_RE.match(att):
                    del attrs[att]
                elif self._striAtStart(att, 'on'):
                    del attrs[att]
        return Element

    def filterUnsafeUrlInAttribute(self, Element, attribute):
        url = Element['attributes'].get(attribute, '')
        for scheme in self.safeLinksWhitelist:
            if self._striAtStart(url, scheme):
                return Element
        Element['attributes'][attribute] = url.replace(':', '%3A')
        return Element

    @staticmethod
    def _striAtStart(string: str, needle: str) -> bool:
        if len(needle) > len(string):
            return False
        return string[:len(needle)].lower() == needle.lower()

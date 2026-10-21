"""Non-executing Lisp delimiter checks and conservative indentation helpers."""
import re
import syntax_highlight as SH

_languages, _ = SH.load_languages()
_lisp = SH.language_for('buffer.lisp', _languages)
_basic = SH.language_for('buffer.bas', _languages)


def _error(text, offset, message, source_name):
    line = text.count('\n', 0, offset) + 1
    column = offset - text.rfind('\n', 0, offset)
    error = SyntaxError(f'{source_name}: {message} at line {line}, column {column}')
    error.filename, error.lineno, error.offset = source_name, line, column
    raise error


def check_lisp(text, source_name='<buffer>'):
    """Strict lexical/delimiter check; never expand macros or evaluate forms."""
    spans = _lisp.spans(text)
    for tag, start, end in spans:
        if tag == 'string':
            token = text[start:end]
            pattern = r'"""[\s\S]*?"""' if token.startswith('"""') else r'"(?:\\[\s\S]|[^"\\])*"'
            if not re.fullmatch(pattern, token):
                _error(text, start, 'Unterminated string', source_name)
    mask = SH.code_mask(spans, len(text))
    stack = []
    for pos, char in enumerate(text):
        if mask[pos]:
            continue
        if char in '([{':
            stack.append((char, pos))
        elif char in ')]}':
            if not stack or '([{'.index(stack[-1][0]) != ')]}'.index(char):
                _error(text, pos, f'Unexpected closing bracket: {char}', source_name)
            stack.pop()
    if stack:
        char, pos = stack[-1]
        _error(text, pos, f'Unclosed bracket: {char}', source_name)
    # Use the reader as well (e.g. a dangling quote), without macro expansion.
    import lispy3
    tokens = lispy3.tokenize(text, source_name=source_name)
    try:
        while tokens:
            lispy3.read_from_tokens(tokens)
    except SyntaxError as error:
        if error.lineno is None:
            _error(text, len(text), str(error), source_name)
        raise
    return mask


def indent_lisp(text, source_name='<buffer>'):
    mask = check_lisp(text, source_name)
    strings = [(a,b) for tag,a,b in _lisp.spans(text) if tag == 'string']
    depth, offset, output = 0, 0, []
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip(' \t')
        # Continuation lines of raw/ordinary multiline strings are literal data.
        if any(a < offset < b for a,b in strings):
            output.append(line)
        else:
            closers = 0
            for char in stripped:
                if char not in ')]}':
                    break
                closers += 1
            output.append(' ' * (2 * max(0, depth - closers)) + stripped if stripped.strip() else stripped)
        for i, char in enumerate(line):
            if not mask[offset+i]:
                depth += (1 if char in '([{' else -1 if char in ')]}' else 0)
        offset += len(line)
    return ''.join(output)


def _basic_effect(line):
    code = list(line)
    for tag, start, end in _basic.spans(line):
        if tag in ('string', 'comment'):
            code[start:end] = ' ' * (end-start)
    statements = ''.join(code).upper().split(':')
    delta = 0
    for statement in statements:
        statement = re.sub(r'^\s*\d+\s*', '', statement).strip()
        if re.match(r'^(NEXT\b|ENDWHILE\b|UNTIL\b|ENDIF\b|ENDCASE\b|ENDPROC\b)', statement):
            delta -= 1
        elif re.match(r'^(FOR\b|WHILE\b|REPEAT\b|CASE\b|DEF\s*PROC)', statement):
            delta += 1
        elif re.match(r'^IF\b.*\bTHEN\s*$', statement):
            delta += 1
    first = statements[0].strip()
    first = re.sub(r'^\d+\s*', '', first)
    dedent = bool(re.match(r'^(NEXT\b|ENDWHILE\b|UNTIL\b|ENDIF\b|ENDCASE\b|ENDPROC\b|ELSE\b|WHEN\b|OTHERWISE\b)', first))
    return delta, dedent


def indent_basic(text):
    """Indent common BASIC block statements, preserving all non-leading text."""
    depth, output = 0, []
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip(' \t')
        delta, dedent = _basic_effect(stripped)
        level = max(0, depth - int(dedent))
        numbered = re.match(r'^(\d+)[ \t]+(.*)', stripped, re.DOTALL)
        if numbered:
            output.append(numbered[1]+' '+('  '*level)+numbered[2].lstrip(' \t'))
        else:
            output.append('  '*level+stripped if stripped.strip() else stripped)
        depth = max(0, depth+delta)
    return ''.join(output)


def next_indent(text, basic=False):
    """Indentation for Return while a program is still incomplete."""
    if basic:
        last = indent_basic(text+'\nX').splitlines()[-1]
        return len(last)-len(last.lstrip())
    mask = SH.code_mask(_lisp.spans(text), len(text))
    depth = sum((1 if c in '([{' else -1 if c in ')]}' else 0)
                for i,c in enumerate(text) if not mask[i])
    return 2*max(0, depth)


def file_reference_at_cursor(text, offset, language='Lisp'):
    """Decode a string under the caret without evaluating source code."""
    import ast
    language = next((item for item in _languages if item.name == language), _lisp)
    for tag, start, end in language.spans(text):
        if tag != 'string' or not start <= offset < end:
            continue
        token = text[start:end]
        try:
            if language.name == 'BBC BASIC':
                return token[1:-1].replace('""', '"')
            if language.name == 'Lisp':
                import lispy3
                value = lispy3.atom(token)
                return value.value if isinstance(value, lispy3.String) else None
            value = ast.literal_eval(token)
            return value if isinstance(value, str) else None
        except (ValueError, SyntaxError):
            return None
    return None

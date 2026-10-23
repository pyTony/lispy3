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


LAYOUT_WIDTH = 72
# Forms whose body goes on new lines: head plus N leading arguments stay on line one.
_BODY_FORMS = {'define': 1, 'define-macro': 1, 'defmacro': 2, 'lambda': 1, 'let': 1,
               'let*': 1, 'letrec': 1, 'when': 1, 'unless': 1, 'begin': 0, 'cond': 0,
               'case': 1, 'dotimes': 1, 'while': 1, 'try': 0, 'define-library': 1}


def _layout_items(line, mask):
    """Parse one line of complete forms into nested [open, items, close] lists and atoms."""
    stack, pos, glued = [[]], 0, ''
    while pos < len(line):
        char = line[pos]
        if not mask[pos] and char.isspace():
            pos += 1
            continue
        if not mask[pos] and char in '([{':
            stack.append([glued + char])
            glued = ''
            pos += 1
            continue
        if not mask[pos] and char in ')]}':
            if glued or len(stack) < 2:
                return None
            node = stack.pop()
            stack[-1].append((node[0], node[1:], char))
            pos += 1
            continue
        end = pos
        while end < len(line) and (mask[end] or not (line[end].isspace() or line[end] in '()[]{}')):
            end += 1
        if end == pos:
            end = pos + 1
        atom = glued + line[pos:end]
        if end < len(line) and not mask[end] and line[end] in '([{':
            glued = atom                   # 'x(, #( and ,@( prefixes join their list
        elif atom and atom[-1] in "'`," and not any(mask[pos:end]):
            glued = atom                   # quote prefix before an atom or list
        else:
            stack[-1].append(atom)
            glued = ''
        pos = end
    return stack[0] if len(stack) == 1 and not glued else None


def _flat(node):
    if isinstance(node, str):
        return node
    opener, items, closer = node
    return opener + ' '.join(map(_flat, items)) + closer


def _head(node):
    return node[1][0] if not isinstance(node, str) and node[1] and isinstance(node[1][0], str) else None


def _keep_on_one_line(node, column, top):
    if len(_flat(node)) + column > LAYOUT_WIDTH:
        return False
    if top and _head(node) in ('define', 'define-macro', 'defmacro') and len(node[1]) > 2:
        # Function definitions keep their name line separate from the body.
        return not isinstance(node[1][1], tuple)
    return True


def _layout(node, depth, top=False):
    """Lines (without indentation) for node; indent_lisp adds 2 spaces per depth."""
    if isinstance(node, str) or _keep_on_one_line(node, 2 * depth, top) or not node[1]:
        return [_flat(node)]
    opener, items, closer = node
    head = items[0]
    if isinstance(head, str):
        keep = _BODY_FORMS.get(head.lstrip("'`,@#"), 1)
        if head in ('let', 'let*', 'letrec') and len(items) > 1 and isinstance(items[1], str):
            keep = 2                       # named let
        first = [head] + items[1:1 + keep]
        rest = items[1 + keep:]
        # A leading argument that cannot stay on line one moves to its own line.
        if len(' '.join(map(_flat, first))) + 2 * depth + 1 > LAYOUT_WIDTH:
            first, rest = [head], items[1:]
    else:
        first, rest = [], items
    if first:
        lines = [opener + ' '.join(map(_flat, first))]
    else:                                  # e.g. a cond clause or let bindings
        lines = _layout(rest[0], depth + 1)
        lines[0] = opener + lines[0]
        rest = rest[1:]
    if first and head not in _BODY_FORMS and head != 'if' and all(isinstance(i, str) for i in rest):
        # A plain list of atoms (e.g. import names) is filled line by line.
        lines.append('')
        for item in rest:
            if lines[-1] and 2 * (depth + 1) + len(lines[-1]) + len(item) + 2 > LAYOUT_WIDTH:
                lines.append('')
            lines[-1] = (lines[-1] + ' ' + item).lstrip()
        rest = []
    for item in rest:
        lines.extend(_layout(item, depth + 1))
    lines[-1] += closer
    return lines


def layout_lisp(text, source_name='<buffer>', first_line=0, stop_line=None):
    """Break one-line function definitions and over-long lines into multiple lines.

    Only lines made entirely of complete forms, without comments, are touched;
    multi-line layout written by the user is kept. Indentation is left to indent_lisp.
    """
    mask = check_lisp(text, source_name)
    spans = _lisp.spans(text)
    comments = SH.code_mask(spans, len(text), tags=('comment',))
    depth, offset, output = 0, 0, []
    for number, line in enumerate(text.splitlines(keepends=True)):
        body = line.rstrip('\r\n')
        start = offset + len(body) - len(body.lstrip(' \t'))
        end = offset + len(body)
        # A trailing ; comment stays at the end of the form's first line.
        comment = next((i for i in range(start, end) if comments[i]), end)
        code = text[start:comment].rstrip(' \t')
        in_range = number >= first_line and (stop_line is None or number < stop_line)
        changed = False
        if in_range and code and (len(body) > LAYOUT_WIDTH or depth == 0):
            items = _layout_items(code, mask[start:start + len(code)])
            if items:
                lines = []
                for item in items:
                    lines.extend(_layout(item, depth, top=depth == 0))
                if len(lines) > len(items):
                    if comment < end:
                        lines[0] += ' ' + text[comment:end]
                    output.append('\n'.join(lines) + line[len(body):])
                    changed = True
        if not changed:
            output.append(line)
        for i, char in enumerate(line):
            if not mask[offset+i]:
                depth += (1 if char in '([{' else -1 if char in ')]}' else 0)
        offset += len(line)
    return ''.join(output)


def reindent_lisp(text, source_name='<buffer>', first_line=0, stop_line=None):
    """Lay out and indent lines first_line..stop_line (0-based, end exclusive).

    Returns the new text; lines outside the range keep their original form.
    """
    laid_out = layout_lisp(text, source_name, first_line, stop_line)
    formatted = indent_lisp(laid_out, source_name)
    if first_line == 0 and stop_line is None:
        return formatted
    original = text.splitlines(keepends=True)
    added = laid_out.count('\n') - text.count('\n')
    stop = len(original) if stop_line is None else stop_line
    new_lines = formatted.splitlines(keepends=True)
    return ''.join(original[:first_line] + new_lines[first_line:stop + added] + original[stop:])


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
        if tag != 'string' or not start <= offset <= end:
            continue
        token = text[start:end]
        try:
            if language.name == 'BBC BASIC':
                return token[1:-1].replace('""', '"')
            if language.name == 'Lisp':
                # File navigation also accepts paths pasted from Windows Explorer.
                quote = '"""' if token.startswith('"""') else '"'
                literal = token[len(quote):-len(quote)]
                if re.match(r'^[A-Za-z]:\\', literal) and '\\\\' not in literal:
                    return literal
                import lispy3
                value = lispy3.atom(token)
                return value.value if isinstance(value, lispy3.String) else None
            value = ast.literal_eval(token)
            return value if isinstance(value, str) else None
        except (ValueError, SyntaxError):
            return None
    return None

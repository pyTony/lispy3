"""Console value decoding for the Lispy BASIC INPUT statement."""
import csv
import math
import re
from contextlib import contextmanager
from contextvars import ContextVar


_reader = ContextVar('basic_console_reader', default=None)


@contextmanager
def input_from(reader):
    token = _reader.set(reader)
    try:
        yield
    finally:
        _reader.reset(token)


def read_line():
    reader = _reader.get()
    return reader() if reader is not None else input()


def _number(text):
    """BBC INPUT uses a numeric prefix, never evaluates an expression."""
    text = text.lstrip()
    hexadecimal = re.match(r'([+-]?)&([0-9a-fA-F]+)', text)
    if hexadecimal:
        return (-1 if hexadecimal[1] == '-' else 1) * int(hexadecimal[2], 16)
    match = re.match(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?', text)
    if not match:
        return 0
    value = float(match[0]) if any(c in match[0].lower() for c in '.e') else int(match[0])
    if not math.isfinite(value):
        raise ValueError('INPUT: number out of range')
    return value


def read_values(kinds, read_line, line_mode=False, question=True):
    values, pending = [], []
    for kind in kinds:
        if not pending:
            if question or values:
                print('?', end='', flush=True)
            text = read_line()
            if line_mode:
                pending = [text]
            else:
                try:
                    pending = next(csv.reader([text], skipinitialspace=True, strict=True)) or ['']
                except csv.Error as error:
                    raise ValueError(f'INPUT: {error}') from error
        value = pending.pop(0)
        if kind != ':str':
            value = _number(value)
            if kind == ':int':
                value = math.trunc(value)
        values.append(value)
    return values

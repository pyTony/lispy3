"""
syntax_highlight.py - file-driven syntax colouring for the Lispy Machine editor.

Each language lives in syntax/<name>.json:

  name          shown in the status bar
  extensions    file endings that pick this language, e.g. [".lisp"]
  line_comment  what Ctrl+/ puts in front of a line, e.g. ";"
  colors        tag -> "#rrggbb" foreground colour
  rules         ordered list of {"tag": ..., "pattern": regex}
  word_pattern  regex for a plain word (symbol / identifier)
  words         tag -> list of words that get that tag
  env_words     true: colour words the interpreter knows (builtin / variable)

The buffer is scanned once, left to right. At each position the first rule
that matches wins and its text is consumed, so a ; inside "a string" stays
part of the string and a " inside a ; comment stays part of the comment.
Words are matched last and coloured from the word lists.

This module has no tkinter dependency so it can be tested on its own.
"""
import json
import os
import re

from lispy_support import PROJECT_ROOT

SYNTAX_DIR = str(PROJECT_ROOT / "syntax")

# Used for any tag a language file names but gives no colour.
DEFAULT_COLORS = {
    "comment":  "#6a9955",
    "string":   "#ce9178",
    "char":     "#d7ba7d",
    "keyword":  "#c586c0",
    "special":  "#569cd6",
    "constant": "#569cd6",
    "number":   "#b5cea8",
    "builtin":  "#4ec9b0",
    "variable": "#9cdcfe",
    "function": "#dcdcaa",
    "decorator": "#dcdcaa",
}


class Language:
    def __init__(self, spec: dict, source: str = "<dict>"):
        self.source = source
        self.name = spec.get("name", os.path.splitext(os.path.basename(source))[0])
        self.extensions = [e.lower() for e in spec.get("extensions", [])]
        self.line_comment = spec.get("line_comment", "")
        self.env_words = bool(spec.get("env_words", False))
        self.case_insensitive = bool(spec.get("case_insensitive", False))

        self.words = {}                       # word -> tag (first list wins)
        for tag, words in spec.get("words", {}).items():
            for w in words:
                self.words.setdefault(w.casefold() if self.case_insensitive else w, tag)

        rules = list(spec.get("rules", []))
        parts, self._group_tags = [], {}
        for i, rule in enumerate(rules):
            re.compile(rule["pattern"])       # report a bad pattern on its own
            group = f"g{i}"
            parts.append(f"(?P<{group}>{rule['pattern']})")
            self._group_tags[group] = rule["tag"]
        if spec.get("word_pattern"):
            re.compile(spec["word_pattern"])
            parts.append(f"(?P<word>{spec['word_pattern']})")
        self.regex = re.compile("|".join(parts), re.IGNORECASE if self.case_insensitive else 0) if parts else None

        tags = set(self._group_tags.values()) | set(self.words.values())
        if self.env_words:
            tags |= {"builtin", "variable"}
        colors = spec.get("colors", {})
        self.colors = {t: colors.get(t, DEFAULT_COLORS.get(t, "#d4d4d4"))
                       for t in sorted(tags | set(colors))}

    def spans(self, text: str, builtins=frozenset(), variables=frozenset()):
        """Return [(tag, start, end), ...] for `text`, without overlaps."""
        out = []
        if self.regex is None:
            return out
        for m in self.regex.finditer(text):
            group = m.lastgroup
            if group == "word":
                w = m.group()
                tag = self.words.get(w.casefold() if self.case_insensitive else w)
                if tag is None and self.env_words:
                    if w in variables:
                        tag = "variable"
                    elif w in builtins:
                        tag = "builtin"
                if tag:
                    out.append((tag, m.start(), m.end()))
            elif m.end() > m.start():
                out.append((self._group_tags[group], m.start(), m.end()))
        return out


def load_language(path: str) -> Language:
    with open(path, encoding="utf-8") as f:
        return Language(json.load(f), source=path)


def load_languages(directory: str = SYNTAX_DIR):
    """Load every *.json in `directory`. Returns (languages, errors)."""
    langs, errors = [], []
    try:
        names = sorted(os.listdir(directory))
    except OSError as e:
        return langs, [f"{directory}: {e}"]
    for fn in names:
        if fn.lower().endswith(".json"):
            path = os.path.join(directory, fn)
            try:
                langs.append(load_language(path))
            except (OSError, ValueError, KeyError, re.error) as e:
                errors.append(f"{fn}: {e}")
    return langs, errors


def language_for(filename: str, languages, default=None):
    """Pick the language whose extensions match `filename`."""
    ext = os.path.splitext(filename or "")[1].lower()
    for lang in languages:
        if ext and ext in lang.extensions:
            return lang
    return default


def code_mask(spans, length: int, tags=("string", "comment", "char")):
    """Return a bytearray: 1 where text is inside one of `tags`, else 0."""
    mask = bytearray(length)
    for tag, s, e in spans:
        if tag in tags:
            mask[s:e] = b"\x01" * (e - s)
    return mask

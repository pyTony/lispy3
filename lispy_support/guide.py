"""
guide.py - the Lispy guide pages, turned from Markdown into styled text.

The Lispy3 Machine shows these pages in its Help window. Nothing here needs
tkinter: `render` turns Markdown into runs of (text, tags, link) that the
window inserts into a Text widget, and lists the headings for the contents.

Only the Markdown the docs use is understood: # headings, paragraphs,
- bullets, 1. numbered lists, indented and ``` code blocks, | tables |,
`code`, **bold**, [links](target) and --- rules.
"""
import os
import re

from lispy_support import PROJECT_ROOT

DOCS_DIR = str(PROJECT_ROOT / "docs")

# (title, file in docs/) in the order the guide lists them; None = the built-ins page
PAGES = [
    ("Quick start",      "QUICK_START.md"),
    ("Lispy by example", "LISPY_BY_EXAMPLE.md"),
    ("Quick reference",  "QUICK_REFERENCE.md"),
    ("Built-ins",        None),
]
BUILTINS_PAGE = "Built-ins"

INLINE = re.compile(r"`([^`]+)`|\*\*(.+?)\*\*|\[([^\]]+)\]\(([^)\s]+)\)")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
BULLET = re.compile(r"^(\s*)[-*+]\s+(.*)$")
NUMBERED = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
TABLE_RULE = re.compile(r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")
# A table's first column is padded to this many characters at most
MAX_FIRST_COLUMN = 30


def slug(title: str) -> str:
    """The #anchor GitHub gives a heading: "Choosing: if" -> "choosing-if"."""
    plain = INLINE.sub(lambda m: m.group(1) or m.group(2) or m.group(3), title)
    plain = re.sub(r"[^\w\- ]", "", plain.strip().lower())
    return plain.replace(" ", "-")


def builtins_markdown(topics) -> str:
    """The built-ins page, from lispy3.HELP_TOPICS: one table per topic."""
    lines = ["# Built-ins", "",
             "Every name Lispy knows, the same list `(help)` gives. "
             "`(help 'name)` in the Listener explains one name.", ""]
    for topic, entries in topics.items():
        lines += [f"## {topic}", "", "| Name | What it does |", "|---|---|"]
        for name, text in entries:
            lines.append(f"| `{name}` | {text.replace('|', '/')} |")
        lines.append("")
    return "\n".join(lines)


def load_page(title: str, topics=None, docs_dir: str = DOCS_DIR) -> str:
    """The Markdown of the guide page called `title`."""
    for page, filename in PAGES:
        if page == title:
            if filename is None:
                return builtins_markdown(topics or {})
            return read_markdown(os.path.join(docs_dir, filename))
    raise KeyError(title)


def read_markdown(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError) as e:
        return f"# {os.path.basename(path)}\n\nThis page could not be read: {e}\n"


def page_for_file(filename: str):
    """The guide page shown for a linked .md file, or None."""
    base = os.path.basename(filename)
    for page, name in PAGES:
        if name == base:
            return page
    return None


class Rendered:
    """A page as runs of styled text, plus its headings for the contents list."""

    def __init__(self):
        self.runs: list[tuple[str, tuple, str | None]] = []   # (text, tags, link target)
        self.headings: list[tuple[int, str, str, int]] = []  # (level, title, anchor, offset)
        self.anchors: dict[str, int] = {}                    # anchor -> character offset
        self.length = 0

    @property
    def text(self) -> str:
        return "".join(t for t, _, _ in self.runs)

    def add(self, text: str, tags=(), link=None):
        if text:
            self.runs.append((text, tuple(tags), link))
            self.length += len(text)

    def inline(self, text: str, tags=()):
        """Add `text` with its `code`, **bold** and [links] styled."""
        pos = 0
        for m in INLINE.finditer(text):
            self.add(text[pos:m.start()], tags)
            code, bold, label, target = m.groups()
            if code is not None:
                self.add(code, tags + ("code",))
            elif bold is not None:
                self.inline(bold, tags + ("bold",))
            else:
                self.add(label, tags + ("link",), target)
            pos = m.end()
        self.add(text[pos:], tags)


def plain_length(text: str) -> int:
    """How many characters `text` takes once its Markdown is rendered."""
    return len(INLINE.sub(lambda m: m.group(1) or m.group(2) or m.group(3), text))


def split_row(line: str) -> list[str]:
    """The cells of a | table | row; a | inside `code` does not split."""
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    cells, cell, in_code = [], "", False
    for ch in line:
        if ch == "`":
            in_code = not in_code
        if ch == "|" and not in_code:
            cells.append(cell.strip())
            cell = ""
        else:
            cell += ch
    cells.append(cell.strip())
    return cells


def render(markdown: str) -> Rendered:
    """Turn the Markdown of one guide page into styled runs."""
    out = Rendered()
    lines = markdown.replace("\t", "    ").split("\n")
    i, paragraph = 0, []

    def flush():
        if paragraph:
            out.inline(" ".join(s.strip() for s in paragraph))
            out.add("\n\n")
            paragraph.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            flush()
            i += 1
            block = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            out.add("\n".join(block) + "\n", ("codeblock",))
            out.add("\n")
            continue
        if line.startswith("    ") and not paragraph:
            block = []
            while i < len(lines) and (lines[i].startswith("    ") or not lines[i].strip()):
                block.append(lines[i][4:])
                i += 1
            while block and not block[-1].strip():
                block.pop()
            out.add("\n".join(block) + "\n", ("codeblock",))
            out.add("\n")
            continue
        if not stripped:
            flush()
            i += 1
            continue
        m = HEADING.match(line)
        if m:
            flush()
            level, title = len(m.group(1)), m.group(2)
            anchor = slug(title)
            out.headings.append((level, plain_text(title), anchor, out.length))
            out.anchors.setdefault(anchor, out.length)
            out.inline(title, (f"h{min(level, 3)}",))
            out.add("\n")
            i += 1
            continue
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", stripped):
            flush()
            out.add("\n", ("rule",))
            out.add("\n")
            i += 1
            continue
        if stripped.startswith("|") and i + 1 < len(lines) and TABLE_RULE.match(lines[i + 1].strip()):
            flush()
            rows = [split_row(line)]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            render_table(out, rows)
            continue
        m = BULLET.match(line) or NUMBERED.match(line)
        if m:
            flush()
            depth = len(m.group(1)) // 2
            if m.re is BULLET:
                mark, item = "•", m.group(2)
            else:
                mark, item = m.group(2) + ".", m.group(3)
            for box, sign in (("[x] ", "☑ "), ("[X] ", "☑ "), ("[ ] ", "☐ ")):
                if item.startswith(box):
                    item = sign + item[len(box):]
            i += 1
            while (i < len(lines) and lines[i].strip() and lines[i].startswith("  ")
                   and not BULLET.match(lines[i]) and not NUMBERED.match(lines[i])):
                item += " " + lines[i].strip()
                i += 1
            out.add(f"{mark} ", (f"item{min(depth, 2)}",))
            out.inline(item, (f"item{min(depth, 2)}",))
            out.add("\n")
            if i >= len(lines) or not (BULLET.match(lines[i]) or NUMBERED.match(lines[i])):
                out.add("\n")
            continue
        paragraph.append(line)
        i += 1
    flush()
    return out


def render_table(out: Rendered, rows: list[list[str]]):
    """A table as lines: the first column padded, the rest after it.

    Each line has the tag hangN, so a wrapped line lines up under the
    second column (N characters in).
    """
    width = min(max(plain_length(r[0]) for r in rows), MAX_FIRST_COLUMN)
    hang = f"hang{width + 2}"
    for n, row in enumerate(rows):
        tags = ("table", hang) + (("tablehead",) if n == 0 else ())
        first = row[0]
        out.inline(first, tags)
        out.add(" " * max(width - plain_length(first), 0) + "  ", tags)
        out.inline("  ·  ".join(c for c in row[1:] if c), tags)
        out.add("\n", tags)
    out.add("\n")


def plain_text(text: str) -> str:
    return INLINE.sub(lambda m: m.group(1) or m.group(2) or m.group(3), text)


def find_all(text: str, needle: str) -> list[int]:
    """Where `needle` starts in `text`, ignoring case."""
    if not needle:
        return []
    hay, needle = text.lower(), needle.lower()
    found, pos = [], hay.find(needle)
    while pos != -1:
        found.append(pos)
        pos = hay.find(needle, pos + 1)
    return found


def find_name(text: str, name: str):
    """Where the built-ins page's line for `name` starts, or None."""
    pos = text.find("\n" + name + " ")
    return None if pos == -1 else pos + 1

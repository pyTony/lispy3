"""Tests for guide.py, which turns the docs into the editor's Help window pages.

Run:  python -m unittest discover tests
"""
import unittest

from support import lispy3
import guide


class RenderTest(unittest.TestCase):
    def test_headings_get_github_anchors(self):
        page = guide.render("# Lispy\n\n## Choosing: if\n\ntext\n")
        self.assertEqual([h[:3] for h in page.headings],
                         [(1, "Lispy", "lispy"), (2, "Choosing: if", "choosing-if")])
        self.assertEqual(page.text[page.anchors["choosing-if"]:].split("\n")[0], "Choosing: if")

    def test_inline_code_bold_and_links(self):
        page = guide.render("Use `car` for **the head**, see [Quick Start](QUICK_START.md).\n")
        self.assertEqual(page.text, "Use car for the head, see Quick Start.\n\n")
        styled = {text: (tags, link) for text, tags, link in page.runs}
        self.assertEqual(styled["car"], (("code",), None))
        self.assertEqual(styled["the head"], (("bold",), None))
        self.assertEqual(styled["Quick Start"], (("link",), "QUICK_START.md"))

    def test_indented_and_fenced_code(self):
        page = guide.render("Try:\n\n    lispy3> (+ 1 2)\n    3\n\n```\n(car x)\n```\n")
        blocks = [text for text, tags, _ in page.runs if "codeblock" in tags]
        self.assertEqual(blocks, ["lispy3> (+ 1 2)\n3\n", "(car x)\n"])

    def test_table_lines_up_columns(self):
        page = guide.render("| Write | Meaning |\n|---|---|\n| `42` | a number |\n| `(f a b)` | a call |\n")
        lines = page.text.strip("\n").split("\n")
        self.assertEqual(lines, ["Write    Meaning", "42       a number", "(f a b)  a call"])

    def test_bar_inside_code_does_not_split_a_cell(self):
        self.assertEqual(guide.split_row("| `a|b` | c |"), ["`a|b`", "c"])

    def test_lists(self):
        page = guide.render("- one\n- [x] done\n1. first\n")
        self.assertEqual(page.text, "• one\n• ☑ done\n1. first\n\n")


class PagesTest(unittest.TestCase):
    def test_every_page_loads_and_has_headings(self):
        for title, _ in guide.PAGES:
            page = guide.render(guide.load_page(title, lispy3.HELP_TOPICS))
            self.assertTrue(page.headings, title)
            self.assertNotIn("could not be read", page.text, title)

    def test_builtins_page_lists_every_help_name(self):
        text = guide.render(guide.load_page(guide.BUILTINS_PAGE, lispy3.HELP_TOPICS)).text
        for entries in lispy3.HELP_TOPICS.values():
            for name, _ in entries:
                self.assertIsNotNone(guide.find_name(text, name), name)

    def test_links_between_docs_open_guide_pages(self):
        self.assertEqual(guide.page_for_file("QUICK_REFERENCE.md"), "Quick reference")
        self.assertIsNone(guide.page_for_file("../TODO.md"))

    def test_contents_links_match_headings(self):
        page = guide.render(guide.load_page("Lispy by example"))
        targets = [link[1:] for _, _, link in page.runs if link and link.startswith("#")]
        self.assertTrue(targets)
        for target in targets:
            self.assertIn(target, page.anchors)

    def test_search_ignores_case(self):
        self.assertEqual(guide.find_all("Car car CAR", "car"), [0, 4, 8])
        self.assertEqual(guide.find_all("abc", ""), [])


if __name__ == "__main__":
    unittest.main()

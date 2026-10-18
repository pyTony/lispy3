"""Tests for the right-click Cut / Copy / Paste menu in the Lispy Machine.

Run:  python -m unittest discover tests
"""
import unittest

from test_machine_args import machine


def enabled(has_selection, editable):
    """The labels of the menu items that can be chosen."""
    return [label for label, _, on in machine.context_menu_items(has_selection, editable) if on]


class ContextMenu(unittest.TestCase):
    def test_items_fire_the_usual_virtual_events(self):
        """Each item sends the event Ctrl+X, Ctrl+C, Ctrl+V or select all would."""
        events = [virtual for _, virtual, _ in machine.context_menu_items(True, True)]
        self.assertEqual(events, ["<<Cut>>", "<<Copy>>", "<<Paste>>", "<<SelectAll>>"])

    def test_editor_with_a_selection_offers_everything(self):
        """In an editor with text selected, all four items work."""
        self.assertEqual(enabled(True, True), ["Cut", "Copy", "Paste", "Select all"])

    def test_copy_needs_a_selection(self):
        """With nothing selected there is nothing to cut or copy."""
        self.assertEqual(enabled(False, True), ["Paste", "Select all"])

    def test_read_only_text_can_still_be_copied(self):
        """The Inspector, Listener transcript and Guide can be copied from, not changed."""
        self.assertEqual(enabled(True, False), ["Copy", "Select all"])


if __name__ == "__main__":
    unittest.main()

"""CLS control sequences must clear the Listener without printing a new prompt."""
from unittest import TestCase
from test_machine_args import machine


class _Output:
    def __init__(self):
        self.text = ''
        self.clears = 0

    def _ui_post(self, callback, *args):
        callback(*args)

    def listener_write(self, text, tag=None):
        self.text += text

    def _clear_listener_screen(self):
        self.text = ''
        self.clears += 1


class ListenerClsTest(TestCase):
    def test_cls_discards_previous_output_and_control_bytes(self):
        app = _Output()
        writer = machine._ListenerWriter(app)
        writer.write('old\n\x1b[2J\x1b[Hnew\n')
        self.assertEqual(app.text, 'new\n')
        self.assertEqual(app.clears, 1)

    def test_cls_split_across_writes_and_repeated(self):
        app = _Output()
        writer = machine._ListenerWriter(app)
        for character in 'old\x1b[2J\x1b[Hmiddle\x1b[2J\x1b[Hlast':
            self.assertEqual(writer.write(character), 1)
        self.assertEqual(app.text, 'last')
        self.assertEqual(app.clears, 2)

    def test_other_output_and_incomplete_controls_are_preserved(self):
        app = _Output()
        writer = machine._ListenerWriter(app)
        text = '\x1b[31mred\x1b[0m\x1b['
        writer.write(text)
        writer.flush()
        self.assertEqual(app.text, text)
        self.assertEqual(app.clears, 0)

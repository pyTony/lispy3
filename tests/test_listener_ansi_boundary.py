from unittest import TestCase
from unittest.mock import Mock
from test_machine_args import machine


class ListenerAnsiBoundaryTest(TestCase):
    def test_output_is_plain_even_when_sequences_span_writes(self):
        app=Mock()
        writer=machine._ListenerWriter(app)
        for part in ['hello \x1b[3','1mred','\x1b[0m\n','\x1b]0;hidden title','\x07world']:
            self.assertEqual(writer.write(part),len(part))
        text=''.join(call.args[1] for call in app._ui_post.call_args_list)
        self.assertEqual(text,'hello red\nworld')

    def test_unicode_and_whitespace_are_preserved(self):
        app=Mock()
        writer=machine._ListenerWriter(app)
        writer.write('ää\tλ\n')
        self.assertEqual(app._ui_post.call_args.args[1], 'ää\tλ\n')

    def test_direct_diagnostic_cannot_insert_ansi(self):
        app=Mock(console_ready=False)
        app.plain_repl.get.return_value=False
        machine.LispMachine.listener_write(app,'bad \x1b[31margument\x1b[0m','error')
        app.listener_text.insert.assert_called_once_with('end-1c','bad argument','error')

    def test_c1_and_string_controls_are_removed_incrementally(self):
        from lispy_support.listener_output import PlainTextOutput
        sink=PlainTextOutput()
        chunks=['a\x9b3','1mb\x1bPprivate',' data\x1b','\\c\x1b(Bd']
        self.assertEqual(''.join(sink.feed(part) for part in chunks),'abcd')

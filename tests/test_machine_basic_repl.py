from unittest.mock import Mock
from support import LispyTestCase, lispy3 as L
from test_machine_args import machine
from test_machine_stop import _FakeMachine
from basic_repl import BasicRepl


class BasicListenerTest(LispyTestCase):
    def test_prompt_identifies_basic(self):
        app=Mock(repl_pending='')
        app.basic_repl_mode.get.return_value=True
        self.assertEqual(machine.LispMachine._prompt_text(app), 'BASIC>')

    def test_feed_runs_on_worker_and_uses_private_session(self):
        app=_FakeMachine()
        app.current_tab=Mock(return_value=None)
        app._cache_current_buffer_for_basic=lambda: machine.LispMachine._cache_current_buffer_for_basic(app)
        app._get_basic_buffer_text=lambda: machine.LispMachine._get_basic_buffer_text(app)
        app.basic_repl=BasicRepl(L)
        self.addCleanup(app.basic_repl.close)
        app.listener_history=[]
        app._show_prompt=Mock()
        machine.LispMachine._basic_feed(app, ['30 PRINT "last"','10 PRINT "first"','RUN'])
        self.assertTrue(app.loop())
        self.assertEqual(''.join(app.lines), 'first\nlast\n')
        app._show_prompt.assert_called_once()
        self.assertEqual(app.basic_repl.source(), '10 PRINT "first"\n30 PRINT "last"\n')

    def test_to_buffer_exports_basic_program(self):
        app=Mock()
        app.basic_repl_mode.get.return_value=True
        app._busy.return_value=False
        app.basic_repl.source.return_value='10 PRINT 42\n'
        machine.LispMachine.listener_to_buffer(app)
        app.new_buffer.assert_called_once_with('basic-repl.bas','10 PRINT 42\n')

    def test_decoder_is_reused_for_tokenized_load(self):
        from pathlib import Path
        from unittest.mock import patch
        app=Mock(settings={'basic_python':'python-custom','basic_directory':'/mini'})
        with patch.object(machine.BR,'detokenize_bbc',return_value='10 PRINT 42') as decode:
            self.assertEqual(machine.LispMachine._read_basic_repl_source(app,Path('a.bbc')), '10 PRINT 42')
        decode.assert_called_once_with('a.bbc',executable='python-custom',package_root='/mini')

    def test_basic_keyword_tab_inserts_uppercase(self):
        app=Mock(console_ready=True)
        app.basic_repl_mode.get.return_value=True
        app.listener_text.get.return_value='pri'
        machine.LispMachine._listener_tab(app)
        app.listener_text.insert.assert_called_with('insert','PRINT ')

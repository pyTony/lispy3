import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch
from support import fresh_global_env
from test_machine_args import machine
from test_machine_eval_buffer import _FakeMachine


class StartupOptionsTest(TestCase):
    def setUp(self):
        fresh_global_env()

    def test_hidden_startup_uses_empty_buffer(self):
        app = Mock()
        app.tabs = {}
        app.startup_show_buffer.get.return_value = False
        machine.LispMachine._open_initial_buffers(app, ())
        app.new_buffer.assert_called_once_with('untitled.lisp', '', path=None)

    def test_shown_startup_preserves_current_default(self):
        app = Mock()
        app.tabs = {}
        app.startup_show_buffer.get.return_value = True
        with patch.object(machine, 'read_startup', return_value=('startup.lisp', '(+ 1 2)', '/startup.lisp')):
            machine.LispMachine._open_initial_buffers(app, ())
        app.new_buffer.assert_called_once_with('startup.lisp', '(+ 1 2)', path='/startup.lisp')

    def test_startup_runs_once_even_when_hidden(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'startup.lisp'
            path.write_text('(set! startup-counter (+ startup-counter 1))\n(define initialized 42)', encoding='utf-8')
            machine.L.global_env['startup-counter'] = 0
            app = _FakeMachine('')
            app.startup_run = Mock()
            app.startup_run.get.return_value = True
            app._startup_ran, app._job = False, None
            with patch.object(machine, 'STARTUP_FILE', str(path)):
                machine.LispMachine._run_startup(app)
                machine.LispMachine._run_startup(app)
            self.assertEqual(machine.L.global_env['startup-counter'], 1)
            self.assertEqual(machine.L.global_env['initialized'], 42)

    def test_disabled_startup_does_not_read_or_execute(self):
        app = Mock()
        app.startup_run.get.return_value = False
        app._startup_ran = False
        machine.LispMachine._run_startup(app)
        app._start.assert_not_called()

    def test_startup_errors_are_visible(self):
        app = _FakeMachine('')
        app.startup_run = Mock()
        app.startup_run.get.return_value = True
        app._startup_ran, app._job = False, None
        with patch.object(machine, 'STARTUP_FILE', '/missing/startup-file-for-test.lisp'):
            machine.LispMachine._run_startup(app)
        self.assertIn('startup.lisp', ''.join(app.lines))
        self.assertIn('Error', ''.join(app.lines))

    def test_explicit_files_still_open_when_startup_is_hidden(self):
        app = Mock()
        app.tabs = {}
        app.startup_show_buffer.get.return_value = False
        def open_tab(name, content, path):
            app.tabs[name] = Mock()
        app.new_buffer.side_effect = open_tab
        with patch.object(machine, 'read_file_arg', return_value=('demo.bas', 'PRINT 1', '/demo.bas')):
            machine.LispMachine._open_initial_buffers(app, ['demo.bas'])
        app.new_buffer.assert_called_once_with('demo.bas', 'PRINT 1', path='/demo.bas')

    def test_restart_does_not_restore_hidden_startup_buffer(self):
        app = Mock()
        tab = Mock(path=machine.STARTUP_FILE)
        tab.dirty = False
        app.tabs = {'startup.lisp': tab}
        app.startup_show_buffer.get.return_value = False
        app.plain_repl.get.return_value = False
        with patch.object(machine.subprocess, 'Popen') as launch:
            machine.LispMachine.restart(app)
        self.assertNotIn(machine.STARTUP_FILE, launch.call_args.args[0])

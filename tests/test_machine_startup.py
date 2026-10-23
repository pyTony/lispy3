import os
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


class ReopenLastSessionTest(TestCase):
    def _app(self, settings, reopen=True):
        app = Mock()
        app.tabs, app.settings = {}, settings
        app.startup_reopen_files.get.return_value = reopen
        app.startup_show_buffer.get.return_value = True
        app._reopen_last_session = lambda: machine.LispMachine._reopen_last_session(app)
        def open_tab(name, content, path):
            tab = Mock(name=name, path=path)
            app.tabs[name] = tab
            return tab
        app.new_buffer.side_effect = open_tab
        return app

    def test_reopens_saved_files_in_order_skipping_missing(self):
        with tempfile.TemporaryDirectory() as folder:
            a, b = Path(folder)/'a.lisp', Path(folder)/'b.lisp'
            a.write_text('(a)', encoding='utf-8')
            b.write_text('(b)', encoding='utf-8')
            app = self._app({'last_session_files': [str(a), str(Path(folder)/'gone.lisp'), str(b)],
                             'last_session_current': str(b)})
            errors = machine.LispMachine._open_initial_buffers(app, ())
        self.assertEqual(errors, [])
        self.assertEqual([c.args[0] for c in app.new_buffer.call_args_list], ['a.lisp', 'b.lisp'])
        app.notebook.select.assert_called_once_with(app.tabs['b.lisp'])

    def test_falls_back_to_startup_when_nothing_remains(self):
        app = self._app({'last_session_files': ['/missing/x.lisp']})
        with patch.object(machine, 'read_startup', return_value=('startup.lisp', '', '/startup.lisp')):
            machine.LispMachine._open_initial_buffers(app, ())
        app.new_buffer.assert_called_once_with('startup.lisp', '', path='/startup.lisp')

    def test_disabled_option_ignores_saved_files(self):
        with tempfile.TemporaryDirectory() as folder:
            a = Path(folder)/'a.lisp'
            a.write_text('(a)', encoding='utf-8')
            app = self._app({'last_session_files': [str(a)]}, reopen=False)
            with patch.object(machine, 'read_startup', return_value=('startup.lisp', '', '/startup.lisp')):
                machine.LispMachine._open_initial_buffers(app, ())
        app.new_buffer.assert_called_once_with('startup.lisp', '', path='/startup.lisp')

    def test_command_line_files_win_over_saved_session(self):
        app = self._app({'last_session_files': ['/somewhere/a.lisp']})
        with patch.object(machine, 'read_file_arg', return_value=('demo.lisp', '', '/demo.lisp')):
            machine.LispMachine._open_initial_buffers(app, ['demo.lisp'])
        app.new_buffer.assert_called_once_with('demo.lisp', '', path='/demo.lisp')

    def test_close_remembers_open_files_and_current_buffer(self):
        app = Mock()
        first, untitled, second = Mock(path='/x/a.lisp'), Mock(path=None, source_path=None), Mock(path='/x/b.lisp')
        app.tabs = {'a.lisp': first, 'untitled.lisp': untitled, 'b.lisp': second}
        app.tab_order = ['a.lisp', 'untitled.lisp', 'b.lisp']
        app.current_tab.return_value = second
        app.settings = {}
        with patch.object(machine, 'save_settings') as save:
            machine.LispMachine._remember_open_files(app)
        expected = [os.path.abspath('/x/a.lisp'), os.path.abspath('/x/b.lisp')]
        self.assertEqual(app.settings['last_session_files'], expected)
        self.assertEqual(app.settings['last_session_current'], expected[1])
        save.assert_called_once_with(app.settings)

from unittest import TestCase
from unittest.mock import patch
from support import lispy3 as L
from test_machine_args import machine


class StartupOverrideTest(TestCase):
    def test_cli_loads_temporary_startup_before_repl(self):
        with patch.object(L,'run_file',return_value=True) as load, patch.object(L,'repl') as repl:
            self.assertEqual(L.main(['--startup','custom setup.lisp']),0)
        load.assert_called_once_with('custom setup.lisp')
        repl.assert_called_once()

    def test_cli_missing_startup_argument_is_usage_error(self):
        with patch.object(L,'repl') as repl:
            self.assertEqual(L.main(['--startup']),2)
        repl.assert_not_called()

    def test_machine_passes_override_without_saving_settings(self):
        with patch.object(machine.sys,'argv',['lispy_machine.pyw','--repl','--startup','custom.lisp']), patch.object(machine,'LispMachine') as app, patch.object(machine,'save_settings') as save:
            machine.main()
        app.assert_called_once_with([],plain_repl=True,startup_file='custom.lisp')
        save.assert_not_called()

    def test_gui_executes_override_instead_of_default(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import Mock
        from support import fresh_global_env
        from test_machine_eval_buffer import _FakeMachine
        fresh_global_env()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'custom.lisp'
            path.write_text('(define custom-startup-marker 42)')
            app=_FakeMachine('')
            app.startup_file=str(path)
            app.startup_run=Mock()
            app.startup_run.get.return_value=True
            app._startup_ran=False
            app._job=None
            machine.LispMachine._run_startup(app)
            self.assertEqual(L.global_env['custom-startup-marker'],42)

    def test_failed_cli_startup_does_not_enter_repl(self):
        with patch.object(L,'run_file',return_value=False), patch.object(L,'repl') as repl:
            self.assertEqual(L.main(['--startup','missing.lisp']),1)
        repl.assert_not_called()

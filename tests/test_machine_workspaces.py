from unittest import TestCase
from unittest.mock import Mock
from test_machine_args import machine
from test_machine_eval_buffer import _FakeMachine
from support import lispy3 as L
from lispy_workspaces import WorkspaceManager

class MachineWorkspaceTest(TestCase):
    def setUp(self):
        self.saved = L.global_env, L.macro_table, L.library_system, L.workspaces
        L.workspaces = WorkspaceManager(L)
        L.workspaces.new()
    def tearDown(self):
        L.global_env, L.macro_table, L.library_system, L.workspaces = self.saved
    def test_fresh_basic_run_does_not_reuse_old_loop_counter(self):
        from test_machine_basic_buffer import _FakeMachine as BasicMachine
        app = BasicMachine('FOR I=1 TO 3:NEXT:PRINT I')
        machine.LispMachine.eval_buffer(app, basic=True, fresh=True)
        self.assertIn('4\n', ''.join(app.lines))
        with self.assertRaises(NameError): L.eval_exp(L.parse('I'))
        app.tab.content = 'PRINT I'
        app.lines.clear()
        machine.LispMachine.eval_buffer(app, basic=True, fresh=True)
        self.assertNotIn('4\n', ''.join(app.lines))
        self.assertIn('Undefined symbol: I', ''.join(app.lines))
    def test_fresh_lisp_run_has_no_previous_definition_but_results_remain(self):
        app = _FakeMachine('(define old-value 7)')
        machine.LispMachine.eval_buffer(app, fresh=True)
        self.assertEqual(L.eval_exp(L.parse('old-value')), 7)
        app.tab.content = '(define current-value 8)'
        machine.LispMachine.eval_buffer(app, fresh=True)
        with self.assertRaises(NameError): L.eval_exp(L.parse('old-value'))
        self.assertEqual(L.eval_exp(L.parse('current-value')), 8)
    def test_interactive_eval_reuses_active_workspace(self):
        app = _FakeMachine('(define count 1)')
        machine.LispMachine.eval_buffer(app, fresh=True)
        app.tab.content = '(set! count (+ count 1))'
        machine.LispMachine.eval_buffer(app)
        self.assertEqual(L.eval_exp(L.parse('count')), 2)
    def test_workspace_menu_action_does_not_touch_editor_buffers(self):
        app = Mock(); app._busy.return_value = False
        app._start.side_effect = lambda work: work()
        before = app.tabs
        L.global_env['stale'] = 9
        machine.LispMachine._workspace_action(app, 'new')
        self.assertNotIn('stale', L.global_env)
        self.assertIs(app.tabs, before)
        app.new_buffer.assert_not_called()

    def test_fresh_workspace_retains_gui_dispatch_and_interruptible_sleep(self):
        import threading
        import turtle_stub
        from unittest.mock import patch
        from test_machine_stop import _FakeMachine as WorkerMachine
        app = WorkerMachine()
        app.lisp_help = lambda *args: None
        calls = []
        with patch.object(turtle_stub, 'fd', side_effect=lambda *args: calls.append(threading.current_thread())):
            L.workspaces.add_initializer(lambda env: machine.LispMachine._initialize_workspace_env(app, env))
            L.workspaces.new()
            self.assertIs(L.global_env['sleep'].__self__, app)
            app._start(lambda: app._run('(fd 1)'), app.done)
            self.assertTrue(app.loop())
        self.assertEqual(calls, [threading.current_thread()])
        self.assertIsNone(app.results[-1][0][1])

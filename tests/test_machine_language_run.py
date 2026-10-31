from unittest import TestCase
from unittest.mock import Mock, patch
from support import fresh_global_env
from test_machine_eval_buffer import _FakeMachine
from test_machine_args import machine


class LanguageRunTest(TestCase):
    def setUp(self):
        fresh_global_env()

    def tearDown(self):
        machine.L.library_system.reset()
        fresh_global_env()

    def test_f6_basic_defaults_to_lispy_even_with_old_python_setting(self):
        from test_machine_basic_buffer import _FakeMachine as BasicMachine
        app = BasicMachine('PRINT "lispy-default"')
        app.tab.name = 'example.bas'
        app.settings = {'basic_backend': 'python'}
        with patch.object(machine.BR, 'run_python_basic') as external:
            machine.LispMachine.eval_buffer(app)
        external.assert_not_called()
        self.assertIn('lispy-default\n', ''.join(app.lines))

    def test_f5_basic_uses_lispy(self):
        app = _FakeMachine('PRINT 42')
        app.tab.name = 'example.bas'
        app.eval_basic_at_cursor = Mock()
        machine.LispMachine.eval_form_at_cursor(app)
        app.eval_basic_at_cursor.assert_called_once_with(backend='lispy')

    def test_f8_explicitly_chooses_python_basic(self):
        app = _FakeMachine('PRINT 42')
        app.eval_buffer = Mock()
        machine.LispMachine.eval_basic_buffer(app)
        app.eval_buffer.assert_called_once_with(basic=True, basic_backend='python')

    def test_f6_python_executes_python_instead_of_lisp_reader(self):
        app = _FakeMachine('print("python-output")')
        app.tab.name = 'example.py'
        def run(source, write, **kwargs):
            self.assertEqual(source, 'print("python-output")')
            write('python-output\n')
            return 0
        with patch.object(machine.BR, 'run_python_source', side_effect=run):
            machine.LispMachine.eval_buffer(app)
        self.assertIn('python-output\n', app.lines)

    def test_f5_python_uses_selected_source_and_line_offset(self):
        app = _FakeMachine('print(42)')
        app.tab.name = 'example.py'
        app.tab.text = Mock()
        app.tab.text.tag_ranges.return_value = ('7.0', '8.0')
        app.tab.text.get.return_value = 'print(42)'
        app.eval_buffer = Mock()
        machine.LispMachine.eval_form_at_cursor(app)
        app.eval_buffer.assert_called_once_with(python_source=True, source='print(42)', source_line=7)

    def test_python_basic_hold_status_is_success(self):
        app = _FakeMachine('PRINT 42')
        with patch.object(machine.BR, 'run_python_basic', return_value=10):
            machine.LispMachine.eval_buffer(app, basic=True, basic_backend='python')
        self.assertIn(';; Python mini_basic finished (console hold requested).\n', app.lines)

    def test_run_as_python_dialect_passes_dialect_once(self):
        app = _FakeMachine('PRINT 42')
        app.eval_buffer = lambda **kwargs: machine.LispMachine.eval_buffer(app, **kwargs)
        app.settings = {}
        with patch.object(machine.BR, 'run_python_basic', return_value=0) as external:
            machine.LispMachine.eval_basic_buffer_as(app, backend='python', dialect='mini')
            self.assertEqual(external.call_args.kwargs['dialect'], 'mini')
            machine.LispMachine.eval_buffer(app, basic=True, basic_backend='python')
            self.assertIsNone(external.call_args.kwargs['dialect'])
        self.assertEqual(app.settings, {})

    def test_run_as_menu_lists_mini_mbasic_and_bbc(self):
        labels = [label for label, _ in machine.BASIC_DIALECT_RUNS]
        self.assertTrue(any('MBASIC' in label for label in labels))
        self.assertTrue(any('mini dialect' in label for label in labels))
        self.assertTrue(any('BBC' in label for label in labels))

    def test_python_script_exit_10_is_not_basic_hold(self):
        app = _FakeMachine('raise SystemExit(10)')
        app.tab.name = 'example.py'
        with patch.object(machine.BR, 'run_python_source', return_value=10):
            machine.LispMachine.eval_buffer(app)
        self.assertIn(';; Python exited with status 10.\n', app.lines)

    def test_explicit_output_commands_choose_and_save_destination(self):
        for name, destination, terminal in [('eval_buffer_listener', 'listener', False),
                                             ('eval_buffer_in_terminal', 'ansi', True)]:
            app = Mock()
            getattr(machine.LispMachine, name)(app)
            app.basic_output.set.assert_called_once_with(destination)
            app._save_basic_settings.assert_called_once()
            app.eval_buffer.assert_called_once_with(terminal=terminal, fresh=True)


class PilLanguageRunTest(TestCase):
    def test_pil_description_buffer_explains_where_it_runs(self):
        app = _FakeMachine('read a dst $W\nretire\n')
        app.tab.name = 'add.pil'
        machine.LispMachine.eval_buffer(app)
        self.assertIn(machine.PIL_BUFFER_NOTE, app.lines)

    def test_f5_and_f6_assemble_x86_buffers(self):
        for run in (machine.LispMachine.eval_buffer, machine.LispMachine.eval_form_at_cursor):
            app = _FakeMachine('        org 100h\n')
            app.tab.name = 'hello.asm'
            app.run_asm_buffer = Mock()
            run(app)
            app.run_asm_buffer.assert_called_once_with(app.tab)

    def test_run_asm_buffer_launches_pil_frontend(self):
        import tempfile
        from pathlib import Path
        app = _FakeMachine('; pil-args: 30\n        org 100h\n')
        app.tab.name = 'factor.asm'
        with tempfile.TemporaryDirectory() as folder:
            program = Path(folder)/'FACTOR.COM'
            program.write_bytes(b'\xc3')
            with patch.object(machine.PE, 'assemble', return_value=program) as assemble, \
                 patch.object(machine.PE, 'launch_command', return_value=['py', '/pil/tools/dos_terminal.py']) as launch, \
                 patch.object(machine.subprocess, 'Popen') as popen:
                self.assertTrue(machine.LispMachine.run_asm_buffer(app, app.tab))
        assemble.assert_called_once()
        launch.assert_called_once_with(program, {'mode': 'dos', 'args': '30'})
        popen.assert_called_once()
        self.assertTrue(any('FACTOR.COM (1 bytes)' in line for line in app.lines))

    def test_run_asm_buffer_reports_nasm_error_line(self):
        app = _FakeMachine('        org 100h\n        mov ax,\n')
        app.tab.name = 'bad.asm'
        error = machine.PE.PilError('/tmp/x/bad.asm:2: error: invalid combination of opcode and operands')
        with patch.object(machine.PE, 'assemble', side_effect=error), \
             patch.object(machine.LispMachine, '_highlight_source_error') as highlight:
            self.assertFalse(machine.LispMachine.run_asm_buffer(app, app.tab))
        self.assertEqual(highlight.call_args[0][2].lineno, 2)
        self.assertTrue(any('invalid combination' in line for line in app.lines))

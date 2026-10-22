"""Output transport and terminal selection without opening real GUI windows."""
import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import socket
import threading
from unittest import TestCase
from unittest.mock import patch, MagicMock
import lispy_terminal as terminal
import basic_io


def which_of(*names):
    return lambda name: '/bin/'+name if name in names else None


class TerminalTransportTest(TestCase):
    def test_closed_terminal_during_input_reports_error(self):
        server, client = socket.socketpair()
        try:
            client.close()
            with self.assertRaisesRegex(terminal.TerminalError, 'closed.*input'):
                terminal._read_terminal_line(server, terminal._messages(server, interruptible=True))
        finally:
            server.close()

    def test_terminal_eof_during_input_is_reported(self):
        server, client = socket.socketpair()
        try:
            terminal._send_message(client, 'eof')
            with self.assertRaises(EOFError):
                terminal._read_terminal_line(server, terminal._messages(server, interruptible=True))
        finally:
            server.close()
            client.close()

    def test_viewer_input_notices_close_after_terminal_reset(self):
        server, client = socket.socketpair()
        try:
            terminal._send_message(server, 'output', '\x1b[0m')
            server.close()
            keyboard = MagicMock()
            keyboard.kbhit.return_value = False
            with patch.object(sys.stdin, 'isatty', return_value=True), patch.object(sys, 'platform', 'win32'), patch.dict(sys.modules, {'msvcrt': keyboard}), patch.object(sys, 'stdout', MagicMock()):
                with self.assertRaises(terminal._ViewerDisconnected):
                    terminal._console_read_line(client)
        finally:
            server.close()
            client.close()

    def test_stop_interrupts_terminal_input_wait_on_worker(self):
        from test_machine_stop import _FakeMachine
        app = _FakeMachine()
        requested, closed = threading.Event(), threading.Event()
        threads = []
        def launch(port, token, cwd):
            def peer():
                with socket.create_connection(('127.0.0.1', port), timeout=5) as connection:
                    connection.sendall(token.encode('ascii')+b'\n')
                    for message in terminal._messages(connection):
                        if message['type'] == 'input':
                            requested.set()
                closed.set()
            thread = threading.Thread(target=peer, daemon=True)
            thread.start()
            threads.append(thread)
        def evaluate():
            with terminal.ansi_terminal_output():
                return basic_io.read_line()
        with patch.object(terminal, 'launch_viewer', launch), patch.object(sys, '__stdout__', None):
            app._start(lambda: app._eval_with_turtle(evaluate), app.done)
            app.loop(seconds=0.3)
            self.assertTrue(requested.is_set(), 'worker did not request terminal input')
            app.stop()
            self.assertTrue(app.loop(), 'Stop did not interrupt terminal input')
        for thread in threads:
            thread.join(timeout=2)
        self.assertTrue(closed.is_set(), 'cancelled input left the connection open')
        self.assertTrue(app.results[-1][1])

    def test_real_viewer_returns_unicode_and_empty_input(self):
        processes = []
        def launch(port, token, cwd):
            process = subprocess.Popen([sys.executable, terminal.__file__, '--connect', str(port), '--token', token],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env=dict(os.environ, PYTHONIOENCODING='utf-8'))
            process.stdin.write('héllo, world\n\n'.encode('utf-8'))
            process.stdin.flush()
            processes.append(process)
            return process
        try:
            with patch.object(terminal, 'launch_viewer', launch), patch.object(sys, '__stdout__', None), contextlib.redirect_stdout(io.StringIO()), patch('builtins.input', side_effect=AssertionError('INPUT used the parent console')):
                with terminal.ansi_terminal_output():
                    print('Name? ', end='', flush=True)
                    first = basic_io.read_line()
                    print('Press Enter', end='', flush=True)
                    second = basic_io.read_line()
                    print('reply=['+first+']['+second+']')
            stdout, stderr = processes[0].communicate(timeout=10)
            self.assertEqual(processes[0].returncode, 0, stderr)
            self.assertEqual((first, second), ('héllo, world', ''))
            self.assertIn('reply=[héllo, world][]'.encode('utf-8'), stdout)
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.communicate()

    def test_existing_terminal_reads_from_its_input(self):
        stream = io.StringIO()
        stream.isatty = lambda: True
        with patch.object(terminal, 'launch_viewer') as launch, contextlib.redirect_stdout(stream), patch.object(sys.stdin, 'isatty', return_value=False), patch('builtins.input', return_value='45'):
            with terminal.ansi_terminal_output():
                self.assertEqual(basic_io.read_line(), '45')
            launch.assert_not_called()

    def test_gui_basic_input_uses_real_viewer_instead_of_listener(self):
        from test_machine_basic_buffer import _FakeMachine
        from test_machine_args import machine
        app = _FakeMachine('INPUT "LIMIT ",L\nPRINT ;L\nINPUT "PRESS ENTER",pause$\nPRINT "finished"')
        processes = []
        def launch(port, token, cwd):
            process = subprocess.Popen([sys.executable, terminal.__file__, '--connect', str(port), '--token', token],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env=dict(os.environ, PYTHONIOENCODING='utf-8'))
            process.stdin.write(b'45\n\n')
            process.stdin.flush()
            processes.append(process)
        try:
            with patch.object(terminal, 'launch_viewer', launch), patch.object(sys, '__stdout__', None), contextlib.redirect_stdout(io.StringIO()), patch.object(machine.LispMachine, '_begin_basic_input', side_effect=AssertionError('ANSI INPUT opened Listener input')):
                machine.LispMachine.eval_buffer(app, basic=True, terminal=True)
            stdout, stderr = processes[0].communicate(timeout=10)
            self.assertEqual(processes[0].returncode, 0, stderr)
            self.assertIn(b'LIMIT ?45\nPRESS ENTER?finished\n', stdout)
            self.assertNotIn('Error:', ''.join(app.lines))
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.communicate()

    def test_real_viewer_receives_ansi_and_unicode(self):
        processes = []
        def launch(port, token, cwd):
            process = subprocess.Popen([sys.executable, terminal.__file__, '--connect', str(port), '--token', token],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            processes.append(process)
            return process
        try:
            with patch.object(terminal, 'launch_viewer', launch), patch.object(sys, '__stdout__', None), contextlib.redirect_stdout(io.StringIO()):
                with terminal.ansi_terminal_output():
                    print('\x1b[31mhéllo\x1b[0m')
            stdout, stderr = processes[0].communicate(timeout=10)
            self.assertEqual(processes[0].returncode, 0, stderr)
            self.assertIn('\x1b[31mhéllo\x1b[0m\n'.encode(), stdout)
            self.assertTrue(stdout.endswith(b'\x1b[0m'))
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.communicate()

    def test_existing_terminal_is_reused_and_nested_calls_do_not_launch(self):
        stream = io.StringIO()
        stream.isatty = lambda: True
        with patch.object(terminal, 'launch_viewer') as launch, contextlib.redirect_stdout(stream):
            with terminal.ansi_terminal_output():
                with terminal.ansi_terminal_output():
                    print('same workspace')
            launch.assert_not_called()
        self.assertEqual(stream.getvalue(), 'same workspace\n\x1b[0m')
        self.assertFalse(terminal.terminal_output_active())

    def test_hold_waits_for_explicit_enter_after_end_of_output(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.recv.return_value = b''
        output = MagicMock()
        with patch.object(terminal.socket, 'create_connection', return_value=connection), patch.object(sys, 'stdout', output), patch.object(sys.stdin, 'isatty', return_value=True), patch('builtins.input', return_value='') as enter:
            terminal.viewer(1234, 'token', hold=True)
        enter.assert_called_once()
        self.assertIn('Press Enter to close', enter.call_args.args[0])

    def test_hold_keeps_connection_errors_visible_too(self):
        with patch.object(terminal.socket, 'create_connection', side_effect=OSError('not connected')), patch.object(sys, 'stdout', MagicMock()), patch.object(sys.stdin, 'isatty', return_value=True), patch('builtins.input', return_value='') as enter, contextlib.redirect_stderr(io.StringIO()) as errors:
            with self.assertRaises(OSError):
                terminal.viewer(1234, 'token', hold=True)
        enter.assert_called_once()
        self.assertIn('not connected', errors.getvalue())


class ViewerCommandTest(TestCase):
    viewer = ['python', '/work path/viewer.py', '--connect', '1234', '--token', 'token', '--hold']

    def command(self, platform, *found, **env):
        return terminal.viewer_command('/work path', self.viewer, platform, which_of(*found), env)

    def test_windows_console_and_windows_terminal(self):
        self.assertEqual(self.command('win32'), self.viewer)
        self.assertEqual(self.command('win32', 'wt.exe'), ['wt.exe', '-w', 'new', '-d', '/work path', *self.viewer])

    def test_linux_argv_preserves_paths_and_hold(self):
        self.assertEqual(self.command('linux', 'gnome-terminal'), ['gnome-terminal', '--working-directory=/work path', '--', *self.viewer])
        self.assertEqual(self.command('linux', 'xterm'), ['xterm', '-e', *self.viewer])
        self.assertEqual(self.command('linux', 'kitty'), ['kitty', '--directory', '/work path', *self.viewer])

    def test_wsl_windows_terminal_runs_linux_interpreter(self):
        self.assertEqual(self.command('linux', 'wt.exe', WSL_DISTRO_NAME='Ubuntu'),
                         ['wt.exe', '-w', 'new', 'wsl.exe', '--distribution', 'Ubuntu', '--cd', '/work path', '--exec', *self.viewer])

    def test_missing_terminal_is_a_clear_error(self):
        with self.assertRaisesRegex(terminal.TerminalError, 'no terminal emulator'):
            self.command('linux')

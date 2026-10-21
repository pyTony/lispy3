"""Real-terminal stdout routing, shared by lispy3 and Lispy Machine.

The viewer receives UTF-8 output over an authenticated loopback socket. Lisp
continues evaluating in its original process/environment; input is not rerouted.
"""
import contextlib
from contextvars import ContextVar
import ctypes
import io
import json
import os
from pathlib import Path
import secrets
import shlex
import shutil
import socket
import subprocess
import sys


class TerminalError(RuntimeError):
    pass


LINUX_TERMINALS = (
    ('x-terminal-emulator', ()),
    ('gnome-terminal', ('--working-directory={cwd}',)),
    ('konsole', ('--workdir', '{cwd}')),
    ('xfce4-terminal', ('--working-directory={cwd}',)),
    ('mate-terminal', ('--working-directory={cwd}',)),
    ('lxterminal', ('--working-directory={cwd}',)),
    ('alacritty', ('--working-directory', '{cwd}')),
    ('kitty', ('--directory', '{cwd}')),
    ('xterm', ()),
)


def terminal_command(cwd, platform=sys.platform, which=shutil.which, env=os.environ):
    """Open an ordinary shell; preserve View > Open terminal behavior."""
    if platform == 'win32':
        return ['wt.exe', '-d', cwd] if which('wt.exe') else [env.get('COMSPEC', 'cmd.exe')]
    if platform == 'darwin':
        return ['open', '-a', 'Terminal', cwd]
    if env.get('TERMINAL') and which(env['TERMINAL']):
        return [env['TERMINAL']]
    for program, args in LINUX_TERMINALS:
        if which(program):
            return [program] + [a.format(cwd=cwd) for a in args]
    if env.get('WSL_DISTRO_NAME'):
        if which('wt.exe'):
            return ['wt.exe', 'wsl.exe', '--cd', cwd]
        if which('cmd.exe'):
            return ['cmd.exe', '/c', 'start', 'wsl.exe', '--cd', cwd]
    return None


def console_python(executable=sys.executable, platform=sys.platform):
    if platform == 'win32' and Path(executable).name.lower() == 'pythonw.exe':
        console = Path(executable).with_name('python.exe')
        if not console.is_file():
            raise TerminalError('ANSI terminal: python.exe is missing beside pythonw.exe')
        return str(console)
    return executable


def viewer_command(cwd, viewer, platform=sys.platform, which=shutil.which, env=os.environ):
    """Build argv, never a shell-interpolated command for Windows or Linux."""
    if platform == 'win32':
        if which('wt.exe'):
            return ['wt.exe', '-w', 'new', '-d', cwd, *viewer]
        return list(viewer)  # Popen supplies CREATE_NEW_CONSOLE.
    if platform == 'darwin':
        # AppleScript requires a string; quote shell arguments before encoding it.
        command = 'cd '+shlex.quote(cwd)+' && exec '+shlex.join(viewer)
        return ['osascript', '-e', 'tell application "Terminal" to activate', '-e',
                'tell application "Terminal" to do script '+json.dumps(command, ensure_ascii=False)]
    terminal = terminal_command(cwd, platform, which, env)
    if terminal is None:
        raise TerminalError('ANSI terminal: no terminal emulator found; set TERMINAL or start Lispy from a terminal')
    name = Path(terminal[0]).name
    if name in ('wt.exe', 'cmd.exe') and env.get('WSL_DISTRO_NAME'):
        wsl = ['wsl.exe', '--distribution', env['WSL_DISTRO_NAME'], '--cd', cwd, '--exec', *viewer]
        if name == 'wt.exe':
            return ['wt.exe', '-w', 'new', *wsl]
        return ['cmd.exe', '/c', 'start', *wsl]
    if name == 'gnome-terminal':
        return [*terminal, '--', *viewer]
    if name in ('xfce4-terminal', 'mate-terminal'):
        return [*terminal, '-x', *viewer]
    if name == 'lxterminal':
        return [*terminal, '-e', shlex.join(viewer)]
    if name == 'kitty':
        return [*terminal, *viewer]
    return [*terminal, '-e', *viewer]


_active = ContextVar('lispy_ansi_terminal_output', default=False)


def terminal_output_active():
    return _active.get()


class TerminalWriter(io.TextIOBase):
    def __init__(self, connection):
        self.connection = connection

    @property
    def encoding(self):
        return 'utf-8'

    def writable(self):
        return True

    def isatty(self):
        return True

    def write(self, text):
        try:
            self.connection.sendall(text.encode('utf-8', errors='replace'))
        except OSError as error:
            raise TerminalError('ANSI terminal was closed while the program was writing') from error
        return len(text)

    def flush(self):
        pass


def launch_viewer(port, token, cwd):
    viewer = [console_python(), str(Path(__file__).resolve()), '--connect', str(port), '--token', token, '--hold']
    command = viewer_command(cwd, viewer)
    flags = getattr(subprocess, 'CREATE_NEW_CONSOLE', 0) if sys.platform == 'win32' else 0
    try:
        return subprocess.Popen(command, cwd=cwd, creationflags=flags)
    except OSError as error:
        raise TerminalError(f'Could not open ANSI terminal: {error}') from error


@contextlib.contextmanager
def ansi_terminal_output(timeout=10):
    """Route output to a terminal, retaining the current evaluator and workspace."""
    if _active.get():
        yield
        return
    token = _active.set(True)
    try:
        stream = sys.stdout
        if not getattr(stream, 'isatty', lambda: False)():
            stream = sys.__stdout__
        if stream is not None and getattr(stream, 'isatty', lambda: False)():
            _enable_windows_ansi()
            with contextlib.redirect_stdout(stream):
                try:
                    yield
                finally:
                    stream.write('\x1b[0m')
                    stream.flush()
            return
        with socket.socket() as server:
            server.bind(('127.0.0.1', 0))
            server.listen(1)
            server.settimeout(timeout)
            secret = secrets.token_hex(16)
            launch_viewer(server.getsockname()[1], secret, os.getcwd())
            try:
                connection, _ = server.accept()
            except TimeoutError as error:
                raise TerminalError('ANSI terminal did not connect; check the terminal emulator') from error
            with connection:
                connection.settimeout(timeout)
                handshake = bytearray()
                try:
                    while len(handshake) <= len(secret):
                        byte = connection.recv(1)
                        if not byte or byte == b'\n':
                            break
                        handshake.extend(byte)
                except OSError as error:
                    raise TerminalError('ANSI terminal did not authenticate') from error
                if not secrets.compare_digest(bytes(handshake), secret.encode('ascii')):
                    raise TerminalError('ANSI terminal authentication failed')
                connection.settimeout(None)
                with contextlib.redirect_stdout(TerminalWriter(connection)):
                    try:
                        yield
                    finally:
                        # Restore the viewer's terminal even if Lisp raises or is stopped.
                        try:
                            connection.sendall(b'\x1b[0m')
                        except OSError:
                            pass
    finally:
        _active.reset(token)


def call_with_ansi_terminal(thunk):
    with ansi_terminal_output():
        return thunk()


def _enable_windows_ansi():
    if sys.platform == 'win32':
        kernel = ctypes.windll.kernel32
        kernel.GetStdHandle.restype = ctypes.c_void_p
        kernel.GetConsoleMode.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        kernel.SetConsoleMode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        handle = kernel.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if kernel.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel.SetConsoleMode(handle, mode.value | 4)


def viewer(port, token, hold=False):
    _enable_windows_ansi()
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=10) as connection:
            connection.sendall(token.encode('ascii')+b'\n')
            connection.settimeout(None)
            while data := connection.recv(65536):
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
    except Exception as error:
        print(f'ANSI terminal error: {error}', file=sys.stderr)
        raise
    finally:
        sys.stdout.buffer.write(b'\x1b[0m')
        sys.stdout.buffer.flush()
        if hold and sys.stdin.isatty():
            input('\nProgram output finished. Press Enter to close this terminal. ')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Lispy ANSI terminal output viewer')
    parser.add_argument('--connect', type=int, required=True)
    parser.add_argument('--token', required=True)
    parser.add_argument('--hold', action='store_true')
    args = parser.parse_args()
    viewer(args.connect, args.token, args.hold)

"""Real-terminal stdout routing, shared by lispy3 and Lispy Machine.

The viewer exchanges output and input requests over an authenticated loopback
socket. Lisp continues evaluating in its original process/environment.
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
import select
import threading
import time
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lispy_support import basic_io


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
_input_reader = ContextVar('lispy_ansi_terminal_input', default=None)


def terminal_output_active():
    return _active.get()


def _send_message(connection, kind, text=''):
    connection.sendall((json.dumps({'type': kind, 'text': text}, ensure_ascii=False)+'\n').encode('utf-8', errors='replace'))


def _messages(connection, interruptible=False):
    pending = bytearray()
    while True:
        if interruptible and not select.select([connection], [], [], 0.05)[0]:
            continue
        data = connection.recv(65536)
        if not data:
            return
        pending.extend(data)
        while b'\n' in pending:
            line, _, rest = pending.partition(b'\n')
            pending = bytearray(rest)
            yield json.loads(line.decode('utf-8'))


def _read_terminal_line(connection, replies):
    try:
        _send_message(connection, 'input')
        reply = next(replies, None)
    except OSError as error:
        raise TerminalError('ANSI terminal was closed while waiting for input') from error
    if reply is None:
        raise TerminalError('ANSI terminal was closed while waiting for input')
    if reply['type'] == 'eof':
        raise EOFError('End of input in ANSI terminal')
    if reply['type'] != 'input':
        raise TerminalError('Unexpected ANSI terminal input response')
    return reply['text']


def read_line():
    reader = _input_reader.get()
    if reader is None:
        raise TerminalError('ANSI terminal input is not connected')
    return reader()


class _ViewerDisconnected(Exception):
    pass


def _console_read_line(connection=None):
    """Read a terminal line with short waits so Stop/disconnection can interrupt."""
    if not sys.stdin.isatty():
        return input()
    chars = []
    pending = bytearray()
    while True:
        if connection is not None and select.select([connection], [], [], 0)[0]:
            data = connection.recv(65536)
            if not data:
                raise _ViewerDisconnected()
            # Stop can deliver the final terminal reset before closing the
            # connection. Drain it so buffered output cannot hide the EOF.
            pending.extend(data)
            while b'\n' in pending:
                line, _, rest = pending.partition(b'\n')
                pending = bytearray(rest)
                message = json.loads(line.decode('utf-8'))
                if message['type'] == 'output':
                    sys.stdout.buffer.write(message['text'].encode('utf-8', errors='replace'))
                    sys.stdout.buffer.flush()
        if sys.platform == 'win32':
            import msvcrt
            if not msvcrt.kbhit():
                time.sleep(0.05)
                continue
            char = msvcrt.getwch()
            if char in ('\x00', '\xe0'):
                msvcrt.getwch()
            elif char in ('\r', '\n'):
                print()
                return ''.join(chars)
            elif char == '\x03':
                raise KeyboardInterrupt
            elif char in ('\x04', '\x1a'):
                raise EOFError('End of input in ANSI terminal')
            elif char == '\b':
                if chars:
                    chars.pop()
                    print('\b \b', end='', flush=True)
            else:
                chars.append(char)
                print(char, end='', flush=True)
        elif select.select([sys.stdin], [], [], 0.05)[0]:
            return input()


# Program output is joined until this many characters are waiting (or a short
# delay passes) before the Listener or terminal shows it. 0 shows every write.
output_buffer = 256


class TerminalWriter(io.TextIOBase):
    """Send program output to the viewer, joining writes made within a short delay.

    One message per character made the viewer redraw its console for each one,
    so a program printing a character at a time ran far slower than its work.
    """
    delay = 0.03

    def __init__(self, connection):
        self.connection = connection
        self._lock = threading.Lock()
        self._pending = []
        self._size = 0
        self._timer = None
        self._error = None

    @property
    def encoding(self):
        return 'utf-8'

    def writable(self):
        return True

    def isatty(self):
        return True

    def write(self, text):
        if self._error is not None:
            raise TerminalError('ANSI terminal was closed while the program was writing') from self._error
        with self._lock:
            self._pending.append(text)
            self._size += len(text)
            full = self._size >= max(output_buffer, 1)
            if not full and self._timer is None:
                self._timer = threading.Timer(self.delay, self._send_later)
                self._timer.daemon = True
                self._timer.start()
        if full:
            self.flush()
        return len(text)

    def _send_later(self):
        try:
            self.flush()
        except TerminalError:
            pass                                 # the next write reports it

    def flush(self):
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            text, self._pending, self._size = ''.join(self._pending), [], 0
            if not text:
                return
            try:
                _send_message(self.connection, 'output', text)
            except OSError as error:
                self._error = error
                raise TerminalError('ANSI terminal was closed while the program was writing') from error


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
            input_token = _input_reader.set(_console_read_line)
            with contextlib.redirect_stdout(stream), basic_io.input_from(read_line):
                try:
                    yield
                finally:
                    _input_reader.reset(input_token)
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
                replies = _messages(connection, interruptible=True)
                writer = TerminalWriter(connection)
                def read_terminal_line():
                    writer.flush()                       # the prompt comes before the input request
                    return _read_terminal_line(connection, replies)
                input_token = _input_reader.set(read_terminal_line)
                with contextlib.redirect_stdout(writer), basic_io.input_from(read_line):
                    try:
                        yield
                    finally:
                        _input_reader.reset(input_token)
                        # Restore the viewer's terminal even if Lisp raises or is stopped.
                        try:
                            writer.write('\x1b[0m')
                            writer.flush()
                        except TerminalError:
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
            for message in _messages(connection):
                if message['type'] == 'output':
                    sys.stdout.buffer.write(message['text'].encode('utf-8', errors='replace'))
                    sys.stdout.buffer.flush()
                elif message['type'] == 'input':
                    try:
                        line = _console_read_line(connection)
                    except EOFError:
                        _send_message(connection, 'eof')
                    else:
                        _send_message(connection, 'input', line)
    except _ViewerDisconnected:
        hold = False
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

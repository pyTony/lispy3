"""Drive Tony's PIL x86 engine (pyTony/PIL-Processor-Instruction-Language) from Lispy.

PIL itself stays in its own Rust project. Lispy starts the built `pil`
executable as `pil --debug-service` and talks the same newline-delimited JSON
protocol (protocol 1) that PIL's own Tk debugger, tools/pil_debugger.py, uses:
one command line in, one JSON snapshot line out. Nothing of the CPU, the PIL
descriptions or DOS is duplicated here.

The Machine's PIL Settings set DIRECTORY (a PIL checkout) and ENGINE (an
explicit executable); the environment variables PIL_DIRECTORY and PIL_ENGINE
do the same for lispy3.py on the command line.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import atexit
import threading

from lispy_support import PROJECT_ROOT

PROTOCOL = 1
MAX_REPLY = 262144
SERVICE_RUN_LIMIT = 256          # the engine's largest `run N` in service mode
# Statuses after which running further only repeats the same stop
STOPPED = {'breakpoint', 'waiting_rx', 'halt', 'fault', 'decode', 'missing_instruction', 'error'}
REGISTERS = ('eax', 'ecx', 'edx', 'ebx', 'esp', 'ebp', 'esi', 'edi')
FOLDER_NAMES = ('PIL-Processor-Instruction-Language', 'PIL', 'pil')

DIRECTORY = ''
ENGINE = ''
NASM = ''


class PilError(RuntimeError):
    """The engine refused a command, or the engine could not be found or understood."""


def executable_name() -> str:
    return 'pil.exe' if sys.platform == 'win32' else 'pil'


def default_directory() -> str:
    """A PIL checkout beside the Lispy folder, if there is one."""
    for name in FOLDER_NAMES:
        candidate = PROJECT_ROOT.parent / name
        if (candidate / 'Cargo.toml').is_file() and (candidate / 'isa').is_dir():
            return str(candidate)
    return ''


def builds_in(directory) -> list[Path]:
    """Built engines inside a PIL checkout, newest first."""
    root = Path(directory)
    name = executable_name()
    found = [root / name]
    for target in ('target', 'target/windows'):
        found += [root / target / 'release' / name, root / target / 'debug' / name]
    found = [path.resolve() for path in found if path.is_file()]
    return sorted(found, key=lambda path: path.stat().st_mtime, reverse=True)


def find_engine(engine: str = '', directory: str = '') -> Path:
    """The pil executable: explicit setting, then the PIL folder's newest build, then PATH."""
    engine = engine or ENGINE or os.environ.get('PIL_ENGINE', '')
    if engine:
        path = Path(engine).expanduser()
        if not path.is_file():
            raise PilError(f'PIL executable not found: {path}')
        return path.resolve()
    directory = directory or DIRECTORY or os.environ.get('PIL_DIRECTORY', '') or default_directory()
    if directory:
        builds = builds_in(Path(directory).expanduser())
        if builds:
            return builds[0]
    on_path = shutil.which('pil')
    if on_path:
        return Path(on_path).resolve()
    where = f' in {directory}' if directory else ''
    raise PilError(f'No built PIL engine found{where}. Build PIL with cargo build --release, '
                   'or choose the folder or executable in Eval > PIL > PIL Settings.')


def find_tool(name: str, directory: str = '') -> Path:
    """A Python frontend from the PIL checkout's tools folder (dev branch)."""
    directory = directory or DIRECTORY or os.environ.get('PIL_DIRECTORY', '') or default_directory()
    path = Path(directory).expanduser() / 'tools' / name if directory else None
    if path is None or not path.is_file():
        raise PilError(f'tools/{name} not found. Choose a PIL checkout of the dev branch in PIL Settings.')
    return path.resolve()


# --- x86 assembly buffers: NASM builds them, PIL runs them -----------------

# Comment lines NASM ignores and Lispy reads:  ; pil: dos | monitor   ; pil-args: 30
RUN_COMMENT = re.compile(r'^[ \t]*;[ \t]*pil(-args)?[ \t]*:[ \t]*(.*?)[ \t]*$', re.IGNORECASE | re.MULTILINE)
RUN_MODES = ('dos', 'monitor')
NASM_ERROR = re.compile(r'^(?:.*?):(\d+): (?:error|fatal)', re.MULTILINE)


def run_options(source: str) -> dict:
    """How to launch an assembled buffer: DOS .COM (default) or the monitor's raw image."""
    options = {'mode': 'dos', 'args': ''}
    for match in RUN_COMMENT.finditer(source):
        if match[1]:
            options['args'] = match[2]
        else:
            mode = match[2].split()[0].lower() if match[2].split() else ''
            if mode not in RUN_MODES:
                raise PilError(f'Unknown "; pil: {match[2]}" line: use ; pil: dos or ; pil: monitor')
            options['mode'] = mode
    return options


def find_nasm(nasm: str = '') -> Path:
    nasm = nasm or NASM or os.environ.get('NASM', '')
    if nasm:
        path = Path(nasm).expanduser()
        if not path.is_file():
            raise PilError(f'NASM not found: {path}')
        return path.resolve()
    found = shutil.which('nasm')
    if found:
        return Path(found).resolve()
    for folder in (os.environ.get('ProgramFiles', r'C:\Program Files'), os.environ.get('LOCALAPPDATA', '')):
        if folder:
            for candidate in (Path(folder) / 'NASM' / 'nasm.exe', Path(folder) / 'bin' / 'NASM' / 'nasm.exe'):
                if candidate.is_file():
                    return candidate.resolve()
    raise PilError('NASM not found. Install it from nasm.us, or choose nasm.exe in Eval > PIL > PIL Settings.')


def nasm_error_line(message: str):
    """The first source line NASM reports an error on, or None."""
    match = NASM_ERROR.search(message)
    return int(match[1]) if match else None


def assemble(source: str, *, cwd, name: str = 'buffer', nasm: str = '') -> Path:
    """Assemble unsaved buffer text with `nasm -f bin`; %include and incbin search cwd."""
    stem = re.sub(r'[^A-Za-z0-9_-]', '', Path(name).stem)[:8].upper() or 'BUFFER'
    folder = Path(tempfile.mkdtemp(prefix='lispy-pil-'))
    source_path = folder / (stem.lower() + '.asm')
    source_path.write_text(source, encoding='utf-8')
    output = folder / (stem + '.COM')
    include = str(Path(cwd).resolve()) + os.sep
    try:
        result = subprocess.run([str(find_nasm(nasm)), '-f', 'bin', '-i', include, str(source_path), '-o', str(output)],
            cwd=str(cwd), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if sys.platform == 'win32' else 0)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise PilError(f'Cannot run NASM: {error}') from None
    if result.returncode or not output.is_file():
        raise PilError((result.stderr or result.stdout).strip() or f'NASM failed with status {result.returncode}')
    return output


def launch_command(program, options: dict, *, engine=None, python=None) -> list[str]:
    """The PIL frontend command that runs an assembled program."""
    engine = str(engine or find_engine())
    python = python or sys.executable
    if options['mode'] == 'monitor':
        return [python, str(find_tool('pil_debugger.py')), '--engine', engine, '--load', str(program)]
    command = [python, str(find_tool('dos_terminal.py')), '--engine', engine]
    if options.get('args'):
        command += ['--args', options['args']]
    return command + [str(program)]


def decode_reply(line: str, expected_seq: int) -> dict:
    """Check one service reply the same way PIL's own debugger frontend does."""
    if len(line.encode('utf-8')) > MAX_REPLY or not line.endswith('\n'):
        raise PilError('Oversized or incomplete PIL reply')
    try:
        message = json.loads(line)
    except ValueError as error:
        raise PilError(f'PIL reply is not JSON: {error}') from None
    if (not isinstance(message, dict) or message.get('protocol') != PROTOCOL
            or message.get('seq') != expected_seq or not isinstance(message.get('ok'), bool)
            or not isinstance(message.get('quit'), bool) or not isinstance(message.get('text'), str)
            or not isinstance(message.get('status'), str)):
        raise PilError('Unsupported or out-of-order PIL reply')
    state, data = message.get('state'), message.get('guest_output')
    if (not isinstance(state, dict) or not isinstance(state.get('registers'), list)
            or len(state['registers']) != 8 or not isinstance(data, list)
            or not all(type(b) is int and 0 <= b <= 255 for b in data)):
        raise PilError('Invalid PIL state or guest output')
    return message


class PilSession:
    """One `pil --debug-service` process; one command and one reply at a time."""

    def __init__(self, engine=None, load=None):
        self.engine = Path(engine) if engine else find_engine()
        # A .py engine is a stand-in run by this Python (the tests use one).
        argv = ([sys.executable] if self.engine.suffix == '.py' else []) + [str(self.engine), '--debug-service']
        if load:
            argv += ['--load', str(Path(load).expanduser().resolve())]
        self.stderr = tempfile.TemporaryFile()
        self.lock = threading.Lock()
        self.seq = 0
        try:
            self.process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=self.stderr, text=True, encoding='utf-8', errors='strict', bufsize=1,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if sys.platform == 'win32' else 0)
        except OSError as error:
            self.stderr.close()
            raise PilError(f'Cannot start PIL engine {self.engine}: {error}') from None
        self.last = self._read()

    @property
    def alive(self) -> bool:
        return self.process.poll() is None and not self.last.get('quit')

    def _read(self) -> dict:
        line = self.process.stdout.readline(MAX_REPLY + 1)
        if not line:
            self.process.wait(timeout=2)
            self.stderr.seek(0)
            detail = self.stderr.read(8192).decode('utf-8', errors='replace').strip()
            self.close()
            raise PilError(detail or 'PIL engine disconnected')
        return decode_reply(line, self.seq)

    def request(self, command: str) -> dict:
        command = str(command).strip()
        if '\n' in command or '\r' in command or len(command.encode('utf-8')) > 4095:
            raise PilError('Give one PIL command, at most 4095 bytes')
        with self.lock:
            if not self.alive:
                raise PilError('The PIL session has ended; (pil-start) starts a new one')
            self.process.stdin.write(command + '\n')
            self.process.stdin.flush()
            self.seq += 1
            self.last = self._read()
        if self.last['quit']:
            self.close()
        return self.last

    def close(self):
        process = self.process
        if process.poll() is None:
            try:
                process.stdin.close()
                process.wait(timeout=1)
            except (OSError, subprocess.TimeoutExpired):
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        for stream in (process.stdin, process.stdout, self.stderr):
            try:
                stream.close()
            except OSError:
                pass


def guest_text(message: dict) -> str:
    """Bytes the guest sent to the mock serial port, as text."""
    return bytes(message['guest_output']).decode('latin-1')


def state_map(message: dict) -> dict:
    """The snapshot as plain values keyed by Lisp symbol names."""
    state = message['state']
    result = {'status': message['status'], 'eip': state.get('eip', 0), 'flags': state.get('flags', 0),
              'undefined-flags': state.get('undefined_flags', 0)}
    result.update(zip(REGISTERS, state['registers']))
    for key in ('demo', 'version', 'listing', 'memory', 'stack', 'segments', 'pil'):
        if isinstance(state.get(key), str):
            result[key] = state[key]
    if isinstance(state.get('breakpoints'), list):
        result['breakpoints'] = list(state['breakpoints'])
    return result


# --- the session shared by the Lisp procedures ---------------------------

_session = None


def session() -> PilSession:
    global _session
    if _session is None or not _session.alive:
        _session = PilSession()
    return _session


def start(load=None) -> PilSession:
    global _session
    stop()
    _session = PilSession(load=load)
    return _session


def stop() -> bool:
    global _session
    if _session is None:
        return False
    _session.close()
    _session = None
    return True


atexit.register(stop)


def command(text: str, write=None) -> dict:
    message = session().request(text)
    output = guest_text(message)
    if output and write:
        write(output)
    if not message['ok']:
        raise PilError(message['text'])
    return message


def run(steps: int, write=None) -> dict:
    """Run up to `steps` guest instructions in service-sized slices; stop early at a stop."""
    if not isinstance(steps, int) or steps < 1:
        raise PilError('pil-run needs a positive number of steps')
    left = steps
    message = session().last
    while left > 0:
        if message['status'] == 'tx_blocked':
            message = command('serial tx', write)
            continue
        now = min(left, SERVICE_RUN_LIMIT)
        message = command(f'run {now}', write)
        left -= now
        if message['status'] in STOPPED:
            break
    return message


def install(env, Procedure, String) -> None:
    """Lisp procedures: pil, pil-start, pil-run, pil-state, pil-stop."""
    def write(text):
        sys.stdout.write(text)
        sys.stdout.flush()

    def lisp_text(value):
        return value.value if isinstance(value, String) else str(value)

    def pil(*words):
        if not words:
            raise PilError('usage: (pil "command"), for example (pil "demo hello")')
        message = command(' '.join(lisp_text(word) for word in words), write)
        return String(message['text'])

    def pil_start(path=None):
        message = start(None if path is None else lisp_text(path)).last
        return String(f"{message['text']} (PIL {message['state'].get('version', '?')})")

    def pil_run(steps=1000):
        return run(steps, write)['status']

    def pil_state():
        return {key: String(value) if isinstance(value, str) and key != 'status' else value
                for key, value in state_map(session().last).items()}

    procedures = {
        'pil': pil,
        'pil-start': pil_start,
        'pil-run': pil_run,
        'pil-state': pil_state,
        'pil-stop': stop,
    }
    for name, function in procedures.items():
        env[name] = Procedure(parms=['*args'], body=None, env=env, native_fn=function, name=name)

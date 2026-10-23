"""Python mini_basic CLI adapter; no editor or interpreter imports."""
import os
from lispy_support import PROJECT_ROOT
from pathlib import Path
import queue
import re
import subprocess
import sys
import tempfile
import threading


def error_source_line(source, message, first_line=1, numbered=False):
    match = re.search(r'\bline\s+(\d+)\b', str(message), re.IGNORECASE)
    if not match:
        return None
    number = int(match[1])
    lines = source.splitlines()
    if numbered:
        if 'source line' in str(message).lower():
            return first_line+number-1 if 1 <= number <= len(lines) else None
        for index, line in enumerate(lines):
            if re.match(r'^\s*'+str(number)+r'\s', line):
                return first_line+index
        # The CLI numbers nonblank unnumbered statements 10,20,... . Avoid
        # guessing for mixed sources or joined continuations/preambles.
        if any(re.match(r'^\s*\d+\s', line) or line.rstrip().endswith('\\') or
               line.lstrip().startswith('#!') for line in lines):
            return None
        active = [index for index,line in enumerate(lines) if line.strip()]
        index = number//10-1
        return first_line+active[index] if number % 10 == 0 and 0 <= index < len(active) else None
    if 1 <= number <= len(lines)+1:
        return first_line+min(number-1, max(0, len(lines)-1))
    return None


def default_package_root():
    root = PROJECT_ROOT
    for candidate in (root/'mini_basic', root.parent/'mini_basic'):
        if (candidate/'mini_basic'/'__main__.py').is_file():
            return str(candidate)
    return ''


def run_python_basic(source, write, *, cwd, executable=None, package_root='', dialect=None, pygame=False):
    """Stream a CLI subprocess; always stop/reap it on cancellation or errors.

    INPUT has no console here; programs needing interactive input should use
    the standalone terminal runner. GUI graphics can use the pygame option.
    """
    from lispy_support.lispy_terminal import console_python
    executable = executable or console_python()
    env = dict(os.environ, PYTHONUTF8='1', PYTHONUNBUFFERED='1')
    if package_root:
        if not (Path(package_root)/'mini_basic'/'__main__.py').is_file():
            raise RuntimeError('Select the Python mini_basic project directory containing mini_basic/__main__.py')
        env['PYTHONPATH'] = package_root+os.pathsep+env.get('PYTHONPATH', '')
    with tempfile.TemporaryDirectory(prefix='lispy-basic-') as folder:
        path = Path(folder)/'buffer.bas'
        path.write_text(source, encoding='utf-8')
        command = [executable, '-u', '-m', 'mini_basic', '-q']
        if dialect:
            command += ['--dialect', dialect]
        if pygame:
            command += ['--pygame', '--tee-terminal', '--hold']
        else:
            command += ['--display', 'terminal']
        command.append(str(path))
        return _stream_command(command, write, cwd, env)


def _stream_command(command, write, cwd, env):
    process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace',
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if sys.platform == 'win32' else 0)
    process.stdout.reconfigure(newline='')  # Preserve ANSI carriage returns.
    messages = queue.Queue()

    def read_output():
        try:
            for line in process.stdout:
                messages.put(line)
        finally:
            messages.put(None)

    reader = threading.Thread(target=read_output, daemon=True)
    try:
        reader.start()
        while True:
            try:
                line = messages.get(timeout=0.05)
            except queue.Empty:
                continue
            if line is None:
                break
            write(line)
        return process.wait()
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        reader.join(timeout=2)
        process.stdout.close()


def run_python_source(source, write, *, cwd, executable=None, filename='<buffer>', source_line=1):
    """Run unsaved Python in a fresh process, retaining source traceback lines."""
    import textwrap
    from lispy_support.lispy_terminal import console_python
    env = dict(os.environ, PYTHONUTF8='1', PYTHONUNBUFFERED='1')
    with tempfile.TemporaryDirectory(prefix='lispy-python-') as folder:
        path = Path(folder)/'buffer.py'
        path.write_text('\n'*(source_line-1)+textwrap.dedent(source), encoding='utf-8')
        wrapper = ("import pathlib,sys,types; p=sys.argv[1]; filename=sys.argv[2]; "
                   "sys.path[0]=sys.argv[3]; sys.argv=[filename]; "
                   "module=types.ModuleType('__main__'); module.__file__=filename; "
                   "sys.modules['__main__']=module; "
                   "exec(compile(pathlib.Path(p).read_text(encoding='utf-8'),filename,'exec'),module.__dict__)")
        command = [executable or console_python(), '-u', '-c', wrapper, str(path), filename, cwd]
        return _stream_command(command, write, cwd, env)


def default_bbcsdl():
    import shutil
    installed = Path(r'C:\Program Files (x86)\BBC BASIC for SDL 2.0\bbcsdl.exe')
    return str(installed) if installed.is_file() else (shutil.which('bbcsdl') or '')


def run_bbcsdl(source, *, cwd, executable='', helper=''):
    """Run unsaved text via BBCSDL's native basrun helper, in its own window."""
    executable = executable or default_bbcsdl()
    if not executable or not Path(executable).is_file():
        raise RuntimeError('Select the real BBC BASIC for SDL executable in BASIC Settings.')
    if not helper or not Path(helper).is_file():
        raise RuntimeError('Select a native basrun.bbc helper in BASIC Settings; see docs/BBCSDL.md.')
    with tempfile.TemporaryDirectory(prefix='lispy-bbcsdl-') as folder:
        path = Path(folder)/'buffer.bas'
        path.write_text(source, encoding='utf-8')
        process = subprocess.Popen([str(executable), str(helper), str(path)], cwd=cwd)
        try:
            while True:
                try:
                    return process.wait(timeout=0.1)
                except subprocess.TimeoutExpired:
                    pass
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def detokenize_bbc(path, *, executable=None, package_root=''):
    """Reuse Python mini_basic's Wilson/Russell decoder; never run the BASIC."""
    import json
    from lispy_support.lispy_terminal import console_python
    path = str(Path(path).resolve())
    package_root = package_root or default_package_root()
    env = dict(os.environ, PYTHONUTF8='1')
    if package_root:
        if not (Path(package_root)/'mini_basic'/'__init__.py').is_file():
            raise RuntimeError('Select the Python mini_basic project directory in BASIC Settings.')
        env['PYTHONPATH'] = package_root+os.pathsep+env.get('PYTHONPATH', '')
    # A .bbc may hold a text listing: read it as mini_basic's LOAD does (shared
    # program_bytes_to_source); older mini_basic lacks it, so null means text.
    script = ("import json, sys; from pathlib import Path; "
              "import mini_basic.bbc_detokenize as d; "
              "data = Path(sys.argv[1]).read_bytes(); "
              "shared = getattr(d, 'program_bytes_to_source', None); "
              "print(json.dumps(shared(data) if shared else "
              "d.bbc_binary_to_source(data) if d.detect_bbc_binary_format(data) else None))")
    try:
        result = subprocess.run([executable or console_python(), '-c', script, path],
            env=env, cwd=str(Path(path).parent), capture_output=True, text=True,
            encoding='utf-8', errors='replace', timeout=30,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if sys.platform == 'win32' else 0)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f'Cannot read tokenised BASIC with Python mini_basic: {error}') from error
    if result.returncode:
        if 'ModuleNotFoundError' in result.stderr or 'ImportError' in result.stderr:
            raise RuntimeError('Tokenised .bbc input requires Python mini_basic. Select its project directory '
                               'and Python executable in BASIC Settings.')
        detail = result.stderr.strip().splitlines()
        raise RuntimeError('Cannot detokenise BBC program: '+(detail[-1] if detail else 'decoder failed'))
    try:
        lines = json.loads(result.stdout)
        if lines is None:
            return Path(path).read_text(encoding='utf-8', errors='replace')
        if not isinstance(lines, list) or not all(isinstance(line, str) for line in lines):
            raise ValueError('expected source lines')
    except (ValueError, TypeError) as error:
        raise RuntimeError('Invalid response from the Python mini_basic detokenizer.') from error
    return '\n'.join(lines)+('\n' if lines else '')

"""Python mini_basic CLI adapter; no editor or interpreter imports."""
import os
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
    root = Path(__file__).resolve().parent
    for candidate in (root/'mini_basic', root.parent/'mini_basic'):
        if (candidate/'mini_basic'/'__main__.py').is_file():
            return str(candidate)
    return ''


def run_python_basic(source, write, *, cwd, executable=None, package_root='', dialect='bbc', pygame=False):
    """Stream a CLI subprocess; always stop/reap it on cancellation or errors.

    INPUT has no console here; programs needing interactive input should use
    the standalone terminal runner. GUI graphics can use the pygame option.
    """
    from lispy_terminal import console_python
    executable = executable or console_python()
    env = dict(os.environ, PYTHONUTF8='1', PYTHONUNBUFFERED='1')
    if package_root:
        if not (Path(package_root)/'mini_basic'/'__main__.py').is_file():
            raise RuntimeError('Select the Python mini_basic project directory containing mini_basic/__main__.py')
        env['PYTHONPATH'] = package_root+os.pathsep+env.get('PYTHONPATH', '')
    with tempfile.TemporaryDirectory(prefix='lispy-basic-') as folder:
        path = Path(folder)/'buffer.bas'
        path.write_text(source, encoding='utf-8')
        command = [executable, '-u', '-m', 'mini_basic', '-q', '--dialect', dialect]
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
    from lispy_terminal import console_python
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

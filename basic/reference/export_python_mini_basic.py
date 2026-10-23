"""Export concrete BASIC runs from the external Python mini_basic pytest suite.

The original tests and interpreter still run normally, with their assertions.
No files in the external repository are edited. Exports are observations, not
BBCSDL goldens: mocks, host state, dialects and Python-only assertions need review.
"""
import argparse
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import inspect
import io
import json
import os
from pathlib import Path
import re
import sys
import weakref


class Tee:
    """Observe writes while preserving the test's existing capture stream."""

    def __init__(self, stream):
        self.stream = stream
        self.buffer = io.StringIO()

    def write(self, text):
        self.buffer.write(text)
        return self.stream.write(text)

    def flush(self):
        self.stream.flush()

    def __getattr__(self, name):
        return getattr(self.stream, name)


class ExportRuns:
    def __init__(self, output):
        self.output = output
        self.current = None
        self.test_sources = {}
        self.runs = []
        self.reports = []
        self.submitted_lines = weakref.WeakKeyDictionary()

    def pytest_runtest_setup(self, item):
        self.current = item.nodeid
        try:
            self.test_sources[item.nodeid] = inspect.getsource(item.obj)
        except (AttributeError, OSError, TypeError):
            self.test_sources[item.nodeid] = None

    def pytest_runtest_logreport(self, report):
        self.reports.append(dict(test=report.nodeid, phase=report.when,
                                 outcome=report.outcome))

    def capture(self, original_run, interpreter, *args, **kwargs):
        # Capture the exact stored program before RUN can mutate interpreter state.
        source = ''.join(f'{number} {text}\n'
                         for number, text in sorted(interpreter.program.items()))
        dialect = str(getattr(interpreter.config, 'dialect', 'unknown'))
        identifier = f'{len(self.runs) + 1:04}-{hashlib.sha256(source.encode()).hexdigest()[:10]}'
        row = dict(id=identifier, test=self.current, dialect=dialect,
                   source=f'{identifier}.bas', stdout=f'{identifier}.stdout.txt',
                   stderr=f'{identifier}.stderr.txt', run_exception=None,
                   portability='unreviewed: check dialect, mocks, input and host state',
                   python_test_source=self.test_sources.get(self.current))
        self.runs.append(row)
        (self.output / row['source']).write_text(source, encoding='utf-8', newline='\n')
        submitted = self.submitted_lines.get(interpreter, {})
        if interpreter.program and set(submitted) == set(interpreter.program):
            row['submitted_source'] = f'{identifier}.input.bas'
            raw = ''.join(f'{number} {submitted[number]}\n' for number in sorted(submitted))
            (self.output / row['submitted_source']).write_text(raw, encoding='utf-8', newline='\n')
            row['stored_source_differs_from_submitted'] = raw != source
        else:
            row['submitted_source'] = None
        stdout, stderr = Tee(sys.stdout), Tee(sys.stderr)
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                return original_run(interpreter, *args, **kwargs)
        except BaseException as exc:
            row['run_exception'] = f'{type(exc).__name__}: {exc}'
            raise
        finally:
            (self.output / row['stdout']).write_text(stdout.buffer.getvalue(), encoding='utf-8')
            (self.output / row['stderr']).write_text(stderr.buffer.getvalue(), encoding='utf-8')


def write_menu(output, runs):
    """Bundle independent control-flow examples without rewriting BASIC syntax.

    Use one concrete run per test method. Reject sources whose semantics could
    depend on external files/input, global DATA pooling or numeric references.
    All individual .bas files remain available regardless of bundling.
    """
    selected, seen = [], set()
    forbidden = re.compile(r'\b(GOTO|GOSUB|RESTORE|RESUME|DATA|READ|INPUT|CHAIN|RUN|'
                           r'OPENIN|OPENOUT|OPENUP|SYS|OSCLI)\b|\*', re.I)
    for row in runs:
        if row['test'] in seen:
            continue
        source = (output / row['source']).read_text(encoding='utf-8')
        code = re.sub(r'"(?:[^"]|"")*"', '""', source)
        if forbidden.search(code) or row['run_exception']:
            continue
        selected.append((row, source))
        seen.add(row['test'])
    if not selected or len(selected) > 30:
        return []
    lines = ['10 REM Representative Python mini_basic tests; fresh RUN per case',
             '20 ON ERROR PRINT "ERROR ";ERR;" AT LINE ";ERL:REPORT:PRINT:END']
    mapping = []
    for index, (row, _) in enumerate(selected, 1):
        lines.append(f'{20 + index} PRINT "{index} {row["id"]} dialect={row["dialect"]}"')
    lines.append(f'110 INPUT "Case (1-{len(selected)}): " choice%')
    for index in range(1, len(selected) + 1):
        lines.append(f'{120 + index} IF choice%={index} THEN GOTO {index * 2000}')
    lines.append('200 PRINT "Invalid case":END')
    for index, (row, source) in enumerate(selected, 1):
        base = index * 2000
        lines.append(f'{base} REM {row["id"]}')
        for source_line in source.splitlines():
            number, text = source_line.split(' ', 1)
            if not 1 <= int(number) < 1900:
                return []  # Keep originals; do not emit an overlapping bundle.
            lines.append(f'{base + int(number)} {text}')
        lines.append(f'{base + 1999} END')
        mapping.append(dict(case=index, run=row['id'], test=row['test'],
                            dialect=row['dialect'], stdout=row['stdout']))
    (output / 'representative-menu.bas').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return mapping


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('tests', nargs='+', help='Paths/node IDs relative to --repo')
    args = parser.parse_args()
    repo, output = args.repo.resolve(), args.output.resolve()
    if output == repo or repo in output.parents:
        parser.error('Choose an output directory outside the external repository')
    if not (repo / 'mini_basic' / '__init__.py').is_file():
        parser.error('--repo must contain the Python mini_basic package')
    output.mkdir(parents=True, exist_ok=False)
    # Keep pytest/Hypothesis/Python caches out of the external repository.
    sys.dont_write_bytecode = True
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    os.environ['HYPOTHESIS_STORAGE_DIRECTORY'] = str(output / 'hypothesis')
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    sys.path.insert(0, str(repo))
    import pytest
    from hypothesis import settings
    from mini_basic import BASICInterpreter
    from mini_basic.display import ensure_no_pygame_leftovers

    # Capture deterministic concrete examples, not a permanent generative suite.
    settings.register_profile('source_export', database=None, derandomize=True)
    settings.load_profile('source_export')
    plugin = ExportRuns(output)
    original_run = BASICInterpreter.run
    original_set_line = BASICInterpreter.set_program_line

    def observed_run(interpreter, *run_args, **run_kwargs):
        return plugin.capture(original_run, interpreter, *run_args, **run_kwargs)

    def observed_set_line(interpreter, number, statement, *line_args, **line_kwargs):
        result = original_set_line(interpreter, number, statement, *line_args, **line_kwargs)
        submitted = plugin.submitted_lines.setdefault(interpreter, {})
        if number in interpreter.program:
            submitted[number] = statement
        else:
            submitted.pop(number, None)
        return result

    BASICInterpreter.run = observed_run
    BASICInterpreter.set_program_line = observed_set_line
    selected = [str(repo / target.split('::', 1)[0]) +
                ('::' + target.split('::', 1)[1] if '::' in target else '')
                for target in args.tests]
    exit_code = None
    try:
        exit_code = int(pytest.main(['-q', '-p', 'no:cacheprovider', *selected], plugins=[plugin]))
    finally:
        BASICInterpreter.run = original_run
        BASICInterpreter.set_program_line = original_set_line
        ensure_no_pygame_leftovers()
        manifest = dict(repository=str(repo), selected=args.tests,
                        pytest_exit_code=exit_code, runs=plugin.runs,
                        test_reports=plugin.reports,
                        note='Observed Python output, not independently verified BBCSDL expectations.')
        manifest['representative_menu'] = write_menu(output, plugin.runs)
        (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Exported {len(plugin.runs)} BASIC executions to {output}')
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())

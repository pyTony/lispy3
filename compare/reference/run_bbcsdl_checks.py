"""Run the supplied, already tokenised jumping.bbc fixture in isolation.

This is fixture instrumentation, not a BASIC tokenizer: preserve existing
records and their tokens, replace only selection line 110 with an ASCII
assignment, add a native *SPOOL line, and replace final END tokens with *QUIT
so each process exits. The source fixture must match the recorded hash.
Optional exit probes copy existing loop records to test case 5's continuation.
Terminator probes jump past opening statements and reach individual terminators.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


FIXTURE_SHA256 = '6ab9dad2802d6ef5f2c921482eeda4af8f115748946baaa0b972c6c3ead9e51c'
TERMINATORS = ('next', 'until', 'endwhile', 'endif', 'endcase', 'return')


def records(data):
    pos = 0
    while pos < len(data) and data[pos]:
        size = data[pos]
        if size < 4 or pos + size > len(data) or data[pos + size - 1] != 13:
            raise ValueError('Invalid native line record')
        yield int.from_bytes(data[pos + 1:pos + 3], 'little'), data[pos + 3:pos + size - 1]
        pos += size
    if data[pos:] != b'\x00\xff\xff':
        raise ValueError('Unexpected native program terminator')


def record(number, body):
    if len(body) + 4 > 255:
        raise ValueError('Instrumented line too long')
    return bytes([len(body) + 4]) + number.to_bytes(2, 'little') + body + b'\r'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, default=Path(
        r'C:\Program Files (x86)\BBC BASIC for SDL 2.0\bbcsdl.exe'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=float, default=5)
    parser.add_argument('--case', type=int, choices=range(1, 15), action='append')
    parser.add_argument('--exit-probe', choices=('fresh-for', 'fresh-while', 'enclosing-while'))
    parser.add_argument('--terminator-probe', choices=TERMINATORS + ('all',))
    parser.add_argument('--exported-menu', type=Path,
                        help='Tokenised representative menu saved from exported Python tests')
    args = parser.parse_args()
    if args.exported_menu and (args.exit_probe or args.terminator_probe):
        parser.error('Exported menus cannot be combined with jump-fixture probes')
    if args.exit_probe and args.terminator_probe:
        parser.error('Select either an exit probe or a terminator probe')
    if (args.exit_probe or args.terminator_probe) and args.case not in (None, [5]):
        parser.error('Probes are only valid for case 5')
    fixture_path = args.exported_menu or Path(__file__).with_name('jumping.bbc')
    fixture = fixture_path.read_bytes()
    fixture_hash = hashlib.sha256(fixture).hexdigest()
    menu = None
    if args.exported_menu:
        menu = json.loads(fixture_path.with_name('manifest.json').read_text(encoding='utf-8'))['representative_menu']
        if not menu or [entry['case'] for entry in menu] != list(range(1, len(menu) + 1)):
            parser.error('Exported menu manifest must list consecutive case numbers')
        if args.case and any(case > len(menu) for case in args.case):
            parser.error('Selected case is absent from the exported menu')
    elif fixture_hash != FIXTURE_SHA256:
        raise ValueError('Fixture changed; inspect it before instrumenting')
    original = list(records(fixture))
    assert [n for n, _ in original].count(110) == 1
    baseline = dict(original)
    if menu:
        if not baseline[110].startswith(b'\xe8 ') or b'choice%' not in baseline[110]:
            parser.error('Exported fixture does not have the expected selection line')
        for entry in menu:
            header = f'{entry["case"]} {entry["run"]} dialect={entry["dialect"]}'.encode('ascii')
            if not any(header in body for _, body in original):
                parser.error('Native menu headers do not match the export manifest')
    instrumented = dict(baseline)
    if args.exit_probe:
        # Copy already-tokenised bodies verbatim; no new keyword encoding.
        # Fresh loops push/pop their own frames. The enclosing variant instead
        # reaches an outer ENDWHILE with an abandoned inner FOR frame on top.
        additions = {
            'fresh-for': {5081: 1010, 5082: 1040, 5083: 1050},
            'fresh-while': {5081: 2010, 5082: 2020, 5083: 2030,
                            5084: 2060, 5085: 2070},
            'enclosing-while': {5005: 2010, 5006: 2020,
                                5081: 2030, 5082: 2070},
        }[args.exit_probe]
        for target, source in additions.items():
            assert target not in instrumented
            instrumented[target] = dict(original)[source]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    results = []
    if args.terminator_probe:
        names = TERMINATORS if args.terminator_probe == 'all' else (args.terminator_probe,)
        jobs = [(5, name) for name in names]
    else:
        cases = args.case or ([5] if args.exit_probe else range(1, len(menu) + 1) if menu else range(1, 15))
        jobs = [(case, None) for case in cases]
    for case, terminator in jobs:
        if terminator:
            instrumented = dict(baseline)
            # Initialise n, then jump over the opening statements to line 5080.
            # Reuse the fixture's encoded GOTO target; keep skipped FOR visible.
            instrumented[5010] = baseline[2010]
            instrumented[5011] = baseline[5030]
            instrumented[5012] = baseline[5010]
            endings = dict(next=baseline[1050], until=baseline[8070],
                           endwhile=baseline[2070], endif=baseline[3050],
                           endcase=baseline[9080],
                           return_=baseline[11100].rsplit(b':', 1)[1].strip())
            instrumented[5081] = endings['return_' if terminator == 'return' else terminator]
            instrumented[5082] = baseline[3060]  # PRINT "after", only if accepted.
        suffix = f'-orphan-{terminator}' if terminator else ''
        log = output / f'case-{case:02}{suffix}.txt'
        program = output / f'case-{case:02}{suffix}.bbc'
        chunks = [record(1, f'*SPOOL "{log}"'.encode('ascii'))]
        for number, body in sorted(instrumented.items()):
            if number == 110:
                body = f'choice%={case}'.encode('ascii')
            # END is token E0 in this inspected fixture; only terminal ENDs
            # are replaced, including the error handler. Targets stay intact.
            if body.endswith(b'\xe0'):
                body = body[:-1] + b'*QUIT'
            chunks.append(record(number, body))
        program.write_bytes(b''.join(chunks) + b'\x00\xff\xff')
        process = subprocess.Popen([str(args.exe), str(program), '-hidden'],
                                   cwd=output, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
        timed_out = False
        try:
            process.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()  # Only the isolated process started for this case.
            process.wait()
        result = dict(case=case, timed_out=timed_out, exit_code=process.returncode,
                      log=log.name,
                      output=log.read_text(encoding='latin-1') if log.exists() else None)
        if menu:
            entry = menu[case - 1]
            header = ''.join(f'{e["case"]} {e["run"]} dialect={e["dialect"]}\n' for e in menu)
            actual = result['output']
            body = actual[len(header):] if actual is not None and actual.startswith(header) else None
            expected = fixture_path.with_name(entry['stdout']).read_text(encoding='utf-8')
            result.update(test=entry['test'], dialect=entry['dialect'],
                          fixture_sha256=fixture_hash, actual_stdout=body,
                          python_stdout=expected,
                          comparison='matches' if body == expected else 'differs' if body is not None else 'unreadable')
        if args.exit_probe:
            result['exit_probe'] = args.exit_probe
        if terminator:
            result['terminator_probe'] = terminator
        results.append(result)
        print(json.dumps(result), flush=True)
        (output / 'results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()

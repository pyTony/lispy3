"""Compare shared control-flow fixtures with real BBCSDL via its native loader.

This runner never tokenises BASIC. Supply basrun.bbc saved by BBCSDL; sources
and logs are retained in a new output directory. Each case is an isolated child
process with a timeout. Imported module functions are safe without BBCSDL.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess


def instrument(source, log):
    spool = 'SPOOL "' + log.resolve().as_posix() + '"'
    header = 'OSCLI "' + spool.replace('"', '""') + '"\n'
    header += 'ON ERROR PRINT "BBC_ERROR:";ERR;":";REPORT$;":";ERL : OSCLI "SPOOL" : QUIT\n'
    rows, ends = [], 0
    for row in source.splitlines():
        match = re.fullmatch(r'(\s*(?:\d+\s*)?)END\s*', row)
        if match:
            row = match[1] + 'OSCLI "SPOOL":QUIT'
            ends += 1
        rows.append(row)
    if not ends:
        raise ValueError('Reference fixture needs a standalone END before its definitions')
    return header + '\n'.join(rows) + '\n'


def classify(name, actual, expected):
    if name == 'abandoned-for-diagnostic':
        if re.fullmatch(r'1\nBBC_ERROR:46:Not in a WHILE loop:90\n', actual):
            return 'documented-difference'
        return 'differs'
    return 'matches' if actual == expected else 'differs'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--helper', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reference-version', required=True, help='Installed BBCSDL version, verified by the caller')
    parser.add_argument('--timeout', type=float, default=10)
    args = parser.parse_args()
    # Keep junction aliases: basrun parses @cmd$ and a resolved helper path
    # containing spaces can change its native argument parsing.
    exe, helper = args.exe.absolute(), args.helper.absolute()
    if not exe.is_file() or not helper.is_file():
        parser.error('Executable and native basrun helper must exist')
    if args.timeout <= 0:
        parser.error('Timeout must be positive')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    # Keep native CRLF logs byte-for-byte when Git checks them in.
    (output/'.gitattributes').write_text('*.txt -text\n', encoding='utf-8')
    report = dict(reference='BBC BASIC for SDL', version=args.reference_version,
                  timestamp_utc=datetime.now(timezone.utc).isoformat(),
                  executable=str(exe), helper=str(helper),
                  helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(), cases=[])
    for path in sorted(Path(__file__).with_name('structured').glob('*.bas')):
        source = path.read_text(encoding='utf-8')
        expected = path.with_suffix('.out').read_text(encoding='utf-8')
        program, log = output/(path.stem+'.bas'), output/(path.stem+'.txt')
        program.write_text(instrument(source, log), encoding='utf-8')
        process = subprocess.Popen([str(exe), str(helper), str(program)], cwd=output,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        timed_out = False
        try:
            process.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            process.wait()
        actual = log.read_text(encoding='latin-1') if log.exists() else None
        comparison = (classify(path.stem, actual, expected) if actual is not None and
                      not timed_out and process.returncode == 0 else 'failed')
        result = dict(case=path.stem, source=path.name,
                      source_sha256_utf8_lf=hashlib.sha256(source.encode('utf-8')).hexdigest(),
                      exit_code=process.returncode, timed_out=timed_out, log=log.name,
                      actual_stdout=actual, lispy_expected_stdout=expected, comparison=comparison)
        report['cases'].append(result)
        (output/'results.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        print(f'{path.stem}: {comparison}', flush=True)
    return 0 if report['cases'] and all(case['comparison'] in ('matches','documented-difference')
                                       for case in report['cases']) else 1


if __name__ == '__main__':
    raise SystemExit(main())

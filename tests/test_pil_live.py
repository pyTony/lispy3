"""Lispy's PIL bridge against a real PIL checkout, a real `pil` build and NASM.

test_pil_engine.py checks the bridge with a stand-in engine. These tests use
the real things when this computer has them and are skipped otherwise:

- a PIL checkout: PIL_DIRECTORY, or a PIL folder beside the Lispy folder
- a built engine: PIL_ENGINE, or `cargo build --release` in that checkout
- NASM: NASM, PATH, or the folders the NASM installer uses on Windows

    pytest -rs tests/test_pil_live.py
"""
import contextlib
import io
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from support import LispyTestCase
from lispy_support import pil_engine as PE


def available(find):
    try:
        return find()
    except PE.PilError:
        return None


def checkout():
    directory = PE.DIRECTORY or os.environ.get('PIL_DIRECTORY', '') or PE.default_directory()
    path = Path(directory).expanduser() if directory else None
    return path if path and (path / 'isa').is_dir() else None


ENGINE = available(PE.find_engine)
NASM = available(PE.find_nasm)
CHECKOUT = checkout()
NO_ENGINE = 'no built PIL engine (set PIL_DIRECTORY or PIL_ENGINE, then cargo build --release)'

# A monitor program: CS:0100, output on port E9, HLT stops it.
MONITOR_SOURCE = """\
        org 100h
        mov al,'O'
        out 0e9h,al
        mov al,'K'
        out 0e9h,al
        hlt
"""


@unittest.skipIf(ENGINE is None or ENGINE.suffix == '.py', NO_ENGINE)
class RealEngineTest(unittest.TestCase):

    def setUp(self):
        PE.stop()

    def tearDown(self):
        PE.stop()

    def test_hello_demo(self):
        written = []
        PE.command('demo hello')
        message = PE.run(1000, written.append)
        self.assertEqual(message['status'], 'halt')
        self.assertEqual(''.join(written), 'Hello, world!\n')
        state = PE.state_map(message)
        self.assertEqual(state['demo'], 'hello')
        self.assertTrue(state['version'])

    def test_debugger_commands_answer(self):
        PE.command('demo hello')
        self.assertTrue(PE.command('regs')['text'])
        self.assertTrue(PE.command('help')['text'])
        with self.assertRaises(PE.PilError):
            PE.command('no-such-command')

    @unittest.skipIf(NASM is None, 'NASM is not installed')
    def test_assembled_monitor_program(self):
        with tempfile.TemporaryDirectory() as folder:
            program = PE.assemble(MONITOR_SOURCE, cwd=folder, name='ok.asm')
            written = []
            try:
                PE.start(load=program)
                message = PE.run(100, written.append)
            finally:
                shutil.rmtree(program.parent, ignore_errors=True)
        self.assertEqual(message['status'], 'halt')
        self.assertEqual(''.join(written), 'OK')


@unittest.skipIf(ENGINE is None or ENGINE.suffix == '.py', NO_ENGINE)
class RealEngineLispTest(LispyTestCase):

    def tearDown(self):
        PE.stop()
        super().tearDown()

    def test_pil_procedures(self):
        self.assertIn('(PIL ', self.show('(pil-start)'))
        self.show('(pil "demo hello")')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(self.show('(pil-run 1000)'), 'halt')
        self.assertEqual(out.getvalue(), 'Hello, world!\n')
        self.assertEqual(self.show("(get (pil-state) 'demo)"), '"hello"')


@unittest.skipIf(CHECKOUT is None, 'no PIL checkout (set PIL_DIRECTORY)')
@unittest.skipIf(NASM is None, 'NASM is not installed')
class PilProgramsTest(unittest.TestCase):
    """PIL's own DOS programs assemble the same way in Lispy as in PIL."""

    def test_dos_programs_match_their_com_files(self):
        programs = CHECKOUT / 'programs' / 'dos'
        sources = sorted(programs.glob('*.asm'))
        if not sources:
            self.skipTest('the PIL checkout has no programs/dos/*.asm')
        for source in sources:
            built = programs / (source.stem.upper() + '.COM')
            if not built.is_file():
                continue
            with self.subTest(program=source.name):
                program = PE.assemble(source.read_text(encoding='utf-8'), cwd=programs, name=source.name)
                try:
                    self.assertEqual(program.read_bytes(), built.read_bytes())
                finally:
                    shutil.rmtree(program.parent, ignore_errors=True)

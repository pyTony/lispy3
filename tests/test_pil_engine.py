"""Lispy's bridge to the PIL x86 engine (lispy_support/pil_engine.py).

The real engine is Rust (pyTony/PIL-Processor-Instruction-Language); these
tests use tests/fixtures/fake_pil_engine.py, which speaks the same protocol.
"""
import contextlib
import io
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from support import LispyTestCase, REPO_DIR, TESTS_DIR, lispy3
from lispy_support import pil_engine as PE
from lispy_support import syntax_highlight as SH

FAKE = os.path.join(TESTS_DIR, 'fixtures', 'fake_pil_engine.py')


class FakeEngineMixin:
    def setUp(self):
        super().setUp()
        self.saved = PE.ENGINE, PE.DIRECTORY, PE.NASM
        PE.ENGINE = FAKE
        PE.stop()

    def tearDown(self):
        PE.stop()
        PE.ENGINE, PE.DIRECTORY, PE.NASM = self.saved
        super().tearDown()


class SessionTest(FakeEngineMixin, unittest.TestCase):

    def test_demo_runs_and_reports_guest_output(self):
        written = []
        PE.command('demo hello')
        message = PE.run(1000, written.append)
        self.assertEqual(message['status'], 'halt')
        self.assertEqual(''.join(written), 'Hello, world!\n')
        state = PE.state_map(message)
        self.assertEqual(state['eax'], 0x0a)
        self.assertEqual(state['eip'], 0x138)
        self.assertEqual(state['demo'], 'hello')

    def test_run_is_split_into_service_sized_slices(self):
        PE.command('demo loop')
        start = PE.session().last['state']['eip']
        message = PE.run(600)
        self.assertEqual(message['status'], 'budget')
        self.assertEqual(message['state']['eip'] - start, 3)    # 256 + 256 + 88

    def test_refused_command_raises_with_engine_text(self):
        with self.assertRaisesRegex(PE.PilError, 'not available'):
            PE.command('frobnicate')

    def test_start_passes_a_raw_image(self):
        PE.start(load='prog.bin')
        self.assertTrue(PE.command('loaded')['text'].endswith('prog.bin'))

    def test_quit_ends_and_next_command_restarts(self):
        PE.command('quit')
        self.assertEqual(PE.command('demo hello')['text'], 'demo hello loaded')

    def test_out_of_order_reply_is_rejected(self):
        line = '{"protocol":1,"seq":5,"ok":true,"quit":false,"text":"","status":"ready","guest_output":[],"state":{"registers":[0,0,0,0,0,0,0,0]}}\n'
        with self.assertRaisesRegex(PE.PilError, 'out-of-order'):
            PE.decode_reply(line, 4)


class LispProceduresTest(FakeEngineMixin, LispyTestCase):

    def test_pil_procedures(self):
        self.assertIn('PIL 0.35-fake', self.show('(pil-start)'))
        self.assertEqual(self.show('(pil "demo" "hello")'), '"demo hello loaded"')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(self.show('(pil-run 1000)'), 'halt')
        self.assertEqual(out.getvalue(), 'Hello, world!\n')
        self.assertEqual(self.ev('(get (pil-state) (quote eax))'), 10)
        self.assertEqual(self.show('(get (pil-state) (quote demo))'), '"hello"')
        self.assertTrue(self.ev('(pil-stop)'))


class EngineSearchTest(unittest.TestCase):

    def setUp(self):
        self.saved = PE.ENGINE, PE.DIRECTORY
        PE.ENGINE = PE.DIRECTORY = ''
        self.env = {key: os.environ.pop(key) for key in ('PIL_ENGINE', 'PIL_DIRECTORY') if key in os.environ}

    def tearDown(self):
        PE.ENGINE, PE.DIRECTORY = self.saved
        os.environ.update(self.env)

    def test_newest_build_in_the_pil_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for build in ('debug', 'release'):
                (root/'target'/build).mkdir(parents=True)
            old, new = root/'target'/'debug'/PE.executable_name(), root/'target'/'release'/PE.executable_name()
            old.write_text('old')
            new.write_text('new')
            os.utime(old, (1, 1))
            self.assertEqual(PE.find_engine(directory=folder), new.resolve())
            (root/'tools').mkdir()
            (root/'tools'/'pil_debugger.py').write_text('')
            self.assertEqual(PE.find_tool('pil_debugger.py', folder).name, 'pil_debugger.py')

    def test_missing_engine_explains_how_to_build(self):
        with tempfile.TemporaryDirectory() as folder:
            if shutil.which('pil'):
                self.skipTest('a pil executable is on PATH')
            with self.assertRaisesRegex(PE.PilError, 'cargo build --release'):
                PE.find_engine(directory=folder)


class AssemblyTest(unittest.TestCase):

    def test_run_comments(self):
        self.assertEqual(PE.run_options('org 100h\n'), {'mode': 'dos', 'args': ''})
        self.assertEqual(PE.run_options('; PIL: monitor\n  ; pil-args: 30 \n'), {'mode': 'monitor', 'args': '30'})
        with self.assertRaisesRegex(PE.PilError, 'Unknown'):
            PE.run_options('; pil: windows\n')

    def test_launch_commands_use_pil_frontends(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'tools').mkdir()
            for name in ('pil_debugger.py', 'dos_terminal.py'):
                (Path(folder)/'tools'/name).write_text('')
            saved = PE.DIRECTORY
            PE.DIRECTORY = folder
            try:
                dos = PE.launch_command('A.COM', {'mode': 'dos', 'args': '30'}, engine='pil', python='py')
                monitor = PE.launch_command('A.COM', {'mode': 'monitor', 'args': ''}, engine='pil', python='py')
            finally:
                PE.DIRECTORY = saved
        self.assertEqual(Path(dos[1]).name, 'dos_terminal.py')
        self.assertEqual(dos[2:], ['--engine', 'pil', '--args', '30', 'A.COM'])
        self.assertEqual(Path(monitor[1]).name, 'pil_debugger.py')
        self.assertEqual(monitor[2:], ['--engine', 'pil', '--load', 'A.COM'])

    def test_nasm_error_line(self):
        self.assertEqual(PE.nasm_error_line('/tmp/x/buffer.asm:7: error: invalid combination'), 7)
        self.assertIsNone(PE.nasm_error_line('warning only'))

    @unittest.skipUnless(shutil.which('nasm'), 'NASM is not installed')
    def test_assemble_com(self):
        source = "        org 100h\n        mov ah,4ch\n        int 21h\n"
        with tempfile.TemporaryDirectory() as folder:
            program = PE.assemble(source, cwd=folder, name='exit.asm')
            self.assertEqual(program.name, 'EXIT.COM')
            self.assertEqual(program.read_bytes(), bytes([0xb4, 0x4c, 0xcd, 0x21]))
            with self.assertRaises(PE.PilError) as caught:
                PE.assemble("        org 100h\n        mov ax,\n", cwd=folder)
            self.assertEqual(PE.nasm_error_line(str(caught.exception)), 2)


class SyntaxTest(unittest.TestCase):

    def test_pil_and_x86_languages(self):
        languages, errors = SH.load_languages()
        self.assertEqual(errors, [])
        pil = SH.language_for('add.pil', languages)
        asm = SH.language_for('factor.asm', languages)
        self.assertEqual((pil.name, asm.name), ('PIL', 'x86 assembly'))
        text = 'read a dst $W\nflag CF cf\nretire # done'
        tags = {text[s:e]: tag for tag, s, e in pil.spans(text)}
        self.assertEqual((tags['read'], tags['dst'], tags['$W'], tags['CF'], tags['# done']),
                         ('keyword', 'special', 'constant', 'builtin', 'comment'))
        text = '.skip:  lodsb\n        org 100h ; go'
        tags = {text[s:e]: tag for tag, s, e in asm.spans(text)}
        self.assertEqual((tags['.skip:'], tags['lodsb'], tags['org'], tags['100h'], tags['; go']),
                         ('function', 'keyword', 'special', 'number', 'comment'))


if __name__ == '__main__':
    unittest.main()

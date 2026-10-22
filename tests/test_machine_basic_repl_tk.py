"""Exercise real Listener mode switches and BASIC evaluation in a child process."""
import subprocess
import sys
from pathlib import Path
from unittest import TestCase


class BasicListenerTkTest(TestCase):
    def test_real_listener_modes_and_program_run(self):
        script = r'''
import importlib.machinery, importlib.util, sys, time, tkinter as tk
from unittest.mock import patch
loader=importlib.machinery.SourceFileLoader('machine_probe','lispy_machine.pyw')
spec=importlib.util.spec_from_loader(loader.name,loader)
module=importlib.util.module_from_spec(spec)
sys.modules[loader.name]=module
loader.exec_module(module)
with patch.object(module,'load_settings',return_value={'startup_run':False,'startup_show_buffer':False}), patch.object(module,'save_settings'):
    try:
        app=module.LispMachine([])
    except tk.TclError as error:
        if 'display' in str(error).lower(): sys.exit(77)
        raise
    app.withdraw()
    try:
        app.listener_mode.set('basic')
        app._select_listener_mode()
        assert app._prompt_text() == 'BASIC>'
        tab=app.new_buffer('current.bas', 'PRINT "first"\nPRINT "second"\n')
        app.eval_buffer()
        deadline=time.monotonic()+10
        while app._job is not None and time.monotonic()<deadline:
            app.update(); time.sleep(.005)
        assert app._job is None, 'worker did not complete'
        output=app.listener_text.get('1.0','end')
        assert 'first\nsecond\n' in output, output
        assert 'Error:' not in output, output
        tab.text.delete('1.0','end')
        tab.text.insert('1.0','PRINT "edited buffer"\n')
        app._basic_feed(['10 PRINT "stale CLI program"', 'RUN'])
        deadline=time.monotonic()+10
        while app._job is not None and time.monotonic()<deadline:
            app.update(); time.sleep(.005)
        assert app._job is None, 'worker did not complete'
        output=app.listener_text.get('1.0','end')
        assert 'edited buffer\n' in output, output
        assert 'stale CLI program\n' not in output, output
        for cli_run in (False, True):
            tab.text.delete('1.0','end')
            tab.text.insert('1.0','10 PRINT "before error"\n100 FOR\n')
            if cli_run:
                app._basic_feed(['RUN'])
            else:
                app.eval_buffer()
            deadline=time.monotonic()+10
            while app._job is not None and time.monotonic()<deadline:
                app.update(); time.sleep(.005)
            assert app._job is None, 'worker did not complete'
            ranges=tuple(str(index) for index in tab.text.tag_ranges('syntax_error'))
            assert ranges == ('2.0','2.7'), ranges
        tab.text.delete('1.0','end')
        tab.text.insert('1.0','REM before\nREM before\nFOR\n')
        app.eval_buffer(source='FOR',source_line=3)
        deadline=time.monotonic()+10
        while app._job is not None and time.monotonic()<deadline:
            app.update(); time.sleep(.005)
        assert app._job is None, 'worker did not complete'
        ranges=tuple(str(index) for index in tab.text.tag_ranges('syntax_error'))
        assert ranges == ('3.0','3.3'), ranges
        tab.text.delete('1.0','end')
        tab.text.insert('1.0','INPUT "Name: " n$\nPRINT "reply=[";n$;"]"\n')
        app.eval_buffer()
        deadline=time.monotonic()+10
        while getattr(app,'_basic_input_queue',None) is None and time.monotonic()<deadline:
            app.update(); time.sleep(.005)
        assert getattr(app,'_basic_input_queue',None) is not None, app.listener_text.get('1.0','end')
        assert app.console_ready and app._job is not None
        app.listener_text.insert('end','RUN')
        app._console_return()
        deadline=time.monotonic()+10
        while app._job is not None and time.monotonic()<deadline:
            app.update(); time.sleep(.005)
        assert app._job is None, 'INPUT did not resume'
        output=app.listener_text.get('1.0','end')
        assert 'reply=[RUN]\n' in output, output
        assert app.console_ready
        app.eval_buffer()
        deadline=time.monotonic()+10
        while getattr(app,'_basic_input_queue',None) is None and time.monotonic()<deadline:
            app.update(); time.sleep(.005)
        assert app._basic_input_queue is not None, 'second RUN did not wait for input'
        app.stop()
        deadline=time.monotonic()+10
        while app._job is not None and time.monotonic()<deadline:
            app.update(); time.sleep(.005)
        assert app._job is None, 'Stop did not interrupt INPUT'
        assert app._basic_input_queue is None
        assert app.console_ready
        app._basic_feed(['PRINT "after stop"'])
        deadline=time.monotonic()+10
        while app._job is not None and time.monotonic()<deadline:
            app.update(); time.sleep(.005)
        assert app._job is None
        assert 'after stop\n' in app.listener_text.get('1.0','end')
        app.listener_mode.set('lisp')
        app._select_listener_mode()
        assert app._prompt_text() == 'lispy3>'
        assert not app.basic_repl_mode.get()
        app.listener_mode.set('listener')
        app._select_listener_mode()
        assert not app.plain_repl.get()
    finally:
        app.basic_repl.close()
        app.destroy()
print('BASIC Listener modes and execution OK')
'''
        result=subprocess.run([sys.executable,'-c',script],cwd=Path(__file__).resolve().parents[1],
                              capture_output=True,text=True,timeout=30)
        if result.returncode == 77:
            self.skipTest('Tk display unavailable')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('BASIC Listener modes and execution OK',result.stdout)

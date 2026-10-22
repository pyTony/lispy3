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
        app._basic_feed(['20 PRINT "second"','10 PRINT "first"','RUN'])
        deadline=time.monotonic()+10
        while app._job is not None and time.monotonic()<deadline:
            app.update(); time.sleep(.005)
        assert app._job is None, 'worker did not complete'
        output=app.listener_text.get('1.0','end')
        assert 'first\nsecond\n' in output, output
        assert 'Error:' not in output, output
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

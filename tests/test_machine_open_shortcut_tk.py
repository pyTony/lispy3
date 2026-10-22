"""Exercise real Tk binding order for Ctrl+O without opening a file dialog."""
import subprocess
import sys
from pathlib import Path
from unittest import TestCase


class OpenShortcutTkTest(TestCase):
    def test_ctrl_o_opens_once_without_editing_text(self):
        script = r'''
import importlib.machinery, importlib.util, sys, tkinter as tk
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
    try:
        tab=app.new_buffer('shortcut.bas','PRINT "untouched"\n')
        app.update()
        def check(widget):
            content=(lambda: widget.get()) if widget is app.listener_input else (lambda: widget.get('1.0','end'))
            before=content()
            widget.focus_force()
            app.update()
            with patch.object(module.filedialog,'askopenfilename',return_value='') as dialog:
                widget.event_generate('<Control-o>')
                app.update()
                assert dialog.call_count == 1, (str(widget),dialog.call_count)
            assert content() == before, str(widget)
        check(tab.text)
        app.listener_mode.set('basic')
        app._select_listener_mode()
        app._set_console_input('pending command')
        check(app.listener_text)
        replies=module.queue.Queue()
        app._begin_basic_input(replies)
        app._set_console_input('pending reply')
        check(app.listener_text)
        assert replies.empty()
        app._end_basic_input(replies)
        check(app.listener_text)
        check(app.inspector)
        app.listener_mode.set('listener')
        app._select_listener_mode()
        app.listener_input.insert(0,'pending Lisp input')
        check(app.listener_input)
    finally:
        app.basic_repl.close()
        app.destroy()
print('Ctrl+O bindings OK')
'''
        result = subprocess.run([sys.executable, '-c', script],
            cwd=Path(__file__).resolve().parents[1], capture_output=True,
            text=True, timeout=30)
        if result.returncode == 77:
            self.skipTest('Tk display unavailable')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Ctrl+O bindings OK', result.stdout)

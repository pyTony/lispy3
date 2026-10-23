"""Exercise real Tk binding order for Ctrl+O without opening a file dialog."""
import subprocess
import sys
from pathlib import Path
from unittest import TestCase


class OpenShortcutTkTest(TestCase):
    def test_ctrl_o_opens_once_without_editing_text(self):
        script = r'''
import importlib.machinery, importlib.util, sys, tkinter as tk, tempfile
from pathlib import Path
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
            for keysym, state in [('o',4),('O',6)]:
                with patch.object(module.filedialog,'askopenfilename',return_value='') as dialog:
                    widget.event_generate('<KeyPress>',keysym=keysym,state=state)
                    app.update()
                    assert dialog.call_count == 1, (str(widget),keysym,state,dialog.call_count)
            assert content() == before, str(widget)
            for key,action in [('n','new_buffer_dialog'),('w','close_current'),('q','_on_close')]:
                for symbol,state in [(key,4),(key.upper(),6)]:
                    with patch.object(app,action) as call:
                        widget.event_generate('<KeyPress>',keysym=symbol,state=state)
                        app.update()
                        assert call.call_count == 1, (str(widget),symbol,state,call.call_count)
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
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'saved.bas'
            tab.path=str(path)
            for widget in (tab.text,app.listener_text,app.listener_input,app.inspector):
                widget.focus_force()
                app.update()
                before=tab.get_content()
                tab.dirty=True
                def saved(title,message,**kwargs):
                    assert title == 'File saved', title
                    assert str(path.resolve()) in message, message
                    assert path.read_text(encoding='utf-8') == before
                for keysym,state in [('s',4),('S',6)]:
                    with patch.object(module.messagebox,'showinfo',side_effect=saved) as notice:
                        widget.event_generate('<KeyPress>',keysym=keysym,state=state)
                        app.update()
                        assert notice.call_count == 1, (str(widget),keysym,state,notice.call_count)
                assert not tab.dirty
                assert tab.get_content() == before
            tab.path=None
            path=Path(directory)/'first-save.bas'
            with patch.object(module.filedialog,'asksaveasfilename',return_value=str(path)) as choose, patch.object(module.messagebox,'showinfo',side_effect=saved) as notice:
                tab.text.focus_force()
                app.update()
                tab.text.event_generate('<Control-s>')
                app.update()
                assert choose.call_count == 1
                assert notice.call_count == 1
                assert tab.path == str(path)
        for mode in ('listener','lisp','basic'):
            app.listener_mode.set(mode)
            app._select_listener_mode()
            widget=app.listener_input if mode=='listener' else app.listener_text
            for keysym,state in [('l',4),('L',6)]:
                app.listener_write('old output\n','result')
                if mode=='listener':
                    app.listener_input.delete(0,'end')
                    app.listener_input.insert(0,'pending command')
                else:
                    app._set_console_input('pending command')
                widget.focus_force();app.update()
                widget.event_generate('<KeyPress>',keysym=keysym,state=state)
                app.update()
                assert 'old output' not in app.listener_text.get('1.0','end'),(mode,keysym)
                pending=app.listener_input.get() if mode=='listener' else app._console_input()
                assert pending=='pending command',(mode,keysym,pending)
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

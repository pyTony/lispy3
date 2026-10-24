"""Python editor execution/input, highlighting and indentation using real Tk."""
from pathlib import Path
import subprocess
import sys
from unittest import TestCase


class PythonEditorTkTest(TestCase):
    def test_python_editor_execution_and_indentation(self):
        script = r'''
import contextlib, importlib.machinery, importlib.util, io, os, subprocess, sys, time, tkinter as tk
from unittest.mock import patch
loader=importlib.machinery.SourceFileLoader('python_machine_probe','lispy_machine.pyw')
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
    def wait(predicate):
        deadline=time.monotonic()+12
        while not predicate() and time.monotonic()<deadline:
            app.update(); time.sleep(.005)
        assert predicate(), app.listener_text.get('1.0','end')
    try:
        tab=app.new_buffer('interactive.py','name=input("Name: ")\nprint("Hello",name)\n')
        assert tab.language.name == 'Python'
        for mode in ('basic','listener'):
            app.listener_mode.set(mode)
            app._select_listener_mode()
            if mode == 'basic': app._set_console_input('pending command')
            app.eval_buffer()
            wait(lambda: getattr(app,'_basic_input_queue',None) is not None)
            app.listener_text.insert('end','RUN')
            app._console_return()
            wait(lambda: app._job is None)
            assert 'Hello RUN\n' in app.listener_text.get('1.0','end').replace('\r\n','\n')
            assert app.listener_mode.get() == mode
            if mode == 'basic': assert app._console_input() == 'pending command'
        app.eval_buffer()
        wait(lambda: getattr(app,'_basic_input_queue',None) is not None)
        app.stop()
        wait(lambda: app._job is None)
        assert getattr(app,'_basic_input_queue',None) is None
        assert app.listener_mode.get() == 'listener'

        tab.text.delete('1.0','end')
        tab.text.insert('1.0','print("ok")\n1/0\n')
        app.eval_buffer()
        wait(lambda: app._job is None)
        assert str(tab.text.tag_ranges('syntax_error')[0]) == '2.0'
        tab.text.delete('1.0','end')
        tab.text.insert('1.0','\n'*6+'    print("selected")\n    raise ValueError("selection")\n')
        app.eval_buffer(python_source=True,source='    print("selected")\n    raise ValueError("selection")',source_line=7)
        wait(lambda: app._job is None)
        assert str(tab.text.tag_ranges('syntax_error')[0]) == '8.0'

        source='if True:\n  text="""line\n  literal\n"""\n  print(text)\n'
        tab.text.delete('1.0','end')
        tab.text.insert('1.0',source)
        app.reindent_buffer()
        assert tab.get_content() == 'if True:\n    text="""line\n  literal\n"""\n    print(text)\n'
        tab.text.edit_undo()
        assert tab.get_content() == source
        tab.text.delete('1.0','end')
        tab.text.insert('1.0','if True:')
        tab.text.mark_set('insert','end-1c')
        tab._on_return()
        assert tab.get_content() == 'if True:\n    '

        tab.text.delete('1.0','end')
        tab.text.insert('1.0','name=input("ANSI name: ")\nprint("ANSI hello",name)\n')
        children=[]
        def launch(port,token,cwd):
            process=subprocess.Popen([sys.executable,module.lispy_terminal.__file__,'--connect',str(port),'--token',token],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                env=dict(os.environ,PYTHONIOENCODING='utf-8'))
            process.stdin.write(b'Ada\n'); process.stdin.flush()
            children.append(process)
            return process
        with patch.object(module.lispy_terminal,'launch_viewer',launch), patch.object(sys,'__stdout__',None), contextlib.redirect_stdout(io.StringIO()):
            app.eval_buffer(terminal=True)
            wait(lambda: app._job is None)
        output,error=children[0].communicate(timeout=5)
        assert children[0].returncode == 0,error
        assert b'ANSI hello Ada' in output,output
        assert app.listener_mode.get() == 'listener'
    finally:
        app.basic_repl.close()
        app.destroy()
print('Python editor execution, input and indentation OK')
'''
        result = subprocess.run([sys.executable, '-c', script],
            cwd=Path(__file__).resolve().parents[1], capture_output=True,
            text=True, timeout=65)
        if result.returncode == 77:
            self.skipTest('Tk display unavailable')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Python editor execution, input and indentation OK', result.stdout)

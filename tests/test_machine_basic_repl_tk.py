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
with patch.object(module,'load_settings',return_value={'startup_run':False,'startup_show_buffer':False,'lispy_support.basic_repl':True,'plain_repl':True}), patch.object(module,'save_settings'):
    try:
        app=module.LispMachine([])
    except tk.TclError as error:
        if 'display' in str(error).lower(): sys.exit(77)
        raise
    app.withdraw()
    try:
        assert not app.basic_repl_mode.get(), 'startup restored BASIC instead of Lisp'
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
        app._basic_feed(['10 PRINT "stored CLI program"', 'RUN'])
        deadline=time.monotonic()+10
        while app._job is not None and time.monotonic()<deadline:
            app.update(); time.sleep(.005)
        assert app._job is None, 'worker did not complete'
        output=app.listener_text.get('1.0','end')
        assert 'stored CLI program\n' in output, output
        assert 'edited buffer\n' not in output, output
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
        tab.text.delete('1.0','end')
        tab.text.insert('1.0','PRINT "before CLS"\nCLS\nPRINT "after CLS"\nINPUT "Enter: " pause$\n')
        app.eval_buffer()
        deadline=time.monotonic()+10
        while getattr(app,'_basic_input_queue',None) is None and time.monotonic()<deadline:
            app.update(); time.sleep(.005)
        assert getattr(app,'_basic_input_queue',None) is not None
        output=app.listener_text.get('1.0','end-1c')
        assert output == 'after CLS\nEnter: ', repr(output)
        app._console_return()
        deadline=time.monotonic()+10
        while app._job is not None and time.monotonic()<deadline:
            app.update(); time.sleep(.005)
        assert app._job is None
        output=app.listener_text.get('1.0','end-1c')
        assert output == 'after CLS\nEnter: \nBASIC> ', repr(output)
        app._set_console_input('PRINT "next command"')
        app._console_return()
        deadline=time.monotonic()+10
        while app._job is not None and time.monotonic()<deadline:
            app.update(); time.sleep(.005)
        assert app._job is None
        assert 'next command\n' in app.listener_text.get('1.0','end')
        app._set_console_input('PRINT "pending command"')
        writer=module._ListenerWriter(app)
        writer.write('\x1b[2J\x1b[H')
        assert app.listener_text.get('1.0','end-1c') == 'BASIC> PRINT "pending command"'
        assert app.console_ready
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'loaded program.bas'
            path.write_text('10 PRINT "loaded source"\n')
            app._output_mode='ansi'
            with patch.object(module.lispy_terminal,'ansi_terminal_output',side_effect=AssertionError('management opened terminal')):
                app._basic_feed(['LOAD "'+path.as_posix()+'"','LIST'])
                deadline=time.monotonic()+10
                while app._job is not None and time.monotonic()<deadline:
                    app.update(); time.sleep(.005)
                assert app._job is None
            loaded=app.current_tab()
            assert loaded.path == str(path.resolve()), loaded.path
            assert loaded.get_content() == '10 PRINT "loaded source"\n'
            assert '10 PRINT "loaded source"\n' in app.listener_text.get('1.0','end')
            app._output_mode='listener'
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
